# Todoist Daily Reminders

Automated daily reminder creation for Todoist tasks. Creates reminders at 8am, 11am, 4pm, and 7pm for all tasks that are due today and have the `@commit` label.

## Features

- Fetches tasks due today with `@commit` label
- Creates 4 reminders per task at configurable times (default: 8am, 11am, 4pm, 7pm)
- Clears existing reminders before adding new ones (prevents duplicates)
- Skips reminder times that have already passed
- AWS Lambda deployment for daily automated execution
- Configurable timezone and label

## Requirements

- Python 3.9+
- Todoist Premium subscription (reminders are a premium feature)
- AWS account (for Lambda deployment)

## Local Development

### Setup

1. Create a virtual environment:
   ```bash
   cd apps/todoist-daily-reminders
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   export TODOIST_API_TOKEN="your-todoist-api-token"
   export TODOIST_LABEL="commit"  # Optional, default is "commit"
   export TODOIST_TIMEZONE="America/New_York"  # Optional
   ```

### Running Locally

```bash
cd src
python reminder_main.py
```

## AWS Lambda Deployment

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. AWS Lambda execution role with SSM Parameter Store access

### Parameter Store Setup

Create the following parameters in AWS Systems Manager Parameter Store:

```bash
# Required: Todoist API token (SecureString)
aws ssm put-parameter \
  --name "/todoist-reminders/api-token" \
  --type "SecureString" \
  --value "your-todoist-api-token"

# Optional: Label to filter tasks (String)
aws ssm put-parameter \
  --name "/todoist-reminders/label" \
  --type "String" \
  --value "commit"

# Optional: Timezone (String)
aws ssm put-parameter \
  --name "/todoist-reminders/timezone" \
  --type "String" \
  --value "America/New_York"
```

### Create Lambda Function

1. Package the Lambda function:
   ```bash
   cd apps/todoist-daily-reminders

   # Create deployment package
   mkdir -p package
   pip install -r requirements.txt -t package/
   cp -r src/* package/
   cp lambda_handler.py package/

   cd package
   zip -r ../lambda-deployment.zip .
   cd ..
   ```

2. Create Lambda function via AWS Console or CLI:
   ```bash
   aws lambda create-function \
     --function-name todoist-daily-reminders \
     --runtime python3.9 \
     --handler lambda_handler.daily_reminders_handler \
     --zip-file fileb://lambda-deployment.zip \
     --role arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_LAMBDA_ROLE \
     --timeout 60 \
     --memory-size 256
   ```

### EventBridge Schedule

Create an EventBridge rule to trigger the Lambda daily at 6:00 AM EST:

```bash
# Create the rule
aws events put-rule \
  --name "todoist-daily-reminders-schedule" \
  --schedule-expression "cron(0 11 * * ? *)" \
  --description "Trigger Todoist daily reminders at 6am EST (11am UTC)"

# Add Lambda as target
aws events put-targets \
  --rule "todoist-daily-reminders-schedule" \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:todoist-daily-reminders"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name todoist-daily-reminders \
  --statement-id eventbridge-daily-trigger \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:YOUR_ACCOUNT_ID:rule/todoist-daily-reminders-schedule
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TODOIST_API_TOKEN` | Yes | - | Todoist API token |
| `TODOIST_LABEL` | No | `commit` | Label to filter tasks (without @) |
| `TODOIST_TIMEZONE` | No | `America/New_York` | Timezone for reminders |
| `TODOIST_REMINDER_TIMES` | No | `08:00,11:00,16:00,19:00` | Comma-separated reminder times |

### Custom Reminder Times

To use custom reminder times, set the `TODOIST_REMINDER_TIMES` environment variable:

```bash
export TODOIST_REMINDER_TIMES="09:00,12:00,15:00,18:00"
```

Format: `HH:MM` (24-hour format), comma-separated.

## How It Works

1. **Task Fetching**: Uses Todoist REST API v2 with filter syntax (`today & @commit`) to find matching tasks
2. **Reminder Management**: Uses Todoist Sync API v9 to create/delete reminders (REST API doesn't support reminders)
3. **Duplicate Prevention**: Clears existing reminders for each task before creating new ones
4. **Time Filtering**: Only creates reminders for times that haven't passed yet

## Troubleshooting

### "Reminders not working"
- Ensure you have a Todoist Premium subscription (reminders are a premium feature)
- Check that the API token has the correct permissions

### "No tasks found"
- Verify tasks are actually due today (not just scheduled)
- Confirm the `@commit` label exists and is applied to tasks
- Check the label name matches (case-sensitive)

### "API errors"
- Verify your API token is valid
- Check API rate limits (300 requests per minute)

## API Reference

### Todoist REST API v2
- Used for fetching tasks with filters
- Documentation: https://developer.todoist.com/rest/v2

### Todoist Sync API v9
- Used for reminder management
- Documentation: https://developer.todoist.com/sync/v9

## License

See repository LICENSE file.
