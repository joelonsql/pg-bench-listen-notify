# pg-bench-listen-notify

A benchmarking tool that measures PostgreSQL LISTEN/NOTIFY performance by comparing Transactions Per Second (TPS) between standard PostgreSQL and the optimized version across different connection counts and `notify_multicast_threshold` settings.

> **⚠️ IMPORTANT DISCLAIMER**
>
> The patches referenced in this benchmark have **not been carefully reviewed** yet by experts in PostgreSQL's async.c subsystem. While the benchmark results show promising performance characteristics, these results might be misleading if the optimization approach has unforeseen issues or doesn't work correctly in practice. The patches must undergo thorough review and testing before any conclusions are drawn about their viability.
>
> **Patches:**
> - [patch-v4: Improve NOTIFY scalability with multicast signaling](https://github.com/joelonsql/postgresql/commit/cf8444ff7a5bf6644c1b4ae2d70b44378703504a)

## Key Results

### TPS Performance Comparison
![TPS Performance](plot-v4.png)

The log-log scale chart shows TPS (Transactions Per Second) performance across different connection counts:
- **X-axis**: Number of extra listening connections (0, 10, 100, 1000) - log scale
- **Y-axis**: Transactions per second - log scale  
- **Data points**: Maximum TPS values from 3 runs per configuration
- **Configurations tested**:
  - master (baseline)
  - patch-v4 with `notify_multicast_threshold=1`
  - patch-v4 with `notify_multicast_threshold=8`
  - patch-v4 with `notify_multicast_threshold=16`

The `notify_multicast_threshold` parameter controls when PostgreSQL switches from unicast to multicast signaling for NOTIFY operations. Lower values trigger multicast behavior with fewer listeners, while higher values require more listeners before switching to multicast.

### pgbench Performance Results

Additional performance analysis using pgbench shows detailed comparisons across different workload patterns and threshold values:

![Performance Overview - Connections Equal Jobs](performance_overview_connections_equal_jobs-v4.png)

![Performance Overview - Fixed Connections](performance_overview_fixed_connections-v4.png)

For detailed analysis of all test scenarios and complete performance data, see [performance_overview-v4.md](performance_overview-v4.md).

## How the Benchmark Works

The benchmark creates a controlled environment to measure LISTEN/NOTIFY performance:

1. **Setup**: Creates isolated PostgreSQL instances with `max_connections=2000`
2. **Ping-pong measurement**: Two threads exchange NOTIFY messages continuously
3. **Idle listeners**: Adds the specified number of idle LISTEN connections
4. **TPS calculation**: Measures round-trips over 10 seconds after 1-second warm-up
5. **Averaging**: Takes 3 measurements per connection count for stability
6. **Threshold testing**: For patch-v4, tests multiple `notify_multicast_threshold` values

### Test Configuration

**Connection counts tested:** 0, 10, 100, 1000 extra listeners  
**Threshold values tested:** 1, 8, 16 (patch-v4 only)  
**Measurements per configuration:** 3 runs  
**Measurement duration:** 10 seconds per run  
**Warm-up period:** 1 second before each measurement

## Setup

The benchmark script expects PostgreSQL installations in specific locations in your home directory:

```bash
# Expected directory structure:
~/pg-master/bin/                    # Baseline PostgreSQL master branch
~/pg-patch-v4/bin/                  # Patched version with multicast support
```

## Quick Start

```bash
# Run full benchmark for all versions and threshold values
./benchmark_all_versions.sh

# Generate plot from existing results
./plot.sh

# Run pgbench performance tests with different thresholds
./pgbench.sh

# Generate pgbench performance charts
./plot_pgbench.sh
```

## License

MIT License - See LICENSE file
