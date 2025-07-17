use anyhow::{Context, Result};
use csv::Writer;
use libc::{rlimit, RLIMIT_NOFILE};

use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tempfile::TempDir;
use tokio::sync::mpsc;
use tokio::task::JoinHandle;
use tokio::time::sleep;
use tokio_postgres::NoTls;

// Test with exactly these numbers of extra listening connections
const EXTRA_CONNECTION_COUNTS: &[usize] = &[0, 10, 100, 1000];
const MEASUREMENTS_PER_CONNECTION_COUNT: usize = 3;

#[derive(Debug, Clone)]
struct BenchmarkResult {
    connection_count: usize,
    tps: f64,
    version: String,
}

async fn find_free_port() -> Result<u16> {
    for port in 5432..65535 {
        if port_scanner::local_port_available(port) {
            return Ok(port);
        }
    }
    anyhow::bail!("No free port found")
}

async fn setup_postgres(
    pg_bin_path: Option<&Path>,
    custom_version: Option<String>,
    notify_multicast_threshold: Option<String>,
) -> Result<(TempDir, u16, String, String)> {
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
    for (tool_name, tool_path) in &[
        ("initdb", &initdb_cmd),
        ("pg_ctl", &pg_ctl_cmd),
        ("createdb", &createdb_cmd),
    ] {
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
autovacuum = off

# Connection logging settings
# log_connections = on
# log_disconnections = on
# log_statement = 'all'
# log_min_messages = debug1
# trace_notify = on

"#;

    file.write_all(config_settings.as_bytes())
        .context("Failed to write to postgresql.conf")?;

    println!("Appended configuration to postgresql.conf");

    // Start PostgreSQL
    let mut pg_ctl_args = vec![
        "-D",
        data_dir.to_str().unwrap(),
        "-l",
        "/tmp/pg.log",
        "-o",
    ];
    
    // Build the options string for postgres
    let mut postgres_options = format!("-p {}", port);
    if let Some(ref threshold) = notify_multicast_threshold {
        postgres_options.push_str(&format!(" -c notify_multicast_threshold={}", threshold));
        println!("Starting PostgreSQL with notify_multicast_threshold={}", threshold);
    }
    
    pg_ctl_args.push(&postgres_options);
    pg_ctl_args.push("start");
    
    let output = Command::new(&pg_ctl_cmd)
        .args(&pg_ctl_args)
        .output()?;

    if !output.status.success() {
        anyhow::bail!(
            "pg_ctl start failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
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
        anyhow::bail!(
            "createdb failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    let connection_string = format!(
        "host=127.0.0.1 port={} dbname=testdb user={}",
        port,
        whoami::username()
    );

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

async fn cleanup_postgres(
    data_dir: &PathBuf,
    _port: u16,
    pg_bin_path: Option<&Path>,
) -> Result<()> {
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
        eprintln!(
            "Warning: pg_ctl stop failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    Ok(())
}

async fn create_listener_thread(
    thread_id: usize,
    connection_string: String,
    ready: Arc<AtomicBool>,
    other_ready: Arc<AtomicBool>,
    round_trip_counter: Arc<AtomicU64>,
    stop_flag: Arc<AtomicBool>,
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
        client
            .execute(&format!("LISTEN {}", channel_name), &[])
            .await?;

        // Signal that we're ready
        ready.store(true, Ordering::SeqCst);

        // Wait for the other thread to be ready
        while !other_ready.load(Ordering::SeqCst) {
            sleep(Duration::from_millis(10)).await;
        }

        // Thread 1 initiates the ping-pong
        if thread_id == 1 {
            sleep(Duration::from_millis(100)).await;
            let initial_notify = "SELECT pg_notify('thread_2', NULL)";
            client.execute(initial_notify, &[]).await?;
        }

        // Main notification loop
        let mut notification_count = 0;
        while let Some(notification) = rx_notif.recv().await {
            notification_count += 1;

            // Check if we should stop
            if stop_flag.load(Ordering::SeqCst) {
                println!(
                    "Thread {} stopping after {} notifications",
                    thread_id, notification_count
                );
                break;
            }

            // Increment round-trip counter (only count on one thread to avoid double counting)
            if thread_id == 1 {
                let current_count = round_trip_counter.fetch_add(1, Ordering::SeqCst);
                if current_count % 10000 == 0 && current_count > 0 {
                    println!("Thread 1 processed {} round-trips", current_count);
                }
            }

            // Verify notification
            let expected_channel = format!("thread_{}", thread_id);
            if notification.channel() != expected_channel {
                anyhow::bail!(
                    "Unexpected channel: {} (expected {})",
                    notification.channel(),
                    expected_channel
                );
            }
            if !notification.payload().is_empty() {
                anyhow::bail!(
                    "Unexpected payload: {} (expected empty)",
                    notification.payload()
                );
            }

            // Send notification to the other thread
            let other_thread = if thread_id == 1 { 2 } else { 1 };
            let notify_cmd = format!("SELECT pg_notify('thread_{}', NULL)", other_thread);
            if let Err(e) = client.execute(&notify_cmd, &[]).await {
                eprintln!("Thread {} failed to send notification: {}", thread_id, e);
                break;
            }
        }

        println!(
            "Thread {} exiting after {} notifications",
            thread_id, notification_count
        );
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
                match client
                    .execute(&format!("LISTEN {}", channel_name), &[])
                    .await
                {
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
    let mut custom_version = None;
    let mut notify_multicast_threshold = None;

    // Simple argument parsing
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--version-name" => {
                if i + 1 < args.len() {
                    custom_version = Some(args[i + 1].clone());
                    i += 2;
                } else {
                    anyhow::bail!("--version-name requires a value");
                }
            }
            "--notify-multicast-threshold" => {
                if i + 1 < args.len() {
                    notify_multicast_threshold = Some(args[i + 1].clone());
                    i += 2;
                } else {
                    anyhow::bail!("--notify-multicast-threshold requires a value");
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
    if let Some(ref threshold) = notify_multicast_threshold {
        println!("Using notify_multicast_threshold: {}", threshold);
    }

    // Check and increase OS limits
    println!("Checking and adjusting OS limits...");

    // Get current limits
    let mut rlim = rlimit {
        rlim_cur: 0,
        rlim_max: 0,
    };

    unsafe {
        if libc::getrlimit(RLIMIT_NOFILE, &mut rlim) == 0 {
            println!(
                "Current file descriptor limit: soft={}, hard={}",
                rlim.rlim_cur, rlim.rlim_max
            );

            // Try to set to 65536 (equivalent to ulimit -n 65536)
            let target_limit = 65536u64;
            rlim.rlim_cur = target_limit;
            if rlim.rlim_max < target_limit {
                rlim.rlim_max = target_limit;
            }

            if libc::setrlimit(RLIMIT_NOFILE, &rlim) == 0 {
                println!("Successfully set file descriptor limit to {}", target_limit);
            } else {
                // If that fails, try just setting to the hard limit
                rlim.rlim_cur = rlim.rlim_max;
                if libc::setrlimit(RLIMIT_NOFILE, &rlim) == 0 {
                    println!("Set file descriptor limit to hard limit: {}", rlim.rlim_max);
                } else {
                    eprintln!("Warning: Could not increase file descriptor limit");
                    eprintln!("You may need to run: ulimit -n 65536");
                }
            }

            // Verify the new limit
            if libc::getrlimit(RLIMIT_NOFILE, &mut rlim) == 0 {
                println!(
                    "New file descriptor limit: soft={}, hard={}",
                    rlim.rlim_cur, rlim.rlim_max
                );
            }
        }
    }

    // Create or append to CSV file
    let file_exists = std::path::Path::new(output_file).exists();
    let file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(output_file)?;
    let mut csv_writer = Writer::from_writer(file);

    // Write header only if file is new
    if !file_exists {
        csv_writer.write_record(&["connections", "tps", "version"])?;
    }

    let mut benchmark_results: Vec<BenchmarkResult> = Vec::new();

    // Test each connection count
    for &extra_connections in EXTRA_CONNECTION_COUNTS {
        for measurement_run in 1..=MEASUREMENTS_PER_CONNECTION_COUNT {
            println!("\n========================================");
            println!(
                "Testing with {} extra connections - Run {}/{}",
                extra_connections,
                measurement_run,
                MEASUREMENTS_PER_CONNECTION_COUNT
            );
            println!("========================================");

            // Setup PostgreSQL for this test run
            println!("Setting up PostgreSQL for this test run...");
            let (temp_dir, port, connection_string, pg_version) =
                setup_postgres(pg_bin_path, custom_version.clone(), notify_multicast_threshold.clone()).await?;
            let data_dir = temp_dir.path().join("data");

            println!("PostgreSQL started on port {}", port);
            println!("Data directory: {:?}", data_dir);
            println!("Connection string: {}", connection_string);
            println!("PostgreSQL version: {}", pg_version);

            // Create monitoring connection
            println!("Creating monitoring connection...");
            let (monitor_client, monitor_connection) =
                tokio_postgres::connect(&connection_string, NoTls).await?;
            tokio::spawn(async move {
                if let Err(e) = monitor_connection.await {
                    eprintln!("Monitor connection error: {}", e);
                }
            });

            // Verify max_connections setting
            let row = monitor_client
                .query_one("SHOW max_connections", &[])
                .await?;
            let max_conn: &str = row.get(0);
            println!("PostgreSQL max_connections: {}", max_conn);

            // Check other connection limits
            let row = monitor_client
                .query_one("SHOW superuser_reserved_connections", &[])
                .await?;
            let reserved: &str = row.get(0);
            println!("PostgreSQL superuser_reserved_connections: {}", reserved);

            // Also check shared_buffers as it affects max connections
            let row = monitor_client.query_one("SHOW shared_buffers", &[]).await?;
            let shared_buffers: &str = row.get(0);
            println!("PostgreSQL shared_buffers: {}", shared_buffers);

            println!("Manual connection test command:");
            println!("  psql '{}'", connection_string);

            let total_connections = 3 + extra_connections; // 2 ping-pong threads + 1 monitor + extra listeners

            println!("\n========================================");
            println!(
                "Testing with {} extra connections ({} total) - Run {}/{}",
                extra_connections,
                total_connections,
                measurement_run,
                MEASUREMENTS_PER_CONNECTION_COUNT
            );
            println!("Connection string: {}", connection_string);
            println!("Test plan:");
            println!("  - 2 ping-pong threads (thread_1, thread_2)");
            println!("  - 1 monitor connection");
            println!(
                "  - {} idle listener threads (thread_3 to thread_{})",
                extra_connections,
                3 + extra_connections - 1
            );
            println!("========================================");

            // Create ready flags and counters
            let thread1_ready = Arc::new(AtomicBool::new(false));
            let thread2_ready = Arc::new(AtomicBool::new(false));
            let round_trip_counter = Arc::new(AtomicU64::new(0));
            let stop_flag = Arc::new(AtomicBool::new(false));

            // Start listener threads
            println!("Starting ping-pong threads...");
            let _thread1 = create_listener_thread(
                1,
                connection_string.clone(),
                thread1_ready.clone(),
                thread2_ready.clone(),
                round_trip_counter.clone(),
                stop_flag.clone(),
            )
            .await?;

            let _thread2 = create_listener_thread(
                2,
                connection_string.clone(),
                thread2_ready.clone(),
                thread1_ready.clone(),
                round_trip_counter.clone(),
                stop_flag.clone(),
            )
            .await?;

            // Wait for both threads to be ready
            while !thread1_ready.load(Ordering::SeqCst) || !thread2_ready.load(Ordering::SeqCst) {
                sleep(Duration::from_millis(10)).await;
            }

            // Create idle listener connections
            let mut idle_threads = Vec::new();
            println!(
                "Creating {} idle listener connections...",
                extra_connections
            );
            for thread_id in 3..(3 + extra_connections) {
                println!("Creating idle listener thread {}", thread_id);
                match create_idle_listener(connection_string.clone(), thread_id).await {
                    Ok(idle_thread) => {
                        idle_threads.push(idle_thread);
                    }
                    Err(e) => {
                        eprintln!("Failed to create idle listener {}: {}", thread_id, e);
                        break;
                    }
                }
            }

            // Wait a bit for all connections to be established
            println!("Waiting 500ms for all connections to be established...");
            sleep(Duration::from_millis(500)).await;

            // Check if ping-pong is still active before warm-up
            println!("Checking ping-pong activity...");
            let pre_warmup_count = round_trip_counter.load(Ordering::SeqCst);
            sleep(Duration::from_millis(100)).await;
            let post_check_count = round_trip_counter.load(Ordering::SeqCst);

            if post_check_count > pre_warmup_count {
                println!(
                    "Ping-pong is active: {} round-trips during 100ms check",
                    post_check_count - pre_warmup_count
                );
            } else {
                println!("WARNING: Ping-pong appears to be stalled before warm-up!");
                println!("Manual test commands:");
                println!("  psql '{}' -c \"LISTEN thread_1;\"", connection_string);
                println!("  psql '{}' -c \"LISTEN thread_2;\"", connection_string);
                println!(
                    "  psql '{}' -c \"SELECT pg_notify('thread_2', NULL);\"",
                    connection_string
                );
                println!(
                    "  psql '{}' -c \"SELECT pg_notify('thread_1', NULL);\"",
                    connection_string
                );
            }

            // Warm-up period (1 second)
            println!("Starting 1-second warm-up period...");
            sleep(Duration::from_secs(1)).await;

            // Check if ping-pong is still active after warm-up
            let pre_reset_count = round_trip_counter.load(Ordering::SeqCst);
            println!(
                "Ping-pong completed {} round-trips during warm-up",
                pre_reset_count
            );

            // Reset counter after warm-up
            round_trip_counter.store(0, Ordering::SeqCst);

            // Start timing for TPS measurement
            println!("Starting 10-second TPS measurement...");
            let start_time = Instant::now();

            // Check periodically if ping-pong is active
            for i in 0..10 {
                sleep(Duration::from_secs(1)).await;
                let current_count = round_trip_counter.load(Ordering::SeqCst);
                if i == 0 && current_count == 0 {
                    println!("WARNING: No round-trips detected in first second!");
                }
                if i % 2 == 0 {
                    println!("After {} seconds: {} round-trips", i + 1, current_count);
                }
            }

            // Stop the ping-pong
            stop_flag.store(true, Ordering::SeqCst);

            let elapsed = start_time.elapsed();
            let round_trips = round_trip_counter.load(Ordering::SeqCst);
            let tps = round_trips as f64 / elapsed.as_secs_f64();

            println!(
                "Completed {} round-trips in {:.2} seconds",
                round_trips,
                elapsed.as_secs_f64()
            );
            println!("TPS: {:.2}", tps);

            // Store result
            benchmark_results.push(BenchmarkResult {
                connection_count: extra_connections,
                tps,
                version: pg_version.clone(),
            });

            // Clean up threads (they should exit naturally due to stop_flag)
            sleep(Duration::from_millis(100)).await;

            // Cleanup PostgreSQL for this test run
            println!("Cleaning up PostgreSQL for this test run...");
            cleanup_postgres(&data_dir, port, pg_bin_path).await?;
            println!("PostgreSQL cleanup complete.");
        }
    }

    // Write all collected measurements to CSV
    println!(
        "\nWriting {} measurements to CSV...",
        benchmark_results.len()
    );
    for result in benchmark_results {
        csv_writer.write_record(&[
            result.connection_count.to_string(),
            format!("{:.2}", result.tps),
            result.version,
        ])?;
    }
    csv_writer.flush()?;
    println!("CSV writing complete.");

    Ok(())
}
