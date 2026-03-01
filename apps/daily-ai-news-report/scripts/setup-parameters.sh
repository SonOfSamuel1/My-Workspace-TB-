#!/bin/bash
# Setup AWS Secrets Manager for Daily AI News Report

set -e

SECRET_NAME="${SECRET_NAME:-daily-ai-news/credentials}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "==================================="
echo "Setup AWS Secrets Manager"
echo "==================================="
echo "Secret: $SECRET_NAME"
echo "Region: $AWS_REGION"
echo ""

# Check for required environment variables
if [ -z "$SENDER_EMAIL" ]; then
    echo "Enter sender email (must be verified in SES):"
    read SENDER_EMAIL
fi

if [ -z "$RECIPIENT_EMAIL" ]; then
    echo "Enter recipient email:"
    read RECIPIENT_EMAIL
fi

# Create secret JSON
SECRET_STRING=$(cat <<EOF
{
    "SENDER_EMAIL": "$SENDER_EMAIL",
    "RECIPIENT_EMAIL": "$RECIPIENT_EMAIL",
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
        --description "Credentials for Daily AI News Report Lambda" \
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
