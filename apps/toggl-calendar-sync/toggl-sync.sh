#!/bin/bash
#
# Toggl Calendar Sync Helper Script
#
# Usage:
#   ./toggl-sync.sh              # Sync today
#   ./toggl-sync.sh yesterday    # Sync yesterday
#   ./toggl-sync.sh week         # Sync this week
#   ./toggl-sync.sh logs         # View logs
#   ./toggl-sync.sh status       # Check sync status
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
source venv/bin/activate

case "$1" in
    yesterday)
        echo "Syncing yesterday's entries..."
        python src/main.py --mode yesterday
        ;;
    week)
        echo "Syncing this week's entries..."
        python src/main.py --mode week
        ;;
    logs)
        echo "=== Recent Sync Logs ==="
        tail -50 logs/sync.log
        ;;
    cron-logs)
        echo "=== Recent Cron Logs ==="
        tail -50 logs/cron.log
        ;;
    status)
        echo "=== Sync Status ==="
        python src/main.py --mode validate
        ;;
    validate)
        echo "=== Validating Services ==="
        python src/main.py --mode validate
        ;;
    *)
        echo "Syncing today's entries..."
        python src/main.py --mode today
        ;;
esac
