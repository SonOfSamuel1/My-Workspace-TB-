#!/bin/bash
# Set up EventBridge daily sync rule for Fireflies backfill.
# Runs every day at 9 AM UTC (4 AM EST) to pick up new recordings.
#
# Usage: bash scripts/setup-eventbridge-sync.sh

set -e

FUNCTION_NAME="fireflies-meeting-notes"
RULE_NAME="fireflies-daily-sync"
REGION="us-east-1"

echo "Creating EventBridge rule: $RULE_NAME"
RULE_ARN=$(aws events put-rule \
  --name "$RULE_NAME" \
  --schedule-expression "cron(0 9 * * ? *)" \
  --state ENABLED \
  --region "$REGION" \
  --query "RuleArn" \
  --output text)
echo "Rule ARN: $RULE_ARN"

FUNCTION_ARN=$(aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --query "Configuration.FunctionArn" \
  --output text)
echo "Function ARN: $FUNCTION_ARN"

echo "Adding Lambda permission for EventBridge"
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "AllowEventBridgeDailySync" \
  --action "lambda:InvokeFunction" \
  --principal "events.amazonaws.com" \
  --source-arn "$RULE_ARN" \
  --region "$REGION" 2>/dev/null || echo "(permission already exists)"

echo "Setting Lambda as EventBridge target with daily_sync payload"
aws events put-targets \
  --rule "$RULE_NAME" \
  --targets "[{\"Id\":\"1\",\"Arn\":\"$FUNCTION_ARN\",\"Input\":\"{\\\"action\\\":\\\"daily_sync\\\"}\"}]" \
  --region "$REGION"

echo "Done. EventBridge will trigger daily sync at 9 AM UTC (4 AM EST)."
