#!/usr/bin/env python3
"""
HTML Report Generator for GitHub Trending Report

Generates inline-CSS HTML email reports (no Jinja2 dependency).
600px single-column layout optimized for email client compatibility.
"""
import logging
from datetime import datetime
from typing import Dict
from urllib.parse import quote_plus

import pytz
from github_fetcher import TrendingRepo
from trending_analyzer import ProcessedTrending

logger = logging.getLogger(__name__)

# Language colors matching GitHub's language color scheme
LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "C#": "#178600",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "Scala": "#c22d40",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Lua": "#000080",
    "Zig": "#ec915c",
    "Haskell": "#5e5086",
    "Elixir": "#6e4a7e",
    "Clojure": "#db5855",
    "Jupyter Notebook": "#DA5B0B",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
}


def _get_language_color(language: str) -> str:
    """Get the GitHub color for a programming language."""
    return LANGUAGE_COLORS.get(language, "#8b8b8b")


def _format_number(n: int) -> str:
    """Format a number with K/M suffix for readability."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_repo_card(rank: int, repo: TrendingRepo) -> str:
    """Render a single repo card as an HTML table row."""
    desc = _escape_html(repo.description[:200]) if repo.description else ""
    lang_color = _get_language_color(repo.language or "")
    lang_html = ""
    if repo.language:
        lang_html = (
            f'<span style="display:inline-block;width:12px;height:12px;'
            f"border-radius:50%;background-color:{lang_color};"
            f'vertical-align:middle;margin-right:4px;"></span>'
            f'<span style="color:#586069;font-size:13px;">'
            f"{_escape_html(repo.language)}</span>"
        )

    topics_html = ""
    if repo.topics:
        badges = []
        for topic in repo.topics[:5]:
            badges.append(
                f'<span style="display:inline-block;background:#ddf4ff;'
                f"color:#0969da;font-size:11px;padding:2px 8px;"
                f'border-radius:12px;margin:2px 4px 2px 0;">'
                f"{_escape_html(topic)}</span>"
            )
        topics_html = "".join(badges)

    license_html = ""
    if repo.license_name and repo.license_name != "NOASSERTION":
        license_html = (
            f'<span style="color:#586069;font-size:12px;margin-left:12px;">'
            f"{_escape_html(repo.license_name)}</span>"
        )

    return f"""
    <tr>
      <td style="padding:16px 20px;border-bottom:1px solid #e1e4e8;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="vertical-align:top;width:36px;">
              <span style="display:inline-block;background:#0969da;color:#fff;
                font-size:14px;font-weight:bold;width:28px;height:28px;
                line-height:28px;text-align:center;border-radius:50%;">
                {rank}
              </span>
            </td>
            <td style="vertical-align:top;padding-left:12px;">
              <a href="{repo.html_url}" style="color:#0969da;font-size:16px;
                font-weight:600;text-decoration:none;">
                {_escape_html(repo.full_name)}
              </a>
              <p style="color:#24292f;font-size:14px;margin:6px 0 8px 0;
                line-height:1.5;">
                {desc}
              </p>
              <div style="margin-bottom:4px;">
                {topics_html}
              </div>
              <div style="margin-top:8px;">
                {lang_html}
                <span style="color:#586069;font-size:13px;margin-left:12px;">
                  &#9733; {_format_number(repo.stars)}
                </span>
                <span style="color:#586069;font-size:13px;margin-left:12px;">
                  &#128268; {_format_number(repo.forks)}
                </span>
                {license_html}
              </div>
              <div style="margin-top:10px;">
                <a href="https://www.perplexity.ai/search?q={quote_plus(f"What does the GitHub repo {repo.full_name} do and what is its value? {repo.html_url}")}"  # noqa: E501
                  style="display:inline-block;background:#1a1a2e;color:#ffffff;
                  font-size:12px;font-weight:600;padding:6px 14px;
                  border-radius:6px;text-decoration:none;"
                  target="_blank">
                  Ask Perplexity
                </a>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""


def _render_language_breakdown(language_breakdown: Dict[str, int]) -> str:
    """Render the language breakdown section."""
    if not language_breakdown:
        return ""

    total = sum(language_breakdown.values())
    rows = []
    for lang, count in language_breakdown.items():
        pct = (count / total) * 100
        color = _get_language_color(lang)
        rows.append(
            f"""
            <tr>
              <td style="padding:4px 12px;font-size:13px;">
                <span style="display:inline-block;width:10px;height:10px;
                  border-radius:50%;background-color:{color};
                  vertical-align:middle;margin-right:6px;"></span>
                {_escape_html(lang)}
              </td>
              <td style="padding:4px 12px;font-size:13px;text-align:right;
                color:#586069;">
                {count} repo{"s" if count != 1 else ""} ({pct:.0f}%)
              </td>
            </tr>"""
        )

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
      style="margin-top:8px;">
      {"".join(rows)}
    </table>"""


def generate_html_report(processed: ProcessedTrending) -> str:
    """
    Generate complete HTML email report.

    Args:
        processed: ProcessedTrending object with ranked repos

    Returns:
        Complete HTML string
    """
    logger.info("Generating HTML report...")

    now = datetime.now(pytz.timezone("America/New_York"))
    period_start = processed.period_start.strftime("%B %d")
    period_end = processed.period_end.strftime("%B %d, %Y")

    # Render repo cards
    repo_cards = ""
    for i, repo in enumerate(processed.trending_repos, 1):
        repo_cards += _render_repo_card(i, repo)

    # Render language breakdown
    lang_section = _render_language_breakdown(processed.language_breakdown)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GitHub Weekly Trending</title>
</head>
<body style="margin:0;padding:0;background-color:#f6f8fa;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,
  sans-serif;">

  <!-- Container -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
    style="background-color:#f6f8fa;">
    <tr>
      <td align="center" style="padding:20px 0;">

        <!-- Email body -->
        <table width="600" cellpadding="0" cellspacing="0" border="0"
          style="background-color:#ffffff;border-radius:8px;
          box-shadow:0 1px 3px rgba(0,0,0,0.1);">

          <!-- Header -->
          <tr>
            <td style="background-color:#24292f;padding:28px 24px;
              border-radius:8px 8px 0 0;">
              <h1 style="color:#ffffff;font-size:22px;margin:0;
                font-weight:600;">
                GitHub Weekly Trending
              </h1>
              <p style="color:#8b949e;font-size:14px;margin:8px 0 0 0;">
                Top {len(processed.trending_repos)} trending repositories
                &middot; {period_start} &ndash; {period_end}
              </p>
            </td>
          </tr>

          <!-- Repo list -->
          {repo_cards}

          <!-- Language Breakdown -->
          <tr>
            <td style="padding:20px 24px;border-top:2px solid #e1e4e8;">
              <h2 style="color:#24292f;font-size:16px;margin:0 0 8px 0;
                font-weight:600;">
                Language Breakdown
              </h2>
              {lang_section}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f6f8fa;padding:16px 24px;
              border-radius:0 0 8px 8px;border-top:1px solid #e1e4e8;">
              <p style="color:#8b949e;font-size:12px;margin:0;
                text-align:center;">
                Generated on {now.strftime("%B %d, %Y at %I:%M %p %Z")}
                &middot; Fetched {processed.total_fetched} repos total
              </p>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

</body>
</html>"""

    logger.info(
        f"Report generated: {len(html)} characters, "
        f"{len(processed.trending_repos)} repos"
    )
    return html


def generate_subject(processed: ProcessedTrending) -> str:
    """Generate email subject line."""
    date_str = processed.period_end.strftime("%B %d, %Y")
    return f"GitHub Weekly Trending - {date_str}"


def generate_plain_text(processed: ProcessedTrending) -> str:
    """Generate plain text version of the report."""
    lines = []
    lines.append("GITHUB WEEKLY TRENDING")
    lines.append(
        f"Week of {processed.period_start.strftime('%B %d')} - "
        f"{processed.period_end.strftime('%B %d, %Y')}"
    )
    lines.append("")
    lines.append(f"Top {len(processed.trending_repos)} Trending Repositories")
    lines.append("=" * 60)
    lines.append("")

    for i, repo in enumerate(processed.trending_repos, 1):
        lines.append(f"{i}. {repo.full_name}")
        lines.append(f"   {repo.html_url}")
        stars = _format_number(repo.stars)
        forks = _format_number(repo.forks)
        lang = repo.language or "Unknown"
        lines.append(f"   Stars: {stars} | Forks: {forks} | Language: {lang}")
        if repo.description:
            desc = repo.description[:150]
            lines.append(f"   {desc}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("")
    lines.append("LANGUAGE BREAKDOWN")
    lines.append("-" * 30)
    for lang, count in processed.language_breakdown.items():
        lines.append(f"  {lang}: {count}")

    lines.append("")
    lines.append("=" * 60)
    now = datetime.now(pytz.timezone("America/New_York"))
    lines.append(f"Generated on {now.strftime('%B %d, %Y at %I:%M %p')}")
    lines.append(f"Fetched {processed.total_fetched} repos total")

    return "\n".join(lines)
