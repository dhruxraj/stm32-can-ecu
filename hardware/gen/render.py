"""render.py - matplotlib renders of the board for visual review."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle
from board import (placed_pads_cache, PLACEMENT, courtyard, outline_polygon, BX1, BY1, BX2, BY2)
from design import PARTS

LAYER_COL = {"F.Cu": "#c83434", "B.Cu": "#3a5fcd", "In1.Cu": "#999900", "In2.Cu": "#aa55aa"}


def _pad_patch(p, **kw):
    kind, pts, r = p.geom()
    if len(pts) == 1:
        return Circle(pts[0], r, **kw)
    if len(pts) == 2:
        # oval: draw as thick polygon approx
        import math
        (x1, y1), (x2, y2) = pts
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * r, dx / L * r
        poly = [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
        return Polygon(poly, closed=True, **kw)
    if r > 0:
        # expand polygon approx by r (axis-aligned)
        xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        return Rectangle((min(xs) - r, min(ys) - r), max(xs) - min(xs) + 2 * r, max(ys) - min(ys) + 2 * r, **kw)
    return Polygon(pts, closed=True, **kw)


def render(path, tracks=(), vias=(), title="", zoom=None, show_crt=True, show_nets=False, dpi=110, layers=("F.Cu", "B.Cu")):
    fig, ax = plt.subplots(figsize=(16, 12))
    ol = outline_polygon()
    ax.add_patch(Polygon(ol, closed=True, fill=True, fc="#0d3b1e", ec="yellow", lw=1.2))
    for t in tracks:
        if t["layer"] not in layers:
            continue
        import math
        (x1, y1), (x2, y2) = t["a"], t["b"]
        L = math.hypot(x2 - x1, y2 - y1) or 1e-9
        hw = t["w"] / 2
        nx, ny = -(y2 - y1) / L * hw, (x2 - x1) / L * hw
        kw = dict(fc=LAYER_COL[t["layer"]], ec="none", alpha=0.85 if t["layer"] == "F.Cu" else 0.7,
                  zorder=3 if t["layer"] == "F.Cu" else 2)
        ax.add_patch(Polygon([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], **kw))
        ax.add_patch(Circle((x1, y1), hw, **kw)); ax.add_patch(Circle((x2, y2), hw, **kw))
    for p in placed_pads_cache():
        if p.kind == "np_thru_hole":
            ax.add_patch(Circle((p.x, p.y), p.drill / 2, fc="black", ec="white", lw=0.5, zorder=4))
            continue
        col = "#d4a017" if p.kind != "thru_hole" else "#e0c060"
        ax.add_patch(_pad_patch(p, fc=col, ec="k", lw=0.2, zorder=4))
        if p.drill:
            ax.add_patch(Circle((p.x, p.y), p.drill / 2, fc="black", zorder=5))
        if show_nets and p.net:
            ax.text(p.x, p.y, p.net, fontsize=3 if not zoom else 6, clip_on=True, ha="center", va="center", zorder=6, color="navy")
    for v in vias:
        ax.add_patch(Circle(v["at"], v["size"] / 2, fc="#bbbbbb", ec="k", lw=0.3, zorder=5))
        ax.add_patch(Circle(v["at"], v["drill"] / 2, fc="black", zorder=6))
    for ref in PARTS:
        x1, y1, x2, y2 = courtyard(ref)
        if show_crt:
            ax.add_patch(Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, ec="#ff66ff", lw=0.5, zorder=6))
        fx, fy, _ = PLACEMENT[ref]
        ax.text((x1 + x2) / 2, (y1 + y2) / 2, ref, fontsize=6 if not zoom else 9, ha="center", va="center", clip_on=True,
                color="white", zorder=7, weight="bold")
    if zoom:
        ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[3], zoom[1])
    else:
        ax.set_xlim(BX1 - 2, BX2 + 2); ax.set_ylim(BY2 + 2, BY1 - 2)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.grid(True, lw=0.2, alpha=0.4)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "/tmp/place.png", title="placement", show_nets=True)
