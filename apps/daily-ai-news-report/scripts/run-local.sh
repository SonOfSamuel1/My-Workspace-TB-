#!/bin/bash
# Run Daily AI News Report locally

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

echo "==================================="
echo "Daily AI News Report - Local Run"
echo "==================================="

# Check for virtual environment
if [ ! -d "$APP_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$APP_DIR/venv"
fi

# Activate virtual environment
source "$APP_DIR/venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -r "$APP_DIR/requirements.txt" --quiet

# Check for .env file
if [ ! -f "$APP_DIR/.env" ]; then
    echo ""
    echo "WARNING: No .env file found!"
    echo "Copy .env.example to .env and configure your settings:"
    echo "  cp $APP_DIR/.env.example $APP_DIR/.env"
    echo ""
fi

# Parse arguments
DRY_RUN=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run the report
echo ""
echo "Running report..."
cd "$APP_DIR"
python -m src.news_main $DRY_RUN $VERBOSE

echo ""
echo "Done!"
