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

# Define standard PostgreSQL versions
declare -a PG_PATHS=(
    "/Applications/Postgres.app/Contents/Versions/13/bin"
    "/Applications/Postgres.app/Contents/Versions/14/bin"
    "/Applications/Postgres.app/Contents/Versions/15/bin"
    "/Applications/Postgres.app/Contents/Versions/16/bin"
    "/Applications/Postgres.app/Contents/Versions/17/bin"
)

# Run benchmark for standard versions
for pg_path in "${PG_PATHS[@]}"; do
    if [ -d "$pg_path" ]; then
        echo ""
        echo "=========================================="
        echo "Testing PostgreSQL at: $pg_path"
        echo "=========================================="

        ./target/release/pg-bench-listen-notify "$pg_path" "$OUTPUT_FILE"

        if [ $? -eq 0 ]; then
            echo "✅ Benchmark completed for $pg_path"
        else
            echo "❌ Benchmark failed for $pg_path"
        fi
    else
        echo "⚠️  Skipping $pg_path (directory not found)"
    fi
done

# Test HEAD version
HEAD_PATH="$HOME/pg-dev-head-release/bin"
if [ -d "$HEAD_PATH" ]; then
    echo ""
    echo "=========================================="
    echo "Testing PostgreSQL HEAD at: $HEAD_PATH"
    echo "=========================================="

    ./target/release/pg-bench-listen-notify "$HEAD_PATH" "$OUTPUT_FILE" --version-name "HEAD"

    if [ $? -eq 0 ]; then
        echo "✅ Benchmark completed for HEAD"
    else
        echo "❌ Benchmark failed for HEAD"
    fi
else
    echo "⚠️  Skipping HEAD (directory not found: $HEAD_PATH)"
fi

# Test optimization patch
PATCH_PATH="$HOME/pg-dev-notify-single-listener-opt-release/bin"
if [ -d "$PATCH_PATH" ]; then
    echo ""
    echo "=========================================="
    echo "Testing PostgreSQL patch at: $PATCH_PATH"
    echo "=========================================="

    ./target/release/pg-bench-listen-notify "$PATCH_PATH" "$OUTPUT_FILE" --version-name "jj/notify-single-listener-opt"

    if [ $? -eq 0 ]; then
        echo "✅ Benchmark completed for jj/notify-single-listener-opt"
    else
        echo "❌ Benchmark failed for jj/notify-single-listener-opt"
    fi
else
    echo "⚠️  Skipping patch (directory not found: $PATCH_PATH)"
fi

echo ""
echo "All benchmarks completed!"
echo "Results saved in: $OUTPUT_FILE"