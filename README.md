# pg-bench-listen-notify

A benchmarking tool that measures how PostgreSQL LISTEN/NOTIFY performance scales with the number of idle listening connections.

## Key Results

![Benchmark Results](candlestick_comparison.png)

### Understanding LISTEN/NOTIFY Latency

**Base latency (2-3 connections):** PostgreSQL's LISTEN/NOTIFY achieves remarkably low round-trip latencies of **0.08-0.10 ms** when only the essential connections are present. This sub-millisecond performance makes it an attractive choice for real-time applications.

**Impact of idle connections:** Each additional idle listening connection adds a consistent overhead to every notification. Our measurements show:
- **PostgreSQL 14-18**: ~4.2 µs per connection
- **PostgreSQL 13**: ~12.9 µs per connection (3x slower)

This means with 1,000 connections, a notification that originally took 0.08ms will take:
- **4.2ms** on PostgreSQL 14+ (50x slower)
- **12.9ms** on PostgreSQL 13 (160x slower)

### PostgreSQL 14's LISTEN/NOTIFY Performance Breakthrough

PostgreSQL 13 exhibits significantly noisier measurements (R²=0.953) compared to newer versions (R²=0.998-0.999), suggesting less predictable performance. PostgreSQL 14 introduced critical optimizations that reduced per-connection overhead by 67%.

The key improvement likely came from **eliminating synchronous fsync calls** in the notification queue ([commit dee663f](https://github.com/postgres/postgres/commit/dee663f7843)). Previously, PostgreSQL would fsync after writing each notification queue page, causing I/O stalls that scaled poorly with many connections. PostgreSQL 14 defers these writes to the next checkpoint, dramatically reducing overhead.

Additional optimizations include:
- **Streamlined signal handling** ([commit 0eff10a](https://github.com/postgres/postgres/commit/0eff10a0084)) - moved NOTIFY signals to transaction commit, eliminating redundant operations
- **Fixed race conditions** ([commit 9c83b54](https://github.com/postgres/postgres/commit/9c83b54a9cc)) - prevented queue truncation issues under concurrent load
- **Prevented SLRU lock contention** ([commit 566372b](https://github.com/postgres/postgres/commit/566372b3d64)) - avoided concurrent SimpleLruTruncate operations

These improvements have been maintained through versions 15, 16, 17, and 18beta1.

### Practical Implications

| Connections | Latency (v14+) | Latency (v13) | Impact |
|------------|----------------|---------------|---------|
| 10         | ~0.12ms       | ~0.21ms      | Negligible |
| 100        | ~0.50ms       | ~1.37ms      | Noticeable |
| 500        | ~2.19ms       | ~6.54ms      | User-visible |
| 1,000      | ~4.29ms       | ~13.00ms     | Problematic |

**Key takeaway:** LISTEN/NOTIFY performance degrades linearly with connection count because PostgreSQL must check every listening connection when delivering a notification, even if those connections are completely idle.

## How the Benchmark Works

The tool creates a controlled test environment:

1. **Ping-pong threads**: Two connections exchange NOTIFY messages continuously, measuring round-trip time
2. **Idle connections**: Progressively adds connections that LISTEN but never send messages
3. **Statistical analysis**: Records latency distribution (min, Q1, median, Q3, max) every 20 round-trips
4. **Outlier filtering**: Uses IQR method to remove measurement noise
5. **Regression analysis**: Computes linear scaling factor from 100-1000 connection range

## Quick Start

```bash
# Run full benchmark for all PostgreSQL versions
./benchmark_all_versions.sh

# Or regenerate plot from existing data
./replot.sh
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
- `candlestick_comparison.png` - Visual comparison across PostgreSQL versions

## Technical Implementation

The benchmark:
1. Sets up isolated PostgreSQL instances with `max_connections=2000`
2. Uses two threads exchanging NOTIFY messages to measure round-trip time
3. Progressively adds idle LISTEN connections
4. Filters outliers using IQR method
5. Computes linear regression on 100-1000 connection range for stable results

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
