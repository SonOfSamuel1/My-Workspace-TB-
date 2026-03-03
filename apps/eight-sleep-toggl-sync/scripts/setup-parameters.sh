#!/bin/bash
# Setup AWS SSM Parameters for Eight Sleep -> Toggl Sync

set -e

PREFIX="/eight-sleep-toggl-sync"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "==================================="
echo "Setup SSM Parameters"
echo "==================================="
echo "Prefix: $PREFIX"
echo "Region: $AWS_REGION"
echo ""

put_param() {
    local name="$1" value="$2" type="${3:-SecureString}"
    aws ssm put-parameter \
        --name "$PREFIX/$name" \
        --value "$value" \
        --type "$type" \
        --overwrite \
        --region "$AWS_REGION" \
        --output text > /dev/null
    echo "  Set $PREFIX/$name"
}

if [ -z "$EIGHT_SLEEP_EMAIL" ]; then
    echo "Enter Eight Sleep email:"
    read EIGHT_SLEEP_EMAIL
fi

if [ -z "$EIGHT_SLEEP_PASSWORD" ]; then
    echo "Enter Eight Sleep password:"
    read -s EIGHT_SLEEP_PASSWORD
    echo ""
fi

if [ -z "$TOGGL_API_TOKEN" ]; then
    echo "Enter Toggl API token:"
    read TOGGL_API_TOKEN
fi

if [ -z "$TOGGL_WORKSPACE_ID" ]; then
    echo "Enter Toggl workspace ID:"
    read TOGGL_WORKSPACE_ID
fi

echo "Creating parameters..."
put_param "eight-sleep-email" "$EIGHT_SLEEP_EMAIL"
put_param "eight-sleep-password" "$EIGHT_SLEEP_PASSWORD"
put_param "toggl-api-token" "$TOGGL_API_TOKEN"
put_param "toggl-workspace-id" "$TOGGL_WORKSPACE_ID" "String"

echo ""
echo "==================================="
echo "Parameters configured!"
echo "==================================="
