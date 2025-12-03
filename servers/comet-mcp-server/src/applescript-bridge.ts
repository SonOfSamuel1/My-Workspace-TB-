import { exec } from 'child_process';
import { promisify } from 'util';
import { readFile } from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const execAsync = promisify(exec);

// Get the directory of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * AppleScript Bridge for executing AppleScript files and commands
 */
export class AppleScriptBridge {
  private scriptPath: string;

  constructor() {
    // Path to AppleScript files
    this.scriptPath = path.join(__dirname, '..', 'applescript');
  }

  /**
   * Execute an AppleScript file with optional arguments
   */
  async executeScriptFile(scriptName: string, args: string[] = []): Promise<string> {
    const scriptFilePath = path.join(this.scriptPath, scriptName);

    // Build the command
    let command = `osascript "${scriptFilePath}"`;

    // Add arguments if provided
    if (args.length > 0) {
      const escapedArgs = args.map(arg => `"${arg.replace(/"/g, '\\"')}"`).join(' ');
      command += ` ${escapedArgs}`;
    }

    try {
      const { stdout, stderr } = await execAsync(command);
      if (stderr) {
        console.warn(`AppleScript warning: ${stderr}`);
      }
      return stdout.trim();
    } catch (error: any) {
      throw new Error(`AppleScript execution failed: ${error.message}`);
    }
  }

  /**
   * Execute raw AppleScript code
   */
  async executeScript(script: string): Promise<string> {
    try {
      const { stdout, stderr } = await execAsync(`osascript -e '${this.escapeAppleScript(script)}'`);
      if (stderr) {
        console.warn(`AppleScript warning: ${stderr}`);
      }
      return stdout.trim();
    } catch (error: any) {
      throw new Error(`AppleScript execution failed: ${error.message}`);
    }
  }

  /**
   * Check if Comet is running
   */
  async isCometRunning(): Promise<boolean> {
    const result = await this.executeScriptFile('check-comet-running.scpt');
    return result === 'running';
  }

  /**
   * Activate Comet browser
   */
  async activateComet(): Promise<void> {
    const isRunning = await this.isCometRunning();
    if (!isRunning) {
      // Launch Comet if not running
      await this.executeScript('tell application "Comet" to launch');
      // Wait for it to start
      await this.delay(3000);
    }
    await this.executeScriptFile('activate-comet.scpt');
  }

  /**
   * Send a prompt to Comet
   */
  async sendPrompt(prompt: string): Promise<string> {
    // Ensure Comet is active
    await this.activateComet();

    // Send the prompt
    const result = await this.executeScriptFile('send-prompt.scpt', [prompt]);
    return result;
  }

  /**
   * Extract text from Comet's response area
   */
  async extractText(): Promise<string> {
    const result = await this.executeScriptFile('extract-text.scpt');
    return result;
  }

  /**
   * Navigate to a URL in Comet
   */
  async navigateToURL(url: string): Promise<string> {
    await this.activateComet();
    const result = await this.executeScriptFile('navigate-url.scpt', [url]);
    return result;
  }

  /**
   * Type text at the current cursor position
   */
  async typeText(text: string): Promise<void> {
    const script = `
      tell application "System Events"
        keystroke "${this.escapeAppleScript(text)}"
      end tell
    `;
    await this.executeScript(script);
  }

  /**
   * Press a key combination
   */
  async pressKey(key: string, modifiers: string[] = []): Promise<void> {
    let script = 'tell application "System Events"\n';

    if (modifiers.length > 0) {
      const modifierString = modifiers.map(m => `${m} down`).join(', ');
      script += `  keystroke "${key}" using {${modifierString}}\n`;
    } else {
      script += `  keystroke "${key}"\n`;
    }

    script += 'end tell';
    await this.executeScript(script);
  }

  /**
   * Press Enter key
   */
  async pressEnter(): Promise<void> {
    const script = `
      tell application "System Events"
        key code 36
      end tell
    `;
    await this.executeScript(script);
  }

  /**
   * Take a screenshot of the Comet window
   */
  async takeScreenshot(outputPath: string): Promise<void> {
    const script = `
      tell application "Comet"
        set windowBounds to bounds of window 1
      end tell

      set x to item 1 of windowBounds
      set y to item 2 of windowBounds
      set w to (item 3 of windowBounds) - x
      set h to (item 4 of windowBounds) - y

      do shell script "screencapture -R" & x & "," & y & "," & w & "," & h & " " & quoted form of "${outputPath}"
    `;
    await this.executeScript(script);
  }

  /**
   * Escape special characters for AppleScript
   */
  private escapeAppleScript(text: string): string {
    return text
      .replace(/\\/g, '\\\\')
      .replace(/"/g, '\\"')
      .replace(/'/g, "\\'")
      .replace(/\n/g, '\\n')
      .replace(/\r/g, '\\r')
      .replace(/\t/g, '\\t');
  }

  /**
   * Delay execution for a specified number of milliseconds
   */
  private async delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get clipboard content
   */
  async getClipboard(): Promise<string> {
    const script = 'get the clipboard as string';
    return await this.executeScript(script);
  }

  /**
   * Set clipboard content
   */
  async setClipboard(text: string): Promise<void> {
    const script = `set the clipboard to "${this.escapeAppleScript(text)}"`;
    await this.executeScript(script);
  }

  /**
   * Select all text in the current field
   */
  async selectAll(): Promise<void> {
    await this.pressKey('a', ['command']);
  }

  /**
   * Copy selected text to clipboard
   */
  async copy(): Promise<void> {
    await this.pressKey('c', ['command']);
  }

  /**
   * Paste from clipboard
   */
  async paste(): Promise<void> {
    await this.pressKey('v', ['command']);
  }
}