"""
design.py - the electrical design: parts, values, footprints, pin->net mapping.
This is the single source of truth. The schematic, PCB, BOM and pin-map
documents are all generated from it.
"""

PROJECT = "CAN_ECU"
REV = "A"
TITLE = "STM32G4 CAN ECU development board"

NC = None   # marker for an intentionally unconnected pin


class Part:
    def __init__(self, ref, sym, value, fp, pins, mpn="", mfr="", desc="", dnp=False, group=""):
        self.ref, self.sym, self.value, self.fp = ref, sym, value, fp
        self.pins = pins            # {pin_number(str): net_name or None}
        self.mpn, self.mfr, self.desc, self.dnp, self.group = mpn, mfr, desc, dnp, group


P = []


def add(*a, **k):
    p = Part(*a, **k)
    P.append(p)
    return p


def R(ref, val, a, b, fp="R_0603_1608Metric", mpn="", desc="", group=""):
    return add(ref, "R", val, fp, {"1": a, "2": b}, mpn=mpn, mfr="any",
               desc=desc or f"Resistor {val}, {fp.split('_')[1]}, 1%, thick film", group=group)


def C(ref, val, a, b, fp="C_0603_1608Metric", mpn="", desc="", group=""):
    return add(ref, "C", val, fp, {"1": a, "2": b}, mpn=mpn, mfr="any",
               desc=desc or f"Ceramic capacitor {val}, {fp.split('_')[1]}", group=group)


# ------------------------------------------------------------------ POWER
add("J1", "Conn_01x02", "PWR_IN 8-18V", "TerminalBlock_1x02_P5.08mm_Horizontal",
    {"1": "VIN_RAW", "2": "GND"}, mpn="1729128 (MKDS 1,5/ 2-5,08) or equivalent", mfr="Phoenix Contact",
    desc="2-pos 5.08 mm PCB screw terminal, power input (1 = +VIN, 2 = GND)", group="power")
add("F1", "Polyfuse", "PTC 0.5A/30V", "Fuse_1812_4532Metric", {"1": "VIN_RAW", "2": "VIN_FUSED"},
    mpn="1812 PTC, Ihold 0.5 A, Vmax >= 30 V (e.g. Bourns MF-MSMF series - select 30 V rated)", mfr="Bourns/Littelfuse",
    desc="Resettable PTC fuse, 1812", group="power")
add("D1", "D_TVS", "SMBJ18A", "D_SMB", {"1": "VIN_FUSED", "2": "GND"}, mpn="SMBJ18A", mfr="Littelfuse",
    desc="600 W unidirectional TVS, VRWM 18 V, SMB", group="power")
add("D2", "D_Schottky", "SS34", "D_SMA", {"1": "VIN_PROT", "2": "VIN_FUSED"}, mpn="SS34", mfr="onsemi/various",
    desc="3 A 40 V Schottky, reverse-polarity protection, SMA", group="power")
C("C1", "10uF 50V X7R", "VIN_PROT", "GND", fp="C_1210_3225Metric", desc="Input ceramic 10 uF 50 V X7R 1210", group="power")
add("C2", "C_Polarized", "47uF 35V", "CP_Radial_D6.3mm_P2.50mm", {"1": "VIN_PROT", "2": "GND"},
    mpn="47 uF 35 V aluminium electrolytic, D6.3 mm, P2.5 mm, low-ESR", mfr="any",
    desc="Input bulk / damping capacitor", group="power")
add("U1", "R-78E5.0-0.5", "R-78E5.0-0.5", "Converter_DCDC_RECOM_R-78E-0.5_THT",
    {"1": "VIN_PROT", "2": "GND", "3": "+5V"}, mpn="R-78E5.0-0.5", mfr="RECOM",
    desc="5 V 0.5 A non-isolated switching regulator module, 7-28 V in, SIP-3", group="power")
C("C3", "10uF 16V X5R", "+5V", "GND", fp="C_0805_2012Metric", desc="5 V rail output capacitor 0805", group="power")
add("U2", "AP2112K-3.3", "AP2112K-3.3", "SOT-23-5", {"1": "+5V", "2": "GND", "3": "+5V", "4": NC, "5": "+3V3"},
    mpn="AP2112K-3.3TRG1", mfr="Diodes Inc.", desc="3.3 V 600 mA LDO, SOT-23-5", group="power")
C("C4", "1uF 16V X7R", "+5V", "GND", desc="LDO input capacitor", group="power")
C("C5", "10uF 10V X5R", "+3V3", "GND", fp="C_0805_2012Metric", desc="LDO output capacitor", group="power")
R("R1", "1k5", "+5V", "PWR_LED_A", group="power")
add("D3", "LED", "GREEN PWR", "LED_0603_1608Metric", {"2": "PWR_LED_A", "1": "GND"}, mpn="0603 green LED, Vf~2.0 V",
    mfr="any", desc="Power indicator (5 V rail)", group="power")
R("R2", "100k 1%", "VIN_PROT", "VIN_SENSE", group="power", desc="VIN divider top, 1%")
R("R3", "15k 1%", "VIN_SENSE", "GND", group="power", desc="VIN divider bottom, 1%")
C("C6", "100nF", "VIN_SENSE", "GND", group="power")

# ------------------------------------------------------------------ MCU
mcu_pins = {
    "1": "+3V3", "2": "USER_BTN", "3": NC, "4": NC, "5": "OSC_IN", "6": "OSC_OUT", "7": "NRST",
    "8": "VIN_SENSE", "9": NC, "10": "UART_TX", "11": "UART_RX", "12": "EXP_PA4", "13": "EXP_PA5",
    "14": "EXP_PA6", "15": "EXP_PA7", "16": "EXP_PB0", "17": NC, "18": NC, "19": "GND", "20": "+3V3A",
    "21": "+3V3A", "22": "NODE_ID0", "23": "GND", "24": "+3V3", "25": "NODE_ID1", "26": "LED_STATUS",
    "27": "LED_FAULT", "28": "LED_CANTX", "29": "LED_CANRX", "30": "CAN_S", "31": NC, "32": NC,
    "33": "CAN_RX", "34": "CAN_TX", "35": "GND", "36": "+3V3", "37": "SWDIO", "38": "SWCLK",
    "39": "I2C_SCL", "40": "SWO", "41": NC, "42": "IMU_INT1", "43": NC, "44": "I2C_SDA", "45": "BOOT0",
    "46": "IMU_INT2", "47": "GND", "48": "+3V3"}
add("U3", "STM32G431CBTx", "STM32G431CBT6", "LQFP-48_7x7mm_P0.5mm", mcu_pins, mpn="STM32G431CBT6",
    mfr="STMicroelectronics", desc="Cortex-M4F 170 MHz, 128 KB Flash, 32 KB RAM, FDCAN, LQFP48", group="mcu")
C("C7", "100nF", "+3V3", "GND", group="mcu", desc="VDD pin 48 decoupling")
C("C8", "100nF", "+3V3", "GND", group="mcu", desc="VDD pin 36 decoupling")
C("C9", "100nF", "+3V3", "GND", group="mcu", desc="VDD pin 24 decoupling")
C("C10", "4.7uF 10V X5R", "+3V3", "GND", fp="C_0805_2012Metric", group="mcu", desc="VDD bulk")
C("C11", "100nF", "+3V3", "GND", group="mcu", desc="VBAT decoupling")
add("FB1", "FerriteBead", "600R@100MHz", "L_0603_1608Metric", {"1": "+3V3", "2": "+3V3A"},
    mpn="BLM18AG601SN1D (or equiv. 0603 bead, >=200 mA)", mfr="Murata", desc="VDDA filter bead", group="mcu")
C("C12", "1uF 16V X7R", "+3V3A", "GND", group="mcu", desc="VDDA bulk")
C("C13", "100nF", "+3V3A", "GND", group="mcu", desc="VDDA decoupling")
C("C14", "100nF", "+3V3A", "GND", group="mcu", desc="VREF+ decoupling")
add("Y1", "Crystal_GND24", "8MHz CL12pF", "Crystal_SMD_3225-4Pin_3.2x2.5mm",
    {"1": "OSC_OUT", "2": "GND", "3": "OSC_IN", "4": "GND"},
    mpn="8.000 MHz, 3225 4-pad, +-20 ppm, CL = 12 pF (ESR <= 100R)", mfr="any",
    desc="HSE crystal for accurate CAN bit timing", group="mcu")
C("C16", "15pF C0G", "OSC_IN", "GND", group="mcu", desc="HSE load cap (for CL = 12 pF crystal)")
C("C17", "15pF C0G", "OSC_OUT", "GND", group="mcu", desc="HSE load cap (for CL = 12 pF crystal)")
C("C15", "100nF", "NRST", "GND", group="mcu", desc="NRST filter")
add("SW1", "SW_Push", "RESET", "SW_PUSH_6mm", {"1": "NRST", "2": "GND"}, mpn="6x6 mm THT tactile switch",
    mfr="any", desc="Reset push-button", group="mcu")
R("R4", "10k", "BOOT0", "GND", group="mcu", desc="BOOT0 pull-down (boot from Flash)")
add("JP1", "SolderJumper_2_Open", "BOOT0", "SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
    {"1": "BOOT0", "2": "+3V3"}, mfr="-", desc="Close to force ST system bootloader", group="mcu")
R("R5", "10k", "+3V3", "USER_BTN", group="ui", desc="User button pull-up")
C("C18", "100nF", "USER_BTN", "GND", group="ui", desc="User button debounce")
add("SW2", "SW_Push", "USER", "SW_PUSH_6mm", {"1": "USER_BTN", "2": "GND"}, mpn="6x6 mm THT tactile switch",
    mfr="any", desc="User push-button", group="ui")
for r, d, net, col, a in [("R6", "D4", "LED_STATUS", "GREEN STATUS", "LED_STATUS_A"),
                          ("R7", "D5", "LED_FAULT", "RED FAULT", "LED_FAULT_A"),
                          ("R8", "D6", "LED_CANTX", "YELLOW CAN-TX", "LED_CANTX_A"),
                          ("R9", "D7", "LED_CANRX", "ORANGE CAN-RX", "LED_CANRX_A")]:
    R(r, "680R", net, a, group="ui")
    add(d, "LED", col, "LED_0603_1608Metric", {"2": a, "1": "GND"}, mpn=f"0603 {col.split()[0].lower()} LED",
        mfr="any", desc=f"{col.split()[1]} indicator", group="ui")
add("JP3", "SolderJumper_2_Open", "NODE_ID0", "SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
    {"1": "NODE_ID0", "2": "GND"}, mfr="-", desc="Node-ID bit 0 (closed = 1)", group="ui")
add("JP4", "SolderJumper_2_Open", "NODE_ID1", "SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm",
    {"1": "NODE_ID1", "2": "GND"}, mfr="-", desc="Node-ID bit 1 (closed = 1)", group="ui")

# ------------------------------------------------------------------ CAN
add("U4", "TJA1051T-3", "TJA1051T/3", "SOIC-8_3.9x4.9mm_P1.27mm",
    {"1": "CAN_TX", "2": "GND", "3": "+5V", "4": "CAN_RX", "5": "+3V3", "6": "CANL", "7": "CANH", "8": "CAN_S"},
    mpn="TJA1051T/3,118", mfr="NXP", desc="High-speed CAN (FD) transceiver with VIO, SO8. Must be the /3 (VIO) variant!",
    group="can")
R("R10", "10k", "+3V3", "CAN_S", group="can", desc="Transceiver S pull-up: SILENT until firmware enables")
C("C19", "100nF", "+5V", "GND", group="can", desc="Transceiver VCC decoupling")
C("C20", "100nF", "+3V3", "GND", group="can", desc="Transceiver VIO decoupling")
C("C21", "4.7uF 16V X5R", "+5V", "GND", fp="C_0805_2012Metric", group="can", desc="Transceiver VCC bulk")
add("D8", "PESD1CAN", "PESD1CAN", "SOT-23", {"1": "CANH", "2": "CANL", "3": "GND"},
    mpn="PESD1CAN,215", mfr="Nexperia", desc="CAN bus ESD protection, SOT-23 (verify pinout: 1,2 = bus lines, 3 = GND)",
    group="can")
R("R11", "60R4 1%", "CANH", "TERM_H", fp="R_0805_2012Metric", group="can", desc="Split termination 60.4R 0805")
R("R12", "60R4 1%", "CANL", "TERM_L", fp="R_0805_2012Metric", group="can", desc="Split termination 60.4R 0805")
C("C22", "4.7nF 50V", "TERM_MID", "GND", group="can", desc="Split termination common-mode capacitor")
add("JP2", "Conn_02x02", "CAN_TERM", "PinHeader_2x02_P2.54mm_Vertical",
    {"1": "TERM_H", "2": "TERM_L", "3": "TERM_MID", "4": "TERM_MID"},
    mpn="2x2 2.54 mm header + 2 jumper shunts", mfr="any",
    desc="Termination enable: fit BOTH shunts (1-3 and 2-4) on end-of-bus nodes only", group="can")
for j in ("J2", "J3"):
    add(j, "Conn_01x03", "CAN", "TerminalBlock_1x03_P5.08mm_Horizontal", {"1": "CANH", "2": "CANL", "3": "GND"},
        mpn="1729131 (MKDS 1,5/ 3-5,08) or equivalent", mfr="Phoenix Contact",
        desc="CAN bus connector (1 = CANH, 2 = CANL, 3 = GND); J2/J3 are paralleled for daisy-chain", group="can")

# ------------------------------------------------------------------ IMU
add("U5", "LSM6DS3TR-C", "LSM6DS3TR-C", "LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
    {"1": "GND", "2": "GND", "3": "GND", "4": "IMU_INT1", "5": "+3V3", "6": "GND", "7": "GND", "8": "+3V3",
     "9": "IMU_INT2", "10": NC, "11": NC, "12": "+3V3", "13": "I2C_SCL", "14": "I2C_SDA"},
    mpn="LSM6DS3TR-C", mfr="STMicroelectronics", desc="6-axis IMU (accel + gyro), I2C addr 0x6A", group="imu")
C("C23", "100nF", "+3V3", "GND", group="imu", desc="IMU VDD decoupling")
C("C24", "100nF", "+3V3", "GND", group="imu", desc="IMU VDDIO decoupling")
R("R13", "4k7", "+3V3", "I2C_SCL", group="imu", desc="I2C SCL pull-up")
R("R14", "4k7", "+3V3", "I2C_SDA", group="imu", desc="I2C SDA pull-up")

# ------------------------------------------------------------------ CONNECTORS / TEST
add("J4", "Conn_01x06", "SWD", "PinHeader_1x06_P2.54mm_Vertical",
    {"1": "+3V3", "2": "SWCLK", "3": "GND", "4": "SWDIO", "5": "NRST", "6": "SWO"},
    mpn="1x6 2.54 mm pin header", mfr="any",
    desc="SWD: 1 VDD_TARGET, 2 SWCLK, 3 GND, 4 SWDIO, 5 NRST, 6 SWO (Nucleo CN4 order)", group="conn")
add("J5", "Conn_02x05", "EXPANSION", "PinHeader_2x05_P2.54mm_Vertical",
    {"1": "+3V3", "2": "GND", "3": "UART_TX", "4": "UART_RX", "5": "EXP_PA4", "6": "EXP_PA5",
     "7": "EXP_PA6", "8": "EXP_PA7", "9": "EXP_PB0", "10": "GND"},
    mpn="2x5 2.54 mm pin header", mfr="any", desc="Expansion / debug UART (USART2)", group="conn")
for tp, net in [("TP1", "CANH"), ("TP2", "CANL"), ("TP3", "VIN_PROT"), ("TP4", "+5V"), ("TP5", "+3V3"),
                ("TP6", "GND"), ("TP7", "CAN_TX"), ("TP8", "CAN_RX")]:
    add(tp, "TestPoint", net, "TestPoint_Pad_D1.5mm", {"1": net}, mfr="-", desc=f"Test pad {net}", group="test")
for h in ("H1", "H2", "H3", "H4"):
    add(h, "MountingHole", "M3", "MountingHole_3.2mm_M3", {}, mfr="-", desc="M3 mounting hole (NPTH)", group="mech")

PARTS = {p.ref: p for p in P}


def nets():
    n = {}
    for p in P:
        for pin, net in p.pins.items():
            if net:
                n.setdefault(net, []).append((p.ref, pin))
    return n
