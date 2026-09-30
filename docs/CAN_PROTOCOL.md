# CAN protocol (application layer)

Machine-readable versions: `tools/can_ecu.dbc` (all messages, all 4 node IDs) and `tools/canp.py` (Python decoder, identical to `firmware/Core/Src/can_protocol.c`).

## Physical / data link

| Item | Value |
|---|---|
| Bit rate | 500 kbit/s, classic CAN 2.0A (11-bit IDs), no remote frames |
| Bit timing (170 MHz PCLK1) | prescaler 17, TSEG1 15, TSEG2 4, SJW 4 → 20 tq, **sample point 80 %** |
| Termination | 120 Ω at both physical ends (JP2 fitted on those two boards only) |
| Transceiver | TJA1051T/3, VCC 5 V, VIO 3.3 V, S pin = silent while MCU not ready |
| Connector | J2 / J3: 1 = CANH, 2 = CANL, 3 = GND (paralleled, for daisy-chaining) |

## Identifiers

`ID = 0x100 + (node << 4) + message`, node = 0..3 from jumpers JP3/JP4.

| Message | Offset | Node 0 | Node 1 | Node 2 | Node 3 | Period | Direction |
|---|---:|---:|---:|---:|---:|---:|---|
| HEARTBEAT | 0 | 0x100 | 0x110 | 0x120 | 0x130 | 100 ms | ECU → bus |
| ACCEL | 1 | 0x101 | 0x111 | 0x121 | 0x131 | 20 ms | ECU → bus |
| GYRO | 2 | 0x102 | 0x112 | 0x122 | 0x132 | 20 ms | ECU → bus |
| BOARD | 3 | 0x103 | 0x113 | 0x123 | 0x133 | 100 ms | ECU → bus |
| DIAG | 4 | 0x104 | 0x114 | 0x124 | 0x134 | 1000 ms | ECU → bus |
| COMMAND to node n | - | 0x0F0 | 0x0F1 | 0x0F2 | 0x0F3 | event | any → node |
| COMMAND broadcast | - | 0x0FF | | | | event | any → all |

Lower ID means higher priority: commands win arbitration over data, and heartbeats over sensor data of the same node.

Bus load per node is 121 frames/s (10 + 50 + 50 + 10 + 1). At ≤ 130 bits per 8-byte frame including worst-case bit stuffing, that is ≈ 16 kbit/s ≈ **3 % of 500 kbit/s**. Four nodes use about 13 %.

## Common frame rules

* **DLC** = 8 always. Frames with another DLC are rejected and counted as errors.
* **Byte order:** little-endian (Intel). Signed values are two's complement.
* **Byte 6:** bits 0-3 are the **rolling counter** (0…15, +1 per message ID). Bits 4-7 are the **status nibble**:
  * bit 4 `DATA_VALID`
  * bit 5 `SENSOR_FAULT`
  * bit 6 `DEGRADED`
  * bit 7 reserved
* **Byte 7:** **CRC-8 SAE J1850** (poly 0x1D, init 0xFF, final XOR 0xFF). It is computed over `[ID & 0xFF, (ID >> 8) & 0x07, byte0 … byte6]`, so the ID is protected as well. Check value: CRC("123456789") = 0x4B.
* **Receiver checks** (`canp_check()`):
  * DLC == 8, then CRC.
  * Counter equal to the previous one → *repeated/stale* frame, rejected.
  * Counter jump → frames lost, accepted but counted.
  * CRC, DLC or repeat errors set fault `CAN_E2E` for 1 s.

> This counter + CRC scheme is inspired by AUTOSAR E2E profiles. It is **not** an implementation of any AUTOSAR E2E profile and is not safety-certified.

## Message layouts

### HEARTBEAT (0x100 + node·16), 100 ms

| Byte | Signal | Type | Unit / values |
|---|---|---|---|
| 0 | node_id | u8 | 0..3 |
| 1 | state | u8 | 0 INIT, 1 RUN, 2 DEGRADED, 3 FAULT |
| 2-3 | faults | u16 | active fault bits (table below) |
| 4 | peers_alive | u8 | bit n = heartbeat of node n received within 300 ms |
| 5 | fw_version | u8 | major << 4 \| minor (0x10 = 1.0) |
| 6 | counter / status | | status bit 6 = DEGRADED |
| 7 | CRC | | |

### ACCEL (+1) and GYRO (+2), 20 ms

| Byte | Signal | Type | Scaling | Range |
|---|---|---|---|---|
| 0-1 | X | s16 | ACCEL: 1 mg/bit; GYRO: 0.1 °/s/bit | ±4000 mg; ±500 °/s |
| 2-3 | Y | s16 | as above | |
| 4-5 | Z | s16 | as above | |
| 6 | counter / status | | DATA_VALID, SENSOR_FAULT | |
| 7 | CRC | | | |

The sensor is sampled at 104 Hz ODR and read every 20 ms. The firmware converts the raw sensor LSBs to these physical units (0.122 mg/LSB, 17.5 mdps/LSB). When the IMU is faulty, frames keep being sent (last values, `DATA_VALID` = 0, `SENSOR_FAULT` = 1), so receivers can tell "sensor fault" from "node lost".

### BOARD (+3), 100 ms

| Byte | Signal | Type | Scaling |
|---|---|---|---|
| 0-1 | vin | u16 | 1 mV/bit |
| 2-3 | imu_temp | s16 | 0.01 °C/bit |
| 4-5 | uptime | u16 | 1 s/bit (wraps at 65535 s) |

### DIAG (+4), 1000 ms

| Byte | Signal | Meaning |
|---|---|---|
| 0 | TEC | FDCAN transmit error counter |
| 1 | REC | FDCAN receive error counter |
| 2 | proto_flags | bit0 error-warning, bit1 error-passive, bit2 bus-off, bits 3-5 last error code (LEC) |
| 3 | busoff_count | saturating at 255 |
| 4 | e2e_errors | received CRC/DLC/repeat errors since last clear (saturating) |
| 5 | reset_cause | 0 unknown, 1 power-on/BOR, 2 pin, 3 software, 4 IWDG, 5 WWDG, 6 low-power, 7 option-byte |

### COMMAND (0x0F0 + target, or 0x0FF broadcast)

| Byte | Signal | Values |
|---|---|---|
| 0 | command | 1 IDENTIFY (STATUS LED blinks fast for 3 s), 2 CLEAR_FAULTS (clear latched fault history) |
| 1 | source node | 0..3, 0x0F = PC tool |
| 2 | argument | reserved (0) |
| 3-5 | reserved | 0 |
| 6-7 | counter / CRC | as for all frames |

A short press of the USER button sends IDENTIFY broadcast. A long press (≥ 2 s) clears local faults and broadcasts CLEAR_FAULTS.

## Fault bits (heartbeat bytes 2-3)

| Bit | Name | Set when | Cleared when |
|---:|---|---|---|
| 0 | IMU_COMM | WHO_AM_I wrong / I2C error | IMU re-init succeeds (retried every 1 s) |
| 1 | IMU_DATA | 50 identical samples (stuck) or all-zero accel | data plausible again |
| 2 | CAN_BUSOFF | FDCAN bus-off (**critical → state FAULT**) | automatic recovery done |
| 3 | CAN_PASSIVE | error-passive (e.g. alone on the bus, no ACK) | counters decrease |
| 4 | PEER_TIMEOUT | a peer seen before sends no heartbeat for 300 ms | peer back |
| 5 | CAN_E2E | CRC / DLC / repeated-counter error received | 1 s without errors |
| 6 | VIN_LOW | VIN < 7.5 V | VIN > 7.8 V |
| 7 | VIN_HIGH | VIN > 18.5 V | VIN < 18.0 V |
| 8 | HSE | crystal failed (CSS) → running from HSI16 ±1 % | reset |
| 9 | WDG_RESET | last reset by watchdog (latched only) | CLEAR_FAULTS |
| 10 | CAN_TX_OVF | TX FIFO full, frame dropped | 1 s without overflow |
| 11 | MCU_TEMP | die temperature > 100 °C | < 100 °C |
| 12 | ID_CONFLICT | a frame with our own node ID was received | CLEAR_FAULTS/reset |

**State machine:**

* INIT: stays in INIT for at least 200 ms and until all drivers are initialised.
* FAULT: if any critical fault is active.
* DEGRADED: if any other fault is active.
* RUN: otherwise.

"Latched" faults (history since power-up or the last CLEAR_FAULTS) are shown by a slow FAULT-LED blink.

## Example frames (golden vectors, verified in C and Python)

```
0x110  01 01 00 00 01 10 03 3A   HEARTBEAT node 1, RUN, no faults, peers 0x01, fw 1.0, counter 3, CRC 0x3A
0x101  0C 00 DD FF E6 03 17 7E   ACCEL node 0: X = 12 mg, Y = -35 mg, Z = 998 mg, DATA_VALID, counter 7
```
