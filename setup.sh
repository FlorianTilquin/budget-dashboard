#!/bin/bash

# Budget Dashboard Setup Script

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    pip install uv || pipx install uv
fi

# Set up virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
# Ensure we reinstall to reflect any changes
uv pip uninstall budget-dashboard || true
uv pip install -e .

# Run the app
echo "Starting the Budget Dashboard..."
echo "Access it at http://127.0.0.1:8050/"
./run.py 