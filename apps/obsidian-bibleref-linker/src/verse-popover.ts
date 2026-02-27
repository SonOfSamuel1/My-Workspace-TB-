import { BibleReference, buildBibleRefUrl, referenceToString } from "./bible-reference";
import { VerseApi, VerseResult } from "./verse-api";

const DISMISS_DELAY = 200;
const LONG_PRESS_MS = 500;

export class VersePopover {
  private popoverEl: HTMLElement | null = null;
  private dismissTimer: ReturnType<typeof setTimeout> | null = null;
  private currentRef: string | null = null;
  private verseApi: VerseApi;
  private translation: string;
  private outsideTapHandler: ((e: Event) => void) | null = null;

  constructor(verseApi: VerseApi, translation: string) {
    this.verseApi = verseApi;
    this.translation = translation;
  }

  setTranslation(translation: string): void {
    this.translation = translation;
  }

  show(ref: BibleReference, anchorEl: HTMLElement): void {
    const refKey = referenceToString(ref);

    // Already showing this reference
    if (this.currentRef === refKey && this.popoverEl) {
      this.cancelDismiss();
      return;
    }

    this.hideImmediate();
    this.currentRef = refKey;

    const popover = document.createElement("div");
    popover.addClass("bibleref-popover");

    // Header
    const header = popover.createDiv({ cls: "bibleref-popover-header" });
    header.createSpan({ cls: "bibleref-popover-title", text: refKey });
    header.createSpan({ cls: "bibleref-popover-translation" });

    // Body: loading state
    const body = popover.createDiv({ cls: "bibleref-popover-text" });
    body.createSpan({ cls: "bibleref-popover-loading", text: "Loading verse..." });

    // Footer
    const footer = popover.createDiv({ cls: "bibleref-popover-footer" });
    const link = footer.createEl("a", {
      text: "View on BibleRef.com",
      href: buildBibleRefUrl(ref),
    });
    link.setAttr("target", "_blank");
    link.setAttr("rel", "noopener");

    // Position below the anchor element
    const rect = anchorEl.getBoundingClientRect();
    popover.style.top = `${rect.bottom + 4}px`;
    popover.style.left = `${rect.left}px`;

    // Desktop: keep popover visible when hovering over it
    popover.addEventListener("mouseenter", () => this.cancelDismiss());
    popover.addEventListener("mouseleave", () => this.scheduleDismiss());

    // Mobile: dismiss when tapping outside the popover
    this.removeOutsideTapHandler();
    this.outsideTapHandler = (e: Event) => {
      if (this.popoverEl && !this.popoverEl.contains(e.target as Node)) {
        this.hideImmediate();
      }
    };
    // Use setTimeout so the current touch event doesn't immediately dismiss
    setTimeout(() => {
      if (this.outsideTapHandler) {
        document.addEventListener("touchstart", this.outsideTapHandler, { passive: true });
        document.addEventListener("click", this.outsideTapHandler, { passive: true });
      }
    }, 50);

    document.body.appendChild(popover);
    this.popoverEl = popover;

    // Clamp popover within viewport
    requestAnimationFrame(() => {
      if (!this.popoverEl) return;
      const popRect = this.popoverEl.getBoundingClientRect();
      if (popRect.right > window.innerWidth - 8) {
        this.popoverEl.style.left = `${window.innerWidth - popRect.width - 8}px`;
      }
      if (popRect.bottom > window.innerHeight - 8) {
        this.popoverEl.style.top = `${rect.top - popRect.height - 4}px`;
      }
    });

    // Fetch verse text
    this.verseApi.fetchVerse(ref, this.translation).then((result: VerseResult) => {
      if (this.currentRef !== refKey || !this.popoverEl) return;

      body.empty();
      const translationEl = this.popoverEl.querySelector(".bibleref-popover-translation");

      if (result.error) {
        body.createSpan({ cls: "bibleref-popover-error", text: result.error });
      } else {
        body.setText(result.text);
        if (translationEl) {
          translationEl.setText(result.translation);
        }
      }
    });
  }

  scheduleDismiss(): void {
    this.cancelDismiss();
    this.dismissTimer = setTimeout(() => this.hideImmediate(), DISMISS_DELAY);
  }

  cancelDismiss(): void {
    if (this.dismissTimer) {
      clearTimeout(this.dismissTimer);
      this.dismissTimer = null;
    }
  }

  hideImmediate(): void {
    this.cancelDismiss();
    this.removeOutsideTapHandler();
    if (this.popoverEl) {
      this.popoverEl.remove();
      this.popoverEl = null;
    }
    this.currentRef = null;
  }

  private removeOutsideTapHandler(): void {
    if (this.outsideTapHandler) {
      document.removeEventListener("touchstart", this.outsideTapHandler);
      document.removeEventListener("click", this.outsideTapHandler);
      this.outsideTapHandler = null;
    }
  }

  /** Attach long-press handlers to an element for mobile popover support */
  attachLongPress(el: HTMLElement, ref: BibleReference): void {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let didLongPress = false;

    el.addEventListener(
      "touchstart",
      (e: TouchEvent) => {
        didLongPress = false;
        timer = setTimeout(() => {
          didLongPress = true;
          this.show(ref, el);
          e.preventDefault();
        }, LONG_PRESS_MS);
      },
      { passive: false }
    );

    el.addEventListener(
      "touchend",
      () => {
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
      },
      { passive: true }
    );

    el.addEventListener(
      "touchmove",
      () => {
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
      },
      { passive: true }
    );

    // Prevent the tap from navigating if we just showed a popover
    el.addEventListener("click", (e: MouseEvent) => {
      if (didLongPress) {
        e.preventDefault();
        e.stopPropagation();
        didLongPress = false;
      }
    });
  }
}
