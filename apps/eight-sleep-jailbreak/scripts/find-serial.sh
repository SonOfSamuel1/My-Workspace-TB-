#!/bin/bash
# Find connected serial devices for FTDI adapter
set -euo pipefail

echo "=== Serial Device Finder ==="
echo ""
echo "Looking for serial devices..."
echo ""

# List all tty devices that look like USB serial adapters
devices=$(ls /dev/tty.usbserial-* /dev/tty.usbmodem-* /dev/tty.SLAB_USBtoUART* 2>/dev/null || true)

if [ -z "$devices" ]; then
    echo "No USB serial devices found."
    echo ""
    echo "Troubleshooting:"
    echo "  1. Is the FTDI adapter plugged into your Mac?"
    echo "  2. Try a different USB port or cable"
    echo "  3. Check System Preferences > Security if a driver was blocked"
    echo ""
    echo "All tty devices:"
    ls /dev/tty.* 2>/dev/null | head -20
else
    echo "Found serial device(s):"
    echo ""
    for dev in $devices; do
        echo "  $dev"
    done
    echo ""
    echo "To connect, run:"
    first_dev=$(echo "$devices" | head -1)
    echo "  minicom -b 921600 -o -D $first_dev"
fi
