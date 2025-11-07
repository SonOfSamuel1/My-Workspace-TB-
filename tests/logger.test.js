/**
 * Tests for Logger utility
 */

const Logger = require('../lib/logger');

describe('Logger', () => {
  let logger;
  let consoleLogSpy;
  let consoleErrorSpy;
  let consoleWarnSpy;

  beforeEach(() => {
    logger = new Logger({ service: 'test' });
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  test('logs info messages as JSON', () => {
    logger.info('test message', { foo: 'bar' });

    expect(consoleLogSpy).toHaveBeenCalledTimes(1);
    const loggedData = JSON.parse(consoleLogSpy.mock.calls[0][0]);

    expect(loggedData).toMatchObject({
      level: 'INFO',
      message: 'test message',
      service: 'test',
      foo: 'bar'
    });
    expect(loggedData.timestamp).toBeDefined();
  });

  test('logs error messages with stack trace', () => {
    const error = new Error('test error');
    logger.error('error occurred', { error });

    expect(consoleErrorSpy).toHaveBeenCalledTimes(1);
    const loggedData = JSON.parse(consoleErrorSpy.mock.calls[0][0]);

    expect(loggedData).toMatchObject({
      level: 'ERROR',
      message: 'error occurred',
      service: 'test'
    });
    expect(loggedData.stack).toBeDefined();
  });

  test('respects log level', () => {
    process.env.LOG_LEVEL = 'error';
    const restrictedLogger = new Logger();

    restrictedLogger.debug('debug message');
    restrictedLogger.info('info message');
    restrictedLogger.warn('warn message');
    restrictedLogger.error('error message');

    expect(consoleLogSpy).not.toHaveBeenCalled();
    expect(consoleWarnSpy).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledTimes(1);

    delete process.env.LOG_LEVEL;
  });

  test('child logger inherits parent context', () => {
    const childLogger = logger.child({ requestId: '123' });
    childLogger.info('child message');

    const loggedData = JSON.parse(consoleLogSpy.mock.calls[0][0]);
    expect(loggedData).toMatchObject({
      service: 'test',
      requestId: '123',
      message: 'child message'
    });
  });
});
