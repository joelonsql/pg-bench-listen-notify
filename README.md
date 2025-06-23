# pg-bench-listen-notify

A benchmarking tool that measures how PostgreSQL LISTEN/NOTIFY performance scales with the number of idle listening connections.

> **⚠️ IMPORTANT DISCLAIMER**
> 
> The `optimize_listen_notify` patch referenced in this benchmark has **not been carefully reviewed** by experts in PostgreSQL's async.c subsystem. While the benchmark results show promising near-O(1) performance characteristics, these results might be misleading if the optimization approach has unforeseen issues or doesn't work correctly in practice. The patch must undergo thorough review and testing before any conclusions are drawn about its viability.

## Key Results

### Overall Comparison
![Benchmark Results](candlestick_comparison.png)

The chart shows three panels with different connection ranges to provide clear visualization:
- **0-10 connections**: All data points shown for detailed view of low connection counts
- **10-100 connections**: Every 10th connection shown (10, 20, 30, ..., 100)
- **100-1000 connections**: Every 100th connection shown (100, 200, 300, ..., 1000) with linear regression analysis

### Scaling Analysis: O(N) vs Near-O(1) Performance

Our analysis reveals that all PostgreSQL versions from 9.6 through master exhibit **consistent O(N) scaling**, where N is the number of listening connections. The optimization patch achieves **near-O(1) performance** with minimal scaling overhead.

| Version | Complexity | Latency Formula |
|---------|------------|-----------------|
| PostgreSQL 9.6-13 | O(N) | ~0.4-0.7 + 12.4-13.3×10⁻³ × N ms |
| PostgreSQL 14-17 | O(N) | ~0.3-0.4 + 13.0-13.1×10⁻³ × N ms |
| master | O(N) | 0.354 + 13.174×10⁻³ × N ms |
| optimize_listen_notify | **~O(1)** | **0.570 + 0.108×10⁻³ × N ms** |

### Understanding LISTEN/NOTIFY Latency

**Base latency (2-3 connections):** PostgreSQL's LISTEN/NOTIFY achieves remarkably low round-trip latencies of **0.4-0.7 ms** when only the essential connections are present. This sub-millisecond performance makes it an attractive choice for real-time applications.

**Impact of idle connections:** All PostgreSQL versions exhibit similar O(N) scaling:
- **PostgreSQL 9.6-master**: Each connection adds ~12.4-13.3 µs to every notification
- **Optimization patch**: Each connection adds only ~0.11 µs (near constant time)

This means with 1,000 connections, a notification that originally took 0.4-0.7ms will take:
- **~13-14ms** on any PostgreSQL version (problematic for real-time applications)
- **~0.68ms** with the optimization patch (maintains sub-millisecond performance)

### Consistent O(N) Performance Across All Versions

Remarkably, all PostgreSQL versions from 9.6 through master show nearly identical O(N) scaling characteristics:
- Slopes range from 12.466 to 13.430 μs/connection
- R² values > 0.85 indicate strong linear relationships
- No significant performance improvements between versions

This consistency suggests that the core LISTEN/NOTIFY implementation has remained largely unchanged across these versions, with the O(N) scaling being a fundamental characteristic of the current architecture.

### The Optimization Patch: Near-O(1) Performance

The `optimize_listen_notify` patch achieves a dramatic improvement:
- **Slope**: 0.108 μs/connection (120x improvement over standard PostgreSQL)
- **R² value**: 0.0904 (connection count has minimal impact on latency)
- **Mean latency**: 0.625 ms (remains nearly constant regardless of connection count)

### Practical Implications

**Current PostgreSQL vs Optimization Patch:**

| Connections | Current PG Latency | Patch Latency | Improvement | Impact on Current | Impact on Patch |
|-------------|-------------------|---------------|-------------|-------------------|-----------------|
| 10          | ~0.5ms           | ~0.57ms       | -14%        | Negligible        | Negligible      |
| 100         | ~1.7ms           | ~0.58ms       | 66%         | Noticeable        | Negligible      |
| 500         | ~6.9ms           | ~0.62ms       | 91%         | User-visible      | Negligible      |
| 1,000       | ~13.5ms          | ~0.68ms       | 95%         | Problematic       | Negligible      |

**Key takeaway:** While current PostgreSQL versions exhibit consistent O(N) scaling across all versions, the optimization patch achieves near-O(1) performance, maintaining sub-millisecond latency even with thousands of connections.

## Detailed Scaling Analysis Output

Here's the complete output from `analyze_scaling.py` showing the mathematical analysis of each PostgreSQL version using all data points:

```
PostgreSQL LISTEN/NOTIFY Scaling Analysis (all connections)
================================================================================

Version: REL9_6_24
  Linear regression: 0.564 + 13.174×10⁻³ × N ms
  Mean latency: 7.191 ms ± 4.043 ms
  Coefficient of variation: 56.2%
  R² value: 0.8847
  Slope: 13.174 μs/connection
  Intercept: 0.564 ms
  Data points: 2000

Version: REL_10_23
  Linear regression: 0.577 + 13.171×10⁻³ × N ms
  Mean latency: 7.202 ms ± 3.979 ms
  Coefficient of variation: 55.3%
  R² value: 0.9130
  Slope: 13.171 μs/connection
  Intercept: 0.577 ms
  Data points: 2000

Version: REL_11_22
  Linear regression: 0.663 + 12.925×10⁻³ × N ms
  Mean latency: 7.165 ms ± 3.875 ms
  Coefficient of variation: 54.1%
  R² value: 0.9272
  Slope: 12.925 μs/connection
  Intercept: 0.663 ms
  Data points: 2000

Version: REL_12_22
  Linear regression: 0.523 + 13.328×10⁻³ × N ms
  Mean latency: 7.227 ms ± 4.062 ms
  Coefficient of variation: 56.2%
  R² value: 0.8970
  Slope: 13.328 μs/connection
  Intercept: 0.523 ms
  Data points: 2000

Version: REL_13_21
  Linear regression: 0.438 + 12.408×10⁻³ × N ms
  Mean latency: 6.679 ms ± 3.603 ms
  Coefficient of variation: 54.0%
  R² value: 0.9882
  Slope: 12.408 μs/connection
  Intercept: 0.438 ms
  Data points: 2000

Version: REL_14_18
  Linear regression: 0.351 + 13.046×10⁻³ × N ms
  Mean latency: 6.913 ms ± 3.791 ms
  Coefficient of variation: 54.8%
  R² value: 0.9871
  Slope: 13.046 μs/connection
  Intercept: 0.351 ms
  Data points: 2000

Version: REL_15_13
  Linear regression: 0.369 + 12.971×10⁻³ × N ms
  Mean latency: 6.893 ms ± 3.768 ms
  Coefficient of variation: 54.7%
  R² value: 0.9877
  Slope: 12.971 μs/connection
  Intercept: 0.369 ms
  Data points: 2000

Version: REL_16_9
  Linear regression: 0.324 + 13.038×10⁻³ × N ms
  Mean latency: 6.882 ms ± 3.787 ms
  Coefficient of variation: 55.0%
  R² value: 0.9876
  Slope: 13.038 μs/connection
  Intercept: 0.324 ms
  Data points: 2000

Version: REL_17_4
  Linear regression: 0.364 + 13.042×10⁻³ × N ms
  Mean latency: 6.925 ms ± 3.788 ms
  Coefficient of variation: 54.7%
  R² value: 0.9878
  Slope: 13.042 μs/connection
  Intercept: 0.364 ms
  Data points: 2000

Version: master
  Linear regression: 0.354 + 13.174×10⁻³ × N ms
  Mean latency: 6.981 ms ± 3.826 ms
  Coefficient of variation: 54.8%
  R² value: 0.9877
  Slope: 13.174 μs/connection
  Intercept: 0.354 ms
  Data points: 2000

Version: optimize_listen_notify
  Linear regression: 0.570 + 0.108×10⁻³ × N ms
  Mean latency: 0.625 ms ± 0.104 ms
  Coefficient of variation: 16.6%
  R² value: 0.0904
  Slope: 0.108 μs/connection
  Intercept: 0.570 ms
  Data points: 2000


Summary Table
----------------------------------------------------------------------------------------------------
Version                             Slope (μs/conn)    Intercept (ms)  R²         Formula
----------------------------------------------------------------------------------------------------
REL9_6_24                                   13.174           0.564     0.8847     0.564 + 13.174×10⁻³ × N ms
REL_10_23                                   13.171           0.577     0.9130     0.577 + 13.171×10⁻³ × N ms
REL_11_22                                   12.925           0.663     0.9272     0.663 + 12.925×10⁻³ × N ms
REL_12_22                                   13.328           0.523     0.8970     0.523 + 13.328×10⁻³ × N ms
REL_13_21                                   12.408           0.438     0.9882     0.438 + 12.408×10⁻³ × N ms
REL_14_18                                   13.046           0.351     0.9871     0.351 + 13.046×10⁻³ × N ms
REL_15_13                                   12.971           0.369     0.9877     0.369 + 12.971×10⁻³ × N ms
REL_16_9                                    13.038           0.324     0.9876     0.324 + 13.038×10⁻³ × N ms
REL_17_4                                    13.042           0.364     0.9878     0.364 + 13.042×10⁻³ × N ms
master                                      13.174           0.354     0.9877     0.354 + 13.174×10⁻³ × N ms
optimize_listen_notify                       0.108           0.570     0.0904     0.570 + 0.108×10⁻³ × N ms
----------------------------------------------------------------------------------------------------
```

### Key Observations from the Analysis

- **Consistent O(N) scaling**: All PostgreSQL versions show remarkably similar slopes (12.4-13.3 μs/connection)
- **R² values**: Most versions show strong linear fit (R² > 0.88), with v13-master showing excellent fit (R² > 0.98)
- **Low R² for patch**: The optimization patch's R² of 0.0904 indicates that connection count has minimal impact on latency
- **Slope reduction**: The optimization patch reduces the per-connection overhead by 99.2% (from ~13 μs to ~0.11 μs)

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
- `candlestick_comparison-1.png` through `candlestick_comparison-10.png` - Version pair comparisons

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
