#!/usr/bin/env node
/**
 * Secure Credential Manager for Node.js/Lambda
 * Handles encrypted credential storage and AWS Secrets Manager integration
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const os = require('os');
const { promisify } = require('util');

// AWS SDK (optional, for Lambda deployments)
let AWS;
try {
  AWS = require('aws-sdk');
} catch (e) {
  console.log('AWS SDK not available, using local storage only');
}

class SecureCredentialManager {
  constructor(options = {}) {
    this.vaultPath = options.vaultPath || path.join(os.homedir(), '.my-workspace-vault');
    this.useAWS = options.useAWS && AWS !== undefined;
    this.awsRegion = options.awsRegion || process.env.AWS_REGION || 'us-east-1';

    // Initialize AWS Secrets Manager if available
    if (this.useAWS) {
      this.secretsManager = new AWS.SecretsManager({ region: this.awsRegion });
    }

    // Ensure vault directory exists with proper permissions
    this.initializeVault();

    // Initialize encryption
    this.encryptionKey = this.getOrCreateEncryptionKey();

    // Audit log
    this.auditLog = [];
  }

  /**
   * Initialize vault directory with secure permissions
   */
  initializeVault() {
    if (!fs.existsSync(this.vaultPath)) {
      fs.mkdirSync(this.vaultPath, { recursive: true, mode: 0o700 });
    }

    // Set secure permissions on existing directory
    try {
      fs.chmodSync(this.vaultPath, 0o700);
    } catch (err) {
      console.warn(`Could not set permissions on ${this.vaultPath}:`, err.message);
    }
  }

  /**
   * Get or create encryption key
   */
  getOrCreateEncryptionKey() {
    const keyFile = path.join(this.vaultPath, '.key');

    if (fs.existsSync(keyFile)) {
      const key = fs.readFileSync(keyFile);
      return key;
    }

    // Generate new key
    const key = crypto.randomBytes(32);
    fs.writeFileSync(keyFile, key);
    fs.chmodSync(keyFile, 0o600);

    return key;
  }

  /**
   * Encrypt data
   */
  encrypt(text) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-256-cbc', this.encryptionKey, iv);
    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return iv.toString('hex') + ':' + encrypted;
  }

  /**
   * Decrypt data
   */
  decrypt(text) {
    const parts = text.split(':');
    const iv = Buffer.from(parts.shift(), 'hex');
    const encryptedText = Buffer.from(parts.join(':'), 'hex');
    const decipher = crypto.createDecipheriv('aes-256-cbc', this.encryptionKey, iv);
    let decrypted = decipher.update(encryptedText);
    decrypted = Buffer.concat([decrypted, decipher.final()]);
    return decrypted.toString();
  }

  /**
   * Store credential locally
   */
  async storeCredentialLocal(service, key, value, metadata = {}) {
    const credFile = path.join(this.vaultPath, 'credentials.json');

    let credentials = {};
    if (fs.existsSync(credFile)) {
      const encrypted = fs.readFileSync(credFile, 'utf8');
      try {
        const decrypted = this.decrypt(encrypted);
        credentials = JSON.parse(decrypted);
      } catch (err) {
        console.warn('Could not decrypt existing credentials, starting fresh');
        credentials = {};
      }
    }

    // Store credential
    if (!credentials[service]) {
      credentials[service] = {};
    }

    credentials[service][key] = {
      value: value,
      createdAt: new Date().toISOString(),
      rotateBy: new Date(Date.now() + (metadata.rotateDays || 30) * 24 * 60 * 60 * 1000).toISOString(),
      metadata: metadata
    };

    // Save encrypted
    const encrypted = this.encrypt(JSON.stringify(credentials, null, 2));
    fs.writeFileSync(credFile, encrypted);
    fs.chmodSync(credFile, 0o600);

    // Audit log
    this.logAudit('CREDENTIAL_STORED', { service, key });

    return true;
  }

  /**
   * Store credential in AWS Secrets Manager
   */
  async storeCredentialAWS(service, key, value, metadata = {}) {
    const secretName = `my-workspace/${service}`;

    try {
      // Get existing secret or create new one
      let existingSecret = {};
      try {
        const data = await this.secretsManager.getSecretValue({ SecretId: secretName }).promise();
        existingSecret = JSON.parse(data.SecretString);
      } catch (err) {
        if (err.code !== 'ResourceNotFoundException') {
          throw err;
        }
      }

      // Update secret
      existingSecret[key] = value;

      // Store in Secrets Manager
      try {
        await this.secretsManager.updateSecret({
          SecretId: secretName,
          SecretString: JSON.stringify(existingSecret)
        }).promise();
      } catch (err) {
        if (err.code === 'ResourceNotFoundException') {
          // Create new secret
          await this.secretsManager.createSecret({
            Name: secretName,
            SecretString: JSON.stringify(existingSecret),
            Description: `Credentials for ${service}`,
            Tags: [
              { Key: 'Application', Value: 'my-workspace' },
              { Key: 'Service', Value: service },
              { Key: 'ManagedBy', Value: 'credential-manager' }
            ]
          }).promise();
        } else {
          throw err;
        }
      }

      // Audit log
      this.logAudit('CREDENTIAL_STORED_AWS', { service, key });

      return true;
    } catch (err) {
      console.error('Failed to store credential in AWS:', err);
      throw err;
    }
  }

  /**
   * Store credential (auto-selects storage method)
   */
  async storeCredential(service, key, value, metadata = {}) {
    // Always store locally as backup
    await this.storeCredentialLocal(service, key, value, metadata);

    // Also store in AWS if configured
    if (this.useAWS) {
      try {
        await this.storeCredentialAWS(service, key, value, metadata);
      } catch (err) {
        console.warn('Failed to store in AWS, local storage successful');
      }
    }

    return true;
  }

  /**
   * Get credential from local storage
   */
  async getCredentialLocal(service, key) {
    const credFile = path.join(this.vaultPath, 'credentials.json');

    if (!fs.existsSync(credFile)) {
      return null;
    }

    try {
      const encrypted = fs.readFileSync(credFile, 'utf8');
      const decrypted = this.decrypt(encrypted);
      const credentials = JSON.parse(decrypted);

      if (credentials[service] && credentials[service][key]) {
        const entry = credentials[service][key];

        // Check rotation
        const rotateBy = new Date(entry.rotateBy);
        if (rotateBy < new Date()) {
          console.warn(`Credential ${service}:${key} needs rotation (expired ${rotateBy})`);
        }

        // Audit log
        this.logAudit('CREDENTIAL_ACCESSED', { service, key });

        return entry.value;
      }
    } catch (err) {
      console.error('Failed to get credential locally:', err);
    }

    return null;
  }

  /**
   * Get credential from AWS Secrets Manager
   */
  async getCredentialAWS(service, key) {
    const secretName = `my-workspace/${service}`;

    try {
      const data = await this.secretsManager.getSecretValue({ SecretId: secretName }).promise();
      const secrets = JSON.parse(data.SecretString);

      if (secrets[key]) {
        // Audit log
        this.logAudit('CREDENTIAL_ACCESSED_AWS', { service, key });
        return secrets[key];
      }
    } catch (err) {
      if (err.code !== 'ResourceNotFoundException') {
        console.error('Failed to get credential from AWS:', err);
      }
    }

    return null;
  }

  /**
   * Get credential (auto-selects storage method)
   */
  async getCredential(service, key) {
    // Try AWS first if configured
    if (this.useAWS) {
      const awsValue = await this.getCredentialAWS(service, key);
      if (awsValue) {
        return awsValue;
      }
    }

    // Fall back to local storage
    return await this.getCredentialLocal(service, key);
  }

  /**
   * Migrate credentials from .env file
   */
  async migrateFromEnv(envFilePath, service) {
    if (!fs.existsSync(envFilePath)) {
      console.warn(`Environment file not found: ${envFilePath}`);
      return;
    }

    const content = fs.readFileSync(envFilePath, 'utf8');
    const lines = content.split('\n');
    const migrated = [];

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        const [key, ...valueParts] = trimmed.split('=');
        const value = valueParts.join('=').trim().replace(/^["']|["']$/g, '');

        // Determine rotation period
        let rotateDays = 30;
        if (key.toLowerCase().includes('api') || key.toLowerCase().includes('key')) {
          rotateDays = 90;
        }

        await this.storeCredential(service, key.trim(), value, { rotateDays });
        migrated.push(key.trim());
      }
    }

    if (migrated.length > 0) {
      console.log(`Migrated ${migrated.length} credentials from ${envFilePath}`);

      // Backup original file
      const backupPath = envFilePath + '.backup';
      fs.renameSync(envFilePath, backupPath);
      console.log(`Original file backed up to ${backupPath}`);

      // Log migration
      this.logAudit('ENV_FILE_MIGRATED', { service, file: envFilePath, keys: migrated });
    }

    return migrated;
  }

  /**
   * Setup Lambda environment variables
   */
  async setupLambdaEnvironment() {
    const credentials = await this.getAllCredentials();
    const env = {};

    for (const [service, keys] of Object.entries(credentials)) {
      for (const [key, entry] of Object.entries(keys)) {
        // Convert to uppercase environment variable format
        const envKey = `${service.toUpperCase()}_${key.toUpperCase()}`;
        env[envKey] = entry.value;
      }
    }

    return env;
  }

  /**
   * Get all credentials (for listing)
   */
  async getAllCredentials() {
    const credFile = path.join(this.vaultPath, 'credentials.json');

    if (!fs.existsSync(credFile)) {
      return {};
    }

    try {
      const encrypted = fs.readFileSync(credFile, 'utf8');
      const decrypted = this.decrypt(encrypted);
      return JSON.parse(decrypted);
    } catch (err) {
      console.error('Failed to load credentials:', err);
      return {};
    }
  }

  /**
   * Check which credentials need rotation
   */
  async checkRotation() {
    const credentials = await this.getAllCredentials();
    const needsRotation = [];

    for (const [service, keys] of Object.entries(credentials)) {
      for (const [key, entry] of Object.entries(keys)) {
        const rotateBy = new Date(entry.rotateBy);
        if (rotateBy < new Date()) {
          needsRotation.push({
            service,
            key,
            expiredAt: entry.rotateBy,
            daysOverdue: Math.floor((new Date() - rotateBy) / (1000 * 60 * 60 * 24))
          });
        }
      }
    }

    return needsRotation;
  }

  /**
   * Validate file permissions
   */
  validatePermissions() {
    const results = {};
    const paths = [
      this.vaultPath,
      path.join(this.vaultPath, '.key'),
      path.join(this.vaultPath, 'credentials.json'),
      path.join(this.vaultPath, 'audit.log')
    ];

    for (const p of paths) {
      if (fs.existsSync(p)) {
        const stats = fs.statSync(p);
        const mode = (stats.mode & parseInt('777', 8)).toString(8);

        let isSecure;
        if (stats.isDirectory()) {
          isSecure = mode === '700';
        } else {
          isSecure = mode === '600';
        }

        results[p] = { mode, isSecure };

        if (!isSecure) {
          console.warn(`Insecure permissions on ${p}: ${mode}`);
          // Fix permissions
          if (stats.isDirectory()) {
            fs.chmodSync(p, 0o700);
          } else {
            fs.chmodSync(p, 0o600);
          }
          results[p].fixed = true;
        }
      }
    }

    return results;
  }

  /**
   * Log audit event
   */
  logAudit(action, details) {
    const entry = {
      timestamp: new Date().toISOString(),
      action,
      details,
      user: process.env.USER || 'unknown',
      pid: process.pid
    };

    this.auditLog.push(entry);

    // Also write to file
    const auditFile = path.join(this.vaultPath, 'audit.log');
    fs.appendFileSync(auditFile, JSON.stringify(entry) + '\n');

    // Ensure proper permissions
    if (fs.existsSync(auditFile)) {
      try {
        fs.chmodSync(auditFile, 0o600);
      } catch (err) {
        // Ignore permission errors on some systems
      }
    }
  }

  /**
   * Setup secure MCP configuration
   */
  async setupMCPConfig(services = []) {
    const configDir = path.join(os.homedir(), '.config', 'claude');

    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true, mode: 0o700 });
    }

    const config = {
      mcpServers: {}
    };

    // Configure each service
    for (const service of services) {
      if (service === 'gmail') {
        const token = await this.getCredential('gmail', 'oauth_token');
        if (token) {
          config.mcpServers.gmail = {
            command: 'npx',
            args: ['-y', '@gongrzhe/server-gmail-autoauth-mcp'],
            env: {
              GMAIL_OAUTH_TOKEN: token
            }
          };
        }
      } else if (service === 'todoist') {
        const apiKey = await this.getCredential('todoist', 'api_key');
        if (apiKey) {
          config.mcpServers.todoist = {
            command: 'npx',
            args: ['-y', '@todoist/mcp-server'],
            env: {
              TODOIST_API_TOKEN: apiKey
            }
          };
        }
      } else if (service === 'ynab') {
        const apiKey = await this.getCredential('ynab', 'api_key');
        if (apiKey) {
          config.mcpServers.ynab = {
            command: 'npx',
            args: ['-y', '@ynab/mcp-server'],
            env: {
              YNAB_API_KEY: apiKey
            }
          };
        }
      }
    }

    // Write config file with secure permissions
    const configFile = path.join(configDir, 'claude_code_config.json');
    fs.writeFileSync(configFile, JSON.stringify(config, null, 2));
    fs.chmodSync(configFile, 0o600);

    console.log(`MCP configuration written to ${configFile}`);
    return configFile;
  }
}

// CLI interface
if (require.main === module) {
  const manager = new SecureCredentialManager({
    useAWS: process.env.USE_AWS === 'true'
  });

  const args = process.argv.slice(2);
  const command = args[0];

  async function main() {
    switch (command) {
      case 'store':
        if (args.length < 4) {
          console.error('Usage: credential-manager.js store <service> <key> <value>');
          process.exit(1);
        }
        await manager.storeCredential(args[1], args[2], args[3]);
        console.log(`Stored credential for ${args[1]}:${args[2]}`);
        break;

      case 'get':
        if (args.length < 3) {
          console.error('Usage: credential-manager.js get <service> <key>');
          process.exit(1);
        }
        const value = await manager.getCredential(args[1], args[2]);
        if (value) {
          console.log(value);
        } else {
          console.error(`Credential not found: ${args[1]}:${args[2]}`);
          process.exit(1);
        }
        break;

      case 'migrate':
        if (args.length < 3) {
          console.error('Usage: credential-manager.js migrate <env-file> <service>');
          process.exit(1);
        }
        await manager.migrateFromEnv(args[1], args[2]);
        break;

      case 'check-rotation':
        const needsRotation = await manager.checkRotation();
        if (needsRotation.length > 0) {
          console.log('Credentials needing rotation:');
          for (const cred of needsRotation) {
            console.log(`  - ${cred.service}:${cred.key} (overdue by ${cred.daysOverdue} days)`);
          }
        } else {
          console.log('All credentials are up to date');
        }
        break;

      case 'validate':
        const results = manager.validatePermissions();
        console.log('Permission validation results:');
        for (const [path, info] of Object.entries(results)) {
          const status = info.isSecure ? '✓ SECURE' : (info.fixed ? '⚠️ FIXED' : '✗ INSECURE');
          console.log(`  ${path}: ${status} (${info.mode})`);
        }
        break;

      case 'setup-mcp':
        if (args.length < 2) {
          console.error('Usage: credential-manager.js setup-mcp <service1,service2,...>');
          process.exit(1);
        }
        const services = args[1].split(',');
        await manager.setupMCPConfig(services);
        break;

      default:
        console.log('Usage: credential-manager.js <command> [options]');
        console.log('Commands:');
        console.log('  store <service> <key> <value>  - Store a credential');
        console.log('  get <service> <key>            - Retrieve a credential');
        console.log('  migrate <env-file> <service>   - Migrate from .env file');
        console.log('  check-rotation                 - Check for credentials needing rotation');
        console.log('  validate                       - Validate file permissions');
        console.log('  setup-mcp <services>          - Setup MCP configuration');
        process.exit(1);
    }
  }

  main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
  });
}

module.exports = SecureCredentialManager;