"""Session discovery for Claude Code session transcripts.

Scans ~/.claude/projects/ for recent JSONL session files,
filtering by modification time and minimum file size.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$"
)


@dataclass
class SessionMetadata:
    """Lightweight metadata about a discovered session file."""

    session_id: str
    project_dir: str
    file_path: Path
    last_modified: datetime
    file_size: int


def discover_all_sessions(
    lookback_days: int = 7,
    min_file_size: int = 5000,
    include_project_patterns: Optional[List[str]] = None,
) -> List[SessionMetadata]:
    """Discover all recent session JSONL files under ~/.claude/projects/.

    Args:
        lookback_days: Only include sessions modified within this many days.
        min_file_size: Minimum file size in bytes (skip trivial sessions).
        include_project_patterns: Optional list of substring patterns to filter
            project directories. None means scan all projects.

    Returns:
        List of SessionMetadata sorted by last_modified descending (newest first).
    """
    if not CLAUDE_PROJECTS_DIR.exists():
        logger.warning(f"Claude projects directory not found: {CLAUDE_PROJECTS_DIR}")
        return []

    cutoff = datetime.now() - timedelta(days=lookback_days)
    sessions: List[SessionMetadata] = []

    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        # Apply project pattern filter if configured
        if include_project_patterns:
            dir_name = project_dir.name
            if not any(pat in dir_name for pat in include_project_patterns):
                continue

        # Scan top-level JSONL files only (skip subdirectories like memory/)
        for f in project_dir.iterdir():
            if not f.is_file():
                continue
            if not UUID_PATTERN.match(f.name):
                continue

            stat = f.stat()

            # Filter by size
            if stat.st_size < min_file_size:
                continue

            # Filter by modification time
            mtime = datetime.fromtimestamp(stat.st_mtime)
            if mtime < cutoff:
                continue

            session_id = f.stem  # UUID without .jsonl extension
            sessions.append(
                SessionMetadata(
                    session_id=session_id,
                    project_dir=project_dir.name,
                    file_path=f,
                    last_modified=mtime,
                    file_size=stat.st_size,
                )
            )

    # Sort newest first
    sessions.sort(key=lambda s: s.last_modified, reverse=True)
    logger.info(
        f"Discovered {len(sessions)} sessions "
        f"(lookback={lookback_days}d, min_size={min_file_size}B)"
    )
    return sessions
