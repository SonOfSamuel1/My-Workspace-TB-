"""HTML builder for the Follow-up tab in the ActionOS dashboard.

Renders sent emails that are awaiting a reply, grouped into
"Needs Review" and "Reviewed" sections with a 7-day review cycle.
"""

import html
import logging
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _to_gmail_app_link(url: str) -> str:
    """Convert a Gmail web URL to the iOS Gmail app deep link."""
    if url.startswith("https://mail.google.com"):
        return url.replace("https://mail.google.com", "googlegmail://", 1)
    return url

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)

_CC_LABEL = "Claude"


def _is_followup_reviewed(thread_id: str, state: dict) -> bool:
    ts = state.get("reviews", {}).get(thread_id)
    if not ts:
        return False
    try:
        reviewed_at = datetime.fromisoformat(ts)
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - reviewed_at).days < 7
    except Exception:
        return False


def _days_until_review_reset(thread_id: str, state: dict) -> int:
    ts = state.get("reviews", {}).get(thread_id)
    if not ts:
        return 0
    try:
        reviewed_at = datetime.fromisoformat(ts)
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
        return max(0, 7 - (datetime.now(timezone.utc) - reviewed_at).days)
    except Exception:
        return 0


def _format_email_age(date_str: str) -> str:
    """Return a human-readable age string like '3d ago'."""
    if not date_str:
        return ""
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - dt).days
        if days == 0:
            return "today"
        if days == 1:
            return "1d ago"
        return f"{days}d ago"
    except Exception:
        return ""


def _format_recipient(to_str: str) -> str:
    """Shorten recipient to first email address, strip display name."""
    if not to_str:
        return ""
    first = to_str.split(",")[0].strip()
    if "<" in first and ">" in first:
        return first[first.index("<") + 1 : first.index(">")]
    return first


def _build_followup_card(
    email: Dict[str, Any],
    reviewed: bool,
    days_remaining: int,
    function_url: str,
    action_token: str,
    idx: int,
) -> str:
    tid = email.get("threadId", "")
    msg_id = email.get("id", "")
    tid_safe = html.escape(tid)
    tid_enc = urllib.parse.quote(tid)
    msg_id_enc = urllib.parse.quote(msg_id)

    subject = html.escape(email.get("subject", "(no subject)"))
    to_raw = email.get("to", "")
    recipient = html.escape(_format_recipient(to_raw))
    msg_count = email.get("thread_message_count", 1)
    age = html.escape(_format_email_age(email.get("date", "")))
    gmail_link = html.escape(_to_gmail_app_link(email.get("gmail_link", "")))

    base_url = function_url.rstrip("/")
    open_url = html.escape(
        function_url.rstrip("/") + "?action=open&msg_id=" + msg_id_enc
    )

    if reviewed:
        review_btn = (
            f'<button class="review-btn reviewed" style="cursor:default;" '
            f'onclick="event.stopPropagation()">'
            f"\u2713 Reviewed ({days_remaining}d)</button>"
        )
    else:
        rev_url = html.escape(
            base_url + "?action=followup_reviewed&thread_id=" + tid_enc
        )
        review_btn = (
            f'<button class="review-btn" '
            f"onclick=\"event.stopPropagation();doReview(this,'{tid_safe}','{rev_url}')\">"
            "Review</button>"
        )

    res_url = html.escape(base_url + "?action=followup_resolved&thread_id=" + tid_enc)
    resolve_btn = (
        ""
        if reviewed
        else (
            f'<button class="resolve-btn" '
            f"onclick=\"event.stopPropagation();doResolve(this,'{tid_safe}','{res_url}')\">"
            "Resolved</button>"
        )
    )

    gmail_btn = ""
    if gmail_link:
        gmail_btn = (
            f'<a href="{gmail_link}" target="_blank" rel="noopener" class="gcal-link" '
            f'onclick="event.stopPropagation()">'
            f"Open in Gmail \u2197</a>"
        )

    # Assign CC button — copy email info to clipboard for Claude Code
    safe_subject_cc = subject.replace("'", "\\'")
    safe_recipient_cc = recipient.replace("'", "\\'")
    safe_gmail_cc = gmail_link.replace("'", "\\'")
    assign_cc_btn = (
        f'<button class="assign-cc-btn" title="Assign CC" '
        f'onclick="event.stopPropagation();doCopyFollowupForClaude(this,'
        f"'{safe_subject_cc}','{safe_recipient_cc}','{safe_gmail_cc}')\">"
        + _CC_LABEL
        + "</button>"
    )

    card_extra = " reviewed-card" if reviewed else " unreviewed-card"
    msg_label = f"{msg_count} message{'s' if msg_count != 1 else ''}"

    return (
        f'<div class="task-card{card_extra}" id="fu-card-{idx}" '
        f'data-open-url="{open_url}" onclick="openEmail(this)" style="cursor:pointer;">'
        f'<div class="card-row">'
        f'<div class="card-content">'
        f'<div class="task-title-row">'
        f'<span class="task-title">{subject}</span>'
        f'<span class="age-badge">{age}</span>'
        f"</div>"
        f'<div class="task-meta">To: {recipient} \u00b7 {msg_label}</div>'
        f'<div class="task-actions">'
        f"{review_btn}"
        f"{resolve_btn}"
        f"{gmail_btn}"
        f"{assign_cc_btn}"
        f"</div>"
        f"</div></div>"
        f"</div>"
    )


def build_followup_html(
    emails_dict: Dict[str, Dict[str, Any]],
    state: dict,
    function_url: str,
    action_token: str,
    embed: bool = False,
) -> str:
    """Build the Follow-up page with Needs Review and Reviewed sections."""
    emails = list(emails_dict.values())

    unreviewed = []
    reviewed_emails = []
    for email in emails:
        tid = email.get("threadId", "")
        if _is_followup_reviewed(tid, state):
            reviewed_emails.append(email)
        else:
            unreviewed.append(email)

    unreviewed_count = len(unreviewed)
    _card_idx = [0]

    def _cards(email_list):
        out = ""
        for email in email_list:
            idx = _card_idx[0]
            _card_idx[0] += 1
            tid = email.get("threadId", "")
            r = _is_followup_reviewed(tid, state)
            days_rem = _days_until_review_reset(tid, state)
            out += _build_followup_card(
                email, r, days_rem, function_url, action_token, idx
            )
        return out

    unreviewed_cards = _cards(unreviewed)
    if not unreviewed_cards:
        unreviewed_cards = '<div class="empty-state">All caught up \u2713</div>'

    reviewed_cards = _cards(reviewed_emails)
    if not reviewed_cards:
        reviewed_cards = '<div class="empty-state">No reviewed threads</div>'

    topbar_height = "0px" if embed else "57px"
    split_height = f"calc(100vh - {topbar_height})"
    embed_css = ".top-bar{display:none;}" if embed else ""

    post_message_js = ""
    if embed:
        post_message_js = (
            "var followupCount=" + str(unreviewed_count) + ";"
            "function postCount(){"
            "window.parent.postMessage({type:'count',source:'followup',count:followupCount},'*');"
            "}"
            "postCount();"
        )

    if unreviewed_count > 0:
        needs_review_html = (
            f'<div class="section-hdr">'
            f'<span style="color:var(--warn);">Needs Review</span>'
            f'<span class="section-badge" id="fu-unrev-badge" style="background:var(--warn-bg);'
            f'color:var(--warn);border:1px solid var(--warn-b);">{unreviewed_count}</span>'
            f"</div>" + unreviewed_cards
        )
    else:
        needs_review_html = (
            f'<div class="section-hdr">'
            f'<span style="color:var(--ok);">All Followed Up</span>'
            f'<span class="section-badge" id="fu-unrev-badge" style="background:var(--ok-bg);'
            f'color:var(--ok);border:1px solid var(--ok-b);">0</span>'
            f"</div>"
        )

    card_list_html = (
        needs_review_html + f'<div class="section-hdr" style="margin-top:24px;">'
        f'<span style="color:var(--text-2);">Reviewed</span>'
        f'<span class="section-badge" id="reviewed-badge" style="background:var(--border);color:var(--text-2);">'
        f"{len(reviewed_emails)}</span>"
        f"</div>"
        f'<div id="reviewed-list">' + reviewed_cards + "</div>"
    )

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
        '&display=swap" rel="stylesheet">'
        "<title>Follow-up</title>"
        "<style>"
        ":root{"
        "--bg-base:#1a1a1a;--bg-s0:#1c1c1e;--bg-s1:#252528;--bg-s2:#2c2c2e;"
        "--text-1:#ffffff;--text-2:#8e8e93;--text-3:#48484a;"
        "--border:rgba(255,255,255,0.08);--border-h:rgba(255,255,255,0.12);"
        "--accent:#6366f1;--accent-l:#818cf8;"
        "--accent-bg:rgba(99,102,241,0.10);--accent-b:rgba(99,102,241,0.20);"
        "--accent-hbg:rgba(99,102,241,0.08);"
        "--ok:#22c55e;--ok-bg:rgba(34,197,94,0.10);--ok-b:rgba(34,197,94,0.20);"
        "--warn:#eab308;--warn-bg:rgba(234,179,8,0.10);--warn-b:rgba(234,179,8,0.20);"
        "--err:#ef4444;--err-bg:rgba(239,68,68,0.10);--err-b:rgba(239,68,68,0.20);"
        "--scrollbar:rgba(255,255,255,0.10);color-scheme:dark;}"
        "@media(prefers-color-scheme:light){:root{"
        "--bg-base:#eeeef0;--bg-s0:#fff;--bg-s1:#fff;--bg-s2:#f5f5f7;"
        "--text-1:#202124;--text-2:#5f6368;--text-3:#80868b;"
        "--border:rgba(0,0,0,0.08);--border-h:rgba(0,0,0,0.15);"
        "--accent:#6366f1;--accent-l:#4f46e5;"
        "--accent-bg:rgba(99,102,241,0.08);--accent-b:rgba(99,102,241,0.15);"
        "--accent-hbg:rgba(99,102,241,0.06);"
        "--ok:#188038;--ok-bg:#e6f4ea;--ok-b:rgba(24,128,56,0.20);"
        "--warn:#e37400;--warn-bg:#fef7e0;--warn-b:rgba(227,116,0,0.20);"
        "--err:#d93025;--err-bg:#fce8e6;--err-b:rgba(217,48,37,0.20);"
        "--scrollbar:rgba(0,0,0,0.12);color-scheme:light;}}"
        "*{box-sizing:border-box;margin:0;padding:0;}"
        "body{font-family:" + _FONT + ";background:var(--bg-base);color:var(--text-1);"
        "-webkit-font-smoothing:antialiased;}"
        + embed_css
        + ".top-bar{background:var(--bg-s0);border-bottom:1px solid var(--border);"
        "padding:14px 20px;display:flex;align-items:center;gap:12px;"
        "position:sticky;top:0;z-index:20;}"
        ".top-bar-title{color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;}"
        ".refresh-btn{margin-left:auto;background:var(--border);border:1px solid var(--border);"
        "color:var(--text-1);font-size:13px;font-weight:600;padding:6px 14px;"
        "border-radius:6px;cursor:pointer;}"
        ".refresh-btn:hover{background:var(--border-h);}"
        ".split-wrap{display:flex;height:" + split_height + ";overflow:hidden;}"
        ".left-pane{flex:0 0 45%;min-width:0;overflow-y:auto;}"
        "#viewer-pane{display:flex;flex-direction:column;flex:1 1 55%;"
        "border-left:1px solid var(--border);background:var(--bg-base);"
        "position:relative;overflow:hidden;}"
        "#viewer-frame{width:100%;height:100%;border:none;display:none;}"
        "#viewer-placeholder{display:flex;align-items:center;justify-content:center;"
        "flex:1;color:var(--text-3);font-size:14px;flex-direction:column;gap:8px;}"
        ".close-btn{position:absolute;top:10px;right:14px;z-index:11;"
        "background:var(--border);border:none;cursor:pointer;font-size:20px;"
        "color:var(--text-2);width:36px;height:36px;border-radius:50%;"
        "display:flex;align-items:center;justify-content:center;}"
        ".close-btn:hover{background:var(--border-h);}"
        ".viewer-mobile-header{display:none;}"
        ".viewer-back-btn{display:flex;align-items:center;gap:6px;background:none;border:none;"
        "color:var(--accent-l);font-family:inherit;font-size:15px;font-weight:600;"
        "cursor:pointer;padding:8px 4px;touch-action:manipulation;}"
        ".task-list{max-width:600px;margin:0 auto;padding:12px 16px;overflow:hidden;}"
        ".section-hdr{display:flex;align-items:center;gap:8px;padding:16px 0 8px;"
        "font-size:11px;font-weight:600;color:var(--text-3);text-transform:uppercase;"
        "letter-spacing:0.6px;border-bottom:1px solid var(--border);margin-bottom:10px;"
        "position:sticky;top:0;z-index:10;background:var(--bg-base);}"
        ".section-badge{background:var(--border);color:var(--text-2);font-size:11px;"
        "font-weight:700;padding:2px 7px;border-radius:8px;}"
        ".task-card{background:var(--bg-s1);border-radius:8px;"
        "border:1px solid var(--border);padding:14px 16px;margin-bottom:10px;"
        "transition:border-color .15s,background .15s,opacity .3s;overflow:hidden;}"
        ".task-card:hover{border-color:var(--border-h);background:var(--bg-s2);}"
        ".task-card.active-card{background:var(--accent-hbg)!important;"
        "border-color:var(--accent-b)!important;}"
        ".unreviewed-card{border-left:3px solid var(--warn);}"
        ".reviewed-card{opacity:0.65;}"
        ".card-row{display:flex;align-items:flex-start;gap:10px;}"
        ".card-content{flex:1;min-width:0;overflow:hidden;}"
        ".task-title-row{display:flex;align-items:baseline;justify-content:space-between;"
        "gap:8px;margin-bottom:4px;}"
        ".task-title{font-size:15px;font-weight:600;color:var(--text-1);"
        "line-height:1.4;word-break:break-word;flex:1;min-width:0;}"
        ".age-badge{font-size:11px;font-weight:600;color:var(--text-2);"
        "white-space:nowrap;flex-shrink:0;}"
        ".task-meta{font-size:12px;color:var(--text-2);margin-bottom:10px;line-height:1.5;"
        "word-break:break-word;overflow-wrap:break-word;}"
        ".task-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}"
        ".review-btn{font-family:inherit;font-size:12px;font-weight:600;padding:5px 14px;"
        "border-radius:6px;background:var(--warn-bg);color:var(--warn);"
        "border:1px solid var(--warn-b);cursor:pointer;transition:background .15s;}"
        ".review-btn:hover{background:var(--warn-b);}"
        ".review-btn.reviewed{background:var(--ok-bg);color:var(--ok);"
        "border-color:var(--ok-b);cursor:default;}"
        ".resolve-btn{font-family:inherit;font-size:12px;font-weight:600;padding:5px 14px;"
        "border-radius:6px;background:var(--border);color:var(--text-2);"
        "border:1px solid var(--border);cursor:pointer;transition:background .15s;}"
        ".resolve-btn:hover{background:var(--border-h);color:var(--text-1);}"
        ".assign-cc-btn{display:inline-flex;align-items:center;justify-content:center;"
        "padding:5px 10px;border-radius:6px;"
        "background:rgba(196,120,64,0.10);border:1px solid rgba(196,120,64,0.25);"
        "cursor:pointer;transition:background .15s;color:#c47840;font-size:13px;font-weight:600;}"
        ".assign-cc-btn:hover{background:rgba(196,120,64,0.25);}"
        ".gcal-link{color:var(--accent-l);font-size:12px;font-weight:500;"
        "text-decoration:none;white-space:nowrap;}"
        ".gcal-link:hover{text-decoration:underline;}"
        ".empty-state{text-align:center;color:var(--text-2);padding:24px 20px;font-size:14px;}"
        "@media(max-width:768px){"
        ".left-pane{flex:1 1 100%!important;}"
        "#viewer-pane{display:none;position:fixed;top:0;right:0;bottom:0;width:100%;"
        "z-index:10;border-left:none;flex-direction:column;}"
        ".close-btn{display:none!important;}"
        ".viewer-mobile-header{display:flex!important;align-items:center;"
        "background:var(--bg-s0);border-bottom:1px solid var(--border);"
        "padding:0 12px;height:52px;flex-shrink:0;z-index:12;}"
        ".task-actions{gap:6px;}"
        ".review-btn,.resolve-btn{font-size:11px;padding:4px 6px;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style></head><body>"
        + (
            ""
            if embed
            else (
                '<div class="top-bar">'
                '<span class="top-bar-title">Follow-up</span>'
                '<button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>'
                "</div>"
            )
        )
        + '<div class="split-wrap">'
        '<div class="left-pane">'
        '<div class="task-list">' + card_list_html + "</div></div>"
        '<div id="viewer-pane">'
        '<div class="viewer-mobile-header">'
        '<button class="viewer-back-btn" onclick="closeViewer()">&#8592; Back</button>'
        "</div>"
        '<button class="close-btn" onclick="closeViewer()" title="Close">&times;</button>'
        '<div id="viewer-placeholder">'
        '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
        'style="color:var(--text-3)">'
        '<polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/>'
        "</svg>"
        "<span>Select a thread to view</span>"
        "</div>"
        '<iframe id="viewer-frame" src="about:blank"></iframe>'
        "</div>"
        "</div>"
        "<script>"
        + post_message_js
        + "var _cs=getComputedStyle(document.documentElement);"
        "function cv(n){return _cs.getPropertyValue(n).trim();}"
        "function openEmail(card){"
        "var url=card.getAttribute('data-open-url');"
        "if(!url)return;"
        "var all=document.querySelectorAll('.task-card');"
        "for(var i=0;i<all.length;i++)all[i].classList.remove('active-card');"
        "card.classList.add('active-card');"
        "var frame=document.getElementById('viewer-frame');"
        "frame.src=url+'&embed=1';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "frame.style.display='block';"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='flex';"
        "document.body.classList.add('viewer-open');"
        "try{window.parent.postMessage({type:'viewer-open'},'*');}catch(e){}"
        "}}"
        "function closeViewer(){"
        "var frame=document.getElementById('viewer-frame');"
        "frame.src='about:blank';frame.style.display='none';"
        "document.getElementById('viewer-placeholder').style.display='flex';"
        "var all=document.querySelectorAll('.task-card');"
        "for(var i=0;i<all.length;i++)all[i].classList.remove('active-card');"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='none';"
        "document.body.classList.remove('viewer-open');"
        "try{window.parent.postMessage({type:'viewer-close'},'*');}catch(e){}"
        "}}"
        "function doCopyFollowupForClaude(btn,subject,toAddr,gmailLink){"
        "var orig=btn.innerHTML;"
        "var msg='Please follow up on this sent email:\\n\\nSubject: '+subject+(toAddr?'\\nTo: '+toAddr:'')+(gmailLink?'\\nGmail: '+gmailLink:'');"
        "navigator.clipboard.writeText(msg).then(function(){"
        "btn.textContent='\\u2713';setTimeout(function(){btn.innerHTML=orig;},1500);"
        "}).catch(function(){btn.textContent='!';setTimeout(function(){btn.innerHTML=orig;},1500);});}"
        "function doReview(btn,tid,url){"
        "btn.style.pointerEvents='none';btn.textContent='Reviewing\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.className='review-btn reviewed';btn.textContent='\u2713 Reviewed (7d)';"
        "btn.style.cursor='default';btn.style.pointerEvents='auto';"
        "var card=btn.closest('.task-card');"
        "if(card){card.classList.remove('unreviewed-card');card.classList.add('reviewed-card');"
        "var acts=card.querySelectorAll('.resolve-btn');"
        "for(var i=0;i<acts.length;i++)acts[i].style.display='none';"
        "var rl=document.getElementById('reviewed-list');"
        "if(rl){var es=rl.querySelector('.empty-state');if(es)es.remove();rl.insertBefore(card,rl.firstChild);}"
        "var rb=document.getElementById('reviewed-badge');"
        "if(rb)rb.textContent=parseInt(rb.textContent||'0',10)+1;}"
        "if(typeof followupCount!=='undefined'){followupCount=Math.max(0,followupCount-1);"
        "if(typeof postCount==='function')postCount();}"
        "var b=document.getElementById('fu-unrev-badge');"
        "if(b&&typeof followupCount!=='undefined')b.textContent=followupCount;"
        "}else{btn.textContent='Review';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Review';btn.style.pointerEvents='auto';});}"
        "function doResolve(btn,tid,url){"
        "btn.style.pointerEvents='none';btn.textContent='Resolving\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "var card=btn.closest('.task-card');"
        "if(card){card.style.opacity='0';card.style.maxHeight=card.offsetHeight+'px';"
        "setTimeout(function(){card.style.maxHeight='0';card.style.marginBottom='0';"
        "card.style.padding='0';card.style.overflow='hidden';"
        "setTimeout(function(){card.remove();},300);},300);}"
        "closeViewer();"
        "if(typeof followupCount!=='undefined'){followupCount=Math.max(0,followupCount-1);"
        "if(typeof postCount==='function')postCount();}"
        "var b=document.getElementById('fu-unrev-badge');"
        "if(b&&typeof followupCount!=='undefined')b.textContent=followupCount;"
        "}else{btn.textContent='Resolved';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Resolved';btn.style.pointerEvents='auto';});}"
        "</script>"
        "</body></html>"
    )
