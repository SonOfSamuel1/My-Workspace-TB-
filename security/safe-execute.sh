#!/bin/bash

################################################################################
# Safe Execution Wrapper for My Workspace
#
# This script provides a secure environment for running applications with
# the --dangerously-skip-permissions flag by implementing multiple security
# layers and validation checks.
#
# Usage: ./safe-execute.sh <app-name> [options]
################################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECURITY_DIR="${WORKSPACE_ROOT}/security"
VAULT_DIR="${HOME}/.my-workspace-vault"
LOG_DIR="${WORKSPACE_ROOT}/logs/security"
AUDIT_LOG="${LOG_DIR}/audit.log"

# Create necessary directories
mkdir -p "${LOG_DIR}"
mkdir -p "${VAULT_DIR}"

# Set secure permissions on directories
chmod 700 "${VAULT_DIR}" 2>/dev/null || true
chmod 700 "${LOG_DIR}" 2>/dev/null || true

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1" >> "${AUDIT_LOG}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >> "${AUDIT_LOG}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "${AUDIT_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "${AUDIT_LOG}"
}

################################################################################
# Security Validation Functions
################################################################################

check_file_permissions() {
    local file="$1"
    local expected="$2"

    if [[ -e "$file" ]]; then
        local perms=$(stat -f "%OLp" "$file" 2>/dev/null || stat -c "%a" "$file" 2>/dev/null)
        if [[ "$perms" != "$expected" ]]; then
            log_warning "Insecure permissions on $file: $perms (expected $expected)"
            chmod "$expected" "$file"
            log_success "Fixed permissions on $file"
        else
            log_info "Permissions OK for $file"
        fi
    fi
}

validate_credentials() {
    log_info "Validating credential security..."

    # Check credential manager
    if [[ -f "${SECURITY_DIR}/credential-manager.py" ]]; then
        python3 "${SECURITY_DIR}/credential-manager.py" validate --vault-path "${VAULT_DIR}" || {
            log_error "Credential validation failed"
            return 1
        }
    fi

    # Check for .env files (should not exist after migration)
    local env_files=$(find "${WORKSPACE_ROOT}" -name ".env" -type f 2>/dev/null | grep -v ".env.example" | grep -v ".env.backup" || true)
    if [[ -n "$env_files" ]]; then
        log_warning "Found unsecured .env files:"
        echo "$env_files"
        read -p "Migrate these to secure storage? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            migrate_env_files
        fi
    fi

    # Validate AWS credentials if present
    if [[ -n "${AWS_PROFILE:-}" ]]; then
        log_info "Using AWS Profile: ${AWS_PROFILE}"
    fi

    log_success "Credential validation complete"
}

migrate_env_files() {
    log_info "Migrating .env files to secure storage..."

    # Find all .env files
    find "${WORKSPACE_ROOT}" -name ".env" -type f | while read -r env_file; do
        # Determine service name from path
        local service=$(basename "$(dirname "$env_file")")

        log_info "Migrating $env_file for service: $service"

        # Use credential manager to migrate
        if [[ -f "${SECURITY_DIR}/credential-manager.py" ]]; then
            python3 "${SECURITY_DIR}/credential-manager.py" migrate \
                --env-file "$env_file" \
                --service "$service" \
                --vault-path "${VAULT_DIR}"
        fi
    done

    log_success "Migration complete"
}

################################################################################
# Rate Limiting Implementation
################################################################################

check_rate_limits() {
    local app="$1"
    local rate_file="${LOG_DIR}/.rate_limits_${app}"
    local current_time=$(date +%s)

    # Initialize rate limit tracking
    if [[ ! -f "$rate_file" ]]; then
        echo "{}" > "$rate_file"
        chmod 600 "$rate_file"
    fi

    # Check email rate limit (10 per hour)
    local email_count=$(grep "EMAIL_SENT" "${AUDIT_LOG}" 2>/dev/null | tail -3600 | wc -l || echo 0)
    if [[ $email_count -ge 10 ]]; then
        log_warning "Email rate limit approaching (${email_count}/10 per hour)"
    fi

    # Check SMS rate limit (1 per 5 minutes)
    # For macOS compatibility, use different date calculation
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local five_min_ago=$(date -v-5M '+%Y-%m-%d %H:%M')
    else
        local five_min_ago=$(date -d '5 minutes ago' '+%Y-%m-%d %H:%M')
    fi
    local sms_recent=$(grep "SMS_SENT" "${AUDIT_LOG}" 2>/dev/null | tail -1 | grep -E "$five_min_ago" || true)
    if [[ -n "$sms_recent" ]]; then
        log_error "SMS rate limit: Must wait 5 minutes between SMS messages"
        return 1
    fi

    log_info "Rate limits OK"
}

################################################################################
# Application-Specific Security
################################################################################

setup_email_assistant_security() {
    log_info "Setting up Autonomous Email Assistant security..."

    # Create classification rules file
    cat > "${WORKSPACE_ROOT}/apps/autonomous-email-assistant/security-config.json" <<EOF
{
  "email_classification": {
    "tier_1_confidence_threshold": 0.95,
    "tier_2_confidence_threshold": 0.9,
    "tier_3_auto_draft": true,
    "off_limits_contacts": [
      "darrell.coleman@example.com",
      "paul.robertson@example.com",
      "tatyana.brandon@example.com"
    ]
  },
  "rate_limits": {
    "emails_per_hour": 10,
    "sms_per_5_minutes": 1,
    "api_calls_per_minute": 30
  },
  "audit": {
    "log_all_sends": true,
    "log_all_classifications": true,
    "store_drafts": true
  }
}
EOF
    chmod 600 "${WORKSPACE_ROOT}/apps/autonomous-email-assistant/security-config.json"

    log_success "Email Assistant security configured"
}

setup_budget_report_security() {
    log_info "Setting up Weekly Budget Report security..."

    # Create read-only YNAB configuration
    cat > "${WORKSPACE_ROOT}/apps/weekly-budget-report/security-config.json" <<EOF
{
  "ynab": {
    "read_only": true,
    "allowed_operations": ["GET"],
    "blocked_operations": ["POST", "PUT", "PATCH", "DELETE"]
  },
  "email": {
    "allowed_recipients": ["terrance@goodportion.org"],
    "require_encryption": false
  },
  "rate_limits": {
    "reports_per_day": 1,
    "api_calls_per_hour": 100
  }
}
EOF
    chmod 600 "${WORKSPACE_ROOT}/apps/weekly-budget-report/security-config.json"

    log_success "Budget Report security configured"
}

setup_love_tracker_security() {
    log_info "Setting up Love Tracker security..."

    # Create document whitelist
    cat > "${WORKSPACE_ROOT}/apps/love-brittany-tracker/security-config.json" <<EOF
{
  "google_docs": {
    "allowed_document_ids": [],
    "allowed_calendar_ids": [],
    "read_only_mode": false
  },
  "email": {
    "allowed_recipients": ["terrance@goodportion.org"],
    "sanitize_content": true
  },
  "rate_limits": {
    "reports_per_week": 2,
    "api_calls_per_hour": 50
  }
}
EOF
    chmod 600 "${WORKSPACE_ROOT}/apps/love-brittany-tracker/security-config.json"

    # Copy for Kaelin tracker
    cp "${WORKSPACE_ROOT}/apps/love-brittany-tracker/security-config.json" \
       "${WORKSPACE_ROOT}/apps/love-kaelin-tracker/security-config.json"
    chmod 600 "${WORKSPACE_ROOT}/apps/love-kaelin-tracker/security-config.json"

    log_success "Love Tracker security configured"
}

################################################################################
# MCP Server Security
################################################################################

setup_mcp_security() {
    log_info "Setting up MCP server security..."

    # Create secure MCP configuration
    local mcp_config="${HOME}/.config/claude/claude_code_config.json"

    if [[ -f "${SECURITY_DIR}/credential-manager.js" ]]; then
        node "${SECURITY_DIR}/credential-manager.js" setup-mcp gmail,todoist,ynab
    fi

    # Set proper permissions
    if [[ -f "$mcp_config" ]]; then
        chmod 600 "$mcp_config"
        log_success "MCP configuration secured"
    fi
}

################################################################################
# Environment Setup
################################################################################

setup_secure_environment() {
    local app="$1"

    log_info "Setting up secure environment for $app..."

    # Load credentials from secure storage
    if [[ -f "${SECURITY_DIR}/credential-manager.py" ]]; then
        # Export credentials as environment variables
        while IFS= read -r line; do
            export "$line"
        done < <(python3 "${SECURITY_DIR}/credential-manager.py" export-env --service "$app" 2>/dev/null || true)
    fi

    # Set security environment variables
    export SECURITY_MODE="enforced"
    export AUDIT_ENABLED="true"
    export RATE_LIMITING="enabled"
    export CREDENTIAL_VAULT="${VAULT_DIR}"

    # Set process limits
    ulimit -n 1024  # Max open files
    ulimit -u 512   # Max processes

    log_success "Secure environment configured"
}

################################################################################
# Pre-flight Checks
################################################################################

run_preflight_checks() {
    local app="$1"

    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   SECURITY PRE-FLIGHT CHECKS FOR: ${app}${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

    # 1. Validate credentials
    validate_credentials || return 1

    # 2. Check rate limits
    check_rate_limits "$app" || return 1

    # 3. Validate file permissions
    log_info "Checking file permissions..."
    check_file_permissions "${VAULT_DIR}" "700"
    check_file_permissions "${LOG_DIR}" "700"
    check_file_permissions "${AUDIT_LOG}" "600"

    # 4. Setup application-specific security
    case "$app" in
        "autonomous-email-assistant")
            setup_email_assistant_security
            ;;
        "weekly-budget-report")
            setup_budget_report_security
            ;;
        "love-brittany-tracker"|"love-kaelin-tracker")
            setup_love_tracker_security
            ;;
    esac

    # 5. Setup MCP security if needed
    if [[ "$app" == "autonomous-email-assistant" ]]; then
        setup_mcp_security
    fi

    echo -e "\n${GREEN}✓ All pre-flight checks passed${NC}\n"
    return 0
}

################################################################################
# Execution Wrapper
################################################################################

execute_with_monitoring() {
    local app="$1"
    shift  # Remove app name from arguments

    local app_dir="${WORKSPACE_ROOT}/apps/${app}"

    if [[ ! -d "$app_dir" ]]; then
        log_error "Application not found: $app"
        exit 1
    fi

    # Change to app directory
    cd "$app_dir"

    # Determine execution command based on app
    local exec_cmd=""

    if [[ -f "lambda_handler.py" ]]; then
        exec_cmd="python3 lambda_handler.py"
    elif [[ -f "src/${app%%-*}_main.py" ]]; then
        exec_cmd="python3 src/${app%%-*}_main.py"
    elif [[ -f "index.js" ]]; then
        exec_cmd="node index.js"
    elif [[ -f "lambda/index.js" ]]; then
        exec_cmd="node lambda/index.js"
    else
        log_error "No executable found for $app"
        exit 1
    fi

    # Add monitoring wrapper
    log_info "Executing: $exec_cmd $*"
    log_info "With security monitoring enabled"

    # Create monitoring process
    (
        while true; do
            # Monitor for suspicious activity
            if grep -q "SECURITY_VIOLATION" "${AUDIT_LOG}" 2>/dev/null; then
                log_error "Security violation detected - terminating"
                kill $$ 2>/dev/null
            fi
            sleep 1
        done
    ) &
    local monitor_pid=$!

    # Execute the command
    local exit_code=0
    if $exec_cmd "$@"; then
        log_success "Execution completed successfully"
    else
        exit_code=$?
        log_error "Execution failed with code: $exit_code"
    fi

    # Clean up monitor
    kill $monitor_pid 2>/dev/null || true

    return $exit_code
}

################################################################################
# Post-execution Cleanup
################################################################################

cleanup_after_execution() {
    log_info "Running post-execution cleanup..."

    # Clear temporary credentials
    if [[ -d "/tmp/.gmail-mcp" ]]; then
        rm -rf "/tmp/.gmail-mcp"
        log_info "Cleaned up temporary Gmail credentials"
    fi

    if [[ -d "/tmp/.config/claude" ]]; then
        rm -rf "/tmp/.config/claude"
        log_info "Cleaned up temporary Claude config"
    fi

    # Archive logs if they're too large
    if [[ -f "${AUDIT_LOG}" ]]; then
        local log_size=$(du -k "${AUDIT_LOG}" | cut -f1)
        if [[ $log_size -gt 10240 ]]; then  # 10MB
            local archive="${LOG_DIR}/audit.$(date +%Y%m%d_%H%M%S).log.gz"
            gzip -c "${AUDIT_LOG}" > "$archive"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log rotated" > "${AUDIT_LOG}"
            chmod 600 "$archive"
            log_info "Archived audit log to $archive"
        fi
    fi

    # Report statistics
    local email_count=$(grep -c "EMAIL_SENT" "${AUDIT_LOG}" 2>/dev/null || echo 0)
    local api_count=$(grep -c "API_CALL" "${AUDIT_LOG}" 2>/dev/null || echo 0)

    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   EXECUTION STATISTICS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "  Emails sent:    $email_count"
    echo -e "  API calls made: $api_count"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

    log_success "Cleanup complete"
}

################################################################################
# Main Execution
################################################################################

main() {
    # Check for help
    if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        echo "Usage: $0 <app-name> [options]"
        echo ""
        echo "Available apps:"
        echo "  autonomous-email-assistant"
        echo "  weekly-budget-report"
        echo "  love-brittany-tracker"
        echo "  love-kaelin-tracker"
        echo ""
        echo "Options:"
        echo "  --skip-preflight    Skip pre-flight security checks"
        echo "  --dry-run          Run checks but don't execute"
        echo "  --migrate-env      Migrate .env files to secure storage"
        echo ""
        exit 0
    fi

    local app="$1"
    shift

    # Handle special flags
    local skip_preflight=false
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-preflight)
                skip_preflight=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --migrate-env)
                migrate_env_files
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done

    # Start execution
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     SECURE EXECUTION WRAPPER FOR MY WORKSPACE         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"

    # Run pre-flight checks unless skipped
    if [[ "$skip_preflight" != true ]]; then
        if ! run_preflight_checks "$app"; then
            log_error "Pre-flight checks failed. Use --skip-preflight to override (not recommended)"
            exit 1
        fi
    fi

    # Setup secure environment
    setup_secure_environment "$app"

    # Execute if not dry run
    if [[ "$dry_run" != true ]]; then
        # Trap cleanup on exit
        trap cleanup_after_execution EXIT

        # Execute with monitoring
        execute_with_monitoring "$app" "$@"
        exit_code=$?

        # Cleanup happens via trap
        exit $exit_code
    else
        log_info "Dry run complete - no execution performed"
    fi
}

# Run main function
main "$@"