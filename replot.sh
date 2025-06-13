#!/bin/bash

# Script to regenerate the plot from existing benchmark results

echo "📊 Regenerating comparison plot from existing results..."

# Check if benchmark results file exists
if [ ! -f "benchmark_results.csv" ]; then
    echo "❌ Error: benchmark_results.csv not found"
    echo "Run ./benchmark_all_versions.sh first to generate benchmark data"
    exit 1
fi

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import pandas" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip install -q -r requirements.txt
fi

# Generate the candlestick comparison plot
echo "Generating candlestick plot..."
python plot_candlestick.py

deactivate

if [ -f "candlestick_comparison.png" ]; then
    echo "✅ Plot regenerated successfully!"
    echo "📍 Output: candlestick_comparison.png"
else
    echo "❌ Failed to generate plot"
    exit 1
fi