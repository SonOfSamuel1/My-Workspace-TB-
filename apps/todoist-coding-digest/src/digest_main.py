#!/usr/bin/env python3
"""Main entry point for Todoist Coding Digest.

Fetches tasks from the Todoist "Claude" project, scores them by value,
and sends a daily HTML digest email via AWS SES.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# Add src to path (index 0 = highest priority for local modules)
sys.path.insert(0, str(Path(__file__).parent))
# Add cc-session-tracker AFTER local src to avoid shadowing todoist_service, etc.
sys.path.append(str(Path(__file__).parent.parent.parent / "cc-session-tracker" / "src"))

from email_report import build_html_only, send_digest  # noqa: E402
from todoist_service import TodoistService  # noqa: E402
from value_scorer import score_and_sort  # noqa: E402

try:
    from session_scanner import discover_all_sessions
    from session_summarizer import parse_session

    HAS_SESSION_TRACKER = True
except ImportError:
    HAS_SESSION_TRACKER = False

logger = logging.getLogger(__name__)


def setup_logging():
    """Setup logging to stdout + file."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "coding_digest.log"),
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


def validate_setup(config: dict) -> bool:
    """Validate that all services are properly configured."""
    print("\n" + "=" * 60)
    print("TODOIST CODING DIGEST - SETUP VALIDATION")
    print("=" * 60 + "\n")

    digest_config = config.get("coding_digest", {})
    project_name = digest_config.get("project_name", "Claude")

    # Check API token
    api_token = os.getenv("TODOIST_API_TOKEN", "")
    if not api_token:
        print("  API token: MISSING")
        return False
    print("  Todoist API token: present")

    # Check Todoist connection + project
    print(f"\n  Looking up project '{project_name}'...")
    try:
        service = TodoistService(api_token)
        project_id = service.get_project_id_by_name(project_name)
        if not project_id:
            print(f"  Project '{project_name}' not found in Todoist")
            return False
        print(f"  Project found (ID: {project_id})")

        tasks = service.get_all_tasks_in_project(project_id)
        print(f"  Open tasks: {len(tasks)}")
    except Exception as e:
        print(f"  Todoist connection failed: {e}")
        return False

    # Check email config
    recipient = os.getenv("EMAIL_RECIPIENT", "")
    ses_sender = os.getenv("SES_SENDER_EMAIL", "")
    print(f"\n  Email recipient: {'set' if recipient else 'MISSING'}")
    print(f"  SES sender: {'set' if ses_sender else 'MISSING'}")

    if not recipient or not ses_sender:
        print("\n  Email configuration incomplete")
        return False

    print("\n" + "=" * 60)
    print("  ALL VALIDATIONS PASSED")
    print("=" * 60 + "\n")
    return True


def _group_sessions_by_app(summaries: list) -> dict:
    """Keep only the most recent session per app_name.

    Args:
        summaries: List of SessionSummary objects (already sorted newest-first).

    Returns:
        Dict mapping app_name -> dict with session info for the email.
    """
    by_app = {}
    for s in summaries:
        if s.app_name not in by_app:
            by_app[s.app_name] = {
                "session_id": s.session_id,
                "cwd": s.cwd,
                "first_user_message": s.first_user_message,
                "last_timestamp": s.last_timestamp,
                "user_message_count": s.user_message_count,
                "assistant_message_count": s.assistant_message_count,
            }
    return by_app


def run_digest(config: dict, dry_run: bool = False) -> dict:
    """Run the full digest pipeline.

    Returns summary dict with task count and status.
    """
    digest_config = config.get("coding_digest", {})
    project_name = digest_config.get("project_name", "Claude")

    api_token = os.getenv("TODOIST_API_TOKEN", "")
    if not api_token:
        raise ValueError("TODOIST_API_TOKEN not set")

    recipient = os.getenv("EMAIL_RECIPIENT", "")
    ses_sender = os.getenv("SES_SENDER_EMAIL", "")
    ses_region = digest_config.get("ses", {}).get("region", "us-east-1")
    function_url = os.getenv("FUNCTION_URL", "")
    repo_mappings = digest_config.get("repo_mappings", {})

    # 1. Fetch tasks
    logger.info(f"Fetching tasks from project '{project_name}'...")
    service = TodoistService(api_token)
    project_id = service.get_project_id_by_name(project_name)
    if not project_id:
        raise ValueError(f"Project '{project_name}' not found in Todoist")

    tasks = service.get_all_tasks_in_project(project_id)
    logger.info(f"Found {len(tasks)} open tasks")

    # 2. Score and sort
    scored_tasks = score_and_sort(tasks)

    # 2b. Scan open Claude Code sessions (non-fatal)
    sessions_by_app = {}
    if HAS_SESSION_TRACKER:
        try:
            sessions_config = digest_config.get("sessions", {})
            lookback = sessions_config.get("lookback_days", 3)
            min_size = sessions_config.get("min_file_size", 5000)

            raw_sessions = discover_all_sessions(
                lookback_days=lookback, min_file_size=min_size
            )
            summaries = []
            for meta in raw_sessions:
                summary = parse_session(meta)
                if summary:
                    summaries.append(summary)

            sessions_by_app = _group_sessions_by_app(summaries)
            logger.info(f"Found {len(sessions_by_app)} active session(s)")
        except Exception as e:
            logger.warning(f"Session scanning failed (non-fatal): {e}")
            sessions_by_app = {}

    # 3. Build HTML + send or save
    if dry_run:
        html = build_html_only(
            scored_tasks,
            function_url=function_url,
            repo_mappings=repo_mappings,
            sessions=sessions_by_app,
        )
        # Save to output directory
        if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            output_dir = Path("/tmp")
        else:
            output_dir = Path(__file__).parent.parent / "output"
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"coding_digest_{timestamp}.html"
        with open(output_file, "w") as f:
            f.write(html)

        print(f"\n  Dry run complete. Report saved to: {output_file}")
        logger.info(f"Dry run saved to {output_file}")
    else:
        if not recipient or not ses_sender:
            raise ValueError("EMAIL_RECIPIENT and SES_SENDER_EMAIL must be set")

        send_digest(
            scored_tasks,
            recipient=recipient,
            ses_sender=ses_sender,
            ses_region=ses_region,
            function_url=function_url,
            repo_mappings=repo_mappings,
            sessions=sessions_by_app,
        )
        print(f"\n  Digest sent to {recipient} ({len(scored_tasks)} tasks)")

    # Print summary
    print(f"\n{'=' * 60}")
    print("CODING DIGEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total tasks: {len(scored_tasks)}")
    if sessions_by_app:
        print(f"  Open sessions: {len(sessions_by_app)}")
    for task in scored_tasks[:5]:
        s = task["scoring"]
        print(
            f"  [{s['value_label']:6s}] (score: {s['total_score']:3d}) "
            f"{task['content'][:60]}"
        )
    if len(scored_tasks) > 5:
        print(f"  ... and {len(scored_tasks) - 5} more")
    print(f"{'=' * 60}\n")

    return {"task_count": len(scored_tasks), "dry_run": dry_run}


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Todoist Coding Digest - Daily task email"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate setup and config"
    )
    parser.add_argument(
        "--generate", action="store_true", help="Generate and send digest"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate HTML but do not send email",
    )
    args = parser.parse_args()

    setup_logging()
    load_environment()
    config = load_config()

    if args.validate:
        sys.exit(0 if validate_setup(config) else 1)
    elif args.generate:
        run_digest(config, dry_run=False)
    elif args.dry_run:
        run_digest(config, dry_run=True)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python src/digest_main.py --validate")
        print("  python src/digest_main.py --dry-run")
        print("  python src/digest_main.py --generate")


if __name__ == "__main__":
    main()
