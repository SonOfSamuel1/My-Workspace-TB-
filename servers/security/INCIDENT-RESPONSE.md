# 🚨 Incident Response Procedures

## Table of Contents
1. [Incident Severity Levels](#incident-severity-levels)
2. [Immediate Response Actions](#immediate-response-actions)
3. [Incident Types and Procedures](#incident-types-and-procedures)
4. [Contact Information](#contact-information)
5. [Recovery Procedures](#recovery-procedures)
6. [Post-Incident Review](#post-incident-review)

---

## Incident Severity Levels

### 🔴 CRITICAL (P1)
**Response Time: Immediate (< 5 minutes)**
- Complete system compromise
- Credential theft/exposure
- Data breach
- Ransomware/malware detection
- Production system down

### 🟠 HIGH (P2)
**Response Time: < 30 minutes**
- Multiple authentication failures
- Rate limit violations (sustained)
- Audit log tampering detected
- Unauthorized access attempts
- API key exposure (non-production)

### 🟡 MEDIUM (P3)
**Response Time: < 2 hours**
- Single component failure
- Performance degradation
- Non-critical credential rotation needed
- Unusual API usage patterns

### 🟢 LOW (P4)
**Response Time: < 24 hours**
- Configuration issues
- Minor permission problems
- Routine maintenance needed

---

## Immediate Response Actions

### For ANY Security Incident:

```bash
# 1. Run immediate security check
cd /path/to/security
./security-monitor.sh check

# 2. Check audit logs for violations
python3 audit-logger.py search --event SECURITY_VIOLATION --period daily

# 3. Review credential status
python3 credential-manager.py check-rotation

# 4. Generate incident report
./security-audit.sh full > incident-$(date +%Y%m%d-%H%M%S).txt
```

---

## Incident Types and Procedures

### 1. 🔐 Credential Compromise

#### Detection Indicators:
- Unauthorized API calls
- Login from unknown IP/location
- Unusual access patterns
- Failed authentication spikes

#### Immediate Actions:

```bash
# Step 1: Revoke all credentials
cd security

# List all credentials
python3 credential-manager.py list

# Rotate specific service
python3 credential-manager.py store --service <service> --key <key> --value <new_value> --rotate-days 0

# Step 2: Kill active sessions
./safe-execute.sh --kill-all-sessions

# Step 3: Review access logs
python3 audit-logger.py search --event AUTH_SUCCESS --user unknown --period daily
```

#### Recovery Steps:
1. Generate new credentials for affected service
2. Update secure vault
3. Redeploy applications with new credentials
4. Monitor for unauthorized access
5. Enable 2FA where possible

### 2. 📧 Email System Compromise

#### Detection Indicators:
- Unauthorized email sends
- Off-limits contact violations
- Tier classification bypass
- SMS escalation abuse

#### Immediate Actions:

```bash
# Step 1: Disable email sending
cd apps/autonomous-email-assistant
echo '{"enabled": false}' > emergency-stop.json

# Step 2: Review sent emails
grep "EMAIL_SENT" ~/.my-workspace-vault/audit/*.jsonl | tail -50

# Step 3: Check rate limits
cd ../../security
python3 rate-limiter.py status --app autonomous-email-assistant

# Step 4: Revoke Gmail credentials
python3 credential-manager.py store --service gmail --key oauth_token --value REVOKED
```

#### Recovery Steps:
1. Review all sent emails in Gmail sent folder
2. Contact any incorrectly emailed recipients
3. Re-authenticate Gmail MCP server
4. Update off-limits contact list
5. Adjust classification thresholds

### 3. 💰 Financial System Breach (YNAB)

#### Detection Indicators:
- Unauthorized transaction creation
- Budget modification attempts
- Excessive API calls
- Data export attempts

#### Immediate Actions:

```bash
# Step 1: Revoke YNAB API access
cd security
python3 credential-manager.py store --service weekly-budget --key YNAB_API_KEY --value REVOKED

# Step 2: Check for modifications
python3 audit-logger.py search --event API_CALL --details ynab --period weekly

# Step 3: Enable read-only mode
cd ../apps/weekly-budget-report
echo '{"ynab": {"read_only": true, "emergency_mode": true}}' > security-override.json
```

#### Recovery Steps:
1. Login to YNAB web interface
2. Review all recent transactions
3. Check budget modifications
4. Generate new API token
5. Implement additional validation

### 4. 🔍 Audit Log Tampering

#### Detection Indicators:
- Hash chain verification failure
- Missing log entries
- Timestamp anomalies
- File permission changes

#### Immediate Actions:

```bash
# Step 1: Verify all logs
cd security
for app in autonomous-email-assistant weekly-budget-report; do
    echo "Checking $app..."
    python3 audit-logger.py verify --app $app
done

# Step 2: Backup current logs
tar -czf audit-backup-$(date +%Y%m%d).tar.gz ~/.my-workspace-vault/audit/

# Step 3: Check file integrity
find ~/.my-workspace-vault -type f -exec ls -la {} \; | grep -v "rw-------"
```

#### Recovery Steps:
1. Restore from backup if available
2. Reconstruct from CloudWatch logs
3. Re-initialize hash chain
4. Increase monitoring frequency
5. Enable immutable storage

### 5. 🚫 Rate Limit Abuse

#### Detection Indicators:
- Sustained rate limit violations
- API quota exhaustion
- Service degradation
- Cost spike alerts

#### Immediate Actions:

```bash
# Step 1: Check all rate limits
cd security
for app in autonomous-email-assistant weekly-budget-report; do
    python3 rate-limiter.py status --app $app
done

# Step 2: Reset rate limits (emergency)
python3 rate-limiter.py reset --app <affected-app>

# Step 3: Identify source
grep "RATE_LIMIT" ~/.my-workspace-vault/audit/*.jsonl | tail -100
```

#### Recovery Steps:
1. Identify root cause (bug, attack, misconfiguration)
2. Adjust rate limits if needed
3. Implement circuit breaker
4. Add IP-based rate limiting
5. Review cost implications

### 6. 🐛 Malware/Ransomware Detection

#### Detection Indicators:
- Encrypted files
- Suspicious processes
- Unexpected network connections
- File system modifications
- Performance degradation

#### Immediate Actions:

```bash
# Step 1: ISOLATE IMMEDIATELY
# Disconnect from network if possible

# Step 2: Check for encrypted files
find ~/. -name "*.encrypted" -o -name "*.locked" 2>/dev/null

# Step 3: Check running processes
ps aux | grep -E "claude|python|node" | grep -v grep

# Step 4: Backup critical data (if safe)
tar -czf emergency-backup.tar.gz ~/.my-workspace-vault/ --exclude="*.encrypted"

# Step 5: Check system integrity
cd security
./security-audit.sh full
```

#### Recovery Steps:
1. DO NOT pay ransom
2. Restore from clean backup
3. Rebuild affected systems
4. Change ALL credentials
5. Implement additional security layers

---

## Contact Information

### Internal Contacts

| Role | Contact | When to Contact |
|------|---------|----------------|
| Primary Admin | Terrance Brandon | All incidents |
| Email | terrance@goodportion.org | Non-critical |
| Phone | +1-407-744-8449 | CRITICAL only |

### External Contacts

| Service | Contact | Purpose |
|---------|---------|---------|
| AWS Support | Via Console | Lambda/CloudWatch issues |
| Google Cloud | Via Console | Gmail API issues |
| YNAB Support | support@ynab.com | API security concerns |
| Todoist Support | Via app | API issues |

### Emergency Services

| Incident Type | Contact |
|--------------|---------|
| Data Breach | Local authorities + legal counsel |
| Financial Fraud | Bank + YNAB support |
| Identity Theft | FTC + Credit bureaus |

---

## Recovery Procedures

### 1. Full System Recovery

```bash
#!/bin/bash
# Full recovery script

echo "Starting full system recovery..."

# Step 1: Verify backups
ls -la ~/backups/

# Step 2: Restore credentials
cd security
python3 credential-manager.py migrate --env-file ~/backups/credentials.backup --service all

# Step 3: Validate configurations
for app in apps/*; do
    if [[ -f "$app/security-config.json" ]]; then
        echo "Validating $app..."
        jq . "$app/security-config.json" > /dev/null
    fi
done

# Step 4: Reset rate limits
python3 rate-limiter.py reset --app all

# Step 5: Clear audit logs (start fresh)
rm -f ~/.my-workspace-vault/audit/*.jsonl
python3 audit-logger.py init

# Step 6: Test each component
./safe-execute.sh --test-all

echo "Recovery complete"
```

### 2. Credential Rotation

```bash
#!/bin/bash
# Rotate all credentials

cd security

# Gmail
echo "Rotating Gmail credentials..."
# Re-run Gmail OAuth flow
cd ../servers/gmail-mcp-server
npm run auth

# YNAB
echo "Rotating YNAB API key..."
# Get new key from https://app.ynab.com/settings/developer
read -p "Enter new YNAB API key: " ynab_key
cd ../../security
python3 credential-manager.py store --service weekly-budget --key YNAB_API_KEY --value "$ynab_key"

# Todoist
echo "Rotating Todoist token..."
# Get from Todoist settings
read -p "Enter new Todoist token: " todoist_token
python3 credential-manager.py store --service todoist --key api_token --value "$todoist_token"

echo "Credential rotation complete"
```

### 3. Backup Restoration

```bash
#!/bin/bash
# Restore from backup

BACKUP_DATE=$1
if [[ -z "$BACKUP_DATE" ]]; then
    echo "Usage: $0 <backup-date>"
    exit 1
fi

echo "Restoring from backup: $BACKUP_DATE"

# Restore vault
tar -xzf ~/backups/vault-$BACKUP_DATE.tar.gz -C ~/

# Restore configurations
tar -xzf ~/backups/configs-$BACKUP_DATE.tar.gz -C ~/workspace/

# Verify restoration
cd security
python3 credential-manager.py validate
python3 audit-logger.py verify

echo "Restoration complete"
```

---

## Post-Incident Review

### Within 24 Hours:

1. **Document Timeline**
   - When was incident detected?
   - What were the indicators?
   - Who responded?
   - What actions were taken?

2. **Assess Impact**
   - What systems were affected?
   - Was any data compromised?
   - What was the service downtime?
   - Any financial impact?

3. **Identify Root Cause**
   - Technical vulnerability?
   - Process failure?
   - Human error?
   - External attack?

### Within 1 Week:

1. **Update Security Measures**
   ```bash
   # Update security configurations
   cd security
   ./update-security-configs.sh

   # Run comprehensive audit
   ./security-audit.sh full
   ```

2. **Implement Lessons Learned**
   - Update this document
   - Adjust monitoring thresholds
   - Add new detection rules
   - Update training materials

3. **Test Recovery Procedures**
   ```bash
   # Run incident simulation
   ./simulate-incident.sh <incident-type>
   ```

### Monthly Reviews:

```bash
# Generate monthly security report
cd security
./generate-monthly-report.sh

# Review includes:
# - Incident trends
# - Security metrics
# - Compliance status
# - Improvement recommendations
```

---

## Prevention Checklist

### Daily:
- [ ] Check security monitor dashboard
- [ ] Review critical alerts
- [ ] Verify backup completion

### Weekly:
- [ ] Run security audit
- [ ] Check credential rotation status
- [ ] Review access logs
- [ ] Test one recovery procedure

### Monthly:
- [ ] Full security audit
- [ ] Update security configurations
- [ ] Rotate credentials
- [ ] Security training/review
- [ ] Update this document

---

## Quick Reference Card

### Emergency Commands:

```bash
# STOP ALL OPERATIONS
killall python node claude

# EMERGENCY CREDENTIAL REVOKE
echo "REVOKED" | python3 security/credential-manager.py store --service all --key all --value -

# LOCKDOWN MODE
echo '{"lockdown": true}' > /tmp/emergency-lockdown.json

# BACKUP EVERYTHING NOW
tar -czf emergency-backup-$(date +%Y%m%d-%H%M%S).tar.gz ~/. 2>/dev/null

# CHECK EVERYTHING
cd security && ./security-audit.sh full && ./security-monitor.sh check
```

### Recovery Validation:

```bash
# After any incident, run:
cd security
./post-incident-validation.sh

# This checks:
# ✓ All credentials valid
# ✓ No active threats
# ✓ Logs intact
# ✓ Services operational
# ✓ Monitoring active
```

---

**Document Version:** 1.0
**Last Updated:** 2024-11-24
**Next Review:** 2024-12-24
**Owner:** Terrance Brandon

**Remember:** In any security incident, it's better to over-react than under-react. When in doubt, escalate.