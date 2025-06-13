use anyhow::{Context, Result};
use libc::{rlimit, setrlimit, RLIMIT_NOFILE};
use csv::Writer;
use std::collections::VecDeque;
use std::fs::File;
use std::path::PathBuf;
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tempfile::TempDir;
use tokio::sync::mpsc;
use tokio::task::JoinHandle;
use tokio::time::sleep;
use tokio_postgres::NoTls;

#[derive(Debug, Clone)]
struct Measurement {
    round_trip_ns: u128,
    #[allow(dead_code)]
    thread_id: usize,
}

#[derive(Debug)]
struct Stats {
    min: f64,
    max: f64,
    avg: f64,
    stddev: f64,
}

fn calculate_stats(measurements: &[Measurement]) -> Stats {
    let values: Vec<f64> = measurements
        .iter()
        .map(|m| m.round_trip_ns as f64 / 1_000_000.0) // Convert to milliseconds
        .collect();

    let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let avg = values.iter().sum::<f64>() / values.len() as f64;

    let variance = values
        .iter()
        .map(|&x| (x - avg).powi(2))
        .sum::<f64>() / values.len() as f64;
    let stddev = variance.sqrt();

    Stats { min, max, avg, stddev }
}

async fn find_free_port() -> Result<u16> {
    for port in 5432..65535 {
        if port_scanner::local_port_available(port) {
            return Ok(port);
        }
    }
    anyhow::bail!("No free port found")
}

async fn setup_postgres() -> Result<(TempDir, u16, String)> {
    // Check for PostgreSQL tools
    for tool in &["initdb", "pg_ctl", "createdb"] {
        Command::new(tool)
            .arg("--version")
            .output()
            .with_context(|| format!("{} not found in PATH", tool))?;
    }

    let temp_dir = TempDir::new()?;
    let data_dir = temp_dir.path().join("data");
    let port = find_free_port().await?;

    // Initialize database
    let output = Command::new("initdb")
        .arg("-D")
        .arg(&data_dir)
        .arg("--auth=trust")
        .arg("--encoding=UTF8")
        .output()?;

    if !output.status.success() {
        anyhow::bail!("initdb failed: {}", String::from_utf8_lossy(&output.stderr));
    }


    // Start PostgreSQL
    let output = Command::new("pg_ctl")
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
    let output = Command::new("createdb")
        .arg("-p")
        .arg(port.to_string())
        .arg("testdb")
        .output()?;

    if !output.status.success() {
        anyhow::bail!("createdb failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    // Connect to postgres database first (not testdb) to set max_connections
    println!("Configuring max connections...");
    let postgres_connection_string = format!("host=127.0.0.1 port={} dbname=postgres user={}", port, whoami::username());
    
    // Try connecting with retries
    let mut connected = false;
    for i in 0..10 {
        match tokio_postgres::connect(&postgres_connection_string, NoTls).await {
            Ok((client, connection)) => {
                tokio::spawn(async move {
                    if let Err(e) = connection.await {
                        eprintln!("Setup connection error: {}", e);
                    }
                });

                // Set multiple parameters for high connection count
                // With 128GB RAM, use 25% (32GB) for shared_buffers
                let settings = vec![
                    "ALTER SYSTEM SET max_connections = 10100",
                    "ALTER SYSTEM SET shared_buffers = '32GB'",
                    "ALTER SYSTEM SET work_mem = '1MB'",
                    "ALTER SYSTEM SET maintenance_work_mem = '256MB'",
                ];
                
                let mut all_success = true;
                for setting in &settings {
                    match client.execute(*setting, &[]).await {
                        Ok(_) => println!("Applied: {}", setting),
                        Err(e) => {
                            eprintln!("{} failed: {}", setting, e);
                            all_success = false;
                        }
                    }
                }
                
                if all_success {
                    connected = true;
                    break;
                }
            }
            Err(e) => {
                eprintln!("Connection attempt {} failed: {}", i + 1, e);
                sleep(Duration::from_secs(1)).await;
            }
        }
    }

    if !connected {
        anyhow::bail!("Failed to connect and set max_connections");
    }

    // Stop PostgreSQL
    println!("Stopping PostgreSQL...");
    let output = Command::new("pg_ctl")
        .arg("-D")
        .arg(&data_dir)
        .arg("-m")
        .arg("fast")
        .arg("stop")
        .output()?;

    if !output.status.success() {
        eprintln!("pg_ctl stop warning: {}", String::from_utf8_lossy(&output.stderr));
    }

    // Wait for shutdown
    sleep(Duration::from_secs(2)).await;

    // Start PostgreSQL again with new settings
    println!("Starting PostgreSQL with new settings...");
    let output = Command::new("pg_ctl")
        .arg("-D")
        .arg(&data_dir)
        .arg("-l")
        .arg(temp_dir.path().join("logfile"))
        .arg("-o")
        .arg(format!("-p {}", port))
        .arg("start")
        .output()?;

    if !output.status.success() {
        anyhow::bail!("pg_ctl start (after restart) failed: {}", String::from_utf8_lossy(&output.stderr));
    }

    // Wait for PostgreSQL to start
    println!("Waiting for PostgreSQL to start...");
    sleep(Duration::from_secs(3)).await;

    let connection_string = format!("host=127.0.0.1 port={} dbname=testdb user={}", port, whoami::username());
    Ok((temp_dir, port, connection_string))
}

async fn cleanup_postgres(data_dir: &PathBuf, _port: u16) -> Result<()> {
    let output = Command::new("pg_ctl")
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
            
            // Try to set to a high value (20000 should be enough for 10000 connections)
            let new_limit = 20000;
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
    let (temp_dir, port, connection_string) = setup_postgres().await?;
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

    // Create CSV writer
    let file = File::create("stats.csv")?;
    let mut csv_writer = Writer::from_writer(file);
    csv_writer.write_record(&["connections", "min_ms", "avg_ms", "max_ms", "stddev_ms"])?;

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

    let mut measurements = VecDeque::new();
    let mut idle_threads = Vec::new();
    let mut next_thread_id = 3;
    let mut measurement_count = 0;
    let mut phase = "increasing"; // "increasing" or "decreasing"

    // Main measurement loop
    loop {
        if let Ok(measurement) = rx.try_recv() {
            measurements.push_back(measurement);
            measurement_count += 1;

            // Collect stats every 10 measurements per thread (20 total)
            if measurement_count % 20 == 0 {
                let recent: Vec<Measurement> = measurements.drain(..).collect();
                let stats = calculate_stats(&recent);

                let connection_count = 3 + idle_threads.len(); // 2 threads + 1 monitor
                
                println!(
                    "Connections: {:5}, Min: {:7.2}ms, Avg: {:7.2}ms, Max: {:7.2}ms, StdDev: {:7.2}ms",
                    connection_count, stats.min, stats.avg, stats.max, stats.stddev
                );

                // Write to CSV
                csv_writer.write_record(&[
                    connection_count.to_string(),
                    format!("{:.2}", stats.min),
                    format!("{:.2}", stats.avg),
                    format!("{:.2}", stats.max),
                    format!("{:.2}", stats.stddev),
                ])?;
                csv_writer.flush()?;

                if phase == "increasing" {
                    // Create new idle listener
                    match create_idle_listener(connection_string.clone(), next_thread_id).await {
                        Ok(idle_thread) => {
                            idle_threads.push(idle_thread);
                            next_thread_id += 1;
                        }
                        Err(e) => {
                            eprintln!("Failed to create idle listener {}: {}", next_thread_id, e);
                            eprintln!("Connection string: {}", connection_string);
                        }
                    }

                    // Switch to decreasing phase after reaching 10000
                    if idle_threads.len() >= 10000 {
                        println!("Reached 10000 idle connections, now decreasing...");
                        phase = "decreasing";
                    }
                } else if phase == "decreasing" {
                    // Remove one idle connection
                    if let Some(handle) = idle_threads.pop() {
                        handle.abort();
                    }
                    
                    // Stop when we're back to just the two main threads
                    if idle_threads.is_empty() {
                        println!("Back to 2 connections, stopping...");
                        break;
                    }
                }
            }
        } else {
            sleep(Duration::from_millis(1)).await;
        }
    }

    // Cleanup
    println!("Cleaning up...");
    cleanup_postgres(&data_dir, port).await?;

    Ok(())
}