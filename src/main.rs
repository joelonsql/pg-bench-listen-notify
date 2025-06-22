use anyhow::{Context, Result};
use libc::{rlimit, RLIMIT_NOFILE};
use csv::Writer;

use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tempfile::TempDir;
use tokio::sync::mpsc;
use tokio::task::JoinHandle;
use tokio::time::sleep;
use tokio_postgres::NoTls;

const MAX_CONNECTIONS: usize = 1000;

#[derive(Debug, Clone)]
struct Measurement {
    round_trip_ns: u128,
    #[allow(dead_code)]
    thread_id: usize,
}

async fn find_free_port() -> Result<u16> {
    for port in 5432..65535 {
        if port_scanner::local_port_available(port) {
            return Ok(port);
        }
    }
    anyhow::bail!("No free port found")
}

async fn setup_postgres(pg_bin_path: Option<&Path>, custom_version: Option<String>) -> Result<(TempDir, u16, String, String)> {
    // Build command paths
    let (initdb_cmd, pg_ctl_cmd, createdb_cmd) = if let Some(bin_path) = pg_bin_path {
        (
            bin_path.join("initdb"),
            bin_path.join("pg_ctl"),
            bin_path.join("createdb"),
        )
    } else {
        (
            PathBuf::from("initdb"),
            PathBuf::from("pg_ctl"),
            PathBuf::from("createdb"),
        )
    };

    // Check for PostgreSQL tools
    for (tool_name, tool_path) in &[("initdb", &initdb_cmd), ("pg_ctl", &pg_ctl_cmd), ("createdb", &createdb_cmd)] {
        Command::new(tool_path)
            .arg("--version")
            .output()
            .with_context(|| format!("{} not found at {:?}", tool_name, tool_path))?;
    }

    let temp_dir = TempDir::new()?;
    let data_dir = temp_dir.path().join("data");
    let port = find_free_port().await?;

    // Initialize database
    let output = Command::new(&initdb_cmd)
        .arg("-D")
        .arg(&data_dir)
        .arg("--auth=trust")
        .arg("--encoding=UTF8")
        .output()?;

    if !output.status.success() {
        anyhow::bail!("initdb failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    // Configure PostgreSQL settings by appending to postgresql.conf
    println!("Configuring PostgreSQL settings...");
    let config_file = data_dir.join("postgresql.conf");

    // Append configuration settings
    use std::fs::OpenOptions;
    use std::io::Write;

    let mut file = OpenOptions::new()
        .append(true)
        .open(&config_file)
        .context("Failed to open postgresql.conf")?;

    // With 128GB RAM, use 25% (32GB) for shared_buffers
    let config_settings = r#"
# Custom settings for benchmarking
max_connections = 2000
shared_buffers = 32GB
work_mem = 1MB
maintenance_work_mem = 256MB
"#;

    file.write_all(config_settings.as_bytes())
        .context("Failed to write to postgresql.conf")?;

    println!("Appended configuration to postgresql.conf");

    // Start PostgreSQL
    let output = Command::new(&pg_ctl_cmd)
        .arg("-D")
        .arg(&data_dir)
        .arg("-l")
        .arg(temp_dir.path().join("logfile"))
        .arg("-o")
        .arg(format!("-p {}", port))
        .arg("start")
        .output()?;

    if !output.status.success() {
        anyhow::bail!("pg_ctl start failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    // Wait for PostgreSQL to start
    println!("Waiting for PostgreSQL to start...");
    sleep(Duration::from_secs(3)).await;

    // Create test database
    println!("Creating test database...");
    let output = Command::new(&createdb_cmd)
        .arg("-p")
        .arg(port.to_string())
        .arg("testdb")
        .output()?;

    if !output.status.success() {
        anyhow::bail!("createdb failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    let connection_string = format!("host=127.0.0.1 port={} dbname=testdb user={}", port, whoami::username());

    // Get PostgreSQL version
    let (client, connection) = tokio_postgres::connect(&connection_string, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("Version check connection error: {}", e);
        }
    });

    let version = if let Some(custom) = custom_version {
        // Use custom version name if provided
        custom
    } else {
        // Otherwise query PostgreSQL for its version
        let row = client.query_one("SELECT version()", &[]).await?;
        row.get(0)
    };

    println!("PostgreSQL version: {}", version);

    Ok((temp_dir, port, connection_string, version))
}

async fn cleanup_postgres(data_dir: &PathBuf, _port: u16, pg_bin_path: Option<&Path>) -> Result<()> {
    let pg_ctl_cmd = if let Some(bin_path) = pg_bin_path {
        bin_path.join("pg_ctl")
    } else {
        PathBuf::from("pg_ctl")
    };

    let output = Command::new(&pg_ctl_cmd)
        .arg("-D")
        .arg(data_dir)
        .arg("-m")
        .arg("immediate")
        .arg("stop")
        .output()?;

    if !output.status.success() {
        eprintln!("Warning: pg_ctl stop failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    Ok(())
}

async fn create_listener_thread(
    thread_id: usize,
    connection_string: String,
    tx: mpsc::Sender<Measurement>,
    ready: Arc<AtomicBool>,
    other_ready: Arc<AtomicBool>,
) -> Result<JoinHandle<Result<()>>> {
    let handle = tokio::spawn(async move {
        let (client, mut connection) = tokio_postgres::connect(&connection_string, NoTls).await?;

        // Create channel for notifications
        let (tx_notif, mut rx_notif) = mpsc::unbounded_channel();

        // Spawn connection handler
        tokio::spawn(async move {
            loop {
                match futures_util::future::poll_fn(|cx| connection.poll_message(cx)).await {
                    Some(Ok(tokio_postgres::AsyncMessage::Notification(notif))) => {
                        if tx_notif.send(notif).is_err() {
                            break;
                        }
                    }
                    Some(Ok(_)) => {} // Ignore other message types
                    Some(Err(e)) => {
                        eprintln!("Thread {} connection error: {}", thread_id, e);
                        break;
                    }
                    None => break,
                }
            }
        });

        // Listen on our channel
        let channel_name = format!("thread_{}", thread_id);
        client.execute(&format!("LISTEN {}", channel_name), &[]).await?;

        // Signal that we're ready
        ready.store(true, Ordering::SeqCst);

        // Wait for the other thread to be ready
        while !other_ready.load(Ordering::SeqCst) {
            sleep(Duration::from_millis(10)).await;
        }

        // Thread 1 initiates the ping-pong
        if thread_id == 1 {
            sleep(Duration::from_millis(100)).await;
            client.execute("SELECT pg_notify('thread_2', NULL)", &[]).await?;
        }

        // Main notification loop
        let mut start_time = Instant::now();

        while let Some(notification) = rx_notif.recv().await {
            let elapsed = start_time.elapsed();

            // Send measurement
            tx.send(Measurement {
                round_trip_ns: elapsed.as_nanos(),
                thread_id,
            }).await?;

            // Verify notification
            let expected_channel = format!("thread_{}", thread_id);
            if notification.channel() != expected_channel {
                anyhow::bail!("Unexpected channel: {} (expected {})", notification.channel(), expected_channel);
            }
            if !notification.payload().is_empty() {
                anyhow::bail!("Unexpected payload: {} (expected empty)", notification.payload());
            }

            // Record new start time before sending notification
            start_time = Instant::now();

            // Send notification to the other thread
            let other_thread = if thread_id == 1 { 2 } else { 1 };
            client.execute(&format!("SELECT pg_notify('thread_{}', NULL)", other_thread), &[]).await?;
        }

        Ok(())
    });

    Ok(handle)
}

async fn create_idle_listener(
    connection_string: String,
    thread_id: usize,
) -> Result<JoinHandle<Result<()>>> {
    let conn_str = connection_string.clone();
    let handle = tokio::spawn(async move {
        match tokio_postgres::connect(&conn_str, NoTls).await {
            Ok((client, connection)) => {
                tokio::spawn(async move {
                    if let Err(e) = connection.await {
                        eprintln!("Idle thread {} connection error: {}", thread_id, e);
                    }
                });

                // Listen on our channel
                let channel_name = format!("thread_{}", thread_id);
                match client.execute(&format!("LISTEN {}", channel_name), &[]).await {
                    Ok(_) => {
                        // Remain idle
                        loop {
                            sleep(Duration::from_secs(3600)).await;
                        }
                    }
                    Err(e) => {
                        eprintln!("Idle thread {} LISTEN failed: {}", thread_id, e);
                        return Err(e.into());
                    }
                }
            }
            Err(e) => {
                eprintln!("Idle thread {} connection failed: {}", thread_id, e);
                return Err(e.into());
            }
        }
    });

    Ok(handle)
}

#[tokio::main]
async fn main() -> Result<()> {
    // Parse command line arguments
    let args: Vec<String> = env::args().collect();
    let mut pg_bin_path = None;
    let mut output_file = "stats.csv";
    let mut increment = 1;
    let mut custom_version = None;

    // Simple argument parsing
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--increment" => {
                if i + 1 < args.len() {
                    increment = args[i + 1].parse::<usize>()
                        .context("Invalid increment value")?;
                    if increment == 0 {
                        anyhow::bail!("Increment must be greater than 0");
                    }
                    i += 2;
                } else {
                    anyhow::bail!("--increment requires a value");
                }
            }
            "--version-name" => {
                if i + 1 < args.len() {
                    custom_version = Some(args[i + 1].clone());
                    i += 2;
                } else {
                    anyhow::bail!("--version-name requires a value");
                }
            }
            arg => {
                // Positional arguments
                if pg_bin_path.is_none() && !arg.starts_with("--") {
                    pg_bin_path = Some(Path::new(arg));
                } else if output_file == "stats.csv" && !arg.starts_with("--") {
                    output_file = arg;
                }
                i += 1;
            }
        }
    }

    if let Some(path) = pg_bin_path {
        println!("Using PostgreSQL binaries from: {:?}", path);
    }
    if let Some(ref version) = custom_version {
        println!("Using custom version name: {}", version);
    }
    println!("Connection increment: {} per measurement", increment);

    // Check and increase OS limits
    println!("Checking and adjusting OS limits...");

    // Get current limits
    let mut rlim = rlimit {
        rlim_cur: 0,
        rlim_max: 0,
    };

    unsafe {
        if libc::getrlimit(RLIMIT_NOFILE, &mut rlim) == 0 {
            println!("Current file descriptor limit: soft={}, hard={}", rlim.rlim_cur, rlim.rlim_max);

            // Try to set to a high value (3 times MAX_CONNECTIONS should be enough)
            let new_limit = (MAX_CONNECTIONS * 3) as u64;
            rlim.rlim_cur = new_limit;
            if rlim.rlim_max < new_limit {
                rlim.rlim_max = new_limit;
            }

            if libc::setrlimit(RLIMIT_NOFILE, &rlim) == 0 {
                println!("Successfully set file descriptor limit to {}", new_limit);
            } else {
                // If that fails, try just setting to the hard limit
                rlim.rlim_cur = rlim.rlim_max;
                if libc::setrlimit(RLIMIT_NOFILE, &rlim) == 0 {
                    println!("Set file descriptor limit to hard limit: {}", rlim.rlim_max);
                } else {
                    eprintln!("Warning: Could not increase file descriptor limit");
                }
            }

            // Verify the new limit
            if libc::getrlimit(RLIMIT_NOFILE, &mut rlim) == 0 {
                println!("New file descriptor limit: soft={}, hard={}", rlim.rlim_cur, rlim.rlim_max);
            }
        }
    }

    println!("Setting up PostgreSQL...");
    let (temp_dir, port, connection_string, pg_version) = setup_postgres(pg_bin_path, custom_version).await?;
    let data_dir = temp_dir.path().join("data");

    println!("PostgreSQL started on port {}", port);

    // Create monitoring connection
    let (monitor_client, monitor_connection) = tokio_postgres::connect(&connection_string, NoTls).await?;
    tokio::spawn(async move {
        if let Err(e) = monitor_connection.await {
            eprintln!("Monitor connection error: {}", e);
        }
    });

    // Verify max_connections setting
    let row = monitor_client.query_one("SHOW max_connections", &[]).await?;
    let max_conn: &str = row.get(0);
    println!("PostgreSQL max_connections: {}", max_conn);

    // Check other connection limits
    let row = monitor_client.query_one("SHOW superuser_reserved_connections", &[]).await?;
    let reserved: &str = row.get(0);
    println!("PostgreSQL superuser_reserved_connections: {}", reserved);

    // Also check shared_buffers as it affects max connections
    let row = monitor_client.query_one("SHOW shared_buffers", &[]).await?;
    let shared_buffers: &str = row.get(0);
    println!("PostgreSQL shared_buffers: {}", shared_buffers);

    // Create or append to CSV file
    let file_exists = std::path::Path::new(output_file).exists();
    let file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(output_file)?;
    let mut csv_writer = Writer::from_writer(file);

    // Write header only if file is new
    if !file_exists {
        csv_writer.write_record(&[
            "connections", "latency_ms", "version"
        ])?;
    }

    // Create channels for measurements
    let (tx, mut rx) = mpsc::channel::<Measurement>(1000);

    // Create ready flags
    let thread1_ready = Arc::new(AtomicBool::new(false));
    let thread2_ready = Arc::new(AtomicBool::new(false));

    // Start listener threads
    println!("Starting listener threads...");
    let _thread1 = create_listener_thread(
        1,
        connection_string.clone(),
        tx.clone(),
        thread1_ready.clone(),
        thread2_ready.clone(),
    ).await?;

    let _thread2 = create_listener_thread(
        2,
        connection_string.clone(),
        tx.clone(),
        thread2_ready.clone(),
        thread1_ready.clone(),
    ).await?;

    // Wait for both threads to be ready
    while !thread1_ready.load(Ordering::SeqCst) || !thread2_ready.load(Ordering::SeqCst) {
        sleep(Duration::from_millis(10)).await;
    }

    println!("Threads ready, starting measurements...");

    let mut idle_threads = Vec::new();
    let mut next_thread_id = 3;
    let mut measurement_count = 0;

    // Main measurement loop
    loop {
        if let Ok(measurement) = rx.try_recv() {
            let connection_count = 3 + idle_threads.len(); // 2 threads + 1 monitor
            let latency_ms = measurement.round_trip_ns as f64 / 1_000_000.0;

            // Write individual measurement to CSV
            csv_writer.write_record(&[
                connection_count.to_string(),
                format!("{:.2}", latency_ms),
                pg_version.clone(),
            ])?;
            csv_writer.flush()?;

            measurement_count += 1;

            // Print progress every 20 measurements
            if measurement_count % 20 == 0 {
                println!("Connections: {:5}, Latest latency: {:7.2}ms (measurement {})", 
                         connection_count, latency_ms, measurement_count);
            }

            // Add new connections every 20 measurements
            if measurement_count % 20 == 0 {
                // Create new idle listeners based on increment
                let mut added = 0;
                for _ in 0..increment {
                    if idle_threads.len() >= MAX_CONNECTIONS {
                        break;
                    }
                    match create_idle_listener(connection_string.clone(), next_thread_id).await {
                        Ok(idle_thread) => {
                            idle_threads.push(idle_thread);
                            next_thread_id += 1;
                            added += 1;
                        }
                        Err(e) => {
                            eprintln!("Failed to create idle listener {}: {}", next_thread_id, e);
                            eprintln!("Connection string: {}", connection_string);
                            break;
                        }
                    }
                }

                if added > 0 && added < increment && idle_threads.len() < MAX_CONNECTIONS {
                    eprintln!("Warning: Only added {} connections instead of {}", added, increment);
                }

                // Stop when we reach MAX_CONNECTIONS connections
                if idle_threads.len() >= MAX_CONNECTIONS {
                    println!("Reached {} idle connections, stopping...", MAX_CONNECTIONS);
                    break;
                }
            }
        } else {
            sleep(Duration::from_millis(1)).await;
        }
    }

    // Cleanup
    println!("Cleaning up...");
    cleanup_postgres(&data_dir, port, pg_bin_path).await?;

    Ok(())
}