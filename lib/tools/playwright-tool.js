/**
 * Playwright Tool for Web Automation
 * Enables autonomous web actions for the email agent
 */

const logger = require('../logger');

class PlaywrightTool {
  constructor() {
    this.name = 'playwright';
    this.description = 'Web automation tool for autonomous browser actions';
    this.browser = null;
    this.context = null;
    this.page = null;
    this.actions = this.initializeActions();
  }

  /**
   * Initialize available actions
   */
  initializeActions() {
    return {
      'navigate': {
        description: 'Navigate to a URL',
        parameters: ['url'],
        handler: this.navigate.bind(this)
      },
      'click': {
        description: 'Click an element',
        parameters: ['selector'],
        handler: this.click.bind(this)
      },
      'fill': {
        description: 'Fill a form field',
        parameters: ['selector', 'value'],
        handler: this.fill.bind(this)
      },
      'extract': {
        description: 'Extract text from elements',
        parameters: ['selector'],
        handler: this.extractText.bind(this)
      },
      'screenshot': {
        description: 'Take a screenshot',
        parameters: ['filename'],
        handler: this.screenshot.bind(this)
      },
      'wait': {
        description: 'Wait for an element',
        parameters: ['selector', 'timeout'],
        handler: this.waitForSelector.bind(this)
      },
      'scroll': {
        description: 'Scroll page',
        parameters: ['direction'],
        handler: this.scroll.bind(this)
      },
      'submit': {
        description: 'Submit a form',
        parameters: ['selector'],
        handler: this.submitForm.bind(this)
      }
    };
  }

  /**
   * Execute an action
   */
  async execute(parameters) {
    const { action, ...params } = parameters;

    const actionDef = this.actions[action];

    if (!actionDef) {
      throw new Error(`Unknown Playwright action: ${action}`);
    }

    logger.info('Executing Playwright action', { action, params });

    // Ensure browser is initialized
    await this.ensureBrowser();

    try {
      const result = await actionDef.handler(params);

      return {
        success: true,
        action,
        result,
        summary: `${action} completed successfully`
      };
    } catch (error) {
      logger.error('Playwright action failed', {
        action,
        error: error.message
      });

      return {
        success: false,
        action,
        error: error.message
      };
    }
  }

  /**
   * Ensure browser is running
   */
  async ensureBrowser() {
    if (this.browser && this.page) {
      return;
    }

    const { chromium } = require('playwright');

    logger.info('Launching browser');

    this.browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    this.context = await this.browser.newContext({
      viewport: { width: 1280, height: 720 },
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    });

    this.page = await this.context.newPage();

    logger.info('Browser launched successfully');
  }

  /**
   * Navigate to URL
   */
  async navigate(params) {
    const { url, waitUntil = 'networkidle' } = params;

    logger.info('Navigating to URL', { url });

    await this.page.goto(url, {
      waitUntil,
      timeout: 30000
    });

    const title = await this.page.title();

    return {
      url,
      title,
      currentUrl: this.page.url()
    };
  }

  /**
   * Click element
   */
  async click(params) {
    const { selector, waitTime = 0 } = params;

    logger.info('Clicking element', { selector });

    await this.page.click(selector);

    if (waitTime > 0) {
      await this.page.waitForTimeout(waitTime);
    }

    return {
      clicked: selector,
      currentUrl: this.page.url()
    };
  }

  /**
   * Fill form field
   */
  async fill(params) {
    const { selector, value } = params;

    logger.info('Filling form field', { selector });

    await this.page.fill(selector, value);

    return {
      filled: selector,
      value: value
    };
  }

  /**
   * Extract text from elements
   */
  async extractText(params) {
    const { selector } = params;

    logger.info('Extracting text', { selector });

    const elements = await this.page.$$(selector);
    const texts = [];

    for (const element of elements) {
      const text = await element.textContent();
      texts.push(text.trim());
    }

    return {
      selector,
      count: texts.length,
      texts
    };
  }

  /**
   * Take screenshot
   */
  async screenshot(params) {
    const { filename = 'screenshot.png', fullPage = false } = params;

    logger.info('Taking screenshot', { filename });

    const buffer = await this.page.screenshot({
      path: filename,
      fullPage
    });

    return {
      filename,
      size: buffer.length,
      fullPage
    };
  }

  /**
   * Wait for selector
   */
  async waitForSelector(params) {
    const { selector, timeout = 30000 } = params;

    logger.info('Waiting for selector', { selector });

    await this.page.waitForSelector(selector, { timeout });

    return {
      found: selector
    };
  }

  /**
   * Scroll page
   */
  async scroll(params) {
    const { direction = 'down', amount = 500 } = params;

    logger.info('Scrolling page', { direction, amount });

    if (direction === 'down') {
      await this.page.evaluate((amt) => window.scrollBy(0, amt), amount);
    } else if (direction === 'up') {
      await this.page.evaluate((amt) => window.scrollBy(0, -amt), amount);
    } else if (direction === 'bottom') {
      await this.page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    } else if (direction === 'top') {
      await this.page.evaluate(() => window.scrollTo(0, 0));
    }

    return {
      direction,
      scrolled: true
    };
  }

  /**
   * Submit form
   */
  async submitForm(params) {
    const { selector } = params;

    logger.info('Submitting form', { selector });

    await this.page.click(selector);
    await this.page.waitForLoadState('networkidle');

    return {
      submitted: selector,
      currentUrl: this.page.url()
    };
  }

  /**
   * Execute custom script
   */
  async executeScript(params) {
    const { script } = params;

    logger.info('Executing custom script');

    const result = await this.page.evaluate(script);

    return {
      result,
      type: typeof result
    };
  }

  /**
   * Get page information
   */
  async getPageInfo() {
    return {
      url: this.page.url(),
      title: await this.page.title(),
      content: await this.page.content()
    };
  }

  /**
   * Close browser
   */
  async close() {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.context = null;
      this.page = null;

      logger.info('Browser closed');
    }
  }

  /**
   * Register with email agent
   */
  register(emailAgent) {
    emailAgent.registerTool(this.name, this);
    logger.info('Playwright tool registered with email agent');
  }

  /**
   * Get available actions
   */
  getActions() {
    return Object.entries(this.actions).map(([name, def]) => ({
      name,
      description: def.description,
      parameters: def.parameters
    }));
  }
}

module.exports = new PlaywrightTool();
module.exports.PlaywrightTool = PlaywrightTool;
