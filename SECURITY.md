# Security Policy

## Supported Versions

This is a personal development monorepo with active development. Security updates are applied to all active projects.

| Project | Version | Supported |
|---------|---------|-----------|
| MCP Servers | 1.0.x | ✅ |
| Love Brittany Tracker | 1.0.x | ✅ |
| Utilities | Latest | ✅ |

## Reporting a Vulnerability

### How to Report

If you discover a security vulnerability, please follow these steps:

1. **DO NOT** open a public issue
2. **DO NOT** commit fixes to public repositories
3. **DO** report privately via one of these methods:
   - Email: [Create issue and request private disclosure]
   - GitHub Security Advisories: Use the "Report a vulnerability" button in the Security tab

### What to Include

Please include the following information in your report:

- **Description**: Clear description of the vulnerability
- **Impact**: What could an attacker accomplish?
- **Reproduction**: Step-by-step instructions to reproduce
- **Affected Components**: Which projects/files are affected
- **Suggested Fix**: If you have ideas for remediation
- **Disclosure Timeline**: When you plan to disclose publicly (if applicable)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - **Critical**: 24-48 hours
  - **High**: 7 days
  - **Medium**: 30 days
  - **Low**: 90 days

## Security Best Practices

### Credentials and Secrets

#### Never Commit

- ❌ `.env` files
- ❌ API keys or tokens
- ❌ OAuth credentials
- ❌ Private keys (`.pem`, `.key`)
- ❌ Passwords or sensitive configuration
- ❌ AWS credentials

#### Always Use

- ✅ `.env.example` files (with placeholder values)
- ✅ Environment variables for sensitive data
- ✅ AWS Parameter Store for cloud deployments
- ✅ `.gitignore` patterns for credential files

### API Keys and Tokens

#### Storage Locations

**Local Development:**
- MCP Servers: Environment variables in `.env` files
- Python Apps: `.env` files or `config.yaml` (gitignored)
- Gmail: `~/.gmail-mcp-credentials.json` and `~/.gmail-mcp-token.json`

**Production/Cloud:**
- AWS: Use AWS Parameter Store
- Render: Use environment variables in dashboard
- Docker: Use secrets management

#### Rotation Policy

- **API Keys**: Rotate every 90 days
- **OAuth Tokens**: Refresh automatically when possible
- **Access Tokens**: Use shortest expiration practical

### Dependency Management

#### Automated Scanning

- **Renovate Bot**: Automated dependency updates (configured in `renovate.json`)
- **GitHub Dependabot**: Security alerts enabled
- **npm audit**: Runs in CI/CD pipelines
- **Safety**: Python dependency scanning

#### Manual Checks

```bash
# Check npm dependencies
cd servers/<server-name>
npm audit

# Check Python dependencies
cd apps/<app-name>
pip install safety
safety check -r requirements.txt
```

### Code Security

#### Pre-commit Hooks

Automatically check for:
- Exposed secrets (via detect-secrets)
- Security issues (via bandit for Python)
- Large files that might contain credentials

#### Manual Security Review

Before committing:
1. Search for hardcoded credentials
2. Validate input sanitization
3. Check for SQL injection vulnerabilities
4. Verify API endpoint authentication
5. Review error messages (don't expose internals)

### API Security

#### Authentication

- **Google APIs**: OAuth 2.0 with refresh tokens
- **Todoist API**: Personal access tokens
- **YNAB API**: Personal access tokens
- **Never** share tokens between environments

#### Rate Limiting

- Implement exponential backoff
- Respect API rate limits
- Cache responses when appropriate
- Monitor usage quotas

#### Input Validation

```python
# Example: Validate user input
def create_task(title: str):
    # Sanitize input
    if not title or len(title) > 500:
        raise ValueError("Invalid title")

    # Escape special characters
    safe_title = html.escape(title)

    # Use parameterized queries
    return api.create_task(safe_title)
```

### Infrastructure Security

#### AWS Lambda

- Use least privilege IAM roles
- Enable AWS WAF for public endpoints
- Encrypt environment variables
- Enable CloudWatch logging
- Regular security group audits

#### Environment Variables

```bash
# Good: Use environment variables
YNAB_API_KEY="${env:YNAB_API_KEY}"

# Bad: Hardcode credentials
YNAB_API_KEY="abc123..."
```

### Network Security

#### HTTPS Only

- All external API calls use HTTPS
- No HTTP fallbacks
- Validate SSL certificates

#### Webhook Security

- Validate webhook signatures
- Use HTTPS endpoints only
- Implement rate limiting
- Log all webhook events

## Known Security Considerations

### Google OAuth

- **Tokens**: Stored locally in `~/.gmail-mcp-token.json`
- **Risk**: Local file access = account access
- **Mitigation**: File permissions (600), regular rotation

### API Token Storage

- **Location**: `.env` files and environment variables
- **Risk**: File system access = API access
- **Mitigation**: `.gitignore`, file permissions, rotation

### MCP Server Access

- **Risk**: MCP servers run with user's credentials
- **Mitigation**: Only grant necessary scopes, audit tool calls

## Security Tooling

### Installed Tools

- **detect-secrets**: Pre-commit hook for secret scanning
- **bandit**: Python security linter
- **npm audit**: Node.js dependency scanner
- **safety**: Python dependency scanner
- **TruffleHog**: Git history secret scanning (CI/CD)
- **CodeQL**: Static analysis (GitHub Actions)

### Running Security Scans

```bash
# Scan for secrets
pre-commit run detect-secrets --all-files

# Python security check
bandit -r apps/ utils/

# Dependency checks
npm audit --audit-level=high
safety check -r requirements.txt

# Git history scan
docker run -v $(pwd):/repo trufflesecurity/trufflehog:latest filesystem /repo
```

## Incident Response

### If Credentials Are Exposed

1. **Immediately revoke** the exposed credentials
2. **Generate new** credentials
3. **Update** all systems using the old credentials
4. **Audit** recent API activity for suspicious behavior
5. **Document** the incident and lessons learned

### If Vulnerability Discovered

1. **Assess severity** (Critical/High/Medium/Low)
2. **Create private branch** for fix
3. **Develop and test** patch
4. **Deploy** to production
5. **Document** in CHANGELOG.md
6. **Notify** affected users (if applicable)

## Compliance

### Data Handling

- **Personal Data**: Minimize collection, encrypt at rest
- **API Data**: Follow provider terms of service
- **Logs**: Don't log sensitive information
- **Retention**: Delete data when no longer needed

### Third-Party Services

- Google APIs: [Privacy Policy](https://policies.google.com/privacy)
- Todoist: [Privacy Policy](https://todoist.com/privacy)
- YNAB: [Privacy Policy](https://www.ynab.com/privacy-policy)

## Security Checklist

Before deploying:

- [ ] No hardcoded credentials
- [ ] All secrets in environment variables
- [ ] `.env` files in `.gitignore`
- [ ] Dependencies up to date
- [ ] Security scans passing
- [ ] HTTPS only for external calls
- [ ] Input validation implemented
- [ ] Error messages sanitized
- [ ] Logging excludes sensitive data
- [ ] Access controls verified
- [ ] Documentation updated

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Node.js Security Best Practices](https://nodejs.org/en/docs/guides/security/)
- [Python Security](https://python.readthedocs.io/en/latest/library/security_warnings.html)

## Contact

For security-related questions: Create a private security advisory on GitHub.

---

**Last Updated**: 2025-11-17
