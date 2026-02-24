#!/usr/bin/env python3
"""
Email Formatter

Builds the daily HTML email with two JT- teachings, each containing:
  - Teaching title
  - Key verse (blockquote styled)
  - 2 reflection questions
"""

import re
import logging
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)


class EmailFormatter:
    """Builds HTML and plain-text versions of the daily teachings email."""

    def format_email(
        self,
        teachings: List[dict],
        date: datetime = None,
    ) -> dict:
        """
        Build the daily email content.

        Args:
            teachings: List of 2 teaching dicts (title, verse, core_content)
            date: Date for the email subject (default: today)

        Returns:
            Dict with keys: subject, html, text
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%B %-d, %Y")
        subject = f"Jesus Teachings Daily \u2014 {date_str}"

        html = self._build_html(teachings, date_str)
        text = self._build_text(teachings, date_str)

        return {
            "subject": subject,
            "html": html,
            "text": text,
        }

    def _build_html(
        self,
        teachings: List[dict],
        date_str: str,
    ) -> str:
        teaching_blocks = ""
        for i, teaching in enumerate(teachings):
            if i > 0:
                teaching_blocks += self._divider()
            teaching_blocks += self._teaching_block_html(i + 1, teaching)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Teachings</title>
  <style>
    body {{
      font-family: Georgia, 'Times New Roman', serif;
      background-color: #f9f7f4;
      color: #2c2c2c;
      margin: 0;
      padding: 0;
    }}
    .wrapper {{
      max-width: 600px;
      margin: 0 auto;
      background-color: #ffffff;
    }}
    .header {{
      background: linear-gradient(160deg, #152912 0%, #1f4020 55%, #2d5522 100%);
      color: #f0e8d0;
      text-align: center;
      padding: 36px 24px 28px;
    }}
    .header h1 {{
      margin: 0 0 6px;
      font-size: 22px;
      font-weight: bold;
      letter-spacing: 1px;
    }}
    .header .date {{
      font-size: 14px;
      color: #c8b88a;
      margin: 0;
    }}
    .body {{
      padding: 32px 36px;
    }}
    .teaching-badge {{
      display: inline-block;
      width: 30px;
      height: 30px;
      border: 2px solid #c8b88a;
      border-radius: 50%;
      color: #c8b88a;
      font-size: 13px;
      font-weight: bold;
      text-align: center;
      line-height: 26px;
      margin-bottom: 10px;
      font-family: Georgia, serif;
    }}
    .teaching-title {{
      font-size: 20px;
      font-weight: bold;
      color: #1a3a1a;
      margin: 0 0 10px;
      line-height: 1.3;
    }}
    .title-rule {{
      width: 48px;
      height: 2px;
      background-color: #c8b88a;
      margin: 0 0 20px;
      border: none;
    }}
    .verse-container {{
      background-color: #fdf9f0;
      border-radius: 4px;
      padding: 20px 24px 16px;
      margin: 0 0 24px;
    }}
    .verse-open-quote {{
      font-size: 48px;
      line-height: 1;
      color: #c8b88a;
      font-family: Georgia, serif;
      margin-bottom: 4px;
    }}
    .verse-body {{
      font-style: italic;
      font-size: 16px;
      line-height: 1.75;
      color: #3a2e1a;
      margin: 0 0 12px;
    }}
    .verse-citation {{
      text-align: right;
      font-size: 13px;
      color: #7a6a4a;
      letter-spacing: 0.5px;
      font-style: normal;
    }}
    .footer {{
      background-color: #f4f0e8;
      text-align: center;
      padding: 18px 24px;
      font-size: 13px;
      color: #7a6a4a;
      border-top: 1px solid #ece8e0;
    }}
    .footer em {{
      font-style: italic;
    }}
    @media only screen and (max-width: 480px) {{
      .body {{ padding: 20px 18px; }}
      .teaching-title {{ font-size: 18px; }}
      .verse-body {{ font-size: 15px; }}
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>Daily Teachings</h1>
      <p class="date">{date_str}</p>
    </div>
    <div class="body">
{teaching_blocks}
    </div>
    <div class="footer">
      <em>Let these words take root and bear fruit today.</em>
    </div>
  </div>
</body>
</html>"""

    def _teaching_block_html(
        self,
        number: int,
        teaching: dict,
    ) -> str:
        title = self._escape_html(teaching.get("title", "Teaching"))
        verse_raw = teaching.get("verse", "")
        verse_html = self._verse_to_html(verse_raw)

        return f"""      <div class="teaching">
        <div class="teaching-badge">{number}</div>
        <h2 class="teaching-title">{title}</h2>
        <div class="title-rule"></div>
        {verse_html}
      </div>
"""

    def _parse_verse_parts(self, verse_text: str) -> Tuple[str, str]:
        """
        Split verse into (reference, body).
        If the first line matches a Bible reference pattern (e.g. 'Luke 6:36 (ESV)'),
        return it as reference. Otherwise reference is empty string.
        Strips surrounding quote characters from body.
        """
        if not verse_text:
            return ("", "")

        lines = verse_text.strip().splitlines()
        ref_pattern = re.compile(
            r"^(?:\d\s+)?[A-Z]\w+(\s\w+)?\s+\d+:\d+[\d\-,\s]*(\s*\(\w+\))?$"
        )

        reference = ""
        body_lines = lines

        if lines and ref_pattern.match(lines[0].strip()):
            reference = lines[0].strip()
            body_lines = lines[1:]

        body = "\n".join(body_lines).strip()
        # Strip surrounding typographic or straight quotes
        body = body.strip("\u201c\u201d\u2018\u2019\"'")
        body = body.strip()

        return (reference, body)

    def _verse_to_html(self, verse_text: str) -> str:
        """Convert plain verse text to premium quote HTML."""
        if not verse_text:
            return '<div class="verse-container"><div class="verse-body"><em>(No verse found)</em></div></div>'

        reference, body = self._parse_verse_parts(verse_text)

        citation_html = ""
        if reference:
            citation_html = f'\n        <div class="verse-citation">\u2014 {self._escape_html(reference)}</div>'

        escaped_body = self._escape_html(body).replace("\n", "<br>")

        return (
            f'<div class="verse-container">\n'
            f'          <div class="verse-open-quote">\u275d</div>\n'
            f'          <div class="verse-body">{escaped_body}</div>'
            f"{citation_html}\n"
            f"        </div>"
        )

    def _divider(self) -> str:
        return (
            '      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"'
            ' style="margin: 32px 0;">\n'
            "        <tr>\n"
            '          <td style="border-top: 1px solid #d4c9a8;"></td>\n'
            '          <td style="color: #c8b88a; font-size: 14px; padding: 0 12px;'
            ' white-space: nowrap; font-family: Georgia, serif;">&#10022;</td>\n'
            '          <td style="border-top: 1px solid #d4c9a8;"></td>\n'
            "        </tr>\n"
            "      </table>\n"
        )

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _build_text(
        self,
        teachings: List[dict],
        date_str: str,
    ) -> str:
        """Build plain-text fallback version of the email."""
        lines = [
            f"JESUS TEACHINGS DAILY \u2014 {date_str}",
            "=" * 50,
            "",
        ]

        for i, teaching in enumerate(teachings):
            lines.append(f"TEACHING {i + 1}")
            lines.append(teaching.get("title", "Teaching"))
            lines.append("")
            verse = teaching.get("verse", "").strip()
            if verse:
                reference, body = self._parse_verse_parts(verse)
                lines.append("Key Verse:")
                if reference:
                    lines.append(reference)
                    lines.append("")
                lines.append(body)
            lines.append("")
            if i < len(teachings) - 1:
                lines.append("-" * 40)
                lines.append("")

        lines.append("=" * 50)
        lines.append("Let these words take root and bear fruit today.")
        return "\n".join(lines)
