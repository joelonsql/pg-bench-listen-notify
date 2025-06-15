# pg-bench-listen-notify

A benchmarking tool that measures how PostgreSQL LISTEN/NOTIFY performance scales with the number of idle listening connections.

## Key Results

### Overall Comparison
![Benchmark Results](candlestick_comparison.png)

### Scaling Analysis: O(N) vs O(1) Behavior

Our analysis reveals that PostgreSQL LISTEN/NOTIFY exhibits **O(N) scaling** for all standard versions, where N is the number of listening connections. Only the optimization patch achieves true **O(1) constant-time** performance.

| Version | Complexity | Latency Formula (N ≥ 100) |
|---------|------------|----------------------------|
| PostgreSQL 13.21 | O(N) | -0.034 + 12.419×10⁻³ × N ms |
| PostgreSQL 14-17 | O(N) | ~0.08 + 4.2×10⁻³ × N ms |
| HEAD | O(N) | 0.087 + 4.159×10⁻³ × N ms |
| [jj/notify-single-listener-opt](https://github.com/joelonsql/postgresql/commit/4adfad94cd22b17fb3809d46b0d5a04a64be4884) | **O(1)** | **≈ 0.102 ms (constant)** |

### Understanding LISTEN/NOTIFY Latency

**Base latency (2-3 connections):** PostgreSQL's LISTEN/NOTIFY achieves remarkably low round-trip latencies of **0.08-0.10 ms** when only the essential connections are present. This sub-millisecond performance makes it an attractive choice for real-time applications.

**Impact of idle connections:** For standard PostgreSQL versions with O(N) scaling:
- **PostgreSQL 14-HEAD**: Each connection adds ~4.2 µs to every notification
- **PostgreSQL 13**: Each connection adds ~12.4 µs (3x worse)
- **Optimization patch**: Latency remains constant at ~0.1 ms regardless of connections

This means with 1,000 connections, a notification that originally took 0.08ms will take:
- **4.3ms** on PostgreSQL 14+ (50x slower)
- **12.4ms** on PostgreSQL 13 (155x slower)
- **0.1ms** with the optimization patch (no degradation)

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

#### HEAD → Optimization Patch: Achieving O(1) Performance
![HEAD vs patch](candlestick_comparison-6.png)

The optimization patch eliminates the O(N) scaling entirely, achieving constant-time notifications regardless of listener count.

### Practical Implications

| Connections | Latency (v14+) | Latency (v13) | Impact |
|------------|----------------|---------------|---------|
| 10         | ~0.12ms       | ~0.21ms      | Negligible |
| 100        | ~0.50ms       | ~1.37ms      | Noticeable |
| 500        | ~2.19ms       | ~6.54ms      | User-visible |
| 1,000      | ~4.29ms       | ~13.00ms     | Problematic |

**Key takeaway:** LISTEN/NOTIFY performance degrades linearly with connection count because PostgreSQL must check every listening connection when delivering a notification, even if those connections are completely idle.

## Detailed Scaling Analysis Output

Here's the complete output from `analyze_scaling.py` showing the mathematical analysis of each PostgreSQL version:

```
PostgreSQL LISTEN/NOTIFY Scaling Analysis (connections >= 100)
================================================================================

Version: PostgreSQL 13.21 (Postgres.app) on x86_64-apple-darwin19.6.0, compiled by Apple clang version 11.0.3 (clang-1103.0.32.62), 64-bit
  Complexity: O(N)
  Latency formula: -0.034 + 12.419×10⁻³ × N ms
  Mean latency: 6.812 ms ± 3.334 ms
  Coefficient of variation: 48.9%
  R² value: 0.9439
  Slope: 12.419 μs/connection
  Data points: 1807

Version: PostgreSQL 14.18 (Postgres.app) on aarch64-apple-darwin20.6.0, compiled by Apple clang version 12.0.5 (clang-1205.0.22.9), 64-bit
  Complexity: O(N)
  Latency formula: 0.079 + 4.250×10⁻³ × N ms
  Mean latency: 2.421 ms ± 1.110 ms
  Coefficient of variation: 45.8%
  R² value: 0.9975
  Slope: 4.250 μs/connection
  Data points: 1807

Version: PostgreSQL 15.13 (Postgres.app) on aarch64-apple-darwin21.6.0, compiled by Apple clang version 14.0.0 (clang-1400.0.29.102), 64-bit
  Complexity: O(N)
  Latency formula: 0.086 + 4.200×10⁻³ × N ms
  Mean latency: 2.402 ms ± 1.097 ms
  Coefficient of variation: 45.7%
  R² value: 0.9974
  Slope: 4.200 μs/connection
  Data points: 1807

Version: PostgreSQL 16.9 (Postgres.app) on aarch64-apple-darwin21.6.0, compiled by Apple clang version 14.0.0 (clang-1400.0.29.102), 64-bit
  Complexity: O(N)
  Latency formula: 0.079 + 4.245×10⁻³ × N ms
  Mean latency: 2.420 ms ± 1.109 ms
  Coefficient of variation: 45.8%
  R² value: 0.9975
  Slope: 4.245 μs/connection
  Data points: 1807

Version: PostgreSQL 17.5 (Postgres.app) on aarch64-apple-darwin23.6.0, compiled by Apple clang version 15.0.0 (clang-1500.3.9.4), 64-bit
  Complexity: O(N)
  Latency formula: 0.078 + 4.232×10⁻³ × N ms
  Mean latency: 2.410 ms ± 1.104 ms
  Coefficient of variation: 45.8%
  R² value: 0.9989
  Slope: 4.232 μs/connection
  Data points: 1807

Version: HEAD
  Complexity: O(N)
  Latency formula: 0.087 + 4.159×10⁻³ × N ms
  Mean latency: 2.380 ms ± 1.086 ms
  Coefficient of variation: 45.6%
  R² value: 0.9980
  Slope: 4.159 μs/connection
  Data points: 1807

Version: jj/notify-single-listener-opt
  Complexity: O(1)
  Latency formula: ≈ 0.102 ms (constant)
  Mean latency: 0.102 ms ± 0.016 ms
  Coefficient of variation: 16.0%
  R² value: 0.0078
  Slope: 0.006 μs/connection
  Data points: 1807


Summary Table
--------------------------------------------------------------------------------
Version                             Complexity Formula
--------------------------------------------------------------------------------
PostgreSQL 13.21                    O(N)       -0.034 + 12.419×10⁻³ × N ms
PostgreSQL 14.18                    O(N)       0.079 + 4.250×10⁻³ × N ms
PostgreSQL 15.13                    O(N)       0.086 + 4.200×10⁻³ × N ms
PostgreSQL 16.9                     O(N)       0.079 + 4.245×10⁻³ × N ms
PostgreSQL 17.5                     O(N)       0.078 + 4.232×10⁻³ × N ms
HEAD                                O(N)       0.087 + 4.159×10⁻³ × N ms
jj/notify-single-listener-opt       O(1)       ≈ 0.102 ms (constant)
--------------------------------------------------------------------------------

O(1) scaling (constant time): 1 versions
O(N) scaling (linear with connections): 6 versions

O(1) versions (excellent scaling):
  - jj/notify-single-listener-opt: 0.102 ms average

O(N) versions (latency increases with connections):
  - PostgreSQL 13.21: 12.4 μs per connection
  - PostgreSQL 14.18: 4.2 μs per connection
  - PostgreSQL 15.13: 4.2 μs per connection
  - PostgreSQL 16.9: 4.2 μs per connection
  - PostgreSQL 17.5: 4.2 μs per connection
  - HEAD: 4.2 μs per connection
```

### Key Observations from the Analysis

- **R² values**: PostgreSQL 14+ shows excellent linear fit (R² > 0.997), while v13 has more variance (R² = 0.944)
- **Coefficient of variation**: The optimization patch has much lower variance (16%) compared to standard versions (45-49%)
- **Slope significance**: The near-zero slope (0.006 μs/connection) for the optimization patch confirms true O(1) behavior

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

The candlestick chart visualizes latency distribution:
- **Box**: Interquartile range (Q1-Q3) - where 50% of measurements fall
- **Line in box**: Median latency
- **Whiskers**: Minimum and maximum values
- **Dashed line**: Linear regression trend (computed from 100-1000 connections)

Smaller boxes = more consistent performance. The regression line slope indicates scaling efficiency.

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
