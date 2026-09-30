"""geom.py - exact 2-D distance helpers. Every copper object is modelled as a
convex point set (1 point = circle, 2 points = capsule, >=3 = convex polygon)
dilated by a radius."""
import math
import numpy as np


def seg_pt(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _cross(ax, ay, bx, by, cx, cy):
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def seg_seg(a, b, c, d):
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = a, b, c, d
    d1 = _cross(cx, cy, dx, dy, ax, ay)
    d2 = _cross(cx, cy, dx, dy, bx, by)
    d3 = _cross(ax, ay, bx, by, cx, cy)
    d4 = _cross(ax, ay, bx, by, dx, dy)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 * d2 != 0 and d3 * d4 != 0:
        return 0.0
    return min(seg_pt(cx, cy, dx, dy, ax, ay), seg_pt(cx, cy, dx, dy, bx, by),
               seg_pt(ax, ay, bx, by, cx, cy), seg_pt(ax, ay, bx, by, dx, dy))


def point_in_convex(pts, px, py):
    n = len(pts)
    sign = 0
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        c = _cross(ax, ay, bx, by, px, py)
        if c != 0:
            s = 1 if c > 0 else -1
            if sign == 0:
                sign = s
            elif s != sign:
                return False
    return True


def edges(pts):
    if len(pts) == 1:
        return [(pts[0], pts[0])]
    if len(pts) == 2:
        return [(pts[0], pts[1])]
    return [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]


def core_dist(A, B):
    """distance between two convex cores (point / segment / polygon)."""
    if len(A) >= 3:
        for p in B:
            if point_in_convex(A, *p):
                return 0.0
    if len(B) >= 3:
        for p in A:
            if point_in_convex(B, *p):
                return 0.0
    best = 1e9
    for e1 in edges(A):
        for e2 in edges(B):
            best = min(best, seg_seg(e1[0], e1[1], e2[0], e2[1]))
            if best == 0:
                return 0.0
    return best


def shape_dist(s1, s2):
    """s = (pts, radius). returns edge-to-edge gap (negative/0 = touching)."""
    return core_dist(s1[0], s2[0]) - s1[1] - s2[1]


def bbox(s, grow=0.0):
    xs = [p[0] for p in s[0]]
    ys = [p[1] for p in s[0]]
    r = s[1] + grow
    return (min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r)


def bb_overlap(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


# ---------------- vectorised signed distance for rasterisation -----------
def raster_dist(pts, r, X, Y):
    """signed-ish distance from grid points (X, Y arrays) to shape; <=0 inside."""
    if len(pts) == 1:
        return np.hypot(X - pts[0][0], Y - pts[0][1]) - r
    if len(pts) == 2:
        (ax, ay), (bx, by) = pts
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
        return np.hypot(X - ax - t * dx, Y - ay - t * dy) - r
    d = np.full(X.shape, 1e9)
    inside = np.ones(X.shape, bool)
    n = len(pts)
    # orientation
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    for i in range(n):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
        d = np.minimum(d, np.hypot(X - ax - t * dx, Y - ay - t * dy))
        inside &= (sgn * ((bx - ax) * (Y - ay) - (by - ay) * (X - ax)) >= 0)
    return np.where(inside, -d, d) - r
