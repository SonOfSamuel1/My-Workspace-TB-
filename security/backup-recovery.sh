#!/bin/bash

################################################################################
# Automated Backup and Recovery System for My Workspace
#
# Provides scheduled backups, automated recovery, and disaster recovery
# capabilities for the entire security framework.
#
# Usage: ./backup-recovery.sh [backup|restore|verify|schedule|dr-test]
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
BACKUP_ROOT="${HOME}/my-workspace-backups"
VAULT_DIR="${HOME}/.my-workspace-vault"
SECURITY_DIR="${WORKSPACE_ROOT}/security"
MAX_BACKUPS=30  # Keep last 30 backups
BACKUP_TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Ensure backup directory exists
mkdir -p "${BACKUP_ROOT}"
chmod 700 "${BACKUP_ROOT}"

################################################################################
# Functions
################################################################################

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

################################################################################
# Backup Functions
################################################################################

backup_credentials() {
    log "Backing up credentials..."

    local backup_dir="${BACKUP_ROOT}/${BACKUP_TIMESTAMP}"
    mkdir -p "${backup_dir}/vault"

    # Backup entire vault directory
    if [[ -d "$VAULT_DIR" ]]; then
        tar -czf "${backup_dir}/vault/vault-complete.tar.gz" \
            -C "$(dirname "$VAULT_DIR")" \
            "$(basename "$VAULT_DIR")" 2>/dev/null

        # Also create encrypted backup
        tar -czf - -C "$(dirname "$VAULT_DIR")" "$(basename "$VAULT_DIR")" 2>/dev/null | \
            openssl enc -aes-256-cbc -salt -pass pass:"${BACKUP_PASSWORD:-default}" \
            -out "${backup_dir}/vault/vault-encrypted.tar.gz.enc"

        log_success "Credentials backed up"
    else
        log_warning "Vault directory not found"
    fi
}

backup_configurations() {
    log "Backing up configurations..."

    local backup_dir="${BACKUP_ROOT}/${BACKUP_TIMESTAMP}"
    mkdir -p "${backup_dir}/configs"

    # Backup security configurations
    for app in "${WORKSPACE_ROOT}"/apps/*/security-config.json; do
        if [[ -f "$app" ]]; then
            cp "$app" "${backup_dir}/configs/$(basename $(dirname "$app"))-security-config.json"
        fi
    done

    # Backup MCP configurations
    if [[ -f "${HOME}/.config/claude/claude_code_config.json" ]]; then
        cp "${HOME}/.config/claude/claude_code_config.json" \
           "${backup_dir}/configs/mcp-config.json"
    fi

    # Backup .env.example files for reference
    find "${WORKSPACE_ROOT}" -name ".env.example" -exec cp {} "${backup_dir}/configs/" \;

    log_success "Configurations backed up"
}

backup_audit_logs() {
    log "Backing up audit logs..."

    local backup_dir="${BACKUP_ROOT}/${BACKUP_TIMESTAMP}"
    mkdir -p "${backup_dir}/audit"

    # Backup audit logs
    if [[ -d "${VAULT_DIR}/audit" ]]; then
        tar -czf "${backup_dir}/audit/audit-logs.tar.gz" \
            -C "${VAULT_DIR}" "audit" 2>/dev/null
        log_success "Audit logs backed up"
    else
        log_warning "No audit logs found"
    fi

    # Backup security monitor logs
    if [[ -d "${WORKSPACE_ROOT}/logs/security" ]]; then
        tar -czf "${backup_dir}/audit/security-logs.tar.gz" \
            -C "${WORKSPACE_ROOT}/logs" "security" 2>/dev/null
    fi
}

backup_scripts() {
    log "Backing up security scripts..."

    local backup_dir="${BACKUP_ROOT}/${BACKUP_TIMESTAMP}"
    mkdir -p "${backup_dir}/scripts"

    # Backup all security scripts
    cp -r "${SECURITY_DIR}"/*.{sh,py,js,md} "${backup_dir}/scripts/" 2>/dev/null || true

    log_success "Security scripts backed up"
}

create_backup_manifest() {
    log "Creating backup manifest..."

    local backup_dir="${BACKUP_ROOT}/${BACKUP_TIMESTAMP}"

    cat > "${backup_dir}/manifest.json" <<EOF
{
    "timestamp": "${BACKUP_TIMESTAMP}",
    "date": "$(date '+%Y-%m-%d %H:%M:%S')",
    "hostname": "$(hostname)",
    "user": "$(whoami)",
    "workspace_root": "${WORKSPACE_ROOT}",
    "components": {
        "vault": $(ls -la "${backup_dir}/vault" 2>/dev/null | wc -l),
        "configs": $(ls -la "${backup_dir}/configs" 2>/dev/null | wc -l),
        "audit": $(ls -la "${backup_dir}/audit" 2>/dev/null | wc -l),
        "scripts": $(ls -la "${backup_dir}/scripts" 2>/dev/null | wc -l)
    },
    "size": "$(du -sh "${backup_dir}" | cut -f1)",
    "checksum": "$(find "${backup_dir}" -type f -exec md5sum {} \; | md5sum | cut -d' ' -f1)"
}
EOF

    log_success "Manifest created"
}

perform_full_backup() {
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           AUTOMATED BACKUP SYSTEM                      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"

    log "Starting full backup..."

    # Create backup directory
    local backup_dir="${BACKUP_ROOT}/${BACKUP_TIMESTAMP}"
    mkdir -p "${backup_dir}"

    # Perform backups
    backup_credentials
    backup_configurations
    backup_audit_logs
    backup_scripts
    create_backup_manifest

    # Set permissions
    chmod -R 700 "${backup_dir}"

    # Cleanup old backups
    cleanup_old_backups

    # Create latest symlink
    ln -sfn "${backup_dir}" "${BACKUP_ROOT}/latest"

    echo -e "\n${GREEN}✓ Backup completed successfully${NC}"
    echo "Location: ${backup_dir}"
    echo "Size: $(du -sh "${backup_dir}" | cut -f1)"
}

################################################################################
# Restore Functions
################################################################################

restore_credentials() {
    local backup_dir="$1"

    log "Restoring credentials..."

    if [[ -f "${backup_dir}/vault/vault-complete.tar.gz" ]]; then
        # Backup current vault
        if [[ -d "$VAULT_DIR" ]]; then
            mv "$VAULT_DIR" "${VAULT_DIR}.old-$(date +%Y%m%d)"
            log_warning "Existing vault backed up to ${VAULT_DIR}.old-$(date +%Y%m%d)"
        fi

        # Restore vault
        tar -xzf "${backup_dir}/vault/vault-complete.tar.gz" \
            -C "$(dirname "$VAULT_DIR")"

        log_success "Credentials restored"
    else
        log_error "Credential backup not found"
        return 1
    fi
}

restore_configurations() {
    local backup_dir="$1"

    log "Restoring configurations..."

    # Restore security configs
    for config in "${backup_dir}"/configs/*-security-config.json; do
        if [[ -f "$config" ]]; then
            local app_name=$(basename "$config" | sed 's/-security-config.json//')
            local dest="${WORKSPACE_ROOT}/apps/${app_name}/security-config.json"

            if [[ -f "$dest" ]]; then
                cp "$dest" "${dest}.backup-$(date +%Y%m%d)"
            fi

            cp "$config" "$dest"
            log_success "Restored config for ${app_name}"
        fi
    done

    # Restore MCP config
    if [[ -f "${backup_dir}/configs/mcp-config.json" ]]; then
        local mcp_dest="${HOME}/.config/claude/claude_code_config.json"
        mkdir -p "$(dirname "$mcp_dest")"

        if [[ -f "$mcp_dest" ]]; then
            cp "$mcp_dest" "${mcp_dest}.backup-$(date +%Y%m%d)"
        fi

        cp "${backup_dir}/configs/mcp-config.json" "$mcp_dest"
        log_success "Restored MCP configuration"
    fi
}

restore_audit_logs() {
    local backup_dir="$1"

    log "Restoring audit logs..."

    if [[ -f "${backup_dir}/audit/audit-logs.tar.gz" ]]; then
        # Backup current logs
        if [[ -d "${VAULT_DIR}/audit" ]]; then
            mv "${VAULT_DIR}/audit" "${VAULT_DIR}/audit.old-$(date +%Y%m%d)"
        fi

        # Restore logs
        tar -xzf "${backup_dir}/audit/audit-logs.tar.gz" \
            -C "${VAULT_DIR}"

        log_success "Audit logs restored"
    else
        log_warning "No audit logs to restore"
    fi
}

perform_restore() {
    local backup_id="${1:-latest}"

    echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║           AUTOMATED RESTORE SYSTEM                     ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"

    # Resolve backup directory
    local backup_dir
    if [[ "$backup_id" == "latest" ]]; then
        backup_dir="${BACKUP_ROOT}/latest"
    else
        backup_dir="${BACKUP_ROOT}/${backup_id}"
    fi

    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup not found: $backup_id"
        echo "Available backups:"
        ls -lt "${BACKUP_ROOT}" | grep -v latest | head -10
        return 1
    fi

    log "Restoring from: $(readlink -f "$backup_dir")"

    # Confirm restore
    read -p "This will overwrite current configuration. Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Restore cancelled"
        return 0
    fi

    # Perform restore
    restore_credentials "$backup_dir"
    restore_configurations "$backup_dir"
    restore_audit_logs "$backup_dir"

    # Verify restore
    verify_installation

    echo -e "\n${GREEN}✓ Restore completed successfully${NC}"
}

################################################################################
# Verification Functions
################################################################################

verify_installation() {
    echo -e "\n${BLUE}Verifying installation...${NC}"

    local issues=0

    # Check vault
    if [[ -d "$VAULT_DIR" ]]; then
        log_success "Vault directory exists"
    else
        log_error "Vault directory missing"
        ((issues++))
    fi

    # Check credentials
    if [[ -f "${VAULT_DIR}/credentials.enc" ]]; then
        log_success "Credentials file exists"
    else
        log_error "Credentials file missing"
        ((issues++))
    fi

    # Check permissions
    local vault_perms=$(stat -f "%OLp" "$VAULT_DIR" 2>/dev/null || stat -c "%a" "$VAULT_DIR" 2>/dev/null)
    if [[ "$vault_perms" == "700" ]]; then
        log_success "Vault permissions correct"
    else
        log_warning "Vault permissions: $vault_perms (should be 700)"
    fi

    # Check configurations
    for app in autonomous-email-assistant weekly-budget-report; do
        if [[ -f "${WORKSPACE_ROOT}/apps/${app}/security-config.json" ]]; then
            log_success "Config exists for $app"
        else
            log_warning "Config missing for $app"
        fi
    done

    # Test credential manager
    if cd "${SECURITY_DIR}" && python3 credential-manager.py validate &>/dev/null; then
        log_success "Credential manager operational"
    else
        log_error "Credential manager issue"
        ((issues++))
    fi

    if [[ $issues -eq 0 ]]; then
        echo -e "\n${GREEN}✓ All verification checks passed${NC}"
        return 0
    else
        echo -e "\n${YELLOW}⚠ $issues issues detected${NC}"
        return 1
    fi
}

################################################################################
# Disaster Recovery Test
################################################################################

disaster_recovery_test() {
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║         DISASTER RECOVERY TEST                         ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"

    log "Starting disaster recovery test..."

    # Create test directory
    local test_dir="/tmp/dr-test-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$test_dir"

    log "Test directory: $test_dir"

    # Simulate disaster
    log_warning "Simulating disaster scenario..."

    # Backup current state
    perform_full_backup

    # Move current installation to test directory
    if [[ -d "$VAULT_DIR" ]]; then
        cp -r "$VAULT_DIR" "$test_dir/vault-original"
    fi

    # Corrupt installation (simulation)
    echo "CORRUPTED" > "${VAULT_DIR}/credentials.enc"
    rm -f "${VAULT_DIR}/audit/"*.jsonl 2>/dev/null

    log_error "Installation corrupted (simulation)"

    # Test detection
    log "Testing detection capabilities..."
    if ! verify_installation; then
        log_success "Corruption detected successfully"
    else
        log_error "Failed to detect corruption"
    fi

    # Test recovery
    log "Testing recovery procedures..."
    perform_restore "latest"

    # Verify recovery
    if verify_installation; then
        log_success "Recovery successful"
    else
        log_error "Recovery failed"
    fi

    # Cleanup
    rm -rf "$test_dir"

    echo -e "\n${GREEN}✓ Disaster recovery test completed${NC}"
}

################################################################################
# Scheduling Functions
################################################################################

setup_cron_schedule() {
    echo -e "${BLUE}Setting up automated backup schedule...${NC}"

    local cron_entry="0 2 * * * ${SECURITY_DIR}/backup-recovery.sh backup > ${BACKUP_ROOT}/backup.log 2>&1"

    # Check if already scheduled
    if crontab -l 2>/dev/null | grep -q "backup-recovery.sh"; then
        log_warning "Backup already scheduled"
        echo "Current schedule:"
        crontab -l | grep backup-recovery
    else
        # Add to crontab
        (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
        log_success "Backup scheduled for 2 AM daily"
    fi

    # Also create systemd timer (for systems with systemd)
    if command -v systemctl &> /dev/null; then
        create_systemd_timer
    fi
}

create_systemd_timer() {
    local service_file="/tmp/my-workspace-backup.service"
    local timer_file="/tmp/my-workspace-backup.timer"

    cat > "$service_file" <<EOF
[Unit]
Description=My Workspace Security Backup
After=network.target

[Service]
Type=oneshot
User=$(whoami)
ExecStart=${SECURITY_DIR}/backup-recovery.sh backup
StandardOutput=append:${BACKUP_ROOT}/backup.log
StandardError=append:${BACKUP_ROOT}/backup.log

[Install]
WantedBy=multi-user.target
EOF

    cat > "$timer_file" <<EOF
[Unit]
Description=Daily My Workspace Security Backup
Requires=my-workspace-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    echo "Systemd timer files created in /tmp/"
    echo "To install (requires sudo):"
    echo "  sudo cp /tmp/my-workspace-backup.* /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable --now my-workspace-backup.timer"
}

cleanup_old_backups() {
    log "Cleaning up old backups..."

    local backup_count=$(ls -1 "${BACKUP_ROOT}" | grep -v latest | wc -l)

    if [[ $backup_count -gt $MAX_BACKUPS ]]; then
        local to_delete=$((backup_count - MAX_BACKUPS))
        log_warning "Removing $to_delete old backups"

        ls -1t "${BACKUP_ROOT}" | grep -v latest | tail -n "$to_delete" | while read backup; do
            rm -rf "${BACKUP_ROOT:?}/${backup}"
            log "Removed: $backup"
        done
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    case "${1:-help}" in
        backup)
            perform_full_backup
            ;;
        restore)
            perform_restore "${2:-latest}"
            ;;
        verify)
            verify_installation
            ;;
        schedule)
            setup_cron_schedule
            ;;
        dr-test)
            disaster_recovery_test
            ;;
        list)
            echo "Available backups:"
            ls -lht "${BACKUP_ROOT}" | head -20
            ;;
        clean)
            cleanup_old_backups
            ;;
        help)
            cat <<EOF
Usage: $0 [command] [options]

Commands:
  backup              Perform full backup
  restore [id]        Restore from backup (default: latest)
  verify              Verify current installation
  schedule            Setup automated backup schedule
  dr-test             Run disaster recovery test
  list                List available backups
  clean               Clean old backups
  help                Show this help

Environment Variables:
  BACKUP_ROOT         Backup directory (default: ~/my-workspace-backups)
  MAX_BACKUPS         Number of backups to keep (default: 30)
  BACKUP_PASSWORD     Password for encrypted backups

Examples:
  $0 backup                    # Create new backup
  $0 restore                   # Restore from latest backup
  $0 restore 20241124-143022  # Restore specific backup
  $0 schedule                  # Setup daily backups
  $0 dr-test                   # Test disaster recovery

EOF
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"