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

# Define PostgreSQL versions and their configurations
declare -a CONFIGS=(
    "master:default"
    "patch-v4:1"
    "patch-v4:8"
    "patch-v4:16"
)

# Run benchmark for each configuration
for config in "${CONFIGS[@]}"; do
    IFS=':' read -r version threshold <<< "$config"
    pg_path="$HOME/pg-${version}/bin"

    if [ -d "$pg_path" ]; then
        echo ""
        echo "=========================================="
        if [ "$threshold" = "default" ]; then
            echo "Testing PostgreSQL ${version} at: $pg_path"
            version_name="${version}"
        else
            echo "Testing PostgreSQL ${version} (notify_multicast_threshold=${threshold}) at: $pg_path"
            version_name="${version}-t${threshold}"
        fi
        echo "=========================================="

        # Build command
        if [ "$threshold" = "default" ]; then
            # Master version - no threshold parameter
            ./target/release/pg-bench-listen-notify "$pg_path" "$OUTPUT_FILE" --version-name "${version_name}"
        else
            # Patch version with threshold
            ./target/release/pg-bench-listen-notify "$pg_path" "$OUTPUT_FILE" --version-name "${version_name}" --notify-multicast-threshold "${threshold}"
        fi

        if [ $? -eq 0 ]; then
            echo "✅ Benchmark completed for ${version_name}"
        else
            echo "❌ Benchmark failed for ${version_name}"
        fi
    else
        echo "⚠️  Skipping ${version} (directory not found: $pg_path)"
    fi
done

echo ""
echo "All benchmarks completed!"
echo "Results saved in: $OUTPUT_FILE"
