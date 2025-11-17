# Applications Directory

This directory contains full-featured applications and automation systems.

## Available Applications

### love-brittany-tracker
**Path:** `apps/love-brittany-tracker/`
**Type:** Python automation system
**Purpose:** Automated relationship tracking with bi-weekly HTML email reports

**Key Features:**
- Tracks 9 relationship activity categories
- Generates bi-weekly HTML email reports
- Google Calendar, Docs, and Gmail integration
- Toggl time tracking analytics
- AWS Lambda deployment ready
- Automated scheduling with EventBridge

**Tech Stack:**
- Python 3.x
- Google APIs (Calendar, Docs, Gmail)
- Toggl API
- AWS Lambda, Parameter Store, EventBridge

**Quick Start:**
```bash
cd love-brittany-tracker
python src/relationship_main.py --validate
python src/relationship_main.py --generate
```

**Documentation:**
- [README.md](love-brittany-tracker/README.md) - Main documentation
- [Quick Start Guide](love-brittany-tracker/docs/QUICK_START_RELATIONSHIP.md)
- [AWS Deployment Guide](love-brittany-tracker/AWS_DEPLOYMENT.md)

## Adding New Applications

### Structure Guidelines

When adding a new application to this directory:

1. **Create a dedicated directory:**
   ```
   apps/your-app-name/
   ├── README.md              # Main documentation
   ├── src/                   # Source code
   ├── docs/                  # Additional documentation
   ├── scripts/               # Helper scripts
   ├── requirements.txt       # Python dependencies
   │   or package.json        # Node.js dependencies
   ├── config.yaml/.env       # Configuration
   └── .gitignore            # Ignore patterns
   ```

2. **Include essential documentation:**
   - README.md with quick start
   - Setup/installation guide
   - Configuration instructions
   - Usage examples
   - Troubleshooting section

3. **Follow naming conventions:**
   - Use kebab-case for directory names
   - Be descriptive but concise
   - Consider: `type-purpose-name` pattern

### Application Checklist

Before considering an application complete:

- [ ] README.md with clear description and quick start
- [ ] All dependencies documented
- [ ] Configuration files have examples (.env.example)
- [ ] Sensitive files in .gitignore
- [ ] Setup scripts or wizard (if complex)
- [ ] Basic usage examples
- [ ] Troubleshooting documentation
- [ ] License file (if applicable)

## Development Standards

### Dependencies
- Pin versions in requirements.txt or package.json
- Document minimum required versions
- Include both development and production dependencies

### Configuration
- Use `.env.example` or `config.yaml.example` for templates
- Never commit actual credentials
- Document all configuration options
- Provide sensible defaults where possible

### Documentation
- Keep README.md up to date
- Include inline code comments
- Document API integrations
- Provide setup walkthrough

### Testing
- Include test scripts or commands
- Document how to run tests
- Provide test data examples (sanitized)

## Common Patterns

### Python Applications
```
your-app/
├── src/
│   ├── __init__.py
│   ├── main.py
│   └── services/
├── requirements.txt
├── .env.example
└── README.md
```

### Node.js Applications
```
your-app/
├── src/
│   └── index.ts
├── dist/              # Compiled output
├── package.json
├── tsconfig.json
├── .env.example
└── README.md
```

### AWS Lambda Applications
```
your-app/
├── lambda_handler.py  # Entry point
├── src/               # Application code
├── scripts/           # Deployment scripts
│   ├── deploy-lambda-zip.sh
│   └── setup-parameters.sh
├── requirements.txt
└── Dockerfile.lambda  # Optional container
```

## Integration Points

### Google APIs
Applications using Google services typically need:
- OAuth2 credentials in `credentials/credentials.json`
- Token storage (token.pickle)
- Scopes configuration
- Service account setup (for server apps)

### AWS Services
Lambda-deployed applications require:
- IAM role with appropriate permissions
- Parameter Store for secrets
- EventBridge rules for scheduling
- CloudWatch for logs

### Third-Party APIs
- Store API keys in .env files
- Use environment variables in production
- Document rate limits
- Provide error handling examples

## Deployment

### Local Development
```bash
cd apps/your-app
# Install dependencies
pip install -r requirements.txt
# or
npm install

# Run application
python src/main.py
# or
npm start
```

### AWS Lambda
```bash
cd apps/your-app
# Deploy using deployment script
./scripts/deploy-lambda-zip.sh
```

### Scheduled Execution
- Use AWS EventBridge for Lambda
- Use cron jobs for local deployment
- Document schedule in README

## Troubleshooting

### Common Issues

**Import errors:**
- Verify all dependencies installed
- Check Python path or NODE_PATH
- Ensure virtual environment activated

**Configuration errors:**
- Verify .env file exists
- Check configuration syntax
- Validate required fields present

**API authentication:**
- Refresh OAuth tokens
- Verify API keys valid
- Check API quotas/limits

### Debug Mode

Most applications support verbose logging:
```bash
# Python
python src/main.py --verbose
# or set environment
DEBUG=true python src/main.py
```

## Resources

- [Main Workspace README](../CLAUDE.md)
- [MCP Servers](../servers/CLAUDE.md)
- [Utilities](../utils/CLAUDE.md)
- [Documentation](../docs/)

---

**Directory Purpose:** Full-featured applications and automation systems
**Last Updated:** 2025-11-16
