# Feature Specification: Todoist Task Attachment Viewer (Mobile)

**Feature Branch**: `002-task-attachment-viewer`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "allow me to view attachments in todoist tasks when i click detailed view on aos mobile app"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Image Attachments Inline (Priority: P1)

A user on the AOS mobile app taps a Todoist task that has image attachments. When the detail pane opens, they can see the attachment thumbnails and tap one to view it full-size — without leaving the AOS app.

**Why this priority**: This is the primary use case. Currently tapping an image attachment triggers `target="_blank"`, which opens an external browser tab, breaking the in-app experience on mobile.

**Independent Test**: Open a Todoist task with an image attachment in AOS mobile detail view. Tap the image. Confirm it expands to full-size within the app UI (not in a new tab).

**Acceptance Scenarios**:

1. **Given** a task has one or more image attachments, **When** the user opens the task detail pane on mobile, **Then** image thumbnails are visible in the "Attachments & Comments" section.
2. **Given** an image thumbnail is visible, **When** the user taps it, **Then** the image expands to a full-screen lightbox overlay within the app.
3. **Given** the lightbox is open, **When** the user taps outside the image or a close button, **Then** the lightbox closes and returns to the detail pane.
4. **Given** multiple images are present, **When** the lightbox is open, **Then** the user can swipe or tap arrows to navigate between images.

---

### User Story 2 - Access Non-Image File Attachments (Priority: P2)

A user on AOS mobile taps a task that has a non-image file attachment (PDF, doc, etc.). They can tap the file link in the detail pane to download or open the file in a way that works within the mobile browser context.

**Why this priority**: Non-image attachments (PDFs, docs) are common in Todoist. The current `target="_blank"` behavior may work acceptably for file downloads but needs to be confirmed as mobile-appropriate.

**Independent Test**: Open a Todoist task with a PDF or doc attachment in AOS mobile. Tap the file. Confirm the file opens or prompts a download without requiring separate app navigation.

**Acceptance Scenarios**:

1. **Given** a task has a non-image file attachment, **When** the user opens the task detail pane, **Then** the file is listed with a recognizable file icon and name.
2. **Given** a file attachment link is visible, **When** the user taps it on mobile, **Then** the file opens or downloads without breaking the AOS app session.

---

### User Story 3 - Graceful Handling When No Attachments Exist (Priority: P3)

When a task has no attachments or comments, the detail pane shows no attachments section — not a loading spinner or empty placeholder.

**Why this priority**: UX polish — prevents user confusion about whether attachments failed to load.

**Independent Test**: Open a task with no comments/attachments in AOS mobile. Confirm no "Attachments & Comments" section or empty state is shown.

**Acceptance Scenarios**:

1. **Given** a task has no comments or attachments, **When** the detail pane loads, **Then** no attachment section or loading indicator is shown.
2. **Given** the attachment fetch API call fails, **When** the detail pane loads, **Then** the rest of the detail pane renders normally with no error shown to the user.

---

### Edge Cases

- What happens when an attachment URL has expired (Todoist CDN links may be time-limited)?
- How does the lightbox handle very tall or very wide images on a small screen?
- What if a task has more than 10 attachments?
- What if the attachment section is still loading when the user scrolls away or taps another task?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The detail pane MUST display image attachment thumbnails when a task has image file attachments in its comments.
- **FR-002**: Tapping an image thumbnail on mobile MUST open a full-screen inline lightbox (not a new browser tab).
- **FR-003**: The lightbox MUST include a close control (tap-outside or explicit close button).
- **FR-004**: When multiple images exist, the lightbox MUST support navigating between them.
- **FR-005**: Non-image file attachments MUST be tappable and open in a mobile-compatible manner (system browser download or preview).
- **FR-006**: If no comments or attachments exist for a task, the attachment section MUST NOT render.
- **FR-007**: If the attachment fetch fails, the detail pane MUST continue to render all other task information without error.

### Key Entities

- **Task Comment**: A Todoist comment on a task; may contain `file_attachment` with `file_url`, `file_name`, `file_type`, and `image` (thumbnail URL).
- **Image Attachment**: A comment with `file_type` starting with `image/` — displayed inline as a thumbnail.
- **File Attachment**: A comment with `file_type` not starting with `image/` — displayed as a named file link.
- **Lightbox**: Full-screen overlay for viewing an image within the app without leaving the current context.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view image attachments without leaving the AOS mobile app (0 navigations to external browser tabs for images).
- **SC-002**: Tapping an image thumbnail shows the full-size image in under 1 second on a standard mobile connection.
- **SC-003**: The lightbox is dismissible in 1 tap or gesture.
- **SC-004**: Multi-image navigation requires no more than 1 swipe or tap per image.
- **SC-005**: Tasks without attachments show no attachment UI, eliminating false "loading" states.

## Assumptions

- The existing `loadTaskAttachments` function and `task_comments` API endpoint are correct and return valid data — no backend changes are needed.
- Attachment image URLs from Todoist are publicly accessible (no additional auth headers required for `<img src>`).
- The feature targets the mobile breakpoint (viewport ≤ 768px) but the lightbox should also work on desktop.
- File attachment links for non-image types may continue to use browser-native behavior; no custom file viewer is required.
- No new API endpoints are required; this is a front-end change to `todoist_views.py`.
