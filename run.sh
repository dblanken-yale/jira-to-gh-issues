#!/bin/bash
# Activation script for the Jira to GitHub migration tool
# Usage: ./run.sh [command and arguments]

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Path to the virtual environment Python
PYTHON_PATH="$SCRIPT_DIR/.venv/bin/python"

# Check if virtual environment exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Virtual environment not found at $PYTHON_PATH"
    echo "Please run: python setup.py"
    exit 1
fi

# Run the command with the virtual environment Python
"$PYTHON_PATH" "$SCRIPT_DIR/main.py" "$@"
