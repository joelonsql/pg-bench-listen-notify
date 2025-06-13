#!/bin/bash

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import pandas" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Run the plot script
echo "Generating plot from stats.csv..."
python plot_stats.py "$@"

# Deactivate virtual environment
deactivate

echo "Done! Check benchmark_results.png"