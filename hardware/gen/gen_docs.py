"""
gen_docs.py - documents and figures derived directly from the design data
(so they cannot drift from the KiCad files):
  docs/PIN_MAPPING.md, docs/COMPONENTS.md, docs/VALIDATION_REPORT.md,
  docs/img/*.png (block diagram, power tree, placement, copper layers)
"""
import csv
import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from design import PARTS
from lib import build_symbols, build_footprints
from board import PLACEMENT, courtyard, BX1, BY1, BX2, BY2

ROOT = "/home/claude/stm32-can-ecu"
DOCS = os.path.join(ROOT, "docs")
IMG = os.path.join(DOCS, "img")
SYMS = build_symbols()
FPS = build_footprints()

MCU_FUNC = {
    "PC13": "USER button SW2 (active low, ext. 10k pull-up)", "PF0-OSC_IN": "HSE 8 MHz crystal Y1",
    "PF1-OSC_OUT": "HSE 8 MHz crystal Y1", "PG10-NRST": "Reset: SW1, C15 100 nF, SWD pin 5",
    "PA0": "ADC1_IN1 - VIN sense divider 100k/15k", "PA2": "USART2_TX (AF7) debug console -> J5.3",
    "PA3": "USART2_RX (AF7) debug console -> J5.4", "PA4": "Expansion J5.5 (GPIO/ADC/DAC)",
    "PA5": "Expansion J5.6", "PA6": "Expansion J5.7", "PA7": "Expansion J5.8", "PB0": "Expansion J5.9",
    "PB10": "NODE_ID bit0 - solder jumper JP3 to GND (internal pull-up)",
    "PB11": "NODE_ID bit1 - solder jumper JP4 to GND (internal pull-up)",
    "PB12": "LED STATUS (green) via 680R", "PB13": "LED FAULT (red) via 680R",
    "PB14": "LED CAN-TX (yellow) via 680R", "PB15": "LED CAN-RX (orange) via 680R",
    "PA8": "CAN transceiver S (silent) - 10k pull-up, LOW = normal",
    "PA11": "FDCAN1_RX (AF9) <- TJA1051 RXD", "PA12": "FDCAN1_TX (AF9) -> TJA1051 TXD",
    "PA13": "SWDIO (J4.4)", "PA14": "SWCLK (J4.2)", "PA15": "I2C1_SCL (AF4) - IMU, 4k7 pull-up",
    "PB3": "SWO trace output (J4.6)", "PB5": "IMU INT1 (accel data-ready)", "PB7": "I2C1_SDA (AF4) - IMU, 4k7 pull-up",
    "PB8-BOOT0": "BOOT0: 10k pull-down, JP1 to 3V3 = system bootloader", "PB9": "IMU INT2 (spare)",
    "VBAT": "+3V3 (no backup battery), 100 nF", "VDD": "+3V3, 100 nF per pin + 4.7 uF bulk",
    "VSS": "GND", "VSSA": "GND", "VDDA": "+3V3A (ferrite FB1 + 1 uF + 100 nF)", "VREF+": "+3V3A, 100 nF",
}


def pin_mapping():
    mcu = PARTS["U3"]
    sym = SYMS["STM32G431CBTx"]
    names = {p.num: p.name for p in sym.pins}
    L = ["# MCU pin mapping - STM32G431CBT6 (LQFP48)", "",
         "Generated from `hardware/gen/design.py` (single source of truth for schematic, PCB and firmware "
         "`Core/Inc/board.h`). Pin numbers/names were checked against ST datasheet DS12589 (LQFP48 pinout). "
         "Unused pins are unconnected on the PCB and configured as analog inputs by the firmware.", "",
         "| Pin | Name | Net | Function |", "|---:|---|---|---|"]
    for n in range(1, 49):
        nm = names.get(str(n), "?")
        net = mcu.pins.get(str(n))
        base = nm.split("/")[0]
        func = MCU_FUNC.get(nm, MCU_FUNC.get(base, "not connected (analog input)" if net is None else ""))
        L.append(f"| {n} | {nm} | {net or '-'} | {func} |")
    L += ["", "## Alternate-function summary", "",
          "| Peripheral | Signal | Pin | AF |", "|---|---|---|---|",
          "| FDCAN1 | RX | PA11 | AF9 |", "| FDCAN1 | TX | PA12 | AF9 |",
          "| I2C1 | SCL | PA15 | AF4 |", "| I2C1 | SDA | PB7 | AF4 |",
          "| USART2 | TX | PA2 | AF7 |", "| USART2 | RX | PA3 | AF7 |",
          "| SWD | SWDIO / SWCLK / SWO | PA13 / PA14 / PB3 | AF0 (reset default) |",
          "| ADC1 | IN1 (VIN sense) | PA0 | analog |", "",
          "**Why no USB:** on the STM32G431 the only FDCAN1 pin pair that does not collide with other "
          "functions here is PA11/PA12 - the same pins as USB DM/DP. The alternative FDCAN1 pins PB8/PB9 "
          "would put CAN RX on the BOOT0 pin (PB8), which is a known source of boot problems. Rev A therefore "
          "uses PA11/PA12 for CAN and provides a 3.3 V UART on J5 instead of USB.", ""]
    L += ["## Connectors", ""]
    for ref, title in [("J1", "Power input (5.08 mm screw terminal)"), ("J2", "CAN bus A (5.08 mm, 3-pole)"),
                       ("J3", "CAN bus B (5.08 mm, 3-pole, parallel to J2 for daisy-chaining)"),
                       ("J4", "SWD debug (1x6 2.54 mm, ST-LINK/Nucleo CN4 order)"),
                       ("J5", "Expansion / UART (2x5 2.54 mm)"), ("JP2", "CAN termination (2x2 2.54 mm, fit 2 shunts: 1-3 and 2-4)")]:
        p = PARTS[ref]
        L += [f"### {ref} - {title}", "", "| Pin | Net |", "|---:|---|"]
        for k in sorted(p.pins, key=int):
            L.append(f"| {k} | {p.pins[k]} |")
        L.append("")
    L += ["## Jumpers", "", "| Ref | Function | Open (default) | Closed |", "|---|---|---|---|",
          "| JP1 | BOOT0 | boot from flash | ST system bootloader (UART/FDCAN/I2C/SPI) |",
          "| JP2 | CAN termination (2 shunts) | no termination | 2 x 60.4 R split + 4.7 nF |",
          "| JP3 | NODE_ID bit 0 (PB10) | 0 | 1 |", "| JP4 | NODE_ID bit 1 (PB11) | 0 | 1 |", "",
          "Node ID = JP4*2 + JP3 -> 0..3. Two boards must have **different** node IDs "
          "(e.g. board A: both open = node 0; board B: JP3 closed = node 1).", ""]
    open(os.path.join(DOCS, "PIN_MAPPING.md"), "w").write("\n".join(L))


VERIFY = {
    "LQFP-48_7x7mm_P0.5mm": "Generated to IPC-7351-like dimensions (pads 1.475 x 0.3 at +-4.1625). Compare with KiCad Package_QFP:LQFP-48_7x7mm_P0.5mm.",
    "LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y": "**VERIFY** against ST LSM6DS3TR-C land-pattern recommendation (pads 0.5 x 0.25 mm). Pin-1 orientation is critical.",
    "SOIC-8_3.9x4.9mm_P1.27mm": "Standard JEDEC MS-012 land pattern.",
    "Converter_DCDC_RECOM_R-78E-0.5_THT": "**VERIFY** pin pitch (2.54 mm) and body side against the RECOM drawing; 6.5 mm keep-out reserved both sides.",
    "Crystal_SMD_3225-4Pin_3.2x2.5mm": "Standard 3225 4-pad; confirm pad 1/3 = crystal, 2/4 = GND for the chosen part.",
    "SOT-23": "**VERIFY** PESD1CAN pinout (1 = CANH/line, 2 = CANL/line, 3 = common) - symmetric part, swapping 1/2 is harmless.",
    "SOT-23-5": "AP2112K SOT-23-5 pinout checked (1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT).",
    "TerminalBlock_1x02_P5.08mm_Horizontal": "**VERIFY** hole size/pitch vs. the terminal block actually bought (Phoenix MKDS 1,5/2-5,08 style).",
    "TerminalBlock_1x03_P5.08mm_Horizontal": "**VERIFY** as above (3-pole).",
    "Fuse_1812_4532Metric": "Generic 1812 PTC land pattern.",
}


def components():
    L = ["# Component and footprint list", "",
         "Generated from `hardware/gen/design.py` and `lib.py`. All footprints live in the project library "
         "`hardware/kicad/CAN_ECU.pretty` (self-contained project); the column *KiCad std* names the equivalent "
         "footprint in KiCad's official libraries, which you may swap in. Rows marked **VERIFY** must be checked "
         "against the manufacturer drawing of the exact part you buy before ordering PCBs.", "",
         "## Components", "", "| Ref | Value | Part / specification | Footprint | Function |", "|---|---|---|---|---|"]
    import re
    key = lambda r: (re.match(r"[A-Z]+", r).group(), int(re.search(r"\d+", r).group()))
    for ref in sorted(PARTS, key=key):
        p = PARTS[ref]
        L.append(f"| {ref} | {p.value} | {p.mpn or '-'} {('(' + p.mfr + ')') if p.mfr and p.mfr != 'any' else ''} | {p.fp} | {p.desc} |")
    L += ["", "## Footprints", "", "| Project footprint | KiCad std equivalent | Type | Used by | Verification note |",
          "|---|---|---|---|---|"]
    for name, f in FPS.items():
        users = sorted([r for r, p in PARTS.items() if p.fp == name], key=key)
        if not users:
            continue
        L.append(f"| {name} | {f.std} | {f.attr} | {' '.join(users)} | {VERIFY.get(name, 'Standard generic land pattern.')} |")
    L += ["", "## BOM", "", "See `hardware/fab/BOM.csv` (grouped, with rough cost estimates)."]
    open(os.path.join(DOCS, "COMPONENTS.md"), "w").write("\n".join(L) + "\n")


def block_diagram():
    fig, ax = plt.subplots(figsize=(12, 6.2))
    ax.set_xlim(0, 120); ax.set_ylim(0, 62); ax.axis("off")

    def box(x, y, w, h, t, c):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4", fc=c, ec="#333", lw=1.2))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8.5)

    def arr(x1, y1, x2, y2, t="", both=False):
        ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="<->" if both else "->", lw=1.2))
        if t:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.2, t, ha="center", fontsize=7.5, color="#224")
    box(2, 44, 14, 10, "J1\n8-18 V DC in", "#ffe0b0")
    box(21, 44, 20, 10, "Protection\nPTC 0.5 A + TVS SMBJ18A\n+ Schottky SS34", "#ffd0d0")
    box(46, 44, 18, 10, "R-78E5.0-0.5\nswitching module\n+5 V / 0.5 A", "#ffe0b0")
    box(69, 44, 17, 10, "AP2112K-3.3\nLDO\n+3V3 / 0.6 A", "#ffe0b0")
    box(40, 14, 26, 22, "STM32G431CBT6\nCortex-M4F 170 MHz\n128 KB flash / 32 KB RAM\nFDCAN1, I2C1, USART2,\nADC1, IWDG", "#d0e4ff")
    box(76, 20, 18, 10, "TJA1051T/3\nCAN transceiver\n(S pin: silent)", "#d0ffd8")
    box(100, 26, 18, 10, "J2 / J3\nCANH CANL GND\n+ PESD1CAN ESD", "#d0ffd8")
    box(100, 10, 18, 10, "JP2 split\ntermination\n2x60.4R + 4.7nF", "#d0ffd8")
    box(40, 0, 26, 8, "LSM6DS3TR-C IMU (I2C 0x6A)\naccel +-4 g, gyro +-500 dps", "#f0e0ff")
    box(6, 22, 20, 10, "J4 SWD (ST-LINK)\nJ5 UART + GPIO", "#eeeeee")
    box(6, 6, 20, 10, "LEDs PWR/STATUS/FAULT\n/CAN-TX/CAN-RX\nbuttons, jumpers", "#eeeeee")
    box(76, 4, 18, 8, "8 MHz crystal", "#eeeeee")
    arr(16, 49, 21, 49); arr(41, 49, 46, 49, "VIN_PROT"); arr(64, 49, 69, 49, "+5V")
    arr(77.5, 44, 53, 36, "+3V3"); arr(60, 44, 83, 30, "+5V (VCC)")
    arr(66, 27, 76, 27, "TXD/RXD/S", both=True); arr(94, 27, 100, 31, both=True); arr(94, 23, 100, 15)
    arr(53, 14, 53, 8, "I2C1 + INT", both=True); arr(26, 27, 40, 27, "SWD / UART", both=True)
    arr(40, 18, 26, 11, "GPIO"); arr(66, 16, 76, 8, "HSE", both=True)
    arr(30, 44, 42, 34, "VIN sense (ADC)")
    ax.set_title("STM32 CAN ECU - block diagram", fontsize=12)
    fig.savefig(os.path.join(IMG, "block_diagram.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


def power_tree():
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.axis("off"); ax.set_xlim(0, 110); ax.set_ylim(0, 36)
    items = [(2, "VIN 8-18 V\n(12 V nom.)"), (20, "F1 PTC 0.5 A\nD1 TVS 18 V"), (38, "D2 SS34\n~0.4 V drop"),
             (56, "U1 R-78E5.0\n5.0 V, ~80 %"), (76, "U2 AP2112K\n3.3 V LDO"), (94, "FB1 ->\n+3V3A (VDDA)")]
    for x, t in items:
        ax.add_patch(FancyBboxPatch((x, 18), 14, 12, boxstyle="round,pad=0.4", fc="#fff2d0", ec="#444"))
        ax.text(x + 7, 24, t, ha="center", va="center", fontsize=8)
    for a, b in zip(items[:-1], items[1:]):
        ax.annotate("", (b[0] - 0.5, 24), (a[0] + 14.5, 24), arrowprops=dict(arrowstyle="->"))
    ax.text(63, 10, "+5V loads: TJA1051 VCC 10-70 mA,\nPWR LED 2 mA, LDO input", ha="center", fontsize=8)
    ax.text(83, 10, "+3V3 loads: MCU ~40 mA, IMU 1 mA,\nLEDs <8 mA, pull-ups ~2 mA", ha="center", fontsize=8)
    ax.text(27, 10, "reverse polarity: D2 blocks,\nD1 conducts -> PTC trips", ha="center", fontsize=8)
    ax.set_title("Power tree (worst case ~125 mA @ 5 V, ~0.85 W from VIN)", fontsize=11)
    fig.savefig(os.path.join(IMG, "power_tree.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)


def board_images():
    from render import render
    R = json.load(open(os.path.join(ROOT, "hardware/gen/routes.json")))
    render(os.path.join(IMG, "pcb_placement.png"), (), (), title="Placement (courtyards, pad nets)", show_nets=True, dpi=90)
    render(os.path.join(IMG, "pcb_routed_top_bottom.png"), R["tracks"], R["vias"],
           title="Routing: red = F.Cu (top), blue = B.Cu (bottom); In1 = GND plane, In2 = +3V3 plane",
           show_crt=False, dpi=90)
    render(os.path.join(IMG, "pcb_zoom_mcu.png"), R["tracks"], R["vias"], zoom=(124, 112, 152, 145),
           title="MCU / IMU / crystal area", show_nets=True, dpi=80)


def validation_report():
    buf = io.StringIO()
    import checks
    import validate_files
    with redirect_stdout(buf):
        res = checks.run(os.path.join(ROOT, "hardware/gen/routes.json"))
        errs = validate_files.main()
    t = subprocess.run(["make", "-C", os.path.join(ROOT, "firmware/tests")], capture_output=True, text=True)
    tt = subprocess.run([sys.executable, "test_tools.py"], cwd=os.path.join(ROOT, "tools"), capture_output=True, text=True)
    L = ["# Validation report", "",
         "KiCad itself was **not available** in the environment where this design was generated, so KiCad's own "
         "ERC/DRC could not be run. Instead the checks below were implemented independently and run on the "
         "generated data and files. **Run KiCad ERC and DRC yourself before ordering** (see docs/MANUFACTURING.md).", "",
         "## 1. PCB design-rule and connectivity check (hardware/gen/checks.py)", "",
         "Rules: copper clearance 0.20 mm, copper-edge 0.30 mm, hole-hole 0.25 mm, min track 0.20 mm, no via-in-pad, "
         "courtyard overlap, full net connectivity including the In1 (GND) / In2 (+3V3) planes (raster flood-fill "
         "with 0.25 mm antipads).", "", "```", buf.getvalue().split("  sch_symbols")[0].strip(), "```", "",
         "Note: In2.Cu shows small isolated copper islands with no +3V3 connection; KiCad removes these "
         "automatically when zones are filled (default island removal).", "",
         "## 2. Generated-file check (hardware/gen/validate_files.py)", "",
         "Re-parses the KiCad files: S-expression syntax of every file, schematic connectivity rebuilt from wires / "
         "labels / pin positions and compared net-by-net with the design netlist, ERC subset (unconnected pins, "
         "undriven power inputs, conflicting outputs/labels, single-pin nets), PCB pad nets vs. schematic, closed "
         "board outline, silkscreen vs. pads / edge / other text.", "", "```",
         "  sch_symbols" + buf.getvalue().split("  sch_symbols")[1].strip(), "```", "",
         "## 3. Firmware host tests (firmware/tests)", "", "```", t.stdout.strip()[-1500:], "```", "",
         "## 4. PC tools self-test (tools/test_tools.py)", "", "```", tt.stdout.strip(), "```", "",
         "## What could NOT be verified here", "",
         "* KiCad ERC/DRC and zone filling (file format written for KiCad 7; opens in KiCad 7/8/9).",
         "* A real `arm-none-eabi-gcc` build against the ST HAL (only a stub-HAL compile check was possible). "
         "Build it with the CMake project or STM32CubeIDE - see docs/FIRMWARE.md.",
         "* Signal integrity / EMC, thermal behaviour, crystal start-up margin - require hardware measurement.",
         "* Footprints marked VERIFY in docs/COMPONENTS.md against the exact purchased parts.", ""]
    open(os.path.join(DOCS, "VALIDATION_REPORT.md"), "w").write("\n".join(L))
    return res, errs, t.returncode, tt.returncode


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    pin_mapping(); components(); block_diagram(); power_tree(); board_images()
    res, errs, rc1, rc2 = validation_report()
    print("DRC", len(res["drc"]), "unconnected", len(res["unconnected"]), "file errors", len(errs), "tests rc", rc1, rc2)
