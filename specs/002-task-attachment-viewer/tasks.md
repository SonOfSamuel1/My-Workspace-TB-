# Tasks: Todoist Task Attachment Viewer (Mobile)

**Input**: Design documents from `specs/002-task-attachment-viewer/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅ **Tests**: Not
requested — no test tasks generated **Organization**: Tasks grouped by user
story; all changes in one file: `apps/ActionOS/src/todoist_views.py`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (touches a different section of the file, no
  dependency on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

No project setup required — this feature modifies an existing file with no new
dependencies, no new routes, and no build step.

---

## Phase 2: Foundational (Lightbox Scaffolding)

**Purpose**: Add the lightbox CSS and HTML element that User Story 1 depends on.
Both tasks touch different sections of `todoist_views.py` and can be done in
parallel.

**⚠️ CRITICAL**: US1 implementation cannot begin until both T001 and T002 are
complete.

- [ ] T001 [P] Add lightbox CSS rules to the `<style>` string block in
      `apps/ActionOS/src/todoist_views.py` (insert after `.detail-attachments`
      block, around line 688) — rules for `#lb-overlay`, `#lb-img`, `#lb-close`,
      `#lb-prev`, `#lb-next`, `#lb-counter` as specified in plan.md Phase 1
- [ ] T002 [P] Add `#lb-overlay` HTML element to the viewer pane in
      `apps/ActionOS/src/todoist_views.py` (insert after
      `<iframe id="viewer-frame">`, around line 739) — full element with close,
      prev/next buttons, img, counter, and
      `onclick="if(event.target===this)closeLightbox()"` on the overlay as
      specified in plan.md Phase 2

**Checkpoint**: Lightbox scaffold in place — invisible until triggered. Ready
for US1 JS wiring.

---

## Phase 3: User Story 1 — View Image Attachments Inline (Priority: P1) 🎯 MVP

**Goal**: Replace `target="_blank"` image links in `loadTaskAttachments` with
in-app lightbox. Users tap an image thumbnail and see it full-screen inside AOS
without leaving the app.

**Independent Test**: Open AOS on mobile with a Todoist task that has ≥1 image
attachment. Tap the task → tap the image thumbnail → confirm full-screen
lightbox opens within the app (no new browser tab).

### Implementation for User Story 1

- [ ] T003 [US1] Modify the image-attachment branch of `loadTaskAttachments` in
      `apps/ActionOS/src/todoist_views.py` (lines ~1142–1151) — declare
      `var lbImgs=[]` before the `d.comments.forEach` loop; replace the
      `<a href="..." target="_blank"><img ...></a>` pattern with
      `<div class="attachment-item" style="cursor:pointer;" onclick="openLightbox(lbImgs,LBIDX)"><img ...></div>`
      where each image pushes `fu||img` to `lbImgs` and uses
      `var lbIdx=lbImgs.length` before the push for the index
- [ ] T004 [US1] Add `_lbUrls`, `_lbIdx` state variables and `_lbRender`,
      `_lbKey` helper functions in `apps/ActionOS/src/todoist_views.py` (insert
      after `loadTaskAttachments` function, before `showEmailInPane` around
      line 1166) — `_lbRender` sets `#lb-img` src, shows/hides nav buttons,
      updates counter text; `_lbKey` handles Escape/ArrowLeft/ArrowRight
      (depends on T001, T002)
- [ ] T005 [US1] Add `openLightbox`, `closeLightbox`, `lightboxNav` functions in
      `apps/ActionOS/src/todoist_views.py` (same insertion point as T004, after
      `_lbKey`) — `openLightbox(urls,idx)` sets state, calls `_lbRender`, adds
      `lb-open` class, registers `_lbKey` keydown listener, attaches named touch
      handlers (`window._lbTouchStart`, `window._lbTouchEnd`) for
      swipe-left/right; `closeLightbox()` removes `lb-open` class, removes all
      listeners; `lightboxNav(dir)` wraps index and calls `_lbRender` — use the
      revised touch handler with cleanup from plan.md Implementation Notes
      (depends on T004)

**Checkpoint**: Image attachments open in lightbox on mobile. Swipe navigation,
ESC, tap-outside-to-close all work. No new browser tab opened for images.

---

## Phase 4: User Story 2 — Access Non-Image File Attachments (Priority: P2)

**Goal**: Confirm non-image file attachments (PDFs, docs) still render as
tappable links that open via native browser behavior. No regression from US1
changes.

**Independent Test**: Open AOS with a Todoist task that has a non-image file
attachment. Tap the task → confirm file name and icon appear in detail pane →
tap the link → confirm native browser download/preview is triggered (not a
lightbox).

### Implementation for User Story 2

- [ ] T006 [US2] Verify the `else if(fu)` branch in the modified
      `loadTaskAttachments` in `apps/ActionOS/src/todoist_views.py` retains
      `target="_blank"` on the `<a>` element and that the non-image path was not
      altered by T003; if any regression exists, restore the original
      `else if(fu)` block exactly as defined in plan.md Phase 3

**Checkpoint**: Non-image file attachments open via native browser. Image and
file paths are independent. US1 and US2 both functional.

---

## Phase 5: User Story 3 — Graceful No-Attachment State (Priority: P3)

**Goal**: Tasks with no comments/attachments show no attachment section in the
detail pane. Tasks with a failed attachment fetch still render all other detail
content normally.

**Independent Test**: Open AOS with a Todoist task that has zero comments.
Confirm the detail pane renders with title, meta, description, and actions — no
"Attachments & Comments" header, no spinner, no empty block.

### Implementation for User Story 3

- [ ] T007 [US3] Verify the early-exit guard in `loadTaskAttachments` in
      `apps/ActionOS/src/todoist_views.py`
      (`if(!d.ok||!d.comments||!d.comments.length)return;`) is still present and
      untouched after T003 modifications; also confirm the
      `.catch(function(){})` silent error handler remains so a failed fetch does
      not surface an error to the user

**Checkpoint**: No-attachment and error cases are silent and correct. All three
user stories functional.

---

## Phase 6: Polish & Deploy

**Purpose**: Deploy and smoke-test on real mobile device.

- [ ] T008 Deploy updated `todoist_views.py` to AWS Lambda via
      `./scripts/deploy-lambda-zip.sh` from `apps/ActionOS/`
- [ ] T009 [P] Smoke test on mobile browser (≤768px viewport): open a task with
      image attachments → tap image → verify lightbox full-screen, swipe
      navigation, close gesture; open a task with a non-image file → tap file →
      verify native download; open a task with no attachments → verify no
      attachment section appears
- [ ] T010 [P] Smoke test on desktop browser: same three scenarios — verify
      lightbox works with keyboard (ESC closes, arrow keys navigate),
      click-outside closes lightbox, file link opens in new tab

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: Start immediately — T001 and T002 are independent
  and can run in parallel
- **US1 (Phase 3)**: Depends on T001 + T002 complete; T003 → T004 → T005 are
  sequential within phase
- **US2 (Phase 4)**: Depends on T003 complete (verification of the modified
  else-branch)
- **US3 (Phase 5)**: Depends on T003 complete (verification of the early-exit
  guard)
- **Polish (Phase 6)**: Depends on T003–T007 all complete; T009 and T010 can run
  in parallel

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational (T001, T002)
- **US2 (P2)**: Depends on T003 (same function as US1 modifications)
- **US3 (P3)**: Depends on T003 (same function as US1 modifications)
- **US2 and US3 can run in parallel** after T003 completes

### Within US1

- T003 → T004 → T005 (sequential — functions call each other)

---

## Parallel Execution Examples

### Foundational Phase

```
# Run in parallel:
Task agent A: T001 — Add lightbox CSS to <style> block (~line 688)
Task agent B: T002 — Add #lb-overlay HTML to viewer pane (~line 739)
```

### After T003 Completes (US2 + US3)

```
# Run in parallel:
Task agent A: T006 — Verify non-image file attachment branch (US2)
Task agent B: T007 — Verify no-attachment early-exit guard (US3)
```

### Smoke Tests (after deploy)

```
# Run in parallel:
Task agent A: T009 — Mobile browser smoke test
Task agent B: T010 — Desktop browser smoke test
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete T001 + T002 (foundational scaffolding)
2. Complete T003 → T004 → T005 (US1 lightbox wiring)
3. **STOP and VALIDATE**: Tap an image attachment on mobile — lightbox opens
   in-app
4. Deploy T008 and confirm on device

### Full Delivery (all 3 user stories)

1. T001 + T002 in parallel
2. T003 → T004 → T005 (US1)
3. T006 + T007 in parallel (US2 + US3 verification)
4. T008 deploy → T009 + T010 smoke tests in parallel

---

## Notes

- All 10 tasks modify or verify a single file:
  `apps/ActionOS/src/todoist_views.py`
- No new files, no backend changes, no dependency additions
- T006 and T007 are verification tasks — they confirm no regression; if the code
  is correct from T003, they may be zero-effort
- The `lbImgs` array in `loadTaskAttachments` is declared in the `.then()`
  callback scope and passed by reference to `openLightbox()` — this is correct;
  no closure-over-loop-variable bug exists
- Pre-commit hooks (black, isort, flake8, bandit) run on Python —
  `todoist_views.py` must pass all linters before commit
