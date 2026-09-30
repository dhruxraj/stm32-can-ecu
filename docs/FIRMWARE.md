# Firmware

`firmware/` is an STM32Cube HAL project in C11 for the STM32G431CBT6. No RTOS is used.

## Module structure

| File | Responsibility |
|---|---|
| `Core/Src/main.c` | Start-up sequence, clock tree (HSE→PLL 170 MHz, HSI16 fallback, clock-security system), reset-cause capture, watchdog, main loop |
| `Core/Src/board.c` / `board.h` | Pin map, GPIO init (unused pins → analog), LEDs, button, node-ID jumpers, transceiver S pin, ADC (VIN, VREFINT, die temperature) |
| `Core/Src/can.c` / `can.h` | FDCAN1: 500 kbit/s timing, RX filters, interrupt RX into a lock-free ring buffer, TX FIFO queue, error counters, **bus-off recovery** |
| `Core/Src/can_protocol.c` / `.h` | Pure-C protocol: IDs, payload packing, rolling counter, CRC-8, receive checks, peer timeout (host unit-tested) |
| `Core/Src/imu.c` / `imu.h` | LSM6DS3TR-C: WHO_AM_I, soft reset, configuration, burst read, unit conversion, stuck/implausible detection, automatic re-init |
| `Core/Src/diagnostics.c` / `.h` | Fault bits, active/latched handling, VIN hysteresis, node state machine (host unit-tested) |
| `Core/Src/app.c` / `app.h` | Cooperative scheduler, CAN message handling, commands, LED patterns, button, UART status output |
| `Core/Src/debug.c` | USART2 115200 8N1 console; `printf` via `_write` |
| `Core/Src/stm32g4xx_it.c`, `stm32g4xx_hal_msp.c` | Interrupt handlers (SysTick, FDCAN1_IT0, NMI/CSS, faults) and peripheral clock/pin/NVIC setup |
| `Core/Inc/stm32g4xx_hal_conf.h` | HAL module selection, HSE_VALUE = 8 MHz |
| `STM32G431CBTX_FLASH.ld` | Linker script (128 KB flash, 32 KB RAM) |
| `CMakeLists.txt`, `cmake/` | arm-none-eabi-gcc build |
| `tests/` | Host unit tests + compile check of all sources against HAL stubs |

## Scheduler and timing

The scheduler runs on the 1 ms `HAL_GetTick()`, cooperatively and without blocking. All HAL calls have timeouts of 20 ms or less.

| Period | Work |
|---|---|
| 10 ms | drain CAN RX queue (max 16 frames), FDCAN status + bus-off recovery, fault flags, state machine, button, LEDs |
| 20 ms | IMU read (or re-init attempt once per second when faulty), ACCEL + GYRO frames |
| 100 ms | VIN measurement, peer heartbeat supervision (300 ms timeout), HEARTBEAT + BOARD frames |
| 1000 ms | MCU temperature, DIAG frame, one UART status line |

## Robustness features ("automotive-style", not certified)

* **Watchdog:**
  * The IWDG runs at about 1 s (LSI/32, reload 1000) and is frozen while the debugger halts the core.
  * It is refreshed only if the 10 ms task ran within the last 100 ms. A stuck loop, a HardFault or `Error_Handler()` therefore causes a reset.
  * A watchdog reset is latched as fault `WDG_RESET` and reported in DIAG.
* **Reset cause:** read from RCC_CSR at start-up and sent in DIAG.
* **Clock monitoring:**
  * If the crystal does not start, the PLL is built from HSI16 at the same 170 MHz, so the CAN timing is unchanged.
  * The clock security system (NMI) catches a crystal failure at run time.
  * Both cases set fault `HSE`, because HSI accuracy (±1 %) is marginal for CAN.
* **CAN bus handling:**
  * RX filters accept only 0x100-0x13F plus own and broadcast commands.
  * Error-warning, error-passive and bus-off are monitored.
  * Bus-off is recovered automatically: after 100 ms the firmware clears CCCR.INIT, and the controller then waits for 128×11 recessive bits.
  * The TX FIFO fill level is checked before sending; overflow is flagged.
  * The transceiver stays silent until FDCAN is running.
* **End-to-end-style checks:** rolling counter + CRC-8 on every frame, DLC check, repeated-frame detection, lost-frame counting, 300 ms heartbeat timeout per peer, detection of a second node with the same ID.
* **Sensor faults:**
  * WHO_AM_I and register read-back at init.
  * I2C error counting.
  * Stuck-data detection (50 identical samples) and all-zero detection.
  * Automatic re-initialisation every 1 s.
  * Invalid data is still transmitted but marked `DATA_VALID = 0` / `SENSOR_FAULT = 1`.
* **Supply monitoring:** VIN is measured against VREFINT with hysteresis, and the die temperature is checked.

## LED indication

| LED | Pattern | Meaning |
|---|---|---|
| PWR (D3, green) | on | +5 V present |
| STATUS (D4, green) | 5 Hz blink | INIT |
| | 1 Hz short flash | RUN |
| | 2 Hz blink | DEGRADED |
| | off | FAULT |
| | 10 Hz for 3 s | IDENTIFY received |
| FAULT (D5, red) | on | active fault |
| | short flash every 2 s | only latched (past) faults |
| | off | no faults |
| CAN TX (D6) | flicker | frame transmitted |
| CAN RX (D7) | flicker | frame received |

## Building

### Option A - CMake + GNU Arm toolchain (Linux/macOS/Windows)

```bash
cd firmware
./scripts/fetch_st_drivers.sh        # clones ST's HAL + CMSIS from github.com/STMicroelectronics
cmake -B build -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake -DCMAKE_BUILD_TYPE=Debug
cmake --build build                  # -> build/can_ecu.elf, .hex, .bin
```

Requires `arm-none-eabi-gcc` (Arm GNU Toolchain 12 or newer), CMake ≥ 3.20 and git.

### Option B - STM32CubeIDE

1. Go to **File → New → STM32 Project**, pick **STM32G431CBTx**, and choose an empty C project with the STM32Cube firmware package.
2. Delete the generated `Core/Src/main.c` and `Core/Inc/main.h`.
3. Copy every file from `firmware/Core/Inc` and `firmware/Core/Src` into the project's `Core/Inc` and `Core/Src`, overwriting `stm32g4xx_hal_conf.h`, `stm32g4xx_it.*` and `stm32g4xx_hal_msp.c`.
4. Make sure the HAL drivers for ADC, FDCAN, I2C, IWDG and UART are present in `Drivers/STM32G4xx_HAL_Driver`. Copy them from the STM32CubeG4 package if the wizard did not add them.
5. Delete CubeIDE's `syscalls.c` **or** our `_write()` in `debug.c`. Keep only one `_write`.
6. Build with Project → Build, then Run → Debug with the ST-LINK.

### Host tests (any PC with gcc)

```bash
make -C firmware/tests      # 60 unit checks (ASan/UBSan) + stub-HAL compile of every source file
python3 tools/test_tools.py # Python decoder == C golden vectors, DBC layout check
```

> **Honest status:** the protocol, diagnostics and IMU-conversion logic were compiled and unit-tested on a PC. Every other source file was compiled with `-Wall -Wextra -Werror` against a minimal HAL *stub*. The firmware was **not** built with arm-none-eabi-gcc against the real ST HAL, and not run on hardware, in the generation environment. Expect possible small compile fixes if your HAL version differs; the code avoids version-specific details (for example, `DataLength` is handled for both HAL encodings).

## Programming

1. Connect an ST-LINK V2/V3 (or a Nucleo board's ST-LINK with its CN2 jumpers removed) to **J4**:

   | J4 pin | Signal |
   |---|---|
   | 1 | VDD_TARGET (sense only) |
   | 2 | SWCLK |
   | 3 | GND |
   | 4 | SWDIO |
   | 5 | NRST |
   | 6 | SWO |

   Pin 1 is the square pad.
2. Power the board from J1 (12 V). The ST-LINK does **not** power the board.
3. Flash:
   * **STM32CubeProgrammer:** `STM32_Programmer_CLI -c port=SWD mode=UR -w build/can_ecu.hex -v -rst`
   * **OpenOCD:** `openocd -f interface/stlink.cfg -f target/stm32g4x.cfg -c "program build/can_ecu.elf verify reset exit"`
   * **CubeIDE:** Run/Debug.
4. Console: connect a 3.3 V USB-UART to J5.
   * J5 pin 3 (board TX) → adapter RX.
   * J5 pin 4 (board RX) ← adapter TX.
   * J5 pin 2 → GND.
   * Settings: 115200 8N1.

**Fallback without ST-LINK:**

1. Close JP1 (BOOT0) and reset.
2. Use STM32CubeProgrammer over UART on PA2/PA3: `-c port=/dev/ttyUSB0`. USART2 is a bootloader interface on G431 — **verify against ST AN2606 (STM32G431 section)**.
3. Open JP1 again afterwards.
