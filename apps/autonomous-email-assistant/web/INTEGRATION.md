# Integration Guide

This guide explains how to integrate the web application with the parent CLI email processing system.

## Overview

The web app provides a REST API endpoint that allows the CLI email processing system to sync results to the database for visualization and management.

## API Endpoints

### POST /api/integration/sync

Sync processed emails to the web application.

**Authentication**: API key in `X-API-Key` header

**Request Body**:
```json
{
  "agentEmail": "assistant@yourdomain.com",
  "emails": [
    {
      "gmailId": "gmail-msg-123",
      "gmailThreadId": "gmail-thread-456",
      "subject": "Meeting Request",
      "from": "client@example.com",
      "to": "assistant@yourdomain.com",
      "snippet": "Can we schedule a meeting?",
      "body": "Full email body...",
      "tier": 3,
      "reasoning": "Meeting request - draft for approval",
      "confidence": 0.85,
      "status": "pending_approval",
      "receivedAt": "2025-11-09T12:00:00Z",
      "processedAt": "2025-11-09T12:01:00Z",
      "actions": [
        {
          "type": "draft_created",
          "data": { "responseText": "..." },
          "requiresApproval": true,
          "status": "pending"
        }
      ]
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "synced": 1,
  "agentId": "agent-id-123"
}
```

### GET /api/integration/sync?agentEmail=...

Get agent configuration by email.

**Authentication**: API key in `X-API-Key` header

**Response**:
```json
{
  "id": "agent-id-123",
  "name": "Executive Assistant",
  "agentEmail": "assistant@yourdomain.com",
  "enabled": true,
  "config": {
    "timezone": "America/New_York",
    "businessHours": { "start": 9, "end": 17 },
    "communicationStyle": "professional",
    "offLimitsContacts": ["boss@company.com"]
  },
  "lastRunAt": "2025-11-09T12:00:00Z",
  "stats": {
    "totalEmails": 150,
    "totalActions": 200
  }
}
```

## Setup

### 1. Generate API Key

Generate a secure API key:

```bash
openssl rand -base64 32
```

### 2. Configure Web App

Add to `.env`:

```bash
INTEGRATION_API_KEY="your-generated-api-key"
```

### 3. Configure CLI Project

In the parent project's `.env`:

```bash
WEB_APP_URL="http://localhost:3000"
INTEGRATION_API_KEY="your-generated-api-key"
```

## Integration from CLI

### Method 1: Use Integration Helper

Copy `integration-example.js` to your project:

```javascript
const { syncEmailsToWebApp } = require('./web/integration-example.js');

// After processing emails
await syncEmailsToWebApp({
  agentEmail: 'assistant@yourdomain.com',
  emails: processedEmails
});
```

### Method 2: Direct API Call

```javascript
const fetch = require('node-fetch');

async function syncEmails(processedEmails) {
  const response = await fetch('http://localhost:3000/api/integration/sync', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': process.env.INTEGRATION_API_KEY,
    },
    body: JSON.stringify({
      agentEmail: 'assistant@yourdomain.com',
      emails: processedEmails,
    }),
  });

  return response.json();
}
```

## Data Format

### Email Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| gmailId | string | Yes | Gmail message ID |
| gmailThreadId | string | No | Gmail thread ID |
| subject | string | Yes | Email subject |
| from | string | Yes | Sender email |
| to | string | No | Recipient email |
| snippet | string | No | Email preview text |
| body | string | No | Full email body |
| tier | number (1-4) | Yes | Classification tier |
| reasoning | string | Yes | Agent's reasoning |
| confidence | number (0-1) | No | Confidence score |
| status | string | Yes | `processed`, `pending_approval`, `escalated`, `flagged` |
| receivedAt | ISO string | Yes | When email was received |
| processedAt | ISO string | No | When email was processed |
| actions | array | No | Actions taken by agent |

### Action Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | `response_sent`, `draft_created`, `sms_sent`, `tool_executed` |
| data | object | Yes | Action-specific data |
| requiresApproval | boolean | No | Whether action needs approval |
| toolName | string | No | Tool used (e.g., `playwright`) |
| toolInput | object | No | Tool input parameters |
| toolOutput | object | No | Tool output results |
| status | string | No | `pending`, `completed`, `failed` |

## Integration Workflow

### GitHub Actions Integration

Update `.github/workflows/hourly-email-management.yml`:

```yaml
- name: Process Emails
  run: node process-emails.js
  env:
    CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    WEB_APP_URL: https://your-app.vercel.app
    INTEGRATION_API_KEY: ${{ secrets.INTEGRATION_API_KEY }}
```

Add to GitHub secrets:
- `INTEGRATION_API_KEY`

### Lambda Integration

Update Lambda function environment variables:
- `WEB_APP_URL`: Your deployed web app URL
- `INTEGRATION_API_KEY`: Same API key as web app

## Error Handling

The integration is designed to be fault-tolerant:

- If sync fails, the CLI continues to work normally
- Sync errors are logged but don't block email processing
- Duplicate emails (same gmailId) are updated instead of creating duplicates

## Production Deployment

### Security Checklist

- [ ] Use HTTPS for WEB_APP_URL in production
- [ ] Rotate API keys regularly
- [ ] Add rate limiting to the sync endpoint
- [ ] Monitor sync endpoint for suspicious activity
- [ ] Consider IP whitelisting for GitHub Actions/Lambda

### Scaling Considerations

For high volume (>1000 emails/hour):

1. **Batch syncing**: Sync in batches of 50-100 emails
2. **Async processing**: Use a queue (Redis, SQS) for sync jobs
3. **Database indexing**: Ensure indexes on `gmailId` and `agentId`
4. **Caching**: Cache agent configs to reduce DB reads

## Monitoring

Track sync health:

```sql
-- Recent syncs
SELECT agentId, lastRunAt, COUNT(*) as email_count
FROM Email
WHERE processedAt > NOW() - INTERVAL '1 hour'
GROUP BY agentId, lastRunAt;

-- Failed actions
SELECT type, status, COUNT(*)
FROM AgentAction
WHERE status = 'failed'
  AND createdAt > NOW() - INTERVAL '24 hours'
GROUP BY type, status;
```

## Troubleshooting

### "Unauthorized" Error

- Check `INTEGRATION_API_KEY` matches in both web app and CLI
- Ensure API key is passed in `X-API-Key` header

### "Agent not found" Error

- Verify agent exists in web app with matching `agentEmail`
- Check spelling of agent email address
- Create agent in web app first before syncing

### Sync Timeout

- Reduce batch size (sync fewer emails per request)
- Check database connection pool settings
- Verify network connectivity between CLI and web app

### Duplicate Emails

- Ensure `gmailId` is unique per email
- Check that update logic is working (existing emails should be updated)

## Advanced: Webhook Integration (Future)

For real-time bidirectional sync, consider webhooks:

```javascript
// Web app sends webhook when draft is approved
POST https://your-cli-endpoint.com/webhook/draft-approved
{
  "emailId": "...",
  "responseText": "...",
  "approvedBy": "user@example.com"
}
```

## Support

For issues with integration:
1. Check logs in both CLI and web app
2. Verify API key configuration
3. Test endpoint with curl/Postman
4. Open an issue on GitHub with error details
