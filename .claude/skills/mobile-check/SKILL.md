---
description:
  After deploying an ActionOS feature, run 10 mobile-specific QA tests at iPhone
  viewport (390x844) using Playwright, screenshot each result, and fix any issues
  found before reporting a final summary
---

# Mobile QA Check — ActionOS

Run this skill immediately after any ActionOS deploy to validate the new feature
on a mobile viewport. Follow every step in sequence without skipping.

---

## Context You Must Know Before Starting

- **ActionOS base URL**: `https://d6oxvq5j3kdwua7qdxtpkzueru0wjlkq.lambda-url.us-east-1.on.aws/`
- **Workspace root**: `/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/My-Workspace-TB-/My-Workspace-TB-/`
- **ActionOS source**: `apps/ActionOS/src/`
- **Deploy script**: Run from `apps/ActionOS/` → `./scripts/deploy-lambda-zip.sh`
- **Mobile viewport**: 390 wide × 844 tall (iPhone 14)
- **Auth token**: Read from `apps/ActionOS/credentials/` or `.env` if present; if not found, check `lambda_handler.py` for the token parameter name and read from AWS SSM or environment

---

## Step 1 — Understand the Recent Feature

Run these commands to understand what was just deployed:

```bash
cd /Users/terrancebrandon/Desktop/Code\ Projects\ \(Official\)/My\ Workspace/My-Workspace-TB-/My-Workspace-TB-
git log --oneline -5
git show HEAD --stat
```

After running:
- Read the commit messages and changed files
- Identify which ActionOS views or components were modified (e.g., `calendar_views.py`, `todoist_views.py`, `dashboard_shell.py`)
- Write a 2–3 sentence plain-English summary of what the feature does and what it changes in the UI

Do not proceed until you have this summary.

---

## Step 2 — Generate 10 Mobile-Specific QA Test Scenarios

Based on the feature summary from Step 1, generate exactly 10 test scenarios.
Each scenario must be specific to the feature just deployed AND address a
real mobile UX concern. Do not use generic placeholder tests.

For every test, define:
- **Test name** (short, descriptive)
- **What to navigate to** (URL path or tab)
- **What to check** (element, behavior, or visual concern)
- **Mobile UX concern being validated** (tap target, overflow, scroll, z-index, font size, modal fit, etc.)

### Required coverage areas (map these to the specific feature):

1. Primary feature element is visible on first paint — no scroll required
2. Primary interactive element (button, link, toggle) has tap target >= 44px height
3. No horizontal overflow or content clipped at 390px width
4. Any modal or popover fits within 390×844 without cropping
5. Text is readable — no font smaller than 14px on key labels
6. Action buttons are not obscured by sticky headers, footers, or overlays
7. Touch scroll works on any scrollable list or container
8. Feature still functions when accessed from a secondary tab or iframe
9. Empty state or loading state renders correctly at mobile size
10. Feature-specific edge case (e.g., long task title, many items, 0 items)

Adjust each scenario to name the actual element from the deployed feature. For
example, if a Schedule button was added, test #2 should read "Schedule button
has sufficient tap target height" not a generic description.

Print the full list of 10 tests before proceeding to Step 3.

---

## Step 3 — Run Tests With Playwright

For each of the 10 tests, execute this sequence exactly:

### 3a. Build the full URL

Start from the base URL:
```
https://d6oxvq5j3kdwua7qdxtpkzueru0wjlkq.lambda-url.us-east-1.on.aws/
```

If the feature lives in a specific tab or iframe, append the appropriate
query param or path (e.g., `?tab=calendar`, `?tab=todoist`). Check
`dashboard_shell.py` to confirm the tab parameter names if unsure.

### 3b. Navigate and set viewport

Use the Playwright MCP `playwright_navigate` tool with:
- `url`: the full URL for this test
- `width`: 390
- `height`: 844

Example call structure:
```
playwright_navigate(url="<full-url>", width=390, height=844)
```

### 3c. Take a screenshot

Use `playwright_screenshot` with:
- `name`: `qa-test-{N}-{kebab-case-test-name}` (e.g., `qa-test-1-feature-visible-on-load`)
- `savePng`: true
- `fullPage`: false (capture viewport only, simulating phone screen)

### 3d. Evaluate the screenshot

After each screenshot, examine the image and record:
- PASS: the element/behavior is correct at mobile size
- FAIL: describe exactly what is wrong (overflow, clipped, too small, hidden, etc.)

### 3e. Repeat for all 10 tests

Do not batch or skip. Run one test at a time, screenshot, evaluate, then move
to the next. After all 10, compile the results list before proceeding to Step 4.

---

## Step 4 — Fix Any Issues Found

For each FAIL result:

### 4a. Identify the source file

Check which source file controls the failing element:

| UI area                  | Source file                          |
|--------------------------|--------------------------------------|
| Shell, tabs, header      | `src/dashboard_shell.py`             |
| Calendar tab             | `src/calendar_views.py`              |
| Todoist / Tasks tab      | `src/todoist_views.py`               |
| Home / Overview tab      | `src/home_views.py`                  |
| Follow-up tab            | `src/followup_views.py`              |
| Email / Gmail tab        | `src/email_report.py`                |
| Code / diff views        | `src/code_views.py`                  |

Read the relevant file before making any edits.

### 4b. Apply targeted fixes

Common mobile fixes and where to apply them:

- **Tap target too small**: add `min-height: 44px; min-width: 44px; padding: 10px 16px;` to the button or link style
- **Horizontal overflow**: add `overflow-x: hidden; max-width: 100%; box-sizing: border-box;` to the container
- **Modal clips at bottom**: add `max-height: 90vh; overflow-y: auto;` to the modal wrapper
- **Button hidden behind header**: increase `z-index` on the button or add `padding-top` to the content area
- **Text too small**: set `font-size: 14px` minimum on label elements
- **Content requires horizontal scroll**: replace fixed pixel widths with `width: 100%` or `max-width: 100%`
- **Sticky element covers interactive area**: adjust `bottom` offset or add `padding-bottom` to scrollable container

Make only the minimum change needed. Do not refactor or rewrite unrelated code.

### 4c. Redeploy

After all fixes are applied, run the deploy script once for all changes:

```bash
cd /Users/terrancebrandon/Desktop/Code\ Projects\ \(Official\)/My\ Workspace/My-Workspace-TB-/My-Workspace-TB-/apps/ActionOS
./scripts/deploy-lambda-zip.sh
```

Wait for the deploy to complete before re-testing.

### 4d. Re-test fixed scenarios

For each scenario that previously FAILED, re-run the Playwright test:
- Navigate to the same URL with 390×844 viewport
- Take a new screenshot named `qa-test-{N}-{test-name}-fixed`
- Mark as PASS or still FAIL

If still FAIL after the fix, investigate further — read the rendered HTML with
`playwright_get_visible_html` using a CSS selector targeting the broken element,
then adjust the fix and redeploy again.

---

## Step 5 — Final Summary Report

After all tests are complete (and fixes verified), output this report:

```
## Mobile QA Summary — [Feature Name] — [Date]

### Viewport: 390×844 (iPhone 14)

### Test Results

| # | Test Name                        | Result | Notes                          |
|---|----------------------------------|--------|--------------------------------|
| 1 | [test name]                      | PASS   |                                |
| 2 | [test name]                      | PASS   |                                |
| 3 | [test name]                      | FAIL → FIXED | Added min-height to button |
...

### Issues Fixed
- [File changed] — [What was changed and why]

### Screenshots Taken
- qa-test-1-[name].png
- qa-test-2-[name].png
...

### Overall Result
[All 10 tests passing / X issues remain open]
```

If any tests remain FAIL after attempted fixes, list them explicitly and
describe what investigation is needed next.

---

## Error Handling

**If the ActionOS URL is unreachable:**
Check that the Lambda function is deployed. Run:
```bash
aws lambda get-function --function-name actionos-lambda --query 'Configuration.LastModified'
```
If not recently updated, redeploy first.

**If a Playwright navigate times out:**
The Lambda cold start may be slow. Wait 10 seconds and retry the same URL once.

**If a screenshot shows a blank or error page:**
Use `playwright_get_visible_text` to read the page content and diagnose whether
it is a 500 error, auth failure, or missing tab parameter. Check `lambda_handler.py`
for the correct routing logic.

**If the deploy script fails:**
Read the error output. Common causes: missing AWS credentials (run
`aws configure list`), or Python syntax error in a modified source file (run
`python -m py_compile src/<file>.py` to validate before redeploying).

---

## Trigger

Invoke this skill after any ActionOS deploy by typing:

```
/mobile-check
```

No arguments required. The skill reads context from git history automatically.
