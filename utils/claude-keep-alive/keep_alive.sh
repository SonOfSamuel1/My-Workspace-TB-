#!/bin/bash
# Claude Max Keep-Alive
# Sends a minimal request every 30 minutes to keep the usage counter running.
# This ensures the 5-hour usage window is always ticking so you get a reset sooner.

CLAUDE_BIN="/Users/terrancebrandon/.local/bin/claude"
LOG_FILE="$HOME/.claude/keep-alive.log"

# Required: unset CLAUDECODE so claude CLI doesn't think it's nested
unset CLAUDECODE

timestamp=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$timestamp] Sending keep-alive ping..." >> "$LOG_FILE"

response=$("$CLAUDE_BIN" -p "." --output-format text --no-session-persistence 2>&1)
exit_code=$?

echo "[$timestamp] Exit: $exit_code | Response: ${response:0:80}" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Keep log under 500 lines
if [ $(wc -l < "$LOG_FILE") -gt 500 ]; then
    tail -n 500 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

exit $exit_code
