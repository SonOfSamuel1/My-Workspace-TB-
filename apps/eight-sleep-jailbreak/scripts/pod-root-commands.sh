#!/bin/bash
# Pod 5 Root Access Commands - Reference Script
# These commands are run ON THE POD via serial terminal, not on your Mac.
# This file is for copy-paste reference only.

cat << 'COMMANDS'
=== PHASE 4: ROOT ACCESS ===
Run these in the serial terminal after catching the boot interrupt (Ctrl+C).

--- Step 1: Check current slot ---
printenv current_slot

--- Step 2: Boot into bash (use rootfs_a or rootfs_b based on step 1) ---
setenv bootargs "root=PARTLABEL=rootfs_a rootwait init=/bin/bash"
run bootcmd

--- Step 3: Mount filesystems ---
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t tmpfs tmpfs /run
mount -o remount,rw /

--- Step 4: Set passwords (you'll be prompted to enter them) ---
passwd root
passwd rewt

--- Step 5: Sync and reboot ---
sync
reboot -f

COMMANDS
