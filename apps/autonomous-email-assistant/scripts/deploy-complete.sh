#!/bin/bash

# Complete Deployment Script for Email Assistant
# Deploys to AWS Lambda with all features enabled

set -e

echo "🚀 Email Assistant Complete Deployment Script"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-production}
AWS_REGION=${AWS_REGION:-us-east-1}
LAMBDA_NAME="email-assistant-processor-${ENVIRONMENT}"
STACK_NAME="email-assistant-stack-${ENVIRONMENT}"

# Paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="${PROJECT_ROOT}/lambda"
BUILD_DIR="${PROJECT_ROOT}/build"
DIST_FILE="${BUILD_DIR}/lambda-deployment.zip"

echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}AWS Region: ${AWS_REGION}${NC}"
echo -e "${BLUE}Lambda Function: ${LAMBDA_NAME}${NC}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}✗ AWS CLI not found. Please install it first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ AWS CLI found${NC}"

    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}✗ Node.js not found. Please install Node.js 20.x${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Node.js found: $(node -v)${NC}"

    # Check npm
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}✗ npm not found. Please install npm${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ npm found: $(npm -v)${NC}"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}✗ AWS credentials not configured. Run 'aws configure'${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ AWS credentials configured${NC}"

    echo ""
}

# Function to validate environment variables
validate_env() {
    echo -e "${YELLOW}Validating environment variables...${NC}"

    local missing=()

    # Required variables
    [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ] && missing+=("CLAUDE_CODE_OAUTH_TOKEN")
    [ -z "$GMAIL_OAUTH_CREDENTIALS" ] && missing+=("GMAIL_OAUTH_CREDENTIALS")
    [ -z "$GMAIL_CREDENTIALS" ] && missing+=("GMAIL_CREDENTIALS")

    # Optional but recommended
    if [ -z "$AGENT_EMAIL" ]; then
        echo -e "${YELLOW}⚠ AGENT_EMAIL not set (Email Agent will be disabled)${NC}"
    fi

    if [ -z "$OPENROUTER_API_KEY" ]; then
        echo -e "${YELLOW}⚠ OPENROUTER_API_KEY not set (Email Agent will be limited)${NC}"
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${RED}✗ Missing required environment variables:${NC}"
        printf '%s\n' "${missing[@]}"
        echo ""
        echo "Please set these variables before deploying."
        exit 1
    fi

    echo -e "${GREEN}✓ All required environment variables set${NC}"
    echo ""
}

# Function to build Lambda package
build_lambda() {
    echo -e "${YELLOW}Building Lambda deployment package...${NC}"

    # Clean build directory
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"

    # Create temporary directory for Lambda package
    TEMP_DIR=$(mktemp -d)
    echo "Using temp directory: $TEMP_DIR"

    # Copy Lambda handler and lib files
    cp "${LAMBDA_DIR}/index-with-agent.js" "${TEMP_DIR}/index.js"
    cp -r "${PROJECT_ROOT}/lib" "${TEMP_DIR}/"
    cp -r "${PROJECT_ROOT}/config" "${TEMP_DIR}/"
    cp -r "${PROJECT_ROOT}/claude-agents" "${TEMP_DIR}/"

    # Copy package.json and install production dependencies
    cp "${LAMBDA_DIR}/package.json" "${TEMP_DIR}/"
    cp "${PROJECT_ROOT}/package.json" "${TEMP_DIR}/package-root.json"

    cd "$TEMP_DIR"
    echo "Installing dependencies..."
    npm install --production --no-audit --no-fund

    # Also install root dependencies if needed
    if [ -f "package-root.json" ]; then
        npm install --production --no-audit --no-fund axios playwright
    fi

    # Create ZIP file
    echo "Creating ZIP archive..."
    zip -r "$DIST_FILE" . -q

    # Cleanup
    cd "$PROJECT_ROOT"
    rm -rf "$TEMP_DIR"

    # Check file size
    FILE_SIZE=$(du -h "$DIST_FILE" | cut -f1)
    echo -e "${GREEN}✓ Lambda package built: ${DIST_FILE} (${FILE_SIZE})${NC}"

    # Warn if file is too large
    FILE_SIZE_MB=$(du -m "$DIST_FILE" | cut -f1)
    if [ "$FILE_SIZE_MB" -gt 50 ]; then
        echo -e "${YELLOW}⚠ Package size is over 50MB. Consider using Lambda Layers or Container deployment.${NC}"
    fi

    echo ""
}

# Function to deploy CloudFormation stack
deploy_infrastructure() {
    echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"

    TEMPLATE_FILE="${PROJECT_ROOT}/infrastructure/cloudformation-stack.yaml"

    if [ ! -f "$TEMPLATE_FILE" ]; then
        echo -e "${RED}✗ CloudFormation template not found: ${TEMPLATE_FILE}${NC}"
        exit 1
    fi

    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" &> /dev/null; then
        echo "Stack exists, updating..."
        STACK_OPERATION="update-stack"
        WAIT_CONDITION="stack-update-complete"
    else
        echo "Creating new stack..."
        STACK_OPERATION="create-stack"
        WAIT_CONDITION="stack-create-complete"
    fi

    # Deploy stack
    aws cloudformation $STACK_OPERATION \
        --stack-name "$STACK_NAME" \
        --template-body "file://${TEMPLATE_FILE}" \
        --parameters \
            ParameterKey=EnvironmentName,ParameterValue="${ENVIRONMENT}" \
            ParameterKey=AlertEmail,ParameterValue="${ALERT_EMAIL:-terrance@goodportion.org}" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region "$AWS_REGION" || {
            if [ "$STACK_OPERATION" = "update-stack" ]; then
                echo -e "${YELLOW}No updates needed for stack${NC}"
            else
                echo -e "${RED}✗ Failed to deploy CloudFormation stack${NC}"
                exit 1
            fi
        }

    # Wait for stack operation to complete
    if [ "$STACK_OPERATION" != "update-stack" ] || aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query "Stacks[0].StackStatus" --output text | grep -q "UPDATE_IN_PROGRESS"; then
        echo "Waiting for stack operation to complete..."
        aws cloudformation wait "$WAIT_CONDITION" --stack-name "$STACK_NAME" --region "$AWS_REGION" || {
            echo -e "${RED}✗ Stack operation failed${NC}"
            exit 1
        }
    fi

    echo -e "${GREEN}✓ CloudFormation stack deployed${NC}"
    echo ""
}

# Function to update Lambda function code
update_lambda_code() {
    echo -e "${YELLOW}Updating Lambda function code...${NC}"

    aws lambda update-function-code \
        --function-name "$LAMBDA_NAME" \
        --zip-file "fileb://${DIST_FILE}" \
        --region "$AWS_REGION" > /dev/null

    echo -e "${GREEN}✓ Lambda function code updated${NC}"
    echo ""
}

# Function to update Lambda environment variables
update_lambda_env() {
    echo -e "${YELLOW}Updating Lambda environment variables...${NC}"

    # Get stack outputs
    DLQ_URL=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='DLQUrl'].OutputValue" \
        --output text \
        --region "$AWS_REGION")

    STATE_TABLE=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='StateTableName'].OutputValue" \
        --output text \
        --region "$AWS_REGION")

    METRICS_BUCKET=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='MetricsBucket'].OutputValue" \
        --output text \
        --region "$AWS_REGION")

    # Build environment variables JSON
    ENV_VARS=$(cat <<EOF
{
    "Variables": {
        "ENVIRONMENT": "${ENVIRONMENT}",
        "DLQ_URL": "${DLQ_URL}",
        "STATE_TABLE": "${STATE_TABLE}",
        "METRICS_BUCKET": "${METRICS_BUCKET}",
        "CLAUDE_CODE_OAUTH_TOKEN": "${CLAUDE_CODE_OAUTH_TOKEN}",
        "GMAIL_OAUTH_CREDENTIALS": "${GMAIL_OAUTH_CREDENTIALS}",
        "GMAIL_CREDENTIALS": "${GMAIL_CREDENTIALS}",
        "ENABLE_EMAIL_AGENT": "${ENABLE_EMAIL_AGENT:-true}",
        "AGENT_EMAIL": "${AGENT_EMAIL:-assistant@yourdomain.com}",
        "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY:-}",
        "REASONING_MODEL": "${REASONING_MODEL:-deepseek/deepseek-r1}",
        "ESCALATION_PHONE": "${ESCALATION_PHONE:-+14077448449}",
        "DASHBOARD_URL": "${DASHBOARD_URL:-https://email-assistant.yourdomain.com}"
    }
}
EOF
)

    aws lambda update-function-configuration \
        --function-name "$LAMBDA_NAME" \
        --environment "$ENV_VARS" \
        --timeout 600 \
        --memory-size 512 \
        --region "$AWS_REGION" > /dev/null

    # Wait for update to complete
    echo "Waiting for configuration update..."
    aws lambda wait function-updated \
        --function-name "$LAMBDA_NAME" \
        --region "$AWS_REGION"

    echo -e "${GREEN}✓ Lambda environment variables updated${NC}"
    echo ""
}

# Function to test Lambda function
test_lambda() {
    echo -e "${YELLOW}Testing Lambda function...${NC}"

    # Create test event
    TEST_EVENT=$(cat <<EOF
{
    "mode": "test",
    "testMode": true
}
EOF
)

    # Invoke function
    aws lambda invoke \
        --function-name "$LAMBDA_NAME" \
        --payload "$TEST_EVENT" \
        --region "$AWS_REGION" \
        /tmp/lambda-response.json > /dev/null

    # Check response
    if grep -q '"success":true' /tmp/lambda-response.json; then
        echo -e "${GREEN}✓ Lambda test successful${NC}"
        echo "Response:"
        cat /tmp/lambda-response.json | python -m json.tool
    else
        echo -e "${RED}✗ Lambda test failed${NC}"
        echo "Response:"
        cat /tmp/lambda-response.json | python -m json.tool
        exit 1
    fi

    echo ""
}

# Function to display deployment summary
display_summary() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # Get CloudWatch Dashboard URL
    DASHBOARD_URL=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='DashboardURL'].OutputValue" \
        --output text \
        --region "$AWS_REGION")

    echo -e "${BLUE}Lambda Function:${NC} ${LAMBDA_NAME}"
    echo -e "${BLUE}Environment:${NC} ${ENVIRONMENT}"
    echo -e "${BLUE}Region:${NC} ${AWS_REGION}"
    echo -e "${BLUE}CloudWatch Dashboard:${NC} ${DASHBOARD_URL}"
    echo ""

    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Verify the EventBridge schedule is enabled"
    echo "2. Check CloudWatch Logs for execution logs"
    echo "3. Monitor the Dead Letter Queue for failures"
    echo "4. Configure SNS email subscription for alerts"
    echo "5. Test email processing with a manual trigger"
    echo ""

    echo -e "${YELLOW}Manual Test Command:${NC}"
    echo "aws lambda invoke --function-name ${LAMBDA_NAME} --payload '{\"mode\":\"morning_brief\"}' response.json"
    echo ""

    echo -e "${YELLOW}View Logs:${NC}"
    echo "aws logs tail /aws/lambda/${LAMBDA_NAME} --follow"
    echo ""
}

# Function to create SSM parameters for secrets
create_ssm_parameters() {
    echo -e "${YELLOW}Creating SSM parameters for secrets...${NC}"

    # Create parameters with SecureString type
    aws ssm put-parameter \
        --name "/email-assistant/${ENVIRONMENT}/claude-token" \
        --value "$CLAUDE_CODE_OAUTH_TOKEN" \
        --type SecureString \
        --overwrite \
        --region "$AWS_REGION" > /dev/null || true

    aws ssm put-parameter \
        --name "/email-assistant/${ENVIRONMENT}/gmail-oauth" \
        --value "$GMAIL_OAUTH_CREDENTIALS" \
        --type SecureString \
        --overwrite \
        --region "$AWS_REGION" > /dev/null || true

    aws ssm put-parameter \
        --name "/email-assistant/${ENVIRONMENT}/gmail-creds" \
        --value "$GMAIL_CREDENTIALS" \
        --type SecureString \
        --overwrite \
        --region "$AWS_REGION" > /dev/null || true

    if [ -n "$OPENROUTER_API_KEY" ]; then
        aws ssm put-parameter \
            --name "/email-assistant/${ENVIRONMENT}/openrouter-key" \
            --value "$OPENROUTER_API_KEY" \
            --type SecureString \
            --overwrite \
            --region "$AWS_REGION" > /dev/null || true
    fi

    echo -e "${GREEN}✓ SSM parameters created${NC}"
    echo ""
}

# Main deployment flow
main() {
    echo "Starting deployment process..."
    echo ""

    # Run all deployment steps
    check_prerequisites
    validate_env
    build_lambda
    deploy_infrastructure
    update_lambda_code
    create_ssm_parameters
    update_lambda_env
    test_lambda
    display_summary
}

# Handle errors
trap 'echo -e "${RED}Deployment failed!${NC}"' ERR

# Run main function
main "$@"