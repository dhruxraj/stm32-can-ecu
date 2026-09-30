# MCU pin mapping - STM32G431CBT6 (LQFP48)

Generated from `hardware/gen/design.py` (single source of truth for schematic, PCB and firmware `Core/Inc/board.h`). Pin numbers/names were checked against ST datasheet DS12589 (LQFP48 pinout). Unused pins are unconnected on the PCB and configured as analog inputs by the firmware.

| Pin | Name | Net | Function |
|---:|---|---|---|
| 1 | VBAT | +3V3 | +3V3 (no backup battery), 100 nF |
| 2 | PC13 | USER_BTN | USER button SW2 (active low, ext. 10k pull-up) |
| 3 | PC14-OSC32_IN | - | not connected (analog input) |
| 4 | PC15-OSC32_OUT | - | not connected (analog input) |
| 5 | PF0-OSC_IN | OSC_IN | HSE 8 MHz crystal Y1 |
| 6 | PF1-OSC_OUT | OSC_OUT | HSE 8 MHz crystal Y1 |
| 7 | PG10-NRST | NRST | Reset: SW1, C15 100 nF, SWD pin 5 |
| 8 | PA0 | VIN_SENSE | ADC1_IN1 - VIN sense divider 100k/15k |
| 9 | PA1 | - | not connected (analog input) |
| 10 | PA2 | UART_TX | USART2_TX (AF7) debug console -> J5.3 |
| 11 | PA3 | UART_RX | USART2_RX (AF7) debug console -> J5.4 |
| 12 | PA4 | EXP_PA4 | Expansion J5.5 (GPIO/ADC/DAC) |
| 13 | PA5 | EXP_PA5 | Expansion J5.6 |
| 14 | PA6 | EXP_PA6 | Expansion J5.7 |
| 15 | PA7 | EXP_PA7 | Expansion J5.8 |
| 16 | PB0 | EXP_PB0 | Expansion J5.9 |
| 17 | PB1 | - | not connected (analog input) |
| 18 | PB2 | - | not connected (analog input) |
| 19 | VSSA | GND | GND |
| 20 | VREF+ | +3V3A | +3V3A, 100 nF |
| 21 | VDDA | +3V3A | +3V3A (ferrite FB1 + 1 uF + 100 nF) |
| 22 | PB10 | NODE_ID0 | NODE_ID bit0 - solder jumper JP3 to GND (internal pull-up) |
| 23 | VSS | GND | GND |
| 24 | VDD | +3V3 | +3V3, 100 nF per pin + 4.7 uF bulk |
| 25 | PB11 | NODE_ID1 | NODE_ID bit1 - solder jumper JP4 to GND (internal pull-up) |
| 26 | PB12 | LED_STATUS | LED STATUS (green) via 680R |
| 27 | PB13 | LED_FAULT | LED FAULT (red) via 680R |
| 28 | PB14 | LED_CANTX | LED CAN-TX (yellow) via 680R |
| 29 | PB15 | LED_CANRX | LED CAN-RX (orange) via 680R |
| 30 | PA8 | CAN_S | CAN transceiver S (silent) - 10k pull-up, LOW = normal |
| 31 | PA9 | - | not connected (analog input) |
| 32 | PA10 | - | not connected (analog input) |
| 33 | PA11 | CAN_RX | FDCAN1_RX (AF9) <- TJA1051 RXD |
| 34 | PA12 | CAN_TX | FDCAN1_TX (AF9) -> TJA1051 TXD |
| 35 | VSS | GND | GND |
| 36 | VDD | +3V3 | +3V3, 100 nF per pin + 4.7 uF bulk |
| 37 | PA13 | SWDIO | SWDIO (J4.4) |
| 38 | PA14 | SWCLK | SWCLK (J4.2) |
| 39 | PA15 | I2C_SCL | I2C1_SCL (AF4) - IMU, 4k7 pull-up |
| 40 | PB3 | SWO | SWO trace output (J4.6) |
| 41 | PB4 | - | not connected (analog input) |
| 42 | PB5 | IMU_INT1 | IMU INT1 (accel data-ready) |
| 43 | PB6 | - | not connected (analog input) |
| 44 | PB7 | I2C_SDA | I2C1_SDA (AF4) - IMU, 4k7 pull-up |
| 45 | PB8-BOOT0 | BOOT0 | BOOT0: 10k pull-down, JP1 to 3V3 = system bootloader |
| 46 | PB9 | IMU_INT2 | IMU INT2 (spare) |
| 47 | VSS | GND | GND |
| 48 | VDD | +3V3 | +3V3, 100 nF per pin + 4.7 uF bulk |

## Alternate-function summary

| Peripheral | Signal | Pin | AF |
|---|---|---|---|
| FDCAN1 | RX | PA11 | AF9 |
| FDCAN1 | TX | PA12 | AF9 |
| I2C1 | SCL | PA15 | AF4 |
| I2C1 | SDA | PB7 | AF4 |
| USART2 | TX | PA2 | AF7 |
| USART2 | RX | PA3 | AF7 |
| SWD | SWDIO / SWCLK / SWO | PA13 / PA14 / PB3 | AF0 (reset default) |
| ADC1 | IN1 (VIN sense) | PA0 | analog |

**Why no USB:** on the STM32G431 the only FDCAN1 pin pair that does not collide with other functions here is PA11/PA12 - the same pins as USB DM/DP. The alternative FDCAN1 pins PB8/PB9 would put CAN RX on the BOOT0 pin (PB8), which is a known source of boot problems. Rev A therefore uses PA11/PA12 for CAN and provides a 3.3 V UART on J5 instead of USB.

## Connectors

### J1 - Power input (5.08 mm screw terminal)

| Pin | Net |
|---:|---|
| 1 | VIN_RAW |
| 2 | GND |

### J2 - CAN bus A (5.08 mm, 3-pole)

| Pin | Net |
|---:|---|
| 1 | CANH |
| 2 | CANL |
| 3 | GND |

### J3 - CAN bus B (5.08 mm, 3-pole, parallel to J2 for daisy-chaining)

| Pin | Net |
|---:|---|
| 1 | CANH |
| 2 | CANL |
| 3 | GND |

### J4 - SWD debug (1x6 2.54 mm, ST-LINK/Nucleo CN4 order)

| Pin | Net |
|---:|---|
| 1 | +3V3 |
| 2 | SWCLK |
| 3 | GND |
| 4 | SWDIO |
| 5 | NRST |
| 6 | SWO |

### J5 - Expansion / UART (2x5 2.54 mm)

| Pin | Net |
|---:|---|
| 1 | +3V3 |
| 2 | GND |
| 3 | UART_TX |
| 4 | UART_RX |
| 5 | EXP_PA4 |
| 6 | EXP_PA5 |
| 7 | EXP_PA6 |
| 8 | EXP_PA7 |
| 9 | EXP_PB0 |
| 10 | GND |

### JP2 - CAN termination (2x2 2.54 mm, fit 2 shunts: 1-3 and 2-4)

| Pin | Net |
|---:|---|
| 1 | TERM_H |
| 2 | TERM_L |
| 3 | TERM_MID |
| 4 | TERM_MID |

## Jumpers

| Ref | Function | Open (default) | Closed |
|---|---|---|---|
| JP1 | BOOT0 | boot from flash | ST system bootloader (UART/FDCAN/I2C/SPI) |
| JP2 | CAN termination (2 shunts) | no termination | 2 x 60.4 R split + 4.7 nF |
| JP3 | NODE_ID bit 0 (PB10) | 0 | 1 |
| JP4 | NODE_ID bit 1 (PB11) | 0 | 1 |

Node ID = JP4*2 + JP3 -> 0..3. Two boards must have **different** node IDs (e.g. board A: both open = node 0; board B: JP3 closed = node 1).
