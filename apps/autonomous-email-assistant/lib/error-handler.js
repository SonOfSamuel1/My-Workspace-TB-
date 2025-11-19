/**
 * Centralized Error Handler
 *
 * Provides consistent error handling and recovery strategies.
 */

const logger = require('./logger');

class EmailAssistantError extends Error {
  constructor(message, code, recoverable = false) {
    super(message);
    this.name = 'EmailAssistantError';
    this.code = code;
    this.recoverable = recoverable;
  }
}

/**
 * Error codes
 */
const ErrorCodes = {
  // Configuration errors (not recoverable)
  INVALID_CONFIG: 'INVALID_CONFIG',
  MISSING_CREDENTIALS: 'MISSING_CREDENTIALS',

  // Runtime errors (potentially recoverable)
  GMAIL_MCP_FAILED: 'GMAIL_MCP_FAILED',
  CLAUDE_CLI_FAILED: 'CLAUDE_CLI_FAILED',
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',

  // Business logic errors
  EMAIL_PROCESSING_FAILED: 'EMAIL_PROCESSING_FAILED',
  CLASSIFICATION_FAILED: 'CLASSIFICATION_FAILED',

  // External service errors
  TWILIO_FAILED: 'TWILIO_FAILED',
  AWS_SERVICE_FAILED: 'AWS_SERVICE_FAILED'
};

/**
 * Handles errors with appropriate recovery strategy
 */
async function handleError(error, context = {}) {
  logger.error('Error occurred', {
    error: error.message,
    code: error.code,
    recoverable: error.recoverable,
    stack: error.stack,
    ...context
  });

  // Determine if error is recoverable
  const isRecoverable = error.recoverable ||
                        isTransientError(error) ||
                        hasRecoveryStrategy(error);

  if (isRecoverable) {
    logger.info('Error is recoverable, attempting recovery');
    return await attemptRecovery(error, context);
  }

  // Non-recoverable error - send alert and fail
  await sendErrorAlert(error, context);
  throw error;
}

/**
 * Check if error is transient (network, rate limit, etc.)
 */
function isTransientError(error) {
  const transientPatterns = [
    'ECONNREFUSED',
    'ETIMEDOUT',
    'ENOTFOUND',
    'rate limit',
    '429',
    '503',
    '504'
  ];

  const errorString = `${error.code} ${error.message}`.toLowerCase();

  return transientPatterns.some(pattern =>
    errorString.includes(pattern.toLowerCase())
  );
}

/**
 * Check if we have a recovery strategy for this error
 */
function hasRecoveryStrategy(error) {
  const recoverableErrors = [
    ErrorCodes.GMAIL_MCP_FAILED,
    ErrorCodes.NETWORK_ERROR,
    ErrorCodes.TIMEOUT
  ];

  return recoverableErrors.includes(error.code);
}

/**
 * Attempt to recover from error
 */
async function attemptRecovery(error, context) {
  switch (error.code) {
    case ErrorCodes.GMAIL_MCP_FAILED:
      logger.info('Attempting Gmail MCP recovery');
      // Could try IMAP fallback here
      return { success: false, message: 'Gmail MCP recovery not implemented' };

    case ErrorCodes.TIMEOUT:
      logger.info('Timeout occurred, can retry');
      return { success: true, shouldRetry: true };

    case ErrorCodes.NETWORK_ERROR:
      logger.info('Network error, can retry');
      return { success: true, shouldRetry: true };

    default:
      logger.warn('No recovery strategy for error', { code: error.code });
      return { success: false };
  }
}

/**
 * Send error alert to admin
 */
async function sendErrorAlert(error, context) {
  const alertData = {
    timestamp: new Date().toISOString(),
    error: {
      message: error.message,
      code: error.code,
      stack: error.stack
    },
    context,
    environment: process.env.NODE_ENV,
    awsRequestId: context.awsRequestId
  };

  logger.error('Sending error alert', { alert: alertData });

  // In a real implementation, this would send:
  // - Email via SES
  // - SMS via SNS
  // - Slack/Discord notification
  // - PagerDuty alert

  // For now, just log it
  console.error('=== ERROR ALERT ===');
  console.error(JSON.stringify(alertData, null, 2));
  console.error('==================');
}

/**
 * Wraps async function with error handling
 */
function withErrorHandling(fn) {
  return async function(...args) {
    try {
      return await fn(...args);
    } catch (error) {
      return await handleError(error, {
        function: fn.name,
        args: JSON.stringify(args)
      });
    }
  };
}

/**
 * Creates safe version of async function that won't throw
 */
function safe(fn) {
  return async function(...args) {
    try {
      const result = await fn(...args);
      return { success: true, data: result, error: null };
    } catch (error) {
      logger.error('Safe function caught error', {
        function: fn.name,
        error: error.message
      });
      return { success: false, data: null, error };
    }
  };
}

module.exports = {
  EmailAssistantError,
  ErrorCodes,
  handleError,
  isTransientError,
  withErrorHandling,
  safe
};
