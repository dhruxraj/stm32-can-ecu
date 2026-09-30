# Bring-up procedure and two-board CAN test

Equipment needed:

* Lab supply with current limit
* Multimeter
* ST-LINK
* 3.3 V USB-UART adapter
* Optional: oscilloscope, USB-CAN adapter (CANable/PCAN/Kvaser/SocketCAN)

## 1. Before power (bare / assembled board)

1. Visual inspection under magnification: LQFP and LGA bridges, orientation of U1 (R-78E), D1, D2, D3-D7, U3 pin 1, U4 pin 1, U5 pin 1, C2 polarity.
2. Resistance to GND. None may be a short. Capacitor charging is normal.

   | Node | Test point | Expected |
   |---|---|---|
   | VIN_PROT | TP3 | > 10 kΩ |
   | +5V | TP4 | > 1 kΩ |
   | +3V3 | TP5 | > 500 Ω |
   | CANH–CANL | J2 pin 1–2 | ≈ 120 Ω with JP2 shunts fitted, open (> 10 kΩ) without |

## 2. First power-up (no MCU firmware yet)

1. Set the supply to **12 V, current limit 150 mA**, and connect J1 (+ = pin 1 marked "+").
2. Expect about 5-25 mA and the PWR LED on.
   * > 60 mA with blank firmware means something is wrong. Switch off and investigate.
3. Measure the rails:

   | Test point | Rail | Expected |
   |---|---|---|
   | TP3 | VIN_PROT | VIN − 0.3…0.5 V |
   | TP4 | +5V | 4.9-5.1 V |
   | TP5 | +3V3 | 3.25-3.35 V |
   | C12/C13 | +3V3A (VDDA) | ≈ 3.3 V |

4. Reverse-polarity test (optional, do it once): apply −12 V with the limit at 150 mA. The supply goes into current limit and the board must survive. Restore the correct polarity; the PTC recovers after cooling.
5. Sweep VIN 8 → 18 V. +5 V must stay in regulation.

## 3. Programming

See `docs/FIRMWARE.md` → Programming.

1. Connect the ST-LINK to J4 and read the device ID with STM32CubeProgrammer (should be 0x468, STM32G431).
2. Flash `can_ecu.hex`.
3. With the UART connected at 115200 8N1 you should see:

```
STM32 CAN ECU fw 1.0  node 0  reset cause 2  clock HSE 8 MHz  IMU WHO_AM_I 0x6A
node 0 DEGRADED faults act=0x0008 lat=0x0008 | VIN 12031 mV MCU 31 C | acc 12 -35 998 mg | ...
```

A **single** board reports `CAN_PASSIVE` (0x0008) and state DEGRADED. This is correct: nobody acknowledges its frames. You will see TEC 128 and the CAN-TX LED flickering at retry rate.

Check on the single board:

* Tilt the board. `acc` must follow gravity (±1000 mg on the axis pointing up/down).
* `clock HSE 8 MHz` is printed. If it prints `HSI16 FALLBACK`, check the crystal and C16/C17.
* The VIN reading matches the supply within ±3 %.
* The USER button prints `[btn] IDENTIFY sent`.
* Optional: probe the crystal with a 10× probe on OSC_OUT (C17), about 8 MHz.

## 4. Two-board CAN test (the main acceptance test)

**Setup:**

* **Board A:** JP3 and JP4 open → **node 0**.
* **Board B:** JP3 closed with a solder blob → **node 1**. Node IDs must differ; a duplicate ID gives fault `ID_CONFLICT`.
* **Termination:** fit **both** JP2 shunts (1-3 and 2-4) on **both** boards, since each is one end of a 2-node bus.

**Wiring:**

| Board A (J2 or J3) | Board B (J2 or J3) |
|---|---|
| 1 CANH | 1 CANH |
| 2 CANL | 2 CANL |
| 3 GND | 3 GND |

Use a twisted pair for CANH/CANL, plus the GND wire, up to a few metres. Each board can have its own supply, but the GND wire in the CAN cable is required.

**Check the termination with power OFF:** measure between CANH and CANL on either connector. It must read **≈ 60 Ω** (two 120 Ω in parallel).

**Procedure:**

1. **Power both boards.** Within about 1 s both STATUS LEDs change from fast blink to a **1 Hz short flash (RUN)**. Both CAN-TX and CAN-RX LEDs flicker, and the FAULT LEDs go off. You may see a slow FAULT flash if a latched `CAN_PASSIVE` from start-up is still stored; a long button press clears it.
2. **UART of board A:**
   * `[can] peer node 1 online (fw 1.0)` appears.
   * The status line shows `RUN faults act=0x0000`, `peers 0x2`, `TEC 0 REC 0`.
   * The `peer 1 ... acc` line shows board B's accelerometer. Tilt board B and watch the values change on board A.
3. **Identify:** press USER on board A. Board B's STATUS LED blinks at 10 Hz for 3 s and its UART prints `[cmd] IDENTIFY from node 0`. Repeat in the other direction.
4. **Timeout test:** unplug the CAN cable.
   * Within 300 ms both boards print `peer ... TIMEOUT` and go to DEGRADED (2 Hz blink).
   * Each has fault `PEER_TIMEOUT`, and also `CAN_PASSIVE`, since there is now no acknowledge.
   * Replug: both return to RUN automatically.
5. **Bus-off test:** short CANH to CANL briefly (< 1 s) while running.
   * The TEC rises and the node may go bus-off (FAULT state, STATUS off, FAULT LED on).
   * After the short is removed it recovers automatically. `busoff_count` in DIAG increments.
6. **With a USB-CAN adapter** (500 kbit/s), for example with Linux SocketCAN:

   ```bash
   sudo ip link set can0 type can bitrate 500000 && sudo ip link set can0 up
   candump can0                               # raw frames 0x100-0x104, 0x110-0x114
   python3 tools/can_monitor.py -i socketcan -c can0   # decoded view, CRC/counter check
   python3 tools/can_monitor.py -i socketcan -c can0 --identify 255
   ```

   Expected:
   * About 121 frames/s per node.
   * Zero CRC errors, zero lost/repeated counters.
   * ACCEL Z ≈ +1000 mg on a flat board.
   * VIN ≈ supply voltage.

   The `.dbc` in `tools/` loads into SavvyCAN, BusMaster, Vector or PCAN-Explorer.
7. **Scope (optional):**
   * CANH idles at 2.5 V and goes to ~3.5 V when dominant; CANL idles at 2.5 V and goes to ~1.5 V.
   * Differential dominant voltage ≈ 2 V.
   * Bit time 2.0 µs.
   * Clean edges, no ringing > 10 % with correct termination.

## 5. Troubleshooting

| Symptom | Likely cause / check |
|---|---|
| No PWR LED | polarity; F1 tripped (let it cool); U1 orientation; VIN < 7 V |
| +5 V ok, no +3V3 | U2 EN (pin 3) must be at 5 V; U2 orientation; short on +3V3 |
| ST-LINK cannot connect | NRST connected? try "connect under reset"; BOOT0 jumper open; VDD at J4.1 = 3.3 V; SWDIO/SWCLK swapped? |
| `HSI16 FALLBACK` | crystal not oscillating: solder joints, wrong CL/caps, crystal 3225 pad mapping (pads 1/3 must be the crystal) |
| `IMU WHO_AM_I 0x00`, fault IMU_COMM | LGA soldering (most common), pull-ups R13/R14, SA0 must be GND (addr 0x6A) |
| Alone on bus: DEGRADED, CAN_PASSIVE | **normal** - needs a second node to acknowledge |
| Two boards, no communication | same node ID? (ID_CONFLICT); CANH/CANL swapped between boards; GND wire missing; termination not ≈ 60 Ω; transceiver S pin stuck high (PA8) |
| CRC/E2E errors | mismatched firmware versions; noisy bus - check termination and GND |
| Frequent watchdog resets (reset cause 4) | a blocking call - check UART connection (20 ms timeout), I2C bus lock-up |
| Board resets when CAN bus shorted to 12 V | not protected: TJA1051 bus pins are rated −58…+58 V, but check wiring - never connect VIN to CAN lines |
