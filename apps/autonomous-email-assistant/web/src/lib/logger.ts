/* eslint-disable no-console */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogContext {
  [key: string]: any
}

class Logger {
  private minLevel: LogLevel
  private context: LogContext

  constructor(minLevel: LogLevel = 'info', context: LogContext = {}) {
    this.minLevel = process.env.LOG_LEVEL as LogLevel || minLevel
    this.context = context
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error']
    return levels.indexOf(level) >= levels.indexOf(this.minLevel)
  }

  private formatMessage(level: LogLevel, message: string, data?: LogContext) {
    const timestamp = new Date().toISOString()
    const ctx = { ...this.context, ...data }
    const contextStr = Object.keys(ctx).length > 0 ? JSON.stringify(ctx, null, 2) : ''

    return {
      timestamp,
      level: level.toUpperCase(),
      message,
      ...ctx,
    }
  }

  private sendToExternalService(level: LogLevel, message: string, data?: LogContext) {
    // Send to external logging service (e.g., Sentry, LogRocket, Datadog)
    if (typeof window !== 'undefined') {
      // Client-side logging
      if ((window as any).Sentry) {
        if (level === 'error') {
          ;(window as any).Sentry.captureMessage(message, {
            level: 'error',
            extra: data,
          })
        }
      }
    } else {
      // Server-side logging
      // Could send to CloudWatch, Datadog, etc.
    }
  }

  debug(message: string, data?: LogContext) {
    if (!this.shouldLog('debug')) return
    const formatted = this.formatMessage('debug', message, data)
    console.debug(formatted)
  }

  info(message: string, data?: LogContext) {
    if (!this.shouldLog('info')) return
    const formatted = this.formatMessage('info', message, data)
    console.info(formatted)
  }

  warn(message: string, data?: LogContext) {
    if (!this.shouldLog('warn')) return
    const formatted = this.formatMessage('warn', message, data)
    console.warn(formatted)
    this.sendToExternalService('warn', message, data)
  }

  error(message: string, error?: Error | LogContext, data?: LogContext) {
    if (!this.shouldLog('error')) return

    let errorData: LogContext = {}
    if (error instanceof Error) {
      errorData = {
        error: {
          name: error.name,
          message: error.message,
          stack: error.stack,
        },
        ...data,
      }
    } else {
      errorData = { ...error, ...data }
    }

    const formatted = this.formatMessage('error', message, errorData)
    console.error(formatted)
    this.sendToExternalService('error', message, errorData)
  }

  // Create child logger with additional context
  child(context: LogContext): Logger {
    return new Logger(this.minLevel, { ...this.context, ...context })
  }

  // Measure execution time
  async measure<T>(name: string, fn: () => Promise<T> | T): Promise<T> {
    const start = performance.now()
    try {
      const result = await fn()
      const duration = performance.now() - start
      this.debug(`${name} completed`, { duration: `${duration.toFixed(2)}ms` })
      return result
    } catch (error) {
      const duration = performance.now() - start
      this.error(`${name} failed`, error as Error, { duration: `${duration.toFixed(2)}ms` })
      throw error
    }
  }
}

// Default logger instance
export const logger = new Logger()

// Create logger for specific module
export function createLogger(module: string, context?: LogContext): Logger {
  return new Logger('info', { module, ...context })
}

// API request logger middleware
export function logAPIRequest(method: string, path: string, userId?: string) {
  logger.info('API Request', {
    method,
    path,
    userId,
    timestamp: new Date().toISOString(),
  })
}

// API error logger
export function logAPIError(method: string, path: string, error: Error, userId?: string) {
  logger.error('API Error', error, {
    method,
    path,
    userId,
    timestamp: new Date().toISOString(),
  })
}

// Database query logger
export function logDatabaseQuery(query: string, duration: number) {
  if (duration > 1000) {
    logger.warn('Slow database query', {
      query,
      duration: `${duration}ms`,
    })
  } else {
    logger.debug('Database query', {
      query,
      duration: `${duration}ms`,
    })
  }
}
