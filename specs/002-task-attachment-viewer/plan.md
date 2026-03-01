# Implementation Plan: Todoist Task Attachment Viewer (Mobile)

**Branch**: `002-task-attachment-viewer` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-task-attachment-viewer/spec.md`

## Summary

Replace `target="_blank"` image-attachment links in the AOS task detail pane with an in-app full-screen lightbox. When a user taps an image attachment on mobile, a fixed overlay opens the image full-size with swipe navigation and a close control — keeping the user inside the AOS app. Non-image file attachments retain native browser download behavior. All changes are confined to a single file: `apps/ActionOS/src/todoist_views.py`.

## Technical Context

**Language/Version**: Python 3.11 (server-side HTML/JS generator)
**Primary Dependencies**: None new — pure vanilla JS/CSS embedded as Python string literals
**Storage**: N/A
**Testing**: Manual browser testing on mobile viewport (≤768px); `--validate` flag smoke-test
**Target Platform**: Mobile Safari / Chrome on iOS and Android; responsive breakpoint at 768px
**Project Type**: AWS Lambda web app (HTML served as response body)
**Performance Goals**: Lightbox image visible within 1 second on mobile connection
**Constraints**: No external CDN dependencies; no npm build step; self-contained single-file HTML output
**Scale/Scope**: Single-user personal app; ~1 file changed, ~80 lines added

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| Automation-First | ✅ PASS | Web feature in existing Lambda app; no new interactive prompts or GUI deps |
| Convention Over Configuration | ✅ PASS | Follows existing inline JS/CSS pattern in `todoist_views.py` |
| Personal-Scale Simplicity | ✅ PASS | No feature flags, no multi-tenancy; YAGNI — vanilla JS only |
| Observability | ✅ PASS | No new Lambda routes; existing CloudWatch logging unchanged |
| Spec-Driven Development | ✅ PASS | Following specify → plan → tasks → implement lifecycle |

No violations. No complexity tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/002-task-attachment-viewer/
├── spec.md              # Feature requirements
├── plan.md              # This file
├── research.md          # Phase 0 research decisions
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (from /speckit-tasks)
```

### Source Code (repository root)

```text
apps/ActionOS/src/
└── todoist_views.py     # Only file modified — all changes here
```

No new files are created. No backend changes. No dependency additions.

## Implementation Phases

### Phase 1: Lightbox CSS

**File**: `apps/ActionOS/src/todoist_views.py`
**Location**: The `<style>` block (around line 688 where `.detail-attachments` is defined)

Add the following CSS rules to the existing style string:

```css
/* Lightbox overlay */
#lb-overlay {
  display: none;
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 1000;
  background: rgba(0,0,0,0.92);
  flex-direction: column;
  align-items: center;
  justify-content: center;
  touch-action: none;
}
#lb-overlay.lb-open { display: flex; }
#lb-img {
  max-width: 95vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 4px;
  user-select: none;
  -webkit-user-drag: none;
}
#lb-close {
  position: absolute;
  top: 14px; right: 18px;
  font-size: 32px;
  color: #fff;
  background: none;
  border: none;
  cursor: pointer;
  line-height: 1;
  opacity: 0.85;
}
#lb-close:hover { opacity: 1; }
#lb-prev, #lb-next {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  font-size: 28px;
  color: rgba(255,255,255,0.7);
  background: none;
  border: none;
  cursor: pointer;
  padding: 12px 16px;
  user-select: none;
}
#lb-prev { left: 4px; }
#lb-next { right: 4px; }
#lb-prev:hover, #lb-next:hover { color: #fff; }
#lb-counter {
  position: absolute;
  bottom: 16px;
  color: rgba(255,255,255,0.6);
  font-size: 13px;
  font-family: inherit;
}
```

### Phase 2: Lightbox HTML Element

**File**: `apps/ActionOS/src/todoist_views.py`
**Location**: Inside the `#viewer-pane` div (after the `<iframe id="viewer-frame">` element, before the closing `</div>`)

Add one HTML block to the viewer pane:

```html
<div id="lb-overlay" role="dialog" aria-modal="true">
  <button id="lb-close" onclick="closeLightbox()" aria-label="Close">&times;</button>
  <button id="lb-prev" onclick="lightboxNav(-1)" aria-label="Previous">&#8249;</button>
  <img id="lb-img" src="" alt="">
  <button id="lb-next" onclick="lightboxNav(1)" aria-label="Next">&#8250;</button>
  <span id="lb-counter"></span>
</div>
```

### Phase 3: Modify `loadTaskAttachments` JS

**File**: `apps/ActionOS/src/todoist_views.py`
**Location**: The `loadTaskAttachments` function (lines ~1132–1165)

**Current behavior for images:**
```js
if(ft.indexOf('image/')===0&&(img||fu)){
  ah+='<div class="attachment-item">';
  ah+='<a href="'+(fu||img)+'" target="_blank">';
  ah+='<img src="'+(img||fu)+'" alt="'+esc(fn)+'" style="max-height:300px;">';
  ah+='</a></div>';
}
```

**New behavior:**
- Collect all image URLs into a JS array `lbImgs` before the `forEach` loop
- For each image, instead of an anchor with `target="_blank"`, render a `<div onclick="openLightbox(lbImgs,N)">` where N is the image's index in the array

**Replacement logic** (replaces the entire image attachment branch):
```js
// Before forEach, collect image data:
var lbImgs=[];
d.comments.forEach(function(c){
  var fa=c.file_attachment;
  if(fa){
    var ft=fa.file_type||'';
    var fn=fa.file_name||'File';
    var fu=fa.file_url||'';
    var img=fa.image||'';
    if(ft.indexOf('image/')===0&&(img||fu)){
      var lbIdx=lbImgs.length;
      lbImgs.push(fu||img);                         // full-res for lightbox
      ah+='<div class="attachment-item" style="cursor:pointer;" '
        +'onclick="openLightbox(lbImgs,'+lbIdx+')">';
      ah+='<img src="'+(img||fu)+'" alt="'+esc(fn)+'" style="max-height:300px;">';
      ah+='</div>';
    } else if(fu){
      // Non-image: keep target="_blank" for native browser download
      ah+='<div class="attachment-item">';
      ah+='<a href="'+fu+'" target="_blank">';
      ah+='<svg class="attachment-file-icon" viewBox="0 0 24 24" fill="none" '
        +'stroke="currentColor" stroke-width="2">'
        +'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        +'<polyline points="14 2 14 8 20 8"/></svg>';
      ah+=esc(fn)+'</a></div>';
    }
  }
  if(c.content){
    ah+='<div class="comment-text">'+esc(c.content)+'</div>';
  }
});
```

**Note**: The `lbImgs` variable must be declared in the outer scope of the `.then` callback so the `onclick` closures capture it correctly. Since each `openLightbox(lbImgs, lbIdx)` call is inlined in the HTML string, the array reference is passed at call time — this works correctly because `lbImgs` is in the enclosing `.then` function scope.

### Phase 4: Add Lightbox JS Functions

**File**: `apps/ActionOS/src/todoist_views.py`
**Location**: After the `loadTaskAttachments` function definition (line ~1166), before `showEmailInPane`

Add three functions:

```js
// Lightbox state
var _lbUrls=[], _lbIdx=0;

function openLightbox(urls, idx){
  _lbUrls=urls; _lbIdx=idx;
  _lbRender();
  var ov=document.getElementById('lb-overlay');
  ov.classList.add('lb-open');
  document.addEventListener('keydown',_lbKey);
  // Touch swipe setup
  var tx=null;
  ov.addEventListener('touchstart',function(e){tx=e.touches[0].clientX;},{passive:true});
  ov.addEventListener('touchend',function(e){
    if(tx===null)return;
    var dx=e.changedTouches[0].clientX-tx;
    if(Math.abs(dx)>50)lightboxNav(dx<0?1:-1);
    tx=null;
  },{passive:true});
}

function closeLightbox(){
  document.getElementById('lb-overlay').classList.remove('lb-open');
  document.removeEventListener('keydown',_lbKey);
}

function lightboxNav(dir){
  _lbIdx=(_lbIdx+dir+_lbUrls.length)%_lbUrls.length;
  _lbRender();
}

function _lbRender(){
  document.getElementById('lb-img').src=_lbUrls[_lbIdx];
  var c=document.getElementById('lb-counter');
  var p=document.getElementById('lb-prev');
  var n=document.getElementById('lb-next');
  if(_lbUrls.length>1){
    c.textContent=(_lbIdx+1)+' / '+_lbUrls.length;
    p.style.display=''; n.style.display='';
  }else{
    c.textContent=''; p.style.display='none'; n.style.display='none';
  }
}

function _lbKey(e){
  if(e.key==='Escape')closeLightbox();
  if(e.key==='ArrowRight')lightboxNav(1);
  if(e.key==='ArrowLeft')lightboxNav(-1);
}
```

**Click-outside-to-close**: Add `onclick` directly on `#lb-overlay` that calls `closeLightbox()` only when the click target is the overlay itself (not the image or nav buttons):

```js
// On the lb-overlay element in HTML:
onclick="if(event.target===this)closeLightbox()"
```

This replaces the separate `onclick="closeLightbox()"` call shown in the HTML phase above.

### Phase 5: Smoke Test

1. Deploy to Lambda via `./scripts/deploy-lambda-zip.sh`
2. Open AOS on mobile browser
3. Navigate to a Todoist view with a task that has image attachments
4. Tap the task → verify detail pane opens
5. Tap an image thumbnail → verify lightbox opens full-screen (no new tab)
6. Swipe left/right → verify navigation (if multiple images)
7. Tap outside or press close → verify lightbox closes, detail pane intact
8. Open a task with a non-image file → verify file link opens normally
9. Open a task with no attachments → verify no "Attachments & Comments" section appears

## Implementation Notes

### Python String Escaping
All JS is embedded as Python string literals. Pay attention to:
- Use `'` inside `"..."` Python strings (or escape with `\'`)
- `\"` for double quotes inside Python `"..."` strings
- The pattern `f"..."` for f-strings embedding `base_action_url`; plain `"..."` for static JS

### Variable Scope for `lbImgs`
The `lbImgs` array is declared inside the `.then(function(d){...})` callback. The `onclick` attributes in the rendered HTML strings reference it by name. This works because when the onclick fires, `lbImgs` is passed as an argument to `openLightbox()` directly — it does not rely on closure capture of a loop variable.

### Touch Event Listeners
Touch event listeners are added each time `openLightbox` is called. To prevent stacking, either:
- (A) Use a named function and `removeEventListener` on close — preferred
- (B) Use `{ once: true }` on each individual event pair

The plan above uses option A: `ov.addEventListener('touchstart', ...)` with cleanup in `closeLightbox()`. Since the overlay is reused across calls, the listener must be removed on close. Use a named reference (`_lbTouchStart`, `_lbTouchEnd`) stored on the window object for removal.

### Revised touch handler with cleanup:
```js
function openLightbox(urls,idx){
  _lbUrls=urls;_lbIdx=idx;_lbRender();
  var ov=document.getElementById('lb-overlay');
  ov.classList.add('lb-open');
  document.addEventListener('keydown',_lbKey);
  window._lbTx=null;
  window._lbTouchStart=function(e){window._lbTx=e.touches[0].clientX;};
  window._lbTouchEnd=function(e){
    if(window._lbTx===null)return;
    var dx=e.changedTouches[0].clientX-window._lbTx;
    if(Math.abs(dx)>50)lightboxNav(dx<0?1:-1);
    window._lbTx=null;
  };
  ov.addEventListener('touchstart',window._lbTouchStart,{passive:true});
  ov.addEventListener('touchend',window._lbTouchEnd,{passive:true});
}

function closeLightbox(){
  var ov=document.getElementById('lb-overlay');
  ov.classList.remove('lb-open');
  document.removeEventListener('keydown',_lbKey);
  ov.removeEventListener('touchstart',window._lbTouchStart);
  ov.removeEventListener('touchend',window._lbTouchEnd);
}
```
