# Component and footprint list

Generated from `hardware/gen/design.py` and `lib.py`. All footprints live in the project library `hardware/kicad/CAN_ECU.pretty` (self-contained project); the column *KiCad std* names the equivalent footprint in KiCad's official libraries, which you may swap in. Rows marked **VERIFY** must be checked against the manufacturer drawing of the exact part you buy before ordering PCBs.

## Components

| Ref | Value | Part / specification | Footprint | Function |
|---|---|---|---|---|
| C1 | 10uF 50V X7R | -  | C_1210_3225Metric | Input ceramic 10 uF 50 V X7R 1210 |
| C2 | 47uF 35V | 47 uF 35 V aluminium electrolytic, D6.3 mm, P2.5 mm, low-ESR  | CP_Radial_D6.3mm_P2.50mm | Input bulk / damping capacitor |
| C3 | 10uF 16V X5R | -  | C_0805_2012Metric | 5 V rail output capacitor 0805 |
| C4 | 1uF 16V X7R | -  | C_0603_1608Metric | LDO input capacitor |
| C5 | 10uF 10V X5R | -  | C_0805_2012Metric | LDO output capacitor |
| C6 | 100nF | -  | C_0603_1608Metric | Ceramic capacitor 100nF, 0603 |
| C7 | 100nF | -  | C_0603_1608Metric | VDD pin 48 decoupling |
| C8 | 100nF | -  | C_0603_1608Metric | VDD pin 36 decoupling |
| C9 | 100nF | -  | C_0603_1608Metric | VDD pin 24 decoupling |
| C10 | 4.7uF 10V X5R | -  | C_0805_2012Metric | VDD bulk |
| C11 | 100nF | -  | C_0603_1608Metric | VBAT decoupling |
| C12 | 1uF 16V X7R | -  | C_0603_1608Metric | VDDA bulk |
| C13 | 100nF | -  | C_0603_1608Metric | VDDA decoupling |
| C14 | 100nF | -  | C_0603_1608Metric | VREF+ decoupling |
| C15 | 100nF | -  | C_0603_1608Metric | NRST filter |
| C16 | 15pF C0G | -  | C_0603_1608Metric | HSE load cap (for CL = 12 pF crystal) |
| C17 | 15pF C0G | -  | C_0603_1608Metric | HSE load cap (for CL = 12 pF crystal) |
| C18 | 100nF | -  | C_0603_1608Metric | User button debounce |
| C19 | 100nF | -  | C_0603_1608Metric | Transceiver VCC decoupling |
| C20 | 100nF | -  | C_0603_1608Metric | Transceiver VIO decoupling |
| C21 | 4.7uF 16V X5R | -  | C_0805_2012Metric | Transceiver VCC bulk |
| C22 | 4.7nF 50V | -  | C_0603_1608Metric | Split termination common-mode capacitor |
| C23 | 100nF | -  | C_0603_1608Metric | IMU VDD decoupling |
| C24 | 100nF | -  | C_0603_1608Metric | IMU VDDIO decoupling |
| D1 | SMBJ18A | SMBJ18A (Littelfuse) | D_SMB | 600 W unidirectional TVS, VRWM 18 V, SMB |
| D2 | SS34 | SS34 (onsemi/various) | D_SMA | 3 A 40 V Schottky, reverse-polarity protection, SMA |
| D3 | GREEN PWR | 0603 green LED, Vf~2.0 V  | LED_0603_1608Metric | Power indicator (5 V rail) |
| D4 | GREEN STATUS | 0603 green LED  | LED_0603_1608Metric | STATUS indicator |
| D5 | RED FAULT | 0603 red LED  | LED_0603_1608Metric | FAULT indicator |
| D6 | YELLOW CAN-TX | 0603 yellow LED  | LED_0603_1608Metric | CAN-TX indicator |
| D7 | ORANGE CAN-RX | 0603 orange LED  | LED_0603_1608Metric | CAN-RX indicator |
| D8 | PESD1CAN | PESD1CAN,215 (Nexperia) | SOT-23 | CAN bus ESD protection, SOT-23 (verify pinout: 1,2 = bus lines, 3 = GND) |
| F1 | PTC 0.5A/30V | 1812 PTC, Ihold 0.5 A, Vmax >= 30 V (e.g. Bourns MF-MSMF series - select 30 V rated) (Bourns/Littelfuse) | Fuse_1812_4532Metric | Resettable PTC fuse, 1812 |
| FB1 | 600R@100MHz | BLM18AG601SN1D (or equiv. 0603 bead, >=200 mA) (Murata) | L_0603_1608Metric | VDDA filter bead |
| H1 | M3 | - (-) | MountingHole_3.2mm_M3 | M3 mounting hole (NPTH) |
| H2 | M3 | - (-) | MountingHole_3.2mm_M3 | M3 mounting hole (NPTH) |
| H3 | M3 | - (-) | MountingHole_3.2mm_M3 | M3 mounting hole (NPTH) |
| H4 | M3 | - (-) | MountingHole_3.2mm_M3 | M3 mounting hole (NPTH) |
| J1 | PWR_IN 8-18V | 1729128 (MKDS 1,5/ 2-5,08) or equivalent (Phoenix Contact) | TerminalBlock_1x02_P5.08mm_Horizontal | 2-pos 5.08 mm PCB screw terminal, power input (1 = +VIN, 2 = GND) |
| J2 | CAN | 1729131 (MKDS 1,5/ 3-5,08) or equivalent (Phoenix Contact) | TerminalBlock_1x03_P5.08mm_Horizontal | CAN bus connector (1 = CANH, 2 = CANL, 3 = GND); J2/J3 are paralleled for daisy-chain |
| J3 | CAN | 1729131 (MKDS 1,5/ 3-5,08) or equivalent (Phoenix Contact) | TerminalBlock_1x03_P5.08mm_Horizontal | CAN bus connector (1 = CANH, 2 = CANL, 3 = GND); J2/J3 are paralleled for daisy-chain |
| J4 | SWD | 1x6 2.54 mm pin header  | PinHeader_1x06_P2.54mm_Vertical | SWD: 1 VDD_TARGET, 2 SWCLK, 3 GND, 4 SWDIO, 5 NRST, 6 SWO (Nucleo CN4 order) |
| J5 | EXPANSION | 2x5 2.54 mm pin header  | PinHeader_2x05_P2.54mm_Vertical | Expansion / debug UART (USART2) |
| JP1 | BOOT0 | - (-) | SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm | Close to force ST system bootloader |
| JP2 | CAN_TERM | 2x2 2.54 mm header + 2 jumper shunts  | PinHeader_2x02_P2.54mm_Vertical | Termination enable: fit BOTH shunts (1-3 and 2-4) on end-of-bus nodes only |
| JP3 | NODE_ID0 | - (-) | SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm | Node-ID bit 0 (closed = 1) |
| JP4 | NODE_ID1 | - (-) | SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm | Node-ID bit 1 (closed = 1) |
| R1 | 1k5 | -  | R_0603_1608Metric | Resistor 1k5, 0603, 1%, thick film |
| R2 | 100k 1% | -  | R_0603_1608Metric | VIN divider top, 1% |
| R3 | 15k 1% | -  | R_0603_1608Metric | VIN divider bottom, 1% |
| R4 | 10k | -  | R_0603_1608Metric | BOOT0 pull-down (boot from Flash) |
| R5 | 10k | -  | R_0603_1608Metric | User button pull-up |
| R6 | 680R | -  | R_0603_1608Metric | Resistor 680R, 0603, 1%, thick film |
| R7 | 680R | -  | R_0603_1608Metric | Resistor 680R, 0603, 1%, thick film |
| R8 | 680R | -  | R_0603_1608Metric | Resistor 680R, 0603, 1%, thick film |
| R9 | 680R | -  | R_0603_1608Metric | Resistor 680R, 0603, 1%, thick film |
| R10 | 10k | -  | R_0603_1608Metric | Transceiver S pull-up: SILENT until firmware enables |
| R11 | 60R4 1% | -  | R_0805_2012Metric | Split termination 60.4R 0805 |
| R12 | 60R4 1% | -  | R_0805_2012Metric | Split termination 60.4R 0805 |
| R13 | 4k7 | -  | R_0603_1608Metric | I2C SCL pull-up |
| R14 | 4k7 | -  | R_0603_1608Metric | I2C SDA pull-up |
| SW1 | RESET | 6x6 mm THT tactile switch  | SW_PUSH_6mm | Reset push-button |
| SW2 | USER | 6x6 mm THT tactile switch  | SW_PUSH_6mm | User push-button |
| TP1 | CANH | - (-) | TestPoint_Pad_D1.5mm | Test pad CANH |
| TP2 | CANL | - (-) | TestPoint_Pad_D1.5mm | Test pad CANL |
| TP3 | VIN_PROT | - (-) | TestPoint_Pad_D1.5mm | Test pad VIN_PROT |
| TP4 | +5V | - (-) | TestPoint_Pad_D1.5mm | Test pad +5V |
| TP5 | +3V3 | - (-) | TestPoint_Pad_D1.5mm | Test pad +3V3 |
| TP6 | GND | - (-) | TestPoint_Pad_D1.5mm | Test pad GND |
| TP7 | CAN_TX | - (-) | TestPoint_Pad_D1.5mm | Test pad CAN_TX |
| TP8 | CAN_RX | - (-) | TestPoint_Pad_D1.5mm | Test pad CAN_RX |
| U1 | R-78E5.0-0.5 | R-78E5.0-0.5 (RECOM) | Converter_DCDC_RECOM_R-78E-0.5_THT | 5 V 0.5 A non-isolated switching regulator module, 7-28 V in, SIP-3 |
| U2 | AP2112K-3.3 | AP2112K-3.3TRG1 (Diodes Inc.) | SOT-23-5 | 3.3 V 600 mA LDO, SOT-23-5 |
| U3 | STM32G431CBT6 | STM32G431CBT6 (STMicroelectronics) | LQFP-48_7x7mm_P0.5mm | Cortex-M4F 170 MHz, 128 KB Flash, 32 KB RAM, FDCAN, LQFP48 |
| U4 | TJA1051T/3 | TJA1051T/3,118 (NXP) | SOIC-8_3.9x4.9mm_P1.27mm | High-speed CAN (FD) transceiver with VIO, SO8. Must be the /3 (VIO) variant! |
| U5 | LSM6DS3TR-C | LSM6DS3TR-C (STMicroelectronics) | LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y | 6-axis IMU (accel + gyro), I2C addr 0x6A |
| Y1 | 8MHz CL12pF | 8.000 MHz, 3225 4-pad, +-20 ppm, CL = 12 pF (ESR <= 100R)  | Crystal_SMD_3225-4Pin_3.2x2.5mm | HSE crystal for accurate CAN bit timing |

## Footprints

| Project footprint | KiCad std equivalent | Type | Used by | Verification note |
|---|---|---|---|---|
| R_0603_1608Metric | Resistor_SMD:R_0603_1608Metric | smd | R1 R2 R3 R4 R5 R6 R7 R8 R9 R10 R13 R14 | Standard generic land pattern. |
| C_0603_1608Metric | Capacitor_SMD:C_0603_1608Metric | smd | C4 C6 C7 C8 C9 C11 C12 C13 C14 C15 C16 C17 C18 C19 C20 C22 C23 C24 | Standard generic land pattern. |
| L_0603_1608Metric | Inductor_SMD:L_0603_1608Metric | smd | FB1 | Standard generic land pattern. |
| C_0805_2012Metric | Capacitor_SMD:C_0805_2012Metric | smd | C3 C5 C10 C21 | Standard generic land pattern. |
| R_0805_2012Metric | Resistor_SMD:R_0805_2012Metric | smd | R11 R12 | Standard generic land pattern. |
| C_1210_3225Metric | Capacitor_SMD:C_1210_3225Metric | smd | C1 | Standard generic land pattern. |
| Fuse_1812_4532Metric | Fuse:Fuse_1812_4532Metric | smd | F1 | Generic 1812 PTC land pattern. |
| D_SMA | Diode_SMD:D_SMA | smd | D2 | Standard generic land pattern. |
| D_SMB | Diode_SMD:D_SMB | smd | D1 | Standard generic land pattern. |
| LED_0603_1608Metric | LED_SMD:LED_0603_1608Metric | smd | D3 D4 D5 D6 D7 | Standard generic land pattern. |
| SOIC-8_3.9x4.9mm_P1.27mm | Package_SO:SOIC-8_3.9x4.9mm_P1.27mm | smd | U4 | Standard JEDEC MS-012 land pattern. |
| LQFP-48_7x7mm_P0.5mm | Package_QFP:LQFP-48_7x7mm_P0.5mm | smd | U3 | Generated to IPC-7351-like dimensions (pads 1.475 x 0.3 at +-4.1625). Compare with KiCad Package_QFP:LQFP-48_7x7mm_P0.5mm. |
| SOT-23 | Package_TO_SOT_SMD:SOT-23 | smd | D8 | **VERIFY** PESD1CAN pinout (1 = CANH/line, 2 = CANL/line, 3 = common) - symmetric part, swapping 1/2 is harmless. |
| SOT-23-5 | Package_TO_SOT_SMD:SOT-23-5 | smd | U2 | AP2112K SOT-23-5 pinout checked (1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT). |
| LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y | Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y | smd | U5 | **VERIFY** against ST LSM6DS3TR-C land-pattern recommendation (pads 0.5 x 0.25 mm). Pin-1 orientation is critical. |
| Crystal_SMD_3225-4Pin_3.2x2.5mm | Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm | smd | Y1 | Standard 3225 4-pad; confirm pad 1/3 = crystal, 2/4 = GND for the chosen part. |
| TerminalBlock_1x02_P5.08mm_Horizontal | TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal | through_hole | J1 | **VERIFY** hole size/pitch vs. the terminal block actually bought (Phoenix MKDS 1,5/2-5,08 style). |
| TerminalBlock_1x03_P5.08mm_Horizontal | TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal | through_hole | J2 J3 | **VERIFY** as above (3-pole). |
| PinHeader_1x06_P2.54mm_Vertical | Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical | through_hole | J4 | Standard generic land pattern. |
| PinHeader_2x05_P2.54mm_Vertical | Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical | through_hole | J5 | Standard generic land pattern. |
| PinHeader_2x02_P2.54mm_Vertical | Connector_PinHeader_2.54mm:PinHeader_2x02_P2.54mm_Vertical | through_hole | JP2 | Standard generic land pattern. |
| SW_PUSH_6mm | Button_Switch_THT:SW_PUSH_6mm | through_hole | SW1 SW2 | Standard generic land pattern. |
| Converter_DCDC_RECOM_R-78E-0.5_THT | Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT | through_hole | U1 | **VERIFY** pin pitch (2.54 mm) and body side against the RECOM drawing; 6.5 mm keep-out reserved both sides. |
| CP_Radial_D6.3mm_P2.50mm | Capacitor_THT:CP_Radial_D6.3mm_P2.50mm | through_hole | C2 | Standard generic land pattern. |
| SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm | Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm | smd | JP1 JP3 JP4 | Standard generic land pattern. |
| TestPoint_Pad_D1.5mm | TestPoint:TestPoint_Pad_D1.5mm | smd | TP1 TP2 TP3 TP4 TP5 TP6 TP7 TP8 | Standard generic land pattern. |
| MountingHole_3.2mm_M3 | MountingHole:MountingHole_3.2mm_M3 | exclude | H1 H2 H3 H4 | Standard generic land pattern. |

## BOM

See `hardware/fab/BOM.csv` (grouped, with rough cost estimates).
