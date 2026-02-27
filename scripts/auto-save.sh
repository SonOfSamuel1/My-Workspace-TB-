#!/bin/bash

# auto-save.sh - Watches repo for file changes and auto-commits/pushes to GitHub
#
# Uses fswatch to detect changes, debounces for 60 seconds of quiet,
# then commits all changes and pushes to origin/main.

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$REPO_DIR/logs/auto-save"
LOG_FILE="$LOG_DIR/auto-save.log"
PID_FILE="$LOG_DIR/auto-save.pid"
DEBOUNCE_SECONDS=60
MAX_LOG_BYTES=$((10 * 1024 * 1024))  # 10MB
PUSH_RETRIES=3
PUSH_RETRY_DELAY=30
BRANCH="main"
REMOTE="origin"

# Directories/patterns to exclude from watching
EXCLUDE_PATTERNS=(
    ".git/"
    "node_modules/"
    "dist/"
    "build/"
    "out/"
    "__pycache__/"
    ".venv/"
    "venv/"
    ".pytest_cache/"
    ".next/"
    "coverage/"
    ".turbo/"
    ".nx/"
    "logs/"
    ".DS_Store"
    "*.pyc"
    "*.log"
    "*.pid"
)

# ── Helpers ────────────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"

log() {
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$timestamp] $*" >> "$LOG_FILE"
}

rotate_log() {
    if [[ -f "$LOG_FILE" ]]; then
        local size
        size=$(stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)
        if (( size > MAX_LOG_BYTES )); then
            mv "$LOG_FILE" "$LOG_FILE.1"
            log "Log rotated (previous log was ${size} bytes)"
        fi
    fi
}

cleanup() {
    log "Shutting down auto-save daemon"
    rm -f "$PID_FILE"
    # Kill fswatch if it's still running
    if [[ -n "${FSWATCH_PID:-}" ]] && kill -0 "$FSWATCH_PID" 2>/dev/null; then
        kill "$FSWATCH_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT SIGHUP EXIT

# ── PID Management ─────────────────────────────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "auto-save is already running (PID $OLD_PID)" >&2
        exit 1
    else
        log "Stale PID file found (PID $OLD_PID no longer running), removing"
        rm -f "$PID_FILE"
    fi
fi

echo $$ > "$PID_FILE"
log "auto-save daemon started (PID $$)"

# ── Dry-run mode ───────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--dry-run" ]]; then
    log "DRY RUN MODE - will detect changes but not commit/push"
    DRY_RUN=true
else
    DRY_RUN=false
fi

# ── Verify fswatch ─────────────────────────────────────────────────────────────
if ! command -v fswatch &>/dev/null; then
    log "ERROR: fswatch not found. Install with: brew install fswatch"
    echo "ERROR: fswatch not found. Install with: brew install fswatch" >&2
    exit 1
fi

# ── Build fswatch exclude args ─────────────────────────────────────────────────
FSWATCH_EXCLUDES=()
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    FSWATCH_EXCLUDES+=(--exclude "$pattern")
done

# ── Summarize changed files for commit message ────────────────────────────────
build_commit_message() {
    local staged_files count dirs unique_dirs summary timestamp

    staged_files=$(git -C "$REPO_DIR" diff --cached --name-only 2>/dev/null)
    count=$(echo "$staged_files" | grep -c . 2>/dev/null || echo 0)
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Extract top-level directories that changed (e.g., apps/ynab-dashboard, servers/gmail)
    dirs=$(echo "$staged_files" | sed 's|/[^/]*$||' | sort -u | head -5)
    unique_dirs=$(echo "$dirs" | tr '\n' ', ' | sed 's/,$//' | sed 's/,/, /g')

    if [[ -n "$unique_dirs" ]]; then
        echo "auto-save: ${count} file(s) changed in ${unique_dirs} [${timestamp}]"
    else
        echo "auto-save: ${count} file(s) changed [${timestamp}]"
    fi
}

# ── Git commit and push ───────────────────────────────────────────────────────
do_commit_and_push() {
    cd "$REPO_DIR"

    # Stage all changes
    git add -A

    # Check if there are actually staged changes
    if git diff --cached --quiet 2>/dev/null; then
        log "No changes to commit (working tree clean after staging)"
        return 0
    fi

    local commit_msg
    commit_msg=$(build_commit_message)

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would commit with message: $commit_msg"
        git reset HEAD -- . >/dev/null 2>&1 || true
        return 0
    fi

    # Commit (bypass pre-commit hooks since mid-edit code won't pass linting)
    if ! git commit --no-verify -m "$commit_msg" 2>&1 | while IFS= read -r line; do log "  git commit: $line"; done; then
        log "WARNING: git commit failed"
        return 1
    fi

    log "Committed: $commit_msg"

    # Push with retry logic
    local attempt=0
    while (( attempt < PUSH_RETRIES )); do
        attempt=$((attempt + 1))

        if git push "$REMOTE" "$BRANCH" 2>&1 | while IFS= read -r line; do log "  git push: $line"; done; then
            log "Pushed to $REMOTE/$BRANCH successfully"
            return 0
        fi

        log "Push attempt $attempt/$PUSH_RETRIES failed"

        # Check if remote has diverged
        git fetch "$REMOTE" "$BRANCH" 2>/dev/null
        local local_head remote_head
        local_head=$(git rev-parse HEAD)
        remote_head=$(git rev-parse "$REMOTE/$BRANCH" 2>/dev/null || echo "")

        if [[ -n "$remote_head" && "$local_head" != "$remote_head" ]]; then
            log "Remote has diverged, attempting rebase..."
            if git rebase "$REMOTE/$BRANCH" 2>&1 | while IFS= read -r line; do log "  git rebase: $line"; done; then
                log "Rebase successful, retrying push..."
                continue
            else
                log "WARNING: Rebase failed with conflicts, aborting rebase"
                git rebase --abort 2>/dev/null || true
                log "Manual intervention required to resolve conflicts"
                return 1
            fi
        fi

        if (( attempt < PUSH_RETRIES )); then
            log "Retrying push in ${PUSH_RETRY_DELAY}s..."
            sleep "$PUSH_RETRY_DELAY"
        fi
    done

    log "WARNING: Push failed after $PUSH_RETRIES attempts. Commit saved locally."
    return 1
}

# ── Main watch loop ────────────────────────────────────────────────────────────
log "Watching $REPO_DIR for changes (debounce: ${DEBOUNCE_SECONDS}s)"

while true; do
    rotate_log

    # Start fswatch in the background - it outputs a path each time something changes
    # --latency is the debounce: waits this long after last event before reporting
    # --one-per-batch: emit one event per batch rather than one per file
    fswatch \
        --recursive \
        --latency "$DEBOUNCE_SECONDS" \
        --one-per-batch \
        "${FSWATCH_EXCLUDES[@]}" \
        "$REPO_DIR" &
    FSWATCH_PID=$!

    # Wait for fswatch to emit (meaning changes detected + debounce elapsed)
    if wait "$FSWATCH_PID" 2>/dev/null; then
        log "Changes detected after ${DEBOUNCE_SECONDS}s quiet period"
        do_commit_and_push || true
    else
        # fswatch exited abnormally (killed or crashed)
        log "fswatch exited unexpectedly, restarting in 5s..."
        sleep 5
    fi
done
