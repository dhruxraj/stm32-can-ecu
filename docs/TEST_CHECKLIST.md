# Test checklist (tick per board)

Board S/N: ______  Node ID: ___  Date: ______  Tester: ______

## Assembly / visual
- [ ] Correct orientation: U1, U2, U3 (pin 1), U4 (pin 1), U5 (pin 1), D1, D2, D3-D8, C2 (+)
- [ ] No solder bridges on U3 (LQFP48) and U4; U5 (LGA) centred, no visible bridging
- [ ] JP1 open, JP3/JP4 set to the planned node ID, JP2 shunts only on end-of-bus boards

## Power (supply current limit 150 mA)
- [ ] No short: TP3/TP4/TP5 to GND resistance OK
- [ ] 12 V input current (blank MCU) ______ mA (expect 5-25 mA)
- [ ] TP4 +5V = ______ V (4.9-5.1)   - [ ] TP5 +3V3 = ______ V (3.25-3.35)
- [ ] VDDA (C12) ≈ 3.3 V
- [ ] 8 V and 18 V input: +5 V and +3V3 in tolerance
- [ ] Reverse polarity 12 V (limited): board survives, PTC recovers (sample test)

## Programming / MCU
- [ ] ST-LINK connects, device ID 0x468
- [ ] Firmware flashed and verified
- [ ] UART banner shows `clock HSE 8 MHz`
- [ ] Reset button restarts (banner, reset cause 2)
- [ ] BOOT0 jumper closed → ROM bootloader answers (optional)

## Peripherals
- [ ] IMU WHO_AM_I = 0x6A, accel magnitude ≈ 1000 mg at rest, axes follow tilt
- [ ] Gyro ≈ 0 at rest (|x|,|y|,|z| < 3 dps), reacts to rotation
- [ ] VIN reading within ±3 % of the supply
- [ ] All LEDs work: PWR, STATUS, FAULT, CAN-TX, CAN-RX
- [ ] USER short press → IDENTIFY sent; long press → faults cleared

## CAN (with a second board or USB-CAN adapter)
- [ ] CANH-CANL resistance (power off): ______ Ω (≈60 Ω on a correctly terminated bus)
- [ ] Peer detected, both nodes RUN, TEC = REC = 0
- [ ] Frames 0x1n0-0x1n4 visible at the expected rates (tools/can_monitor.py), 0 CRC errors, 0 lost frames over 60 s
- [ ] IDENTIFY command works in both directions
- [ ] Cable unplugged → PEER_TIMEOUT within 300 ms, automatic recovery on replug
- [ ] Short CANH-CANL → bus-off → automatic recovery, busoff_count incremented
- [ ] Watchdog: (debug build) halt loop via debugger with IWDG unfrozen → reset cause 4, WDG_RESET latched

Result: PASS / FAIL   Notes: ____________________________________________
