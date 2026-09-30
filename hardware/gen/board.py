"""
board.py - PCB placement and absolute geometry model.

Board: 80 x 60 mm, KiCad page coordinates x 100..180, y 100..160 (Y down).
All parts on the top side (single-sided assembly).
"""
import math
from lib import build_footprints, rot_pt
from design import PARTS, nets

BX1, BY1, BX2, BY2 = 100.0, 100.0, 180.0, 160.0
CORNER_R = 2.0

# ref: (x, y, rotation_deg)  -- footprint origin in board coordinates
PLACEMENT = {
    # ---------------- power input chain (top-left) ----------------
    "J1": (105.0, 118.0, 90),
    "F1": (112.5, 118.0, 0),
    "D2": (120.0, 118.0, 180),
    "D1": (116.5, 124.0, 270),
    "C1": (125.2, 121.0, 270),
    "C2": (129.0, 121.0, 0),
    "U1": (122.0, 109.0, 0),
    "C3": (132.5, 109.95, 270),
    "U2": (137.5, 110.0, 0),
    "C4": (136.3, 113.2, 0),
    "C5": (139.8, 113.4, 0),
    "R1": (132.8, 104.0, 0),
    "D3": (136.0, 104.0, 180),
    "R2": (123.0, 132.0, 270),
    "R3": (123.0, 136.5, 270),
    "C6": (125.4, 136.5, 270),
    # ---------------- MCU -----------------------------------------
    "U3": (140.0, 132.0, 0),
    "C7": (136.2, 124.9, 90),
    "C8": (147.6, 127.6, 90),
    "C9": (145.2, 139.4, 90),
    "C10": (148.0, 124.0, 0),
    "C11": (134.4, 124.9, 90),
    "FB1": (136.4, 140.6, 0),
    "C12": (136.4, 142.6, 0),
    "C13": (139.2, 139.7, 90),
    "C14": (141.0, 139.7, 90),
    "Y1": (130.5, 130.65, 90),
    "C16": (127.0, 129.55, 180),
    "C17": (131.35, 134.4, 270),
    "C15": (118.0, 142.0, 0),
    "SW1": (109.0, 146.0, 0),
    "R4": (135.4, 118.8, 0),
    "JP1": (135.4, 121.2, 0),
    "R5": (126.0, 142.0, 0),
    "C18": (126.0, 143.6, 0),
    "SW2": (119.5, 146.0, 0),
    # LEDs (bottom right)  R above LED, one column per LED
    "R6": (149.0, 146.6, 270), "D4": (149.0, 150.6, 90),
    "R7": (151.5, 146.6, 270), "D5": (151.5, 150.6, 90),
    "R8": (154.0, 146.6, 270), "D6": (154.0, 150.6, 90),
    "R9": (156.5, 146.6, 270), "D7": (156.5, 150.6, 90),
    "JP3": (142.0, 143.4, 270),
    "JP4": (145.4, 143.4, 270),
    # ---------------- CAN ------------------------------------------
    "U4": (158.0, 130.0, 0),
    "R10": (161.3, 125.4, 180),
    "C19": (156.2, 135.2, 0),
    "C20": (160.4, 135.2, 0),
    "C21": (156.2, 137.4, 0),
    "D8": (166.0, 121.0, 180),
    "R11": (163.0, 137.6, 270),
    "R12": (165.54, 137.6, 270),
    "JP2": (163.0, 141.2, 0),
    "C22": (164.27, 146.9, 0),
    "J2": (175.3, 112.9, 270),
    "J3": (175.3, 129.365, 270),
    # ---------------- IMU ------------------------------------------
    "U5": (140.0, 120.625, 0),
    "C23": (143.6, 120.8, 90),
    "C24": (138.8, 117.6, 0),
    "R13": (144.0, 116.6, 0),
    "R14": (144.0, 114.6, 0),
    # ---------------- connectors / test ----------------------------
    "J4": (143.0, 104.0, 90),
    "J5": (130.0, 157.0, 90),
    "TP1": (165.6, 114.6, 0),
    "TP2": (167.2, 134.445, 0),
    "TP3": (125.6, 125.4, 0),
    "TP4": (139.6, 106.4, 0),
    "TP5": (148.0, 110.0, 0),
    "TP6": (151.0, 110.0, 0),
    "TP7": (151.0, 126.0, 0),
    "TP8": (150.6, 136.4, 0),
    "H1": (104.0, 104.0, 0),
    "H2": (176.0, 104.0, 0),
    "H3": (104.0, 156.0, 0),
    "H4": (176.0, 156.0, 0),
}

FOOTPRINTS = build_footprints()


class PadInst:
    """A pad placed on the board, with absolute geometry."""
    def __init__(self, ref, pad, fx, fy, frot, net):
        self.ref, self.num, self.pad = ref, pad.num, pad
        self.net = net
        lx, ly = rot_pt(pad.x, pad.y, frot)
        self.x, self.y = fx + lx, fy + ly
        self.rot = (frot + pad.angle) % 360
        self.w, self.h = pad.w, pad.h
        self.shape = pad.shape
        self.kind = pad.kind
        self.drill = pad.drill
        if pad.kind in ("smd", "smd_nopaste"):
            self.layers = ["F.Cu"]
        elif pad.kind == "np_thru_hole":
            self.layers = []
        else:
            self.layers = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

    def geom(self):
        """Return ('poly', [pts], radius) convex polygon + rounding radius."""
        w, h = self.w, self.h
        if self.shape == "circle":
            return ("poly", [(self.x, self.y)], w / 2)
        if self.shape == "oval":
            if abs(w - h) < 1e-9:
                return ("poly", [(self.x, self.y)], w / 2)
            if w > h:
                a, r = (w - h) / 2, h / 2
                pts = [(-a, 0), (a, 0)]
            else:
                a, r = (h - w) / 2, w / 2
                pts = [(0, -a), (0, a)]
        else:
            r = 0.0
            if self.shape == "roundrect":
                r = min(w, h) * self.pad.rratio
            hw, hh = w / 2 - r, h / 2 - r
            pts = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        out = []
        for (px, py) in pts:
            dx, dy = rot_pt(px, py, self.rot)
            out.append((self.x + dx, self.y + dy))
        return ("poly", out, r)

    def bbox(self):
        _, pts, r = self.geom()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r)


def placed_pads():
    out = []
    for ref, part in PARTS.items():
        fx, fy, frot = PLACEMENT[ref]
        fp = FOOTPRINTS[part.fp]
        for pad in fp.pads:
            net = part.pins.get(pad.num) if pad.num else None
            out.append(PadInst(ref, pad, fx, fy, frot, net))
    return out


def pad(ref, num):
    for p in placed_pads_cache():
        if p.ref == ref and p.num == str(num):
            return p
    raise KeyError((ref, num))


_cache = None


def placed_pads_cache():
    global _cache
    if _cache is None:
        _cache = placed_pads()
    return _cache


def courtyard(ref):
    """Absolute courtyard bbox (axis aligned; all rotations are multiples of 90)."""
    part = PARTS[ref]
    fx, fy, frot = PLACEMENT[ref]
    fp = FOOTPRINTS[part.fp]
    x1, y1, x2, y2 = fp.crt
    pts = [rot_pt(x, y, frot) for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2))]
    xs = [fx + p[0] for p in pts]
    ys = [fy + p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def board_outline():
    """Rounded rectangle as list of ('line'|'arc', ...) primitives."""
    r = CORNER_R
    x1, y1, x2, y2 = BX1, BY1, BX2, BY2
    prims = [
        ("line", (x1 + r, y1), (x2 - r, y1)),
        ("line", (x2, y1 + r), (x2, y2 - r)),
        ("line", (x2 - r, y2), (x1 + r, y2)),
        ("line", (x1, y2 - r), (x1, y1 + r)),
    ]
    k = r * (1 - 1 / math.sqrt(2))
    prims += [
        ("arc", (x1, y1 + r), (x1 + k, y1 + k), (x1 + r, y1)),
        ("arc", (x2 - r, y1), (x2 - k, y1 + k), (x2, y1 + r)),
        ("arc", (x2, y2 - r), (x2 - k, y2 - k), (x2 - r, y2)),
        ("arc", (x1 + r, y2), (x1 + k, y2 - k), (x1, y2 - r)),
    ]
    return prims


def outline_polygon(inset=0.0, n_arc=8):
    """Polygon approximation of the (optionally inset) rounded outline."""
    r = CORNER_R
    pts = []
    corners = [(BX2 - r, BY1 + r, -90, 0), (BX2 - r, BY2 - r, 0, 90),
               (BX1 + r, BY2 - r, 90, 180), (BX1 + r, BY1 + r, 180, 270)]
    for cx, cy, a0, a1 in corners:
        rr = max(r - inset, 0.01)
        for i in range(n_arc + 1):
            a = math.radians(a0 + (a1 - a0) * i / n_arc)
            pts.append((round(cx + rr * math.cos(a), 4), round(cy + rr * math.sin(a), 4)))
    return pts
