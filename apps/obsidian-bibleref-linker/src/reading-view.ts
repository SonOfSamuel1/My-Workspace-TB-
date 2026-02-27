import { MarkdownPostProcessorContext } from "obsidian";
import { findReferences, buildBibleRefUrl, BibleReference } from "./bible-reference";
import { VersePopover } from "./verse-popover";

const SKIP_ELEMENTS = new Set(["A", "CODE", "PRE", "SCRIPT", "STYLE"]);

export function createReadingViewProcessor(
  popover: VersePopover,
  getSettings: () => { autoLink: boolean; openInBrowser: boolean; showPopover: boolean }
) {
  return (el: HTMLElement, _ctx: MarkdownPostProcessorContext) => {
    const settings = getSettings();
    if (!settings.autoLink) return;

    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
      acceptNode(node: Node): number {
        // Skip text inside links, code blocks, etc.
        let parent = node.parentElement;
        while (parent && parent !== el) {
          if (SKIP_ELEMENTS.has(parent.tagName)) {
            return NodeFilter.FILTER_REJECT;
          }
          parent = parent.parentElement;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });

    const textNodes: Text[] = [];
    let node: Node | null;
    while ((node = walker.nextNode())) {
      textNodes.push(node as Text);
    }

    for (const textNode of textNodes) {
      const text = textNode.textContent;
      if (!text) continue;

      const refs = findReferences(text);
      if (refs.length === 0) continue;

      const fragment = document.createDocumentFragment();
      let lastEnd = 0;

      for (const ref of refs) {
        // Text before reference
        if (ref.startIndex > lastEnd) {
          fragment.appendChild(document.createTextNode(text.slice(lastEnd, ref.startIndex)));
        }

        const anchor = createReferenceLink(
          ref,
          settings.openInBrowser,
          popover,
          settings.showPopover
        );
        fragment.appendChild(anchor);
        lastEnd = ref.endIndex;
      }

      // Text after last reference
      if (lastEnd < text.length) {
        fragment.appendChild(document.createTextNode(text.slice(lastEnd)));
      }

      textNode.replaceWith(fragment);
    }
  };
}

function createReferenceLink(
  ref: BibleReference,
  openInBrowser: boolean,
  popover: VersePopover,
  showPopover: boolean
): HTMLAnchorElement {
  const anchor = document.createElement("a");
  anchor.className = "bibleref-link";
  anchor.textContent = ref.fullMatch;
  anchor.href = buildBibleRefUrl(ref);

  if (openInBrowser) {
    anchor.setAttr("target", "_blank");
    anchor.setAttr("rel", "noopener");
  }

  if (showPopover) {
    // Desktop: hover popover
    anchor.addEventListener("mouseenter", () => popover.show(ref, anchor));
    anchor.addEventListener("mouseleave", () => popover.scheduleDismiss());
    // Mobile: long-press popover
    popover.attachLongPress(anchor, ref);
  }

  return anchor;
}
