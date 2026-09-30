"""
validate_files.py - re-parses the generated KiCad files (independently of the
generator's internal data) and checks structure, schematic connectivity (an
ERC subset), schematic <-> PCB netlist agreement and silkscreen collisions.
"""
import os
import re
import sys
from collections import defaultdict

KDIR = "/home/claude/stm32-can-ecu/hardware/kicad"
sys.path.insert(0, os.path.dirname(__file__))


# ------------------------------------------------------------------ s-expr
def tokenize(txt):
    toks = []
    i, n = 0, len(txt)
    while i < n:
        c = txt[i]
        if c in " \t\r\n":
            i += 1
        elif c in "()":
            toks.append(c); i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while txt[j] != '"':
                if txt[j] == "\\":
                    buf.append(txt[j + 1]); j += 2
                else:
                    buf.append(txt[j]); j += 1
            toks.append(("S", "".join(buf))); i = j + 1
        else:
            j = i
            while j < n and txt[j] not in ' \t\r\n()"':
                j += 1
            toks.append(txt[i:j]); i = j
    return toks


def parse(txt):
    toks = tokenize(txt)
    stack = [[]]
    for t in toks:
        if t == "(":
            stack.append([])
        elif t == ")":
            if len(stack) < 2:
                raise ValueError("unbalanced ')'")
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t[1] if isinstance(t, tuple) else t)
    if len(stack) != 1 or len(stack[0]) != 1:
        raise ValueError(f"unbalanced parens (depth {len(stack)})")
    return stack[0][0]


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key):
    r = find(node, key)
    return r[0] if r else None


# ------------------------------------------------------------------ schematic
def check_schematic(errors, info):
    sch = parse(open(os.path.join(KDIR, "CAN_ECU.kicad_sch")).read())
    assert sch[0] == "kicad_sch"
    libs = {}
    for s in find(first(sch, "lib_symbols"), "symbol"):
        pins = {}
        types = {}
        for sub in find(s, "symbol"):
            for p in find(sub, "pin"):
                at = first(p, "at")
                num = first(p, "number")[1]
                pins[num] = (float(at[1]), float(at[2]))
                types[num] = p[1]
        libs[s[1]] = (pins, types, "power" in [x for x in s if isinstance(x, str)])
    key = lambda x, y: (round(float(x), 3), round(float(y), 3))
    pinpts = defaultdict(list)     # point -> [(ref,pin,type)]
    refs = {}
    for s in find(sch, "symbol"):
        lib = first(s, "lib_id")[1]
        at = first(s, "at")
        X, Y = float(at[1]), float(at[2])
        ref = [p[2] for p in find(s, "property") if p[1] == "Reference"][0]
        if ref in refs:
            errors.append(f"SCH duplicate reference {ref}")
        refs[ref] = lib
        if lib not in libs:
            errors.append(f"SCH {ref}: lib symbol {lib} missing from lib_symbols")
            continue
        pins, types, _ = libs[lib]
        for num, (px, py) in pins.items():
            pinpts[key(X + px, Y - py)].append((ref, num, types[num]))
    wires = []
    for w in find(sch, "wire"):
        pts = first(w, "pts")
        a = key(pts[1][1], pts[1][2]); b = key(pts[2][1], pts[2][2])
        wires.append((a, b))
    labels = defaultdict(list)
    for l in find(sch, "label"):
        at = first(l, "at")
        labels[key(at[1], at[2])].append(l[1])
    ncs = {key(first(n, "at")[1], first(n, "at")[2]) for n in find(sch, "no_connect")}
    # union-find over points
    parent = {}

    def f(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def u(a, b):
        parent[f(a)] = f(b)
    for a, b in wires:
        u(a, b)
    for pt, names in labels.items():
        if pt not in parent:
            errors.append(f"SCH label {names} at {pt} not attached to a wire")
        if len(set(names)) > 1:
            errors.append(f"SCH conflicting labels at {pt}: {names}")
        for nm in names:
            u(pt, ("LABEL", nm))
    nets = defaultdict(set)
    for pt, plist in pinpts.items():
        for ref, num, typ in plist:
            if pt in ncs:
                if pt in parent:
                    errors.append(f"SCH {ref}.{num} has a no-connect flag AND a wire")
                continue
            if pt not in parent:
                if typ != "no_connect":
                    errors.append(f"SCH unconnected pin {ref}.{num} ({typ})")
                continue
            nets[f(pt)].add((ref, num, typ))
    # name nets
    named = {}
    for root, members in nets.items():
        names = {k[1] for k in parent if isinstance(k, tuple) and k[0] == "LABEL" and f(k) == root}
        if len(names) != 1:
            errors.append(f"SCH net with labels {names}: {sorted(members)[:4]}")
            continue
        named[names.pop()] = members
    # compare with design
    from design import nets as dnets, PARTS
    dn = dnets()
    for net, pins in dn.items():
        got = {(r, n) for (r, n, t) in named.get(net, set()) if not r.startswith('#FLG')}
        if got != set(pins):
            errors.append(f"SCH net {net} mismatch: missing {set(pins) - got}, extra {got - set(pins)}")
    for ref in PARTS:
        if ref not in refs:
            errors.append(f"SCH missing symbol {ref}")
    # ERC subset: power_in pins must be driven by power_out (incl. PWR_FLAG)
    for net, members in named.items():
        types = [t for (_, _, t) in members]
        if "power_in" in types and "power_out" not in types:
            errors.append(f"ERC net {net}: power input pins not driven (no power_out / PWR_FLAG)")
        if types.count("power_out") > 1:
            errors.append(f"ERC net {net}: {types.count('power_out')} power outputs connected together")
        if types.count("output") > 1:
            errors.append(f"ERC net {net}: multiple outputs")
        if len(members) < 2:
            errors.append(f"ERC net {net}: single pin")
    info["sch_symbols"] = len(refs)
    info["sch_nets"] = len(named)
    info["sch_wires"] = len(wires)
    info["sch_labels"] = sum(len(v) for v in labels.values())
    info["sch_noconnect"] = len(ncs)


# ------------------------------------------------------------------ pcb
def check_pcb(errors, info):
    pcb = parse(open(os.path.join(KDIR, "CAN_ECU.kicad_pcb")).read())
    assert pcb[0] == "kicad_pcb"
    netnames = {int(n[1]): n[2] for n in find(pcb, "net")}
    from design import PARTS
    fps = find(pcb, "footprint")
    seen = set()
    fplib = set(x[:-10] for x in os.listdir(os.path.join(KDIR, "CAN_ECU.pretty")))
    for fp in fps:
        name = fp[1].split(":")[1]
        if name not in fplib:
            errors.append(f"PCB footprint {name} not in CAN_ECU.pretty")
        ref = [t[2] for t in find(fp, "fp_text") if t[1] == "reference"][0]
        seen.add(ref)
        part = PARTS[ref]
        for p in find(fp, "pad"):
            num = p[1]
            nn = first(p, "net")
            got = nn[2] if nn else None
            exp = part.pins.get(num) if num else None
            if got != exp:
                errors.append(f"PCB pad {ref}.{num}: net {got} != schematic {exp}")
            if nn and netnames.get(int(nn[1])) != nn[2]:
                errors.append(f"PCB pad {ref}.{num}: net id/name mismatch")
    for ref in PARTS:
        if ref not in seen:
            errors.append(f"PCB missing footprint {ref}")
    for s in find(pcb, "segment") + find(pcb, "via"):
        nid = int(first(s, "net")[1])
        if nid not in netnames or nid == 0:
            errors.append(f"PCB track/via with bad net {nid}")
    # edge cuts closed
    ends = defaultdict(int)
    for g in find(pcb, "gr_line") + find(pcb, "gr_arc"):
        if first(g, "layer")[1] != "Edge.Cuts":
            continue
        a = first(g, "start"); b = first(g, "end")
        ends[(round(float(a[1]), 3), round(float(a[2]), 3))] += 1
        ends[(round(float(b[1]), 3), round(float(b[2]), 3))] += 1
    if any(v != 2 for v in ends.values()):
        errors.append(f"PCB Edge.Cuts outline not closed: {[k for k, v in ends.items() if v != 2]}")
    info["pcb_footprints"] = len(fps)
    info["pcb_segments"] = len(find(pcb, "segment"))
    info["pcb_vias"] = len(find(pcb, "via"))
    info["pcb_zones"] = len(find(pcb, "zone"))
    info["pcb_nets"] = len(netnames) - 1
    return pcb


def check_silk(pcb, errors, info):
    """silk text boxes vs exposed pads, other text and board edge."""
    import math
    from board import placed_pads_cache, BX1, BY1, BX2, BY2
    from lib import rot_pt
    pads = [p.bbox() for p in placed_pads_cache() if p.kind != "np_thru_hole"]
    holes = [(p.x - 1.8, p.y - 1.8, p.x + 1.8, p.y + 1.8) for p in placed_pads_cache() if p.kind == "np_thru_hole"]
    boxes = []

    def tb(x, y, s, size, rot):
        w = len(s) * size * 0.8 + 0.2; h = size * 1.25
        if rot in (90, 270):
            w, h = h, w
        return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
    for fp in find(pcb, "footprint"):
        at = first(fp, "at")
        fx, fy = float(at[1]), float(at[2])
        frot = float(at[3]) if len(at) > 3 else 0
        for t in find(fp, "fp_text"):
            if first(t, "layer")[1] != "F.SilkS":
                continue
            tat = first(t, "at")
            lx, ly = float(tat[1]), float(tat[2])
            trot = float(tat[3]) if len(tat) > 3 else 0
            dx, dy = rot_pt(lx, ly, frot)
            size = float(first(first(first(t, "effects"), "font"), "size")[1])
            boxes.append((t[2], tb(fx + dx, fy + dy, t[2], size, trot)))
    for g in find(pcb, "gr_text"):
        if first(g, "layer")[1] != "F.SilkS":
            continue
        at = first(g, "at")
        size = float(first(first(first(g, "effects"), "font"), "size")[1])
        rot = float(at[3]) if len(at) > 3 else 0
        boxes.append((g[1], tb(float(at[1]), float(at[2]), g[1], size, rot)))
    ov = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    for i, (s, b) in enumerate(boxes):
        if b[0] < BX1 + 0.3 or b[1] < BY1 + 0.3 or b[2] > BX2 - 0.3 or b[3] > BY2 - 0.3:
            errors.append(f"SILK text '{s}' too close to / outside board edge")
        for p in pads:
            if ov(b, p):
                errors.append(f"SILK text '{s}' overlaps a pad")
                break
        for h in holes:
            if ov(b, h):
                errors.append(f"SILK text '{s}' overlaps a mounting hole")
        for s2, b2 in boxes[i + 1:]:
            if ov(b, b2):
                errors.append(f"SILK text '{s}' overlaps text '{s2}'")
    info["silk_texts"] = len(boxes)


def main():
    errors, info = [], {}
    for fn in ["CAN_ECU.kicad_sym", "CAN_ECU.kicad_sch", "CAN_ECU.kicad_pcb", "sym-lib-table", "fp-lib-table"] + \
              ["CAN_ECU.pretty/" + x for x in sorted(os.listdir(os.path.join(KDIR, "CAN_ECU.pretty")))]:
        try:
            parse(open(os.path.join(KDIR, fn)).read())
        except Exception as e:
            errors.append(f"PARSE {fn}: {e}")
    import json
    json.load(open(os.path.join(KDIR, "CAN_ECU.kicad_pro")))
    check_schematic(errors, info)
    pcb = check_pcb(errors, info)
    check_silk(pcb, errors, info)
    for k, v in info.items():
        print(f"  {k:16s} {v}")
    print(f"ERRORS: {len(errors)}")
    for e in errors:
        print("  ", e)
    return errors


if __name__ == "__main__":
    main()
