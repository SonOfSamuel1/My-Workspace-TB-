"""HTML view builder for the Code Projects (Claude Code) tab in ActionOS.

Shows four sections sorted by priority:
  - In Progress: tasks labelled "In Progress"
  - Planned:     tasks labelled "Planned"
  - Backlog:     tasks labelled "Backlog"
  - New Issues:  remaining unlabelled tasks
"""

import html

from todoist_views import _FONT, _build_task_card

_SVG_CODE = (
    '<svg style="display:inline-block;vertical-align:middle" width="28" height="28" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="4" width="18" height="12" rx="2"/>'
    '<path d="M2 20h20"/><path d="M9 8l-2 2.5L9 13"/><path d="M15 8l2 2.5L15 13"/></svg>'
)
_SVG_CODE_LG = (
    '<svg style="display:inline-block;vertical-align:middle" width="40" height="40" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="4" width="18" height="12" rx="2"/>'
    '<path d="M2 20h20"/><path d="M9 8l-2 2.5L9 13"/><path d="M15 8l2 2.5L15 13"/></svg>'
)


def build_code_projects_html(
    issues_tasks,
    in_progress_tasks,
    planned_tasks,
    backlog_tasks,
    projects,
    function_url,
    action_token,
    embed=False,
):
    """Build the Code Projects page with In Progress, Planned, Backlog, and New Issues sections.

    Args:
        issues_tasks:      List of task dicts for the New Issues section.
        in_progress_tasks: List of task dicts labelled "In Progress".
        planned_tasks:     List of task dicts labelled "Planned".
        backlog_tasks:     List of task dicts labelled "Backlog".
        projects:          Full list of Todoist project dicts.
        function_url:      Base Lambda function URL.
        action_token:      Auth token for action requests.
        embed:             If True, hides the top-bar and posts count to parent.
    """
    projects_by_id = {p["id"]: p.get("name", "Unknown") for p in projects}
    # Badge count = only untagged new issues
    total_count = len(issues_tasks)
    base_action_url = function_url.rstrip("/") + f"?token={html.escape(action_token)}"

    # Project options for bulk-move toolbar
    project_options_html = '<option value="" disabled selected>Move to...</option>'
    for pid, pname in sorted(projects_by_id.items(), key=lambda x: x[1].lower()):
        project_options_html += (
            f'<option value="{html.escape(pid)}">{html.escape(pname)}</option>'
        )

    def _render_cards(tasks, empty_msg):
        if tasks:
            cards = ""
            for task in tasks:
                cards += _build_task_card(
                    task, projects_by_id, function_url, action_token, view_name="code"
                )
            return cards
        return (
            '<div style="text-align:center;padding:32px 20px;color:var(--text-2);">'
            f'<div style="font-size:14px;">{empty_msg}</div>'
            "</div>"
        )

    in_progress_cards = _render_cards(in_progress_tasks, "No tasks in progress")
    planned_cards = _render_cards(planned_tasks, "No planned tasks")
    backlog_cards = _render_cards(backlog_tasks, "No backlog tasks")
    issues_cards = _render_cards(issues_tasks, "No new issues")

    header_html = ""
    if not embed:
        header_html = (
            '<div class="top-bar">'
            '<span class="top-bar-title">Code Projects</span>'
            f'<span class="top-bar-count">{total_count} tasks</span>'
            '<button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>'
            "</div>"
        )

    post_message_js = ""
    if embed:
        post_message_js = (
            f'window.parent.postMessage({{type:"count",source:"code",'
            f'count:{total_count}}},"*");'
        )

    split_height = "calc(100vh - 56px)" if not embed else "100vh"

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
        '&display=swap" rel="stylesheet">'
        "<title>Code Projects</title>"
        "<style>"
        ":root{"
        "--bg-base:#0e0e10;--bg-s0:#161618;--bg-s1:#1c1c1f;--bg-s2:#222225;"
        "--text-1:#ececef;--text-2:#8b8b93;--text-3:#56565e;"
        "--border:rgba(255,255,255,0.06);--border-h:rgba(255,255,255,0.10);"
        "--accent:#6366f1;--accent-l:#818cf8;"
        "--accent-bg:rgba(99,102,241,0.10);--accent-b:rgba(99,102,241,0.20);"
        "--accent-hbg:rgba(99,102,241,0.08);"
        "--ok:#22c55e;--ok-bg:rgba(34,197,94,0.10);--ok-b:rgba(34,197,94,0.20);"
        "--warn:#eab308;--warn-bg:rgba(234,179,8,0.10);--warn-b:rgba(234,179,8,0.20);"
        "--err:#ef4444;--err-bg:rgba(239,68,68,0.10);--err-b:rgba(239,68,68,0.20);"
        "--purple:#a78bfa;--purple-bg:rgba(167,139,250,0.10);--purple-b:rgba(167,139,250,0.20);"
        "--scrollbar:rgba(255,255,255,0.10);color-scheme:dark;}"
        "@media(prefers-color-scheme:light){:root{"
        "--bg-base:#f5f5f5;--bg-s0:#fff;--bg-s1:#fff;--bg-s2:#f8f9fa;"
        "--text-1:#202124;--text-2:#5f6368;--text-3:#80868b;"
        "--border:rgba(0,0,0,0.08);--border-h:rgba(0,0,0,0.15);"
        "--accent:#6366f1;--accent-l:#4f46e5;"
        "--accent-bg:rgba(99,102,241,0.08);--accent-b:rgba(99,102,241,0.15);"
        "--accent-hbg:rgba(99,102,241,0.06);"
        "--ok:#188038;--ok-bg:#e6f4ea;--ok-b:rgba(24,128,56,0.20);"
        "--warn:#e37400;--warn-bg:#fef7e0;--warn-b:rgba(227,116,0,0.20);"
        "--err:#d93025;--err-bg:#fce8e6;--err-b:rgba(217,48,37,0.20);"
        "--purple:#7c4dff;--purple-bg:#ede7f6;--purple-b:rgba(124,77,255,0.20);"
        "--scrollbar:rgba(0,0,0,0.12);color-scheme:light;}}"
        "*{box-sizing:border-box;margin:0;padding:0;}"
        f"body{{font-family:{_FONT};background:var(--bg-base);color:var(--text-1);"
        "-webkit-font-smoothing:antialiased;}"
        + (".top-bar{display:none;}" if embed else "")
        + ".top-bar{background:var(--bg-s0);border-bottom:1px solid var(--border);padding:14px 20px;"
        "display:flex;align-items:center;gap:12px;}"
        ".top-bar-title{color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;}"
        ".top-bar-count{color:var(--text-2);font-size:13px;}"
        ".refresh-btn{margin-left:auto;background:var(--border);border:1px solid var(--border);"
        "color:var(--text-1);font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;cursor:pointer;}"
        ".refresh-btn:hover{background:var(--border-h);}"
        # Section headers (sticky on mobile)
        ".section-hdr{display:flex;align-items:center;justify-content:space-between;"
        "padding:14px 16px 6px;max-width:700px;margin:0 auto;"
        "position:sticky;top:0;z-index:10;background:var(--bg-base);}"
        ".section-title{font-size:11px;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.8px;}"
        ".section-badge{font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px;}"
        ".section-divider{height:1px;background:var(--border);margin:12px 16px 0;"
        "max-width:calc(700px);margin-left:auto;margin-right:auto;}"
        # Split-pane layout
        f".split-wrap{{display:flex;height:{split_height};overflow:hidden;}}"
        ".left-pane{flex:0 0 45%;overflow-y:auto;}"
        "#viewer-pane{display:flex;flex-direction:column;flex:1 1 55%;"
        "border-left:1px solid var(--border);background:var(--bg-s1);position:relative;}"
        "#viewer-frame{flex:1;border:none;width:100%;display:none;}"
        "#detail-content{flex:1;overflow-y:auto;padding:24px;display:none;}"
        ".close-btn{position:absolute;top:10px;right:14px;z-index:10;"
        "background:var(--border);border:none;font-size:22px;cursor:pointer;"
        "width:36px;height:36px;border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;color:var(--text-2);}"
        ".close-btn:hover{background:var(--border-h);}"
        ".viewer-mobile-header{display:none;}"
        ".viewer-back-btn{display:flex;align-items:center;gap:6px;background:none;border:none;"
        "color:var(--accent-l);font-family:inherit;font-size:15px;font-weight:600;"
        "cursor:pointer;padding:8px 4px;touch-action:manipulation;}"
        # Task list / cards
        ".task-list{max-width:700px;margin:0 auto;padding:8px 16px 12px;}"
        ".task-card{background:var(--bg-s1);border-radius:8px;border:1px solid var(--border);"
        "padding:14px 16px;margin-bottom:10px;"
        "transition:opacity .15s ease-out,transform .15s ease-out,"
        "border-color .15s ease-out,background .15s ease-out;cursor:pointer;}"
        ".task-card:hover{border-color:var(--border-h);background:var(--bg-s2);}"
        ".task-card.active-card{background:var(--accent-hbg);border-color:var(--accent-b);}"
        ".task-card.removing{opacity:0;transform:translateX(60px);"
        "margin-bottom:0;padding-top:0;padding-bottom:0;max-height:0;overflow:hidden;}"
        ".card-row{display:flex;align-items:flex-start;gap:10px;}"
        ".card-content{flex:1;min-width:0;}"
        ".select-cb{width:18px;height:18px;margin-top:2px;cursor:pointer;flex-shrink:0;}"
        ".task-title{font-size:15px;font-weight:600;color:var(--text-1);"
        "line-height:1.4;margin-bottom:4px;word-break:break-word;}"
        ".task-title a{font-weight:500;}"
        ".task-meta{font-size:12px;color:var(--text-2);margin-bottom:10px;line-height:1.5;}"
        ".task-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}"
        ".action-select{font-family:inherit;font-size:12px;padding:5px 8px;"
        "border:1px solid var(--border);border-radius:6px;background:var(--bg-s2);"
        "color:var(--text-1);cursor:pointer;}"
        ".action-select:focus{outline:none;border-color:rgba(99,102,241,0.5);"
        "box-shadow:0 0 0 2px rgba(99,102,241,0.15);}"
        ".complete-btn{font-family:inherit;font-size:12px;font-weight:600;padding:5px 14px;"
        "border-radius:6px;background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);"
        "cursor:pointer;transition:background .15s ease-out;}"
        ".complete-btn:hover{background:var(--ok-b);}"
        ".complete-btn:disabled{background:rgba(34,197,94,0.05);color:rgba(34,197,94,0.4);"
        "border-color:var(--ok-bg);cursor:default;}"
        ".commit-btn{font-family:inherit;font-size:12px;font-weight:600;padding:5px 14px;"
        "border-radius:6px;background:var(--warn-bg);color:var(--warn);"
        "border:1px solid var(--warn-b);cursor:pointer;transition:background .15s ease-out;}"
        ".commit-btn:hover{background:var(--warn-b);}"
        ".commit-btn.committed{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);cursor:default;}"
        ".commit-btn.remove{background:var(--err-bg);color:var(--err);border-color:var(--err-b);}"
        ".commit-btn.remove:hover{background:var(--err-b);}"
        ".bestcase-btn{font-family:inherit;font-size:12px;font-weight:600;padding:5px 14px;"
        "border-radius:6px;background:var(--purple-bg);color:var(--purple);"
        "border:1px solid var(--purple-b);cursor:pointer;transition:background .15s ease-out;}"
        ".bestcase-btn:hover{background:var(--purple-b);}"
        ".bestcase-btn.active{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);cursor:default;}"
        ".bestcase-btn.remove{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);}"
        ".bestcase-btn.remove:hover{background:var(--err-bg);color:var(--err);border-color:var(--err-b);}"
        # Backlog button (neutral style)
        ".backlog-btn{font-family:inherit;font-size:12px;font-weight:600;padding:5px 14px;"
        "border-radius:6px;background:var(--border);color:var(--text-2);"
        "border:1px solid var(--border-h);cursor:pointer;transition:background .15s ease-out;}"
        ".backlog-btn:hover{background:var(--border-h);}"
        ".backlog-btn.active{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);}"
        ".task-card.undo-state .card-row{display:none;}"
        ".undo-bar{display:flex;align-items:center;justify-content:center;"
        "gap:10px;padding:12px 0;font-size:13px;color:var(--text-2);}"
        ".undo-bar a{color:var(--accent-l);font-weight:600;cursor:pointer;text-decoration:none;}"
        ".undo-bar a:hover{text-decoration:underline;}"
        "#bulk-toolbar{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);"
        "background:#16161af2;"
        "border:1px solid var(--border);color:var(--text-1);padding:10px 18px;"
        "border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.25);"
        "display:none;align-items:center;gap:10px;z-index:500;font-size:13px;font-weight:500;}"
        "#bulk-toolbar select{font-size:12px;padding:5px 8px;border-radius:6px;"
        "border:1px solid var(--border-h);background:var(--bg-s2);color:var(--text-1);}"
        "#bulk-toolbar button{font-size:12px;font-weight:600;padding:6px 14px;"
        "border:none;border-radius:6px;cursor:pointer;}"
        ".bulk-complete-btn{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);}"
        ".bulk-complete-btn:hover{background:var(--ok-b);}"
        ".bulk-date-input{font-size:12px;padding:5px 8px;border-radius:6px;"
        "border:1px solid var(--border-h);background:var(--bg-s2);color:var(--text-1);}"
        ".detail-title{font-size:20px;font-weight:700;color:var(--text-1);line-height:1.4;margin-bottom:16px;}"
        ".detail-title-editable{outline:none;border-radius:4px;padding:2px 4px;margin:-2px -4px;transition:background .15s;}"
        ".detail-title-editable:hover{background:var(--bg-s2);}"
        ".detail-title-editable:focus{background:var(--bg-s2);box-shadow:0 0 0 2px rgba(99,102,241,0.3);}"
        ".detail-desc-editable{width:100%;font-family:inherit;font-size:14px;color:var(--text-1);"
        "background:var(--bg-s2);border:1px solid var(--border);border-radius:6px;"
        "padding:8px 10px;resize:none;line-height:1.5;margin-bottom:8px;overflow:hidden;}"
        ".detail-desc-editable:focus{outline:none;border-color:rgba(99,102,241,0.5);}"
        ".detail-meta{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}"
        ".detail-meta-tag{display:inline-block;padding:4px 10px;border-radius:6px;"
        "font-size:12px;font-weight:600;background:var(--border);color:var(--text-2);}"
        ".detail-section-label{font-size:11px;font-weight:600;text-transform:uppercase;"
        "color:var(--text-3);letter-spacing:0.5px;margin-bottom:6px;}"
        ".detail-description{font-size:14px;line-height:1.7;color:var(--text-2);"
        "white-space:pre-wrap;margin-bottom:20px;padding:16px;background:var(--bg-s2);"
        "border-radius:8px;border:1px solid var(--border);}"
        ".detail-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px;"
        "padding-top:16px;border-top:1px solid var(--border);}"
        ".detail-action-btn{font-family:inherit;font-size:13px;font-weight:600;"
        "padding:8px 18px;border:none;border-radius:8px;cursor:pointer;}"
        ".view-email-btn{background:var(--accent-bg);color:var(--accent-l);border:1px solid var(--accent-b);}"
        # Schedule button
        ".schedule-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:rgba(56,189,248,0.10);color:#38bdf8;border:1px solid rgba(56,189,248,0.20);cursor:pointer;"
        "transition:background .15s ease-out;}"
        ".schedule-btn:hover{background:rgba(56,189,248,0.25);}"
        # Schedule modal
        "#schedule-overlay{display:none;position:fixed;top:0;left:0;right:0;bottom:0;"
        "z-index:2000;background:rgba(0,0,0,0.6);align-items:center;justify-content:center;}"
        "#schedule-overlay.open{display:flex;}"
        "#schedule-modal{background:var(--bg-s1);border:1px solid var(--border);border-radius:14px;"
        "padding:24px;width:320px;max-width:90vw;box-shadow:0 8px 32px rgba(0,0,0,0.4);}"
        "#schedule-modal h3{font-size:16px;font-weight:700;color:var(--text-1);margin-bottom:4px;}"
        "#schedule-modal p{font-size:13px;color:var(--text-2);margin-bottom:16px;}"
        ".duration-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;}"
        ".duration-opt{font-family:inherit;font-size:14px;font-weight:600;"
        "padding:12px 8px;border-radius:8px;border:1px solid var(--border);"
        "background:var(--bg-s2);color:var(--text-1);cursor:pointer;"
        "transition:all .15s;text-align:center;}"
        ".duration-opt:hover{border-color:rgba(56,189,248,0.4);background:rgba(56,189,248,0.08);color:#38bdf8;}"
        ".duration-opt.selected{border-color:#38bdf8;background:rgba(56,189,248,0.15);color:#38bdf8;}"
        "#schedule-confirm{width:100%;font-family:inherit;font-size:14px;font-weight:700;"
        "padding:12px;border-radius:8px;border:none;cursor:pointer;"
        "background:#38bdf8;color:#0e0e10;transition:opacity .15s;}"
        "#schedule-confirm:hover{opacity:0.85;}"
        "#schedule-confirm:disabled{opacity:0.4;cursor:default;}"
        "#schedule-cancel{width:100%;font-family:inherit;font-size:13px;font-weight:600;"
        "padding:8px;border-radius:8px;border:none;cursor:pointer;margin-top:8px;"
        "background:transparent;color:var(--text-2);}"
        "#schedule-cancel:hover{color:var(--text-1);}"
        "@media(max-width:768px){"
        ".task-actions{gap:6px;}"
        ".action-select,.complete-btn{font-size:11px;padding:4px 6px;}"
        ".left-pane{flex:1 1 100%!important;}"
        "#viewer-pane{display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:200;border-left:none;}"
        ".close-btn{display:none!important;}"
        ".viewer-mobile-header{display:flex;align-items:center;background:var(--bg-s0);"
        "border-bottom:1px solid var(--border);padding:0 12px;height:52px;flex-shrink:0;z-index:12;}"
        "#bulk-toolbar{left:10px;right:10px;transform:none;flex-wrap:wrap;justify-content:center;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style>"
        "</head><body>" + header_html + '<div class="split-wrap" id="split-wrap">'
        # Left pane — four-section task list
        + '<div class="left-pane">'
        # ── In Progress ───────────────────────────────────────────────────
        + '<div class="section-hdr">'
        f'<span class="section-title" style="color:var(--ok);">In Progress</span>'
        f'<span class="section-badge" style="background:var(--ok-bg);color:var(--ok);'
        f'border:1px solid var(--ok-b);">{len(in_progress_tasks)}</span>'
        "</div>" + '<div class="task-list">' + in_progress_cards + "</div>"
        # ── Planned ───────────────────────────────────────────────────────
        + '<div class="section-divider"></div>'
        + '<div class="section-hdr" style="margin-top:4px;">'
        f'<span class="section-title" style="color:var(--warn);">Planned</span>'
        f'<span class="section-badge" style="background:var(--warn-bg);color:var(--warn);'
        f'border:1px solid var(--warn-b);">{len(planned_tasks)}</span>'
        "</div>" + '<div class="task-list">' + planned_cards + "</div>"
        # ── Backlog ───────────────────────────────────────────────────────
        + '<div class="section-divider"></div>'
        + '<div class="section-hdr" style="margin-top:4px;">'
        f'<span class="section-title" style="color:var(--text-2);">Backlog</span>'
        f'<span class="section-badge" style="background:var(--border);color:var(--text-2);'
        f'border:1px solid var(--border-h);">{len(backlog_tasks)}</span>'
        "</div>" + '<div class="task-list">' + backlog_cards + "</div>"
        # ── New Issues ────────────────────────────────────────────────────
        + '<div class="section-divider"></div>'
        + '<div class="section-hdr" style="margin-top:4px;">'
        f'<span class="section-title" style="color:var(--accent-l);">New Issues</span>'
        f'<span class="section-badge" style="background:var(--accent-bg);color:var(--accent-l);'
        f'border:1px solid var(--accent-b);">{len(issues_tasks)}</span>'
        "</div>" + '<div class="task-list">' + issues_cards + "</div>" + "</div>"
        # Right pane — detail / email viewer
        + '<div id="viewer-pane">'
        '<div class="viewer-mobile-header">'
        '<button class="viewer-back-btn" onclick="closeViewer()">&#8592; Back to list</button>'
        "</div>"
        '<button class="close-btn" onclick="closeViewer()" title="Close">&times;</button>'
        '<div id="viewer-placeholder" style="'
        "flex:1;display:flex;flex-direction:column;align-items:center;"
        'justify-content:center;color:var(--text-3);font-size:15px;gap:12px;">'
        + _SVG_CODE_LG
        + "<span>Select a task to view details</span>"
        "</div>"
        '<div id="detail-content"></div>'
        '<iframe id="viewer-frame" src="about:blank"></iframe>'
        "</div>" + "</div>"  # end split-wrap
        # Bulk toolbar
        + '<div id="bulk-toolbar">'
        '<span id="bulk-count">0 selected</span>'
        f'<select id="bulk-move-select" onchange="bulkMove(this.value);this.selectedIndex=0;">'
        f"{project_options_html}</select>"
        '<input type="date" class="bulk-date-input" id="bulk-date-input" '
        'onchange="bulkSetDueDate(this.value);this.value=\'\';" title="Set due date">'
        '<button class="bulk-complete-btn" onclick="bulkComplete()">Complete</button>'
        "</div>"
        # Schedule duration picker modal
        + '<div id="schedule-overlay" onclick="if(event.target===this)closeScheduleModal()">'
        '<div id="schedule-modal">'
        "<h3>Schedule Action</h3>"
        '<p id="schedule-task-label">How long will this take?</p>'
        '<div class="duration-grid">'
        '<button class="duration-opt" data-mins="30">30 min</button>'
        '<button class="duration-opt" data-mins="60">1 hr</button>'
        '<button class="duration-opt" data-mins="90">1.5 hrs</button>'
        '<button class="duration-opt" data-mins="120">2 hrs</button>'
        '<button class="duration-opt" data-mins="150">2.5 hrs</button>'
        '<button class="duration-opt" data-mins="180">3 hrs</button>'
        '<button class="duration-opt" data-mins="210">3.5 hrs</button>'
        '<button class="duration-opt" data-mins="240">4 hrs</button>'
        '<button class="duration-opt" data-mins="270">4.5 hrs</button>'
        '<button class="duration-opt" data-mins="300">5 hrs</button>'
        "</div>"
        '<button id="schedule-confirm" disabled>Schedule</button>'
        '<button id="schedule-cancel" onclick="closeScheduleModal()">Cancel</button>'
        "</div></div>"
        # JavaScript
        + "<script>"
        "var _cs=getComputedStyle(document.documentElement);"
        "function cv(n){return _cs.getPropertyValue(n).trim();}"
        "var viewName='code';"
        f"var taskCount={total_count};"
        + post_message_js
        + "function updateCount(){taskCount--;if(taskCount<0)taskCount=0;"
        + (
            f'window.parent.postMessage({{type:"count",source:"code",count:taskCount}},"*");'
            if embed
            else ""
        )
        + "}"
        "function undoCount(){taskCount++;"
        + (
            f'window.parent.postMessage({{type:"count",source:"code",count:taskCount}},"*");'
            if embed
            else ""
        )
        + "}"
        "var undoTimers={};"
        "function removeCard(id){"
        "var card=document.getElementById('card-'+id);"
        "if(card){card.classList.add('removing');setTimeout(function(){card.remove();},350);}}"
        "function showUndo(taskId,msg,onUndo){"
        "var card=document.getElementById('card-'+taskId);if(!card)return;"
        "card.classList.add('undo-state');"
        "var bar=card.querySelector('.undo-bar');"
        "bar.innerHTML=msg+' <a onclick=\"undoTimers[\\''+taskId+'\\'].undo()\">Undo</a>';"
        "bar.style.display='flex';updateCount();"
        "var timer=setTimeout(function(){delete undoTimers[taskId];removeCard(taskId);},5000);"
        "undoTimers[taskId]={timer:timer,undo:function(){"
        "clearTimeout(timer);delete undoTimers[taskId];"
        "bar.innerHTML='Undoing...';onUndo();}};}"
        "function restoreCard(taskId){"
        "var card=document.getElementById('card-'+taskId);if(!card)return;"
        "card.classList.remove('undo-state');"
        "var bar=card.querySelector('.undo-bar');bar.style.display='none';bar.innerHTML='';"
        "undoCount();}"
        "function doMove(taskId,projectId,sel){"
        "if(!projectId)return;"
        "var card=document.getElementById('card-'+taskId);"
        "var origProjectId=card?card.getAttribute('data-project-id'):'';"
        "var projName=sel.options[sel.selectedIndex].text;sel.disabled=true;"
        f'fetch("{base_action_url}&action=move&task_id="+taskId+"&project_id="+projectId)'
        ".then(function(r){if(r.ok){"
        "showUndo(taskId,'Moved to '+projName+'.',function(){"
        f'fetch("{base_action_url}&action=move&task_id="+taskId+"&project_id="+origProjectId)'
        ".then(function(r2){if(r2.ok){sel.disabled=false;sel.selectedIndex=0;restoreCard(taskId);}else{removeCard(taskId);}})"
        ".catch(function(){removeCard(taskId);});});"
        '}else{sel.disabled=false;alert("Move failed");}})'
        '.catch(function(){sel.disabled=false;alert("Move failed");});}'
        "function doSetPriority(taskId,priority,sel){"
        "sel.disabled=true;"
        f'fetch("{base_action_url}&action=priority&task_id="+taskId+"&priority="+priority)'
        ".then(function(r){if(r.ok){sel.disabled=false;}"
        "else{sel.disabled=false;alert('Priority update failed');}}"
        ").catch(function(){sel.disabled=false;alert('Priority update failed');});}"
        "function doSetDueDate(taskId,dateValue,input){"
        "input.disabled=true;"
        f'fetch("{base_action_url}&action=due_date&task_id="+taskId+"&date="+encodeURIComponent(dateValue))'
        ".then(function(r){if(r.ok){"
        "input.disabled=false;input.style.borderColor='rgba(34,197,94,0.5)';"
        "setTimeout(function(){input.style.borderColor='';},1500);"
        "}else{input.disabled=false;alert('Due date update failed');}}"
        ").catch(function(){input.disabled=false;alert('Due date update failed');});}"
        "function doComplete(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}&action=complete&task_id="+taskId)'
        ".then(function(r){if(r.ok){"
        "showUndo(taskId,'Completed.',function(){"
        f'fetch("{base_action_url}&action=reopen&task_id="+taskId)'
        ".then(function(r2){if(r2.ok){btn.disabled=false;btn.textContent='Complete';restoreCard(taskId);}else{removeCard(taskId);}})"
        ".catch(function(){removeCard(taskId);});});"
        '}else{btn.disabled=false;btn.textContent="Complete";alert("Complete failed");}})'
        '.catch(function(){btn.disabled=false;btn.textContent="Complete";alert("Complete failed");});}'
        # Status label helpers — Planned / In Progress / Backlog
        "function _statusAction(taskId,btn,action,label,resetLabel,onSuccess){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}&action="+action+"&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){if(d.ok){onSuccess(btn);}"
        "else{btn.disabled=false;btn.textContent=resetLabel;alert(label+' failed');}}"
        ").catch(function(){btn.disabled=false;btn.textContent=resetLabel;alert(label+' failed');});}"
        "function _resetSiblingBtns(btn,excludeClass){"
        "var card=btn.closest('.task-card');if(!card)return;"
        "if(excludeClass!=='commit-btn'){var cb=card.querySelector('.commit-btn');"
        "if(cb){cb.textContent='Planned';cb.classList.remove('committed','remove');"
        "cb.style.background=cv('--warn-bg');cb.style.color=cv('--warn');cb.disabled=false;}}"
        "if(excludeClass!=='bestcase-btn'){var bc=card.querySelector('.bestcase-btn');"
        "if(bc){bc.textContent='In Progress';bc.classList.remove('remove','active');"
        "bc.style.background=cv('--purple-bg');bc.style.color=cv('--purple');bc.disabled=false;}}"
        "}"
        "function doPlanned(taskId,btn){"
        "_statusAction(taskId,btn,'planned_label','Planned','Planned',function(b){"
        "b.textContent='\\u2713 Planned';b.classList.add('committed');"
        "b.style.background=cv('--ok-bg');b.style.color=cv('--ok');"
        "_resetSiblingBtns(b,'commit-btn');});}"
        "function doRemovePlanned(taskId,btn){"
        "_statusAction(taskId,btn,'remove_planned','Remove','\\u2713 Planned',function(b){"
        "b.textContent='Planned';b.classList.remove('committed');"
        "b.style.background=cv('--warn-bg');b.style.color=cv('--warn');"
        "b.disabled=false;b.onclick=function(e){e.stopPropagation();doPlanned(taskId,b);};});}"
        "function doInProgress(taskId,btn){"
        "_statusAction(taskId,btn,'in_progress_label','In Progress','In Progress',function(b){"
        "b.textContent='\\u2713 In Progress';b.classList.add('remove');"
        "b.style.background=cv('--ok-bg');b.style.color=cv('--ok');"
        "_resetSiblingBtns(b,'bestcase-btn');});}"
        "function doRemoveInProgress(taskId,btn){"
        "_statusAction(taskId,btn,'remove_in_progress','Remove','\\u2713 In Progress',function(b){"
        "b.textContent='In Progress';b.classList.remove('remove');"
        "b.style.background=cv('--purple-bg');b.style.color=cv('--purple');"
        "b.disabled=false;b.onclick=function(e){e.stopPropagation();doInProgress(taskId,b);};});}"
        "function doBacklog(taskId,btn){"
        "_statusAction(taskId,btn,'backlog_label','Backlog','Backlog',function(b){"
        "b.textContent='\\u2713 Backlog';b.classList.add('remove');"
        "b.style.background=cv('--ok-bg');b.style.color=cv('--ok');"
        "_resetSiblingBtns(b,'');});}"
        "function doRemoveBacklog(taskId,btn){"
        "_statusAction(taskId,btn,'remove_backlog','Remove','\\u2713 Backlog',function(b){"
        "b.textContent='Backlog';b.classList.remove('remove');"
        "b.style.background=cv('--border');b.style.color=cv('--text-2');"
        "b.disabled=false;b.onclick=function(e){e.stopPropagation();doBacklog(taskId,b);};});}"
        # Keep old commit/bestcase functions for other views that might reference them
        "function doCommit(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}&action=commit_label&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){if(d.ok){"
        "btn.textContent='\\u2713 Committed';btn.classList.add('committed');"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "}else{btn.disabled=false;btn.textContent='Commit';alert('Commit failed');}}"
        ").catch(function(){btn.disabled=false;btn.textContent='Commit';alert('Commit failed');});}"
        "function doBestCase(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}&action=bestcase_label&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){if(d.ok){"
        "btn.textContent='\\u2713 Best Case';btn.classList.add('active');"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "}else{btn.disabled=false;btn.textContent='Best Case';alert('Best Case failed');}}"
        ").catch(function(){btn.disabled=false;btn.textContent='Best Case';alert('Best Case failed');});}"
        "function doRemoveBestCase(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}&action=remove_bestcase&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){if(d.ok){"
        "btn.textContent='Best Case';btn.classList.remove('remove','active');"
        "btn.style.background=cv('--purple-bg');btn.style.color=cv('--purple');"
        "btn.disabled=false;btn.onclick=function(e){e.stopPropagation();doBestCase(taskId,btn);};"
        "}else{btn.disabled=false;btn.textContent='\\u2713 Best Case \\u2715';alert('Remove failed');}}"
        ").catch(function(){btn.disabled=false;btn.textContent='\\u2713 Best Case \\u2715';alert('Remove failed');});}"
        "function doRemoveCommit(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}&action=remove_commit&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){if(d.ok){"
        "btn.textContent='Commit';btn.classList.remove('remove','committed');"
        "btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');"
        "btn.disabled=false;btn.onclick=function(e){e.stopPropagation();doCommit(taskId,btn);};"
        "}else{btn.disabled=false;btn.textContent='Remove Commit';alert('Remove failed');}}"
        ").catch(function(){btn.disabled=false;btn.textContent='Remove Commit';alert('Remove failed');});}"
        "function esc(s){var d=document.createElement('div');"
        "d.appendChild(document.createTextNode(String(s)));return d.innerHTML;}"
        f"function doUpdateTask(taskId,payload,callback){{"
        f"payload.task_id=taskId;"
        f'fetch("{base_action_url}&action=update_task",{{method:"POST",'
        f'headers:{{"Content-Type":"application/json"}},'
        f"body:JSON.stringify(payload)}})"
        f".then(function(r){{return r.json();}})"
        f".then(function(d){{if(callback)callback(d.ok||false);}}"
        f").catch(function(){{if(callback)callback(false);}});}}"
        "function linkify(t){"
        "t=t.replace(/\\[([^\\]]+)\\]\\(((?:https?|obsidian):\\/\\/[^)]+)\\)/g,"
        '\'<a href="$2" target="_blank" rel="noopener" style="color:\'+cv(\'--accent-l\')+\';text-decoration:underline;">$1</a>\');'
        't=t.replace(/(?<!href=")(?<!">)((?:https?|obsidian):\\/\\/[^\\s<)]+)/g,'
        '\'<a href="$1" target="_blank" rel="noopener" style="color:\'+cv(\'--accent-l\')+\';text-decoration:underline;">$1</a>\');'
        "return t;}"
        "function openTaskDetail(card){"
        "if(event&&event.target&&event.target.closest('a'))return;"
        "var cbs=card.querySelector('.select-cb');if(cbs&&document.activeElement===cbs)return;"
        "var taskId=card.getAttribute('data-task-id')||'';"
        "var title=card.getAttribute('data-content')||'(no title)';"
        "var description=card.getAttribute('data-description')||'';"
        "var projectName=card.getAttribute('data-project-name')||'';"
        "var priority=parseInt(card.getAttribute('data-priority')||'1');"
        "var pLabel=card.getAttribute('data-priority-label')||'P4';"
        "var pColor=card.getAttribute('data-priority-color')||'#5f6368';"
        "var labels=card.getAttribute('data-labels')||'';"
        "var dueDate=card.getAttribute('data-due-date')||'';"
        "var dueText=card.getAttribute('data-due-text')||'';"
        "var dueColor=card.getAttribute('data-due-color')||'#5f6368';"
        "var openUrl=card.getAttribute('data-open-url')||'';"
        "document.querySelectorAll('.task-card').forEach(function(c){c.classList.remove('active-card');});"
        "card.classList.add('active-card');"
        "var h='';"
        'h+=\'<div contenteditable="true" class="detail-title detail-title-editable" '
        "data-task-id=\"'+esc(taskId)+'\" data-orig=\"'+esc(title)+'\">'+esc(title)+'</div>';"
        "h+='<div class=\"detail-meta\">';"
        "h+='<span class=\"detail-meta-tag\" style=\"background:'+esc(pColor)+'26;color:'+esc(pColor)+';\">'+esc(pLabel)+'</span>';"
        "if(projectName)h+='<span class=\"detail-meta-tag\">'+esc(projectName)+'</span>';"
        "if(dueText)h+='<span class=\"detail-meta-tag\" style=\"color:'+esc(dueColor)+';\">'+esc(dueText)+'</span>';"
        "if(labels){labels.split(',').forEach(function(lbl){"
        "lbl=lbl.trim();if(lbl)h+='<span class=\"detail-meta-tag\" style=\"color:'+cv('--purple')+';\">'+'@'+esc(lbl)+'</span>';})}"
        "h+='</div>';"
        "h+='<div class=\"detail-section-label\">Description</div>';"
        "h+='<div class=\"detail-desc-display\" style=\"white-space:pre-wrap;color:var(--text-2);font-size:14px;line-height:1.6;padding:8px;min-height:40px;cursor:text;border:1px solid transparent;border-radius:6px;\" title=\"Click to edit\">'+(description?linkify(esc(description)):'<span style=\"color:var(--text-3);font-style:italic;\">Click to add description...</span>')+'</div>';"
        'h+=\'<textarea class="detail-desc-editable" data-task-id="\'+esc(taskId)+\'" rows="1" placeholder="Add description..." style="display:none;">\'+esc(description)+\'</textarea>\';'
        'h+=\'<button class="detail-action-btn detail-desc-save-btn" '
        'style="display:none;margin-bottom:8px;background:var(--accent-bg);color:var(--accent-l);border:1px solid var(--accent-b);">Save Description</button>\';'
        "h+='<div class=\"detail-actions\">';"
        "var pOpts=[[4,'P1'],[3,'P2'],[2,'P3'],[1,'P4']];"
        "h+='<select class=\"action-select detail-priority-sel\">';"
        "pOpts.forEach(function(p){var sel=p[0]===priority?' selected':'';h+='<option value=\"'+p[0]+'\"'+sel+'>'+p[1]+'</option>';});"
        "h+='</select>';"
        'h+=\'<input type="date" class="action-select detail-due-input" value="\'+esc(dueDate)+\'">\';'
        'h+=\'<button class="detail-action-btn detail-complete-btn" '
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);">Complete</button>\';'
        "var labelsArr=labels?labels.split(','):[];"
        "var isPlanned=labelsArr.indexOf('Planned')!==-1;"
        "var isInProgress=labelsArr.indexOf('In Progress')!==-1;"
        "var isBacklog=labelsArr.indexOf('Backlog')!==-1;"
        # Planned button in detail
        'if(isPlanned){h+=\'<button class="detail-action-btn detail-status-btn planned" '
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);">\\u2713 Planned</button>\';}'
        'else{h+=\'<button class="detail-action-btn detail-status-btn planned" '
        'style="background:rgba(234,179,8,0.10);color:#eab308;border:1px solid rgba(234,179,8,0.20);">Planned</button>\';}'
        # In Progress button in detail
        'if(isInProgress){h+=\'<button class="detail-action-btn detail-status-btn inprogress" '
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);">\\u2713 In Progress</button>\';}'
        'else{h+=\'<button class="detail-action-btn detail-status-btn inprogress" '
        'style="background:rgba(167,139,250,0.10);color:#a78bfa;border:1px solid rgba(167,139,250,0.20);">In Progress</button>\';}'
        # Backlog button in detail
        'if(isBacklog){h+=\'<button class="detail-action-btn detail-status-btn backlog" '
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);">\\u2713 Backlog</button>\';}'
        'else{h+=\'<button class="detail-action-btn detail-status-btn backlog" '
        "style=\"background:'+cv('--border')+';color:'+cv('--text-2')+';border:1px solid '+cv('--border-h')+';\">Backlog</button>';}"
        "if(openUrl)h+='<button class=\"detail-action-btn view-email-btn\">View Email</button>';"
        "h+='</div>';"
        "var dc=document.getElementById('detail-content');dc.innerHTML=h;"
        "var ps=dc.querySelector('.detail-priority-sel');"
        "if(ps)ps.addEventListener('change',function(){doSetPriority(taskId,this.value,this,pColor);});"
        "var di=dc.querySelector('.detail-due-input');"
        "if(di)di.addEventListener('change',function(){doSetDueDate(taskId,this.value,this);});"
        "var cb=dc.querySelector('.detail-complete-btn');"
        "if(cb)cb.addEventListener('click',function(){doComplete(taskId,cb);});"
        "var plb=dc.querySelector('.detail-status-btn.planned');"
        "if(plb){if(isPlanned){plb.addEventListener('click',function(){doRemovePlanned(taskId,plb);});}"
        "else{plb.addEventListener('click',function(){doPlanned(taskId,plb);});}}"
        "var ipb=dc.querySelector('.detail-status-btn.inprogress');"
        "if(ipb){if(isInProgress){ipb.addEventListener('click',function(){doRemoveInProgress(taskId,ipb);});}"
        "else{ipb.addEventListener('click',function(){doInProgress(taskId,ipb);});}}"
        "var blb=dc.querySelector('.detail-status-btn.backlog');"
        "if(blb){if(isBacklog){blb.addEventListener('click',function(){doRemoveBacklog(taskId,blb);});}"
        "else{blb.addEventListener('click',function(){doBacklog(taskId,blb);});}}"
        "if(openUrl){var eb=dc.querySelector('.view-email-btn');"
        "if(eb)eb.addEventListener('click',function(){showEmailInPane(openUrl);});}"
        "var titleEl=dc.querySelector('.detail-title-editable');"
        "if(titleEl){titleEl.addEventListener('blur',function(){"
        "var newTitle=this.textContent.trim();var orig=this.getAttribute('data-orig');"
        "if(newTitle&&newTitle!==orig){"
        "this.setAttribute('data-orig',newTitle);doUpdateTask(taskId,{content:newTitle});"
        "var card=document.getElementById('card-'+taskId);"
        "if(card){card.setAttribute('data-content',newTitle);"
        "var titleDiv=card.querySelector('.task-title');if(titleDiv)titleDiv.textContent=newTitle;}}"
        "});}"
        "var descDisplay=dc.querySelector('.detail-desc-display');"
        "var descSave=dc.querySelector('.detail-desc-save-btn');"
        "var descArea=dc.querySelector('.detail-desc-editable');"
        "if(descDisplay&&descArea&&descSave){"
        "descDisplay.addEventListener('click',function(e){if(e.target.tagName==='A')return;"
        "descDisplay.style.display='none';descArea.style.display='block';descSave.style.display='inline-block';"
        "descArea.style.height='auto';descArea.style.height=descArea.scrollHeight+'px';descArea.focus();});"
        "descSave.addEventListener('click',function(){"
        "var newDesc=descArea.value;descSave.disabled=true;descSave.textContent='Saving...';"
        "doUpdateTask(taskId,{description:newDesc},function(ok){"
        "if(ok){descSave.textContent='\\u2713 Saved';"
        "var card=document.getElementById('card-'+taskId);"
        "if(card)card.setAttribute('data-description',newDesc);"
        "descDisplay.textContent='';"
        "if(newDesc){descDisplay.innerHTML=linkify(esc(newDesc));}else{descDisplay.innerHTML='<span style=\\\"color:var(--text-3);font-style:italic;\\\">Click to add description...</span>';}"
        "setTimeout(function(){descArea.style.display='none';descSave.style.display='none';descDisplay.style.display='block';descSave.textContent='Save Description';descSave.disabled=false;},800);}"
        "else{descSave.textContent='Failed';descSave.disabled=false;}});});"
        "var _resizeTimer;descArea.addEventListener('input',function(){var el=this;clearTimeout(_resizeTimer);_resizeTimer=setTimeout(function(){el.style.height='auto';el.style.height=el.scrollHeight+'px';},50);});}"
        "dc.style.display='block';"
        "var vf=document.getElementById('viewer-frame');"
        "vf.src='about:blank';vf.style.display='none';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='flex';}}"
        "function showEmailInPane(url){"
        "document.getElementById('detail-content').style.display='none';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "var vf=document.getElementById('viewer-frame');vf.src=url;vf.style.display='block';}"
        "function closeViewer(){"
        "var vf=document.getElementById('viewer-frame');"
        "vf.src='about:blank';vf.style.display='none';"
        "var dc=document.getElementById('detail-content');"
        "dc.style.display='none';dc.innerHTML='';"
        "document.getElementById('viewer-placeholder').style.display='flex';"
        "document.querySelectorAll('.task-card').forEach(function(c){c.classList.remove('active-card');});"
        "if(window.innerWidth<=768){document.getElementById('viewer-pane').style.display='none';}}"
        "function getSelectedCards(){"
        "var cards=[];"
        "document.querySelectorAll('.select-cb:checked').forEach(function(cb){"
        "var card=cb.closest('.task-card');if(card)cards.push(card);});return cards;}"
        "function updateSelection(){"
        "var sel=getSelectedCards();var toolbar=document.getElementById('bulk-toolbar');"
        "var countEl=document.getElementById('bulk-count');"
        "if(sel.length>0){toolbar.style.display='flex';countEl.textContent=sel.length+' selected';}"
        "else{toolbar.style.display='none';}"
        "var allCbs=document.querySelectorAll('.select-cb');var allChecked=allCbs.length>0;"
        "allCbs.forEach(function(cb){if(!cb.checked)allChecked=false;});"
        "var sa=document.getElementById('select-all-cb');if(sa)sa.checked=allChecked;}"
        "function toggleSelectAll(){"
        "var sa=document.getElementById('select-all-cb');var checked=sa?sa.checked:false;"
        "document.querySelectorAll('.select-cb').forEach(function(cb){cb.checked=checked;});"
        "updateSelection();}"
        "function bulkMove(projectId){"
        "if(!projectId)return;var cards=getSelectedCards();"
        "cards.forEach(function(card){var taskId=card.getAttribute('data-task-id');"
        f'fetch("{base_action_url}&action=move&task_id="+taskId+"&project_id="+projectId)'
        ".then(function(r){if(r.ok){card.classList.add('removing');"
        "setTimeout(function(){card.remove();updateCount();updateSelection();},350);}});});}"
        "function bulkComplete(){"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){var taskId=card.getAttribute('data-task-id');"
        f'fetch("{base_action_url}&action=complete&task_id="+taskId)'
        ".then(function(r){if(r.ok){card.classList.add('removing');"
        "setTimeout(function(){card.remove();updateCount();updateSelection();},350);}});});}"
        "function bulkSetDueDate(dateValue){"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){var taskId=card.getAttribute('data-task-id');"
        "var input=card.querySelector('input[type=date]');"
        f'fetch("{base_action_url}&action=due_date&task_id="+taskId+"&date="+encodeURIComponent(dateValue))'
        ".then(function(r){if(r.ok&&input){"
        "input.value=dateValue;input.style.borderColor='rgba(34,197,94,0.5)';"
        "setTimeout(function(){input.style.borderColor='';},1500);}});});"
        "document.querySelectorAll('.select-cb:checked').forEach(function(cb){cb.checked=false;});"
        "updateSelection();}"
        # Schedule modal JS
        "var _schedTaskId=null,_schedMins=0;"
        "function openScheduleModal(taskId){"
        "_schedTaskId=taskId;_schedMins=0;"
        "document.querySelectorAll('.duration-opt').forEach(function(b){"
        "b.classList.remove('selected');});"
        "var btn=document.getElementById('schedule-confirm');"
        "btn.disabled=true;btn.textContent='Schedule';"
        "document.getElementById('schedule-overlay').classList.add('open');"
        "}"
        "function closeScheduleModal(){"
        "document.getElementById('schedule-overlay').classList.remove('open');"
        "_schedTaskId=null;_schedMins=0;"
        "}"
        "document.querySelectorAll('.duration-opt').forEach(function(b){"
        "b.addEventListener('click',function(){"
        "document.querySelectorAll('.duration-opt').forEach(function(x){x.classList.remove('selected');});"
        "this.classList.add('selected');"
        "_schedMins=parseInt(this.getAttribute('data-mins'));"
        "var n=_schedMins/30;"
        "document.getElementById('schedule-confirm').disabled=false;"
        "document.getElementById('schedule-confirm').textContent="
        "'Schedule '+n+' event'+(n>1?'s':'');"
        "});});"
        "document.getElementById('schedule-confirm').addEventListener('click',function(){"
        "if(!_schedTaskId||!_schedMins)return;"
        "var btn=this;btn.disabled=true;btn.textContent='Scheduling...';"
        f'fetch("{base_action_url}&action=schedule_action&task_id="+_schedTaskId+"&duration="+_schedMins)'
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.textContent='\\u2713 '+d.events_created+' events created!';"
        "btn.style.background='#22c55e';"
        "setTimeout(function(){closeScheduleModal();btn.style.background='';},1500);"
        "}else{"
        "btn.textContent='Failed: '+(d.error||'Unknown error');"
        "btn.disabled=false;btn.style.background='#ef4444';"
        "setTimeout(function(){btn.style.background='';btn.textContent='Schedule';},2000);"
        "}"
        "})"
        ".catch(function(e){"
        "btn.textContent='Error';btn.disabled=false;"
        "setTimeout(function(){btn.textContent='Schedule';},2000);"
        "});"
        "});"
        "</script>"
        "</body></html>"
    )
