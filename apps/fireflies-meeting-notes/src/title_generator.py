"""Generate descriptive meeting titles using Anthropic Claude Haiku."""

import logging
import os

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Generate a concise 3-8 word descriptive title for this meeting. "
    "Return ONLY the title, no quotes, no punctuation at the end."
)


def _sanitize_title(raw: str) -> str:
    """Strip quotes, trailing periods, and enforce 3-8 word bounds."""
    title = raw.strip().strip("\"'").rstrip(".")
    words = title.split()
    if len(words) < 3:
        return ""
    if len(words) > 8:
        title = " ".join(words[:8])
    return title


def generate_title(
    summary_overview: str,
    keywords: list[str],
    fallback_title: str,
) -> str:
    """Generate a descriptive meeting title via Anthropic Claude Haiku.

    Args:
        summary_overview: The meeting summary text.
        keywords: List of meeting keywords.
        fallback_title: Original Fireflies title used if generation fails.

    Returns:
        Descriptive title string (3-8 words), or fallback_title on failure.
    """
    if not summary_overview:
        logger.info("No summary available, using fallback title")
        return fallback_title

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, using fallback title")
        return fallback_title

    user_content = f"Summary: {summary_overview[:500]}"
    if keywords:
        user_content += f"\nKeywords: {', '.join(keywords[:10])}"

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=30,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw_title = message.content[0].text
        title = _sanitize_title(raw_title)

        if title:
            logger.info(f"Generated title: '{title}'")
            return title

        logger.warning(f"Title sanitization failed for '{raw_title}', using fallback")
        return fallback_title

    except Exception as e:
        logger.warning(f"Anthropic title generation failed, using fallback: {e}")
        return fallback_title
