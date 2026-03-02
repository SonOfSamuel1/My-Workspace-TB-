"""Send GoFundMe widow digest as an HTML email via SES."""

import os
import logging
from datetime import datetime

import boto3

logger = logging.getLogger(__name__)

DEFAULT_SENDER = "brandonhome.appdev@gmail.com"


def send_digest_email(campaigns, week_label, recipient=None, sender=None):
    """Send an HTML email digest of GoFundMe widow campaigns.

    Args:
        campaigns: List of campaign dicts from gofundme_search.
        week_label: Human-readable week string.
        recipient: Email address to send to (defaults to env var).
        sender: Sender email (defaults to env var or DEFAULT_SENDER).

    Returns:
        True if email sent successfully, False otherwise.
    """
    recipient = recipient or os.environ.get("DIGEST_RECIPIENT_EMAIL", DEFAULT_SENDER)
    sender = sender or os.environ.get("SES_SENDER_EMAIL", DEFAULT_SENDER)

    subject = f"GoFundMe Widow Digest - {week_label}"
    html = _build_html(campaigns, week_label)
    text = _build_plain_text(campaigns, week_label)

    try:
        ses = boto3.client("ses", region_name="us-east-1")
        ses.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html, "Charset": "UTF-8"},
                    "Text": {"Data": text, "Charset": "UTF-8"},
                },
            },
        )
        logger.info("Digest email sent to %s", recipient)
        return True
    except Exception as e:
        logger.error("Failed to send digest email: %s", e)
        return False


def _build_html(campaigns, week_label):
    """Build HTML email body."""
    rows = []
    for c in campaigns:
        location = _fmt_location(c)
        pct = (c["raised"] / c["goal"] * 100) if c["goal"] > 0 else 0
        bar_width = min(pct, 100)
        rows.append(f"""
        <tr>
          <td style="padding:16px 20px;border-bottom:1px solid #eee;">
            <a href="{c['url']}" style="color:#1a73e8;font-size:16px;font-weight:600;text-decoration:none;">
              {c['title']}
            </a>
            <div style="color:#666;font-size:13px;margin:4px 0;">{location}</div>
            <div style="margin:8px 0;">
              <div style="background:#e8e8e8;border-radius:4px;height:8px;width:200px;display:inline-block;">
                <div style="background:#4caf50;border-radius:4px;height:8px;width:{bar_width * 2:.0f}px;"></div>
              </div>
              <span style="font-size:13px;color:#333;margin-left:8px;">
                ${c['raised']:,.0f} of ${c['goal']:,.0f} ({pct:.0f}%)
              </span>
            </div>
            <div style="color:#888;font-size:12px;">{c['donation_count']} donations</div>
            <div style="color:#555;font-size:13px;margin-top:6px;line-height:1.4;">
              {c['description'][:200]}{'...' if len(c['description']) > 200 else ''}
            </div>
          </td>
        </tr>""")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        <tr>
          <td style="background:#1a73e8;padding:24px 20px;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:22px;">GoFundMe Widow Digest</h1>
            <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:14px;">{week_label} &middot; {len(campaigns)} campaigns</p>
          </td>
        </tr>
        {''.join(rows)}
        <tr>
          <td style="padding:16px 20px;text-align:center;color:#999;font-size:12px;">
            Generated {datetime.utcnow().strftime('%b %-d, %Y at %I:%M %p UTC')}
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _build_plain_text(campaigns, week_label):
    """Build plain text fallback."""
    lines = [f"GoFundMe Widow Digest - {week_label}", f"{len(campaigns)} campaigns found", "=" * 50, ""]
    for i, c in enumerate(campaigns, 1):
        location = _fmt_location(c)
        pct = (c["raised"] / c["goal"] * 100) if c["goal"] > 0 else 0
        lines.append(f"{i}. {c['title']}")
        lines.append(f"   {location}")
        lines.append(f"   ${c['raised']:,.0f} of ${c['goal']:,.0f} ({pct:.0f}%) - {c['donation_count']} donations")
        lines.append(f"   {c['url']}")
        lines.append("")
    return "\n".join(lines)


def _fmt_location(c):
    parts = []
    if c.get("city"):
        parts.append(c["city"])
    if c.get("state"):
        parts.append(c["state"])
    return ", ".join(parts) if parts else "Unknown location"
