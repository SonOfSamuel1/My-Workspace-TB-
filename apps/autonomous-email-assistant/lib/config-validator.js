/**
 * Configuration Validator
 *
 * Validates environment variables and configuration to prevent
 * runtime errors from missing or invalid configuration.
 */

const logger = require('./logger');

class ValidationError extends Error {
  constructor(message, errors) {
    super(message);
    this.name = 'ValidationError';
    this.errors = errors;
  }
}

/**
 * Validates required environment variables
 */
function validateEnvironment() {
  const errors = [];

  // Required variables
  const required = [
    'CLAUDE_CODE_OAUTH_TOKEN',
    'GMAIL_OAUTH_CREDENTIALS',
    'GMAIL_CREDENTIALS'
  ];

  for (const varName of required) {
    if (!process.env[varName]) {
      errors.push(`Missing required environment variable: ${varName}`);
    }
  }

  // Validate OAuth token format
  if (process.env.CLAUDE_CODE_OAUTH_TOKEN) {
    const tokenPattern = /^sk-ant-oat01-[A-Za-z0-9_-]+$/;
    if (!tokenPattern.test(process.env.CLAUDE_CODE_OAUTH_TOKEN)) {
      errors.push('CLAUDE_CODE_OAUTH_TOKEN has invalid format');
    }
  }

  // Validate phone number format if provided
  if (process.env.ESCALATION_PHONE) {
    const phonePattern = /^\+\d{10,15}$/;
    if (!phonePattern.test(process.env.ESCALATION_PHONE)) {
      errors.push('ESCALATION_PHONE must be in format +1234567890');
    }
  }

  // Validate Twilio config (all or none)
  const twilioVars = [
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_FROM_NUMBER'
  ];
  const twilioProvided = twilioVars.filter(v => process.env[v]);

  if (twilioProvided.length > 0 && twilioProvided.length < twilioVars.length) {
    errors.push('Twilio config incomplete: must provide all of TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER or none');
  }

  // Validate base64 encoded credentials can be decoded
  try {
    if (process.env.GMAIL_OAUTH_CREDENTIALS) {
      const decoded = Buffer.from(process.env.GMAIL_OAUTH_CREDENTIALS, 'base64').toString('utf-8');
      JSON.parse(decoded);
    }
  } catch (error) {
    errors.push('GMAIL_OAUTH_CREDENTIALS is not valid base64-encoded JSON');
  }

  try {
    if (process.env.GMAIL_CREDENTIALS) {
      const decoded = Buffer.from(process.env.GMAIL_CREDENTIALS, 'base64').toString('utf-8');
      JSON.parse(decoded);
    }
  } catch (error) {
    errors.push('GMAIL_CREDENTIALS is not valid base64-encoded JSON');
  }

  if (errors.length > 0) {
    logger.error('Environment validation failed', { errors });
    throw new ValidationError('Invalid environment configuration', errors);
  }

  logger.info('Environment validation passed');
  return true;
}

/**
 * Validates execution mode
 */
function validateExecutionMode(mode) {
  const validModes = ['morning_brief', 'eod_report', 'midday_check', 'hourly_process'];

  if (!validModes.includes(mode)) {
    throw new ValidationError(
      `Invalid execution mode: ${mode}`,
      [`Mode must be one of: ${validModes.join(', ')}`]
    );
  }

  return true;
}

/**
 * Validates configuration file exists and has required fields
 */
function validateConfigFile(configPath, fs) {
  const errors = [];

  // Check file exists
  if (!fs.existsSync(configPath)) {
    errors.push(`Configuration file not found: ${configPath}`);
    throw new ValidationError('Configuration file missing', errors);
  }

  // Read and validate content
  const content = fs.readFileSync(configPath, 'utf-8');

  const requiredFields = [
    'Name:',
    'Email:',
    'Time Zone:',
    'Delegation Level:'
  ];

  for (const field of requiredFields) {
    if (!content.includes(field)) {
      errors.push(`Configuration file missing required field: ${field}`);
    }
  }

  if (errors.length > 0) {
    logger.error('Configuration file validation failed', { errors, configPath });
    throw new ValidationError('Invalid configuration file', errors);
  }

  logger.info('Configuration file validation passed', { configPath });
  return true;
}

/**
 * Sanitize sensitive data for logging
 */
function sanitizeForLogging(data) {
  const sensitive = ['token', 'password', 'key', 'secret', 'credentials'];

  if (typeof data !== 'object' || data === null) {
    return data;
  }

  const sanitized = Array.isArray(data) ? [] : {};

  for (const [key, value] of Object.entries(data)) {
    const keyLower = key.toLowerCase();
    const isSensitive = sensitive.some(word => keyLower.includes(word));

    if (isSensitive) {
      sanitized[key] = '***REDACTED***';
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = sanitizeForLogging(value);
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

module.exports = {
  validateEnvironment,
  validateExecutionMode,
  validateConfigFile,
  sanitizeForLogging,
  ValidationError
};
