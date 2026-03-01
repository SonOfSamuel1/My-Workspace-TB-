import {
  Decoration,
  DecorationSet,
  EditorView,
  ViewPlugin,
  ViewUpdate,
  WidgetType,
} from "@codemirror/view";
import { RangeSetBuilder } from "@codemirror/state";
import { syntaxTree } from "@codemirror/language";
import { findReferences, buildBibleRefUrl, BibleReference } from "./bible-reference";
import { VersePopover } from "./verse-popover";

// SVG book icon (inline, small)
const BOOK_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6 2a3 3 0 0 0-3 3v14a3 3 0 0 0 3 3h13a1 1 0 1 0 0-2H6a1 1 0 1 1 0-2h13a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1H6zm0 2h12v12H6a2.99 2.99 0 0 0-2 .76V5a1 1 0 0 1 1-1z"/></svg>`;

class BookIconWidget extends WidgetType {
  constructor(readonly ref: BibleReference) {
    super();
  }

  toDOM(): HTMLElement {
    const span = document.createElement("span");
    span.className = "bibleref-cm-icon";
    span.innerHTML = BOOK_ICON_SVG;
    span.setAttribute("aria-label", "Open on BibleRef.com");
    return span;
  }

  eq(other: BookIconWidget): boolean {
    return (
      this.ref.fullMatch === other.ref.fullMatch && this.ref.startIndex === other.ref.startIndex
    );
  }

  ignoreEvent(): boolean {
    return false;
  }
}

// Node types to skip in the CM6 syntax tree
const SKIP_NODE_TYPES = new Set([
  "CodeBlock",
  "FencedCode",
  "InlineCode",
  "CodeText",
  "HyperLink",
  "Link",
  "URL",
  "Image",
  "HTMLTag",
  "comment",
  "hmd-codeblock",
  "formatting",
]);

function shouldSkipPosition(view: EditorView, from: number, to: number): boolean {
  let skip = false;
  syntaxTree(view.state).iterate({
    from,
    to,
    enter(node) {
      if (
        SKIP_NODE_TYPES.has(node.name) ||
        node.name.includes("code") ||
        node.name.includes("Code")
      ) {
        skip = true;
        return false;
      }
    },
  });
  return skip;
}

function buildDecorations(view: EditorView): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  const cursorPos = view.state.selection.main.head;

  for (const { from, to } of view.visibleRanges) {
    const text = view.state.sliceDoc(from, to);
    const refs = findReferences(text);

    for (const ref of refs) {
      const absFrom = from + ref.startIndex;
      const absTo = from + ref.endIndex;

      // Skip if cursor is inside this reference (allow normal editing)
      if (cursorPos >= absFrom && cursorPos <= absTo) continue;

      // Skip code blocks and existing links
      if (shouldSkipPosition(view, absFrom, absTo)) continue;

      builder.add(
        absFrom,
        absTo,
        Decoration.mark({
          class: "bibleref-cm-link",
          attributes: { "data-bibleref-url": buildBibleRefUrl(ref) },
        })
      );

      builder.add(absTo, absTo, Decoration.widget({ widget: new BookIconWidget(ref), side: 1 }));
    }
  }

  return builder.finish();
}

export function createLivePreviewExtension(
  popover: VersePopover,
  getSettings: () => { autoLink: boolean; openInBrowser: boolean; showPopover: boolean }
) {
  return ViewPlugin.fromClass(
    class {
      decorations: DecorationSet;

      constructor(view: EditorView) {
        this.decorations = getSettings().autoLink ? buildDecorations(view) : Decoration.none;
      }

      update(update: ViewUpdate): void {
        if (!getSettings().autoLink) {
          this.decorations = Decoration.none;
          return;
        }
        if (update.docChanged || update.viewportChanged || update.selectionSet) {
          this.decorations = buildDecorations(update.view);
        }
      }
    },
    {
      decorations: (v) => v.decorations,
      eventHandlers: {
        touchstart(event: TouchEvent, view: EditorView) {
          if (!getSettings().showPopover) return;

          const target = event.target as HTMLElement;
          const linkEl = target.closest(".bibleref-cm-link") as HTMLElement;
          if (!linkEl) return;

          const longPressTimer = setTimeout(() => {
            const pos = view.posAtDOM(linkEl);
            const lineText = view.state.doc.lineAt(pos).text;
            const lineFrom = view.state.doc.lineAt(pos).from;
            const refs = findReferences(lineText);

            for (const ref of refs) {
              const absFrom = lineFrom + ref.startIndex;
              const absTo = lineFrom + ref.endIndex;
              if (pos >= absFrom && pos <= absTo) {
                linkEl.dataset.biblerefLongPressed = "true";
                popover.show(ref, linkEl);
                break;
              }
            }
          }, 500);

          const cancel = () => {
            clearTimeout(longPressTimer);
            linkEl.removeEventListener("touchend", cancel);
            linkEl.removeEventListener("touchmove", cancel);
          };
          linkEl.addEventListener("touchend", cancel, { once: true });
          linkEl.addEventListener("touchmove", cancel, { once: true });
        },

        click(event: MouseEvent, view: EditorView) {
          const target = event.target as HTMLElement;
          const settings = getSettings();

          // If this click follows a long-press popover, suppress navigation
          const pressedLink = target.closest("[data-bibleref-long-pressed]") as HTMLElement;
          if (pressedLink) {
            delete pressedLink.dataset.biblerefLongPressed;
            event.preventDefault();
            return;
          }

          // Handle click on book icon widget
          if (target.closest(".bibleref-cm-icon")) {
            const iconEl = target.closest(".bibleref-cm-icon") as HTMLElement;
            const pos = view.posAtDOM(iconEl);
            const lineText = view.state.doc.lineAt(pos).text;
            const lineFrom = view.state.doc.lineAt(pos).from;
            const refs = findReferences(lineText);

            for (const ref of refs) {
              const absTo = lineFrom + ref.endIndex;
              // Find the ref whose end position matches where the icon is
              if (Math.abs(absTo - pos) <= 2) {
                const url = buildBibleRefUrl(ref);
                window.open(url, "_blank");
                event.preventDefault();
                return;
              }
            }
          }

          // Handle click on decorated text
          if (
            target.classList.contains("bibleref-cm-link") ||
            target.closest(".bibleref-cm-link")
          ) {
            const el = target.classList.contains("bibleref-cm-link")
              ? target
              : (target.closest(".bibleref-cm-link") as HTMLElement);
            const url = el?.getAttribute("data-bibleref-url");
            if (url && settings.openInBrowser) {
              window.open(url, "_blank");
              event.preventDefault();
            }
          }
        },

        mouseover(event: MouseEvent, view: EditorView) {
          if (!getSettings().showPopover) return;

          const target = event.target as HTMLElement;
          const linkEl = target.closest(".bibleref-cm-link") as HTMLElement;
          if (!linkEl) return;

          const pos = view.posAtDOM(linkEl);
          const lineText = view.state.doc.lineAt(pos).text;
          const lineFrom = view.state.doc.lineAt(pos).from;
          const refs = findReferences(lineText);

          for (const ref of refs) {
            const absFrom = lineFrom + ref.startIndex;
            const absTo = lineFrom + ref.endIndex;
            if (pos >= absFrom && pos <= absTo) {
              popover.show(ref, linkEl);
              break;
            }
          }
        },

        mouseout(event: MouseEvent) {
          const target = event.target as HTMLElement;
          if (target.closest(".bibleref-cm-link")) {
            popover.scheduleDismiss();
          }
        },
      },
    }
  );
}
