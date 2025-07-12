#!/bin/sh
# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
pip install -q -r requirements.txt
source venv/bin/activate
./plot.py
