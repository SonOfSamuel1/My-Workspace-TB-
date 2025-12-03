/**
 * Utility functions for smart waiting and polling
 */

/**
 * Delay execution for a specified number of milliseconds
 */
export async function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Wait for a condition to be true with timeout
 */
export async function waitForCondition(
  condition: () => Promise<boolean> | boolean,
  options: {
    maxWaitMs?: number;
    intervalMs?: number;
    errorMessage?: string;
  } = {}
): Promise<void> {
  const {
    maxWaitMs = 30000,
    intervalMs = 500,
    errorMessage = 'Condition was not met within timeout'
  } = options;

  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitMs) {
    const result = await condition();
    if (result) {
      return;
    }
    await delay(intervalMs);
  }

  throw new Error(`${errorMessage} (waited ${maxWaitMs}ms)`);
}

/**
 * Exponential backoff retry
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    initialDelayMs?: number;
    maxDelayMs?: number;
    factor?: number;
  } = {}
): Promise<T> {
  const {
    maxRetries = 3,
    initialDelayMs = 1000,
    maxDelayMs = 10000,
    factor = 2
  } = options;

  let lastError: Error | undefined;
  let delayMs = initialDelayMs;

  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;

      if (i < maxRetries) {
        console.warn(`Attempt ${i + 1} failed, retrying in ${delayMs}ms:`, error.message);
        await delay(delayMs);
        delayMs = Math.min(delayMs * factor, maxDelayMs);
      }
    }
  }

  throw lastError || new Error('All retry attempts failed');
}

/**
 * Poll for text changes with stabilization
 */
export async function waitForTextStabilization(
  getText: () => Promise<string>,
  options: {
    maxWaitMs?: number;
    stabilizationMs?: number;
    pollIntervalMs?: number;
  } = {}
): Promise<string> {
  const {
    maxWaitMs = 30000,
    stabilizationMs = 1000,
    pollIntervalMs = 500
  } = options;

  const startTime = Date.now();
  let lastText = '';
  let lastChangeTime = Date.now();
  let currentText = await getText();

  while (Date.now() - startTime < maxWaitMs) {
    await delay(pollIntervalMs);
    currentText = await getText();

    if (currentText !== lastText) {
      lastText = currentText;
      lastChangeTime = Date.now();
    } else if (Date.now() - lastChangeTime >= stabilizationMs && currentText.length > 0) {
      // Text has been stable for the required duration
      return currentText;
    }

    // Check if we're about to timeout
    if (Date.now() - startTime + pollIntervalMs >= maxWaitMs) {
      // Return what we have if there's some text
      if (currentText.length > 0) {
        return currentText;
      }
    }
  }

  // Return whatever we have, even if empty
  return currentText;
}

/**
 * Add random jitter to avoid detection
 */
export async function delayWithJitter(baseMs: number, jitterMs: number = 100): Promise<void> {
  const actualDelay = baseMs + Math.random() * jitterMs;
  await delay(actualDelay);
}