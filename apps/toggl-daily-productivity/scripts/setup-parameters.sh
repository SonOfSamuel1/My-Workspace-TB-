#!/bin/bash
# Setup AWS Secrets Manager for Toggl Daily Productivity Report

set -e

SECRET_NAME="${SECRET_NAME:-toggl-productivity/credentials}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "==================================="
echo "Setup AWS Secrets Manager"
echo "==================================="
echo "Secret: $SECRET_NAME"
echo "Region: $AWS_REGION"
echo ""

# Collect required secrets
if [ -z "$TOGGL_API_TOKEN" ]; then
    echo "Enter your Toggl API token (from track.toggl.com/profile):"
    read TOGGL_API_TOKEN
fi

if [ -z "$TOGGL_WORKSPACE_ID" ]; then
    echo "Enter your Toggl workspace ID:"
    read TOGGL_WORKSPACE_ID
fi

if [ -z "$SES_SENDER_EMAIL" ]; then
    echo "Enter sender email (must be verified in SES):"
    read SES_SENDER_EMAIL
fi

if [ -z "$REPORT_RECIPIENT" ]; then
    echo "Enter recipient email:"
    read REPORT_RECIPIENT
fi

# Create secret JSON
SECRET_STRING=$(cat <<EOF
{
    "TOGGL_API_TOKEN": "$TOGGL_API_TOKEN",
    "TOGGL_WORKSPACE_ID": "$TOGGL_WORKSPACE_ID",
    "SES_SENDER_EMAIL": "$SES_SENDER_EMAIL",
    "REPORT_RECIPIENT": "$REPORT_RECIPIENT",
    "AWS_REGION": "$AWS_REGION"
}
EOF
)

echo "Creating/updating secret..."

# Check if secret exists
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "Updating existing secret..."
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_STRING" \
        --region "$AWS_REGION" \
        --output text
else
    echo "Creating new secret..."
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Credentials for Toggl Daily Productivity Report Lambda" \
        --secret-string "$SECRET_STRING" \
        --region "$AWS_REGION" \
        --output text
fi

echo ""
echo "==================================="
echo "Secret configured successfully!"
echo "==================================="
echo ""
echo "Update your Lambda function environment to use:"
echo "  SECRETS_NAME=$SECRET_NAME"
echo ""
