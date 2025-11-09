/**
 * Structured Logger for Email Assistant
 *
 * Provides consistent, structured logging across the application.
 * Supports different log levels and automatic context injection.
 */

class Logger {
  constructor(context = {}) {
    this.context = context;
    this.levels = {
      error: 0,
      warn: 1,
      info: 2,
      debug: 3
    };
    this.currentLevel = process.env.LOG_LEVEL || 'info';
  }

  shouldLog(level) {
    return this.levels[level] <= this.levels[this.currentLevel];
  }

  formatMessage(level, message, meta = {}) {
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      level: level.toUpperCase(),
      message,
      ...this.context,
      ...meta
    });
  }

  error(message, meta = {}) {
    if (this.shouldLog('error')) {
      console.error(this.formatMessage('error', message, {
        ...meta,
        stack: meta.error?.stack
      }));
    }
  }

  warn(message, meta = {}) {
    if (this.shouldLog('warn')) {
      console.warn(this.formatMessage('warn', message, meta));
    }
  }

  info(message, meta = {}) {
    if (this.shouldLog('info')) {
      console.log(this.formatMessage('info', message, meta));
    }
  }

  debug(message, meta = {}) {
    if (this.shouldLog('debug')) {
      console.log(this.formatMessage('debug', message, meta));
    }
  }

  child(additionalContext) {
    return new Logger({
      ...this.context,
      ...additionalContext
    });
  }
}

// Singleton instance
const logger = new Logger({
  service: 'email-assistant',
  environment: process.env.NODE_ENV || 'production'
});

// Export both the singleton and the class for testing
module.exports = logger;
module.exports.Logger = Logger;
