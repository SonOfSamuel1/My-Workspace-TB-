# Hardware Shopping List

All items needed for the Pod 5 jailbreak. Total cost: ~$70.

## Required Items

### 1. TC2070-IDC 14-pin Tag-Connect Cable (~$50)

**IMPORTANT: Get the IDC variant (with legs), NOT the NL (no legs) variant.**
The legs hold the connector in place during the timing-critical boot interrupt
step.

- [Amazon - FRETTEATRI TC2070-IDC](https://www.amazon.com/FRETTEATRI-TC2070-IDC-Tag-Connect-Electronic-Performance/dp/B0F332RHFC)
- [Tag-Connect Direct](https://www.tag-connect.com/product/tc2070-idc)

### 2. FTDI FT232RL USB to TTL Adapter (~$13)

USB to serial adapter for connecting Mac to the pod's circuit board.

- [Amazon - HiLetgo FT232RL](https://www.amazon.com/HiLetgo-FT232RL-Converter-Adapter-Breakout/dp/B00IJXZQ7C)

### 3. Dupont Jumper Wires - Female to Female (~$7)

For connecting the tag-connect cable to the FTDI adapter.

- Amazon - search "dupont wires female to female"

## Wiring Diagram

```text
Tag-Connect TC2070-IDC          FTDI FT232RL
=====================          =============
Pin 1 (TX)  ──────────────>    RX
Pin 5 (RX)  ──────────────>    TX
Pin 9 (GND) ──────────────>    GND

FTDI jumper: Set to 3.3V (NOT 5V)
```

Refer to the Free Sleep docs for the exact pin mapping on your pod model:
<https://github.com/throwaway31265/free-sleep/blob/main/INSTALLATION.md>
