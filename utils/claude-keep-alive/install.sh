#!/bin/bash
# Install the Claude Max keep-alive launchd agent

PLIST_SRC="$(dirname "$0")/com.terrancebrandon.claude-keep-alive.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.terrancebrandon.claude-keep-alive.plist"
SCRIPT="$(dirname "$0")/keep_alive.sh"
SCRIPT_DEST="$HOME/.local/bin/claude-keep-alive.sh"

# Copy script to ~/.local/bin (accessible by launchd on macOS)
mkdir -p "$HOME/.local/bin"
cp "$SCRIPT" "$SCRIPT_DEST"
chmod +x "$SCRIPT_DEST"

# Copy plist to LaunchAgents
cp "$PLIST_SRC" "$PLIST_DEST"

# Load the agent
launchctl unload "$PLIST_DEST" 2>/dev/null
launchctl load -w "$PLIST_DEST"

echo "Installed. Claude keep-alive will run every 30 minutes."
echo "Logs: ~/.claude/keep-alive.log"
echo "To uninstall: bash $(dirname "$0")/uninstall.sh"
