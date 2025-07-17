#!/bin/bash

# Complete benchmark script: run all versions and plot results

echo "🚀 Starting PostgreSQL LISTEN/NOTIFY benchmark for all versions..."

# Run benchmarks for all versions
./run_all_versions.sh

if [ $? -eq 0 ]; then
    echo ""
    echo "📊 Generating comparison plot..."

    # Generate the comparison plot
    ./plot.sh

    echo ""
    echo "✅ All done! Check plot-v4.png for results"
else
    echo "❌ Benchmark failed"
    exit 1
fi