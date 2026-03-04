---
description:
  After deploying any ActionOS change that touches app.py, lambda_handler.py,
  or any src/ view file, measure TTFB and DCL for 6 key endpoints against
  established baselines, check cache-warming logs, and report pass/fail with
  regression diagnosis if any budget is exceeded
---

# Performance Check — ActionOS

Run this skill immediately after any deploy that modifies `app.py`,
`lambda_handler.py`, or any file under `src/`. Follow every step in
sequence without skipping.

---

## Context You Must Know Before Starting

- **ActionOS base URL**: `https://actionos-production.up.railway.app`
- **Workspace root**: `/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/My-Workspace-TB-/My-Workspace-TB-/`
- **ActionOS source**: `apps/ActionOS/src/`
- **Platform**: Railway (Flask + Gunicorn). Deploy via Railway CLI or git push.
- **Auth**: The session cookie is named `aos_session`. Retrieve the token from
  AWS SSM at `/action-dashboard/action-token` (see Step 2 for the exact
  authentication flow).
- **Cache warming**: On startup, `app.py` warms shell, home, calendar, and
  code views in a background thread. Inbox and follow-up are NOT pre-warmed.
- **Log prefix**: Cache warming events are tagged `[cache-warm]` in Railway
  logs.

---

## Baselines

These budgets were established after the server-side in-memory caching fix
(5-minute TTL) was deployed. Any endpoint that exceeds its budget is a
regression.

| Endpoint              | TTFB Budget | DCL Budget |
|-----------------------|-------------|------------|
| Shell (full page)     | 800ms       | 1500ms     |
| Home (cached)         | 200ms       | 500ms      |
| Calendar (cached)     | 200ms       | 500ms      |
| Code (cached)         | 200ms       | 500ms      |
| Inbox (uncached)      | 3000ms      | 5000ms     |
| Follow-up (uncached)  | 3000ms      | 5000ms     |

---

## Step 1 — Identify What Changed

Run these commands from the workspace root to understand which files were
modified in the last 3 commits:

```bash
cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/My-Workspace-TB-/My-Workspace-TB-"
git log --oneline -3
git diff HEAD~3 HEAD --stat -- apps/ActionOS/
```

After running:
- List which files changed (e.g., `src/calendar_views.py`, `app.py`,
  `lambda_handler.py`)
- Note any new external API calls, added loops, or removed caching logic — these
  are the most common sources of performance regressions
- Write a 1–2 sentence summary of what the change does

Do not proceed until you have this summary. It will be used in Step 5 to
attribute any regressions to a specific change.

---

## Step 2 — Authenticate With Playwright

The app requires an `aos_session` cookie. Retrieve the token and set it via
the login form before navigating to any measured URL.

### 2a. Fetch the token from SSM

```bash
aws ssm get-parameter \
  --name "/action-dashboard/action-token" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text
```

Store this value — it is the `<token>` used in Step 2b.

### 2b. Log in via the login page

Navigate to the login page and submit the token through the form:

```
playwright_navigate(url="https://actionos-production.up.railway.app/?action=login")
```

After the page loads, fill the token field and submit. The server will set the
`aos_session` cookie in the browser session. All subsequent Playwright
navigations in this session will carry the cookie automatically.

If no login form is visible, use `playwright_get_visible_html` to read the
page and determine the correct selector. If the app redirects directly to the
shell, the session cookie was already set — proceed to Step 3.

---

## Step 3 — Measure TTFB and DCL for All 6 Endpoints

For each endpoint below, navigate to the URL, wait for the page to load, then
read timing data from the Navigation Timing API. Measure in this exact order
(shell first, then cached views, then uncached views).

### Endpoints to measure

| Label         | URL                                                                  |
|---------------|----------------------------------------------------------------------|
| Shell         | `https://actionos-production.up.railway.app/?action=web`            |
| Home          | `https://actionos-production.up.railway.app/?action=web&embed=1&view=home`     |
| Calendar      | `https://actionos-production.up.railway.app/?action=web&embed=1&view=calendar` |
| Code          | `https://actionos-production.up.railway.app/?action=web&embed=1&view=code`     |
| Inbox         | `https://actionos-production.up.railway.app/?action=web&embed=1&view=inbox`    |
| Follow-up     | `https://actionos-production.up.railway.app/?action=web&embed=1&view=followup` |

### Measurement sequence (repeat for each endpoint)

**3a. Navigate to the URL:**

For **cached endpoints** (Home, Calendar, Code), use a 120-second timeout to
account for cold-start on the first load after deploy:

```
playwright_navigate(url="<endpoint-url>", waitUntil="domcontentloaded", timeout=120000)
```

For **Shell, Inbox, and Follow-up**, use the default timeout (30 seconds).

**3b. Read timing values:**

```
playwright_evaluate(script=`
  (() => {
    const e = performance.getEntriesByType('navigation')[0];
    return {
      ttfb: Math.round(e.responseStart),
      dcl: Math.round(e.domContentLoadedEventEnd)
    };
  })()
`)
```

Record `ttfb` and `dcl` (both in milliseconds) for this endpoint.

**3c. If a cached endpoint (Home/Calendar/Code) shows TTFB > 5000ms:**

This means the HTML cache was cold — the 120s navigation forced the server to
build and cache the view. **Immediately navigate to the same URL again** (no
timeout needed this time) and re-read timing. The second load will hit the
in-memory cache and should return TTFB < 200ms.

Record only the second (cached) measurement for the baseline comparison.
If the second load is also slow, that is a genuine regression — record it.

**3d. Compare against the baseline table above.**
Mark each endpoint as PASS or FAIL:
- PASS: both `ttfb` and `dcl` are within budget
- FAIL: either `ttfb` or `dcl` exceeds its budget

Do not skip any endpoint. If a navigate times out even at 120 seconds, record
`TIMEOUT`, check Step 4 logs, and investigate before continuing.

---

## Step 4 — Check Cache Warming Logs

Run this command from the ActionOS app directory to read the last 100 lines of
Railway logs:

```bash
cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/My-Workspace-TB-/My-Workspace-TB-/apps/ActionOS"
railway logs --tail 100
```

Scan the output for `[cache-warm]` entries. Report:

- **Success logs do NOT exist** — the warm function only emits a log line when
  something goes wrong. Absence of failure logs = warming was attempted and
  completed without errors. Do NOT conclude warming failed just because there
  are no success entries.
- Any failure entries matching `[cache-warm] ... failed:` — these indicate a
  broken warming step and will cause the next request to that view to be slow
- Whether `[cache-warm] outer failure:` appears — this means the entire warming
  block crashed and no views were warmed at all

If no `[cache-warm]` entries appear at all, two possibilities:
1. The app was not restarted during the deploy window captured by these logs
   (e.g., Railway did an in-place reload, or logs only go back to before startup)
2. Warming completed cleanly with no errors (the normal case)

Check whether the logs include an app startup line (e.g., Gunicorn `Listening
at:` or `Booting worker`). If yes and no `[cache-warm] X failed:` entries
appear, warming succeeded. Note this explicitly in the report.

---

## Step 5 — Report

Output the full performance report in this format:

```
## Performance Check — [YYYY-MM-DD]

### What Changed
[1-2 sentence summary from Step 1. List the specific files that changed.]

### Timing Results

| Endpoint      | TTFB   | DCL     | TTFB Budget | Status  |
|---------------|--------|---------|-------------|---------|
| Shell         | 234ms  | 890ms   | 800ms       | PASS    |
| Home          | 18ms   | 120ms   | 200ms       | PASS    |
| Calendar      | 22ms   | 134ms   | 200ms       | PASS    |
| Code          | 19ms   | 118ms   | 200ms       | PASS    |
| Inbox         | 1240ms | 3100ms  | 3000ms      | PASS    |
| Follow-up     | 2800ms | 4200ms  | 3000ms      | PASS    |

### Cache Warming
[List which views warmed successfully, any failures, and whether the outer
block succeeded. Example: "shell, home, calendar, code all warmed. No
failures detected."]

### Result
[PASS — all endpoints within budget.]
```

### If any endpoint FAILs

When one or more endpoints exceed their budget, add a regression analysis
section immediately after the table:

```
### Regression Analysis

**Failing endpoints:** [list them with their measured vs. budget values]

**Files changed in recent commits:** [from Step 1]

**Likely cause:** [Identify which change probably caused the regression.
Examples:
- "calendar_views.py now fetches from a new external API endpoint on every
  request — this bypasses the cache and adds ~900ms"
- "app.py removed the _warm_caches() call for the home view — the first
  request now cold-starts instead of hitting cache"
- "lambda_handler.py added a synchronous database write inside the cached
  path, adding overhead to every cached response"]

**Recommendation:**
```

Then choose ONE of these recommendations based on severity:

**Rollback** — If TTFB exceeds 2x the budget on a cached endpoint (e.g.,
Home > 400ms, Calendar > 400ms, Code > 400ms), or if Shell exceeds 2000ms:

```
Recommend rollback. The regression is severe enough to impact user experience
on mobile. Run:

  railway rollback

Then re-run /perf-check to confirm the previous version restores baseline.
```

**Optimize** — If TTFB is over budget but under 2x the budget, or if only
uncached endpoints are failing:

```
Recommend optimization before the next deploy. Suggested fix:
[Specific code-level suggestion, e.g., "Move the new API call inside the
cached branch in _get_calendar_html() so it only runs on cache miss, not
on every request."]
```

---

## Error Handling

**If the ActionOS URL is unreachable (connection refused or 502):**
The Railway service may be crashed or deploying. Check Railway status:

```bash
cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/My-Workspace-TB-/My-Workspace-TB-/apps/ActionOS"
railway status
```

Wait 30 seconds for deployment to complete, then retry the navigate.

**If `playwright_navigate` times out on a cached endpoint (Home/Calendar/Code):**
This is often a cold-start, NOT a regression — especially on the first
measurement after a fresh deploy. The `_view_html_cache` has a 5-minute TTL,
so if the cache hasn't been populated yet (warming failed or the cache entry
expired), the server must build the view from scratch.

**Diagnosis protocol:**
1. Re-navigate to the same endpoint with `timeout=120000` — this forces the
   server to build and populate the cache.
   - If it completes in 10–60 seconds: cold-start is expected. Immediately
     navigate again; the second load should be <200ms. Record the cached time.
   - If it still times out at 120 seconds: something is broken. Check logs.

2. **Calendar cold-start** specifically can take 40+ seconds — it fetches
   8–10 Google Calendar API endpoints sequentially (httplib2 is not
   thread-safe, preventing parallelism). This is a known architectural
   constraint, NOT a regression.

3. An additional delay (~10–20s) may occur if the FFM sync runs. This happens
   when the `state-bucket` SSM param is unavailable, preventing persistence of
   `ffm_last_sync`, causing a full sync on every uncached load. This is a
   pre-existing issue, not caused by recent changes — do not attribute it as a
   regression unless it was previously absent.

4. After the 120s cold load completes, **always re-measure**. If the second
   load is within budget, record PASS. Only record FAIL if the second
   (cached) load exceeds the budget.

**If `performance.getEntriesByType('navigation')[0]` returns null:**
The page may have redirected (e.g., auth redirect to login). Run
`playwright_get_visible_text` to check the page content. If it shows the
login page, the `aos_session` cookie was not set — redo Step 2.

**If `railway logs` returns no output or an auth error:**
Ensure the Railway CLI is logged in:

```bash
railway whoami
```

If not logged in, run `railway login` and authenticate, then re-run the
logs command.

**If the SSM parameter fetch fails:**
Check AWS credentials are configured:

```bash
aws sts get-caller-identity
```

If this fails, the session has expired. Re-authenticate with AWS before
re-running the skill.

---

## Source File Reference

Use this table when attributing regressions to specific views:

| View       | Source file                       |
|------------|-----------------------------------|
| Shell      | `src/dashboard_shell.py`          |
| Home       | `src/home_views.py`               |
| Calendar   | `src/calendar_views.py`           |
| Code       | `src/code_views.py`               |
| Inbox      | `src/todoist_views.py`            |
| Follow-up  | `src/followup_views.py`           |
| Auth/cache | `lambda_handler.py`               |
| Scheduling | `app.py`                          |

---

## Trigger

Invoke this skill after any deploy that touches `app.py`, `lambda_handler.py`,
or any file under `src/` by typing:

```
/perf-check
```

No arguments required. The skill reads recent commit context from git
automatically.
