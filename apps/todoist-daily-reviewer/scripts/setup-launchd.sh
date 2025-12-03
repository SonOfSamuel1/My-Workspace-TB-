#!/bin/bash

# Setup LaunchD Agents for Daily Todoist Reviewer
#
# This script installs the launchd agents for:
# 1. Daily report generation (5 AM)
# 2. Email reply polling (every 5 minutes)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
LAUNCHD_DIR="$APP_DIR/launchd"
USER_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "Setting up Todoist Reviewer LaunchD agents..."
echo ""

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$USER_AGENTS_DIR"

# Create logs directory
mkdir -p "$APP_DIR/logs"

# Check if .env exists
if [ ! -f "$APP_DIR/.env" ]; then
  echo "Warning: .env file not found!"
  echo "Please create $APP_DIR/.env with your configuration"
  echo "You can copy from .env.example"
  echo ""
fi

# Function to install a launch agent
install_agent() {
  local plist_name="$1"
  local plist_src="$LAUNCHD_DIR/$plist_name"
  local plist_dest="$USER_AGENTS_DIR/$plist_name"

  echo "Installing $plist_name..."

  # Unload existing agent if running
  if launchctl list | grep -q "${plist_name%.plist}"; then
    echo "  Unloading existing agent..."
    launchctl unload "$plist_dest" 2>/dev/null
  fi

  # Copy plist to LaunchAgents
  cp "$plist_src" "$plist_dest"

  # Load the agent
  launchctl load "$plist_dest"

  if [ $? -eq 0 ]; then
    echo "  ✓ Successfully loaded"
  else
    echo "  ✗ Failed to load"
    return 1
  fi
}

# Install agents
echo ""
install_agent "com.todoist-reviewer.daily.plist"
install_agent "com.todoist-reviewer.poller.plist"

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "The following agents are now installed:"
echo ""
echo "1. Daily Review (com.todoist-reviewer.daily)"
echo "   - Runs at 5 AM every day except Saturday"
echo "   - Generates and sends your daily task review email"
echo ""
echo "2. Reply Poller (com.todoist-reviewer.poller)"
echo "   - Runs every 5 minutes"
echo "   - Monitors for email replies with commands"
echo ""
echo "To check status:"
echo "  launchctl list | grep todoist-reviewer"
echo ""
echo "To manually trigger the daily review:"
echo "  cd $APP_DIR && node src/index.js run"
echo ""
echo "To stop the agents:"
echo "  launchctl unload ~/Library/LaunchAgents/com.todoist-reviewer.*.plist"
echo ""
echo "Logs are saved to:"
echo "  $APP_DIR/logs/"
