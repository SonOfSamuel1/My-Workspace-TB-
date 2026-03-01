#!/usr/bin/env python3
"""Generate docs/APP_CATALOG.md and docs/app-catalog.html from apps/ metadata.

Scans all application directories, extracts metadata (language, dependencies,
deployment target, integrations), and produces a living catalog document in
both Markdown and self-contained HTML formats.

Usage:
    python3 scripts/generate_app_catalog.py
"""

import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Resolve paths relative to repo root (parent of scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent
APPS_DIR = REPO_ROOT / "apps"
OUTPUT_FILE = REPO_ROOT / "docs" / "APP_CATALOG.md"
HTML_OUTPUT_FILE = REPO_ROOT / "docs" / "app-catalog.html"

# Directories to skip when counting source files
SKIP_DIRS = {
    "node_modules",
    "dist",
    "build",
    ".next",
    "__pycache__",
    "deployment",
    ".git",
    "venv",
    ".venv",
    "lambda_build",
    "output",
}

# Map dependency patterns to integration labels
INTEGRATION_MAP = {
    "google-api-python-client": "Google APIs",
    "google-auth": "Google Auth",
    "googleapis": "Google APIs",
    "boto3": "AWS",
    "@aws-sdk": "AWS",
    "requests": "HTTP/REST",
    "flask": "Flask Web Server",
    "twilio": "Twilio SMS",
    "feedparser": "RSS Feeds",
    "beautifulsoup4": "Web Scraping",
    "anthropic": "Claude AI",
    "openai": "OpenAI",
    "playwright": "Browser Automation",
    "next": "Next.js",
    "react": "React",
    "tailwindcss": "Tailwind CSS",
    "zustand": "Zustand State",
    "rich": "Rich CLI",
    "click": "Click CLI",
    "jinja2": "Jinja2 Templates",
    "pyotp": "TOTP/2FA",
}


# Claude Code sessions directory
SESSIONS_PROJECT_DIR = (
    Path.home()
    / ".claude"
    / "projects"
    / "-Users-terrancebrandon-Desktop-Code-Projects--Official-"
    "-My-Workspace-My-Workspace-TB--My-Workspace-TB-"
)


def read_file_safe(path):
    """Read a file, returning empty string on failure."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


def get_last_git_activity(app_dir):
    """Get last commit date for an app directory via git log."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", str(app_dir)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:10]  # YYYY-MM-DD
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


def scan_sessions():
    """Scan Claude Code session JSONL files and extract metadata.

    Returns a list of dicts with id, slug, timestamp, first_msg, and
    a Counter of apps/<name> references found in the first ~80 lines.
    """
    if not SESSIONS_PROJECT_DIR.exists():
        return []

    sessions = []
    for sf in sorted(SESSIONS_PROJECT_DIR.glob("*.jsonl")):
        session_id = sf.stem
        slug = ""
        first_ts = ""
        first_msg = ""
        app_refs = Counter()

        try:
            with open(sf, encoding="utf-8", errors="replace") as f:
                lines_read = 0
                for line in f:
                    lines_read += 1
                    if lines_read > 80:
                        break

                    # Quick regex for app references
                    for m in re.findall(r"apps/([a-zA-Z0-9_-]+)", line):
                        if m not in ("CLAUDE", "__pycache__"):
                            app_refs[m] += 1

                    # Extract first user message metadata
                    if not first_ts and '"type":"user"' in line:
                        try:
                            obj = json.loads(line)
                            if obj.get("type") == "user":
                                slug = obj.get("slug", "")
                                first_ts = obj.get("timestamp", "")
                                content = obj.get("message", {}).get("content", "")
                                if isinstance(content, str):
                                    first_msg = content[:500]
                                elif isinstance(content, list):
                                    for c in content:
                                        if (
                                            isinstance(c, dict)
                                            and c.get("type") == "text"
                                        ):
                                            first_msg = c["text"][:500]
                                            break
                        except (json.JSONDecodeError, KeyError):
                            pass
        except OSError:
            continue

        if first_ts:
            sessions.append(
                {
                    "id": session_id,
                    "slug": slug,
                    "timestamp": first_ts,
                    "first_msg": first_msg,
                    "app_refs": app_refs,
                }
            )

    return sessions


def match_sessions_to_app(app_name, sessions):
    """Find sessions related to a specific app, ranked by relevance.

    A session is related if:
    - The app name appears in the first user message (primary), OR
    - The app is referenced significantly more than other apps in the session
      (focused work, not exploration)
    """
    related = []
    for s in sessions:
        ref_count = s["app_refs"].get(app_name, 0)
        total_unique_apps = len(s["app_refs"])

        in_first_msg = (
            app_name.lower().replace("-", " ")
            in s["first_msg"].lower().replace("-", " ")
            or app_name.lower() in s["first_msg"].lower()
        )

        # Skip sessions that broadly scan many apps (exploration/catalog runs)
        if total_unique_apps > 8 and not in_first_msg:
            continue

        # For tool-ref-only matches, require the app to be a dominant reference
        if not in_first_msg:
            if ref_count < 5:
                continue
            # App should be among the top-referenced in this session
            max_refs = max(s["app_refs"].values()) if s["app_refs"] else 0
            if ref_count < max_refs * 0.3:
                continue

        msg = s["first_msg"]
        # Extract plan/task title if present
        title_match = re.search(r"#\s+(?:Plan:\s*)?(.+)", msg)
        if title_match:
            summary = title_match.group(1).strip()[:100]
        else:
            summary = re.sub(r"<[^>]+>.*?</[^>]+>", "", msg)[:100].strip()
            if not summary:
                summary = f"Session {s['slug']}" if s["slug"] else s["id"][:12]

        related.append(
            {
                "id": s["id"],
                "slug": s["slug"],
                "date": s["timestamp"][:10],
                "summary": summary,
                "relevance": "primary" if in_first_msg else "related",
            }
        )

    # Deduplicate by id, sort by date descending
    seen = set()
    deduped = []
    for r in related:
        if r["id"] not in seen:
            seen.add(r["id"])
            deduped.append(r)
    deduped.sort(key=lambda x: x["date"], reverse=True)
    return deduped


def _is_real_description(text):
    """Check if extracted text looks like an actual description vs metadata."""
    noise_patterns = [
        r"^←",  # navigation links
        r"^(Created|Last Updated|Version):",  # metadata
        r"^(See|Note:?\s)",  # notes / see-also
        r"^\|",  # table rows
        r"^-\s+(Never|Store|Gmail)",  # security notes
        r"^(Built with|Powered by)",  # badge lines
        r"^(Terrance|Brandon)",  # author name
        r"^(See repository|For issues)",  # boilerplate
        r"^(text\s+--)",  # CLI usage accidentally captured
        r"^\d+\.",  # numbered lists
    ]
    for pattern in noise_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    # Too short to be a real description
    if len(text) < 15:
        return False
    return True


def _clean_markdown(text):
    """Strip markdown formatting from text."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)  # images
    text = re.sub(r"[*_`]", "", text)  # bold/italic/code
    text = re.sub(r"<[^>]+>", "", text)  # HTML tags
    text = " ".join(text.split())  # collapse whitespace
    return text.strip()


def extract_readme_description(app_dir):
    """Extract a meaningful description from README.md.

    Tries the first paragraph after H1, then scans subsequent paragraphs
    and common sections (Overview, About, Description) for real content.
    """
    readme = app_dir / "README.md"
    if not readme.exists():
        return ""
    text = read_file_safe(readme)

    # Strategy 1: First paragraph after H1
    # Use [^\n]+ for heading to avoid DOTALL matching across lines
    match = re.search(
        r"^#\s+[^\n]+\n\n(.+?)(?:\n\n|\n#|\Z)", text, re.MULTILINE | re.DOTALL
    )
    if match:
        candidate = _clean_markdown(match.group(1))
        if _is_real_description(candidate):
            if len(candidate) > 200:
                candidate = candidate[:197] + "..."
            return candidate

    # Strategy 2: Look for Overview/About/Description sections
    section_match = re.search(
        r"^##\s+(?:Overview|About|Description|What)[^\n]*\n\n(.+?)(?:\n\n|\n#|\Z)",
        text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if section_match:
        candidate = _clean_markdown(section_match.group(1))
        if _is_real_description(candidate):
            if len(candidate) > 200:
                candidate = candidate[:197] + "..."
            return candidate

    # Strategy 3: Look for Features section and summarize
    features_match = re.search(
        r"^##\s+(?:Features|Key Features)[^\n]*\n\n(.+?)(?:\n\n\n|\n##|\Z)",
        text,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if features_match:
        raw = features_match.group(1).strip()
        # Extract first 3 bullet items
        bullets = re.findall(r"^[-*]\s+(.+)", raw, re.MULTILINE)
        if bullets:
            summary = "; ".join(_clean_markdown(b) for b in bullets[:3])
            if len(summary) > 200:
                summary = summary[:197] + "..."
            return summary

    # Strategy 4: Scan all paragraphs after H1 for first real one
    after_h1 = re.split(r"^#\s+[^\n]+\n", text, maxsplit=1, flags=re.MULTILINE)
    if len(after_h1) > 1:
        paragraphs = re.split(r"\n\n+", after_h1[1])
        for para in paragraphs[:6]:
            candidate = _clean_markdown(para)
            if _is_real_description(candidate) and not candidate.startswith("#"):
                if len(candidate) > 200:
                    candidate = candidate[:197] + "..."
                return candidate

    return ""


def extract_package_json_description(app_dir):
    """Extract description from package.json."""
    pkg = app_dir / "package.json"
    if not pkg.exists():
        return ""
    try:
        data = json.loads(read_file_safe(pkg))
        return data.get("description", "")
    except (json.JSONDecodeError, AttributeError):
        return ""


def extract_config_yaml_description(app_dir):
    """Extract description from config.yaml using regex (no PyYAML needed)."""
    for name in ("config.yaml", "config.yml"):
        cfg = app_dir / name
        if cfg.exists():
            text = read_file_safe(cfg)
            match = re.search(
                r"^description:\s*[\"']?(.+?)[\"']?\s*$", text, re.MULTILINE
            )
            if match:
                return match.group(1).strip()
    return ""


def get_description(app_dir):
    """Get app description from best available source."""
    desc = extract_readme_description(app_dir)
    if not desc:
        desc = extract_package_json_description(app_dir)
    if not desc:
        desc = extract_config_yaml_description(app_dir)
    if not desc:
        # Generate from app name
        name = app_dir.name.replace("-", " ").replace("_", " ").title()
        desc = f"{name} application"
    return desc


def get_short_description(desc):
    """Get a one-line summary suitable for the table."""
    # Take first sentence
    match = re.match(r"(.+?[.!])\s", desc)
    if match:
        short = match.group(1)
    else:
        short = desc
    if len(short) > 80:
        short = short[:77] + "..."
    return short


def detect_language(app_dir):
    """Detect primary language from project files."""
    has_python = (app_dir / "requirements.txt").exists() or any(
        (app_dir / "src").glob("*.py") if (app_dir / "src").exists() else []
    )
    has_node = (app_dir / "package.json").exists()
    has_ts = (app_dir / "tsconfig.json").exists()

    if has_ts:
        return "TypeScript"
    if has_python and has_node:
        return "Python/Node.js"
    if has_node:
        return "Node.js"
    if has_python:
        return "Python"
    # Check for any .py files at top level
    if list(app_dir.glob("*.py")) or list(app_dir.glob("src/*.py")):
        return "Python"
    return "Unknown"


def detect_deployment(app_dir):
    """Detect deployment target."""
    # Check for Vercel
    if (app_dir / "vercel.json").exists():
        return "Vercel"
    # Check for serverless
    if (app_dir / "serverless.yml").exists() or (app_dir / "serverless.yaml").exists():
        return "Serverless"
    # Check for Lambda handler
    for handler in [
        "lambda_handler.py",
        "lambda_handler.js",
        "src/lambda_handler.py",
        "src/lambda_handler.js",
    ]:
        if (app_dir / handler).exists():
            return "AWS Lambda"
    # Check for deploy scripts mentioning lambda
    for script in app_dir.glob("scripts/deploy*"):
        if "lambda" in script.name.lower():
            return "AWS Lambda"
    if (app_dir / "deploy_lambda.sh").exists():
        return "AWS Lambda"
    # Check for Dockerfile
    if (app_dir / "Dockerfile").exists() or (app_dir / "Dockerfile.lambda").exists():
        return "Docker/Lambda"
    # Check for deploy scripts (generic)
    if list(app_dir.glob("scripts/deploy*")) or list(app_dir.glob("deploy*.sh")):
        return "Script Deploy"
    return "Local"


def find_entry_points(app_dir):
    """Find main entry point files."""
    patterns = [
        "src/*_main.py",
        "src/main.py",
        "src/index.js",
        "src/index.ts",
        "lambda_handler.py",
        "lambda_handler.js",
        "src/lambda_handler.py",
    ]
    found = []
    for pattern in patterns:
        for f in app_dir.glob(pattern):
            found.append(str(f.relative_to(app_dir)))
    return sorted(set(found))


def get_dependencies(app_dir):
    """Extract key dependency names."""
    deps = []

    # Python requirements.txt
    req = app_dir / "requirements.txt"
    if req.exists():
        for line in read_file_safe(req).splitlines():
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                name = re.split(r"[>=<!\[]", line)[0].strip()
                if name:
                    deps.append(name)

    # Node package.json
    pkg = app_dir / "package.json"
    if pkg.exists():
        try:
            data = json.loads(read_file_safe(pkg))
            for key in ("dependencies", "devDependencies"):
                if key in data and isinstance(data[key], dict):
                    deps.extend(data[key].keys())
        except (json.JSONDecodeError, AttributeError):
            pass

    return deps


def detect_integrations(deps):
    """Map dependencies to human-readable integration names."""
    integrations = set()
    for dep in deps:
        dep_lower = dep.lower()
        for pattern, label in INTEGRATION_MAP.items():
            if pattern.lower() in dep_lower:
                integrations.add(label)
        # Special cases from dep names
        if "ynab" in dep_lower:
            integrations.add("YNAB")
        if "todoist" in dep_lower:
            integrations.add("Todoist")
        if "toggl" in dep_lower:
            integrations.add("Toggl")
    return sorted(integrations)


def count_source_files(app_dir):
    """Count source files in src/, excluding skip dirs."""
    src_dir = app_dir / "src"
    if not src_dir.exists():
        return 0
    count = 0
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".tsx", ".jsx")):
                count += 1
    return count


def find_config_files(app_dir):
    """List configuration files present."""
    configs = []
    checks = [
        ".env",
        ".env.example",
        "config.yaml",
        "config.yml",
        "vercel.json",
        "serverless.yml",
        "tsconfig.json",
        "Dockerfile",
        "Dockerfile.lambda",
    ]
    for name in checks:
        if (app_dir / name).exists():
            configs.append(name)
    return configs


def gather_app_metadata(app_dir, sessions=None):
    """Collect all metadata for a single app."""
    deps = get_dependencies(app_dir)
    app_name = app_dir.name
    related = match_sessions_to_app(app_name, sessions) if sessions else []
    return {
        "name": app_name,
        "description": get_description(app_dir),
        "language": detect_language(app_dir),
        "deployment": detect_deployment(app_dir),
        "entry_points": find_entry_points(app_dir),
        "dependencies": deps,
        "integrations": detect_integrations(deps),
        "source_file_count": count_source_files(app_dir),
        "config_files": find_config_files(app_dir),
        "has_readme": (app_dir / "README.md").exists(),
        "has_tests": (app_dir / "tests").exists()
        or (app_dir / "test").exists()
        or (app_dir / "__tests__").exists(),
        "last_updated": get_last_git_activity(app_dir),
        "sessions": related,
    }


def generate_catalog_markdown(apps, now):
    """Generate the catalog markdown from pre-gathered app metadata."""
    lines = []
    lines.append("# Application Catalog")
    lines.append("")
    lines.append(f"> Auto-generated on {now} | {len(apps)} applications")
    lines.append(">")
    lines.append(
        "> Regenerate: `npm run catalog` or `python3 scripts/generate_app_catalog.py`"
    )
    lines.append("")

    # --- Quick Reference Table ---
    lines.append("## Quick Reference")
    lines.append("")
    lines.append("| App | Language | Deployment | Last Updated | Description |")
    lines.append("|-----|----------|------------|-------------|-------------|")
    for app in apps:
        short_desc = get_short_description(app["description"])
        updated = app.get("last_updated", "")
        lines.append(
            f"| [{app['name']}](#{app['name']}) | {app['language']} "
            f"| {app['deployment']} | {updated} | {short_desc} |"
        )
    lines.append("")

    # --- Stats Summary ---
    lang_counts = {}
    deploy_counts = {}
    readme_count = sum(1 for a in apps if a["has_readme"])
    for app in apps:
        lang_counts[app["language"]] = lang_counts.get(app["language"], 0) + 1
        deploy_counts[app["deployment"]] = deploy_counts.get(app["deployment"], 0) + 1

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total apps**: {len(apps)}")
    lines.append(
        f"- **Languages**: {', '.join(f'{lang} ({n})' for lang, n in sorted(lang_counts.items()))}"
    )
    lines.append(
        f"- **Deployment**: {', '.join(f'{d} ({n})' for d, n in sorted(deploy_counts.items()))}"
    )
    lines.append(f"- **With README**: {readme_count}/{len(apps)}")
    lines.append("")

    # --- Detailed Entries ---
    lines.append("## Detailed Entries")
    lines.append("")

    for app in apps:
        lines.append(f"### {app['name']}")
        lines.append("")
        lines.append(f"**{app['description']}**")
        lines.append("")
        lines.append("| | |")
        lines.append("|---|---|")
        lines.append(f"| **Language** | {app['language']} |")
        lines.append(f"| **Deployment** | {app['deployment']} |")
        if app.get("last_updated"):
            lines.append(f"| **Last Updated** | {app['last_updated']} |")
        if app["entry_points"]:
            lines.append(f"| **Entry Points** | `{'`, `'.join(app['entry_points'])}` |")
        if app["integrations"]:
            lines.append(f"| **Integrations** | {', '.join(app['integrations'])} |")
        lines.append(f"| **Source Files** | {app['source_file_count']} |")
        if app["config_files"]:
            lines.append(f"| **Config Files** | `{'`, `'.join(app['config_files'])}` |")
        lines.append(f"| **Has README** | {'Yes' if app['has_readme'] else 'No'} |")
        lines.append(f"| **Has Tests** | {'Yes' if app['has_tests'] else 'No'} |")

        if app["dependencies"]:
            # Show top 10 deps
            shown = app["dependencies"][:10]
            remaining = len(app["dependencies"]) - len(shown)
            dep_str = ", ".join(f"`{d}`" for d in shown)
            if remaining > 0:
                dep_str += f" + {remaining} more"
            lines.append("")
            lines.append(f"**Key Dependencies**: {dep_str}")

        if app.get("sessions"):
            lines.append("")
            lines.append(f"**Claude Code Sessions** ({len(app['sessions'])} sessions):")
            for sess in app["sessions"]:
                lines.append(
                    f"- `{sess['date']}` — {sess['summary']} "
                    f"(`claude --resume {sess['id']}`)"
                )

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _html_escape(text):
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_html_catalog(apps, timestamp):
    """Build a self-contained HTML page from app metadata."""

    # Compute stats
    lang_counts = {}
    deploy_counts = {}
    readme_count = sum(1 for a in apps if a["has_readme"])
    test_count = sum(1 for a in apps if a["has_tests"])
    for app in apps:
        lang_counts[app["language"]] = lang_counts.get(app["language"], 0) + 1
        deploy_counts[app["deployment"]] = deploy_counts.get(app["deployment"], 0) + 1

    # Unique languages and deployments for filter buttons
    all_languages = sorted(lang_counts.keys())
    all_deployments = sorted(deploy_counts.keys())

    # Build card HTML for each app
    cards_html = ""
    for app in apps:
        e = _html_escape
        dep_items = ""
        if app["dependencies"]:
            dep_items = "".join(
                f"<span class='dep-tag'>{e(d)}</span>" for d in app["dependencies"]
            )

        integration_pills = "".join(
            f"<span class='integration-pill'>{e(i)}</span>" for i in app["integrations"]
        )

        entry_points_html = "".join(
            f"<code class='entry-point'>{e(ep)}</code>" for ep in app["entry_points"]
        )

        lang_class = (
            app["language"].lower().replace("/", "-").replace(".", "").replace(" ", "-")
        )
        deploy_class = app["deployment"].lower().replace("/", "-").replace(" ", "-")

        # Sessions HTML
        sessions_html = ""
        if app.get("sessions"):
            session_items = ""
            for sess in app["sessions"]:
                sid = e(sess["id"])
                summary = e(sess["summary"])
                date = e(sess["date"])
                relevance_class = (
                    "primary" if sess["relevance"] == "primary" else "related"
                )
                session_items += (
                    f'<div class="session-item {relevance_class}">'
                    f'<span class="session-date">{date}</span>'
                    f'<span class="session-summary">{summary}</span>'
                    f'<button class="copy-btn" data-sid="{sid}" title="Copy resume command">'
                    f"&#x2398;</button></div>"
                )
            sessions_html = (
                f'<details class="sessions-section">'
                f'<summary>Claude Code Sessions ({len(app["sessions"])})</summary>'
                f'<div class="sessions-wrap">{session_items}</div></details>'
            )

        last_updated = app.get("last_updated", "")
        updated_html = (
            f'<div class="meta-row"><span class="meta-label">Last Updated</span>'
            f'<span class="last-updated">{e(last_updated)}</span></div>'
            if last_updated
            else ""
        )

        cards_html += f"""
    <div class="card" data-language="{e(app['language'])}" data-deployment="{e(app['deployment'])}"
         data-search="{e(app['name'])} {e(app['description'])} {e(' '.join(app['integrations']))}">
      <div class="card-header">
        <h2 class="card-title">{e(app['name'])}</h2>
        <div class="card-badges">
          <span class="badge lang-{lang_class}">{e(app['language'])}</span>
          <span class="badge deploy-{deploy_class}">{e(app['deployment'])}</span>
        </div>
      </div>
      <p class="card-desc">{e(app['description'])}</p>
      <div class="card-meta">
        {updated_html}
        {f'<div class="meta-row"><span class="meta-label">Integrations</span><div class="pills-wrap">{integration_pills}</div></div>' if integration_pills else ''}  # noqa: E501
        {f'<div class="meta-row"><span class="meta-label">Entry Points</span><div class="entry-wrap">{entry_points_html}</div></div>' if entry_points_html else ''}  # noqa: E501
        <div class="meta-row">
          <span class="meta-label">Source Files</span><span>{app['source_file_count']}</span>
          <span class="indicator {'yes' if app['has_readme'] else 'no'}">{'&#10003; README' if app['has_readme'] else '&#10007; README'}</span>  # noqa: E501
          <span class="indicator {'yes' if app['has_tests'] else 'no'}">{'&#10003; Tests' if app['has_tests'] else '&#10007; Tests'}</span>  # noqa: E501
        </div>
      </div>
      {f'<details class="deps-section"><summary>Dependencies ({len(app["dependencies"])})</summary><div class="deps-wrap">{dep_items}</div></details>' if dep_items else ''}  # noqa: E501
      {sessions_html}
    </div>"""

    # Build stat pills
    lang_pills = "".join(
        f"<span class='stat-pill'>{_html_escape(lang_name)}: {c}</span>"
        for lang_name, c in sorted(lang_counts.items())
    )
    deploy_pills = "".join(
        f"<span class='stat-pill'>{_html_escape(d)}: {c}</span>"
        for d, c in sorted(deploy_counts.items())
    )

    # Language filter buttons
    lang_buttons = '<button class="filter-btn active" data-filter-type="language" data-value="all">All</button>'
    for lang in all_languages:
        lang_buttons += f'<button class="filter-btn" data-filter-type="language" data-value="{_html_escape(lang)}">{_html_escape(lang)}</button>'  # noqa: E501

    deploy_buttons = '<button class="filter-btn active" data-filter-type="deployment" data-value="all">All</button>'
    for dep in all_deployments:
        deploy_buttons += f'<button class="filter-btn" data-filter-type="deployment" data-value="{_html_escape(dep)}">{_html_escape(dep)}</button>'  # noqa: E501

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>App Catalog — My Workspace</title>
<style>
:root {{
  --bg: #f8f9fa; --surface: #ffffff; --text: #1a1a2e; --text-muted: #6c757d;
  --border: #dee2e6; --accent: #4361ee; --accent-hover: #3a56d4;
  --card-shadow: 0 1px 3px rgba(0,0,0,0.08); --card-hover: 0 4px 12px rgba(0,0,0,0.12);
  --search-bg: #ffffff; --badge-text: #fff;
}}
@media (prefers-color-scheme: dark) {{
  :root:not(.light) {{
    --bg: #0d1117; --surface: #161b22; --text: #e6edf3; --text-muted: #8b949e;
    --border: #30363d; --accent: #58a6ff; --accent-hover: #79b8ff;
    --card-shadow: 0 1px 3px rgba(0,0,0,0.3); --card-hover: 0 4px 12px rgba(0,0,0,0.4);
    --search-bg: #0d1117;
  }}
}}
:root.dark {{
  --bg: #0d1117; --surface: #161b22; --text: #e6edf3; --text-muted: #8b949e;
  --border: #30363d; --accent: #58a6ff; --accent-hover: #79b8ff;
  --card-shadow: 0 1px 3px rgba(0,0,0,0.3); --card-hover: 0 4px 12px rgba(0,0,0,0.4);
  --search-bg: #0d1117;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.5; }}
.container {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}
header {{ text-align: center; margin-bottom: 32px; }}
header h1 {{ font-size: 2rem; margin-bottom: 4px; }}
header .subtitle {{ color: var(--text-muted); font-size: 0.95rem; }}
.theme-toggle {{ position: fixed; top: 16px; right: 16px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 8px; padding: 6px 12px; cursor: pointer;
  color: var(--text); font-size: 0.85rem; z-index: 10; }}
.theme-toggle:hover {{ border-color: var(--accent); }}

.stats-bar {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;
  margin-bottom: 24px; }}
.stat-pill {{ background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
  padding: 4px 14px; font-size: 0.82rem; color: var(--text-muted); white-space: nowrap; }}

.controls {{ margin-bottom: 24px; }}
.search-box {{ width: 100%; padding: 10px 16px; font-size: 1rem; border: 1px solid var(--border);
  border-radius: 8px; background: var(--search-bg); color: var(--text); margin-bottom: 12px; }}
.search-box:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(67,97,238,0.15); }}
.filter-row {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 8px; }}
.filter-label {{ font-size: 0.82rem; color: var(--text-muted); font-weight: 600; margin-right: 4px; }}
.filter-btn {{ background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
  padding: 4px 12px; font-size: 0.82rem; cursor: pointer; color: var(--text); transition: all 0.15s; }}
.filter-btn:hover {{ border-color: var(--accent); }}
.filter-btn.active {{ background: var(--accent); color: var(--badge-text); border-color: var(--accent); }}

.grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
@media (max-width: 1024px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
@media (max-width: 640px) {{ .grid {{ grid-template-columns: 1fr; }} }}

.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  padding: 20px; box-shadow: var(--card-shadow); transition: box-shadow 0.2s, transform 0.2s; }}
.card:hover {{ box-shadow: var(--card-hover); transform: translateY(-2px); }}
.card.hidden {{ display: none; }}
.card-header {{ display: flex; justify-content: space-between; align-items: flex-start;
  flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }}
.card-title {{ font-size: 1.05rem; font-weight: 700; word-break: break-word; }}
.card-badges {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.badge {{ padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; color: var(--badge-text); }}
.lang-python {{ background: #3572A5; }} .lang-node\\.js,.lang-nodejs {{ background: #339933; }}
.lang-typescript {{ background: #4338ca; }} .lang-python\\/node\\.js,.lang-python-nodejs {{ background: #6366f1; }}
.lang-unknown {{ background: #6b7280; }}
.deploy-aws-lambda {{ background: #e67e22; }} .deploy-vercel {{ background: #111; }}
.deploy-local {{ background: #6b7280; }} .deploy-serverless {{ background: #7c3aed; }}
.deploy-script-deploy {{ background: #4b5563; }} .deploy-docker\\/lambda,.deploy-docker-lambda {{ background: #d97706; }}
.card-desc {{ color: var(--text-muted); font-size: 0.88rem; margin-bottom: 12px;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
.card-meta {{ font-size: 0.82rem; }}
.meta-row {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 6px; }}
.meta-label {{ font-weight: 600; min-width: 90px; }}
.pills-wrap {{ display: flex; flex-wrap: wrap; gap: 4px; }}
.integration-pill {{ background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
  padding: 1px 8px; font-size: 0.75rem; white-space: nowrap; }}
.entry-wrap {{ display: flex; flex-wrap: wrap; gap: 4px; }}
code.entry-point {{ background: var(--bg); border: 1px solid var(--border); padding: 1px 6px;
  border-radius: 4px; font-size: 0.78rem; }}
.indicator {{ font-size: 0.78rem; margin-left: 6px; }}
.indicator.yes {{ color: #22c55e; }} .indicator.no {{ color: #ef4444; }}

.deps-section {{ margin-top: 10px; font-size: 0.82rem; }}
.deps-section summary {{ cursor: pointer; color: var(--text-muted); user-select: none; }}
.deps-section summary:hover {{ color: var(--accent); }}
.deps-wrap {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }}
.dep-tag {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 1px 7px; font-size: 0.73rem; font-family: monospace; }}

.sessions-section {{ margin-top: 10px; font-size: 0.82rem; }}
.sessions-section summary {{ cursor: pointer; color: var(--text-muted); user-select: none; }}
.sessions-section summary:hover {{ color: var(--accent); }}
.sessions-wrap {{ margin-top: 6px; }}
.session-item {{ display: flex; align-items: center; gap: 8px; padding: 4px 0;
  border-bottom: 1px solid var(--border); }}
.session-item:last-child {{ border-bottom: none; }}
.session-date {{ font-family: monospace; font-size: 0.75rem; color: var(--text-muted);
  white-space: nowrap; min-width: 80px; }}
.session-summary {{ flex: 1; font-size: 0.78rem; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; }}
.session-item.primary .session-summary {{ font-weight: 600; }}
.copy-btn {{ background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
  cursor: pointer; padding: 2px 6px; font-size: 0.72rem; color: var(--text-muted);
  flex-shrink: 0; transition: all 0.15s; }}
.copy-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
.copy-btn.copied {{ background: #22c55e; color: #fff; border-color: #22c55e; }}
.last-updated {{ font-weight: 600; color: var(--text); }}

.no-results {{ text-align: center; padding: 48px 16px; color: var(--text-muted); display: none; }}
footer {{ text-align: center; margin-top: 40px; padding: 16px; color: var(--text-muted); font-size: 0.82rem; }}
</style>
</head>
<body>
<button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">&#9790; / &#9728;</button>
<div class="container">
  <header>
    <h1>Application Catalog</h1>
    <p class="subtitle">{len(apps)} apps &middot; Generated {_html_escape(timestamp)}</p>
  </header>

  <div class="stats-bar">
    <span class="stat-pill"><strong>Languages:</strong></span>{lang_pills}
    <span class="stat-pill"><strong>Deployment:</strong></span>{deploy_pills}
    <span class="stat-pill">README: {readme_count}/{len(apps)}</span>
    <span class="stat-pill">Tests: {test_count}/{len(apps)}</span>
  </div>

  <div class="controls">
    <input type="text" class="search-box" id="searchBox" placeholder="Search apps by name, description, or integration&hellip;">  # noqa: E501
    <div class="filter-row">
      <span class="filter-label">Language:</span>
      {lang_buttons}
    </div>
    <div class="filter-row">
      <span class="filter-label">Deploy:</span>
      {deploy_buttons}
    </div>
  </div>

  <div class="grid" id="cardGrid">
    {cards_html}
  </div>

  <div class="no-results" id="noResults">No apps match your filters.</div>

  <footer>
    Regenerate: <code>npm run catalog</code> or <code>python3 scripts/generate_app_catalog.py</code>
  </footer>
</div>

<script>
(function() {{
  // Theme toggle
  const toggle = document.getElementById('themeToggle');
  const root = document.documentElement;
  function setTheme(t) {{ root.className = t; localStorage.setItem('catalog-theme', t); }}
  const saved = localStorage.getItem('catalog-theme');
  if (saved) root.className = saved;
  toggle.addEventListener('click', function() {{
    const isDark = root.classList.contains('dark') ||
      (!root.classList.contains('light') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    setTheme(isDark ? 'light' : 'dark');
  }});

  // Filtering
  const cards = Array.from(document.querySelectorAll('.card'));
  const searchBox = document.getElementById('searchBox');
  const noResults = document.getElementById('noResults');
  let activeLanguage = 'all', activeDeployment = 'all';

  function applyFilters() {{
    const q = searchBox.value.toLowerCase();
    let visible = 0;
    cards.forEach(function(card) {{
      const matchLang = activeLanguage === 'all' || card.dataset.language === activeLanguage;
      const matchDeploy = activeDeployment === 'all' || card.dataset.deployment === activeDeployment;
      const matchSearch = !q || card.dataset.search.toLowerCase().includes(q);
      const show = matchLang && matchDeploy && matchSearch;
      card.classList.toggle('hidden', !show);
      if (show) visible++;
    }});
    noResults.style.display = visible === 0 ? 'block' : 'none';
  }}

  searchBox.addEventListener('input', applyFilters);

  document.querySelectorAll('.filter-btn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      const type = btn.dataset.filterType;
      const value = btn.dataset.value;
      // Update active state in the same row
      btn.parentElement.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
      btn.classList.add('active');
      if (type === 'language') activeLanguage = value;
      else activeDeployment = value;
      applyFilters();
    }});
  }});
  // Copy session resume command
  document.querySelectorAll('.copy-btn').forEach(function(btn) {{
    btn.addEventListener('click', function(ev) {{
      ev.stopPropagation();
      var sid = btn.dataset.sid;
      var cmd = 'claude --resume ' + sid;
      navigator.clipboard.writeText(cmd).then(function() {{
        btn.textContent = '\\u2713';
        btn.classList.add('copied');
        setTimeout(function() {{ btn.innerHTML = '\\u2398'; btn.classList.remove('copied'); }}, 1500);
      }});
    }});
  }});
}})();
</script>
</body>
</html>"""


def main():
    """Generate both Markdown and HTML catalog files."""
    if not APPS_DIR.exists():
        print(f"Error: {APPS_DIR} not found")
        return

    # Scan Claude Code sessions once, shared across all apps
    print("Scanning Claude Code sessions...")
    sessions = scan_sessions()
    print(f"Found {len(sessions)} sessions")

    # Collect app directories
    app_dirs = sorted(
        [d for d in APPS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: d.name,
    )
    apps = [gather_app_metadata(d, sessions) for d in app_dirs]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def strip_timestamp(text):
        """Strip timestamp for idempotency comparison."""
        text = re.sub(
            r"(Auto-generated|Generated)\s+(?:on\s+)?\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+UTC",
            r"\1 [TIMESTAMP]",
            text,
        )
        return text

    # --- Markdown ---
    md_content = generate_catalog_markdown(apps, now)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists():
        existing = read_file_safe(OUTPUT_FILE)
        if strip_timestamp(existing) == strip_timestamp(md_content):
            print(f"No changes detected, {OUTPUT_FILE} is up to date.")
        else:
            OUTPUT_FILE.write_text(md_content, encoding="utf-8")
            print(f"Generated {OUTPUT_FILE} ({len(md_content)} bytes)")
    else:
        OUTPUT_FILE.write_text(md_content, encoding="utf-8")
        print(f"Generated {OUTPUT_FILE} ({len(md_content)} bytes)")

    # --- HTML ---
    html_content = generate_html_catalog(apps, now)
    if HTML_OUTPUT_FILE.exists():
        existing_html = read_file_safe(HTML_OUTPUT_FILE)
        if strip_timestamp(existing_html) == strip_timestamp(html_content):
            print(f"No changes detected, {HTML_OUTPUT_FILE} is up to date.")
        else:
            HTML_OUTPUT_FILE.write_text(html_content, encoding="utf-8")
            print(f"Generated {HTML_OUTPUT_FILE} ({len(html_content)} bytes)")
    else:
        HTML_OUTPUT_FILE.write_text(html_content, encoding="utf-8")
        print(f"Generated {HTML_OUTPUT_FILE} ({len(html_content)} bytes)")


if __name__ == "__main__":
    main()
