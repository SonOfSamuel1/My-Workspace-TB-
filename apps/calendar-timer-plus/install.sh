#!/bin/bash
# install.sh — Install the LaunchAgent to run on schedule
# Run once: ./install.sh

set -e

PLIST="com.terrancebrandon.calendar-timer-plus.plist"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

# Make scripts executable
chmod +x "$SCRIPT_DIR/start_timer.sh"
chmod +x "$SCRIPT_DIR/get_next_event.py"

# Copy plist to LaunchAgents
mkdir -p "$LAUNCH_AGENTS"
cp "$SCRIPT_DIR/$PLIST" "$LAUNCH_AGENTS/$PLIST"

# Load the agent
launchctl unload "$LAUNCH_AGENTS/$PLIST" 2>/dev/null || true
launchctl load "$LAUNCH_AGENTS/$PLIST"

echo "Installed. The script will now run every 15 minutes."
echo ""
echo "Test it now:"
echo "  python3 $SCRIPT_DIR/get_next_event.py"
echo ""
echo "Manual trigger:"
echo "  $SCRIPT_DIR/start_timer.sh"
echo ""
echo "View logs:"
echo "  tail -f /tmp/calendar-timer-plus.log"
echo "  tail -f /tmp/calendar-timer-plus-error.log"
echo ""
echo "Uninstall:"
echo "  launchctl unload ~/Library/LaunchAgents/$PLIST && rm ~/Library/LaunchAgents/$PLIST"
