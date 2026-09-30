# Validation report

KiCad itself was **not available** in the environment where this design was generated, so KiCad's own ERC/DRC could not be run. Instead the checks below were implemented independently and run on the generated data and files. **Run KiCad ERC and DRC yourself before ordering** (see docs/MANUFACTURING.md).

## 1. PCB design-rule and connectivity check (hardware/gen/checks.py)

Rules: copper clearance 0.20 mm, copper-edge 0.30 mm, hole-hole 0.25 mm, min track 0.20 mm, no via-in-pad, courtyard overlap, full net connectivity including the In1 (GND) / In2 (+3V3) planes (raster flood-fill with 0.25 mm antipads).

```
DRC violations      : 0
Courtyard issues    : []
Unconnected nets    : 0
Netlist issues      : []
Plane copper islands: {'In1.Cu': 1, 'In2.Cu': 3} | members per island: {'In1.Cu': {1: 58}, 'In2.Cu': {1: 25}}
Tracks: 384 Vias: 103
```

Note: In2.Cu shows small isolated copper islands with no +3V3 connection; KiCad removes these automatically when zones are filled (default island removal).

## 2. Generated-file check (hardware/gen/validate_files.py)

Re-parses the KiCad files: S-expression syntax of every file, schematic connectivity rebuilt from wires / labels / pin positions and compared net-by-net with the design netlist, ERC subset (unconnected pins, undriven power inputs, conflicting outputs/labels, single-pin nets), PCB pad nets vs. schematic, closed board outline, silkscreen vs. pads / edge / other text.

```
  sch_symbols80
  sch_nets         46
  sch_wires        216
  sch_labels       216
  sch_noconnect    12
  pcb_footprints   77
  pcb_segments     384
  pcb_vias         103
  pcb_zones        4
  pcb_nets         46
  silk_texts       96
ERRORS: 0
```

## 3. Firmware host tests (firmware/tests)

```
make: Entering directory '/home/claude/stm32-can-ecu/firmware/tests'
cc -std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -DUNIT_TEST -I../Core/Inc -fsanitize=address,undefined -o test_runner test_main.c ../Core/Src/can_protocol.c ../Core/Src/diagnostics.c ../Core/Src/imu.c
./test_runner
VECTOR 0x110 01 01 00 00 01 10 03 3A
VECTOR 0x101 0C 00 DD FF E6 03 17 7E
60 checks passed, 0 failed
  stub-compiled ../Core/Src/app.c
  stub-compiled ../Core/Src/board.c
  stub-compiled ../Core/Src/can.c
  stub-compiled ../Core/Src/can_protocol.c
  stub-compiled ../Core/Src/debug.c
  stub-compiled ../Core/Src/diagnostics.c
  stub-compiled ../Core/Src/imu.c
  stub-compiled ../Core/Src/main.c
  stub-compiled ../Core/Src/stm32g4xx_hal_msp.c
  stub-compiled ../Core/Src/stm32g4xx_it.c
make: Leaving directory '/home/claude/stm32-can-ecu/firmware/tests'
```

## 4. PC tools self-test (tools/test_tools.py)

```
tools self-test: 178 checks passed
```

## What could NOT be verified here

* KiCad ERC/DRC and zone filling (file format written for KiCad 7; opens in KiCad 7/8/9).
* A real `arm-none-eabi-gcc` build against the ST HAL (only a stub-HAL compile check was possible). Build it with the CMake project or STM32CubeIDE - see docs/FIRMWARE.md.
* Signal integrity / EMC, thermal behaviour, crystal start-up margin - require hardware measurement.
* Footprints marked VERIFY in docs/COMPONENTS.md against the exact purchased parts.
