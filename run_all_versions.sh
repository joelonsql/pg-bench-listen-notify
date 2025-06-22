#!/bin/bash

# Script to run benchmarks for all PostgreSQL versions

echo "Building the benchmark tool..."
cargo build --release

# Single output file for all versions
OUTPUT_FILE="benchmark_results.csv"

# Remove old results file if it exists
if [ -f "$OUTPUT_FILE" ]; then
    echo "Removing old results file: $OUTPUT_FILE"
    rm "$OUTPUT_FILE"
fi

# Define PostgreSQL versions from user's home directory
declare -a PG_VERSIONS=(
    "REL9_6_24"
    "REL_10_23"
    "REL_11_22"
    "REL_12_22"
    "REL_13_21"
    "REL_14_18"
    "REL_15_13"
    "REL_16_9"
    "REL_17_4"
    "master"
    "optimize_listen_notify"
)

# Run benchmark for each version
for version in "${PG_VERSIONS[@]}"; do
    pg_path="$HOME/pg-${version}/bin"

    if [ -d "$pg_path" ]; then
        echo ""
        echo "=========================================="
        echo "Testing PostgreSQL ${version} at: $pg_path"
        echo "=========================================="

        # Use the version name without "pg-" prefix
        ./target/release/pg-bench-listen-notify "$pg_path" "$OUTPUT_FILE" --version-name "${version}"

        if [ $? -eq 0 ]; then
            echo "✅ Benchmark completed for ${version}"
        else
            echo "❌ Benchmark failed for ${version}"
        fi
    else
        echo "⚠️  Skipping ${version} (directory not found: $pg_path)"
    fi
done

echo ""
echo "All benchmarks completed!"
echo "Results saved in: $OUTPUT_FILE"