# Daily Todoist Reviewer

An AI-powered daily task review system that analyzes your high-priority Todoist tasks and sends you a beautiful email report with suggestions for which tasks Claude can help you complete autonomously.

## Features

- **Daily Task Fetch**: Automatically retrieves high-priority, overdue, and upcoming tasks from Todoist
- **AI Analysis**: Categorizes tasks and identifies which ones can be assisted by AI
- **Smart Suggestions**: Provides specific suggestions for how Claude can help with each task
- **Beautiful Reports**: Generates professional, mobile-responsive HTML email reports
- **Time Savings**: Estimates potential time savings from AI assistance
- **Actionable Insights**: Recommendations for task prioritization and batching

## Quick Start

### 1. Install Dependencies

```bash
cd apps/todoist-daily-reviewer
npm install
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your values
nano .env
```

Required configuration:
- `TODOIST_API_TOKEN` - Your Todoist API token ([get it here](https://todoist.com/prefs/integrations))
- `TODOIST_REVIEW_EMAIL` - Email address for daily reports
- Gmail credentials (see Gmail Setup below)

### 3. Test Locally

```bash
# Preview tasks (no email sent)
node scripts/test-local.js preview

# Generate HTML report and open in browser
node scripts/test-local.js generate

# Validate configuration
node scripts/test-local.js validate

# Send actual email
node scripts/test-local.js send
```

### 4. Deploy to AWS Lambda

```bash
# Setup AWS Parameter Store (first time only)
./scripts/setup-parameters.sh

# Deploy Lambda function
./scripts/deploy.sh
```

## Gmail Setup

This app uses the Gmail API to send emails. You'll need OAuth credentials:

### Option A: Use Existing Gmail MCP Credentials

If you already have the Gmail MCP server configured, you can reuse those credentials:

```bash
# Set paths in .env
GOOGLE_CREDENTIALS_FILE=../../servers/gmail-mcp-server/gcp-oauth.keys.json
GOOGLE_TOKEN_FILE=../../servers/gmail-mcp-server/credentials.json
```

### Option B: Create New Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials JSON file
6. Run the authorization flow to generate a token

## Email Report Sections

The daily email includes:

1. **Quick Summary**
   - Total tasks
   - AI-assistable tasks
   - Potential time savings

2. **AI Can Help With These**
   - Tasks suitable for AI assistance
   - Specific suggestions for each task
   - Action items Claude can perform

3. **High Priority Tasks**
   - Urgent and high-priority items
   - Due dates and project info

4. **Overdue Tasks**
   - Past-due items needing attention

5. **Coming Up This Week**
   - Preview of upcoming tasks

6. **Recommendations**
   - Priority suggestions
   - Task batching opportunities
   - Efficiency tips

## Task Categories

The AI analyzer categorizes tasks into:

| Category | AI Can Help | Examples |
|----------|-------------|----------|
| Research | Yes | "Research competitor pricing" |
| Communication | Yes | "Email vendor about quote" |
| Coding | Yes | "Implement login feature" |
| Writing | Yes | "Draft blog post" |
| Administrative | Yes | "Organize project files" |
| Planning | Yes | "Create Q1 roadmap" |
| Analysis | Yes | "Review monthly metrics" |
| Data Work | Yes | "Update sales spreadsheet" |
| Physical | No | "Go to dentist" |
| Personal | No | "Family dinner" |
| Real-time | No | "Team meeting at 2pm" |

## Configuration Options

Edit `config/reviewer-config.js` to customize:

```javascript
{
  // Schedule
  schedule: {
    timezone: 'America/New_York',
    dailyTime: '05:00',
    skipSaturday: true,  // No report on Saturdays
    skipSunday: false
  },

  // Task filtering
  todoist: {
    filters: {
      priorities: ['p2', 'p3', 'p4'],
      timeframes: ['today', 'overdue', '7 days'],
      excludeLabels: ['waiting', 'someday']
    }
  },

  // AI analysis
  ai: {
    analysisDepth: 'detailed',
    enableTaskSuggestions: true,
    enableTimeEstimation: true
  },

  // Email
  email: {
    subjectTemplate: 'Daily Task Review - {date}',
    theme: 'modern'
  }
}
```

## AWS Lambda Deployment

### Architecture

```
EventBridge (5 AM EST, except Saturdays)
        │
        ▼
   Lambda Function
        │
        ├── Fetch from Todoist API
        ├── Analyze tasks
        ├── Generate HTML report
        └── Send via Gmail API
```

### Required Parameter Store Entries

```
/todoist-daily-reviewer/todoist-api-token
/todoist-daily-reviewer/review-email
/todoist-daily-reviewer/gmail-oauth-credentials (base64)
/todoist-daily-reviewer/gmail-credentials (base64)
```

### Manual Lambda Test

```bash
aws lambda invoke \
  --function-name todoist-daily-reviewer \
  --payload '{}' \
  output.json

cat output.json
```

## File Structure

```
todoist-daily-reviewer/
├── config/
│   └── reviewer-config.js    # Configuration options
├── lambda/
│   ├── Dockerfile            # Lambda container definition
│   └── index.js              # Lambda handler
├── scripts/
│   ├── deploy.sh             # AWS deployment script
│   ├── setup-parameters.sh   # Parameter Store setup
│   └── test-local.js         # Local testing
├── src/
│   ├── index.js              # Main entry point
│   ├── task-fetcher.js       # Todoist API integration
│   ├── ai-analyzer.js        # Task analysis logic
│   ├── report-generator.js   # HTML email generation
│   └── email-sender.js       # Gmail API integration
├── tests/
│   └── (test files)
├── .env.example              # Environment template
├── package.json
└── README.md
```

## Development

### Running Tests

```bash
npm test
```

### Debugging

Enable debug logging:

```bash
DEBUG=true LOG_LEVEL=debug node scripts/test-local.js preview
```

### Modifying the Email Template

Edit `src/report-generator.js` to customize:
- Colors and styling in `getStyles()`
- Section content in `generate*Section()` methods
- Layout in `generateReport()`

## Roadmap

### Phase 1 (Current)
- [x] Task fetching from Todoist
- [x] AI analysis and categorization
- [x] HTML email generation
- [x] Gmail integration
- [x] AWS Lambda deployment

### Phase 2 (Planned)
- [ ] Autonomous task execution
- [ ] Calendar integration
- [ ] Reply-to-email task completion
- [ ] Weekly summary reports

### Phase 3 (Future)
- [ ] Metrics dashboard
- [ ] Custom AI prompts per category
- [ ] Slack/Teams integration
- [ ] Mobile app notifications

## Troubleshooting

### "TODOIST_API_TOKEN is required"
Make sure your `.env` file contains a valid Todoist API token.

### "Gmail credentials not configured"
Set up Gmail OAuth credentials. See Gmail Setup section above.

### "No tasks found"
Check your Todoist filter settings in `config/reviewer-config.js`.

### Lambda timeout
Increase the Lambda timeout in `deploy.sh` (default: 300 seconds).

## License

MIT

## Author

Terrance Brandon
