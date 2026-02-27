#!/usr/bin/env python3
"""Main entry point for CC Session Tracker.

Scans Claude Code session transcripts and creates Todoist tasks
for in-progress development work so nothing falls through the cracks.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from session_scanner import discover_all_sessions  # noqa: E402
from session_summarizer import SessionSummary, parse_session  # noqa: E402
from todoist_service import TodoistService  # noqa: E402

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent.parent / "state" / "processed_sessions.json"


# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------


def setup_logging():
    """Setup logging to stdout + file."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "cc_session_tracker.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_environment():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists() and HAS_DOTENV:
        load_dotenv(env_path)
        logger.info("Environment loaded from .env")
    elif env_path.exists():
        logger.info("python-dotenv not available, using env vars only")


# ------------------------------------------------------------------
# State management
# ------------------------------------------------------------------


def load_state() -> dict:
    """Load the processed sessions state file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"processed_sessions": {}, "last_run": None}


def save_state(state: dict):
    """Save the processed sessions state file."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    state["last_run"] = datetime.utcnow().isoformat() + "Z"
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    logger.info(f"State saved to {STATE_FILE}")


# ------------------------------------------------------------------
# Core pipeline
# ------------------------------------------------------------------


def group_by_app(summaries: List[SessionSummary]) -> Dict[str, SessionSummary]:
    """Group sessions by app_name, keeping only the most recent per app.

    Assumes summaries are already sorted newest-first (from scanner).
    """
    grouped: Dict[str, SessionSummary] = {}
    for summary in summaries:
        if summary.app_name not in grouped:
            grouped[summary.app_name] = summary
    logger.info(f"Grouped {len(summaries)} sessions into {len(grouped)} unique apps")
    return grouped


def find_existing_task_for_app(tasks: List[Dict], app_name: str) -> Optional[Dict]:
    """Find an existing open task with a matching [app-name] prefix."""
    prefix = f"[{app_name}]"
    for task in tasks:
        if task.get("content", "").startswith(prefix):
            return task
    return None


# ------------------------------------------------------------------
# Validate
# ------------------------------------------------------------------


def validate_setup(config: dict) -> bool:
    """Validate that all services are properly configured."""
    print("\n" + "=" * 60)
    print("CC SESSION TRACKER - SETUP VALIDATION")
    print("=" * 60 + "\n")

    tracker_config = config.get("cc_session_tracker", {})
    project_name = tracker_config.get(
        "todoist_project_name", "CC- Development in Progress"
    )

    # Check API token
    api_token = os.getenv("TODOIST_API_TOKEN", "")
    if not api_token:
        print("  Todoist API token: MISSING")
        return False
    print("  Todoist API token: present")

    # Check Todoist connection
    print("\n  Testing Todoist connection...")
    try:
        service = TodoistService(api_token)
        if not service.validate_connection():
            print("  Todoist connection: FAILED")
            return False
        print("  Todoist connection: OK")

        project = service.get_project_by_name(project_name)
        if project:
            print(f"  Project '{project_name}': found (id={project['id']})")
        else:
            print(
                f"  Project '{project_name}': not found (will be created on first run)"
            )
    except Exception as e:
        print(f"  Todoist connection failed: {e}")
        return False

    # Check sessions directory
    from session_scanner import CLAUDE_PROJECTS_DIR

    if CLAUDE_PROJECTS_DIR.exists():
        project_dirs = [d for d in CLAUDE_PROJECTS_DIR.iterdir() if d.is_dir()]
        print(f"\n  Claude projects directory: {CLAUDE_PROJECTS_DIR}")
        print(f"  Project directories found: {len(project_dirs)}")
    else:
        print(f"\n  Claude projects directory: NOT FOUND ({CLAUDE_PROJECTS_DIR})")
        return False

    # Quick scan test
    lookback = tracker_config.get("lookback_days", 7)
    min_size = tracker_config.get("min_file_size", 5000)
    sessions = discover_all_sessions(lookback_days=lookback, min_file_size=min_size)
    print(f"  Recent sessions (last {lookback} days, >={min_size}B): {len(sessions)}")

    print("\n" + "=" * 60)
    print("  ALL VALIDATIONS PASSED")
    print("=" * 60 + "\n")
    return True


# ------------------------------------------------------------------
# Run pipeline
# ------------------------------------------------------------------


def run_tracker(config: dict, dry_run: bool = False) -> dict:
    """Run the full scan-and-create pipeline.

    Returns summary dict with counts.
    """
    tracker_config = config.get("cc_session_tracker", {})
    project_name = tracker_config.get(
        "todoist_project_name", "CC- Development in Progress"
    )
    lookback = tracker_config.get("lookback_days", 7)
    min_size = tracker_config.get("min_file_size", 5000)
    max_desc = tracker_config.get("max_description_length", 4000)
    patterns = tracker_config.get("include_project_patterns")

    api_token = os.getenv("TODOIST_API_TOKEN", "")
    if not api_token and not dry_run:
        raise ValueError("TODOIST_API_TOKEN not set")

    state = load_state()

    # 1. Discover sessions
    logger.info("Discovering recent sessions...")
    all_sessions = discover_all_sessions(
        lookback_days=lookback,
        min_file_size=min_size,
        include_project_patterns=patterns,
    )

    if not all_sessions:
        print("\n  No recent sessions found. Nothing to do.")
        return {"sessions_found": 0, "tasks_created": 0, "tasks_updated": 0}

    # 2. Parse each session into a summary
    logger.info("Parsing session transcripts...")
    summaries: List[SessionSummary] = []
    for meta in all_sessions:
        summary = parse_session(meta)
        if summary:
            summaries.append(summary)

    logger.info(f"Parsed {len(summaries)} sessions successfully")

    if not summaries:
        print("\n  No parseable sessions found. Nothing to do.")
        return {
            "sessions_found": len(all_sessions),
            "tasks_created": 0,
            "tasks_updated": 0,
        }

    # 3. Group by app — one task per app
    app_groups = group_by_app(summaries)

    # 4. Dry run — just print
    if dry_run:
        print(f"\n{'=' * 60}")
        print("CC SESSION TRACKER - DRY RUN")
        print(f"{'=' * 60}")
        print(f"\n  Sessions discovered: {len(all_sessions)}")
        print(f"  Sessions parsed: {len(summaries)}")
        print(f"  Unique apps: {len(app_groups)}")
        print()
        for app_name, summary in sorted(app_groups.items()):
            print(f"  --- {app_name} ---")
            print(f"  Title: {summary.task_title()}")
            print(f"  Session: {summary.session_id}")
            print(f"  CWD: {summary.cwd}")
            print(f"  Branch: {summary.git_branch}")
            print(
                f"  Messages: {summary.user_message_count}u / {summary.assistant_message_count}a"
            )
            print(f"  Resume: claude -r {summary.session_id}")
            print()
        print(f"{'=' * 60}\n")
        return {
            "sessions_found": len(all_sessions),
            "tasks_created": 0,
            "tasks_updated": 0,
            "dry_run": True,
        }

    # 5. Connect to Todoist and get/create project
    service = TodoistService(api_token)
    project = service.get_or_create_project(project_name)
    project_id = project["id"]

    # 6. Fetch existing tasks for dedup
    existing_tasks = service.get_tasks_in_project(project_id)
    logger.info(f"Found {len(existing_tasks)} existing tasks in project")

    # 7. Create or update tasks
    created = 0
    updated = 0

    for app_name, summary in app_groups.items():
        title = summary.task_title()
        description = summary.task_description(max_length=max_desc)

        existing = find_existing_task_for_app(existing_tasks, app_name)

        if existing:
            # Update existing task's description with latest session info
            task_id = existing["id"]
            logger.info(f"Updating existing task for [{app_name}]: {task_id}")
            success = service.update_task_description(task_id, description)
            if success:
                updated += 1
                state["processed_sessions"][summary.session_id] = {
                    "processed_at": datetime.utcnow().isoformat() + "Z",
                    "todoist_task_id": task_id,
                    "task_title": title,
                }
        else:
            # Create new task
            logger.info(f"Creating new task for [{app_name}]")
            task = service.create_task(
                content=title,
                project_id=project_id,
                description=description,
            )
            created += 1
            state["processed_sessions"][summary.session_id] = {
                "processed_at": datetime.utcnow().isoformat() + "Z",
                "todoist_task_id": task["id"],
                "task_title": title,
            }

    # 8. Save state
    save_state(state)

    # Print summary
    print(f"\n{'=' * 60}")
    print("CC SESSION TRACKER SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Sessions discovered: {len(all_sessions)}")
    print(f"  Sessions parsed: {len(summaries)}")
    print(f"  Unique apps: {len(app_groups)}")
    print(f"  Tasks created: {created}")
    print(f"  Tasks updated: {updated}")
    print(f"  Todoist project: {project_name}")
    print(f"{'=' * 60}\n")

    return {
        "sessions_found": len(all_sessions),
        "tasks_created": created,
        "tasks_updated": updated,
    }


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CC Session Tracker - Track incomplete Claude Code sessions in Todoist"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate setup and config"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Scan sessions and create/update Todoist tasks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan sessions and show what would be created (no API writes)",
    )
    args = parser.parse_args()

    setup_logging()
    load_environment()
    config = load_config()

    if args.validate:
        sys.exit(0 if validate_setup(config) else 1)
    elif args.generate:
        run_tracker(config, dry_run=False)
    elif args.dry_run:
        run_tracker(config, dry_run=True)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python src/tracker_main.py --validate")
        print("  python src/tracker_main.py --dry-run")
        print("  python src/tracker_main.py --generate")


if __name__ == "__main__":
    main()
