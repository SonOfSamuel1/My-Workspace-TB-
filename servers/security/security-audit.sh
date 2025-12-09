#!/bin/bash

################################################################################
# Automated Security Audit Script for My Workspace
#
# This script performs comprehensive security audits and generates reports
# Can be scheduled via cron for regular security assessments
#
# Usage: ./security-audit.sh [daily|weekly|monthly|full]
################################################################################

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECURITY_DIR="${WORKSPACE_ROOT}/security"
VAULT_DIR="${HOME}/.my-workspace-vault"
AUDIT_REPORT_DIR="${WORKSPACE_ROOT}/security/audit-reports"
REPORT_FILE="${AUDIT_REPORT_DIR}/audit-$(date +%Y%m%d-%H%M%S).txt"

# Create report directory
mkdir -p "${AUDIT_REPORT_DIR}"
chmod 700 "${AUDIT_REPORT_DIR}"

################################################################################
# Audit Functions
################################################################################

print_header() {
    echo "════════════════════════════════════════════════════════════════════"
    echo "                    SECURITY AUDIT REPORT"
    echo "════════════════════════════════════════════════════════════════════"
    echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Host: $(hostname)"
    echo "User: $(whoami)"
    echo "Audit Type: $1"
    echo "────────────────────────────────────────────────────────────────────"
    echo
}

audit_credentials() {
    echo -e "${BLUE}[1/10] CREDENTIAL AUDIT${NC}"
    echo "────────────────────────────────────────"

    # Check credential rotation
    echo "Checking credential rotation status..."
    cd "${SECURITY_DIR}"
    python3 credential-manager.py check-rotation || true

    # Validate permissions
    echo -e "\nValidating credential file permissions..."
    python3 credential-manager.py validate || true

    # List all credentials
    echo -e "\nInventory of stored credentials:"
    python3 credential-manager.py list || true

    echo
}

audit_file_permissions() {
    echo -e "${BLUE}[2/10] FILE PERMISSION AUDIT${NC}"
    echo "────────────────────────────────────────"

    local issues=0

    # Check critical directories
    echo "Checking directory permissions..."
    for dir in "$VAULT_DIR" "${WORKSPACE_ROOT}/logs/security" "${AUDIT_REPORT_DIR}"; do
        if [[ -d "$dir" ]]; then
            local perms=$(stat -f "%OLp" "$dir" 2>/dev/null || stat -c "%a" "$dir" 2>/dev/null)
            if [[ "$perms" == "700" ]]; then
                echo -e "  ✓ $dir: ${GREEN}SECURE${NC} (700)"
            else
                echo -e "  ✗ $dir: ${RED}INSECURE${NC} ($perms)"
                ((issues++))
            fi
        fi
    done

    # Check critical files
    echo -e "\nChecking file permissions..."
    for pattern in "*.enc" ".key" "*.log" "*.json"; do
        find "$VAULT_DIR" -name "$pattern" -type f 2>/dev/null | while read file; do
            local perms=$(stat -f "%OLp" "$file" 2>/dev/null || stat -c "%a" "$file" 2>/dev/null)
            if [[ "$perms" == "600" ]]; then
                echo -e "  ✓ $(basename "$file"): ${GREEN}SECURE${NC} (600)"
            else
                echo -e "  ✗ $(basename "$file"): ${RED}INSECURE${NC} ($perms)"
                ((issues++))
            fi
        done
    done

    echo -e "\nTotal permission issues: $issues"
    echo
}

audit_env_files() {
    echo -e "${BLUE}[3/10] ENVIRONMENT FILE AUDIT${NC}"
    echo "────────────────────────────────────────"

    # Find any remaining .env files
    echo "Searching for unprotected .env files..."
    local env_files=$(find "${WORKSPACE_ROOT}" -name ".env" -o -name ".env.local" | \
                     grep -v ".env.example" | \
                     grep -v ".env.backup" || true)

    if [[ -z "$env_files" ]]; then
        echo -e "  ${GREEN}✓ No unprotected .env files found${NC}"
    else
        echo -e "  ${RED}✗ Found unprotected .env files:${NC}"
        echo "$env_files" | while read file; do
            echo "    - $file"
        done
    fi

    echo
}

audit_rate_limits() {
    echo -e "${BLUE}[4/10] RATE LIMIT AUDIT${NC}"
    echo "────────────────────────────────────────"

    for app in autonomous-email-assistant weekly-budget-report; do
        echo -e "\n$app:"
        cd "${SECURITY_DIR}"
        python3 rate-limiter.py status --app "$app" 2>/dev/null | grep -E "Tokens:|Available:" || echo "  Unable to check"
    done

    echo
}

audit_logs() {
    echo -e "${BLUE}[5/10] AUDIT LOG ANALYSIS${NC}"
    echo "────────────────────────────────────────"

    for app in autonomous-email-assistant weekly-budget-report; do
        echo -e "\n$app:"

        # Check log integrity
        echo "  Integrity check:"
        cd "${SECURITY_DIR}"
        if python3 audit-logger.py verify --app "$app" 2>/dev/null | grep -q "PASSED"; then
            echo -e "    ${GREEN}✓ PASSED${NC}"
        else
            echo -e "    ${RED}✗ FAILED${NC}"
        fi

        # Generate report
        echo "  Recent activity:"
        python3 audit-logger.py report --app "$app" --period daily 2>/dev/null | \
            grep -E "Total Events:|Critical Events:|API Calls:|Emails Sent:" | \
            sed 's/^/    /' || echo "    No data"
    done

    echo
}

audit_api_usage() {
    echo -e "${BLUE}[6/10] API USAGE AUDIT${NC}"
    echo "────────────────────────────────────────"

    # Check API call counts from audit logs
    echo "API calls in last 24 hours:"
    for api in gmail ynab todoist google-docs; do
        local count=$(grep "API_CALL.*$api" "$VAULT_DIR/audit/"*.jsonl 2>/dev/null | \
                     grep "$(date '+%Y-%m-%d')" | \
                     wc -l || echo 0)
        echo "  $api: $count calls"
    done

    echo
}

audit_security_events() {
    echo -e "${BLUE}[7/10] SECURITY EVENT AUDIT${NC}"
    echo "────────────────────────────────────────"

    # Check for security violations
    echo "Critical security events (last 7 days):"
    local critical=$(grep "CRITICAL\|SECURITY_VIOLATION" "$VAULT_DIR/audit/"*.jsonl 2>/dev/null | \
                    tail -20 | wc -l || echo 0)

    if [[ $critical -eq 0 ]]; then
        echo -e "  ${GREEN}✓ No critical events${NC}"
    else
        echo -e "  ${RED}✗ $critical critical events detected${NC}"
        grep "CRITICAL\|SECURITY_VIOLATION" "$VAULT_DIR/audit/"*.jsonl 2>/dev/null | \
            tail -5 | \
            jq -r '"\(.timestamp) - \(.event) - \(.details)"' 2>/dev/null | \
            sed 's/^/    /' || true
    fi

    # Check authentication failures
    echo -e "\nAuthentication failures:"
    local auth_fail=$(grep "AUTH_FAILURE" "$VAULT_DIR/audit/"*.jsonl 2>/dev/null | \
                     tail -20 | wc -l || echo 0)

    if [[ $auth_fail -eq 0 ]]; then
        echo -e "  ${GREEN}✓ No authentication failures${NC}"
    else
        echo -e "  ${YELLOW}⚠ $auth_fail authentication failures${NC}"
    fi

    echo
}

audit_mcp_servers() {
    echo -e "${BLUE}[8/10] MCP SERVER AUDIT${NC}"
    echo "────────────────────────────────────────"

    # Check MCP configuration
    local mcp_config="${HOME}/.config/claude/claude_code_config.json"

    if [[ -f "$mcp_config" ]]; then
        echo "MCP configuration found:"

        # Check file permissions
        local perms=$(stat -f "%OLp" "$mcp_config" 2>/dev/null || stat -c "%a" "$mcp_config" 2>/dev/null)
        if [[ "$perms" == "600" ]]; then
            echo -e "  Permissions: ${GREEN}SECURE${NC} (600)"
        else
            echo -e "  Permissions: ${RED}INSECURE${NC} ($perms)"
        fi

        # List configured servers
        echo "  Configured servers:"
        jq -r '.mcpServers | keys[]' "$mcp_config" 2>/dev/null | sed 's/^/    - /' || echo "    Unable to parse"
    else
        echo -e "  ${YELLOW}⚠ No MCP configuration found${NC}"
    fi

    echo
}

audit_docker_lambda() {
    echo -e "${BLUE}[9/10] DOCKER/LAMBDA AUDIT${NC}"
    echo "────────────────────────────────────────"

    # Check for Docker files
    echo "Docker configurations:"
    find "${WORKSPACE_ROOT}" -name "Dockerfile*" -type f | while read file; do
        echo "  - $file"

        # Check for hardcoded secrets
        if grep -q "API_KEY\|TOKEN\|PASSWORD\|SECRET" "$file"; then
            echo -e "    ${RED}⚠ May contain hardcoded secrets${NC}"
        else
            echo -e "    ${GREEN}✓ No obvious secrets${NC}"
        fi
    done

    # Check Lambda handlers
    echo -e "\nLambda handlers:"
    find "${WORKSPACE_ROOT}" -name "lambda_handler.*" -type f | while read file; do
        echo "  - $file"
    done

    echo
}

audit_compliance() {
    echo -e "${BLUE}[10/10] COMPLIANCE AUDIT${NC}"
    echo "────────────────────────────────────────"

    echo "Security Framework Compliance:"

    # Check required components
    local components=(
        "$SECURITY_DIR/credential-manager.py"
        "$SECURITY_DIR/rate-limiter.py"
        "$SECURITY_DIR/audit-logger.py"
        "$SECURITY_DIR/safe-execute.sh"
        "$SECURITY_DIR/README.md"
    )

    local compliant=0
    local total=${#components[@]}

    for component in "${components[@]}"; do
        if [[ -f "$component" ]]; then
            echo -e "  ✓ $(basename "$component")"
            ((compliant++))
        else
            echo -e "  ✗ $(basename "$component") - MISSING"
        fi
    done

    echo -e "\nCompliance Score: $compliant/$total ($(( compliant * 100 / total ))%)"

    # Check security configurations
    echo -e "\nSecurity Configurations:"
    for app in weekly-budget-report autonomous-email-assistant; do
        if [[ -f "${WORKSPACE_ROOT}/apps/${app}/security-config.json" ]]; then
            echo -e "  ✓ $app"
        else
            echo -e "  ✗ $app - MISSING"
        fi
    done

    echo
}

generate_recommendations() {
    echo -e "${YELLOW}SECURITY RECOMMENDATIONS${NC}"
    echo "────────────────────────────────────────"

    local recommendations=()

    # Check for credential rotation
    local needs_rotation=$(cd "${SECURITY_DIR}" && python3 credential-manager.py check-rotation 2>/dev/null | grep -c "overdue" || echo 0)
    if [[ $needs_rotation -gt 0 ]]; then
        recommendations+=("• Rotate $needs_rotation overdue credentials")
    fi

    # Check for .env files
    local env_count=$(find "${WORKSPACE_ROOT}" -name ".env" | grep -v example | grep -v backup | wc -l || echo 0)
    if [[ $env_count -gt 0 ]]; then
        recommendations+=("• Migrate $env_count .env files to secure storage")
    fi

    # Check audit logs
    local log_size=$(du -sh "$VAULT_DIR/audit" 2>/dev/null | cut -f1)
    recommendations+=("• Current audit log size: $log_size - consider archiving if large")

    # Check for updates
    recommendations+=("• Review and update security configurations monthly")
    recommendations+=("• Test disaster recovery procedures quarterly")
    recommendations+=("• Review access logs for anomalies weekly")

    for rec in "${recommendations[@]}"; do
        echo "$rec"
    done

    echo
}

generate_summary() {
    echo -e "${GREEN}AUDIT SUMMARY${NC}"
    echo "────────────────────────────────────────"

    local score=0
    local total=10

    # Calculate security score
    [[ $(find "${WORKSPACE_ROOT}" -name ".env" | grep -v example | wc -l) -eq 0 ]] && ((score++))
    [[ -f "$VAULT_DIR/credentials.enc" ]] && ((score++))
    [[ -f "$SECURITY_DIR/safe-execute.sh" ]] && ((score++))
    [[ -d "$VAULT_DIR/audit" ]] && ((score++))

    echo "Security Score: $score/$total"

    if [[ $score -ge 8 ]]; then
        echo -e "Status: ${GREEN}EXCELLENT${NC}"
    elif [[ $score -ge 6 ]]; then
        echo -e "Status: ${YELLOW}GOOD${NC}"
    elif [[ $score -ge 4 ]]; then
        echo -e "Status: ${YELLOW}NEEDS IMPROVEMENT${NC}"
    else
        echo -e "Status: ${RED}CRITICAL${NC}"
    fi

    echo -e "\nAudit completed at: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Report saved to: $REPORT_FILE"
}

################################################################################
# Main Execution
################################################################################

main() {
    local audit_type="${1:-daily}"

    # Redirect output to report file
    exec > >(tee -a "$REPORT_FILE")
    exec 2>&1

    print_header "$audit_type"

    case "$audit_type" in
        daily)
            audit_credentials
            audit_rate_limits
            audit_logs
            audit_security_events
            ;;
        weekly)
            audit_credentials
            audit_file_permissions
            audit_env_files
            audit_rate_limits
            audit_logs
            audit_api_usage
            audit_security_events
            ;;
        monthly|full)
            audit_credentials
            audit_file_permissions
            audit_env_files
            audit_rate_limits
            audit_logs
            audit_api_usage
            audit_security_events
            audit_mcp_servers
            audit_docker_lambda
            audit_compliance
            ;;
        *)
            echo "Usage: $0 [daily|weekly|monthly|full]"
            exit 1
            ;;
    esac

    generate_recommendations
    generate_summary

    # Set secure permissions on report
    chmod 600 "$REPORT_FILE"

    echo -e "\n${GREEN}✓ Audit complete${NC}"
}

# Install jq if not present (needed for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo "Installing jq for JSON parsing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq 2>/dev/null || echo "Please install jq manually"
    else
        sudo apt-get install -y jq 2>/dev/null || echo "Please install jq manually"
    fi
fi

main "$@"