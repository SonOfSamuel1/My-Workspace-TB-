#!/bin/bash

################################################################################
# Security Monitoring and Alerting System for My Workspace
#
# This script provides real-time monitoring of security events and automated
# alerting for critical issues.
#
# Usage: ./security-monitor.sh [options]
################################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
WORKSPACE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECURITY_DIR="${WORKSPACE_ROOT}/security"
VAULT_DIR="${HOME}/.my-workspace-vault"
AUDIT_DIR="${VAULT_DIR}/audit"
ALERT_FILE="${AUDIT_DIR}/critical_events.log"
MONITOR_LOG="${AUDIT_DIR}/monitor.log"

# Monitoring settings
CHECK_INTERVAL=60  # Seconds between checks
ALERT_THRESHOLD_CRITICAL=1
ALERT_THRESHOLD_HIGH=5
ALERT_THRESHOLD_MEDIUM=10

# Statistics
STATS_FILE="${AUDIT_DIR}/stats.json"

################################################################################
# Functions
################################################################################

log_monitor() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        CRITICAL)
            echo -e "${RED}[CRITICAL]${NC} $message"
            ;;
        HIGH)
            echo -e "${YELLOW}[HIGH]${NC} $message"
            ;;
        MEDIUM)
            echo -e "${BLUE}[MEDIUM]${NC} $message"
            ;;
        INFO)
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
    esac

    echo "[$timestamp] [$level] $message" >> "${MONITOR_LOG}"
}

check_critical_events() {
    local app="$1"
    local count=0

    if [[ -f "${ALERT_FILE}" ]]; then
        # Count critical events in last hour
        local one_hour_ago=$(date -v-1H '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S')
        count=$(awk -v date="$one_hour_ago" '$1 " " $2 > date' "${ALERT_FILE}" | wc -l)
    fi

    if [[ $count -ge $ALERT_THRESHOLD_CRITICAL ]]; then
        log_monitor "CRITICAL" "$count critical events detected in last hour for $app"
        send_alert "CRITICAL" "$app" "$count critical events in last hour"
        return 1
    fi

    return 0
}

check_rate_limits() {
    local app="$1"

    # Check rate limit status
    local rate_status=$(cd "${SECURITY_DIR}" && python3 rate-limiter.py status --app "$app" 2>/dev/null || echo "ERROR")

    if echo "$rate_status" | grep -q "0.0%"; then
        log_monitor "HIGH" "Rate limit exhausted for $app"
        send_alert "HIGH" "$app" "Rate limit exhausted"
        return 1
    fi

    return 0
}

check_credential_rotation() {
    # Check for credentials needing rotation
    local needs_rotation=$(cd "${SECURITY_DIR}" && python3 credential-manager.py check-rotation 2>/dev/null | grep "overdue" | wc -l || echo 0)

    if [[ $needs_rotation -gt 0 ]]; then
        log_monitor "MEDIUM" "$needs_rotation credentials need rotation"

        # Get details
        local details=$(cd "${SECURITY_DIR}" && python3 credential-manager.py check-rotation 2>/dev/null | grep "overdue")

        if [[ $needs_rotation -ge 3 ]]; then
            send_alert "HIGH" "credentials" "$needs_rotation credentials overdue for rotation"
        fi

        return 1
    fi

    return 0
}

check_audit_integrity() {
    local app="$1"

    # Verify audit log integrity
    local integrity=$(cd "${SECURITY_DIR}" && python3 audit-logger.py verify --app "$app" 2>/dev/null | grep "PASSED\|FAILED")

    if echo "$integrity" | grep -q "FAILED"; then
        log_monitor "CRITICAL" "Audit log integrity check FAILED for $app"
        send_alert "CRITICAL" "$app" "Audit log integrity compromised"
        return 1
    fi

    return 0
}

check_file_permissions() {
    # Check critical file permissions
    local issues=0

    # Check vault directory
    if [[ -d "$VAULT_DIR" ]]; then
        local perms=$(stat -f "%OLp" "$VAULT_DIR" 2>/dev/null || stat -c "%a" "$VAULT_DIR" 2>/dev/null)
        if [[ "$perms" != "700" ]]; then
            log_monitor "HIGH" "Insecure permissions on vault: $perms"
            chmod 700 "$VAULT_DIR"
            ((issues++))
        fi
    fi

    # Check credential files
    for file in "$VAULT_DIR"/*.enc "$VAULT_DIR"/.key; do
        if [[ -f "$file" ]]; then
            local perms=$(stat -f "%OLp" "$file" 2>/dev/null || stat -c "%a" "$file" 2>/dev/null)
            if [[ "$perms" != "600" ]]; then
                log_monitor "HIGH" "Insecure permissions on $file: $perms"
                chmod 600 "$file"
                ((issues++))
            fi
        fi
    done

    if [[ $issues -gt 0 ]]; then
        send_alert "HIGH" "permissions" "$issues permission issues fixed"
    fi

    return 0
}

check_unauthorized_access() {
    local app="$1"

    # Check for unauthorized access attempts
    local auth_failures=$(grep "AUTH_FAILURE\|PERMISSION_DENIED" "${AUDIT_DIR}/${app}_"*.audit.jsonl 2>/dev/null | \
                         jq -r '.timestamp' 2>/dev/null | \
                         awk -v date="$(date -v-1H '+%Y-%m-%d' 2>/dev/null || date -d '1 hour ago' '+%Y-%m-%d')" '$1 > date' | \
                         wc -l || echo 0)

    if [[ $auth_failures -ge 5 ]]; then
        log_monitor "HIGH" "$auth_failures authentication failures for $app in last hour"
        send_alert "HIGH" "$app" "$auth_failures authentication failures"
        return 1
    fi

    return 0
}

send_alert() {
    local severity="$1"
    local component="$2"
    local message="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Log to alert file
    echo "[$timestamp] [$severity] [$component] $message" >> "${ALERT_FILE}"

    # Console notification
    case "$severity" in
        CRITICAL)
            echo -e "\n${RED}╔════════════════════════════════════════════════════════╗${NC}"
            echo -e "${RED}║                    CRITICAL ALERT                      ║${NC}"
            echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
            echo -e "${RED}Component:${NC} $component"
            echo -e "${RED}Message:${NC} $message"
            echo -e "${RED}Time:${NC} $timestamp\n"

            # TODO: Send email/SMS for critical alerts
            ;;
        HIGH)
            echo -e "\n${YELLOW}⚠️  HIGH PRIORITY ALERT${NC}"
            echo -e "${YELLOW}Component:${NC} $component"
            echo -e "${YELLOW}Message:${NC} $message\n"
            ;;
        MEDIUM)
            echo -e "${BLUE}ℹ️  Alert:${NC} [$component] $message"
            ;;
    esac

    # Update statistics
    update_statistics "$severity"
}

update_statistics() {
    local severity="$1"

    if [[ ! -f "$STATS_FILE" ]]; then
        echo '{"critical":0,"high":0,"medium":0,"total":0}' > "$STATS_FILE"
    fi

    # Update counts
    case "$severity" in
        CRITICAL)
            jq '.critical += 1 | .total += 1' "$STATS_FILE" > "$STATS_FILE.tmp"
            ;;
        HIGH)
            jq '.high += 1 | .total += 1' "$STATS_FILE" > "$STATS_FILE.tmp"
            ;;
        MEDIUM)
            jq '.medium += 1 | .total += 1' "$STATS_FILE" > "$STATS_FILE.tmp"
            ;;
    esac

    if [[ -f "$STATS_FILE.tmp" ]]; then
        mv "$STATS_FILE.tmp" "$STATS_FILE"
    fi
}

generate_summary() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}           SECURITY MONITORING SUMMARY${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

    # Check statistics
    if [[ -f "$STATS_FILE" ]]; then
        local stats=$(cat "$STATS_FILE")
        echo "Alert Statistics:"
        echo "  Critical: $(echo "$stats" | jq -r '.critical')"
        echo "  High:     $(echo "$stats" | jq -r '.high')"
        echo "  Medium:   $(echo "$stats" | jq -r '.medium')"
        echo "  Total:    $(echo "$stats" | jq -r '.total')"
    fi

    echo -e "\nRecent Critical Events:"
    if [[ -f "$ALERT_FILE" ]]; then
        tail -5 "$ALERT_FILE" | while read line; do
            echo "  $line"
        done
    else
        echo "  None"
    fi

    echo -e "\nCredential Status:"
    cd "${SECURITY_DIR}" && python3 credential-manager.py check-rotation 2>/dev/null || echo "  Unable to check"

    echo -e "\nRate Limit Status:"
    for app in autonomous-email-assistant weekly-budget-report; do
        echo "  $app:"
        cd "${SECURITY_DIR}" && python3 rate-limiter.py status --app "$app" 2>/dev/null | grep "Available:" | head -3 | sed 's/^/    /'
    done
}

monitor_loop() {
    local apps=("autonomous-email-assistant" "weekly-budget-report" "love-brittany-tracker" "love-kaelin-tracker")

    log_monitor "INFO" "Starting security monitoring (interval: ${CHECK_INTERVAL}s)"

    while true; do
        local issues=0

        # Check each application
        for app in "${apps[@]}"; do
            # Skip if app directory doesn't exist
            if [[ ! -d "${WORKSPACE_ROOT}/apps/${app}" ]]; then
                continue
            fi

            # Run security checks
            check_critical_events "$app" || ((issues++))
            check_rate_limits "$app" || ((issues++))
            check_unauthorized_access "$app" || ((issues++))
            check_audit_integrity "$app" || ((issues++))
        done

        # Global checks
        check_credential_rotation || ((issues++))
        check_file_permissions || ((issues++))

        # Status update
        if [[ $issues -eq 0 ]]; then
            log_monitor "INFO" "All security checks passed"
        else
            log_monitor "MEDIUM" "$issues security issues detected"
        fi

        # Sleep before next check
        sleep "$CHECK_INTERVAL"
    done
}

################################################################################
# Main Execution
################################################################################

main() {
    # Parse arguments
    case "${1:-monitor}" in
        monitor)
            monitor_loop
            ;;
        check)
            # Single check run
            log_monitor "INFO" "Running single security check..."

            for app in autonomous-email-assistant weekly-budget-report; do
                check_critical_events "$app"
                check_rate_limits "$app"
                check_unauthorized_access "$app"
                check_audit_integrity "$app"
            done

            check_credential_rotation
            check_file_permissions

            generate_summary
            ;;
        summary)
            generate_summary
            ;;
        reset)
            # Reset statistics
            echo '{"critical":0,"high":0,"medium":0,"total":0}' > "$STATS_FILE"
            > "$ALERT_FILE"
            log_monitor "INFO" "Statistics reset"
            ;;
        help)
            echo "Usage: $0 [monitor|check|summary|reset|help]"
            echo ""
            echo "Commands:"
            echo "  monitor  - Start continuous monitoring (default)"
            echo "  check    - Run single security check"
            echo "  summary  - Show monitoring summary"
            echo "  reset    - Reset statistics"
            echo "  help     - Show this help"
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Create necessary directories
mkdir -p "$AUDIT_DIR"
chmod 700 "$AUDIT_DIR"

# Run main function with all arguments
main "$@"