# Eight Sleep Pod 5 Jailbreak

Remove cloud/subscription dependency from Eight Sleep Pod 5 using the
[Free Sleep](https://github.com/throwaway31265/free-sleep) open-source project.

## Why

- Eliminates $200-300/yr subscription
- Full local control via web app (temperature, scheduling, alarms, biometrics)
- No internet dependency - works offline
- Heart rate, HRV, breathing rate tracking retained
- Home Assistant integration possible

## Safety

- **Pod 5 cannot be bricked** if instructions are followed
- Fully reversible - factory reset restores stock firmware
- No permanent hardware modifications
- Active community with Discord support

## Quick Start

```bash
# 1. Install Mac-side dependencies
./scripts/setup-mac.sh

# 2. Find your serial device after connecting FTDI adapter
./scripts/find-serial.sh

# 3. Open serial connection (replace device name)
minicom -b 921600 -o -D /dev/tty.usbserial-XXXXX

# 4. Follow GUIDE.md step by step
```

## Files

- `GUIDE.md` - Complete step-by-step jailbreak guide
- `HARDWARE.md` - Hardware shopping list with links
- `scripts/setup-mac.sh` - Mac dependency installer
- `scripts/find-serial.sh` - Serial device finder
- `scripts/pod-root-commands.sh` - Copy-paste commands for root access phase
- `scripts/install-freesleep.sh` - Copy-paste commands for Free Sleep
  installation
- `REVERT.md` - How to restore stock firmware

## Resources

- [Free Sleep GitHub](https://github.com/throwaway31265/free-sleep)
- [Installation Docs](https://github.com/throwaway31265/free-sleep/blob/main/INSTALLATION.md)
- [Discord Support](https://discord.gg/JpArXnBgEj)
- [Kaspersky Security Analysis](https://www.kaspersky.com/blog/how-to-hack-a-smart-mattress/53232/)
