# pg-bench-listen-notify

A Rust benchmarking tool to measure PostgreSQL LISTEN/NOTIFY performance degradation as the number of idle listening connections increases.

## Overview

This tool demonstrates how PostgreSQL's LISTEN/NOTIFY round-trip time is affected by the number of concurrent connections, even when those connections are idle. It creates a controlled environment to measure this effect by:

- Setting up a temporary PostgreSQL instance
- Creating two threads that exchange LISTEN/NOTIFY messages in a ping-pong pattern
- Progressively adding idle listening connections (up to 1,000)
- Measuring round-trip latency at each stage
- Then removing connections one by one to observe recovery

## Results

![Benchmark Results](candlestick_comparison.png)

The candlestick chart shows the distribution of LISTEN/NOTIFY latencies across different PostgreSQL versions. Each candlestick displays:
- **Box**: Interquartile range (Q1 to Q3) showing where 50% of measurements fall
- **Black line**: Median latency
- **Whiskers**: Minimum and maximum latencies
- **Dashed line**: Linear regression based on median values

### Key Findings

Based on benchmark results across PostgreSQL versions 13-18:

1. **Base Round-Trip Latency**: With minimal connections (2-3), LISTEN/NOTIFY round-trip latency is approximately **0.08-0.10ms** across most PostgreSQL versions. This represents the fundamental overhead of the notification mechanism without connection scaling effects.

2. **Linear Scaling**: Latency increases linearly with the number of idle listening connections. For most versions (14-18), each additional connection adds approximately **4.1-4.2 microseconds** to the round-trip time.

3. **Version Comparison**:
   - **PostgreSQL 18beta1** shows the best scaling (4.087 μs/connection)
   - **PostgreSQL 14-17** cluster tightly around 4.15-4.24 μs/connection
   - **PostgreSQL 13** shows significantly worse scaling (12.663 μs/connection), approximately 3x slower

4. **Practical Impact**: 
   - At 100 connections: ~0.5ms latency (5x base latency)
   - At 500 connections: ~2.1ms latency (21x base latency)  
   - At 1000 connections: ~4.2ms latency (42x base latency)

5. **Performance Improvement**: PostgreSQL 14 introduced significant optimizations to LISTEN/NOTIFY, reducing the per-connection overhead by approximately 67% compared to PostgreSQL 13.

### Conclusions

The benchmark demonstrates that while PostgreSQL's LISTEN/NOTIFY is extremely fast with few connections (sub-millisecond), the performance degrades linearly with the number of listening connections. This is because PostgreSQL must check each listening connection when delivering notifications, even if those connections are completely idle.

For applications using LISTEN/NOTIFY:
- **Connection pooling is critical** - minimize the number of database connections
- **Consider upgrading from PostgreSQL 13** - newer versions offer 3x better scaling
- **Design for scale** - at 1000 connections, expect 40-50x slower notifications than baseline
- **Monitor connection count** - the performance impact is predictable and linear

This scaling behavior explains why many high-scale applications eventually migrate from LISTEN/NOTIFY to dedicated message queue systems when connection counts grow large.

## Requirements

- PostgreSQL command-line tools (`initdb`, `pg_ctl`, `createdb`) in PATH
- Rust 1.70 or later
- Python 3.7+ (for plotting results)
- macOS or Linux (Windows not currently supported)
- At least 8GB RAM recommended

## Installation

```bash
# Clone the repository
git clone https://github.com/joelonsql/pg-bench-listen-notify
cd pg-bench-listen-notify

# Build the project
cargo build --release
```

## Usage

### Running the Benchmark

```bash
# Run with default settings (up to 1,000 connections)
cargo run --release

# The tool will:
# 1. Create a temporary PostgreSQL instance
# 2. Configure it for high connection count
# 3. Run the benchmark
# 4. Save results to stats.csv
# 5. Clean up the temporary instance
```

### Plotting Results

```bash
# Install Python dependencies and generate plot
./plot.sh

# Or manually:
pip install -r requirements.txt
python plot_stats.py

# Custom input/output files
python plot_stats.py custom_stats.csv custom_plot.png
```

## How It Works

### Benchmark Process

1. **Setup Phase**
   - Creates a temporary PostgreSQL instance with `max_connections=2000`
   - Configures shared_buffers and other settings for high connection count
   - Increases OS file descriptor limits

2. **Measurement Phase**
   - Two threads (`thread_1` and `thread_2`) exchange LISTEN/NOTIFY messages
   - Each notification round-trip time is measured
   - After every 20 measurements (10 per thread), statistics are calculated
   - A new idle listening connection is added
   - Process continues until 1,000 idle connections

3. **Decreasing Phase**
   - After reaching 1,000 connections, removes one connection after each measurement
   - Continues until back to just the two active threads
   - Allows observation of whether latency recovers

### What Gets Measured

- **Round-trip time**: Time from sending NOTIFY to receiving the notification
- **Statistics per connection count**:
  - Minimum latency
  - Average latency
  - Maximum latency
  - Standard deviation

## Output Files

- `benchmark_results.csv` - Raw benchmark data with columns:
  - `connections`: Total number of connections
  - `min_ms`: Minimum latency in milliseconds
  - `q1_ms`: First quartile (25th percentile)
  - `median_ms`: Median latency (50th percentile)
  - `q3_ms`: Third quartile (75th percentile)
  - `max_ms`: Maximum latency in milliseconds
  - `avg_ms`: Average latency in milliseconds
  - `stddev_ms`: Standard deviation in milliseconds
  - `version`: Full PostgreSQL version string

- `candlestick_comparison.png` - Visualization showing:
  - Candlestick charts for latency distribution
  - Linear regression lines based on median values
  - Full version strings with regression formulas
  - Side-by-side comparison of all tested versions

## Technical Details

### PostgreSQL Configuration

The tool automatically configures PostgreSQL with:
- `max_connections = 2000`
- `shared_buffers = 32GB` (for 128GB RAM systems)
- `work_mem = 1MB`
- `maintenance_work_mem = 256MB`

### OS Limits

On macOS, the tool attempts to increase file descriptor limits. If you encounter "Too many open files" errors, run:

```bash
sudo launchctl limit maxfiles 65536 200000
ulimit -n 20000
```

### Implementation Details

- Uses `tokio-postgres` for async PostgreSQL connections
- Each connection runs in a separate Tokio task
- Notifications are processed using PostgreSQL's async message system
- Timing uses high-resolution `Instant::now()` measurements

## Interpreting Results

The benchmark reveals several important patterns:

### Reading the Candlestick Chart
- **Box height**: Shows consistency - smaller boxes mean more predictable performance
- **Whisker length**: Shows outliers - longer whiskers indicate occasional spikes
- **Median vs Average**: If median is much lower than average, there are occasional high outliers
- **Regression line**: Shows the scaling trend - flatter is better

### Performance Characteristics
- **Sub-millisecond baseline**: All modern PostgreSQL versions achieve ~0.1ms base latency
- **Linear degradation**: Each idle connection adds a fixed overhead (4-12 μs depending on version)
- **Version 13 anomaly**: Shows 3x worse scaling, indicating major improvements in v14
- **Excellent R² values**: 0.94-0.99 indicates highly predictable linear scaling

### Real-World Implications
For a typical application with:
- **10 connections**: Negligible impact (~0.14ms)
- **100 connections**: Noticeable but acceptable (~0.52ms)
- **500 connections**: May impact user experience (~2.2ms)
- **1000+ connections**: Consider alternative architectures (~4.3ms)

The predictable linear scaling allows capacity planning based on your latency requirements and expected connection count.

## Troubleshooting

### "Too many open files" Error
Increase your system's file descriptor limit (see OS Limits section).

### "max_connections" Not Taking Effect
The tool uses `ALTER SYSTEM` and restarts PostgreSQL. Check PostgreSQL logs in the temporary directory if issues persist.

### Connection Failures
Ensure PostgreSQL tools are in your PATH and you have sufficient system resources.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details