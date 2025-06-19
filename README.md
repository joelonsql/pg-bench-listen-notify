# pg-bench-listen-notify

A benchmarking tool that measures how PostgreSQL LISTEN/NOTIFY performance scales with the number of idle listening connections.

> **⚠️ IMPORTANT DISCLAIMER**
> 
> The `jj/notify-single-listener-opt` patch referenced in this benchmark has **not been carefully reviewed** by experts in PostgreSQL's async.c subsystem. While the benchmark results show promising O(1) performance characteristics, these results might be misleading if the optimization approach has unforeseen issues or doesn't work correctly in practice. The patch must undergo thorough review and testing before any conclusions are drawn about its viability.

## Key Results

### Overall Comparison
![Benchmark Results](candlestick_comparison.png)

The chart shows three panels with different connection ranges to provide clear visualization:
- **0-10 connections**: All data points shown for detailed view of low connection counts
- **10-100 connections**: Every 10th connection shown (10, 20, 30, ..., 100)
- **100-1000 connections**: Every 100th connection shown (100, 200, 300, ..., 1000) with linear regression analysis

### Scaling Analysis: O(N) Performance Characteristics

Our analysis reveals that PostgreSQL LISTEN/NOTIFY exhibits **O(N) scaling** for all versions, where N is the number of listening connections. The optimization patch significantly reduces the slope of this scaling but maintains O(N) behavior due to periodic wake-ups for lagging backends.

| Version | Complexity | Latency Formula (N ≥ 100) |
|---------|------------|----------------------------|
| PostgreSQL 13.21 | O(N) | -0.442 + 13.074×10⁻³ × N ms |
| PostgreSQL 14-17 | O(N) | ~0.08 + 4.2×10⁻³ × N ms |
| HEAD | O(N) | 0.079 + 4.218×10⁻³ × N ms |
| [jj/notify-single-listener-opt](https://github.com/joelonsql/postgresql/commit/97a6af9d683422f52d81f951321b00fcf1e26122) | **O(N)** | **0.072 + 0.196×10⁻³ × N ms** |

### Understanding LISTEN/NOTIFY Latency

**Base latency (2-3 connections):** PostgreSQL's LISTEN/NOTIFY achieves remarkably low round-trip latencies of **0.08-0.10 ms** when only the essential connections are present. This sub-millisecond performance makes it an attractive choice for real-time applications.

**Impact of idle connections:** All PostgreSQL versions exhibit O(N) scaling:
- **PostgreSQL 13**: Each connection adds ~13.1 µs to every notification
- **PostgreSQL 14-HEAD**: Each connection adds ~4.2 µs (67% improvement over v13)
- **Optimization patch**: Each connection adds only ~0.2 µs (95% improvement over HEAD)

This means with 1,000 connections, a notification that originally took 0.08ms will take:
- **12.6ms** on PostgreSQL 13 (unacceptable for real-time applications)
- **4.3ms** on PostgreSQL 14+ (3x faster than v13, but still problematic)
- **0.27ms** with the optimization patch (16x faster than HEAD, sub-millisecond maintained)

### PostgreSQL 14's LISTEN/NOTIFY Performance Breakthrough

PostgreSQL 13 exhibits significantly noisier measurements (R²=0.953) compared to newer versions (R²=0.998-0.999), suggesting less predictable performance. PostgreSQL 14 introduced critical optimizations that reduced per-connection overhead by 67%.

The key improvement likely came from **eliminating synchronous fsync calls** in the notification queue ([commit dee663f](https://github.com/postgres/postgres/commit/dee663f7843)). Previously, PostgreSQL would fsync after writing each notification queue page, causing I/O stalls that scaled poorly with many connections. PostgreSQL 14 defers these writes to the next checkpoint, dramatically reducing overhead.

Additional optimizations include:
- **Streamlined signal handling** ([commit 0eff10a](https://github.com/postgres/postgres/commit/0eff10a0084)) - moved NOTIFY signals to transaction commit, eliminating redundant operations
- **Fixed race conditions** ([commit 9c83b54](https://github.com/postgres/postgres/commit/9c83b54a9cc)) - prevented queue truncation issues under concurrent load
- **Prevented SLRU lock contention** ([commit 566372b](https://github.com/postgres/postgres/commit/566372b3d64)) - avoided concurrent SimpleLruTruncate operations

These improvements have been maintained through versions 15, 16, 17, and HEAD.

### Version-by-Version Performance Evolution

#### PostgreSQL 13 → 14: The Major Performance Breakthrough
![13 vs 14](candlestick_comparison-1.png)

The most dramatic improvement in LISTEN/NOTIFY history: 67% reduction in per-connection overhead.

#### PostgreSQL 14 → 15: Stable Performance
![14 vs 15](candlestick_comparison-2.png)

Performance characteristics remain consistent with minor improvements.

#### PostgreSQL 15 → 16: Continued Stability
![15 vs 16](candlestick_comparison-3.png)

The O(N) scaling pattern continues with ~4.2 µs per connection.

#### PostgreSQL 16 → 17: Maintained Efficiency
![16 vs 17](candlestick_comparison-4.png)

No regression in performance; the improvements from v14 are preserved.

#### PostgreSQL 17 → HEAD: Current Development
![17 vs HEAD](candlestick_comparison-5.png)

HEAD maintains the same O(N) scaling as stable versions.

#### HEAD → Optimization Patch: 95% Reduction in Per-Connection Overhead
![HEAD vs patch](candlestick_comparison-6.png)

The optimization patch dramatically reduces the O(N) scaling coefficient by 95%, from ~4.2 µs per connection to ~0.2 µs per connection. While still technically O(N) due to periodic wake-ups for lagging backends, the practical performance improvement is substantial.

### Practical Implications

**HEAD vs Optimization Patch:**

| Connections | HEAD Latency | Patch Latency | Improvement | Impact on HEAD | Impact on Patch |
|------------|--------------|---------------|-------------|----------------|-----------------|
| 10         | ~0.12ms     | ~0.07ms      | 42%         | Negligible     | Negligible      |
| 100        | ~0.50ms     | ~0.09ms      | 82%         | Noticeable     | Negligible      |
| 500        | ~2.19ms     | ~0.17ms      | 92%         | User-visible   | Negligible      |
| 1,000      | ~4.30ms     | ~0.27ms      | 94%         | Problematic    | Barely noticeable |

**Key takeaway:** While both HEAD and the patch exhibit O(N) scaling, the optimization reduces per-connection overhead by 95% (from ~4.2 μs to ~0.2 μs). The existing laggard wake-up mechanism ensures correctness by signaling any backend that falls behind by more than 32kB, now properly including backends in the same database.

## Detailed Scaling Analysis Output

Here's the complete output from `analyze_scaling.py` showing the mathematical analysis of each PostgreSQL version:

```
PostgreSQL LISTEN/NOTIFY Scaling Analysis (connections >= 100)
================================================================================

Version: PostgreSQL 13.21 (Postgres.app) on x86_64-apple-darwin19.6.0, compiled by Apple clang version 11.0.3 (clang-1103.0.32.62), 64-bit
  Linear regression: -0.442 + 13.074×10⁻³ × N ms
  Mean latency: 6.765 ms ± 3.514 ms
  Coefficient of variation: 51.9%
  R² value: 0.9418
  Slope: 13.074 μs/connection
  Intercept: -0.442 ms
  Data points: 1807

Version: PostgreSQL 14.18 (Postgres.app) on aarch64-apple-darwin20.6.0, compiled by Apple clang version 12.0.5 (clang-1205.0.22.9), 64-bit
  Linear regression: 0.077 + 4.264×10⁻³ × N ms
  Mean latency: 2.428 ms ± 1.113 ms
  Coefficient of variation: 45.9%
  R² value: 0.9977
  Slope: 4.264 μs/connection
  Intercept: 0.077 ms
  Data points: 1807

Version: PostgreSQL 15.13 (Postgres.app) on aarch64-apple-darwin21.6.0, compiled by Apple clang version 14.0.0 (clang-1400.0.29.102), 64-bit
  Linear regression: 0.081 + 4.235×10⁻³ × N ms
  Mean latency: 2.415 ms ± 1.106 ms
  Coefficient of variation: 45.8%
  R² value: 0.9978
  Slope: 4.235 μs/connection
  Intercept: 0.081 ms
  Data points: 1807

Version: PostgreSQL 16.9 (Postgres.app) on aarch64-apple-darwin21.6.0, compiled by Apple clang version 14.0.0 (clang-1400.0.29.102), 64-bit
  Linear regression: 0.079 + 4.238×10⁻³ × N ms
  Mean latency: 2.415 ms ± 1.106 ms
  Coefficient of variation: 45.8%
  R² value: 0.9982
  Slope: 4.238 μs/connection
  Intercept: 0.079 ms
  Data points: 1807

Version: PostgreSQL 17.5 (Postgres.app) on aarch64-apple-darwin23.6.0, compiled by Apple clang version 15.0.0 (clang-1500.3.9.4), 64-bit
  Linear regression: 0.077 + 4.256×10⁻³ × N ms
  Mean latency: 2.423 ms ± 1.111 ms
  Coefficient of variation: 45.9%
  R² value: 0.9983
  Slope: 4.256 μs/connection
  Intercept: 0.077 ms
  Data points: 1807

Version: HEAD
  Linear regression: 0.079 + 4.218×10⁻³ × N ms
  Mean latency: 2.405 ms ± 1.101 ms
  Coefficient of variation: 45.8%
  R² value: 0.9981
  Slope: 4.218 μs/connection
  Intercept: 0.079 ms
  Data points: 1807

Version: jj/notify-single-listener-opt
  Linear regression: 0.072 + 0.196×10⁻³ × N ms
  Mean latency: 0.180 ms ± 0.110 ms
  Coefficient of variation: 61.1%
  R² value: 0.2163
  Slope: 0.196 μs/connection
  Intercept: 0.072 ms
  Data points: 1807


Summary Table
----------------------------------------------------------------------------------------------------
Version                             Slope (μs/conn)    Intercept (ms)  R²         Formula
----------------------------------------------------------------------------------------------------
PostgreSQL 13.21                            13.074          -0.442     0.9418     -0.442 + 13.074×10⁻³ × N ms
PostgreSQL 14.18                             4.264           0.077     0.9977     0.077 + 4.264×10⁻³ × N ms
PostgreSQL 15.13                             4.235           0.081     0.9978     0.081 + 4.235×10⁻³ × N ms
PostgreSQL 16.9                              4.238           0.079     0.9982     0.079 + 4.238×10⁻³ × N ms
PostgreSQL 17.5                              4.256           0.077     0.9983     0.077 + 4.256×10⁻³ × N ms
HEAD                                         4.218           0.079     0.9981     0.079 + 4.218×10⁻³ × N ms
jj/notify-single-listener-opt                0.196           0.072     0.2163     0.072 + 0.196×10⁻³ × N ms
----------------------------------------------------------------------------------------------------
```

### Key Observations from the Analysis

- **R² values**: PostgreSQL 14+ shows excellent linear fit (R² > 0.997), while v13 has more variance (R² = 0.942)
- **Low R² for patch (0.216)**: The optimization patch's low R² indicates that connection count explains only 22% of latency variance, suggesting near-constant performance with small periodic variations from the existing wake-up mechanism
- **Slope reduction**: The optimization patch reduces the per-connection overhead from ~4.2 μs to ~0.2 μs, a 95% improvement while maintaining O(N) correctness through the existing laggard wake-up mechanism (now fixed to include all databases)

## How the Benchmark Works

The tool creates a controlled test environment:

1. **Ping-pong threads**: Two connections exchange NOTIFY messages continuously, measuring round-trip time
2. **Idle connections**: Progressively adds connections that LISTEN but never send messages
3. **Statistical analysis**: Records latency distribution (min, Q1, median, Q3, max)
   - 0-100 connections: Every 200 round-trips (more samples for stable base measurements)
   - 100+ connections: Every 20 round-trips (faster data collection)
4. **Outlier filtering**: Uses IQR method to remove measurement noise
5. **Regression analysis**: Computes linear scaling factor from 100-1000 connection range

## Quick Start

```bash
# Run full benchmark for all PostgreSQL versions
./benchmark_all_versions.sh

# Or regenerate plot from existing data
./replot.sh

# Run with custom increment (adds 10 connections per measurement)
cargo run --release -- /path/to/pg/bin output.csv --increment 10

# Analyze scaling behavior (O(N) vs O(1))
python3 analyze_scaling.py benchmark_results.csv
```

### Requirements

- PostgreSQL installations (the script will look for Postgres.app versions)
- Rust 1.70+
- Python 3.7+
- macOS or Linux
- 8GB+ RAM

## Understanding the Chart

The candlestick chart visualizes latency distribution across three panels:

**Chart Elements**:
- **Box**: Interquartile range (Q1-Q3) - where 50% of measurements fall
- **Line in box**: Median latency
- **Whiskers**: Minimum and maximum values
- **Dashed line**: Linear regression trend (shown only in the 100-1000 panel)
- **Colors**: Each PostgreSQL version uses a consistent color across all plots

**Panel Layout**:
- **Left (0-10)**: Shows every connection for fine-grained analysis of startup behavior
- **Middle (10-100)**: Shows every 10th connection to reduce visual clutter
- **Right (100-1000)**: Shows every 100th connection with regression analysis for scaling behavior

Smaller boxes indicate more consistent performance. The regression line slope in the rightmost panel indicates scaling efficiency.

## Output Files

- `benchmark_results.csv` - Raw measurements with latency percentiles
- `candlestick_comparison.png` - Overall comparison across all PostgreSQL versions
- `candlestick_comparison-1.png` through `candlestick_comparison-6.png` - Version pair comparisons

## Technical Implementation

The benchmark:
1. Sets up isolated PostgreSQL instances with `max_connections=2000`
2. Uses two threads exchanging NOTIFY messages to measure round-trip time
3. Progressively adds idle LISTEN connections (default: 1 per measurement)
4. Filters outliers using IQR method
5. Computes linear regression on 100-1000 connection range for stable results

### Command Line Options

```bash
cargo run --release -- [PG_BIN_PATH] [OUTPUT_FILE] [OPTIONS]

Arguments:
  PG_BIN_PATH   Path to PostgreSQL bin directory (optional)
  OUTPUT_FILE   Output CSV file (default: stats.csv)

Options:
  --increment N      Add N connections per measurement (default: 1)
                     Higher values speed up the benchmark but reduce granularity
  --version-name N   Use custom version name instead of querying version()
                     Useful for development builds with meaningful names
```

## Troubleshooting

**"Too many open files"**: Increase file descriptor limit:
```bash
ulimit -n 20000  # Linux/macOS
```

**PostgreSQL not found**: Ensure PostgreSQL binaries are in PATH or specify path:
```bash
cargo run --release /path/to/postgresql/bin
```

## License

MIT License - See LICENSE file
