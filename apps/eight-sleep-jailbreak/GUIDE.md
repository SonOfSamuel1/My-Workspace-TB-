# Eight Sleep Pod 5 Jailbreak - Step-by-Step Guide

## Prerequisites

- [ ] Hardware ordered and received (see HARDWARE.md)
- [ ] Mac dependencies installed (`./scripts/setup-mac.sh`)
- [ ] Pod 5 initial setup completed via Eight Sleep app
- [ ] Read the Free Sleep INSTALLATION.md:
      <https://github.com/throwaway31265/free-sleep/blob/main/INSTALLATION.md>

---

## Phase 1: Preparation

### 1.1 Install Mac Tools

```bash
./scripts/setup-mac.sh
```

### 1.2 Review Pod 5 Teardown

Read the teardown guide in the Free Sleep repo `docs/` directory to understand
how to access the circuit board JTAG header.

---

## Phase 2: Physical Access

### 2.1 Access the Circuit Board

Follow the Pod 5 teardown docs to expose the JTAG header on the circuit board.
No permanent disassembly required - you'll reassemble after connecting.

---

## Phase 3: Serial Connection

### 3.1 Wire Up (Pod UNPLUGGED)

1. Connect tag-connect cable to FTDI adapter via dupont wires (see HARDWARE.md
   wiring diagram)
2. Connect tag-connect to pod's circuit board JTAG header
3. Connect FTDI adapter to Mac via USB

### 3.2 Find Serial Device

```bash
./scripts/find-serial.sh
```

Look for a device like `/dev/tty.usbserial-XXXXX`

### 3.3 Open Serial Terminal

```bash
minicom -b 921600 -o -D /dev/tty.usbserial-XXXXX
```

Replace `XXXXX` with your actual device identifier.

---

## Phase 4: Root Access

**This is the timing-critical phase. Read all steps before starting.**

### 4.1 Boot Interrupt

1. Plug in pod power cable
2. Watch the serial terminal output
3. **QUICKLY press Ctrl+C** when you see "Hit any key to stop autoboot"
   - You have a ~3 second window
   - If you miss it, unplug and try again

### 4.2 U-Boot Commands

Once you're in the U-Boot prompt, run these commands one at a time:

```
printenv current_slot
```

Note the slot (typically `_a`). Then:

```
setenv bootargs "root=PARTLABEL=rootfs_a rootwait init=/bin/bash"
run bootcmd
```

> If `current_slot` shows `_b`, replace `rootfs_a` with `rootfs_b`.

### 4.3 Mount Filesystems

```bash
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t tmpfs tmpfs /run
mount -o remount,rw /
```

### 4.4 Set Root Passwords

```bash
passwd root
passwd rewt
```

Choose strong passwords and save them somewhere secure.

### 4.5 Sync and Reboot

```bash
sync
reboot -f
```

---

## Phase 5: Install Free Sleep

### 5.1 Log In

After reboot, log in via serial terminal as `root` with your new password.

### 5.2 Disable Stock Services

```bash
systemctl disable --now swupdate-progress swupdate defibrillator \
  eight-kernel telegraf vector frankenfirmware dac swupdate.socket

systemctl mask swupdate-progress swupdate defibrillator eight-kernel \
  telegraf vector frankenfirmware dac swupdate.socket
```

### 5.3 Configure Wi-Fi

Replace `YOUR_WIFI_NAME` and `YOUR_WIFI_PASSWORD` with your actual credentials:

```bash
nmcli connection add type wifi con-name YOUR_WIFI_NAME ifname wlan0 \
  ssid YOUR_WIFI_NAME wifi-sec.key-mgmt wpa-psk wifi-sec.psk "YOUR_WIFI_PASSWORD" \
  ipv4.method auto ipv6.method auto

sed -i 's/uuid=.*/uuid=700a7a76-2105-4f46-b1b4-c9f3c791c440/' \
  /persistent/system-connections/*.nmconnection

nmcli connection reload
```

### 5.4 Install Free Sleep

```bash
/bin/bash -c "$(curl -fsSL \
  https://raw.githubusercontent.com/throwaway31265/free-sleep/main/scripts/install.sh)"
```

### 5.5 Get Pod IP Address

```bash
nmcli -g ip4.address device show wlan0
```

Write this down - you'll use it to access the web interface.

---

## Phase 6: Configure & Verify

### 6.1 Access Web Interface

Open in browser: `http://<POD_IP>:3000`

### 6.2 Set Timezone

**Required for scheduling to work correctly.** Go to Settings in the web
interface.

### 6.3 Set Up SSH (Optional but Recommended)

```bash
sh /home/dac/free-sleep/scripts/setup_ssh.sh
```

This lets you SSH into the pod from your Mac for future maintenance.

### 6.4 Block Internet Access (Recommended)

```bash
sh /home/dac/free-sleep/scripts/block_internet_access.sh
```

Prevents the pod from phoning home to Eight Sleep servers.

### 6.5 Add to Phone Home Screen

- iOS: Open `http://<POD_IP>:3000` in Safari > Share > Add to Home Screen
- Android: Open in Chrome > Menu > Add to Home Screen

---

## Phase 7: Validation

### 7.1 Power Cycle Test

1. Unplug pod power
2. Wait 10 seconds
3. Plug back in
4. Wait ~4 minutes for boot
5. Confirm web interface is accessible at `http://<POD_IP>:3000`

### 7.2 Hardware Reassembly

1. Disconnect tag-connect cable from circuit board
2. Reassemble the pod housing
3. Connect mattress cover normally

### 7.3 Temperature Test

1. Set a temperature via the web app
2. Verify the mattress physically changes temperature
3. Check that biometric data appears after sleeping on it

### 7.4 Troubleshooting

If anything isn't working, SSH in and run:

```bash
fs-debug
```

This generates a diagnostic report. Share it on the Free Sleep Discord if
needed.

---

## Done

Your Eight Sleep Pod 5 is now running Free Sleep with full local control. No
subscription. No cloud dependency. No telemetry.

Bookmark: `http://<POD_IP>:3000`
