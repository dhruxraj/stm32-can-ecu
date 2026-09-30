"""
checks.py - independent design-rule and connectivity checks (a stand-in for
KiCad's DRC, which is not available in the generation environment).

Checks:
  * copper clearance (pads/tracks/vias, per layer, different nets)   >= 0.20 mm
  * copper to board edge                                             >= 0.30 mm
  * hole to hole (drill edges)                                       >= 0.25 mm
  * vias not inside SMD pads (no via-in-pad)
  * minimum track width                                              >= 0.20 mm
  * courtyard overlaps / courtyard outside board
  * connectivity: every net fully connected (tracks + vias + pads +
    solid planes In1=GND, In2=+3V3), no unconnected pads
  * plane continuity (raster flood fill of In1 / In2 with antipads)
  * netlist consistency: design nets == PCB pad nets
"""
import json
import math
import sys
import numpy as np
from scipy import ndimage

from board import placed_pads_cache, PARTS, courtyard, outline_polygon, BX1, BY1, BX2, BY2
from design import nets as design_nets
from geom import shape_dist, bbox, bb_overlap, raster_dist

CLR, EDGE, HOLE, MINW = 0.2, 0.3, 0.25, 0.2
ZONE_CLR = 0.25
PLANES = {"In1.Cu": "GND", "In2.Cu": "+3V3"}
OUTLINE = outline_polygon(0.0, 16)


def load(path):
    d = json.load(open(path))
    return d["tracks"], d["vias"]


def build_items(tracks, vias):
    items = []
    nc = 0
    for p in placed_pads_cache():
        if p.kind == "np_thru_hole":
            items.append(dict(kind="npth", net="__NPTH__", layers=set(), shape=([(p.x, p.y)], p.drill / 2),
                              drill=p.drill, at=(p.x, p.y), name=f"{p.ref}"))
            continue
        net = p.net
        if net is None:
            nc += 1
            net = f"__NC{nc}__"
        _, pts, r = p.geom()
        items.append(dict(kind="pad", net=net, layers=set(p.layers), shape=(pts, r), drill=p.drill,
                          at=(p.x, p.y), smd=p.kind != "thru_hole", name=f"{p.ref}.{p.num}"))
    for i, t in enumerate(tracks):
        items.append(dict(kind="track", net=t["net"], layers={t["layer"]}, shape=([tuple(t["a"]), tuple(t["b"])], t["w"] / 2),
                          w=t["w"], name=f"track#{i}({t['net']},{t['layer']})"))
    for i, v in enumerate(vias):
        items.append(dict(kind="via", net=v["net"], layers={"F.Cu", "In1.Cu", "In2.Cu", "B.Cu"},
                          shape=([tuple(v["at"])], v["size"] / 2), drill=v["drill"], at=tuple(v["at"]),
                          name=f"via#{i}({v['net']})"))
    for it in items:
        it["bb"] = bbox(it["shape"])
    return items


def drc(items):
    errs = []
    cu = [it for it in items if it["kind"] != "npth"]
    # clearance on routing layers (inner layers carry only planes + vias/THT)
    for i in range(len(cu)):
        a = cu[i]
        for j in range(i + 1, len(cu)):
            b = cu[j]
            if a["net"] == b["net"]:
                continue
            if not ({"F.Cu", "B.Cu"} & a["layers"] & b["layers"]):
                continue
            if not bb_overlap(a["bb"], (b["bb"][0] - CLR, b["bb"][1] - CLR, b["bb"][2] + CLR, b["bb"][3] + CLR)):
                continue
            d = shape_dist(a["shape"], b["shape"])
            if d < CLR - 1e-4:
                errs.append(("clearance", round(d, 3), a["name"], b["name"]))
    # edge clearance
    for it in cu:
        pts, r = it["shape"]
        dmin = min(-float(raster_dist(OUTLINE, 0, np.array([x]), np.array([y]))[0]) for x, y in pts) - r
        if dmin < EDGE - 1e-4:
            errs.append(("edge", round(dmin, 3), it["name"], ""))
    # holes
    holes = [it for it in items if it.get("drill")]
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            a, b = holes[i], holes[j]
            d = math.dist(a["at"], b["at"]) - a["drill"] / 2 - b["drill"] / 2
            if d < HOLE - 1e-4 and not (a["kind"] == "pad" and b["kind"] == "pad" and a["name"].split(".")[0] == b["name"].split(".")[0] and d > 0):
                errs.append(("hole-hole", round(d, 3), a["name"], b["name"]))
    # via in SMD pad
    for v in [it for it in items if it["kind"] == "via"]:
        for p in [it for it in items if it["kind"] == "pad" and it.get("smd")]:
            if bb_overlap(v["bb"], p["bb"]) and shape_dist(v["shape"], p["shape"]) < 0.0:
                errs.append(("via-in-pad", 0, v["name"], p["name"]))
    for t in [it for it in items if it["kind"] == "track"]:
        if t["w"] < MINW:
            errs.append(("track-width", t["w"], t["name"], ""))
    return errs


def courtyards():
    errs = []
    refs = list(PARTS)
    for i, a in enumerate(refs):
        A = courtyard(a)
        if A[0] < BX1 or A[1] < BY1 or A[2] > BX2 or A[3] > BY2:
            errs.append(("courtyard-outside-board", a))
        for b in refs[i + 1:]:
            B = courtyard(b)
            if min(A[2], B[2]) - max(A[0], B[0]) > 1e-3 and min(A[3], B[3]) - max(A[1], B[1]) > 1e-3:
                errs.append(("courtyard-overlap", a, b))
    return errs


def plane_rasters(items, res=0.05):
    """Raster of In1/In2 copper after antipads; returns labels per plane."""
    nx = int((BX2 - BX1) / res) + 1
    ny = int((BY2 - BY1) / res) + 1
    xs = BX1 + np.arange(nx) * res
    ys = BY1 + np.arange(ny) * res
    X, Y = np.meshgrid(xs, ys)
    inside = raster_dist(OUTLINE, 0.0, X, Y) <= -EDGE
    out = {}
    for L, net in PLANES.items():
        cu = inside.copy()
        for it in items:
            if L not in it["layers"] and it["kind"] != "npth":
                continue
            if it["net"] == net:
                continue
            b = it["bb"]
            i0 = max(0, int((b[0] - ZONE_CLR - BX1) / res) - 1); i1 = min(nx, int((b[2] + ZONE_CLR - BX1) / res) + 2)
            j0 = max(0, int((b[1] - ZONE_CLR - BY1) / res) - 1); j1 = min(ny, int((b[3] + ZONE_CLR - BY1) / res) + 2)
            sub = raster_dist(it["shape"][0], it["shape"][1], X[j0:j1, i0:i1], Y[j0:j1, i0:i1])
            cu[j0:j1, i0:i1] &= sub > ZONE_CLR
        lab, n = ndimage.label(cu)
        out[L] = (lab, n, res)
    return out


def connectivity(items, planes):
    """Union-find over copper objects; planes join all same-net objects that
    touch the plane's main island."""
    objs = [it for it in items if it["kind"] in ("pad", "track", "via")]
    n = len(objs)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    bynet = {}
    for i, o in enumerate(objs):
        bynet.setdefault(o["net"], []).append(i)
    for net, idx in bynet.items():
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                a, b = objs[idx[x]], objs[idx[y]]
                if not (a["layers"] & b["layers"]):
                    continue
                if not bb_overlap(a["bb"], b["bb"]):
                    continue
                if shape_dist(a["shape"], b["shape"]) <= 1e-4:
                    union(idx[x], idx[y])
    report = {}
    plane_islands = {}
    for L, net in PLANES.items():
        lab, nl, res = planes[L]
        members = {}
        for i in bynet.get(net, []):
            o = objs[i]
            if L not in o["layers"]:
                continue
            x, y = o.get("at", o["shape"][0][0])
            li = lab[int(round((y - BY1) / res)), int(round((x - BX1) / res))]
            members.setdefault(int(li), []).append(i)
        plane_islands[L] = {k: len(v) for k, v in members.items()}
        for li, idx in members.items():
            if li == 0:
                continue          # object not touching plane copper (should not happen)
            for i in idx[1:]:
                union(idx[0], i)
    for net, idx in bynet.items():
        if net.startswith("__NC"):
            continue
        roots = {}
        for i in idx:
            roots.setdefault(find(i), []).append(objs[i]["name"])
        pads_in = [[nm for nm in g if "#" not in nm] for g in roots.values()]
        pads_in = [g for g in pads_in if g]
        if len(pads_in) > 1:
            report[net] = pads_in
        # dangling copper (tracks/vias not connected to any pad)
        for g in roots.values():
            if not any("#" not in nm for nm in g):
                report.setdefault(net + " (dangling copper)", []).append(g[:3])
    return report, plane_islands


def netlist_consistency():
    errs = []
    dn = design_nets()
    pn = {}
    for p in placed_pads_cache():
        if p.net:
            pn.setdefault(p.net, set()).add((p.ref, p.num))
    for net, pins in dn.items():
        if set(pins) != pn.get(net, set()):
            errs.append(("netlist-mismatch", net))
        if len(pins) < 2:
            errs.append(("single-pin-net", net, pins))
    return errs


def run(routes="routes.json", verbose=True):
    tracks, vias = load(routes)
    items = build_items(tracks, vias)
    res = {}
    res["drc"] = drc(items)
    res["courtyard"] = courtyards()
    planes = plane_rasters(items)
    res["unconnected"], res["plane_islands"] = connectivity(items, planes)
    res["netlist"] = netlist_consistency()
    res["plane_components"] = {L: planes[L][1] for L in planes}
    if verbose:
        print("DRC violations      :", len(res["drc"]))
        for e in res["drc"][:60]:
            print("   ", e)
        print("Courtyard issues    :", res["courtyard"])
        print("Unconnected nets    :", len(res["unconnected"]))
        for k, v in res["unconnected"].items():
            print("   ", k, v)
        print("Netlist issues      :", res["netlist"])
        print("Plane copper islands:", res["plane_components"], "| members per island:", res["plane_islands"])
        print("Tracks:", len(tracks), "Vias:", len(vias))
    return res


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "routes.json")
