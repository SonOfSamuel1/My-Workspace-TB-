/**
 * Tests for Retry utility
 */

const { executeWithRetry, retryWithCondition, RetryConditions } = require('../lib/retry');

describe('executeWithRetry', () => {
  jest.setTimeout(10000);

  test('returns result on first success', async () => {
    const fn = jest.fn().mockResolvedValue('success');

    const result = await executeWithRetry(fn, { maxRetries: 3 });

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(1);
  });

  test('retries on failure and eventually succeeds', async () => {
    const fn = jest.fn()
      .mockRejectedValueOnce(new Error('fail 1'))
      .mockRejectedValueOnce(new Error('fail 2'))
      .mockResolvedValue('success');

    const result = await executeWithRetry(fn, {
      maxRetries: 3,
      initialDelay: 10
    });

    expect(result).toBe('success');
    expect(fn).toHaveBeenCalledTimes(3);
  });

  test('throws error after all retries exhausted', async () => {
    const fn = jest.fn().mockRejectedValue(new Error('persistent failure'));

    await expect(
      executeWithRetry(fn, { maxRetries: 3, initialDelay: 10 })
    ).rejects.toThrow('persistent failure');

    expect(fn).toHaveBeenCalledTimes(3);
  });

  test('applies exponential backoff', async () => {
    const fn = jest.fn()
      .mockRejectedValueOnce(new Error('fail'))
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValue('success');

    const startTime = Date.now();
    await executeWithRetry(fn, {
      maxRetries: 3,
      initialDelay: 100,
      backoffMultiplier: 2
    });
    const elapsed = Date.now() - startTime;

    // Should wait at least 100ms + 200ms = 300ms
    expect(elapsed).toBeGreaterThanOrEqual(250);
  });

  test('calls onRetry callback', async () => {
    const fn = jest.fn()
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValue('success');

    const onRetry = jest.fn();

    await executeWithRetry(fn, {
      maxRetries: 3,
      initialDelay: 10,
      onRetry
    });

    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onRetry).toHaveBeenCalledWith(1, expect.any(Error));
  });

  test('respects maxDelay limit', async () => {
    const fn = jest.fn()
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValue('success');

    const startTime = Date.now();
    await executeWithRetry(fn, {
      maxRetries: 3,
      initialDelay: 10000, // Would normally be 10s
      maxDelay: 50, // But capped at 50ms
      backoffMultiplier: 2
    });
    const elapsed = Date.now() - startTime;

    // Should wait max 50ms, not 10000ms
    expect(elapsed).toBeLessThan(200);
  });
});

describe('RetryConditions', () => {
  test('isNetworkError identifies network errors', () => {
    expect(RetryConditions.isNetworkError({ code: 'ECONNREFUSED' })).toBe(true);
    expect(RetryConditions.isNetworkError({ code: 'ETIMEDOUT' })).toBe(true);
    expect(RetryConditions.isNetworkError({ message: 'network failure' })).toBe(true);
    expect(RetryConditions.isNetworkError({ code: 'OTHER_ERROR' })).toBe(false);
  });

  test('isRateLimitError identifies rate limit errors', () => {
    expect(RetryConditions.isRateLimitError({ statusCode: 429 })).toBe(true);
    expect(RetryConditions.isRateLimitError({ message: 'rate limit exceeded' })).toBe(true);
    expect(RetryConditions.isRateLimitError({ statusCode: 200 })).toBe(false);
  });

  test('isServerError identifies 5xx errors', () => {
    expect(RetryConditions.isServerError({ statusCode: 500 })).toBe(true);
    expect(RetryConditions.isServerError({ statusCode: 503 })).toBe(true);
    expect(RetryConditions.isServerError({ statusCode: 400 })).toBe(false);
  });

  test('combine merges multiple conditions', () => {
    const combined = RetryConditions.combine(
      RetryConditions.isNetworkError,
      RetryConditions.isRateLimitError
    );

    expect(combined({ code: 'ETIMEDOUT' })).toBe(true);
    expect(combined({ statusCode: 429 })).toBe(true);
    expect(combined({ statusCode: 200 })).toBe(false);
  });
});

describe('retryWithCondition', () => {
  test('only retries when condition is met', async () => {
    const fn = jest.fn()
      .mockRejectedValueOnce({ statusCode: 500 }) // Retryable
      .mockRejectedValueOnce({ statusCode: 400 }) // Not retryable
      .mockResolvedValue('success');

    await expect(
      retryWithCondition(
        fn,
        RetryConditions.isServerError,
        { maxRetries: 3, initialDelay: 10 }
      )
    ).rejects.toEqual({ statusCode: 400 });

    // Should fail on second attempt (400 error), not retry
    expect(fn).toHaveBeenCalledTimes(2);
  });
});
