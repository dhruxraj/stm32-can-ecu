# Design notes, decisions and assumptions

## 1. Architecture

![block diagram](img/block_diagram.png)

The board is a small "ECU-style" CAN node:

* **Power:** 8-18 V DC input (12 V nominal). The input is protected by a resettable PTC fuse, a TVS diode and a series Schottky diode. A RECOM R-78E5.0-0.5 switching module makes +5 V. An AP2112K LDO makes +3V3 from +5 V. A ferrite bead and extra capacitors give a filtered +3V3A for the MCU's analog supply (VDDA / VREF+).
* **MCU:** STM32G431CBT6 in LQFP48. It has a Cortex-M4F at 170 MHz, 128 KB flash, 32 KB RAM and one FDCAN (it can be used as classic CAN). It runs from an 8 MHz crystal with the PLL at 170 MHz.
* **CAN:** NXP TJA1051T/3 transceiver. Its VCC is +5 V and its VIO is 3.3 V, so it talks directly to the MCU at 3.3 V logic. The bus has a PESD1CAN ESD diode and a jumper-selectable split termination. Two paralleled 3-pole screw terminals let you daisy-chain boards.
* **Sensor:** ST LSM6DS3TR-C 6-axis IMU on I2C1 (address 0x6A). Its two interrupt lines go to the MCU.
* **Debug and interface:**
  * SWD header in ST-LINK/Nucleo pin order, with SWO.
  * 3.3 V UART plus 5 GPIO on a 2x5 header.
  * 5 LEDs, reset and user buttons.
  * BOOT0 jumper and two node-ID jumpers.

## 2. Key decisions (and why)

| # | Decision | Reason / trade-off |
|---|---|---|
| D1 | **STM32G431CBT6** (G4, not G0) | G0B1/G0C1 also have FDCAN, but the G431 adds FPU, 170 MHz, better ADC and wide availability. The LQFP48 package is hand-solderable at 0.5 mm pitch. |
| D2 | **No USB in rev A** | FDCAN1 is only usable on PA11/PA12, which are also the USB pins. The alternative PB8/PB9 puts CAN_RX on BOOT0, a well-known boot problem. CAN has priority; a UART on J5 replaces USB. |
| D3 | **Input 8-18 V**, not 5-12 V | The CAN transceiver needs 4.5-5.5 V on VCC. A 5 V rail from a 5 V input with protection drops is not possible, and the R-78E module needs >= 7 V in. 12 V automotive-style supply is the target. 5 V input is **not supported**. |
| D4 | Switching module instead of a linear 5 V regulator | 12 V to 5 V at up to 125 mA would waste ~0.9 W in a linear regulator. The pre-certified module needs no layout-critical inductor loop, which suits a first PCB. |
| D5 | 4-layer stack (signal / GND / 3V3 / signal) | This gives a solid reference plane under every trace. It also allows short via-to-plane decoupling, better EMC and easy routing of a 0.5 mm-pitch MCU. Price difference to 2-layer is small at prototype quantities. |
| D6 | TJA1051**T/3** (VIO variant) | The pin 5 VIO gives true 3.3 V logic levels. The plain TJA1051T has pin 5 NC and 5 V RXD output, which is **not** 3.3 V-safe on every MCU pin. Order the **/3** variant. |
| D7 | S pin pulled HIGH (silent) by default | The node stays off the bus until the firmware has configured FDCAN. This avoids disturbing the bus during reset, programming or a crash. |
| D8 | Split termination on a jumper | The bus needs exactly 120 Ω at each physical end: 2 terminations per bus, 60 Ω total. The split 2x60.4 Ω + 4.7 nF to GND also filters common-mode noise (corner ≈ 1.1 MHz). A permanent 120 Ω on every board would give 40 Ω with 3 boards. |
| D9 | Classic CAN 500 kbit/s | Supported by every USB-CAN adapter and analyzer. CAN FD is possible with this MCU/transceiver later (TJA1051 is specified to 5 Mbit/s). |
| D10 | Node ID by solder jumpers | Identical firmware on all boards, no reflashing needed for a second node. |
| D11 | Label-connected single-sheet schematic | Generated programmatically and guaranteed consistent with the PCB netlist. Net labels at every pin make it easy to trace nets in KiCad (click a label to highlight the whole net). |

## 3. Circuit details and small calculations

**HSE crystal (Y1, 8 MHz, CL = 12 pF).**
C = 2 × (CL − C_stray) = 2 × (12 − ~4.5) pF ≈ 15 pF → C16/C17 = 15 pF C0G.
Check the actual crystal's CL and ESR against ST AN2867 (gm_crit margin). A different CL needs different caps.

**Reset.**
NRST has an internal pull-up (~40 kΩ), plus C15 = 100 nF to GND and the SW1 pushbutton. The SWD header carries NRST (pin 5) so the debugger can reset the MCU.

**BOOT0.**
PB8-BOOT0 is pulled down by R4 (10 kΩ) and boots from flash. Closing JP1 enables the ROM bootloader, which the factory option bytes sample (nSWBOOT0 = 1).

**VBAT.**
Tied to +3V3 with its own 100 nF (no RTC battery).

**VDDA / VREF+.**
+3V3 → FB1 (600 Ω @ 100 MHz) → +3V3A with C12 1 µF + C13/C14 100 nF.

**VIN sense.**
R2 100 kΩ / R3 15 kΩ gives a ratio of 7.667. 18 V → 2.35 V at PA0; 25 V → 3.26 V. C6 100 nF gives τ = 1.3 ms. The ADC is referenced to the measured VREFINT, so the result is ratiometric-corrected.

**I2C pull-ups.**
4k7 at 400 kHz with an estimated ≤ 50 pF bus gives t_r ≈ 0.85 × 4.7 kΩ × 50 pF ≈ 0.2 µs. This is below the 0.3 µs Fast-mode limit.

**LED currents.**
(3.3 V − ~2.0 V) / 680 Ω ≈ 1.9 mA, which is enough for modern high-efficiency 0603 LEDs. The power LED gets (5 V − 2 V) / 1k5 = 2 mA.

**CAN ESD.**
PESD1CAN (SOT-23) sits close to the connectors, and the CAN traces pass the diode before reaching the transceiver.

**Reverse polarity.**
The series Schottky D2 blocks reverse voltage. The TVS D1 sits before D2 and is forward-biased on a reversed input, acting as a crowbar. The resulting fault current trips the PTC F1 (hold 0.5 A) within about a second. The board survives, but the supply sees a short until the PTC trips.

## 4. Assumptions and items that were NOT fully verified

| # | Item | Status / action |
|---|---|---|
| A1 | LSM6DS3TR-C LGA-14 land pattern (0.5 × 0.25 mm pads) | Modelled on the typical ST recommendation. **Verify** against the current ST datasheet/TN before ordering. |
| A2 | PESD1CAN pin assignment (1, 2 = lines, 3 = common) | Symmetric device, so a 1↔2 swap is harmless. **Verify pin 3** = common. |
| A3 | R-78E5.0-0.5 pin pitch 2.54 mm and body offset | The keep-out is reserved ±6.5 mm around the pin row. **Verify** against the RECOM drawing. |
| A4 | Screw terminal MPNs (Phoenix 1729128 / 1729131) and hole sizes | **Verify** with the part you buy; any 5.08 mm-pitch terminal with 1.3 mm drill is fine. |
| A5 | Crystal CL 12 pF, 3225 package | Choose a crystal with CL 10-12 pF and ESR ≤ 80 Ω, and recompute C16/C17. |
| A6 | I2C timing 0x10320309 (400 kHz @ HSI16) | Taken from the RM0440 timing example. Verify with CubeMX or measure SCL. |
| A7 | PTC hold 0.5 A / ≥ 30 V rating | Any 1812 PTC with I_hold ≈ 0.5 A and V_max ≥ 30 V. |
| A8 | TVS SMBJ18A clamp 29.2 V @ Ipp vs. R-78E abs. max input | The module is protected against moderate transients only. **Not rated for ISO 7637 / ISO 16750 load dump.** |
| A9 | STM32 current at 170 MHz ≈ 30-40 mA | Datasheet typical run current plus peripherals. The design budget is 100 mA on +3V3. |
| A10 | KiCad file format | Written as KiCad 7 files (opens in KiCad 7/8/9). Not opened in KiCad during generation. See VALIDATION_REPORT.md. |

## 5. Limitations of rev A

* The board is not qualified for vehicles. It has no ISO 7637-2 / ISO 16750-2 load-dump or cold-crank design, no reverse-battery MOSFET and no AEC-Q parts required.
* There is no CAN common-mode choke. One can be added for EMC-critical use.
* There is no USB (see D2). The UART needs a 3.3 V USB-UART adapter.
* Only one CAN channel (the STM32G431 has one FDCAN).
* The E2E-style counter/CRC and state machine are *automotive-inspired*. They are **not** AUTOSAR E2E or ISO 26262 compliant.
* The IMU is not mechanically isolated. Board flex or screw torque can shift the accelerometer offset slightly.

## 6. Future improvements

* Rev B MCU with 2+ FDCAN and separate USB (e.g. STM32G474 / G0B1): gives USB-C device and a second CAN channel.
* Discrete buck (e.g. LMR51420-class) with a reverse-polarity P-FET ideal diode, load-dump TVS and wider 6-36 V input.
* CAN common-mode choke plus split-termination DNP options, and optional CAN FD bit timing (2 Mbit/s data phase).
* EEPROM or option bytes for node configuration, CAN bootloader for field updates, UDS-like diagnostic services.
* Mount the IMU at the board centroid with a stiffening keep-out, and add a temperature compensation table.
