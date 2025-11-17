#!/bin/bash
#
# iMessage Follow-up Automation Scheduler
#
# This script sets up automated scheduling for the iMessage follow-up system.
# It can be used to configure cron jobs or launchd agents on macOS.
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/src/imessage_main.py"
LOG_DIR="$SCRIPT_DIR/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "iMessage Follow-up Automation - Scheduler Setup"
echo "================================================"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script is designed for macOS${NC}"
    echo "For other systems, please set up cron manually."
    exit 1
fi

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}Error: Python script not found at $PYTHON_SCRIPT${NC}"
    exit 1
fi

echo "Select scheduling method:"
echo "1) launchd (macOS native, recommended)"
echo "2) cron"
echo "3) Show manual setup instructions"
echo "4) Cancel"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        # launchd setup
        echo ""
        echo "Setting up launchd agent..."

        PLIST_FILE="$HOME/Library/LaunchAgents/com.imessage.followup.plist"

        # Check interval
        read -p "Check interval in hours [4]: " interval
        interval=${interval:-4}
        interval_seconds=$((interval * 3600))

        # Create plist
        cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.imessage.followup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$PYTHON_SCRIPT</string>
        <string>--check</string>
    </array>
    <key>StartInterval</key>
    <integer>$interval_seconds</integer>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/scheduler.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/scheduler_error.log</string>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

        echo -e "${GREEN}Created plist file: $PLIST_FILE${NC}"

        # Load the agent
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
        launchctl load "$PLIST_FILE"

        echo -e "${GREEN}✅ launchd agent loaded successfully!${NC}"
        echo ""
        echo "The script will now run every $interval hours."
        echo ""
        echo "Management commands:"
        echo "  Stop:   launchctl unload $PLIST_FILE"
        echo "  Start:  launchctl load $PLIST_FILE"
        echo "  Status: launchctl list | grep imessage.followup"
        echo ""
        echo "Logs will be written to:"
        echo "  $LOG_DIR/scheduler.log"
        echo "  $LOG_DIR/scheduler_error.log"
        ;;

    2)
        # cron setup
        echo ""
        echo "Setting up cron job..."

        read -p "Check interval in hours [4]: " interval
        interval=${interval:-4}

        # Calculate cron expression
        if [ $interval -eq 24 ]; then
            cron_expr="0 9 * * *"  # Daily at 9 AM
        elif [ $interval -eq 12 ]; then
            cron_expr="0 */12 * * *"
        elif [ $interval -eq 6 ]; then
            cron_expr="0 */6 * * *"
        elif [ $interval -eq 4 ]; then
            cron_expr="0 */4 * * *"
        elif [ $interval -eq 2 ]; then
            cron_expr="0 */2 * * *"
        else
            cron_expr="0 */$interval * * *"
        fi

        cron_line="$cron_expr cd $SCRIPT_DIR && /usr/bin/python3 $PYTHON_SCRIPT --check >> $LOG_DIR/cron.log 2>&1"

        echo ""
        echo "Add this line to your crontab (crontab -e):"
        echo ""
        echo -e "${YELLOW}$cron_line${NC}"
        echo ""

        read -p "Would you like to add this automatically? [y/N]: " confirm
        if [[ $confirm =~ ^[Yy]$ ]]; then
            # Add to crontab
            (crontab -l 2>/dev/null || true; echo "$cron_line") | crontab -
            echo -e "${GREEN}✅ Cron job added successfully!${NC}"
        else
            echo "Please add the line manually using: crontab -e"
        fi
        ;;

    3)
        # Manual instructions
        echo ""
        echo "=== Manual Setup Instructions ==="
        echo ""
        echo "1. Create a shell script wrapper:"
        echo ""
        echo "   cat > $SCRIPT_DIR/run_check.sh <<'EOF'"
        echo "   #!/bin/bash"
        echo "   cd $SCRIPT_DIR"
        echo "   /usr/bin/python3 $PYTHON_SCRIPT --check"
        echo "   EOF"
        echo ""
        echo "   chmod +x $SCRIPT_DIR/run_check.sh"
        echo ""
        echo "2. Add to crontab (crontab -e):"
        echo ""
        echo "   # Every 4 hours"
        echo "   0 */4 * * * $SCRIPT_DIR/run_check.sh >> $LOG_DIR/cron.log 2>&1"
        echo ""
        echo "3. Or create a launchd plist in ~/Library/LaunchAgents/"
        echo "   (See README.md for full example)"
        echo ""
        ;;

    4)
        echo "Cancelled."
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo "Setup complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Test the automation: python src/imessage_main.py --check --no-email"
echo "2. Check logs in: $LOG_DIR/"
echo "3. Adjust config.yaml as needed"
echo ""
