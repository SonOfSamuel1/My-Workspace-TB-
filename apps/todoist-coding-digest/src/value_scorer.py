"""Task value scoring engine.

Scores Todoist tasks by monetary/strategic value using:
- Todoist priority (API: 4=urgent, 3=high, 2=medium, 1=normal)
- Keyword scan for value-related terms
- Explicit [$X] monetary tags in content
- Age bonus (1 point/day, capped at 30)
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Todoist API priority mapping (4=urgent/p1, 1=normal/p4)
PRIORITY_SCORES = {4: 100, 3: 70, 2: 40, 1: 10}

VALUE_KEYWORDS = {
    "revenue": 25,
    "client": 20,
    "deadline": 20,
    "security": 15,
    "launch": 25,
    "paid": 25,
    "monetize": 25,
    "deploy": 15,
    "production": 15,
    "bug": 10,
    "fix": 10,
    "urgent": 20,
    "critical": 20,
    "blocker": 20,
    "mvp": 15,
    "demo": 15,
    "contract": 25,
    "invoice": 25,
}

DOLLAR_PATTERN = re.compile(r"\$(\d[\d,]*)")


def _parse_created_date(task: Dict[str, Any]) -> Optional[datetime]:
    """Parse the task created_at timestamp."""
    created = task.get("added_at", "") or task.get("created_at", "")
    if not created:
        return None
    try:
        return datetime.fromisoformat(created.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _extract_dollar_value(text: str) -> Optional[int]:
    """Extract the first dollar amount from text like '$500' or '$1,200'."""
    match = DOLLAR_PATTERN.search(text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def score_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Score a single task and return scoring metadata.

    Returns dict with keys:
        total_score, priority_score, keyword_score, dollar_score,
        age_score, explicit_value, value_label
    """
    content = task.get("content", "")
    description = task.get("description", "")
    searchable = (content + " " + description).lower()

    # Priority score
    api_priority = task.get("priority", 1)
    priority_score = PRIORITY_SCORES.get(api_priority, 10)

    # Keyword score (sum of matched keywords, each counted once)
    keyword_score = 0
    for keyword, points in VALUE_KEYWORDS.items():
        if keyword in searchable:
            keyword_score += points

    # Explicit dollar value
    dollar_value = _extract_dollar_value(content) or _extract_dollar_value(description)
    dollar_score = min(dollar_value, 500) if dollar_value else 0

    # Age bonus
    created_dt = _parse_created_date(task)
    if created_dt:
        age_days = (datetime.now(timezone.utc) - created_dt).days
        age_score = min(age_days, 30)
    else:
        age_days = 0
        age_score = 0

    total_score = priority_score + keyword_score + dollar_score + age_score

    # Value label
    if total_score >= 120:
        value_label = "High"
    elif total_score >= 60:
        value_label = "Medium"
    else:
        value_label = "Low"

    return {
        "total_score": total_score,
        "priority_score": priority_score,
        "keyword_score": keyword_score,
        "dollar_score": dollar_score,
        "age_score": age_score,
        "age_days": age_days,
        "explicit_value": f"${dollar_value:,}" if dollar_value else None,
        "value_label": value_label,
    }


def score_and_sort(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score all tasks and return them sorted by total_score descending.

    Each task dict gets an added 'scoring' key with the scoring metadata.
    """
    scored = []
    for task in tasks:
        task_copy = dict(task)
        task_copy["scoring"] = score_task(task)
        scored.append(task_copy)

    scored.sort(key=lambda t: t["scoring"]["total_score"], reverse=True)
    logger.info(
        f"Scored {len(scored)} tasks. "
        f"High: {sum(1 for t in scored if t['scoring']['value_label'] == 'High')}, "
        f"Medium: {sum(1 for t in scored if t['scoring']['value_label'] == 'Medium')}, "
        f"Low: {sum(1 for t in scored if t['scoring']['value_label'] == 'Low')}"
    )
    return scored
