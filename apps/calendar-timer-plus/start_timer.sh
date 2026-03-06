#!/bin/bash
# start_timer.sh — Manual trigger: get next calendar event and start Timer+
# Run: ./start_timer.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/get_next_event.py" --notify --open
