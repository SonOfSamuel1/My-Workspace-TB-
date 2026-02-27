#!/bin/bash

# auto-save-ctl.sh - Control script for the auto-save daemon
#
# Usage:
#   ./scripts/auto-save-ctl.sh install     Install fswatch (if needed) + register + start service
#   ./scripts/auto-save-ctl.sh start       Start the service
#   ./scripts/auto-save-ctl.sh stop        Stop the service
#   ./scripts/auto-save-ctl.sh restart     Restart the service
#   ./scripts/auto-save-ctl.sh status      Check if running + show recent logs
#   ./scripts/auto-save-ctl.sh logs        Tail the log file
#   ./scripts/auto-save-ctl.sh test        Dry-run mode to verify setup
#   ./scripts/auto-save-ctl.sh uninstall   Remove service entirely

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$REPO_DIR/logs/auto-save"
LOG_FILE="$LOG_DIR/auto-save.log"
PID_FILE="$LOG_DIR/auto-save.pid"

PLIST_NAME="com.terrancebrandon.auto-save"
PLIST_SRC="$SCRIPT_DIR/launchd/${PLIST_NAME}.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

# ── Helpers ────────────────────────────────────────────────────────────────────
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
red()    { printf '\033[31m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

is_loaded() {
    launchctl list 2>/dev/null | grep -q "$PLIST_NAME"
}

is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# ── Commands ───────────────────────────────────────────────────────────────────
cmd_install() {
    bold "Installing auto-save service..."
    echo ""

    # Check/install fswatch
    if command -v fswatch &>/dev/null; then
        green "fswatch found: $(which fswatch)"
    else
        yellow "fswatch not found. Installing via Homebrew..."
        if ! command -v brew &>/dev/null; then
            red "ERROR: Homebrew not found. Install fswatch manually: https://emcrisostomo.github.io/fswatch/"
            exit 1
        fi
        brew install fswatch
        green "fswatch installed successfully"
    fi

    # Create logs directory
    mkdir -p "$LOG_DIR"

    # Create LaunchAgents directory
    mkdir -p "$HOME/Library/LaunchAgents"

    # Unload existing if loaded
    if is_loaded; then
        yellow "Unloading existing service..."
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    # Copy plist
    cp "$PLIST_SRC" "$PLIST_DEST"
    green "Plist copied to $PLIST_DEST"

    # Load service
    launchctl load "$PLIST_DEST"

    if is_loaded; then
        green "Service loaded successfully"
    else
        red "ERROR: Failed to load service"
        exit 1
    fi

    echo ""
    green "auto-save installed and running!"
    echo ""
    echo "  Status:    ./scripts/auto-save-ctl.sh status"
    echo "  Logs:      ./scripts/auto-save-ctl.sh logs"
    echo "  Stop:      ./scripts/auto-save-ctl.sh stop"
    echo "  Uninstall: ./scripts/auto-save-ctl.sh uninstall"
}

cmd_start() {
    if is_running; then
        yellow "auto-save is already running (PID $(cat "$PID_FILE"))"
        return 0
    fi

    if [[ ! -f "$PLIST_DEST" ]]; then
        red "Service not installed. Run: ./scripts/auto-save-ctl.sh install"
        exit 1
    fi

    if is_loaded; then
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi
    launchctl load "$PLIST_DEST"
    green "auto-save started"
}

cmd_stop() {
    if is_loaded; then
        launchctl unload "$PLIST_DEST" 2>/dev/null || true
    fi

    # Also kill the process if PID file exists
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            yellow "Sent SIGTERM to PID $pid"
        fi
        rm -f "$PID_FILE"
    fi

    green "auto-save stopped"
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    bold "auto-save status"
    echo ""

    # Service status
    if is_loaded; then
        green "  launchd: loaded"
    else
        red "  launchd: not loaded"
    fi

    # Process status
    if is_running; then
        green "  process: running (PID $(cat "$PID_FILE"))"
    else
        red "  process: not running"
    fi

    # fswatch check
    if command -v fswatch &>/dev/null; then
        green "  fswatch: installed ($(fswatch --version 2>&1 | head -1 || echo 'unknown version'))"
    else
        red "  fswatch: NOT installed"
    fi

    # Log file
    echo ""
    if [[ -f "$LOG_FILE" ]]; then
        bold "  Recent log entries:"
        echo ""
        tail -10 "$LOG_FILE" | sed 's/^/    /'
    else
        yellow "  No log file yet"
    fi
}

cmd_logs() {
    if [[ ! -f "$LOG_FILE" ]]; then
        yellow "No log file yet at $LOG_FILE"
        exit 0
    fi
    tail -f "$LOG_FILE"
}

cmd_test() {
    bold "Running auto-save in dry-run mode..."
    echo "Press Ctrl+C to stop."
    echo ""
    "$SCRIPT_DIR/auto-save.sh" --dry-run
}

cmd_uninstall() {
    bold "Uninstalling auto-save service..."

    # Stop first
    cmd_stop

    # Remove plist from LaunchAgents
    if [[ -f "$PLIST_DEST" ]]; then
        rm -f "$PLIST_DEST"
        green "Removed $PLIST_DEST"
    fi

    echo ""
    green "auto-save uninstalled"
    yellow "Log files preserved at: $LOG_DIR"
    echo "To remove logs too: rm -rf \"$LOG_DIR\""
}

# ── Main ───────────────────────────────────────────────────────────────────────
case "${1:-help}" in
    install)   cmd_install ;;
    start)     cmd_start ;;
    stop)      cmd_stop ;;
    restart)   cmd_restart ;;
    status)    cmd_status ;;
    logs)      cmd_logs ;;
    test)      cmd_test ;;
    uninstall) cmd_uninstall ;;
    help|--help|-h)
        echo "Usage: $0 {install|start|stop|restart|status|logs|test|uninstall}"
        echo ""
        echo "  install    Install fswatch (if needed) + register + start service"
        echo "  start      Start the service"
        echo "  stop       Stop the service"
        echo "  restart    Restart the service"
        echo "  status     Check if running + show recent logs"
        echo "  logs       Tail the log file"
        echo "  test       Dry-run mode to verify setup"
        echo "  uninstall  Remove service entirely"
        ;;
    *)
        red "Unknown command: $1"
        echo "Usage: $0 {install|start|stop|restart|status|logs|test|uninstall}"
        exit 1
        ;;
esac
