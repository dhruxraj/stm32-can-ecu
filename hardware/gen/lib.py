"""
lib.py - footprint + schematic-symbol definitions for the STM32 CAN ECU board.

All footprint geometry below is modelled on the equivalent KiCad standard-library
footprint (name given in `std`).  Dimensions were taken from those standard
footprints / manufacturer land patterns as far as known; every footprint is
listed in docs/FOOTPRINTS.md with a "verify" note.  Units: mm.
Coordinates follow KiCad conventions (Y axis points DOWN in footprints/PCB,
Y axis points UP inside symbol definitions).
"""
import math

# --------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------
def fmt(v):
    """Format a number the way KiCad does (no trailing zeros)."""
    if isinstance(v, str):
        return v
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    return s


def rot_pt(lx, ly, rot):
    """Rotate a footprint-local point by `rot` degrees (KiCad CCW-on-screen)."""
    a = math.radians(rot)
    c, s = math.cos(a), math.sin(a)
    x = lx * c + ly * s
    y = -lx * s + ly * c
    return (round(x, 6), round(y, 6))


# --------------------------------------------------------------------------
# Footprints
# --------------------------------------------------------------------------
class Pad:
    def __init__(self, num, kind, shape, x, y, w, h, drill=None, rratio=0.25, angle=0):
        self.num, self.kind, self.shape = num, kind, shape
        self.x, self.y, self.w, self.h = x, y, w, h
        self.drill, self.rratio, self.angle = drill, rratio, angle

    @property
    def layers(self):
        if self.kind == "smd":
            return ["F.Cu", "F.Paste", "F.Mask"]
        if self.kind == "smd_nopaste":
            return ["F.Cu", "F.Mask"]
        return ["*.Cu", "*.Mask"]


class Footprint:
    def __init__(self, name, std, attr="smd"):
        self.name = name          # name inside project library CAN_ECU.pretty
        self.std = std            # equivalent KiCad standard-library footprint
        self.attr = attr
        self.pads = []
        self.gfx = []             # (kind, layer, params...)
        self.crt = None           # courtyard rect (x1,y1,x2,y2)
        self.ref_at = (0, -2)
        self.val_at = (0, 2)
        self.body = None          # fab rect

    def pad(self, *a, **k):
        p = Pad(*a, **k)
        self.pads.append(p)
        return p

    def line(self, layer, x1, y1, x2, y2, w):
        self.gfx.append(("line", layer, x1, y1, x2, y2, w))

    def rect(self, layer, x1, y1, x2, y2, w):
        for (a, b, c, d) in ((x1, y1, x2, y1), (x2, y1, x2, y2), (x2, y2, x1, y2), (x1, y2, x1, y1)):
            self.line(layer, a, b, c, d, w)

    def circle(self, layer, cx, cy, r, w):
        self.gfx.append(("circle", layer, cx, cy, r, w))

    def finish(self, body, crt_margin=0.25, silk=True, pin1_mark=None):
        """body=(x1,y1,x2,y2) fab outline. Courtyard = union(body, pads)+margin."""
        self.body = body
        self.rect("F.Fab", *body, 0.1)
        xs = [body[0], body[2]]
        ys = [body[1], body[3]]
        for p in self.pads:
            hw, hh = p.w / 2, p.h / 2
            if p.angle in (90, 270):
                hw, hh = hh, hw
            xs += [p.x - hw, p.x + hw]
            ys += [p.y - hh, p.y + hh]
        x1, x2 = min(xs) - crt_margin, max(xs) + crt_margin
        y1, y2 = min(ys) - crt_margin, max(ys) + crt_margin
        # round courtyard to 0.05 grid
        r = lambda v, f: (math.floor if f else math.ceil)(v / 0.05) * 0.05
        self.crt = (round(r(x1, 1), 3), round(r(y1, 1), 3), round(r(x2, 0), 3), round(r(y2, 0), 3))
        self.rect("F.CrtYd", *self.crt, 0.05)
        if pin1_mark:
            self.circle("F.SilkS", pin1_mark[0], pin1_mark[1], 0.15, 0.3)
        self.ref_at = (0, round(self.crt[1] - 0.7, 2))
        self.val_at = (0, round(self.crt[3] + 0.7, 2))
        return self


def fp_two_terminal(name, std, pitch, pw, ph, body_l, body_w, shape="roundrect", silk_gap=True):
    f = Footprint(name, std)
    f.pad("1", "smd", shape, -pitch / 2, 0, pw, ph)
    f.pad("2", "smd", shape, pitch / 2, 0, pw, ph)
    f.finish((-body_l / 2, -body_w / 2, body_l / 2, body_w / 2))
    # silk: two short lines above/below body, clear of pads
    xs = max(0.0, pitch / 2 - pw / 2 - 0.25)
    if xs > 0.15:
        yy = max(body_w / 2, ph / 2) + 0.15
        f.line("F.SilkS", -xs, -yy, xs, -yy, 0.12)
        f.line("F.SilkS", -xs, yy, xs, yy, 0.12)
    return f


def fp_diode(name, std, pitch, pw, ph, body_l, body_w):
    """pad1 = cathode (KiCad convention); silk cathode bar on pad-1 side."""
    f = fp_two_terminal(name, std, pitch, pw, ph, body_l, body_w, shape="rect")
    xb = -pitch / 2 - pw / 2 - 0.3
    yy = max(body_w, ph) / 2 + 0.1
    f.line("F.SilkS", xb, -yy, xb, yy, 0.2)
    return f


def fp_led0603():
    f = fp_two_terminal("LED_0603_1608Metric", "LED_SMD:LED_0603_1608Metric", 1.575, 0.875, 0.95, 1.6, 0.8)
    # cathode mark (pad 1)
    f.line("F.SilkS", -1.5, -0.6, -1.5, 0.6, 0.15)
    return f


def fp_soic8():
    f = Footprint("SOIC-8_3.9x4.9mm_P1.27mm", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
    ys = [-1.905, -0.635, 0.635, 1.905]
    for i, y in enumerate(ys):
        f.pad(str(i + 1), "smd", "roundrect", -2.475, y, 1.95, 0.6)
    for i, y in enumerate(reversed(ys)):
        f.pad(str(i + 5), "smd", "roundrect", 2.475, y, 1.95, 0.6)
    f.finish((-1.95, -2.45, 1.95, 2.45))
    f.line("F.SilkS", -1.95, -2.56, 1.95, -2.56, 0.12)
    f.line("F.SilkS", -1.95, 2.56, 1.95, 2.56, 0.12)
    f.circle("F.SilkS", -3.6, -2.4, 0.15, 0.3)
    return f


def fp_lqfp48():
    f = Footprint("LQFP-48_7x7mm_P0.5mm", "Package_QFP:LQFP-48_7x7mm_P0.5mm")
    e, L, W = 4.1625, 1.475, 0.3
    for i in range(12):
        off = -2.75 + 0.5 * i
        f.pad(str(1 + i), "smd", "roundrect", -e, off, L, W)
        f.pad(str(13 + i), "smd", "roundrect", off, e, W, L)
        f.pad(str(25 + i), "smd", "roundrect", e, -off, L, W)
        f.pad(str(37 + i), "smd", "roundrect", -off, -e, W, L)
    f.finish((-3.5, -3.5, 3.5, 3.5))
    # silk corner marks
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.line("F.SilkS", sx * 3.61, sy * 3.61, sx * 3.16, sy * 3.61, 0.12)
            f.line("F.SilkS", sx * 3.61, sy * 3.61, sx * 3.61, sy * 3.16, 0.12)
    f.circle("F.SilkS", -4.9, -3.4, 0.15, 0.3)
    return f


def fp_sot23():
    f = Footprint("SOT-23", "Package_TO_SOT_SMD:SOT-23")
    f.pad("1", "smd", "roundrect", -1.1375, -0.95, 1.325, 0.6)
    f.pad("2", "smd", "roundrect", -1.1375, 0.95, 1.325, 0.6)
    f.pad("3", "smd", "roundrect", 1.1375, 0, 1.325, 0.6)
    f.finish((-0.65, -1.45, 0.65, 1.45))
    f.line("F.SilkS", 0, -1.56, 0.76, -1.56, 0.12)
    f.line("F.SilkS", 0, 1.56, 0.76, 1.56, 0.12)
    return f


def fp_sot23_5():
    f = Footprint("SOT-23-5", "Package_TO_SOT_SMD:SOT-23-5")
    for i, y in enumerate([-0.95, 0, 0.95]):
        f.pad(str(i + 1), "smd", "roundrect", -1.1375, y, 1.325, 0.6)
    f.pad("4", "smd", "roundrect", 1.1375, 0.95, 1.325, 0.6)
    f.pad("5", "smd", "roundrect", 1.1375, -0.95, 1.325, 0.6)
    f.finish((-0.8, -1.45, 0.8, 1.45))
    f.line("F.SilkS", -0.3, -1.56, 0.3, -1.56, 0.12)
    f.line("F.SilkS", -0.3, 1.56, 0.3, 1.56, 0.12)
    f.circle("F.SilkS", -1.9, -1.5, 0.12, 0.24)
    return f


def fp_lga14():
    """LSM6DS3TR-C LGA-14L 2.5x3.0 mm, pitch 0.5.  4 pads on each 3.0 mm side,
    3 pads on each 2.5 mm side.  Pin numbering CCW from top-left.
    Modelled on KiCad Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y.
    >>> VERIFY pad sizes against ST land-pattern recommendation <<<"""
    f = Footprint("LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
                  "Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y")
    sx, sy = 1.05, 1.30         # pad centre offsets
    lw, ll = 0.25, 0.50         # pad width (along pitch), length
    ys = [-0.75, -0.25, 0.25, 0.75]
    xs = [-0.5, 0.0, 0.5]
    for i, y in enumerate(ys):                       # 1..4 left, top->bottom
        f.pad(str(1 + i), "smd", "rect", -sx, y, ll, lw)
    for i, x in enumerate(xs):                       # 5..7 bottom, left->right
        f.pad(str(5 + i), "smd", "rect", x, sy, lw, ll)
    for i, y in enumerate(reversed(ys)):             # 8..11 right, bottom->top
        f.pad(str(8 + i), "smd", "rect", sx, y, ll, lw)
    for i, x in enumerate(reversed(xs)):             # 12..14 top, right->left
        f.pad(str(12 + i), "smd", "rect", x, -sy, lw, ll)
    f.finish((-1.25, -1.5, 1.25, 1.5), crt_margin=0.3)
    f.circle("F.SilkS", -1.75, -1.75, 0.12, 0.24)
    return f


def fp_xtal3225():
    f = Footprint("Crystal_SMD_3225-4Pin_3.2x2.5mm", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm")
    f.pad("1", "smd", "rect", -1.1, 0.85, 1.4, 1.2)
    f.pad("2", "smd", "rect", 1.1, 0.85, 1.4, 1.2)
    f.pad("3", "smd", "rect", 1.1, -0.85, 1.4, 1.2)
    f.pad("4", "smd", "rect", -1.1, -0.85, 1.4, 1.2)
    f.finish((-1.6, -1.25, 1.6, 1.25))
    f.circle("F.SilkS", -2.2, 1.7, 0.12, 0.24)
    return f


def fp_terminal(n):
    """Generic 5.08 mm pitch PCB screw terminal (Phoenix MKDS 1,5 / KF301 style).
    Pins along +X, wire entry on the -Y face.  VERIFY body outline vs chosen part."""
    f = Footprint(f"TerminalBlock_1x{n:02d}_P5.08mm_Horizontal",
                  f"TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-{n}-5.08_1x{n:02d}_P5.08mm_Horizontal",
                  attr="through_hole")
    for i in range(n):
        f.pad(str(i + 1), "thru_hole", "rect" if i == 0 else "circle", i * 5.08, 0, 2.6, 2.6, drill=1.3)
    x2 = (n - 1) * 5.08 + 2.54 + 0.2
    f.finish((-2.74, -4.2, x2, 4.0), crt_margin=0.3)
    f.rect("F.SilkS", -2.86, -4.32, x2 + 0.12, 4.12, 0.12)
    return f


def fp_pinheader(cols, rows, name=None):
    """KiCad PinHeader_{cols}x{rows}_P2.54mm_Vertical: pin1 at (0,0);
    for 2 columns odd pins in column 0, even pins in column 1."""
    nm = name or f"PinHeader_{cols}x{rows:02d}_P2.54mm_Vertical"
    f = Footprint(nm, f"Connector_PinHeader_2.54mm:PinHeader_{cols}x{rows:02d}_P2.54mm_Vertical",
                  attr="through_hole")
    k = 1
    for r in range(rows):
        for c in range(cols):
            f.pad(str(k), "thru_hole", "rect" if k == 1 else "oval", c * 2.54, r * 2.54, 1.7, 1.7, drill=1.0)
            k += 1
    x2 = (cols - 1) * 2.54 + 1.27
    y2 = (rows - 1) * 2.54 + 1.27
    f.finish((-1.27, -1.27, x2, y2), crt_margin=0.3)
    f.rect("F.SilkS", -1.39, -1.39, x2 + 0.12, y2 + 0.12, 0.12)
    return f


def fp_sw6mm():
    f = Footprint("SW_PUSH_6mm", "Button_Switch_THT:SW_PUSH_6mm", attr="through_hole")
    f.pad("1", "thru_hole", "circle", 0, 0, 2.0, 2.0, drill=1.1)
    f.pad("2", "thru_hole", "circle", 0, 4.5, 2.0, 2.0, drill=1.1)
    f.pad("1", "thru_hole", "circle", 6.5, 0, 2.0, 2.0, drill=1.1)
    f.pad("2", "thru_hole", "circle", 6.5, 4.5, 2.0, 2.0, drill=1.1)
    f.finish((0.25, -0.75, 6.25, 5.25), crt_margin=0.3)
    f.rect("F.SilkS", 1.2, -0.9, 5.3, 5.4, 0.12)
    f.circle("F.SilkS", 3.25, 2.25, 1.6, 0.12)
    return f


def fp_sip3_r78():
    """RECOM R-78E SIP-3 module, pitch 2.54 mm.  Body 11.6 x 8.5 x 10.4 mm.
    Courtyard reserves +-6.5 mm around the pin row because the exact pin offset
    inside the 8.5 mm body depth must be checked against the RECOM drawing."""
    f = Footprint("Converter_DCDC_RECOM_R-78E-0.5_THT", "Converter_DCDC:Converter_DCDC_RECOM_R-78E-0.5_THT",
                  attr="through_hole")
    for i in range(3):
        f.pad(str(i + 1), "thru_hole", "rect" if i == 0 else "oval", i * 2.54, 0, 1.8, 1.8, drill=1.0)
    f.finish((-3.26, -4.25, 8.34, 4.25), crt_margin=0.2)
    f.crt = (-3.46, -6.5, 8.54, 6.5)
    f.gfx = [g for g in f.gfx if g[1] != "F.CrtYd"]
    f.rect("F.CrtYd", *f.crt, 0.05)
    f.rect("F.SilkS", -3.38, -4.37, 8.46, 4.37, 0.12)
    f.ref_at = (2.54, -5.2)
    f.val_at = (2.54, 5.2)
    return f


def fp_cp_radial():
    f = Footprint("CP_Radial_D6.3mm_P2.50mm", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", attr="through_hole")
    f.pad("1", "thru_hole", "rect", 0, 0, 1.6, 1.6, drill=0.8)
    f.pad("2", "thru_hole", "circle", 2.5, 0, 1.6, 1.6, drill=0.8)
    f.finish((1.25 - 3.15, -3.15, 1.25 + 3.15, 3.15), crt_margin=0.25)
    f.circle("F.SilkS", 1.25, 0, 3.27, 0.12)
    f.line("F.SilkS", -1.9, -2.2, -1.1, -2.2, 0.12)   # '+' mark
    f.line("F.SilkS", -1.5, -2.6, -1.5, -1.8, 0.12)
    return f


def fp_solderjumper():
    f = Footprint("SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm", "Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm")
    f.pad("1", "smd_nopaste", "rect", -0.65, 0, 1.0, 1.5)
    f.pad("2", "smd_nopaste", "rect", 0.65, 0, 1.0, 1.5)
    f.finish((-1.15, -0.75, 1.15, 0.75))
    f.rect("F.SilkS", -1.4, -1.0, 1.4, 1.0, 0.12)
    return f


def fp_testpoint():
    f = Footprint("TestPoint_Pad_D1.5mm", "TestPoint:TestPoint_Pad_D1.5mm")
    f.pad("1", "smd_nopaste", "circle", 0, 0, 1.5, 1.5)
    f.finish((-0.75, -0.75, 0.75, 0.75))
    f.circle("F.SilkS", 0, 0, 0.95, 0.12)
    return f


def fp_mhole():
    f = Footprint("MountingHole_3.2mm_M3", "MountingHole:MountingHole_3.2mm_M3", attr="exclude")
    f.pad("", "np_thru_hole", "circle", 0, 0, 3.2, 3.2, drill=3.2)
    f.finish((-1.6, -1.6, 1.6, 1.6), crt_margin=0)
    f.crt = (-3.45, -3.45, 3.45, 3.45)
    f.gfx = [g for g in f.gfx if g[1] != "F.CrtYd"]
    f.circle("F.CrtYd", 0, 0, 3.45, 0.05)
    f.circle("Cmts.User", 0, 0, 3.2, 0.15)
    return f


def build_footprints():
    F = {}
    def add(f):
        F[f.name] = f
    add(fp_two_terminal("R_0603_1608Metric", "Resistor_SMD:R_0603_1608Metric", 1.65, 0.8, 0.95, 1.6, 0.8))
    add(fp_two_terminal("C_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric", 1.55, 0.9, 0.95, 1.6, 0.8))
    add(fp_two_terminal("L_0603_1608Metric", "Inductor_SMD:L_0603_1608Metric", 1.575, 0.875, 0.95, 1.6, 0.8))
    add(fp_two_terminal("C_0805_2012Metric", "Capacitor_SMD:C_0805_2012Metric", 1.9, 1.0, 1.45, 2.0, 1.25))
    add(fp_two_terminal("R_0805_2012Metric", "Resistor_SMD:R_0805_2012Metric", 1.825, 1.025, 1.4, 2.0, 1.25))
    add(fp_two_terminal("C_1210_3225Metric", "Capacitor_SMD:C_1210_3225Metric", 3.0, 1.15, 2.7, 3.2, 2.5))
    add(fp_two_terminal("Fuse_1812_4532Metric", "Fuse:Fuse_1812_4532Metric", 4.275, 1.325, 3.4, 4.5, 3.2))
    add(fp_diode("D_SMA", "Diode_SMD:D_SMA", 4.0, 2.5, 1.8, 4.3, 2.6))
    add(fp_diode("D_SMB", "Diode_SMD:D_SMB", 4.3, 2.5, 2.3, 4.3, 3.6))
    add(fp_led0603())
    add(fp_soic8())
    add(fp_lqfp48())
    add(fp_sot23())
    add(fp_sot23_5())
    add(fp_lga14())
    add(fp_xtal3225())
    add(fp_terminal(2))
    add(fp_terminal(3))
    add(fp_pinheader(1, 6))
    add(fp_pinheader(2, 5))
    add(fp_pinheader(2, 2))
    add(fp_sw6mm())
    add(fp_sip3_r78())
    add(fp_cp_radial())
    add(fp_solderjumper())
    add(fp_testpoint())
    add(fp_mhole())
    return F


# --------------------------------------------------------------------------
# Schematic symbols
# --------------------------------------------------------------------------
class SymPin:
    def __init__(self, num, name, etype, x, y, angle, length=2.54, hidden=False):
        self.num, self.name, self.etype = num, name, etype
        self.x, self.y, self.angle, self.length, self.hidden = x, y, angle, length, hidden


class Symbol:
    def __init__(self, name, prefix, desc="", power=False):
        self.name, self.prefix, self.desc, self.power = name, prefix, desc, power
        self.pins = []
        self.gfx = []            # raw s-expr strings (symbol units "_0_1")
        self.show_pin_numbers = True
        self.show_pin_names = True
        self.name_offset = 0.508
        self.ref_at = (0, 0, 0)
        self.val_at = (0, 0, 0)
        self.in_bom = True
        self.on_board = True

    def pin(self, *a, **k):
        self.pins.append(SymPin(*a, **k))


def _rect(x1, y1, x2, y2, fill="background"):
    return (f"(rectangle (start {fmt(x1)} {fmt(y1)}) (end {fmt(x2)} {fmt(y2)}) "
            f"(stroke (width 0.254) (type default)) (fill (type {fill})))")


def _poly(pts, w=0.254, fill="none"):
    p = " ".join(f"(xy {fmt(x)} {fmt(y)})" for x, y in pts)
    return f"(polyline (pts {p}) (stroke (width {fmt(w)}) (type default)) (fill (type {fill})))"


def sym_ic(name, prefix, left, right, top=(), bottom=(), width=15.24, desc=""):
    """left/right/top/bottom: list of (num, name, etype) or None for a gap."""
    s = Symbol(name, prefix, desc)
    n = max(len(left), len(right), 1)
    h = (n + 1) * 2.54
    top_y = round((n - 1) / 2 * 2.54, 2)
    top_y = round(math.ceil(top_y / 2.54) * 2.54, 2)
    for i, p in enumerate(left):
        if p:
            s.pin(p[0], p[1], p[2], -width / 2 - 2.54, top_y - i * 2.54, 0)
    for i, p in enumerate(right):
        if p:
            s.pin(p[0], p[1], p[2], width / 2 + 2.54, top_y - i * 2.54, 180)
    ybot = top_y - (n - 1) * 2.54 - 2.54
    ytop = top_y + 2.54
    nt = len(top)
    for i, p in enumerate(top):
        if p:
            s.pin(p[0], p[1], p[2], round((i - (nt - 1) / 2) * 2.54, 2), ytop + 2.54, 270)
    nb = len(bottom)
    for i, p in enumerate(bottom):
        if p:
            s.pin(p[0], p[1], p[2], round((i - (nb - 1) / 2) * 2.54, 2), ybot - 2.54, 90)
    s.gfx.append(_rect(-width / 2, ytop, width / 2, ybot))
    s.ref_at = (-width / 2, ytop + (5.08 if top else 1.27), 0)
    s.val_at = (-width / 2, ybot - (5.08 if bottom else 1.27), 0)
    s.body = (-width / 2, ytop, width / 2, ybot)
    return s


def sym_two(name, prefix, kind, desc=""):
    """Vertical two-pin passive: pin 1 top, pin 2 bottom (for diodes pin1=K at bottom)."""
    s = Symbol(name, prefix, desc)
    s.show_pin_numbers = False
    s.show_pin_names = False
    if kind in ("D", "LED", "TVS", "SCHOTTKY"):
        # pin 2 = anode at top, pin 1 = cathode at bottom -> current flows downwards
        s.pin("2", "A", "passive", 0, 3.81, 270, length=1.27)
        s.pin("1", "K", "passive", 0, -3.81, 90, length=1.27)
        s.gfx.append(_poly([(-1.27, 1.27), (1.27, 1.27), (0, -1.27), (-1.27, 1.27)], fill="none"))
        if kind == "SCHOTTKY":
            s.gfx.append(_poly([(-1.27, -0.762), (-1.27, -1.27), (1.27, -1.27), (1.27, -1.778)]))
        elif kind == "TVS":
            s.gfx.append(_poly([(-1.778, -0.762), (-1.27, -1.27), (1.27, -1.27), (1.778, -1.778)]))
        else:
            s.gfx.append(_poly([(-1.27, -1.27), (1.27, -1.27)]))
        if kind == "LED":
            s.gfx.append(_poly([(1.778, 0.508), (2.794, -0.508)]))
            s.gfx.append(_poly([(1.778, -0.254), (2.794, -1.27)]))
    else:
        s.pin("1", "~", "passive", 0, 3.81, 270, length=1.27)
        s.pin("2", "~", "passive", 0, -3.81, 90, length=1.27)
        if kind == "R":
            s.gfx.append(_rect(-1.016, 2.54, 1.016, -2.54, fill="none"))
        elif kind == "C":
            s.gfx.append(_poly([(-2.032, 0.762), (2.032, 0.762)], w=0.508))
            s.gfx.append(_poly([(-2.032, -0.762), (2.032, -0.762)], w=0.508))
            s.gfx.append(_poly([(0, 2.54), (0, 0.762)]))
            s.gfx.append(_poly([(0, -2.54), (0, -0.762)]))
        elif kind == "CP":
            s.gfx.append(_rect(-2.286, 1.016, 2.286, 0.508, fill="none"))
            s.gfx.append(_rect(-2.286, -0.508, 2.286, -1.016, fill="outline"))
            s.gfx.append(_poly([(-1.778, 2.286), (-0.762, 2.286)]))
            s.gfx.append(_poly([(-1.27, 2.794), (-1.27, 1.778)]))
            s.gfx.append(_poly([(0, 2.54), (0, 1.016)]))
            s.gfx.append(_poly([(0, -2.54), (0, -1.016)]))
        elif kind == "FB":
            s.gfx.append(_poly([(-1.8, 0.4), (-0.4, 1.8), (1.8, -0.4), (0.4, -1.8), (-1.8, 0.4)]))
            s.gfx.append(_poly([(0, 2.54), (0, 1.1)]))
            s.gfx.append(_poly([(0, -2.54), (0, -1.1)]))
        elif kind == "F":
            s.gfx.append(_rect(-0.762, 2.032, 0.762, -2.032, fill="none"))
            s.gfx.append(_poly([(0, 2.54), (0, -2.54)]))
        elif kind == "SW":
            s.gfx.append(_poly([(0, 2.54), (0, 1.27)]))
            s.gfx.append(_poly([(0, -2.54), (0, -1.27)]))
            s.gfx.append(_poly([(0, -1.27), (-1.524, 1.016)]))
            s.gfx.append(_poly([(-2.286, 0), (-1.27, 0)]))
        elif kind == "JP":
            s.gfx.append(_poly([(0, 2.54), (0, 0.762)]))
            s.gfx.append(_poly([(0, -2.54), (0, -0.762)]))
            s.gfx.append(_poly([(-0.762, 0.508), (0.762, 0.508)]))
            s.gfx.append(_poly([(-0.762, -0.508), (0.762, -0.508)]))
    s.ref_at = (2.54, 1.27, 0)
    s.val_at = (2.54, -1.27, 0)
    s.body = (-2.3, 2.6, 2.3, -2.6)
    return s


def sym_conn(name, prefix, n, cols=1, desc=""):
    s = Symbol(name, prefix, desc)
    s.show_pin_names = False
    rows = n // cols
    top = round(math.ceil(((rows - 1) / 2 * 2.54) / 2.54) * 2.54, 2)
    k = 1
    for r in range(rows):
        y = top - r * 2.54
        s.pin(str(k), f"Pin_{k}", "passive", -5.08, y, 0); k += 1
        if cols == 2:
            s.pin(str(k), f"Pin_{k}", "passive", 5.08 + 2.54, y, 180); k += 1
    x2 = 5.08 if cols == 2 else 1.27
    s.gfx.append(_rect(-2.54, top + 1.27, x2, top - (rows - 1) * 2.54 - 1.27))
    s.ref_at = (-2.54, top + 2.54, 0)
    s.val_at = (-2.54, top - (rows - 1) * 2.54 - 2.54, 0)
    s.body = (-2.54, top + 1.27, x2, top - (rows - 1) * 2.54 - 1.27)
    return s


def sym_testpoint():
    s = Symbol("TestPoint", "TP", "Test point")
    s.show_pin_numbers = False
    s.show_pin_names = False
    s.pin("1", "1", "passive", 0, -2.54, 90, length=2.54)
    s.gfx.append("(circle (center 0 0.762) (radius 0.762) (stroke (width 0) (type default)) (fill (type none)))")
    s.ref_at = (1.524, 1.27, 0)
    s.val_at = (1.524, -0.254, 0)
    s.body = (-0.8, 1.6, 0.8, 0)
    return s


def sym_mhole():
    s = Symbol("MountingHole", "H", "Mounting hole (no electrical connection)")
    s.in_bom = False
    s.gfx.append("(circle (center 0 0) (radius 1.27) (stroke (width 1.27) (type default)) (fill (type none)))")
    s.ref_at = (0, 3.175, 0)
    s.val_at = (0, -3.175, 0)
    s.body = (-1.3, 1.3, 1.3, -1.3)
    return s


def sym_pwrflag():
    s = Symbol("PWR_FLAG", "#FLG", "Marks a net as driven by a power source (ERC only)", power=True)
    s.in_bom = False
    s.on_board = False
    s.show_pin_numbers = False
    s.show_pin_names = False
    s.pin("1", "pwr", "power_out", 0, 0, 90, length=0)
    s.gfx.append(_poly([(0, 0), (0, 1.27), (-1.016, 1.905), (0, 2.54), (1.016, 1.905), (0, 1.27)]))
    s.ref_at = (0, 1.905, 0)
    s.val_at = (0, 3.81, 0)
    s.body = (-1.1, 2.6, 1.1, 0)
    return s


def build_symbols():
    S = {}
    def add(s):
        S[s.name] = s
    for k, nm, pre, d in [("R", "R", "R", "Resistor"), ("C", "C", "C", "Capacitor"),
                          ("CP", "C_Polarized", "C", "Polarised capacitor"),
                          ("FB", "FerriteBead", "FB", "Ferrite bead"),
                          ("F", "Polyfuse", "F", "Resettable PTC fuse"),
                          ("LED", "LED", "D", "Light emitting diode (pin1=K)"),
                          ("SCHOTTKY", "D_Schottky", "D", "Schottky diode (pin1=K)"),
                          ("TVS", "D_TVS", "D", "Unidirectional TVS diode (pin1=K)"),
                          ("SW", "SW_Push", "SW", "Momentary push button"),
                          ("JP", "SolderJumper_2_Open", "JP", "2-pad solder jumper (open)")]:
        add(sym_two(nm, pre, k, d))
    add(sym_conn("Conn_01x02", "J", 2, desc="2-pin connector"))
    add(sym_conn("Conn_01x03", "J", 3, desc="3-pin connector"))
    add(sym_conn("Conn_01x06", "J", 6, desc="6-pin connector"))
    add(sym_conn("Conn_02x05", "J", 10, cols=2, desc="2x5 connector"))
    add(sym_conn("Conn_02x02", "JP", 4, cols=2, desc="2x2 jumper header"))
    add(sym_testpoint())
    add(sym_mhole())
    add(sym_pwrflag())

    # ---- STM32G431CBTx (pin numbers from DS12589 Rev 6, Table 12, LQFP48 column)
    left = [("1", "VBAT", "power_in"), ("24", "VDD", "power_in"), ("36", "VDD", "power_in"),
            ("48", "VDD", "power_in"), ("21", "VDDA", "power_in"), ("20", "VREF+", "power_in"),
            None,
            ("7", "PG10-NRST", "bidirectional"), ("45", "PB8-BOOT0", "bidirectional"),
            ("5", "PF0-OSC_IN", "bidirectional"), ("6", "PF1-OSC_OUT", "bidirectional"),
            ("3", "PC14-OSC32_IN", "bidirectional"), ("4", "PC15-OSC32_OUT", "bidirectional"),
            None,
            ("23", "VSS", "power_in"), ("35", "VSS", "power_in"), ("47", "VSS", "power_in"),
            ("19", "VSSA", "power_in")]
    right = [("8", "PA0", "bidirectional"), ("9", "PA1", "bidirectional"),
             ("10", "PA2", "bidirectional"), ("11", "PA3", "bidirectional"),
             ("12", "PA4", "bidirectional"), ("13", "PA5", "bidirectional"),
             ("14", "PA6", "bidirectional"), ("15", "PA7", "bidirectional"),
             ("30", "PA8", "bidirectional"), ("31", "PA9", "bidirectional"),
             ("32", "PA10", "bidirectional"), ("33", "PA11", "bidirectional"),
             ("34", "PA12", "bidirectional"), ("37", "PA13", "bidirectional"),
             ("38", "PA14", "bidirectional"), ("39", "PA15", "bidirectional"),
             None,
             ("16", "PB0", "bidirectional"), ("17", "PB1", "bidirectional"),
             ("18", "PB2", "bidirectional"), ("40", "PB3", "bidirectional"),
             ("41", "PB4", "bidirectional"), ("42", "PB5", "bidirectional"),
             ("43", "PB6", "bidirectional"), ("44", "PB7", "bidirectional"),
             ("46", "PB9", "bidirectional"), ("22", "PB10", "bidirectional"),
             ("25", "PB11", "bidirectional"), ("26", "PB12", "bidirectional"),
             ("27", "PB13", "bidirectional"), ("28", "PB14", "bidirectional"),
             ("29", "PB15", "bidirectional"), None, ("2", "PC13", "bidirectional")]
    add(sym_ic("STM32G431CBTx", "U", left, right, width=22.86,
               desc="STM32G431CBT6, Arm Cortex-M4 170 MHz, 128 KB Flash, FDCAN, LQFP48"))
    add(sym_ic("TJA1051T-3", "U",
               [("1", "TXD", "input"), ("4", "RXD", "output"), ("8", "S", "input"), None, ("2", "GND", "power_in")],
               [("3", "VCC", "power_in"), ("5", "VIO", "power_in"), None, ("7", "CANH", "bidirectional"),
                ("6", "CANL", "bidirectional")], width=12.7,
               desc="NXP TJA1051T/3 high-speed CAN FD transceiver with VIO, SO8"))
    add(sym_ic("LSM6DS3TR-C", "U",
               [("13", "SCL", "input"), ("14", "SDA", "bidirectional"), ("1", "SDO/SA0", "input"),
                ("12", "CS", "input"), ("2", "SDx", "input"), ("3", "SCx", "input"), ("6", "GND", "power_in"),
                ("7", "GND", "power_in")],
               [("8", "VDD", "power_in"), ("5", "VDDIO", "power_in"), None, ("4", "INT1", "output"),
                ("9", "INT2", "output"), None, ("10", "NC", "no_connect"), ("11", "NC", "no_connect")],
               width=12.7, desc="ST LSM6DS3TR-C 6-axis IMU, LGA-14L"))
    add(sym_ic("AP2112K-3.3", "U",
               [("1", "VIN", "power_in"), ("3", "EN", "input"), ("2", "GND", "power_in")],
               [("5", "VOUT", "power_out"), None, ("4", "NC", "no_connect")], width=10.16,
               desc="Diodes AP2112K-3.3 600 mA LDO, SOT-23-5"))
    add(sym_ic("R-78E5.0-0.5", "U",
               [("1", "+VIN", "power_in"), ("2", "GND", "power_in")],
               [("3", "+VOUT", "power_out")], width=10.16,
               desc="RECOM R-78E5.0-0.5 5 V / 0.5 A switching regulator module, SIP-3"))
    add(sym_ic("PESD1CAN", "D",
               [("1", "K1", "passive"), ("2", "K2", "passive")],
               [("3", "A", "passive")], width=7.62,
               desc="Dual bidirectional-capable CAN-bus ESD protection diode, SOT-23"))
    add(sym_ic("Crystal_GND24", "Y",
               [("1", "1", "passive"), ("2", "GND", "passive")],
               [("3", "3", "passive"), ("4", "GND", "passive")], width=7.62,
               desc="4-pad crystal, pins 1/3 = crystal, 2/4 = case ground"))
    return S
