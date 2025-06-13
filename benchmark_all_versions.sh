#!/bin/bash

# Complete benchmark script: run all versions and plot results

echo "🚀 Starting PostgreSQL LISTEN/NOTIFY benchmark for all versions..."

# Run benchmarks for all versions
./run_all_versions.sh

if [ $? -eq 0 ]; then
    echo ""
    echo "📊 Generating comparison plot..."
    
    # Create virtual environment if needed
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    pip install -q -r requirements.txt
    
    # Generate the candlestick comparison plot
    python plot_candlestick.py
    
    deactivate
    
    echo ""
    echo "✅ All done! Check candlestick_comparison.png for results"
else
    echo "❌ Benchmark failed"
    exit 1
fi