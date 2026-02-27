import { App, PluginSettingTab, Setting } from "obsidian";
import type BibleRefLinkerPlugin from "./main";
import { TRANSLATIONS } from "./constants";

export interface BibleRefSettings {
  autoLink: boolean;
  translation: string;
  openInBrowser: boolean;
  showPopover: boolean;
}

export class BibleRefSettingTab extends PluginSettingTab {
  plugin: BibleRefLinkerPlugin;

  constructor(app: App, plugin: BibleRefLinkerPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName("Auto-link Bible references")
      .setDesc("Automatically convert Bible references into clickable links to BibleRef.com")
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.autoLink).onChange(async (value) => {
          this.plugin.settings.autoLink = value;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Bible translation")
      .setDesc("Translation to use for verse text in pop-over")
      .addDropdown((dropdown) => {
        for (const t of TRANSLATIONS) {
          dropdown.addOption(t.value, t.label);
        }
        dropdown.setValue(this.plugin.settings.translation).onChange(async (value) => {
          this.plugin.settings.translation = value;
          this.plugin.popover.setTranslation(value);
          await this.plugin.saveSettings();
        });
      });

    new Setting(containerEl)
      .setName("Open links in browser")
      .setDesc("Open BibleRef.com links in your default browser instead of Obsidian")
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.openInBrowser).onChange(async (value) => {
          this.plugin.settings.openInBrowser = value;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Show verse pop-over")
      .setDesc("Show verse text in a pop-over when hovering over a Bible reference")
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.showPopover).onChange(async (value) => {
          this.plugin.settings.showPopover = value;
          await this.plugin.saveSettings();
        })
      );
  }
}
