#!/bin/bash
# Free Sleep Installation Commands - Reference Script
# These commands are run ON THE POD via serial terminal, not on your Mac.
# This file is for copy-paste reference only.

cat << 'COMMANDS'
=== PHASE 5: INSTALL FREE SLEEP ===
Run these after logging in as root with your new password.

--- Step 1: Disable stock Eight Sleep services ---
systemctl disable --now swupdate-progress swupdate defibrillator \
  eight-kernel telegraf vector frankenfirmware dac swupdate.socket

systemctl mask swupdate-progress swupdate defibrillator eight-kernel \
  telegraf vector frankenfirmware dac swupdate.socket

--- Step 2: Configure Wi-Fi (replace YOUR_WIFI_NAME and YOUR_WIFI_PASSWORD) ---
nmcli connection add type wifi con-name YOUR_WIFI_NAME ifname wlan0 \
  ssid YOUR_WIFI_NAME wifi-sec.key-mgmt wpa-psk wifi-sec.psk "YOUR_WIFI_PASSWORD" \
  ipv4.method auto ipv6.method auto

sed -i 's/uuid=.*/uuid=700a7a76-2105-4f46-b1b4-c9f3c791c440/' \
  /persistent/system-connections/*.nmconnection

nmcli connection reload

--- Step 3: Install Free Sleep ---
/bin/bash -c "$(curl -fsSL \
  https://raw.githubusercontent.com/throwaway31265/free-sleep/main/scripts/install.sh)"

--- Step 4: Get pod IP address ---
nmcli -g ip4.address device show wlan0

--- Step 5: Post-install (optional but recommended) ---
# Set up SSH access
sh /home/dac/free-sleep/scripts/setup_ssh.sh

# Block internet access (prevents phoning home)
sh /home/dac/free-sleep/scripts/block_internet_access.sh

COMMANDS
