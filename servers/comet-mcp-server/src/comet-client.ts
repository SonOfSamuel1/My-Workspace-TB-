import { AppleScriptBridge } from './applescript-bridge.js';
import {
  delay,
  waitForCondition,
  retryWithBackoff,
  waitForTextStabilization,
  delayWithJitter
} from './utils/wait.js';
import {
  parseResponse,
  extractLatestResponse,
  isResponseComplete,
  extractURLs,
  extractCodeBlocks,
  splitPrompt
} from './utils/parser.js';

export interface CometResponse {
  text: string;
  urls?: string[];
  codeBlocks?: Array<{ lang?: string; code: string }>;
  timestamp: Date;
  rawText?: string;
}

export interface CometClientOptions {
  responseTimeout?: number;
  stabilizationTime?: number;
  maxRetries?: number;
  useClipboardFallback?: boolean;
}

/**
 * Client for controlling Comet browser through desktop automation
 */
export class CometClient {
  private bridge: AppleScriptBridge;
  private options: CometClientOptions;
  private lastResponseText: string = '';
  private isInitialized: boolean = false;

  constructor(options: CometClientOptions = {}) {
    this.bridge = new AppleScriptBridge();
    this.options = {
      responseTimeout: options.responseTimeout || 30000,
      stabilizationTime: options.stabilizationTime || 1000,
      maxRetries: options.maxRetries || 3,
      useClipboardFallback: options.useClipboardFallback !== false
    };
  }

  /**
   * Initialize the Comet client and ensure browser is ready
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    console.log('Initializing Comet client...');

    // Check if Comet is running
    const isRunning = await this.bridge.isCometRunning();
    if (!isRunning) {
      console.log('Comet is not running. Launching...');
      await this.bridge.activateComet();
      await delay(3000); // Wait for launch
    } else {
      console.log('Comet is already running. Activating...');
      await this.bridge.activateComet();
    }

    this.isInitialized = true;
    console.log('Comet client initialized successfully');
  }

  /**
   * Send a prompt to Comet and optionally wait for response
   */
  async sendPrompt(prompt: string, waitForResponse: boolean = true): Promise<CometResponse> {
    await this.initialize();

    console.log(`Sending prompt to Comet: ${prompt.substring(0, 100)}...`);

    // Handle long prompts
    const promptChunks = splitPrompt(prompt);

    if (promptChunks.length > 1) {
      console.log(`Prompt split into ${promptChunks.length} chunks`);
    }

    // Send each chunk
    for (let i = 0; i < promptChunks.length; i++) {
      const chunk = promptChunks[i];
      const isLastChunk = i === promptChunks.length - 1;

      await retryWithBackoff(
        async () => {
          await this.bridge.sendPrompt(chunk);
        },
        {
          maxRetries: this.options.maxRetries,
          initialDelayMs: 1000
        }
      );

      if (!isLastChunk) {
        // Wait a bit between chunks
        await delayWithJitter(1000);
      }
    }

    if (!waitForResponse) {
      return {
        text: 'Prompt sent successfully',
        timestamp: new Date()
      };
    }

    // Wait for and extract response
    console.log('Waiting for Comet response...');
    const response = await this.waitForResponse();
    return response;
  }

  /**
   * Wait for Comet to generate a response
   */
  async waitForResponse(): Promise<CometResponse> {
    // Wait a bit for response to start
    await delay(2000);

    // Use text stabilization to detect when response is complete
    const responseText = await waitForTextStabilization(
      async () => await this.extractResponse(),
      {
        maxWaitMs: this.options.responseTimeout,
        stabilizationMs: this.options.stabilizationTime,
        pollIntervalMs: 500
      }
    );

    // Parse and analyze the response
    const parsedText = extractLatestResponse(responseText);

    const response: CometResponse = {
      text: parsedText,
      urls: extractURLs(parsedText),
      codeBlocks: extractCodeBlocks(parsedText),
      timestamp: new Date(),
      rawText: responseText
    };

    this.lastResponseText = parsedText;

    console.log(`Response received (${parsedText.length} chars)`);
    return response;
  }

  /**
   * Extract response text from Comet
   */
  private async extractResponse(): Promise<string> {
    // Try multiple extraction methods
    try {
      // Method 1: Direct extraction via AppleScript
      const text = await this.bridge.extractText();
      if (text && text.length > this.lastResponseText.length) {
        return text;
      }
    } catch (error) {
      console.warn('Direct text extraction failed:', error);
    }

    if (this.options.useClipboardFallback) {
      try {
        // Method 2: Clipboard fallback
        await this.bridge.selectAll();
        await delay(200);
        await this.bridge.copy();
        await delay(200);
        const clipboardText = await this.bridge.getClipboard();
        if (clipboardText && clipboardText.length > 0) {
          return clipboardText;
        }
      } catch (error) {
        console.warn('Clipboard extraction failed:', error);
      }
    }

    // Return whatever we have
    return this.lastResponseText;
  }

  /**
   * Navigate to a URL in Comet
   */
  async navigate(url: string): Promise<void> {
    await this.initialize();
    console.log(`Navigating to: ${url}`);

    await retryWithBackoff(
      async () => {
        await this.bridge.navigateToURL(url);
      },
      {
        maxRetries: this.options.maxRetries
      }
    );

    // Wait for navigation
    await delay(2000);
  }

  /**
   * Extract current page content
   */
  async extractPageContent(): Promise<string> {
    await this.initialize();

    // Select all and copy page content
    await this.bridge.selectAll();
    await delay(200);
    await this.bridge.copy();
    await delay(200);

    const content = await this.bridge.getClipboard();
    return parseResponse(content);
  }

  /**
   * Take a screenshot of the Comet window
   */
  async takeScreenshot(outputPath: string): Promise<void> {
    await this.initialize();
    console.log(`Taking screenshot: ${outputPath}`);
    await this.bridge.takeScreenshot(outputPath);
  }

  /**
   * Type text at current cursor position
   */
  async typeText(text: string): Promise<void> {
    await this.initialize();
    await this.bridge.typeText(text);
  }

  /**
   * Press Enter key
   */
  async pressEnter(): Promise<void> {
    await this.initialize();
    await this.bridge.pressEnter();
  }

  /**
   * Execute a batch of prompts sequentially
   */
  async batchPrompts(prompts: string[]): Promise<CometResponse[]> {
    await this.initialize();

    const responses: CometResponse[] = [];

    for (let i = 0; i < prompts.length; i++) {
      console.log(`Processing prompt ${i + 1}/${prompts.length}`);
      const response = await this.sendPrompt(prompts[i], true);
      responses.push(response);

      // Add delay between prompts to avoid overwhelming
      if (i < prompts.length - 1) {
        await delayWithJitter(2000, 500);
      }
    }

    return responses;
  }

  /**
   * Research a topic with follow-up questions
   */
  async researchTopic(
    topic: string,
    followUpQuestions: string[] = []
  ): Promise<{
    initial: CometResponse;
    followUps: CometResponse[];
  }> {
    await this.initialize();

    console.log(`Researching topic: ${topic}`);

    // Initial research
    const initial = await this.sendPrompt(`Research the following topic: ${topic}`, true);

    // Follow-up questions
    const followUps: CometResponse[] = [];
    for (const question of followUpQuestions) {
      await delayWithJitter(2000);
      const response = await this.sendPrompt(question, true);
      followUps.push(response);
    }

    return { initial, followUps };
  }

  /**
   * Clear the current conversation
   */
  async clearConversation(): Promise<void> {
    await this.initialize();

    // Try common keyboard shortcuts for new chat
    try {
      // Try Cmd+K (common clear shortcut)
      await this.bridge.pressKey('k', ['command']);
      await delay(500);
    } catch {
      // Try Cmd+N (new)
      await this.bridge.pressKey('n', ['command']);
      await delay(500);
    }

    this.lastResponseText = '';
  }

  /**
   * Check if Comet is responsive
   */
  async checkHealth(): Promise<boolean> {
    try {
      const isRunning = await this.bridge.isCometRunning();
      if (!isRunning) {
        return false;
      }

      // Try to activate and get some text
      await this.bridge.activateComet();
      await delay(500);

      // If we can extract text, it's healthy
      await this.bridge.extractText();
      return true;
    } catch {
      return false;
    }
  }
}