/**
 * Retry Logic with Exponential Backoff
 *
 * Provides resilient retry mechanism for handling transient failures.
 */

const logger = require('./logger');

/**
 * Execute a function with retry logic
 *
 * @param {Function} fn - Async function to execute
 * @param {Object} options - Retry options
 * @param {number} options.maxRetries - Maximum number of retry attempts (default: 3)
 * @param {number} options.initialDelay - Initial delay in ms (default: 1000)
 * @param {number} options.maxDelay - Maximum delay in ms (default: 30000)
 * @param {number} options.backoffMultiplier - Backoff multiplier (default: 2)
 * @param {Function} options.onRetry - Callback called before each retry
 * @returns {Promise} Result of the function
 */
async function executeWithRetry(fn, options = {}) {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 30000,
    backoffMultiplier = 2,
    onRetry = null
  } = options;

  let lastError;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      logger.debug('Executing function', { attempt, maxRetries });
      return await fn();
    } catch (error) {
      lastError = error;

      logger.warn('Function execution failed', {
        attempt,
        maxRetries,
        error: error.message,
        willRetry: attempt < maxRetries
      });

      if (attempt < maxRetries) {
        const delay = Math.min(
          initialDelay * Math.pow(backoffMultiplier, attempt - 1),
          maxDelay
        );

        logger.info('Retrying after delay', { delayMs: delay, nextAttempt: attempt + 1 });

        if (onRetry) {
          await onRetry(attempt, error);
        }

        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  logger.error('All retry attempts exhausted', {
    maxRetries,
    finalError: lastError.message
  });

  throw lastError;
}

/**
 * Retry with custom retry condition
 *
 * @param {Function} fn - Async function to execute
 * @param {Function} shouldRetry - Function that determines if error is retryable
 * @param {Object} options - Retry options
 */
async function retryWithCondition(fn, shouldRetry, options = {}) {
  const { maxRetries = 3, initialDelay = 1000 } = options;
  let lastError;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (!shouldRetry(error) || attempt >= maxRetries) {
        throw error;
      }

      const delay = initialDelay * Math.pow(2, attempt - 1);
      logger.info('Retryable error detected', {
        attempt,
        error: error.message,
        nextRetryIn: delay
      });

      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

/**
 * Common retry conditions
 */
const RetryConditions = {
  // Retry on network errors
  isNetworkError: (error) => {
    return error.code === 'ECONNREFUSED' ||
           error.code === 'ETIMEDOUT' ||
           error.code === 'ENOTFOUND' ||
           error.message.includes('network');
  },

  // Retry on rate limit errors
  isRateLimitError: (error) => {
    return error.statusCode === 429 ||
           error.message.includes('rate limit') ||
           error.message.includes('too many requests');
  },

  // Retry on 5xx server errors
  isServerError: (error) => {
    return error.statusCode >= 500 && error.statusCode < 600;
  },

  // Combine multiple conditions
  combine: (...conditions) => {
    return (error) => conditions.some(condition => condition(error));
  }
};

module.exports = {
  executeWithRetry,
  retryWithCondition,
  RetryConditions
};
