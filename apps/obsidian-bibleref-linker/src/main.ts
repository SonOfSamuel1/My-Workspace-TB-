import { Notice, Plugin } from "obsidian";
import { DEFAULT_SETTINGS } from "./constants";
import { BibleRefSettings, BibleRefSettingTab } from "./settings";
import { VerseCache } from "./verse-cache";
import { VerseApi } from "./verse-api";
import { VersePopover } from "./verse-popover";
import { createReadingViewProcessor } from "./reading-view";
import { createLivePreviewExtension } from "./live-preview";

export default class BibleRefLinkerPlugin extends Plugin {
  settings: BibleRefSettings = { ...DEFAULT_SETTINGS };
  cache: VerseCache = new VerseCache();
  verseApi: VerseApi = new VerseApi(this.cache);
  popover: VersePopover = new VersePopover(this.verseApi, DEFAULT_SETTINGS.translation);

  async onload(): Promise<void> {
    await this.loadSettings();
    this.popover.setTranslation(this.settings.translation);

    // Reading view: MarkdownPostProcessor
    this.registerMarkdownPostProcessor(
      createReadingViewProcessor(this.popover, () => this.settings)
    );

    // Live preview: CM6 editor extension
    this.registerEditorExtension(createLivePreviewExtension(this.popover, () => this.settings));

    // Settings tab
    this.addSettingTab(new BibleRefSettingTab(this.app, this));

    // Command: clear verse cache
    this.addCommand({
      id: "clear-verse-cache",
      name: "Clear verse cache",
      callback: () => {
        this.cache.clear();
        new Notice("BibleRef Linker: Verse cache cleared");
      },
    });
  }

  onunload(): void {
    this.popover.hideImmediate();
    this.cache.clear();
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }
}
