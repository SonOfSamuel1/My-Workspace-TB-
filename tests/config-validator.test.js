/**
 * Tests for Config Validator
 */

const { validateEnvironment, validateExecutionMode, sanitizeForLogging, ValidationError } = require('../lib/config-validator');

describe('validateEnvironment', () => {
  let originalEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
    // Set required vars
    process.env.CLAUDE_CODE_OAUTH_TOKEN = 'sk-ant-oat01-validtoken123';
    process.env.GMAIL_OAUTH_CREDENTIALS = Buffer.from(JSON.stringify({ test: 'data' })).toString('base64');
    process.env.GMAIL_CREDENTIALS = Buffer.from(JSON.stringify({ test: 'data' })).toString('base64');
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  test('passes validation with all required vars', () => {
    expect(() => validateEnvironment()).not.toThrow();
  });

  test('fails when required vars are missing', () => {
    delete process.env.CLAUDE_CODE_OAUTH_TOKEN;

    expect(() => validateEnvironment()).toThrow(ValidationError);
    expect(() => validateEnvironment()).toThrow('CLAUDE_CODE_OAUTH_TOKEN');
  });

  test('validates OAuth token format', () => {
    process.env.CLAUDE_CODE_OAUTH_TOKEN = 'invalid-token';

    expect(() => validateEnvironment()).toThrow(ValidationError);
    expect(() => validateEnvironment()).toThrow('invalid format');
  });

  test('validates phone number format', () => {
    process.env.ESCALATION_PHONE = 'not-a-phone';

    expect(() => validateEnvironment()).toThrow(ValidationError);
    expect(() => validateEnvironment()).toThrow('+1234567890');
  });

  test('validates Twilio config completeness', () => {
    process.env.TWILIO_ACCOUNT_SID = 'ACxxxxx';
    // Missing other Twilio vars

    expect(() => validateEnvironment()).toThrow(ValidationError);
    expect(() => validateEnvironment()).toThrow('Twilio');
  });

  test('validates base64 JSON credentials', () => {
    process.env.GMAIL_OAUTH_CREDENTIALS = 'not-base64';

    expect(() => validateEnvironment()).toThrow(ValidationError);
  });
});

describe('validateExecutionMode', () => {
  test('accepts valid modes', () => {
    expect(() => validateExecutionMode('morning_brief')).not.toThrow();
    expect(() => validateExecutionMode('eod_report')).not.toThrow();
    expect(() => validateExecutionMode('midday_check')).not.toThrow();
    expect(() => validateExecutionMode('hourly_process')).not.toThrow();
  });

  test('rejects invalid modes', () => {
    expect(() => validateExecutionMode('invalid_mode')).toThrow(ValidationError);
  });
});

describe('sanitizeForLogging', () => {
  test('redacts sensitive fields', () => {
    const data = {
      username: 'john',
      password: 'secret123',
      apiKey: 'abc123',
      normalField: 'visible'
    };

    const sanitized = sanitizeForLogging(data);

    expect(sanitized.username).toBe('john');
    expect(sanitized.password).toBe('***REDACTED***');
    expect(sanitized.apiKey).toBe('***REDACTED***');
    expect(sanitized.normalField).toBe('visible');
  });

  test('handles nested objects', () => {
    const data = {
      config: {
        token: 'secret',
        public: 'visible'
      }
    };

    const sanitized = sanitizeForLogging(data);

    expect(sanitized.config.token).toBe('***REDACTED***');
    expect(sanitized.config.public).toBe('visible');
  });

  test('handles arrays', () => {
    const data = [
      { password: 'secret' },
      { username: 'john' }
    ];

    const sanitized = sanitizeForLogging(data);

    expect(sanitized[0].password).toBe('***REDACTED***');
    expect(sanitized[1].username).toBe('john');
  });

  test('returns non-objects unchanged', () => {
    expect(sanitizeForLogging('string')).toBe('string');
    expect(sanitizeForLogging(123)).toBe(123);
    expect(sanitizeForLogging(null)).toBe(null);
  });
});
