#!/bin/bash
# Uninstall the Claude Max keep-alive launchd agent

PLIST_DEST="$HOME/Library/LaunchAgents/com.terrancebrandon.claude-keep-alive.plist"

launchctl unload "$PLIST_DEST" 2>/dev/null
rm -f "$PLIST_DEST"

echo "Uninstalled. Claude keep-alive stopped."
