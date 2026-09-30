"""
routing.py - produces tracks + vias for the CAN ECU board.

Strategy (documented in docs/PCB_LAYOUT.md):
 1. Hand-routed critical nets (explicit coordinates below): input power chain
    (VIN_RAW/VIN_FUSED/VIN_PROT, 1.0/0.8 mm), CAN bus trunk (CANH on F.Cu,
    CANL on F.Cu + B.Cu, 0.4 mm) to both connectors, transceiver supply vias,
    special-case plane vias.
 2. Plane fan-out: every SMD pad on GND / +3V3 gets its own short stub + via to
    In1.Cu (GND) or In2.Cu (+3V3).  Through-hole pads reach the planes directly.
 3. Remaining nets are routed one at a time, in a fixed priority order, by a
    grid router (0.125 mm grid, 45-degree moves, turn + via penalties, exact
    clearance fields computed from the real pad/track geometry).  Every result
    is re-checked by the independent analytic DRC in checks.py.
"""
import json
import math
import heapq
import numpy as np

from board import placed_pads_cache, PLACEMENT, outline_polygon, BX1, BY1, BX2, BY2
from design import PARTS, nets as design_nets
from geom import raster_dist, shape_dist, bbox as sbbox, bb_overlap

CLR = 0.2          # copper-copper clearance
EDGE_CLR = 0.3     # copper-edge clearance
VIA_D, VIA_H = 0.6, 0.3
HOLE_CLR = 0.25    # hole-to-hole
G = 0.125          # router grid
PLANE = {"GND": "In1.Cu", "+3V3": "In2.Cu"}
ROUTE_LAYERS = ["F.Cu", "B.Cu"]
ALL_CU = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
KEEPOUT_R = 2.9    # track keep-out radius around M3 holes (screw head)

OUTLINE = outline_polygon(0.0, 16)


class Item:
    __slots__ = ("kind", "net", "layers", "pts", "r", "drill", "smd", "data")

    def __init__(self, kind, net, layers, pts, r, drill=None, smd=False, data=None):
        self.kind, self.net, self.layers, self.pts, self.r = kind, net, set(layers), pts, r
        self.drill, self.smd, self.data = drill, smd, data

    @property
    def shape(self):
        return (self.pts, self.r)


class Router:
    def __init__(self):
        self.items = []
        self.tracks = []
        self.vias = []
        self.log = []
        self.pads = placed_pads_cache()
        nc = 0
        for p in self.pads:
            _, pts, r = p.geom()
            if p.kind == "np_thru_hole":
                self.items.append(Item("keepout", "__KEEPOUT__", ["F.Cu", "B.Cu"], [(p.x, p.y)], KEEPOUT_R))
                self.items.append(Item("hole", "__NPTH__", [], [(p.x, p.y)], p.drill / 2, drill=p.drill))
                continue
            net = p.net
            if net is None:
                nc += 1
                net = f"__NC{nc}__"
            it = Item("pad", net, p.layers, pts, r, drill=p.drill, smd=(p.kind != "thru_hole"), data=p)
            self.items.append(it)

    # ------------------------------------------------------------ adding
    def add_track(self, net, layer, pts, w, tag="auto"):
        for a, b in zip(pts[:-1], pts[1:]):
            if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
                continue
            a = (round(a[0], 4), round(a[1], 4))
            b = (round(b[0], 4), round(b[1], 4))
            self.tracks.append({"net": net, "layer": layer, "a": a, "b": b, "w": w, "tag": tag})
            self.items.append(Item("track", net, [layer], [a, b], w / 2))

    def add_via(self, net, x, y, tag="auto"):
        x, y = round(x, 4), round(y, 4)
        for v in self.vias:
            if v["net"] == net and abs(v["at"][0] - x) < 1e-6 and abs(v["at"][1] - y) < 1e-6:
                return
        self.vias.append({"net": net, "at": (x, y), "size": VIA_D, "drill": VIA_H, "tag": tag})
        self.items.append(Item("via", net, ALL_CU, [(x, y)], VIA_D / 2, drill=VIA_H))

    def pad(self, ref, num):
        for p in self.pads:
            if p.ref == ref and p.num == str(num):
                return p
        raise KeyError((ref, num))

    def P(self, ref, num):
        p = self.pad(ref, num)
        return (p.x, p.y)

    # ------------------------------------------------------------ checks
    def gap_to_others(self, shape, net, layers, skip_smd_same=False):
        bb = sbbox(shape, 3.0)
        best = 1e9
        for it in self.items:
            if it.net == net or not (it.layers & set(layers)):
                continue
            if not bb_overlap(bb, sbbox(it.shape)):
                continue
            best = min(best, shape_dist(shape, it.shape))
        return best

    def edge_gap(self, shape):
        # distance of shape to board edge (inside positive)
        pts, r = shape
        d = min(-float(raster_dist(OUTLINE, 0.0, np.array([x]), np.array([y]))[0]) for x, y in pts)
        return d - r

    def via_ok(self, net, x, y, src_pad=None):
        vs = ([(x, y)], VIA_D / 2)
        if self.gap_to_others(vs, net, ALL_CU) < CLR:
            return False
        if self.edge_gap(vs) < EDGE_CLR:
            return False
        hs = ([(x, y)], VIA_H / 2)
        for it in self.items:
            if it.drill and it.kind != "pad" or (it.kind == "pad" and it.drill):
                if math.hypot(it.pts[0][0] - x, it.pts[0][1] - y) - it.drill / 2 - VIA_H / 2 < HOLE_CLR:
                    return False
            if it.kind == "hole":
                if math.hypot(it.pts[0][0] - x, it.pts[0][1] - y) - it.drill / 2 - VIA_H / 2 < 0.5:
                    return False
            if it.smd and it.kind == "pad":
                if shape_dist(vs, it.shape) < 0.1:
                    return False
        return True

    # ------------------------------------------------------------ fanout
    def fanout(self, overrides):
        for p in self.pads:
            key = (p.ref, p.num)
            if key in overrides:
                pts_, mkvia = overrides[key]
                path = [(p.x, p.y)] + [tuple(q) for q in pts_]
                self.add_track(p.net, "F.Cu", path, 0.25, tag="fanout")
                if mkvia:
                    self.add_via(p.net, *path[-1], tag="fanout")
        for p in self.pads:
            if p.net not in PLANE or p.kind == "thru_hole":
                continue
            key = (p.ref, p.num)
            _, pts, r = p.geom()
            tw = min(0.4, p.w, p.h) if p.ref not in ("U3",) else 0.3
            if key in overrides:
                continue
            fx, fy, _ = PLACEMENT[p.ref]
            ox, oy = p.x - fx, p.y - fy
            pref = math.degrees(math.atan2(oy, ox)) if math.hypot(ox, oy) > 0.05 else None
            best = None
            # reuse an existing same-net via close by
            for v in self.vias:
                if v["net"] != p.net:
                    continue
                vx, vy = v["at"]
                dd = math.hypot(vx - p.x, vy - p.y)
                if dd > 1.6:
                    continue
                ts = ([(p.x, p.y), (vx, vy)], tw / 2)
                if self.gap_to_others(ts, p.net, ["F.Cu"]) >= CLR:
                    if best is None or dd < best[0]:
                        best = (dd, vx, vy, True)
            if best is None:
                ext = max(p.w, p.h) / 2
                for step in range(0, 18):
                    dist = ext + VIA_D / 2 + 0.12 + step * 0.1
                    cands = []
                    for k in range(16):
                        ang = k * 22.5
                        dev = 0 if pref is None else abs((ang - pref + 180) % 360 - 180)
                        if dev > 100:
                            continue
                        cands.append((dev, ang))
                    cands.sort()
                    for dev, ang in cands:
                        vx = p.x + dist * math.cos(math.radians(ang))
                        vy = p.y + dist * math.sin(math.radians(ang))
                        vx, vy = round(vx / 0.025) * 0.025, round(vy / 0.025) * 0.025
                        ts = ([(p.x, p.y), (vx, vy)], tw / 2)
                        if self.gap_to_others(ts, p.net, ["F.Cu"]) < CLR:
                            continue
                        if not self.via_ok(p.net, vx, vy):
                            continue
                        best = (dist + dev * 0.01, vx, vy, False)
                        break
                    if best:
                        break
            if best is None:
                self.log.append(f"FANOUT FAILED {p.ref}.{p.num} {p.net}")
                continue
            _, vx, vy, reused = best
            self.add_track(p.net, "F.Cu", [(p.x, p.y), (vx, vy)], tw, tag="fanout")
            self.add_via(p.net, vx, vy, tag="fanout")

    # ------------------------------------------------------------ grid router
    def _field(self, net, layer, X, Y, extra=0.0):
        """min edge gap from each grid point to other-net copper on `layer`."""
        d = np.full(X.shape, 99.0)
        x0, y0, x1, y1 = X[0, 0], Y[0, 0], X[0, -1], Y[-1, 0]
        for it in self.items:
            if it.net == net or layer not in it.layers:
                continue
            b = sbbox(it.shape, 1.2 + extra)
            if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
                continue
            i0 = max(0, int((b[0] - x0) / G)); i1 = min(X.shape[1], int((b[2] - x0) / G) + 2)
            j0 = max(0, int((b[1] - y0) / G)); j1 = min(X.shape[0], int((b[3] - y0) / G) + 2)
            if i0 >= i1 or j0 >= j1:
                continue
            sub = raster_dist(it.pts, it.r, X[j0:j1, i0:i1], Y[j0:j1, i0:i1])
            d[j0:j1, i0:i1] = np.minimum(d[j0:j1, i0:i1], sub)
        return d

    def route_net(self, net, w, pref=None, margin=8.0, via_cost=14.0, max_expand=900000):
        pref = pref or {"F.Cu": 1.0, "B.Cu": 1.15}
        pins = [p for p in self.pads if p.net == net]
        if len(pins) < 2 and not any(t["net"] == net for t in self.tracks):
            return True
        # connectivity bookkeeping: union-find over pins + existing copper
        comps = self._components(net)
        if len(comps) <= 1:
            return True
        xs = [q[0] for c in comps for q in c["pts"]]
        ys = [q[1] for c in comps for q in c["pts"]]
        wx0 = max(BX1, min(xs) - margin); wx1 = min(BX2, max(xs) + margin)
        wy0 = max(BY1, min(ys) - margin); wy1 = min(BY2, max(ys) + margin)
        wx0 = BX1 + math.floor((wx0 - BX1) / G) * G
        wy0 = BY1 + math.floor((wy0 - BY1) / G) * G
        nx = int((wx1 - wx0) / G) + 1
        ny = int((wy1 - wy0) / G) + 1
        gx = wx0 + np.arange(nx) * G
        gy = wy0 + np.arange(ny) * G
        X, Y = np.meshgrid(gx, gy)
        hw = w / 2
        edge = -raster_dist(OUTLINE, 0.0, X, Y)
        free = {}
        dfield = {}
        for L in ROUTE_LAYERS:
            dfield[L] = self._field(net, L, X, Y)
            free[L] = (dfield[L] >= hw + CLR + 0.01) & (edge >= hw + EDGE_CLR)
        # via feasibility
        smd = np.full(X.shape, 99.0)
        holes = np.full(X.shape, 99.0)
        for it in self.items:
            b = sbbox(it.shape, 1.0)
            if b[2] < wx0 or b[0] > wx1 or b[3] < wy0 or b[1] > wy1:
                continue
            if it.kind == "pad" and it.smd:
                smd = np.minimum(smd, raster_dist(it.pts, it.r, X, Y))
            if it.drill:
                c = it.pts[0]
                extra = 0.5 if it.kind == "hole" else HOLE_CLR
                holes = np.minimum(holes, np.hypot(X - c[0], Y - c[1]) - it.drill / 2 - extra)
        viaok = ((dfield["F.Cu"] >= VIA_D / 2 + CLR + 0.01) & (dfield["B.Cu"] >= VIA_D / 2 + CLR + 0.01)
                 & (smd >= VIA_D / 2 + 0.1) & (holes >= VIA_H / 2) & (edge >= VIA_D / 2 + EDGE_CLR))
        # inner-plane vias of other nets are ignored (planes get antipads)
        Li = {L: k for k, L in enumerate(ROUTE_LAYERS)}

        def cells_of(comp, allow_all=False):
            out = set()
            for L in comp["layers_pts"]:
                for (px, py) in comp["layers_pts"][L]:
                    pass
            for (L, sh) in comp["shapes"]:
                if L not in Li:
                    continue
                b = sbbox(sh, 0)
                i0 = max(0, int(math.floor((b[0] - wx0) / G))); i1 = min(nx, int(math.ceil((b[2] - wx0) / G)) + 1)
                j0 = max(0, int(math.floor((b[1] - wy0) / G))); j1 = min(ny, int(math.ceil((b[3] - wy0) / G)) + 1)
                if i0 >= i1 or j0 >= j1:
                    continue
                sub = raster_dist(sh[0], sh[1], X[j0:j1, i0:i1], Y[j0:j1, i0:i1])
                jj, ii = np.nonzero((sub <= -0.02) & free[L][j0:j1, i0:i1])
                for j, i in zip(jj, ii):
                    out.add((Li[L], j0 + j, i0 + i))
            return out

        # order: start from the largest component as tree
        comps.sort(key=lambda c: -len(c["shapes"]))
        tree = comps[0]
        rest = comps[1:]
        tree_cells = cells_of(tree)
        while rest:
            # nearest remaining component
            def cd(c):
                return min(math.hypot(a[0] - b[0], a[1] - b[1]) for a in c["pts"] for b in tree["pts"])
            rest.sort(key=cd)
            tgt = rest.pop(0)
            tgt_cells = cells_of(tgt)
            if not tree_cells or not tgt_cells:
                self.log.append(f"ROUTE FAILED {net}: no access cells ({len(tree_cells)}/{len(tgt_cells)})")
                return False
            path = self._astar(tree_cells, tgt_cells, free, viaok, nx, ny, pref, via_cost, max_expand)
            if path is None:
                self.log.append(f"ROUTE FAILED {net}: no path to {tgt['label']}")
                return False
            self._emit(net, w, path, wx0, wy0, tgt)
            tree = {"pts": tree["pts"] + tgt["pts"], "shapes": tree["shapes"] + tgt["shapes"],
                    "layers_pts": {}, "label": "tree"}
            tree_cells |= tgt_cells
            for (l, j, i) in path:
                tree_cells.add((l, j, i))
                if viaok[j, i]:
                    pass
        return True

    def _components(self, net):
        objs = []
        for it in self.items:
            if it.net != net:
                continue
            if it.kind == "pad":
                objs.append(it)
            elif it.kind in ("track", "via"):
                objs.append(it)
        n = len(objs)
        parent = list(range(n))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for i in range(n):
            for j in range(i + 1, n):
                if not (objs[i].layers & objs[j].layers):
                    continue
                if shape_dist(objs[i].shape, objs[j].shape) <= 1e-6:
                    parent[find(i)] = find(j)
        groups = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(objs[i])
        comps = []
        for g in groups.values():
            pts, shapes, lab = [], [], []
            for it in g:
                pts += list(it.pts)
                for L in it.layers:
                    shapes.append((L, it.shape))
                if it.kind == "pad":
                    lab.append(f"{it.data.ref}.{it.data.num}")
            if not any(it.kind == "pad" for it in g) and not any(it.kind == "via" for it in g):
                continue
            comps.append({"pts": pts, "shapes": shapes, "layers_pts": {}, "label": ",".join(lab) or "copper"})
        return comps

    def _astar(self, srcs, tgts, free, viaok, nx, ny, pref, via_cost, max_expand):
        DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
        TURN = {0: 0.0, 1: 0.35, 2: 2.5}
        Lp = [pref["F.Cu"], pref["B.Cu"]]
        fr = [free["F.Cu"], free["B.Cu"]]
        tx = np.mean([t[2] for t in tgts]); ty = np.mean([t[1] for t in tgts])
        tset = set(tgts)

        def h(j, i):
            dx, dy = abs(i - tx), abs(j - ty)
            return (max(dx, dy) + 0.4142 * min(dx, dy)) * 1.0
        heap = []
        g = {}
        came = {}
        for (l, j, i) in srcs:
            s = (l, j, i, 8)
            g[s] = 0.0
            heapq.heappush(heap, (h(j, i), 0.0, s))
            came[s] = None
        exp = 0
        while heap:
            f, gc, s = heapq.heappop(heap)
            if gc > g.get(s, 1e18) + 1e-9:
                continue
            l, j, i, d = s
            if (l, j, i) in tset:
                path = []
                while s is not None:
                    path.append(s[:3])
                    s = came[s]
                return path[::-1]
            exp += 1
            if exp > max_expand:
                return None
            for nd, (di, dj) in enumerate(DIRS):
                if d != 8:
                    diff = abs(nd - d) % 8
                    diff = min(diff, 8 - diff)
                    if diff > 2:
                        continue
                    tc = TURN[diff]
                else:
                    tc = 0.0
                ni, nj = i + di, j + dj
                if ni < 0 or nj < 0 or ni >= nx or nj >= ny or not fr[l][nj, ni]:
                    continue
                if di and dj and not (fr[l][j, ni] or fr[l][nj, i]):
                    continue
                step = (1.4142 if di and dj else 1.0) * Lp[l] + tc
                ns = (l, nj, ni, nd)
                ng = gc + step
                if ng < g.get(ns, 1e18) - 1e-9:
                    g[ns] = ng
                    came[ns] = s
                    heapq.heappush(heap, (ng + h(nj, ni), ng, ns))
            if viaok[j, i]:
                nl = 1 - l
                if fr[nl][j, i]:
                    ns = (nl, j, i, 8)
                    ng = gc + via_cost
                    if ng < g.get(ns, 1e18) - 1e-9:
                        g[ns] = ng
                        came[ns] = s
                        heapq.heappush(heap, (ng + h(j, i), ng, ns))
        return None

    def _emit(self, net, w, path, wx0, wy0, tgt):
        pts = [(l, wx0 + i * G, wy0 + j * G) for (l, j, i) in path]
        runs = []
        cur = [pts[0]]
        for p in pts[1:]:
            if p[0] != cur[-1][0]:
                runs.append(cur)
                self.add_via(net, p[1], p[2], tag="route")
                cur = [p]
            else:
                cur.append(p)
        runs.append(cur)
        for k, run in enumerate(runs):
            L = ROUTE_LAYERS[run[0][0]]
            xy = [(q[1], q[2]) for q in run]
            # simplify collinear
            simp = [xy[0]]
            for a in range(1, len(xy) - 1):
                (x0, y0), (x1, y1), (x2, y2) = simp[-1], xy[a], xy[a + 1]
                if abs((x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)) > 1e-9:
                    simp.append(xy[a])
            simp.append(xy[-1])
            # stub into target pad centre on the final run if the pad is on this layer
            if k == len(runs) - 1:
                for (LL, sh) in tgt["shapes"]:
                    if LL == L and len(sh[0]) >= 1:
                        cx = sum(q[0] for q in sh[0]) / len(sh[0]); cy = sum(q[1] for q in sh[0]) / len(sh[0])
                        if raster_dist(sh[0], sh[1], np.array([simp[-1][0]]), np.array([simp[-1][1]]))[0] <= 0 \
                                and raster_dist(sh[0], sh[1], np.array([cx]), np.array([cy]))[0] <= 0 \
                                and len(sh[0]) != 2:
                            if math.hypot(cx - simp[-1][0], cy - simp[-1][1]) > 0.01:
                                simp.append((cx, cy))
                            break
            if len(simp) >= 2:
                self.add_track(net, L, simp, w, tag="route")


# ============================================================ the design's routing
def build():
    R = Router()
    P = R.P
    # ---------------------------------------------------------------- 1. manual
    # input power chain (F.Cu, wide)
    R.add_track("VIN_RAW", "F.Cu", [P("J1", 1), P("F1", 1)], 1.0, "manual")
    R.add_track("VIN_FUSED", "F.Cu", [P("F1", 2), P("D2", 2)], 1.0, "manual")
    d1k = P("D1", 1)
    R.add_track("VIN_FUSED", "F.Cu", [d1k, (d1k[0], P("F1", 2)[1])], 1.0, "manual")
    k = P("D2", 1); c1 = P("C1", 1); c2 = P("C2", 1); u1 = P("U1", 1)
    R.add_track("VIN_PROT", "F.Cu", [k, (c1[0] - 1.2, k[1]), (c1[0], k[1] + 1.2), c1], 0.8, "manual")
    R.add_track("VIN_PROT", "F.Cu", [c1, (c2[0] - 1.5, c1[1]), c2], 0.8, "manual")
    R.add_track("VIN_PROT", "F.Cu", [k, (k[0], u1[1])], 0.8, "manual")
    R.add_track("VIN_PROT", "F.Cu", [(k[0], u1[1]), u1], 0.8, "manual")
    # +5 V from the module to C3 and the LDO (F.Cu), EN tied to VIN around pin 2
    u13 = P("U1", 3); c3 = P("C3", 1); l1 = P("U2", 1); l3 = P("U2", 3)
    R.add_track("+5V", "F.Cu", [u13, (c3[0], u13[1]), c3], 0.6, "manual")
    R.add_track("+5V", "F.Cu", [(c3[0], u13[1]), (l1[0] - 1.0, u13[1]), (l1[0] - 0.95, l1[1]), l1], 0.6, "manual")
    R.add_track("+5V", "F.Cu", [(l1[0] - 0.95, l1[1]), (l1[0] - 1.2, l1[1] + 0.25), (l1[0] - 1.2, l3[1]), l3], 0.3, "manual")
    # LDO GND via under the SOT-23-5 body (pin 2 is boxed in by pins 1/3 and EN route)
    g2 = P("U2", 2)
    R.add_track("GND", "F.Cu", [g2, (g2[0] + 1.15, g2[1])], 0.4, "manual")
    R.add_via("GND", g2[0] + 1.15, g2[1], "manual")
    # CAN transceiver: GND and VCC vias on the left, between TXD and RXD
    u2 = P("U4", 2); u3 = P("U4", 3)
    R.add_track("GND", "F.Cu", [u2, (u2[0] - 1.9, u2[1])], 0.4, "manual")
    R.add_via("GND", u2[0] - 1.9, u2[1], "manual")
    R.add_track("+5V", "F.Cu", [u3, (u3[0] - 1.9, u3[1])], 0.4, "manual")
    R.add_via("+5V", u3[0] - 1.9, u3[1], "manual")
    # CAN bus trunk: CANH on F.Cu, CANL on F.Cu (south) + B.Cu (north)
    h7 = P("U4", 7); l6 = P("U4", 6)
    j2h, j2l = P("J2", 1), P("J2", 2)
    j3h, j3l = P("J3", 1), P("J3", 2)
    XH, XL = 168.5, 170.0
    R.add_track("CANH", "F.Cu", [h7, j3h], 0.4, "manual")
    R.add_track("CANH", "F.Cu", [(XH, h7[1]), (XH, j2h[1]), j2h], 0.4, "manual")
    R.add_track("CANL", "F.Cu", [l6, (XL, l6[1]), (XL, j3l[1]), j3l], 0.4, "manual")
    R.add_via("CANL", XL, l6[1], "manual")
    R.add_track("CANL", "B.Cu", [(XL, l6[1]), (XL, j2l[1]), j2l], 0.4, "manual")
    # ESD diode taps
    d1 = P("D8", 1); d2 = P("D8", 2)
    R.add_track("CANH", "F.Cu", [d1, (XH, d1[1])], 0.4, "manual")
    R.add_track("CANL", "F.Cu", [d2, (d2[0], d2[1] - 1.05)], 0.4, "manual")
    R.add_via("CANL", d2[0], d2[1] - 1.05, "manual")
    R.add_track("CANL", "B.Cu", [(d2[0], d2[1] - 1.05), (XL, d2[1] - 1.05)], 0.4, "manual")
    tp1 = P("TP1", 1); tp2 = P("TP2", 1)
    R.add_track("CANH", "F.Cu", [tp1, (XH, tp1[1])], 0.4, "manual")
    R.add_track("CANL", "F.Cu", [tp2, (XL, tp2[1])], 0.4, "manual")
    # JP2 bottom row: pins 3 and 4 are both TERM_MID
    R.add_track("TERM_MID", "F.Cu", [P("JP2", 3), P("JP2", 4)], 0.4, "manual")

    # ---------------------------------------------------------------- 2. plane fanout
    R.fanout(FANOUT_OVERRIDES)

    # ---------------------------------------------------------------- 3. routed nets
    B5 = {"F.Cu": 1.35, "B.Cu": 1.0}
    FB = {"F.Cu": 1.0, "B.Cu": 1.1}
    order = [
        ("OSC_OUT", 0.25, FB), ("OSC_IN", 0.25, FB),
        ("CAN_TX", 0.25, FB), ("CAN_RX", 0.25, FB),
        ("+3V3A", 0.3, FB),
        ("IMU_INT1", 0.25, FB), ("IMU_INT2", 0.25, FB), ("I2C_SCL", 0.25, FB), ("I2C_SDA", 0.25, FB),
        ("SWDIO", 0.25, FB), ("SWCLK", 0.25, FB), ("SWO", 0.25, FB),
        ("BOOT0", 0.25, FB),
        ("LED_STATUS", 0.25, FB), ("LED_FAULT", 0.25, FB), ("LED_CANTX", 0.25, FB), ("LED_CANRX", 0.25, FB),
        ("LED_STATUS_A", 0.25, FB), ("LED_FAULT_A", 0.25, FB), ("LED_CANTX_A", 0.25, FB), ("LED_CANRX_A", 0.25, FB),
        ("NODE_ID1", 0.25, FB), ("NODE_ID0", 0.25, FB),
        ("CAN_S", 0.25, FB),
        ("CANH", 0.3, FB), ("CANL", 0.3, FB), ("TERM_H", 0.3, FB), ("TERM_L", 0.3, FB), ("TERM_MID", 0.3, FB),
        ("EXP_PB0", 0.25, FB), ("EXP_PA7", 0.25, FB), ("EXP_PA6", 0.25, FB), ("EXP_PA5", 0.25, FB),
        ("EXP_PA4", 0.25, FB), ("UART_RX", 0.25, FB), ("UART_TX", 0.25, FB),
        ("VIN_SENSE", 0.25, FB), ("NRST", 0.25, FB), ("USER_BTN", 0.25, FB),
        ("+5V", 0.5, B5), ("VIN_PROT", 0.4, FB), ("PWR_LED_A", 0.25, FB),
    ]
    failed = []
    for net, w, pref in order:
        ok = R.route_net(net, w, pref)
        if not ok:
            ok = R.route_net(net, w, pref, margin=20.0, max_expand=3000000)
        if not ok:
            failed.append(net)
    return R, failed


# Hand-chosen plane-via positions for pads where the automatic fan-out would
# block signal escape (MCU corners etc).  Coordinates are absolute.
FANOUT_OVERRIDES = {
    # MCU supply pins: short stubs INWARD to vias under the LQFP body, so that
    # every signal pin can escape outward unobstructed.
    ("U3", "48"): ([(137.25, 130.2)], True),                    # VDD  -> In2
    ("U3", "1"): ([(137.25, 129.25)], False),                   # VBAT joins pin-48 stub
    ("U3", "47"): ([(137.75, 128.95), (138.3, 129.5)], True),   # VSS  -> In1
    ("U3", "36"): ([(142.6, 129.25)], True),
    ("U3", "35"): ([(143.2, 129.75), (142.5, 130.45)], True),
    ("U3", "24"): ([(142.75, 133.9)], True),
    ("U3", "23"): ([(142.25, 135.1), (141.7, 134.55)], True),
    ("U3", "19"): ([(140.25, 134.6)], True),                    # VSSA
    # IMU (LGA-14, 0.5 mm pitch): group the GND pads, keep INT/I2C escapes free
    ("U5", "1"): ([(138.45, 119.875), (138.45, 118.9)], True),
    ("U5", "2"): ([(138.45, 120.375)], False),
    ("U5", "3"): ([(138.45, 120.875), (138.45, 119.875)], False),
    ("U5", "6"): ([(140.0, 122.65), (140.25, 122.9)], True),
    ("U5", "7"): ([(140.5, 122.65), (140.25, 122.9)], False),
    ("U5", "5"): ([(139.5, 122.4), (139.0, 122.9)], True),
    ("U5", "8"): ([(141.7, 121.375), (142.05, 121.8)], True),
    ("U5", "12"): ([(140.5, 118.9), (140.9, 118.5)], True),
}


def save(R, path):
    with open(path, "w") as f:
        json.dump({"tracks": R.tracks, "vias": R.vias}, f, indent=0)


if __name__ == "__main__":
    import time, sys
    t = time.time()
    R, failed = build()
    for l in R.log:
        print(l)
    print("failed:", failed)
    print(len(R.tracks), "tracks", len(R.vias), "vias", round(time.time() - t, 1), "s")
    save(R, "/home/claude/stm32-can-ecu/hardware/gen/routes.json")
    from render import render
    render("/tmp/route.png", R.tracks, R.vias, title="routing")
