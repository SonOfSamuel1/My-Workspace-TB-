"""Parse Claude Code session JSONL files into structured summaries.

Streams JSONL line-by-line for memory safety on large files.
Extracts metadata needed to generate Todoist task titles and descriptions.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from session_scanner import SessionMetadata

logger = logging.getLogger(__name__)


@dataclass
class SessionSummary:
    """Structured summary extracted from a session JSONL file."""

    session_id: str
    slug: str
    cwd: str
    git_branch: str
    app_name: str
    first_user_message: str
    first_timestamp: str
    last_timestamp: str
    user_message_count: int
    assistant_message_count: int
    tools_used: Set[str] = field(default_factory=set)
    key_files: List[str] = field(default_factory=list)

    def task_title(self) -> str:
        """Generate Todoist task title: [app-name] First 80 chars of request."""
        truncated = self.first_user_message[:80]
        if len(self.first_user_message) > 80:
            truncated = truncated.rsplit(" ", 1)[0] + "..."
        return f"[{self.app_name}] {truncated}"

    def task_description(self, max_length: int = 4000) -> str:
        """Generate Todoist task description with resume command and context."""
        msg_preview = self.first_user_message[:500]
        if len(self.first_user_message) > 500:
            msg_preview = msg_preview.rsplit(" ", 1)[0] + "..."

        tools_str = (
            ", ".join(sorted(self.tools_used)[:15]) if self.tools_used else "N/A"
        )
        files_str = "\n".join(f"  - {f}" for f in self.key_files[:10])
        if not files_str:
            files_str = "  N/A"

        desc = f"""## Resume Command
claude -r {self.session_id}

## What Was Being Built
{msg_preview}

## Session Info
- Working directory: {self.cwd}
- Branch: {self.git_branch}
- Started: {self.first_timestamp}
- Last activity: {self.last_timestamp}
- Messages: {self.user_message_count} user / {self.assistant_message_count} assistant
- Tools used: {tools_str}
- Key files:
{files_str}"""

        if len(desc) > max_length:
            desc = desc[: max_length - 3] + "..."
        return desc


def _extract_app_name(cwd: str) -> str:
    """Extract app/feature name from the working directory path.

    Examples:
        /apps/gmail-email-actions/ -> gmail-email-actions
        /servers/todoist-mcp-server/ -> todoist-mcp-server
        /My-Workspace-TB- -> My-Workspace-TB- (root)
    """
    parts = Path(cwd).parts

    # Look for known directory markers
    for marker in ("apps", "servers", "utils"):
        if marker in parts:
            idx = parts.index(marker)
            if idx + 1 < len(parts):
                return parts[idx + 1]

    # Fall back to the last directory component
    return Path(cwd).name


def _extract_tool_names(content_list: list) -> Set[str]:
    """Extract tool names from an assistant message content list."""
    tools = set()
    for block in content_list:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            name = block.get("name", "")
            # Strip MCP prefixes like mcp__playwright__
            if "__" in name:
                name = name.split("__")[-1]
            tools.add(name)
    return tools


def _extract_file_paths(content_list: list) -> List[str]:
    """Extract file paths from tool_use inputs (Read, Edit, Write, Glob)."""
    paths = []
    for block in content_list:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            inp = block.get("input", {})
            for key in ("file_path", "path", "pattern"):
                val = inp.get(key)
                if val and isinstance(val, str) and "/" in val:
                    paths.append(val)
    return paths


def parse_session(metadata: SessionMetadata) -> Optional[SessionSummary]:
    """Parse a session JSONL file into a SessionSummary.

    Streams line-by-line for memory safety. Returns None if the session
    cannot be parsed (e.g., corrupt file, no user messages).
    """
    session_id = metadata.session_id
    slug = ""
    cwd = ""
    git_branch = ""
    first_user_message = ""
    first_timestamp = ""
    last_timestamp = ""
    user_count = 0
    assistant_count = 0
    tools_used: Set[str] = set()
    key_files: List[str] = []
    seen_files: Set[str] = set()

    try:
        with open(metadata.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get("type", "")
                timestamp = entry.get("timestamp", "")

                # Track timestamps
                if timestamp:
                    if not first_timestamp:
                        first_timestamp = timestamp
                    last_timestamp = timestamp

                # Extract metadata from user messages
                if entry_type == "user":
                    user_count += 1

                    if not cwd:
                        cwd = entry.get("cwd", "")
                    if not slug:
                        slug = entry.get("slug", "")
                    if not git_branch:
                        git_branch = entry.get("gitBranch", "")

                    # Capture first user message text
                    if not first_user_message:
                        msg = entry.get("message", {})
                        content = msg.get("content", "")
                        if isinstance(content, str) and content.strip():
                            first_user_message = content.strip()
                        elif isinstance(content, list):
                            # Multi-part content — extract text blocks
                            texts = [
                                b.get("text", "")
                                for b in content
                                if isinstance(b, dict) and b.get("type") == "text"
                            ]
                            first_user_message = " ".join(texts).strip()

                # Extract tool usage from assistant messages
                elif entry_type == "assistant":
                    assistant_count += 1
                    msg = entry.get("message", {})
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        tools_used.update(_extract_tool_names(content))
                        for fp in _extract_file_paths(content):
                            if fp not in seen_files:
                                seen_files.add(fp)
                                key_files.append(fp)

    except Exception as e:
        logger.error(f"Failed to parse session {session_id}: {e}")
        return None

    if not first_user_message:
        logger.debug(f"Skipping session {session_id}: no user messages found")
        return None

    app_name = _extract_app_name(cwd) if cwd else "unknown"

    return SessionSummary(
        session_id=session_id,
        slug=slug,
        cwd=cwd,
        git_branch=git_branch,
        app_name=app_name,
        first_user_message=first_user_message,
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        user_message_count=user_count,
        assistant_message_count=assistant_count,
        tools_used=tools_used,
        key_files=key_files[:30],  # cap to avoid huge lists
    )
