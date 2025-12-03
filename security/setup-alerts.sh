#!/bin/bash

################################################################################
# Alert System Setup Script
# Configures email and SMS credentials for security alerting
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SECURITY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_DIR="${HOME}/.my-workspace-vault"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      SECURITY ALERT SYSTEM CONFIGURATION              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"

################################################################################
# Functions
################################################################################

prompt_secure() {
    local prompt="$1"
    local var_name="$2"

    echo -n "$prompt"
    read -s value
    echo
    eval "$var_name='$value'"
}

setup_gmail() {
    echo -e "\n${BLUE}[1/4] Gmail Configuration${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo "Setting up Gmail for alert notifications..."
    echo "You'll need an App Password (not your regular password)"
    echo "Get one at: https://myaccount.google.com/apppasswords"
    echo

    read -p "Gmail address for sending alerts: " gmail_address
    prompt_secure "Gmail App Password: " gmail_password
    read -p "Recipient email (default: terrance@goodportion.org): " recipient_email
    recipient_email=${recipient_email:-terrance@goodportion.org}

    # Store credentials securely
    cd "$SECURITY_DIR"
    python3 credential-manager.py store \
        --service "alerts" \
        --key "SMTP_USERNAME" \
        --value "$gmail_address" \
        --rotate-days 90

    python3 credential-manager.py store \
        --service "alerts" \
        --key "SMTP_PASSWORD" \
        --value "$gmail_password" \
        --rotate-days 90

    python3 credential-manager.py store \
        --service "alerts" \
        --key "ALERT_EMAIL_FROM" \
        --value "$gmail_address" \
        --rotate-days 180

    python3 credential-manager.py store \
        --service "alerts" \
        --key "ALERT_EMAIL_TO" \
        --value "$recipient_email" \
        --rotate-days 180

    echo -e "${GREEN}✓ Gmail configured${NC}"
}

setup_twilio() {
    echo -e "\n${BLUE}[2/4] Twilio SMS Configuration${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo "Setting up Twilio for SMS alerts..."
    echo "Get your credentials from: https://console.twilio.com"
    echo

    read -p "Enable SMS alerts? (y/n): " enable_sms

    if [[ "$enable_sms" =~ ^[Yy]$ ]]; then
        read -p "Twilio Account SID: " twilio_sid
        prompt_secure "Twilio Auth Token: " twilio_token
        read -p "Twilio Phone Number (e.g., +12025551234): " twilio_from
        read -p "Your Phone Number (default: +14077448449): " escalation_phone
        escalation_phone=${escalation_phone:-+14077448449}

        # Store credentials
        cd "$SECURITY_DIR"
        python3 credential-manager.py store \
            --service "alerts" \
            --key "TWILIO_ACCOUNT_SID" \
            --value "$twilio_sid" \
            --rotate-days 90

        python3 credential-manager.py store \
            --service "alerts" \
            --key "TWILIO_AUTH_TOKEN" \
            --value "$twilio_token" \
            --rotate-days 90

        python3 credential-manager.py store \
            --service "alerts" \
            --key "TWILIO_FROM_NUMBER" \
            --value "$twilio_from" \
            --rotate-days 180

        python3 credential-manager.py store \
            --service "alerts" \
            --key "ESCALATION_PHONE" \
            --value "$escalation_phone" \
            --rotate-days 180

        echo -e "${GREEN}✓ Twilio configured${NC}"
    else
        echo -e "${YELLOW}⚠ SMS alerts disabled${NC}"
    fi
}

setup_aws() {
    echo -e "\n${BLUE}[3/4] AWS CloudWatch Configuration${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo "Setting up AWS CloudWatch integration..."
    echo "You'll need AWS credentials with CloudWatch permissions"
    echo

    read -p "Enable CloudWatch integration? (y/n): " enable_cloudwatch

    if [[ "$enable_cloudwatch" =~ ^[Yy]$ ]]; then
        read -p "AWS Access Key ID: " aws_key_id
        prompt_secure "AWS Secret Access Key: " aws_secret_key
        read -p "AWS Region (default: us-east-1): " aws_region
        aws_region=${aws_region:-us-east-1}

        # Store credentials
        cd "$SECURITY_DIR"
        python3 credential-manager.py store \
            --service "aws" \
            --key "AWS_ACCESS_KEY_ID" \
            --value "$aws_key_id" \
            --rotate-days 90

        python3 credential-manager.py store \
            --service "aws" \
            --key "AWS_SECRET_ACCESS_KEY" \
            --value "$aws_secret_key" \
            --rotate-days 90

        python3 credential-manager.py store \
            --service "aws" \
            --key "AWS_REGION" \
            --value "$aws_region" \
            --rotate-days 365

        echo -e "${GREEN}✓ AWS CloudWatch configured${NC}"

        # Create CloudWatch resources
        echo "Creating CloudWatch resources..."
        python3 cloudwatch-integration.py setup || {
            echo -e "${YELLOW}⚠ CloudWatch setup incomplete. Run manually later.${NC}"
        }
    else
        echo -e "${YELLOW}⚠ CloudWatch integration disabled${NC}"
    fi
}

test_notifications() {
    echo -e "\n${BLUE}[4/4] Testing Notifications${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    read -p "Send test notifications? (y/n): " send_test

    if [[ "$send_test" =~ ^[Yy]$ ]]; then
        echo "Sending test notifications..."

        # Export credentials for testing
        export_credentials

        # Test alerts
        cd "$SECURITY_DIR"
        python3 alert-notifier.py test || {
            echo -e "${RED}✗ Test failed. Check credentials.${NC}"
            return 1
        }

        echo -e "${GREEN}✓ Test notifications sent${NC}"
    fi
}

export_credentials() {
    # Export credentials from vault to environment
    cd "$SECURITY_DIR"

    # Email credentials
    export SMTP_USERNAME=$(python3 credential-manager.py get --service alerts --key SMTP_USERNAME 2>/dev/null || echo "")
    export SMTP_PASSWORD=$(python3 credential-manager.py get --service alerts --key SMTP_PASSWORD 2>/dev/null || echo "")
    export ALERT_EMAIL_FROM=$(python3 credential-manager.py get --service alerts --key ALERT_EMAIL_FROM 2>/dev/null || echo "")
    export ALERT_EMAIL_TO=$(python3 credential-manager.py get --service alerts --key ALERT_EMAIL_TO 2>/dev/null || echo "")

    # SMS credentials
    export TWILIO_ACCOUNT_SID=$(python3 credential-manager.py get --service alerts --key TWILIO_ACCOUNT_SID 2>/dev/null || echo "")
    export TWILIO_AUTH_TOKEN=$(python3 credential-manager.py get --service alerts --key TWILIO_AUTH_TOKEN 2>/dev/null || echo "")
    export TWILIO_FROM_NUMBER=$(python3 credential-manager.py get --service alerts --key TWILIO_FROM_NUMBER 2>/dev/null || echo "")
    export ESCALATION_PHONE=$(python3 credential-manager.py get --service alerts --key ESCALATION_PHONE 2>/dev/null || echo "")

    # AWS credentials
    export AWS_ACCESS_KEY_ID=$(python3 credential-manager.py get --service aws --key AWS_ACCESS_KEY_ID 2>/dev/null || echo "")
    export AWS_SECRET_ACCESS_KEY=$(python3 credential-manager.py get --service aws --key AWS_SECRET_ACCESS_KEY 2>/dev/null || echo "")
    export AWS_REGION=$(python3 credential-manager.py get --service aws --key AWS_REGION 2>/dev/null || echo "")
}

create_env_wrapper() {
    echo -e "\n${BLUE}Creating environment wrapper...${NC}"

    cat > "$SECURITY_DIR/load-alert-env.sh" <<'EOF'
#!/bin/bash
# Load alert credentials into environment
SECURITY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Email credentials
export SMTP_USERNAME=$(python3 "$SECURITY_DIR/credential-manager.py" get --service alerts --key SMTP_USERNAME 2>/dev/null)
export SMTP_PASSWORD=$(python3 "$SECURITY_DIR/credential-manager.py" get --service alerts --key SMTP_PASSWORD 2>/dev/null)
export ALERT_EMAIL_FROM=$(python3 "$SECURITY_DIR/credential-manager.py" get --service alerts --key ALERT_EMAIL_FROM 2>/dev/null)
export ALERT_EMAIL_TO=$(python3 "$SECURITY_DIR/credential-manager.py" get --service alerts --key ALERT_EMAIL_TO 2>/dev/null)

# SMS credentials
export TWILIO_ACCOUNT_SID=$(python3 "$SECURITY_DIR/credential-manager.py" get --service alerts --key TWILIO_ACCOUNT_SID 2>/dev/null)
export TWILIO_AUTH_TOKEN=$(python3 "$SECURITY_DIR/credential-manager.py" get --service alerts --key TWILIO_AUTH_TOKEN 2>/dev/null)
export TWILIO_FROM_NUMBER=$(python3 "$SECURITY_DIR/credential-manager.py" get --service alerts --key TWILIO_FROM_NUMBER 2>/dev/null)
export ESCALATION_PHONE=$(python3 "$SECURITY_DIR/credential-manager.py" get --service alerts --key ESCALATION_PHONE 2>/dev/null)

# AWS credentials
export AWS_ACCESS_KEY_ID=$(python3 "$SECURITY_DIR/credential-manager.py" get --service aws --key AWS_ACCESS_KEY_ID 2>/dev/null)
export AWS_SECRET_ACCESS_KEY=$(python3 "$SECURITY_DIR/credential-manager.py" get --service aws --key AWS_SECRET_ACCESS_KEY 2>/dev/null)
export AWS_REGION=$(python3 "$SECURITY_DIR/credential-manager.py" get --service aws --key AWS_REGION 2>/dev/null)

echo "Alert environment loaded"
EOF

    chmod +x "$SECURITY_DIR/load-alert-env.sh"
    echo -e "${GREEN}✓ Environment wrapper created${NC}"
    echo "Use: source security/load-alert-env.sh"
}

install_dependencies() {
    echo -e "\n${BLUE}Installing Python dependencies...${NC}"

    # Check for required packages
    pip3 install --quiet twilio boto3 2>/dev/null || {
        echo -e "${YELLOW}⚠ Some dependencies may need manual installation${NC}"
    }
}

################################################################################
# Main Setup Flow
################################################################################

main() {
    echo
    echo "This wizard will help you configure:"
    echo "  • Gmail for email alerts"
    echo "  • Twilio for SMS alerts"
    echo "  • AWS CloudWatch integration"
    echo "  • Test notifications"
    echo

    read -p "Continue with setup? (y/n): " proceed
    if [[ ! "$proceed" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled"
        exit 0
    fi

    # Install dependencies
    install_dependencies

    # Configure each service
    setup_gmail
    setup_twilio
    setup_aws

    # Create environment wrapper
    create_env_wrapper

    # Test everything
    test_notifications

    echo
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║        ALERT CONFIGURATION COMPLETE                   ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "Next steps:"
    echo "1. Test individual alerts:"
    echo "   python3 security/alert-notifier.py send --severity HIGH --event TEST --message 'Test alert'"
    echo
    echo "2. Monitor for alerts:"
    echo "   tail -f ~/.my-workspace-vault/alerts/*.jsonl"
    echo
    echo "3. Load credentials for scripts:"
    echo "   source security/load-alert-env.sh"
    echo
    echo -e "${BLUE}Alert system is now ready!${NC}"
}

# Run main
main