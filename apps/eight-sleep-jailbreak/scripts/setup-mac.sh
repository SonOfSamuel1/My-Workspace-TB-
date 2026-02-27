#!/bin/bash
# Setup Mac dependencies for Eight Sleep Pod 5 jailbreak
set -euo pipefail

echo "=== Eight Sleep Pod 5 Jailbreak - Mac Setup ==="
echo ""

# Check for Homebrew
if ! command -v brew &>/dev/null; then
    echo "ERROR: Homebrew not found. Install it first:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
fi

echo "[1/2] Installing minicom (serial terminal)..."
if command -v minicom &>/dev/null; then
    echo "  minicom already installed: $(which minicom)"
else
    brew install minicom
    echo "  minicom installed successfully"
fi

echo ""
echo "[2/2] Checking for FTDI drivers..."
# macOS includes built-in FTDI support since Big Sur
# Check if the driver is loaded
if kextstat 2>/dev/null | grep -q FTDI || system_profiler SPUSBDataType 2>/dev/null | grep -q "FTDI"; then
    echo "  FTDI driver detected"
else
    echo "  FTDI driver not detected (this is normal if adapter isn't plugged in yet)"
    echo "  macOS Big Sur+ has built-in FTDI support - no extra driver needed"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Connect your FTDI adapter to Mac via USB"
echo "  2. Run: ./scripts/find-serial.sh"
echo "  3. Follow GUIDE.md"
