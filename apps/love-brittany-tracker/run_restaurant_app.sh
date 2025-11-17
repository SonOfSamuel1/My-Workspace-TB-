#!/bin/bash

# Restaurant Web Application Launcher
# Starts the Flask web server for Atlanta restaurant discovery

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🍽️  Starting Atlanta Restaurant Discovery App..."
echo "Project root: $PROJECT_ROOT"

# Activate virtual environment
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    echo "✓ Virtual environment activated"
else
    echo "❌ Virtual environment not found at $PROJECT_ROOT/venv"
    echo "Please run: python3 -m venv $PROJECT_ROOT/venv"
    exit 1
fi

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing web application dependencies..."
    pip install -r "$SCRIPT_DIR/requirements-web.txt"
fi

# Set environment variables
export FLASK_APP="$SCRIPT_DIR/src/restaurant_web_app.py"
export FLASK_ENV="development"
export PORT=5000

# Start the Flask server
cd "$SCRIPT_DIR"
echo "🚀 Starting server on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

python src/restaurant_web_app.py
