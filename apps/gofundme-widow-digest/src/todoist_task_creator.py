"""Create a Todoist task with the GoFundMe widow digest."""

import requests

TODOIST_API_BASE = "https://api.todoist.com/api/v1"


def create_digest_task(campaigns, todoist_token, config, week_label):
    """Create a single Todoist task containing all campaign links.

    Args:
        campaigns: List of campaign dicts from gofundme_search.
        todoist_token: Todoist API bearer token.
        config: The todoist section of config.yaml.
        week_label: Human-readable week string (e.g. "Mar 1 - Mar 7, 2026").

    Returns:
        The created task dict from the API, or None if no campaigns.
    """
    if not campaigns:
        return None

    headers = {
        "Authorization": f"Bearer {todoist_token}",
        "Content-Type": "application/json",
    }

    project_id = _find_project_id(headers, config.get("project_name", "Inbox"))
    content = f"GoFundMe Widow Digest ({week_label}) - {len(campaigns)} campaigns"
    description = _format_digest(campaigns)

    payload = {
        "content": content,
        "description": description,
        "labels": config.get("labels", []),
        "priority": config.get("priority", 2),
    }
    if project_id:
        payload["project_id"] = project_id

    resp = requests.post(
        f"{TODOIST_API_BASE}/tasks",
        headers=headers,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _find_project_id(headers, project_name):
    """Look up a Todoist project ID by name."""
    resp = requests.get(
        f"{TODOIST_API_BASE}/projects",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    projects = data.get("results", data) if isinstance(data, dict) else data
    for project in projects:
        if project.get("name", "").lower() == project_name.lower():
            return project["id"]
    return None


def _format_digest(campaigns):
    """Format campaigns into a markdown description for the Todoist task."""
    lines = []
    for i, c in enumerate(campaigns, 1):
        location = _format_location(c)
        raised_pct = (c["raised"] / c["goal"] * 100) if c["goal"] > 0 else 0
        lines.append(
            f"{i}. **[{c['title']}]({c['url']})**\n"
            f"   {location} | Goal: ${c['goal']:,.0f} | "
            f"Raised: ${c['raised']:,.0f} ({raised_pct:.0f}%) | "
            f"{c['donation_count']} donations\n"
            f"   {c['description'][:150]}{'...' if len(c['description']) > 150 else ''}"
        )
    return "\n\n".join(lines)


def _format_location(campaign):
    """Format city/state/country into a readable string."""
    parts = []
    if campaign.get("city"):
        parts.append(campaign["city"])
    if campaign.get("state"):
        parts.append(campaign["state"])
    if not parts and campaign.get("country"):
        parts.append(campaign["country"])
    return ", ".join(parts) if parts else "Unknown location"
