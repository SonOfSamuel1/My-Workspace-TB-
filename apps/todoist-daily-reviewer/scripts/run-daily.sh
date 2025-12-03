#!/bin/bash

# Daily Todoist Reviewer - Run Script
#
# This script runs the daily task review and sends the email.
# Intended to be called by macOS launchd at 5 AM daily.

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

# Load environment variables
if [ -f "$APP_DIR/.env" ]; then
  export $(grep -v '^#' "$APP_DIR/.env" | xargs)
fi

# Ensure we're using the correct Node.js
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

# Log file
LOG_DIR="$APP_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/daily-review-$(date +%Y-%m-%d).log"

echo "========================================" >> "$LOG_FILE"
echo "Daily Todoist Review - $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Run the daily review
cd "$APP_DIR"
node src/index.js run >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "Daily review completed successfully" >> "$LOG_FILE"
else
  echo "Daily review failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"

# Keep only last 30 days of logs
find "$LOG_DIR" -name "daily-review-*.log" -mtime +30 -delete

exit $EXIT_CODE
