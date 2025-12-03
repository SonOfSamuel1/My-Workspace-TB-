# Security Framework for My Workspace

## 🔐 Overview

This security framework provides comprehensive protection for running My Workspace applications with the `--dangerously-skip-permissions` flag. It implements defense-in-depth security controls across credentials, applications, and infrastructure.

## ⚡ Quick Start

### 1. Initial Setup

```bash
# Navigate to security directory
cd security

# Install Python dependencies
pip3 install cryptography keyring

# Install Node.js dependencies (if using Lambda)
npm install aws-sdk

# Make scripts executable
chmod +x safe-execute.sh
```

### 2. Migrate Existing Credentials

```bash
# Migrate all .env files to secure storage
./safe-execute.sh --migrate-env

# Or migrate individually
python3 credential-manager.py migrate --env-file ../apps/weekly-budget-report/.env --service weekly-budget
python3 credential-manager.py migrate --env-file ../apps/autonomous-email-assistant/.env --service email-assistant
```

### 3. Run Applications Safely

```bash
# Execute with full security checks
./safe-execute.sh autonomous-email-assistant

# Execute weekly budget report
./safe-execute.sh weekly-budget-report

# Run with dry-run to test security without execution
./safe-execute.sh autonomous-email-assistant --dry-run
```

## 🛡️ Security Components

### 1. Credential Manager (`credential-manager.py` / `credential-manager.js`)

Provides encrypted storage and management of sensitive credentials.

**Features:**
- 🔒 AES-256 encryption for credentials at rest
- 🔑 Master key stored in system keyring
- 📅 Automatic rotation reminders
- 🔍 Audit trail for all credential access
- 🛠️ AWS Secrets Manager integration (optional)

**Usage:**

```bash
# Store a credential
python3 credential-manager.py store --service gmail --key api_key --value "your-key" --rotate-days 30

# Retrieve a credential
python3 credential-manager.py get --service gmail --key api_key

# List all credentials
python3 credential-manager.py list

# Check for credentials needing rotation
python3 credential-manager.py check-rotation

# Validate file permissions
python3 credential-manager.py validate
```

### 2. Safe Execution Wrapper (`safe-execute.sh`)

Provides a secure execution environment with pre-flight checks and monitoring.

**Features:**
- ✅ Pre-flight security validation
- 📊 Rate limit enforcement
- 📝 Audit logging
- 🔐 Secure environment setup
- 🧹 Post-execution cleanup

**Pre-flight Checks:**
1. Credential validation and migration
2. File permission verification (0600/0700)
3. Rate limit status check
4. Application-specific security setup
5. MCP server configuration

**Usage:**

```bash
# Run with full security
./safe-execute.sh autonomous-email-assistant

# Skip pre-flight checks (not recommended)
./safe-execute.sh autonomous-email-assistant --skip-preflight

# Dry run (checks only, no execution)
./safe-execute.sh weekly-budget-report --dry-run
```

### 3. Rate Limiter (`rate-limiter.py`)

Implements token bucket algorithm for API rate limiting.

**Default Limits:**

| Application | Limit Type | Rate |
|------------|------------|------|
| Email Assistant | Email sends | 10/hour |
| Email Assistant | SMS sends | 1/5 minutes |
| Email Assistant | Gmail API | 250/second |
| Budget Report | YNAB API | 200/hour |
| Budget Report | Report generation | 1/day |
| Love Trackers | Google Docs API | 60/minute |

**Usage:**

```python
from security.rate_limiter import ApplicationRateLimiter

# Initialize for specific app
limiter = ApplicationRateLimiter("autonomous-email-assistant")

# Check if action is allowed
if limiter.can_send_email():
    # Send email
    pass
else:
    print("Rate limit exceeded")

# Wait for availability
limiter.wait_for_email()  # Blocks until tokens available

# Check status
status = limiter.get_status()
print(f"Email tokens: {status['email_send']['tokens']}")
```

### 4. Audit Logger (`audit-logger.py`)

Provides tamper-proof audit logging with hash chain verification.

**Features:**
- 🔗 Blockchain-style hash chaining
- 📊 Event categorization by severity
- 🔍 Search and reporting capabilities
- 📦 Automatic log rotation and compression
- ⚠️ Critical event alerting

**Event Types:**
- `AUTH_SUCCESS` / `AUTH_FAILURE`
- `EMAIL_SENT` / `EMAIL_BLOCKED`
- `SMS_SENT` / `SMS_ESCALATION`
- `API_CALL` / `API_RATE_LIMIT`
- `SECURITY_VIOLATION`
- `CREDENTIAL_ACCESS`

**Usage:**

```python
from security.audit_logger import SecureAuditLogger, AuditEvent, AuditLevel

# Initialize
logger = SecureAuditLogger("autonomous-email-assistant")

# Log events
logger.log_email_sent("user@example.com", "Subject", tier=2, confidence=0.95)
logger.log_api_call("gmail", "/messages/send", "POST", 200)
logger.log_security_violation("unauthorized_access", "Details...")

# Verify integrity
is_valid = logger.verify_integrity()

# Generate report
report = logger.generate_report("daily")
```

### 5. Email Classifier Security (`email-classifier-secure.js`)

Secure email classification with validation layers.

**Features:**
- 🚫 Off-limits contact detection
- 📊 Confidence threshold validation
- 🔍 Suspicious pattern detection
- 📝 Classification caching
- 🛡️ Security overrides

**Configuration:**

```json
{
  "email_classification": {
    "tier_1_confidence_threshold": 0.95,
    "tier_2_confidence_threshold": 0.9,
    "off_limits_contacts": [
      "sensitive@example.com"
    ]
  }
}
```

## 🔒 Security Configuration Files

### Application Security Configs

Each application has a `security-config.json`:

```json
{
  "rate_limits": {
    "emails_per_hour": 10,
    "api_calls_per_minute": 30
  },
  "audit": {
    "log_all_sends": true,
    "store_drafts": true
  }
}
```

### File Permissions

All sensitive files are automatically secured:

| File Type | Permission | Octal |
|-----------|------------|-------|
| Credential files | Owner R/W only | 0600 |
| Config files | Owner R/W only | 0600 |
| Log files | Owner R/W only | 0600 |
| Directories | Owner R/W/X only | 0700 |

## 📊 Monitoring & Alerts

### Real-time Monitoring

The safe execution wrapper provides real-time monitoring:

```bash
# View audit logs
tail -f ~/.my-workspace-vault/audit/*.audit.jsonl

# Check rate limit status
python3 rate-limiter.py status --app autonomous-email-assistant

# Verify audit log integrity
python3 audit-logger.py verify --app weekly-budget-report
```

### Critical Event Alerts

Critical events are logged to:
- `~/.my-workspace-vault/audit/critical_events.log`
- CloudWatch Logs (if in AWS Lambda)
- System audit log

## 🚀 AWS Lambda Deployment

### Secure Lambda Setup

1. **Store credentials in AWS Secrets Manager:**
```bash
# Export credentials for AWS
python3 credential-manager.py export-lambda --service email-assistant --output /tmp/secrets.json

# Upload to AWS Secrets Manager
aws secretsmanager create-secret --name my-workspace/email-assistant --secret-string file:///tmp/secrets.json
rm /tmp/secrets.json
```

2. **Configure Lambda environment:**
```json
{
  "Environment": {
    "Variables": {
      "SECURITY_MODE": "enforced",
      "AUDIT_ENABLED": "true",
      "RATE_LIMITING": "enabled"
    }
  }
}
```

3. **IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:my-workspace/*"
    }
  ]
}
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Permission Denied Errors

```bash
# Fix all permissions
python3 credential-manager.py validate
```

#### 2. Rate Limit Exceeded

```bash
# Check status
python3 rate-limiter.py status --app autonomous-email-assistant

# Reset limits (use carefully)
python3 rate-limiter.py reset --app autonomous-email-assistant
```

#### 3. Credential Not Found

```bash
# List all credentials
python3 credential-manager.py list

# Re-migrate from .env
python3 credential-manager.py migrate --env-file path/to/.env --service service-name
```

#### 4. Audit Log Integrity Failure

```bash
# Check specific date range
python3 audit-logger.py verify --app email-assistant --start 20240101 --end 20240131

# Generate integrity report
python3 audit-logger.py report --app email-assistant --period weekly
```

## 📋 Security Checklist

Before running with `--dangerously-skip-permissions`:

- [ ] All credentials migrated to secure storage
- [ ] File permissions validated (0600/0700)
- [ ] Rate limits configured appropriately
- [ ] Audit logging enabled
- [ ] Off-limits contacts configured
- [ ] Security configs in place for each app
- [ ] MCP servers using secure credential manager
- [ ] Backup of original .env files created
- [ ] Critical event monitoring active
- [ ] Post-execution cleanup configured

## 🔐 Best Practices

1. **Credential Rotation**
   - OAuth tokens: Every 30 days
   - API keys: Every 90 days
   - Check weekly: `python3 credential-manager.py check-rotation`

2. **Audit Log Review**
   - Daily: Check critical events
   - Weekly: Generate summary report
   - Monthly: Verify integrity

3. **Rate Limit Tuning**
   - Monitor actual usage patterns
   - Adjust limits based on needs
   - Leave 20% buffer for bursts

4. **Security Updates**
   - Keep dependencies updated
   - Review security configs monthly
   - Test disaster recovery quarterly

## 📊 Security Metrics

Track these KPIs:

| Metric | Target | Check Command |
|--------|--------|---------------|
| Credentials needing rotation | 0 | `credential-manager.py check-rotation` |
| Failed authentications | <5/day | `audit-logger.py search --event AUTH_FAILURE` |
| Rate limit violations | <10/day | `audit-logger.py search --event API_RATE_LIMIT` |
| Security violations | 0 | `audit-logger.py search --level CRITICAL` |
| Audit log integrity | 100% | `audit-logger.py verify` |

## 🆘 Emergency Procedures

### Suspected Breach

1. **Immediately revoke all credentials:**
```bash
# Rotate all credentials
for service in email-assistant budget-report love-tracker; do
    python3 credential-manager.py rotate --service $service --force
done
```

2. **Review audit logs:**
```bash
python3 audit-logger.py search --level CRITICAL --period daily
```

3. **Generate security report:**
```bash
python3 audit-logger.py report --app all --period weekly > security-report.txt
```

### Rate Limit Emergency

```bash
# Emergency reset (use sparingly)
python3 rate-limiter.py reset --app autonomous-email-assistant --emergency
```

## 📚 Additional Resources

- [OWASP Security Guidelines](https://owasp.org)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [Python Cryptography Docs](https://cryptography.io)
- [Node.js Security Checklist](https://blog.risingstack.com/node-js-security-checklist/)

## 🤝 Contributing

When adding new security features:

1. Update this README
2. Add unit tests
3. Document in code
4. Update security checklist
5. Test with `--dry-run` first

## 📝 License

This security framework is part of My Workspace and follows the same license terms.

---

**Security Contact:** For security issues, create a private issue in the repository.

**Last Security Audit:** 2025-11-24
**Next Scheduled Audit:** 2025-12-24