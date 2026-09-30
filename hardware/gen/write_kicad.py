"""
write_kicad.py - emits the KiCad project from design.py / lib.py / board.py /
routes.json.

File format: KiCad 7 (schematic 20230121, symbol lib 20220914, board and
footprints 20221018).  KiCad 7, 8 and 9 open these files directly (8/9 offer
to save them in their newer format).
"""
import json
import math
import os
import uuid

from lib import build_symbols, build_footprints, fmt, rot_pt
from design import PARTS, P as PART_LIST, PROJECT, REV, TITLE, nets as design_nets
from board import PLACEMENT, placed_pads_cache, courtyard, board_outline, outline_polygon, BX1, BY1, BX2, BY2

OUT = "/home/claude/stm32-can-ecu/hardware/kicad"
NS = uuid.UUID("7d1d6d3e-2c0b-4b5e-9a0e-5a1f3c9b2e11")
DATE = "2026-09-30"


def U(*names):
    return str(uuid.uuid5(NS, "/".join(str(n) for n in names)))


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


SYMS = build_symbols()
FPS = build_footprints()
ROOT = U("root-sheet")

DATASHEETS = {
    "STM32G431CBTx": "https://www.st.com/resource/en/datasheet/stm32g431cb.pdf",
    "TJA1051T-3": "https://www.nxp.com/docs/en/data-sheet/TJA1051.pdf",
    "LSM6DS3TR-C": "https://www.st.com/resource/en/datasheet/lsm6ds3tr-c.pdf",
    "AP2112K-3.3": "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
    "R-78E5.0-0.5": "https://recom-power.com/pdf/Innoline/R-78E-0.5.pdf",
    "PESD1CAN": "https://assets.nexperia.com/documents/data-sheet/PESD1CAN.pdf",
}


# =====================================================================
# symbol library
# =====================================================================
def sym_def(s, prefix_lib=""):
    name = (prefix_lib + ":" if prefix_lib else "") + s.name
    o = [f'  (symbol {q(name)}']
    if s.power:
        o[0] += " (power)"
    if not s.show_pin_numbers:
        o[0] += " (pin_numbers hide)"
    if not s.show_pin_names:
        o[0] += " (pin_names (offset 0) hide)"
    else:
        o[0] += f" (pin_names (offset {fmt(s.name_offset)}))"
    o[0] += f" (in_bom {'yes' if s.in_bom else 'no'}) (on_board {'yes' if s.on_board else 'no'})"
    rx, ry, rr = s.ref_at
    vx, vy, vr = s.val_at
    hide_ref = " hide" if s.power else ""
    o.append(f'    (property "Reference" {q(s.prefix)} (id 0) (at {fmt(rx)} {fmt(ry)} {rr})\n'
             f'      (effects (font (size 1.27 1.27)) (justify left){hide_ref})\n    )')
    o.append(f'    (property "Value" {q(s.name)} (id 1) (at {fmt(vx)} {fmt(vy)} {vr})\n'
             f'      (effects (font (size 1.27 1.27)) (justify left))\n    )')
    o.append('    (property "Footprint" "" (id 2) (at 0 0 0)\n      (effects (font (size 1.27 1.27)) hide)\n    )')
    o.append(f'    (property "Datasheet" {q(DATASHEETS.get(s.name, "~"))} (id 3) (at 0 0 0)\n'
             '      (effects (font (size 1.27 1.27)) hide)\n    )')
    o.append(f'    (property "ki_description" {q(s.desc)} (id 4) (at 0 0 0)\n'
             '      (effects (font (size 1.27 1.27)) hide)\n    )')
    o.append(f'    (symbol {q(s.name + "_0_1")}')
    for g in s.gfx:
        o.append("      " + g)
    o.append("    )")
    o.append(f'    (symbol {q(s.name + "_1_1")}')
    for p in s.pins:
        hid = " hide" if p.hidden else ""
        o.append(f'      (pin {p.etype} line (at {fmt(p.x)} {fmt(p.y)} {p.angle}) (length {fmt(p.length)}){hid}\n'
                 f'        (name {q(p.name)} (effects (font (size 1.27 1.27))))\n'
                 f'        (number {q(p.num)} (effects (font (size 1.27 1.27))))\n      )')
    o.append("    )")
    o.append("  )")
    return "\n".join(o)


def write_symbol_lib():
    body = "\n".join(sym_def(s) for s in SYMS.values())
    txt = f"(kicad_symbol_lib (version 20220914) (generator kicad_symbol_editor)\n{body}\n)\n"
    open(os.path.join(OUT, f"{PROJECT}.kicad_sym"), "w").write(txt)


# =====================================================================
# footprint library
# =====================================================================
def fp_graphics(f, indent="  ", tstamps=None):
    o = []
    for k, g in enumerate(f.gfx):
        ts = f" (tstamp {tstamps(k)})" if tstamps else ""
        if g[0] == "line":
            _, L, x1, y1, x2, y2, w = g
            o.append(f'{indent}(fp_line (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)})\n'
                     f'{indent}  (stroke (width {fmt(w)}) (type solid)) (layer {q(L)}){ts})')
        elif g[0] == "circle":
            _, L, cx, cy, r, w = g
            o.append(f'{indent}(fp_circle (center {fmt(cx)} {fmt(cy)}) (end {fmt(cx + r)} {fmt(cy)})\n'
                     f'{indent}  (stroke (width {fmt(w)}) (type solid)) (fill none) (layer {q(L)}){ts})')
    return o


def pad_sexpr(p, rot=0, net=None, tstamp=None, pintype=None):
    ang = (rot + p.angle) % 360
    at = f"(at {fmt(p.x)} {fmt(p.y)}{' ' + fmt(ang) if ang else ''})"
    s = f'(pad {q(p.num)} {p.kind.replace("smd_nopaste", "smd")} {p.shape} {at} (size {fmt(p.w)} {fmt(p.h)})'
    if p.drill:
        s += f" (drill {fmt(p.drill)})"
    s += " (layers " + " ".join(q(l) for l in p.layers) + ")"
    if p.shape == "roundrect":
        s += f" (roundrect_rratio {fmt(p.rratio)})"
    if net:
        s += f" (net {net[0]} {q(net[1])})"
    if pintype:
        s += f" (pintype {q(pintype)})"
    if tstamp:
        s += f" (tstamp {tstamp})"
    return s + ")"


def write_fp_lib():
    d = os.path.join(OUT, f"{PROJECT}.pretty")
    os.makedirs(d, exist_ok=True)
    for name, f in FPS.items():
        o = [f'(footprint {q(name)} (version 20221018) (generator pcbnew)', '  (layer "F.Cu")',
             f'  (descr {q("Project copy modelled on KiCad " + f.std + ". VERIFY against the manufacturer land pattern.")})',
             f'  (tags {q(name)})']
        if f.attr == "exclude":
            o.append("  (attr exclude_from_pos_files exclude_from_bom)")
        else:
            o.append(f"  (attr {f.attr})")
        o.append(f'  (fp_text reference "REF**" (at {fmt(f.ref_at[0])} {fmt(f.ref_at[1])}) (layer "F.SilkS")\n'
                 '      (effects (font (size 0.8 0.8) (thickness 0.12)))\n  )')
        o.append(f'  (fp_text value {q(name)} (at {fmt(f.val_at[0])} {fmt(f.val_at[1])}) (layer "F.Fab")\n'
                 '      (effects (font (size 0.8 0.8) (thickness 0.12)))\n  )')
        o += fp_graphics(f)
        for p in f.pads:
            o.append("  " + pad_sexpr(p))
        o.append(")")
        open(os.path.join(d, name + ".kicad_mod"), "w").write("\n".join(o) + "\n")


def write_lib_tables():
    open(os.path.join(OUT, "sym-lib-table"), "w").write(
        '(sym_lib_table\n  (lib (name "CAN_ECU")(type "KiCad")(uri "${KIPRJMOD}/CAN_ECU.kicad_sym")(options "")'
        '(descr "CAN ECU project symbols"))\n)\n')
    open(os.path.join(OUT, "fp-lib-table"), "w").write(
        '(fp_lib_table\n  (lib (name "CAN_ECU")(type "KiCad")(uri "${KIPRJMOD}/CAN_ECU.pretty")(options "")'
        '(descr "CAN ECU project footprints"))\n)\n')


# =====================================================================
# schematic
# =====================================================================
BLOCKS = [
    ("POWER INPUT, PROTECTION AND REGULATION", (15, 25, 205, 150),
     ["J1", "F1", "D1", "D2", "C1", "C2", "U1", "C3", "U2", "C4", "C5", "R1", "D3", "R2", "R3", "C6",
      "#FLG01", "#FLG02", "#FLG03", "TP3", "TP4", "TP5", "TP6"]),
    ("MICROCONTROLLER STM32G431CBT6 (clock, reset, boot, decoupling)", (215, 25, 420, 265),
     ["U3", "C7", "C8", "C9", "C10", "C11", "FB1", "C12", "C13", "C14", "Y1", "C16", "C17",
      "C15", "SW1", "R4", "JP1"]),
    ("CAN INTERFACE (TJA1051T/3, ESD, switchable split termination)", (430, 25, 580, 175),
     ["U4", "R10", "C19", "C20", "C21", "D8", "R11", "R12", "C22", "JP2", "J2", "J3", "TP1", "TP2", "TP7", "TP8"]),
    ("IMU LSM6DS3TR-C (I2C1, addr 0x6A)", (430, 185, 580, 265), ["U5", "C23", "C24", "R13", "R14"]),
    ("USER INTERFACE: LEDs, button, node-ID jumpers", (15, 160, 205, 265),
     ["R5", "C18", "SW2", "R6", "D4", "R7", "D5", "R8", "D6", "R9", "D7", "JP3", "JP4"]),
    ("DEBUG / EXPANSION CONNECTORS, MECHANICAL", (15, 275, 420, 400), ["J4", "J5", "H1", "H2", "H3", "H4"]),
]

FLAGS = {"#FLG01": "GND", "#FLG02": "VIN_PROT", "#FLG03": "+3V3A"}

NOTES = [
    (430, 280, "DESIGN NOTES\n"
     "1. Supply 8-18 V DC (12 V nominal). Reverse polarity: series Schottky D2; TVS D1 clamps\n"
     "   transients and conducts on reverse polarity so PTC F1 trips. NOT load-dump rated.\n"
     "2. R-78E5.0-0.5 needs >= 7 V in. +5V feeds the CAN transceiver VCC and the 3.3 V LDO.\n"
     "3. FDCAN1 on PA11 (RX) / PA12 (TX), AF9. USB is not available (same pins).\n"
     "4. CAN transceiver S pin pulled HIGH (silent) until firmware drives PA8 low.\n"
     "5. CAN termination: fit BOTH jumpers on JP2 (1-3 and 2-4) ONLY on the two\n"
     "   boards at the physical ends of the bus. 2 x 60.4R split + 4.7 nF to GND.\n"
     "6. BOOT0 = PB8, 10k pull-down. Close JP1 to enter the ST ROM bootloader.\n"
     "7. Node ID: JP3 (PB10) = bit0, JP4 (PB11) = bit1; closed = 1 (internal pull-ups).\n"
     "8. HSE 8 MHz crystal, CL = 12 pF, 15 pF C0G load caps (verify vs crystal datasheet).\n"
     "9. Unused MCU pins are no-connect; firmware configures them as analog."),
]


def sym_bbox_with_labels(sym, ref):
    """bbox in schematic coords relative to symbol origin, including stubs+labels."""
    part = PARTS.get(ref)
    xs, ys = [], []
    b = getattr(sym, "body", (-2.54, 2.54, 2.54, -2.54))
    xs += [b[0], b[2]]; ys += [-b[1], -b[3]]
    for p in sym.pins:
        net = part.pins.get(p.num) if part else FLAGS.get(ref)
        L = len(net or "") * 1.0 + 3.5
        x, y = p.x, -p.y
        dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[p.angle]
        xs += [x + dx * L, x]; ys += [y + dy * L, y]
    return min(xs) - 2, min(ys) - 3.5, max(xs) + 2, max(ys) + 3.5


def layout_schematic():
    pos = {}
    for title, (x0, y0, x1, y1), refs in BLOCKS:
        cx, cy = x0 + 3, y0 + 12
        rowh = 0
        for ref in refs:
            sname = PARTS[ref].sym if ref in PARTS else "PWR_FLAG"
            s = SYMS[sname]
            bx0, by0, bx1, by1 = sym_bbox_with_labels(s, ref)
            w, h = bx1 - bx0, by1 - by0
            if cx + w > x1 and cx > x0 + 3:
                cx = x0 + 3
                cy += rowh + 2
                rowh = 0
            ox = round((cx - bx0) / 2.54) * 2.54
            oy = round((cy - by0) / 2.54) * 2.54
            pos[ref] = (round(ox, 2), round(oy, 2))
            cx += w + 2
            rowh = max(rowh, h)
        if cy + rowh > y1:
            print(f"WARNING schematic block overflow: {title} ({cy + rowh:.0f} > {y1})")
    return pos


def write_schematic():
    pos = layout_schematic()
    used_syms = sorted({PARTS[r].sym for r in PARTS} | {"PWR_FLAG"})
    o = [f'(kicad_sch (version 20230121) (generator eeschema)', f'  (uuid {ROOT})', '  (paper "A2")',
         '  (title_block', f'    (title {q(TITLE)})', f'    (date {q(DATE)})', f'    (rev {q(REV)})',
         '    (company "Open hardware - generated design")',
         '    (comment 1 "Single-sheet, label-connected schematic. Net names match docs/PIN_MAPPING.md")',
         '    (comment 2 "Generated by hardware/gen/*.py - edit design.py and regenerate, or edit in KiCad")',
         '  )', '  (lib_symbols']
    for n in used_syms:
        o.append(sym_def(SYMS[n], PROJECT).replace("\n", "\n  ").replace("  (symbol", "    (symbol", 1))
    o.append('  )')
    items = []
    k = 0
    for title, (x0, y0, x1, y1), refs in BLOCKS:
        items.append(f'  (text {q(title)} (at {fmt(x0 + 2)} {fmt(y0 + 5)} 0)\n'
                     f'    (effects (font (size 2.54 2.54) (thickness 0.508) bold) (justify left bottom))\n'
                     f'    (uuid {U("blocktitle", title)})\n  )')
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        for a, b in zip(pts[:-1], pts[1:]):
            k += 1
            items.append(f'  (polyline (pts (xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])}))\n'
                         f'    (stroke (width 0.254) (type dash))\n    (uuid {U("frame", title, k)})\n  )')
    for x, y, t in NOTES:
        items.append(f'  (text {q(t)} (at {x} {y} 0)\n    (effects (font (size 1.778 1.778)) (justify left top))\n'
                     f'    (uuid {U("note", x, y)})\n  )')
    ann = []
    all_refs = [r for _, _, refs in BLOCKS for r in refs]
    for ref in all_refs:
        is_flag = ref not in PARTS
        sname = "PWR_FLAG" if is_flag else PARTS[ref].sym
        s = SYMS[sname]
        X, Y = pos[ref]
        su = U("sym", ref)
        if is_flag:
            val, fp, ds, mpn, mfr = "PWR_FLAG", "", "~", "", ""
            inbom, onb = "no", "no"
        else:
            part = PARTS[ref]
            val = part.value
            fp = f"{PROJECT}:{part.fp}"
            ds = DATASHEETS.get(s.name, "~")
            mpn, mfr = part.mpn, part.mfr
            inbom = "yes" if s.in_bom else "no"
            onb = "yes"
        rx, ry, _ = s.ref_at
        vx, vy, _ = s.val_at
        hide_ref = " hide" if is_flag else ""
        sym = [f'  (symbol (lib_id {q(PROJECT + ":" + s.name)}) (at {fmt(X)} {fmt(Y)} 0) (unit 1)',
               f'    (in_bom {inbom}) (on_board {onb}) (dnp no)',
               f'    (uuid {su})',
               f'    (property "Reference" {q(ref)} (id 0) (at {fmt(X + rx)} {fmt(Y - ry)} 0)\n'
               f'      (effects (font (size 1.27 1.27)) (justify left){hide_ref})\n    )',
               f'    (property "Value" {q(val)} (id 1) (at {fmt(X + vx)} {fmt(Y - vy)} 0)\n'
               f'      (effects (font (size 1.27 1.27)) (justify left))\n    )',
               f'    (property "Footprint" {q(fp)} (id 2) (at {fmt(X)} {fmt(Y)} 0)\n'
               f'      (effects (font (size 1.27 1.27)) hide)\n    )',
               f'    (property "Datasheet" {q(ds)} (id 3) (at {fmt(X)} {fmt(Y)} 0)\n'
               f'      (effects (font (size 1.27 1.27)) hide)\n    )']
        if not is_flag:
            sym.append(f'    (property "MPN" {q(mpn)} (id 4) (at {fmt(X)} {fmt(Y)} 0)\n'
                       f'      (effects (font (size 1.27 1.27)) hide)\n    )')
            sym.append(f'    (property "Manufacturer" {q(mfr)} (id 5) (at {fmt(X)} {fmt(Y)} 0)\n'
                       f'      (effects (font (size 1.27 1.27)) hide)\n    )')
        for p in s.pins:
            sym.append(f'    (pin {q(p.num)} (uuid {U("pin", ref, p.num)}))')
        sym.append(f'    (instances\n      (project {q(PROJECT)}\n        (path "/{ROOT}"\n'
                   f'          (reference {q(ref)}) (unit 1)\n        )\n      )\n    )')
        sym.append("  )")
        items.append("\n".join(sym))
        # stubs + labels
        for p in s.pins:
            px, py = X + p.x, Y - p.y
            net = FLAGS[ref] if is_flag else PARTS[ref].pins.get(p.num)
            if net is None:
                items.append(f'  (no_connect (at {fmt(px)} {fmt(py)}) (uuid {U("nc", ref, p.num)}))')
                continue
            dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[p.angle]
            ex, ey = round(px + dx * 2.54, 3), round(py + dy * 2.54, 3)
            items.append(f'  (wire (pts (xy {fmt(px)} {fmt(py)}) (xy {fmt(ex)} {fmt(ey)}))\n'
                         f'    (stroke (width 0) (type default))\n    (uuid {U("wire", ref, p.num)})\n  )')
            ang, just = {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, 1): (270, "right"), (0, -1): (90, "left")}[(dx, dy)]
            items.append(f'  (label {q(net)} (at {fmt(ex)} {fmt(ey)} {ang})\n'
                         f'    (effects (font (size 1.27 1.27)) (justify {just} bottom))\n'
                         f'    (uuid {U("label", ref, p.num)})\n  )')
            ann.append((net, ref, p.num, ex, ey))
    o += items
    o.append('  (sheet_instances\n    (path "/" (page "1"))\n  )')
    o.append(")")
    open(os.path.join(OUT, f"{PROJECT}.kicad_sch"), "w").write("\n".join(o) + "\n")
    return pos, ann


# =====================================================================
# PCB
# =====================================================================
NETS_ORDER = None


def net_table():
    names = sorted(design_nets().keys(), key=lambda n: (n != "GND", n))
    return {n: i + 1 for i, n in enumerate(names)}


def text_box(x, y, s, size, rot=0):
    w = len(s) * size * 0.8 + 0.2
    h = size * 1.25
    if rot in (90, 270):
        return (x - h / 2, y - w / 2, x + h / 2, y + w / 2)
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def _boxes_overlap(a, b, m=0.0):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


def place_silk_refs(extra_obstacles):
    """Choose a silkscreen position for every reference designator that
    does not overlap pads, other text, board-level silk or the board edge."""
    pads = placed_pads_cache()
    obst = [p.bbox() for p in pads if p.kind != "np_thru_hole"]
    holes = [(p.x - 3.0, p.y - 3.0, p.x + 3.0, p.y + 3.0) for p in pads if p.kind == "np_thru_hole"]
    placed = list(extra_obstacles)
    silk_lines = footprint_silk_boxes()
    res = {}
    size = 0.8
    order = sorted(PARTS, key=lambda r: -(courtyard(r)[2] - courtyard(r)[0]) * (courtyard(r)[3] - courtyard(r)[1]))
    for ref in order:
        if ref.startswith("H"):
            res[ref] = None
            continue
        x1, y1, x2, y2 = courtyard(ref)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        cands = []
        for d in (0.0, 0.4, 0.9, 1.5):
            cands += [(cx, y1 - 0.55 - d, 0), (cx, y2 + 0.55 + d, 0),
                      (x1 - 0.6 - d - len(ref) * size * 0.4, cy, 0), (x2 + 0.6 + d + len(ref) * size * 0.4, cy, 0),
                      (x1 - 0.65 - d, cy, 90), (x2 + 0.65 + d, cy, 90)]
        if (x2 - x1) > 5 and (y2 - y1) > 4:
            cands.insert(0, (cx, cy, 0))
        chosen = None
        for (tx, ty, rot) in cands:
            b = text_box(tx, ty, ref, size, rot)
            if b[0] < BX1 + 0.6 or b[1] < BY1 + 0.6 or b[2] > BX2 - 0.6 or b[3] > BY2 - 0.6:
                continue
            if any(_boxes_overlap(b, o, 0.15) for o in obst):
                continue
            if any(_boxes_overlap(b, o, 0.1) for o in holes + placed):
                continue
            if any(_boxes_overlap(b, o, 0.1) for (r2, o) in silk_lines if r2 != ref):
                continue
            chosen = (tx, ty, rot, b)
            break
        res[ref] = chosen
        if chosen:
            placed.append(chosen[3])
    return res


def footprint_silk_boxes():
    """bboxes of footprint silkscreen primitives (absolute)."""
    out = []
    for ref, part in PARTS.items():
        fx, fy, frot = PLACEMENT[ref]
        f = FPS[part.fp]
        for g in f.gfx:
            if g[1] != "F.SilkS":
                continue
            if g[0] == "line":
                _, L, x1, y1, x2, y2, w = g
                a = rot_pt(x1, y1, frot); b = rot_pt(x2, y2, frot)
                out.append((ref, (fx + min(a[0], b[0]) - w / 2, fy + min(a[1], b[1]) - w / 2,
                                  fx + max(a[0], b[0]) + w / 2, fy + max(a[1], b[1]) + w / 2)))
            else:
                _, L, cx, cy, r, w = g
                c = rot_pt(cx, cy, frot)
                out.append((ref, (fx + c[0] - r - w / 2, fy + c[1] - r - w / 2, fx + c[0] + r + w / 2, fy + c[1] + r + w / 2)))
    return out


# board-level silkscreen texts: (text, x, y, size, rot)
BOARD_TEXT = [
    ("STM32G4 CAN ECU  rev A", 160.5, 158.0, 1.2, 0),
    ("8-18V", 101.9, 124.2, 0.9, 90),
    ("+", 107.8, 118.0, 1.2, 0),
    ("-", 107.8, 112.9, 1.2, 0),
    ("CANH", 172.0, 112.9, 0.8, 0),
    ("CANL", 172.0, 117.98, 0.8, 0),
    ("GND", 172.0, 123.06, 0.8, 0),
    ("CANH", 172.0, 129.365, 0.8, 0),
    ("CANL", 172.0, 134.445, 0.8, 0),
    ("GND", 172.0, 139.525, 0.8, 0),
    ("TERM: END NODES ONLY", 163.5, 150.2, 0.7, 0),
    ("SWD 1:3V3 2:CLK 3:GND 4:DIO 5:RST 6:SWO", 152.5, 107.3, 0.7, 0),
    ("STA", 149.0, 153.1, 0.7, 0),
    ("FLT", 151.5, 153.1, 0.7, 0),
    ("TX", 154.0, 153.1, 0.7, 0),
    ("RX", 156.5, 153.1, 0.7, 0),
    ("PWR", 136.0, 102.1, 0.7, 0),
    ("BOOT0", 135.4, 123.0, 0.6, 0),
    ("ID0", 142.0, 145.9, 0.6, 0),
    ("ID1", 145.4, 145.9, 0.6, 0),
    ("RESET", 112.3, 152.9, 0.8, 0),
    ("USER", 122.8, 152.9, 0.8, 0),
    ("1:3V3 3:TX 5:PA4 7:PA6 9:PB0", 135.1, 159.0, 0.6, 0),
]


def write_pcb(silk):
    nt = net_table()
    with open("/home/claude/stm32-can-ecu/hardware/gen/routes.json") as f:
        R = json.load(f)
    o = ['(kicad_pcb (version 20221018) (generator pcbnew)', '',
         '  (general\n    (thickness 1.6)\n  )', '', '  (paper "A4")',
         '  (title_block', f'    (title {q(TITLE)})', f'    (date {q(DATE)})', f'    (rev {q(REV)})',
         '    (comment 1 "4-layer 1.6 mm: F.Cu signal / In1.Cu GND plane / In2.Cu +3V3 plane / B.Cu signal")',
         '    (comment 2 "Zones are NOT pre-filled: press B (Edit > Fill All Zones) after opening")',
         '  )', '',
         '  (layers',
         '    (0 "F.Cu" signal)', '    (1 "In1.Cu" power)', '    (2 "In2.Cu" power)', '    (31 "B.Cu" signal)',
         '    (32 "B.Adhes" user "B.Adhesive")', '    (33 "F.Adhes" user "F.Adhesive")',
         '    (34 "B.Paste" user)', '    (35 "F.Paste" user)',
         '    (36 "B.SilkS" user "B.Silkscreen")', '    (37 "F.SilkS" user "F.Silkscreen")',
         '    (38 "B.Mask" user)', '    (39 "F.Mask" user)',
         '    (40 "Dwgs.User" user "User.Drawings")', '    (41 "Cmts.User" user "User.Comments")',
         '    (42 "Eco1.User" user "User.Eco1")', '    (43 "Eco2.User" user "User.Eco2")',
         '    (44 "Edge.Cuts" user)', '    (45 "Margin" user)',
         '    (46 "B.CrtYd" user "B.Courtyard")', '    (47 "F.CrtYd" user "F.Courtyard")',
         '    (48 "B.Fab" user)', '    (49 "F.Fab" user)',
         '  )', '',
         '  (setup',
         '    (pad_to_mask_clearance 0)',
         '  )', '', '  (net 0 "")']
    for n, i in sorted(nt.items(), key=lambda x: x[1]):
        o.append(f'  (net {i} {q(n)})')
    o.append("")
    # footprints
    for ref, part in PARTS.items():
        fx, fy, frot = PLACEMENT[ref]
        f = FPS[part.fp]
        o.append(f'  (footprint {q(PROJECT + ":" + part.fp)} (layer "F.Cu")')
        o.append(f'    (tstamp {U("fp", ref)})')
        o.append(f'    (at {fmt(fx)} {fmt(fy)}{" " + str(frot) if frot else ""})')
        o.append(f'    (descr {q(part.desc)})')
        o.append(f'    (property "Sheetfile" "{PROJECT}.kicad_sch")')
        o.append('    (property "Sheetname" "")')
        o.append(f'    (path "/{U("sym", ref)}")')
        if f.attr == "exclude":
            o.append("    (attr exclude_from_pos_files exclude_from_bom)")
        else:
            o.append(f"    (attr {f.attr})")
        s = silk.get(ref)
        if s:
            tx, ty, trot, _ = s
            lx, ly = rot_pt(tx - fx, ty - fy, -frot)
            layer = "F.SilkS"
        else:
            lx, ly = f.ref_at
            trot = 0
            layer = "F.Fab"
        o.append(f'    (fp_text reference {q(ref)} (at {fmt(lx)} {fmt(ly)} {trot}) (layer {q(layer)})\n'
                 f'        (effects (font (size 0.8 0.8) (thickness 0.15)))\n      (tstamp {U("ref", ref)})\n    )')
        vrot = 0 if frot in (0, 180) else 90
        o.append(f'    (fp_text value {q(part.value)} (at {fmt(f.val_at[0])} {fmt(f.val_at[1])} {vrot}) (layer "F.Fab")\n'
                 f'        (effects (font (size 0.6 0.6) (thickness 0.1)))\n      (tstamp {U("val", ref)})\n    )')
        if s is None or layer == "F.Fab":
            pass
        o += fp_graphics(f, "    ", tstamps=lambda k, r=ref: U("g", r, k))
        for p in f.pads:
            net = part.pins.get(p.num) if p.num else None
            nn = (nt[net], net) if net else None
            pt = None
            if ref in PARTS and p.num:
                sy = SYMS[part.sym]
                for sp in sy.pins:
                    if sp.num == p.num:
                        pt = "no_connect" if net is None else sp.etype
            o.append("    " + pad_sexpr(p, frot, nn, U("pad", ref, p.num, p.x, p.y), pt))
        o.append("  )")
    o.append("")
    # outline
    for k, prim in enumerate(board_outline()):
        if prim[0] == "line":
            (a, b) = prim[1], prim[2]
            o.append(f'  (gr_line (start {fmt(a[0])} {fmt(a[1])}) (end {fmt(b[0])} {fmt(b[1])})\n'
                     f'    (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (tstamp {U("edge", k)}))')
        else:
            a, m, b = prim[1], prim[2], prim[3]
            o.append(f'  (gr_arc (start {fmt(a[0])} {fmt(a[1])}) (mid {fmt(m[0])} {fmt(m[1])}) (end {fmt(b[0])} {fmt(b[1])})\n'
                     f'    (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (tstamp {U("edge", k)}))')
    for k, (t, x, y, sz, rot) in enumerate(BOARD_TEXT):
        o.append(f'  (gr_text {q(t)} (at {fmt(x)} {fmt(y)}{" " + str(rot) if rot else ""}) (layer "F.SilkS") (tstamp {U("txt", k)})\n'
                 f'    (effects (font (size {fmt(sz)} {fmt(sz)}) (thickness {fmt(max(0.15, sz * 0.15))})))\n  )')
    o.append(f'  (gr_text "80 x 60 mm, 4 layers, 1.6 mm" (at 140 163) (layer "Dwgs.User") (tstamp {U("dim")})\n'
             f'    (effects (font (size 1.5 1.5) (thickness 0.2)))\n  )')
    # tracks / vias
    for k, t in enumerate(R["tracks"]):
        o.append(f'  (segment (start {fmt(t["a"][0])} {fmt(t["a"][1])}) (end {fmt(t["b"][0])} {fmt(t["b"][1])}) '
                 f'(width {fmt(t["w"])}) (layer {q(t["layer"])}) (net {nt[t["net"]]}) (tstamp {U("seg", k)}))')
    for k, v in enumerate(R["vias"]):
        o.append(f'  (via (at {fmt(v["at"][0])} {fmt(v["at"][1])}) (size {fmt(v["size"])}) (drill {fmt(v["drill"])}) '
                 f'(layers "F.Cu" "B.Cu") (net {nt[v["net"]]}) (tstamp {U("via", k)}))')
    # zones
    poly = outline_polygon(0.0, 8)
    pts = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in poly)
    for k, (layer, net, prio) in enumerate([("In1.Cu", "GND", 0), ("In2.Cu", "+3V3", 0),
                                            ("F.Cu", "GND", 0), ("B.Cu", "GND", 0)]):
        o.append(f'  (zone (net {nt[net]}) (net_name {q(net)}) (layer {q(layer)}) (tstamp {U("zone", layer)}) '
                 f'(name {q(net + "_" + layer.split(".")[0])}) (hatch edge 0.5)\n'
                 f'    (priority {prio})\n'
                 f'    (connect_pads (clearance 0.25))\n'
                 f'    (min_thickness 0.25) (filled_areas_thickness no)\n'
                 f'    (fill (thermal_gap 0.3) (thermal_bridge_width 0.4))\n'
                 f'    (polygon\n      (pts\n        {pts}\n      )\n    )\n  )')
    o.append(")")
    open(os.path.join(OUT, f"{PROJECT}.kicad_pcb"), "w").write("\n".join(o) + "\n")


# =====================================================================
# project file
# =====================================================================
def write_project():
    nc = lambda name, clr, tw, vd=0.6, vdr=0.3: {
        "name": name, "clearance": clr, "track_width": tw, "via_diameter": vd, "via_drill": vdr,
        "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2,
        "microvia_diameter": 0.3, "microvia_drill": 0.1, "wire_width": 6, "bus_width": 12,
        "line_style": 0, "schematic_color": "rgba(0, 0, 0, 0.000)", "pcb_color": "rgba(0, 0, 0, 0.000)"}
    pro = {
        "board": {
            "3dviewports": [],
            "design_settings": {
                "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                             "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "silk_line_width": 0.12,
                             "silk_text_size_h": 0.8, "silk_text_size_v": 0.8, "silk_text_thickness": 0.12},
                "rules": {"min_clearance": 0.2, "min_connection": 0.0, "min_copper_edge_clearance": 0.3,
                          "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25, "min_microvia_diameter": 0.2,
                          "min_microvia_drill": 0.1, "min_resolved_spokes": 2, "min_silk_clearance": 0.0,
                          "min_text_height": 0.6, "min_text_thickness": 0.1, "min_through_hole_diameter": 0.3,
                          "min_track_width": 0.2, "min_via_annular_width": 0.13, "min_via_diameter": 0.5,
                          "solder_mask_to_copper_clearance": 0.0, "use_height_for_length_calcs": True},
                "track_widths": [0.0, 0.25, 0.3, 0.4, 0.5, 0.8, 1.0],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}],
                "diff_pair_dimensions": [],
                "teardrop_options": [], "teardrop_parameters": [],
            },
            "layer_presets": [], "viewports": []},
        "boards": [], "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 1},
        "net_settings": {
            "classes": [nc("Default", 0.2, 0.25), nc("Power", 0.2, 0.5), nc("CAN", 0.2, 0.4)],
            "meta": {"version": 3},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Power", "pattern": p} for p in
                                  ["GND", "+3V3", "+3V3A", "+5V", "VIN_RAW", "VIN_FUSED", "VIN_PROT"]] +
                                 [{"netclass": "CAN", "pattern": p} for p in ["CANH", "CANL", "TERM_*"]],
        },
        "pcbnew": {"last_paths": {"gencad": "", "idf": "", "netlist": "", "specctra_dsn": "", "step": "",
                                  "vrml": ""}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[ROOT, ""]],
        "text_variables": {},
    }
    open(os.path.join(OUT, f"{PROJECT}.kicad_pro"), "w").write(json.dumps(pro, indent=2) + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    write_symbol_lib()
    write_fp_lib()
    write_lib_tables()
    pos, ann = write_schematic()
    obst = [text_box(x, y, t, s, r) for (t, x, y, s, r) in BOARD_TEXT]
    silk = place_silk_refs(obst)
    write_pcb(silk)
    write_project()
    json.dump({"sch_pos": pos, "silk": {k: (v[:3] if v else None) for k, v in silk.items()}},
              open("/home/claude/stm32-can-ecu/hardware/gen/layout_meta.json", "w"), indent=1)
    missing = [r for r, v in silk.items() if v is None and not r.startswith("H")]
    print("refs moved to F.Fab (no free silk spot):", missing)


if __name__ == "__main__":
    main()
