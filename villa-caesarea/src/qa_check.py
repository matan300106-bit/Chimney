#!/usr/bin/env python3
"""Dimensions & regulations QA checker for 'Beit Kurkar' (villa-caesarea).

Reads the parametric model (model.py / geom.py) and checks geometry consistency,
Israeli planning/building rules used in the brief, stair geometry & headroom,
furniture fit/clearances and site rules.  Prints a report and writes
out/qa_report.md.  Re-runnable: it only reads the model.

    python3 villa-caesarea/src/qa_check.py            # full report
    python3 villa-caesarea/src/qa_check.py --quiet    # summary only on stdout

Severity: ERROR (must fix: code / geometry broken), WARN (should fix / verify),
INFO (note for the drawings / calculation sheet).
"""
from __future__ import annotations

import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
# --model-dir DIR : check a patched copy of model.py (e.g. to validate proposed fixes) – report goes to DIR
MODEL_DIR = None
if "--model-dir" in sys.argv:
    MODEL_DIR = os.path.abspath(sys.argv[sys.argv.index("--model-dir") + 1])
    sys.path.insert(0, MODEL_DIR)

import model as M  # noqa: E402
import geom as G   # noqa: E402

from shapely.geometry import Point, Polygon, box as sbox  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

EPS = 1e-6
LEVELS = ["B", "G", "U", "R"]
LVL_HE = {"B": "מרתף", "G": "קרקע", "U": "קומה א'", "R": "גג"}
NEXT = {"B": "G", "G": "U", "U": "R"}
BELOW = {"G": "B", "U": "G", "R": "U"}

# --------------------------------------------------------------------------- #
#  Rules (one place – tune here)
# --------------------------------------------------------------------------- #
R = dict(
    tol_room_wall=0.03,       # room polygon may overlap a wall by ≤3 cm
    jamb_min_door=0.08,       # door frame needs ≥8 cm of wall beside the junction
    jamb_min_win=0.05,
    door_entry_min=0.90, door_room_min=0.80, door_wc_min=0.70,
    bed_min_area=9.0, bed_min_w=2.60,
    mamad_min_area=9.0, mamad_wall_min=0.25, mamad_door=(0.80, 2.00), mamad_win_max=(1.00, 1.00),
    mamad_service_max=12.0,   # net ממ"ד area normally counted as service – verify takanon
    stair_2rt=(0.61, 0.63), riser_max=0.175, tread_min=0.26, stair_w_min=1.00,
    headroom_min=2.10, headroom_target=2.20,
    clear_hab=2.50, clear_service=2.20, ceil_plenum_min=0.10,
    rail_min=1.05, rail_stair=0.90, guard_drop=0.50, win_sill_guard=0.90,
    lot_coverage=0.40, main_pct=0.35, service_pct=0.16,
    pool_water_max=60.0, pool_depth_max=1.80, pool_boundary_min=2.0,
    roof_room_max=23.0, roof_room_setback=1.20,
    canopy_proj_max=0.40,      # projections into a setback ≤ 40 % of the setback
    bed_side=0.60, closet_front=0.80, kitchen_aisle=1.00, island_clear=1.00, door_approach=0.60,
    park_w=2.50, park_l=5.00,
    win_area_ratio=0.10,
)

# --------------------------------------------------------------------------- #
#  Findings
# --------------------------------------------------------------------------- #
FINDINGS: list[dict] = []
SECTIONS = {}


def add(sev, cat, msg, fix=None, key=None):
    FINDINGS.append(dict(sev=sev, cat=cat, msg=msg, fix=fix, key=key))


def r2(v):
    return f"{v:.2f}"


def cm(v):
    return f"{v * 100:.0f} cm"


def rr(t):
    return "(" + ", ".join(f"{v:.2f}" for v in t) + ")"


def floor_z(level):
    return M.LV[level]


# --------------------------------------------------------------------------- #
#  Geometry helpers
# --------------------------------------------------------------------------- #
def wid(w):
    """short human id of a wall"""
    return (f"{w.level}:{w.kind}{'H' if w.horiz else 'V'}"
            f"[{'y' if w.horiz else 'x'}={w.c:.2f} {w.a0:.2f}→{w.a1:.2f} t{w.t:.2f}]")


def is_site_wall(w):
    """retaining walls of the sunken patio etc. (outside the basement outline)"""
    if w.kind != "retain":
        return False
    cx = (w.a0 + w.a1) / 2 if w.horiz else w.c
    cy = w.c if w.horiz else (w.a0 + w.a1) / 2
    return not (M.X_W - 0.2 <= cx <= M.X_E + 0.2 and M.Y_S_G - 0.2 <= cy <= M.Y_N + 0.2)


def wall_fp(w, extend_ext=True):
    a0, a1 = w.a0, w.a1
    if extend_ext and w.kind in ("ext", "retain") and not is_site_wall(w):
        a0, a1 = a0 - w.t / 2, a1 + w.t / 2
    h = w.t / 2
    if w.horiz:
        return sbox(a0, w.c - h, a1, w.c + h)
    return sbox(w.c - h, a0, w.c + h, a1)


def z_overlap(a0, a1, b0, b1, tol=0.01):
    return min(a1, b1) - max(a0, b0) > tol


def plan_walls(level, include_parapet=False, include_site=False):
    out = []
    for w in M.WALLS:
        if w.level != level:
            continue
        if w.kind == "parapet" and not include_parapet:
            continue
        if is_site_wall(w) and not include_site:
            continue
        out.append(w)
    return out


def col_fp(c):
    return sbox(c.x - c.w / 2, c.y - c.d / 2, c.x + c.w / 2, c.y + c.d / 2)


def cols_on(level):
    z0, z1 = floor_z(level), floor_z(level) + 2.0
    return [c for c in M.COLS if z_overlap(c.z0, c.z1, z0, z1)]


def room_poly(r):
    return unary_union([sbox(*q) for q in r.rects])


def room_label(r):
    return f"{r.no} '{r.name}'"


def furn_box(f):
    return sbox(f.x, f.y, f.x + f.w, f.y + f.d)


def furn_label(f):
    return f"{f.kind}@{f.level}({f.x:.2f},{f.y:.2f} {f.w:.2f}×{f.d:.2f})"


def furn_line(f):
    lab = f', label="{f.label}"' if f.label else ""
    h = f", h={f.h}" if f.h else ""
    return f'furn("{f.kind}", "{f.level}", {f.x}, {f.y}, {f.w}, {f.d}, rot={f.rot}{h}{lab})'


def min_dim(poly):
    if poly.is_empty:
        return 0.0
    x0, y0, x1, y1 = poly.bounds
    return min(x1 - x0, y1 - y0)


def decompose(poly):
    try:
        return G.decompose(poly)
    except Exception:
        return [poly.bounds]


LOW_FURN = {"rug", "mat", "shower"}       # floor-level items (shower = tray zone)
NOT_OBSTACLE = {"rug"}


def furn_shapes(f):
    """Plan shape of a furniture item (L-shapes for *_l)."""
    b = furn_box(f)
    if not f.kind.endswith("_l"):
        return b
    leg = 0.62 if f.kind.startswith("counter") else 0.95
    x0, y0, x1, y1 = f.x, f.y, f.x + f.w, f.y + f.d
    corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    corner = None
    tables = [o for o in M.FURN if o is not f and o.level == f.level and o.kind in ("coffee", "table_rect", "table_round")
              and b.contains(furn_box(o).centroid)]
    if tables and f.kind.startswith("sofa"):
        c = furn_box(tables[0]).centroid
        corner = max(corners, key=lambda p: math.hypot(p[0] - c.x, p[1] - c.y))
    else:  # corner closest to walls
        walls = unary_union([wall_fp(w) for w in plan_walls(f.level)])
        corner = min(corners, key=lambda p: walls.distance(Point(p)))
    cx, cy = corner
    inner = sbox(x0 + leg if cx == x0 else x0, y0 + leg if cy == y0 else y0,
                 x1 - leg if cx == x1 else x1, y1 - leg if cy == y1 else y1)
    return b.difference(inner)


# --------------------------------------------------------------------------- #
#  Openings
# --------------------------------------------------------------------------- #
OPS = []   # (wall, opening)
for _w in M.WALLS:
    for _o in _w.openings:
        OPS.append((_w, _o))


def op_label(w, o):
    t = o.tag or o.kind
    return f"{t} ({w.level}, {'y' if w.horiz else 'x'}={w.c:.2f}, {o.pos:.2f}→{o.end:.2f})"


def op_rect(w, o, extra=0.0, through=0.0):
    h = w.t / 2 + through
    a0, a1 = o.pos - extra, o.end + extra
    if w.horiz:
        return sbox(a0, w.c - h, a1, w.c + h)
    return sbox(w.c - h, a0, w.c + h, a1)


def side_point(w, o, side, d=0.30):
    m = (o.pos + o.end) / 2
    off = side * (w.t / 2 + d)
    return (m, w.c + off) if w.horiz else (w.c + off, m)


def side_zone(w, o, side, depth):
    """rectangle of `depth` in front of the opening on `side` (+1 north/east)."""
    f = w.c + side * w.t / 2
    lo, hi = sorted((f, f + side * depth))
    if w.horiz:
        return sbox(o.pos, lo, o.end, hi)
    return sbox(lo, o.pos, hi, o.end)


def swing_poly(w, o):
    """Swept area of a hinged leaf (quarter disc) or pivot (both sides)."""
    W = o.end - o.pos
    if o.kind == "pivot":
        piv = o.pos + 0.18 * W           # same as plans.py
        rad = max(0.82 * W, 0.18 * W)
        polys = []
        for s in (1, -1):
            f = w.c + s * w.t / 2
            lo, hi = sorted((f, f + s * rad))
            c = Point((piv, f) if w.horiz else (f, piv)).buffer(rad, 64)
            clip = sbox(piv - rad, lo, piv + rad, hi) if w.horiz else sbox(lo, piv - rad, hi, piv + rad)
            polys.append(c.intersection(clip))
        return unary_union(polys)
    s = o.swing
    f = w.c + s * w.t / 2
    ha = o.pos if o.hinge == "a" else o.end
    lo, hi = sorted((f, f + s * W))
    if w.horiz:
        c = Point(ha, f).buffer(W, 64)
        clip = sbox(o.pos, lo, o.end, hi)
    else:
        c = Point(f, ha).buffer(W, 64)
        clip = sbox(lo, o.pos, hi, o.end)
    return c.intersection(clip)


def op_line(w, o):
    """Reconstruct the model.py op(...) line for a fix proposal."""
    c = w.c
    kw = ""
    if o.kind in ("door", "mamad_door", "pivot"):
        kw = f', hinge="{o.hinge}", swing={o.swing}'
    if o.frosted:
        kw += ", frosted=True"
    tag = f', "{o.tag}"' if o.tag else ""
    return (f'op("{w.level}", {"H" if w.horiz else "V"}, {c:.2f}, {o.pos:.2f}, {o.end:.2f}, {o.sill}, {o.head}, '
            f'"{o.kind}"{tag}{kw})')


# --------------------------------------------------------------------------- #
#  Rooms
# --------------------------------------------------------------------------- #
def rooms_on(level):
    return [r for r in M.ROOMS if r.level == level]


def room_at(level, x, y, outdoor=True):
    p = Point(x, y)
    for r in rooms_on(level):
        if not outdoor and r.outdoor:
            continue
        if room_poly(r).buffer(0.02).contains(p):
            return r
    return None


def is_bedroom(r):
    return ("שינה" in r.name) or r.name.startswith("חדר אורחים") or ('ממ"ד' in r.name)


def is_wet(r):
    return any(k in r.name for k in ("רחצה", "שירותי", "כביסה", "ספא", "מקלחת"))


def is_wc(r):
    return "שירותי" in r.name


def is_habitable(r):
    if r.outdoor or r.service:
        return 'ממ"ד' in r.name  # ממ"ד used as a child room
    return not is_wet(r) and not any(k in r.name for k in ("פרוזדור", "מזווה", "מבואה", "יציאה", "הלבשה", "מחסן",
                                                          "טכני", "יין"))


def stair_cage_poly(level):
    """Plan area of the stair cage on a level (for areas / void checks)."""
    sts = [s for s in M.STAIRS if s["level"] == level or NEXT.get(s["level"]) == level]
    if not sts:
        return None
    ys = []
    for s in sts:
        if s["level"] == level:
            ys.append(s["yA0"])
        else:
            ys.append(s["yB_end"])
    xb1 = M.ST["x0"] + 2 * M.ST["w"] + M.ST["gap"]
    return sbox(M.ST["x0"], min(ys), xb1, M.ST["yn"])


# =========================================================================== #
#  1. WALLS
# =========================================================================== #
def check_walls():
    cat = "1 Walls"
    for lvl in LEVELS:
        ws = plan_walls(lvl, include_parapet=True)
        # --- overlaps / duplicates
        for i, a in enumerate(ws):
            fa = wall_fp(a)
            for b in ws[i + 1:]:
                if not z_overlap(a.z0, a.z1, b.z0, b.z1):
                    continue
                fb = wall_fp(b)
                inter = fa.intersection(fb)
                if a.horiz == b.horiz:
                    if abs(a.c - b.c) < (a.t + b.t) / 2 - 0.005:
                        L = min(a.a1, b.a1) - max(a.a0, b.a0)
                        if L > 0.05 and inter.area > 1e-4:
                            d = (a.t + b.t) / 2 - abs(a.c - b.c)
                            if a.kind == "parapet" and b.kind == "parapet":
                                continue
                            if "parapet" in (a.kind, b.kind):
                                p_, o_ = (a, b) if a.kind == "parapet" else (b, a)
                                add("WARN", cat, f"Roof parapet runs through another wall over {L:.2f} m: {wid(p_)} "
                                    f"overlaps {wid(o_)} – stop the parapet at that wall (split the parapet loop)",
                                    fix="in the UF_OUT parapet loop skip the stretch x 12.90→17.80 on the north edge "
                                        "(the roof-exit wall is the parapet there)",
                                    key=f"parapet_overlap:{lvl}:{o_.c:.2f}")
                                continue
                            sev = "ERROR" if (L > 0.5 or d > 0.07) else "WARN"
                            add(sev, cat, f"Parallel walls overlap {cm(d)} over {L:.2f} m: {wid(a)} & {wid(b)}",
                                key=f"wall_overlap:{lvl}:{a.c:.2f}:{b.c:.2f}")
                    elif abs(abs(a.c - b.c) - (a.t + b.t) / 2) < 0.006:
                        L = min(a.a1, b.a1) - max(a.a0, b.a0)
                        if L > 0.3 and "parapet" not in (a.kind, b.kind):
                            add("INFO", cat, f"Double wall (two walls face-to-face over {L:.2f} m, total "
                                f"{cm(a.t + b.t)}): {wid(a)} & {wid(b)} – draw as one or note it",
                                key=f"wall_double:{lvl}:{a.c:.2f}:{b.c:.2f}")
                else:
                    if inter.area < 1e-4:
                        continue
                    h, v = (a, b) if a.horiz else (b, a)
                    vx0, vx1 = v.c - v.t / 2, v.c + v.t / 2
                    hy0, hy1 = h.c - h.t / 2, h.c + h.t / 2
                    ha0, ha1 = wall_fp(h).bounds[0], wall_fp(h).bounds[2]
                    va0, va1 = wall_fp(v).bounds[1], wall_fp(v).bounds[3]
                    h_through = ha0 < vx0 - 0.03 and ha1 > vx1 + 0.03
                    v_through = va0 < hy0 - 0.03 and va1 > hy1 + 0.03
                    if h_through and v_through:
                        add("INFO", cat, f"Walls cross (X-junction) – draw/build as two walls: {wid(h)} × {wid(v)}",
                            key=f"wall_cross:{lvl}:{h.c:.2f}:{v.c:.2f}")
        # --- junctions: free ends / gaps
        allfp = [(w, wall_fp(w)) for w in ws]
        cfp = [col_fp(c) for c in cols_on(lvl)] if lvl != "R" else []
        for w in ws:
            if w.kind in ("ext", "retain", "parapet"):
                continue
            others = [(ww, fp) for ww, fp in allfp if ww is not w and z_overlap(ww.z0, ww.z1, w.z0, w.z1)]
            # attached face-to-face along its length (double wall) → ends are not free
            if any(ww.horiz == w.horiz and abs(abs(ww.c - w.c) - (ww.t + w.t) / 2) < 0.01 and
                   min(ww.a1, w.a1) - max(ww.a0, w.a0) > 0.3 for ww, _ in others):
                continue
            touches = 0
            for end in (0, 1):
                a = w.a0 if end == 0 else w.a1
                d = -1 if end == 0 else 1
                h = w.t / 2
                if w.horiz:
                    probe = sbox(a - 0.02, w.c - h, a + 0.02, w.c + h)
                    cap = sbox(a, w.c - h, a + 1e-4, w.c + h)
                else:
                    probe = sbox(w.c - h, a - 0.02, w.c + h, a + 0.02)
                    cap = sbox(w.c - h, a, w.c + h, a + 1e-4)
                if any(fp.intersection(probe).area > 1e-7 for _, fp in others) or \
                        any(c.intersection(probe).area > 1e-7 for c in cfp):
                    touches += 1
                    continue
                pt = f"({a:.2f},{w.c:.2f})" if w.horiz else f"({w.c:.2f},{a:.2f})"
                cand = sorted(((cap.distance(fp), ww, fp) for ww, fp in others), key=lambda t: t[0])
                if w.kind == "shaft" and any(ww.kind == "shaft" and ww.horiz == w.horiz and abs(ww.c - w.c) < 0.01
                                             and cap.distance(fp) < 1.2 for ww, fp in others):
                    touches += 1      # lift landing door gap (checked in the lift section)
                    continue
                if cand and cand[0][0] < 0.6:
                    gap, ww, fp = cand[0]
                    if ww.horiz != w.horiz:          # perpendicular: close the corner to its far face
                        tgt = (fp.bounds[2] if d > 0 else fp.bounds[0]) if w.horiz else (fp.bounds[3] if d > 0 else fp.bounds[1])
                        if (ww.a0 - 0.01 <= w.c <= ww.a1 + 0.01):   # T: stop at the near face
                            tgt = (fp.bounds[0] if d > 0 else fp.bounds[2]) if w.horiz else (fp.bounds[1] if d > 0 else fp.bounds[3])
                    else:
                        tgt = (fp.bounds[0] if d > 0 else fp.bounds[2]) if w.horiz else (fp.bounds[1] if d > 0 else fp.bounds[3])
                    sev = "INFO" if gap <= 0.08 else "WARN"
                    what = "Corner notch" if gap <= 0.08 else "Gap"
                    add(sev, cat, f"{what} of {cm(gap)} at end {pt} of {wid(w)} (next to {wid(ww)})",
                        fix=f"extend that end of the wall to {'x' if w.horiz else 'y'}={tgt:.2f}",
                        key=f"wall_gap:{lvl}:{w.c:.2f}:{a:.2f}")
                    touches += 1 if gap <= 0.08 else 0
                else:
                    sev = "INFO" if w.kind in ("glass",) or w.t <= 0.10 else "WARN"
                    add(sev, cat, f"Wall ends in mid-air at {pt}: {wid(w)}",
                        fix="tie it into a wall/column or confirm it is a free-standing stub (draw end detail)",
                        key=f"wall_free:{lvl}:{w.c:.2f}:{a:.2f}")
            if touches == 0:
                add("ERROR", cat, f"Interior wall touches nothing at either end: {wid(w)}",
                    key=f"wall_float:{lvl}:{w.c:.2f}")
        # --- exterior outline closed
        ext = [w for w in ws if w.kind in ("ext", "retain") and not is_site_wall(w)]
        if not ext:
            continue
        u = unary_union([wall_fp(w) for w in ext])
        geoms = list(getattr(u, "geoms", [u]))
        holes = sum(len(g.interiors) for g in geoms)
        if len(geoms) != 1 or holes < 1:
            add("ERROR", cat, f"Exterior outline of level {lvl} is not closed (pieces={len(geoms)}, enclosed={holes})")
        else:
            add("INFO", cat, f"Exterior outline {lvl} closed; gross {Polygon(geoms[0].exterior).area:.1f} m² "
                f"(outer faces), inside the exterior walls {Polygon(geoms[0].interiors[0]).area:.1f} m²")


def interior_poly(level):
    ext = [w for w in plan_walls(level) if w.kind in ("ext", "retain")]
    if not ext:
        return None
    u = unary_union([wall_fp(w) for w in ext])
    g = max(getattr(u, "geoms", [u]), key=lambda g: g.area)
    if not g.interiors:
        return None
    return Polygon(max(g.interiors, key=lambda r: Polygon(r).area))


def gross_poly(level):
    ext = [w for w in plan_walls(level) if w.kind in ("ext", "retain")]
    if not ext:
        return None
    u = unary_union([wall_fp(w) for w in ext])
    g = max(getattr(u, "geoms", [u]), key=lambda g: g.area)
    return Polygon(g.exterior)


# =========================================================================== #
#  2. OPENINGS & DOORS
# =========================================================================== #
def stair_obstacles(level):
    """Plan footprint at `level` of stair flights/landing that block walking (treads ≥ 0.3 above floor
    up to 2.0, landing) plus floor voids (holes in the slab of this level)."""
    out = []
    fz = floor_z(level)
    for s in M.STAIRS:
        for (x0, y0, x1, y1, z) in s["treadsA"] + s["treadsB"]:
            if fz + 0.25 < z < fz + 2.05 or fz - 2.2 < z - 0.25 < fz + 2.0 and z > fz + 0.25:
                out.append(sbox(x0, y0, x1, y1))
        x0, y0, x1, y1, z = s["landing"]
        if fz + 0.25 < z < fz + 2.3:
            out.append(sbox(x0, y0, x1, y1))
    for sl in M.SLABS:
        if abs(sl.top + M.FIN - fz) < 0.02 or (level == "R" and abs(sl.top + M.FIN - fz) < 0.02):
            for h in sl.holes:
                out.append(sbox(*h))
    return unary_union(out) if out else None


def check_openings():
    cat = "2 Openings & doors"
    by_wall = defaultdict(list)
    for w, o in OPS:
        by_wall[id(w)].append((w, o))
    swings = []   # (level, poly, w, o)
    for w, o in OPS:
        lvl = w.level
        fz = floor_z(lvl)
        lab = op_label(w, o)
        # --- sill / head
        if o.head <= o.sill + 1e-6:
            add("ERROR", cat, f"{lab}: head {o.head} ≤ sill {o.sill}")
        clear = w.z1 - fz
        if o.head > clear + 0.005:
            if o.kind == "fixed" and o.sill < 0:
                add("INFO", cat, f"{lab}: continuous glazing runs past the slab soffit (head {o.head:.2f} > clear "
                    f"{clear:.2f}) – curtain-wall strip in front of the slab edge; detail the transom")
            else:
                add("ERROR", cat, f"{lab}: head {o.head:.2f} above storey clear height {clear:.2f} (wall top)",
                    fix=f"set head ≤ {clear:.2f}")
        if fz + o.sill < w.z0 - 0.005 and o.kind not in ("open", "passage"):
            add("INFO", cat, f"{lab}: sill {o.sill} is below the host wall base – continuous glazing across the slab "
                "edge; detail the slab-edge transom")
        # --- extents
        if o.pos < w.a0 - 0.005 or o.end > w.a1 + 0.005:
            add("ERROR", cat, f"{lab}: opening outside its wall extent {w.a0:.2f}→{w.a1:.2f}")
        if o.end - o.pos <= 0:
            add("ERROR", cat, f"{lab}: zero/negative width")
        # --- junctions/columns
        oz0, oz1 = fz + min(o.sill, 0 if o.kind in ("passage", "open") else o.sill), fz + o.head
        orect = op_rect(w, o)
        for ww in plan_walls(lvl, include_parapet=True):
            if ww is w or not z_overlap(ww.z0, ww.z1, oz0, oz1):
                continue
            fp = wall_fp(ww)
            ia = fp.intersection(orect).area
            if ia > 1e-4:
                add("ERROR", cat, f"{lab}: opening is cut by / blocked by wall {wid(ww)} "
                    f"(overlap {ia:.3f} m²)", key=f"op_cut:{o.tag}:{w.c:.2f}:{o.pos:.2f}")
            elif o.kind != "open":
                jm = R["jamb_min_door"] if o.kind in ("door", "mamad_door", "pivot") else R["jamb_min_win"]
                if ww.horiz != w.horiz and fp.intersection(op_rect(w, o, extra=jm - 0.001)).area > 1e-6:
                    gap = min(abs(o.pos - (ww.c + ww.t / 2)), abs(o.end - (ww.c - ww.t / 2)))
                    add("WARN", cat, f"{lab}: only {cm(gap)} of wall between opening and junction with {wid(ww)} "
                        f"(min {cm(jm)} for frame/plaster stop)", key=f"op_jamb:{o.tag}:{w.c:.2f}:{o.pos:.2f}")
        for c in M.COLS:
            if not z_overlap(c.z0, c.z1, oz0, oz1):
                continue
            cf = col_fp(c)
            if cf.intersection(orect).area > 1e-4:
                add("ERROR", cat, f"{lab}: opening cuts column ({c.x},{c.y})")
            elif cf.intersection(op_rect(w, o, extra=R["jamb_min_win"] - 0.001)).area > 1e-6 and o.kind != "open":
                ca0, ca1 = (cf.bounds[0], cf.bounds[2]) if w.horiz else (cf.bounds[1], cf.bounds[3])
                np_, ne_ = o.pos, o.end
                if abs(o.end - ca0) < abs(o.pos - ca1):
                    ne_ = round(ca0 - 0.10, 2)
                else:
                    np_ = round(ca1 + 0.10, 2)
                add("WARN", cat, f"{lab}: opening runs flush against column ({c.x},{c.y}) – no jamb / no "
                    "room for the frame anchor",
                    fix=f"{op_line(w, o)} → pos/end {np_:.2f}/{ne_:.2f}", key=f"op_col:{o.tag}:{c.x}:{c.y}")
        # --- door widths
        W = o.end - o.pos
        if o.kind in ("door", "pivot", "mamad_door"):
            sides = [room_at(lvl, *side_point(w, o, s)) for s in (1, -1)]
            names = [r for r in sides if r]
            is_entry = w.kind == "ext" and (None in sides or any(r.outdoor for r in names)) and lvl == "G"
            if o.kind == "pivot" or (o.tag == "D-01"):
                is_entry = True
            need = R["door_room_min"]
            what = "room door"
            if is_entry:
                need, what = R["door_entry_min"], "entrance door"
            elif any(is_wc(r) for r in names):
                need, what = R["door_wc_min"], "WC door"
            if W < need - 0.005:
                add("ERROR", cat, f"{lab}: {what} width {W:.2f} < {need:.2f}")
            if o.kind == "mamad_door":
                if abs(W - R["mamad_door"][0]) > 0.005 or abs(o.head - R["mamad_door"][1]) > 0.005:
                    add("ERROR", cat, f'{lab}: ממ"ד blast door must be 80/200 (is {W:.2f}/{o.head:.2f})')
            if o.head < 2.00:
                add("ERROR", cat, f"{lab}: door head {o.head} < 2.00")
            # swing
            sp = swing_poly(w, o)
            swings.append((lvl, sp, w, o))
            for ww in plan_walls(lvl, include_parapet=True):
                if ww is w or not z_overlap(ww.z0, ww.z1, fz, fz + 2.0):
                    continue
                ia = sp.intersection(wall_fp(ww)).area
                if ia > 0.003:
                    add("ERROR", cat, f"{lab}: door swing hits wall {wid(ww)}", key=f"swing_wall:{o.tag}")
            for c in cols_on(lvl):
                if sp.intersection(col_fp(c)).area > 0.003:
                    add("ERROR", cat, f"{lab}: door swing hits column ({c.x},{c.y})")
            for f in M.FURN:
                if f.level != lvl or f.kind in NOT_OBSTACLE:
                    continue
                ia = sp.intersection(furn_shapes(f)).area
                if ia > 0.003:
                    flip = -o.swing
                    other = swing_poly(w, Opening_like(o, swing=flip))
                    ok_other = not any(other.intersection(furn_shapes(g)).area > 0.003 for g in M.FURN
                                       if g.level == lvl and g.kind not in NOT_OBSTACLE) and not any(
                        other.intersection(wall_fp(x)).area > 0.003 for x in plan_walls(lvl) if x is not w)
                    fx = (f"reverse the swing: {op_line(w, o)} → swing={flip} (other side is clear)"
                          if ok_other and o.kind != "pivot" else
                          f"move {furn_line(f)} out of the swing zone {rr(sp.bounds)} or relocate the door")
                    add("ERROR", cat, f"{lab}: door swing hits furniture {furn_label(f)}",
                        fix=fx, key=f"swing_furn:{o.tag}:{f.kind}")
            obs = stair_obstacles(lvl)
            if obs is not None and o.kind != "pivot" and sp.intersection(obs).area > 0.01:
                add("ERROR", cat, f"{lab}: door swings over the stair flight / void")
        # --- approach on both sides (doors / passages / sliding doors)
        if o.kind in ("door", "pivot", "mamad_door", "passage", "slide") and o.sill <= 0.05:
            obs = stair_obstacles(lvl)
            wide = o.kind in ("slide", "passage") and W > 1.2
            need_w = 0.90 if o.kind == "slide" else 0.80
            for s in (1, -1):
                if o.kind in ("door", "mamad_door") and s == o.swing:
                    continue          # swing side is covered by the swing check
                z = side_zone(w, o, s, R["door_approach"])
                blockers = []
                if obs is not None and z.intersection(obs).area > 0.02:
                    blockers.append(("stair", obs))
                for f in M.FURN:
                    if f.level != lvl or f.kind in LOW_FURN or f.kind in NOT_OBSTACLE:
                        continue
                    if z.intersection(furn_shapes(f)).area > 0.01:
                        blockers.append((f, furn_shapes(f)))
                if not blockers:
                    continue
                if wide:   # a wide slider/passage only needs one clear bay
                    n = max(int(W / 0.05), 1)
                    best = run = 0.0
                    for k in range(n):
                        a0 = o.pos + W * k / n
                        cell = side_zone(w, Opening_like(o, pos=a0, end=a0 + W / n), s, R["door_approach"])
                        if any(cell.intersection(g).area > 0.002 for _, g in blockers):
                            run = 0.0
                        else:
                            run += W / n
                            best = max(best, run)
                    if best >= need_w - 1e-6:
                        continue
                    add("ERROR", cat, f"{lab}: only {best:.2f} m of the opening is clear on the "
                        f"{'N/E' if s > 0 else 'S/W'} side (need one bay ≥ {need_w:.2f}); blocked by "
                        f"{', '.join(furn_label(b) if b != 'stair' else 'stair' for b, _ in blockers)}",
                        key=f"op_block:{o.tag}:{w.c:.2f}:{s}")
                    continue
                for b, g in blockers:
                    if b == "stair":
                        add("ERROR", cat, f"{lab}: the {'N/E' if s > 0 else 'S/W'} side of the opening is blocked by the "
                            f"stair flight / slab void – the door is unusable", key=f"op_stair:{o.tag}:{w.c:.2f}")
                    else:
                        add("ERROR", cat, f"{lab}: furniture {furn_label(b)} blocks the door "
                            f"({'N/E' if s > 0 else 'S/W'} side, within {cm(R['door_approach'])})",
                            fix=f"move {furn_line(b)} clear of {rr(z.bounds)}", key=f"op_block:{o.tag}:{b.kind}")
    # --- overlapping openings on the same wall
    for lst in by_wall.values():
        lst = sorted(lst, key=lambda p: p[1].pos)
        for (w, a), (_, b) in zip(lst, lst[1:]):
            if b.pos < a.end - 0.005:
                fz = floor_z(w.level)
                if z_overlap(a.sill, a.head, b.sill, b.head):
                    add("ERROR", cat, f"Openings overlap on {wid(w)}: {op_label(w, a)} & {op_label(w, b)}")
    # --- swing vs swing
    for i, (l1, p1, w1, o1) in enumerate(swings):
        for (l2, p2, w2, o2) in swings[i + 1:]:
            if l1 == l2 and p1.intersection(p2).area > 0.01:
                add("WARN", cat, f"Door swings clash: {op_label(w1, o1)} & {op_label(w2, o2)}")
    # --- windows: fall protection
    for w, o in OPS:
        if w.kind != "ext" or w.level not in ("U", "R"):
            continue
        if o.kind not in ("window", "slide", "fixed", "open"):
            continue
        outside = (side_point(w, o, w.out, 0.6) if w.out else None)
        out_room = room_at(w.level, *outside) if outside else None
        if out_room is not None and out_room.outdoor and out_room.level == w.level:
            continue      # opens onto a terrace / loggia at the same level
        has_rail = False
        for rl in M.RAILS:
            seg = sbox(min(rl["x0"], rl["x1"]) - 0.05, min(rl["y0"], rl["y1"]) - 0.05,
                       max(rl["x0"], rl["x1"]) + 0.05, max(rl["y0"], rl["y1"]) + 0.05)
            if seg.distance(op_rect(w, o)) < 0.6 and abs(rl["z0"] - floor_z(w.level)) < 0.3:
                has_rail = True
        if o.sill < R["win_sill_guard"] - 0.005 and not has_rail:
            if o.kind == "fixed":
                add("INFO", cat, f"{op_label(w, o)}: fixed glazing below 0.90 on an upper floor – specify laminated "
                    "safety glass designed as barrier (ת\"י 1099) or an inner rail")
                continue
            sev = "WARN" if o.kind == "window" else "ERROR"
            add(sev, cat, f"{op_label(w, o)}: sill {o.sill:.2f} < {R['win_sill_guard']:.2f} on an upper floor with a "
                "drop outside – needs guarding (fixed laminated lower pane or 1.05 m balustrade)",
                fix=(f"add to RAILS: dict(x0={(w.c - 0.10 * w.out) if not w.horiz else o.pos:.2f}, "
                     f"y0={o.pos if not w.horiz else (w.c - 0.10 * w.out):.2f}, "
                     f"x1={(w.c - 0.10 * w.out) if not w.horiz else o.end:.2f}, "
                     f"y1={o.end if not w.horiz else (w.c - 0.10 * w.out):.2f}, z0=LV[\"{w.level}\"], h=1.05, "
                     f"kind=\"glass\")  (inner French balcony) – or raise sill to 0.90 / note fixed laminated "
                     f"pane to 1.05"), key=f"win_guard:{o.tag}")


class Opening_like:
    def __init__(self, o, **kw):
        self.__dict__.update(o.__dict__)
        self.__dict__.update(kw)


# =========================================================================== #
#  3. ROOMS
# =========================================================================== #
def wall_trim_fix(r, walls_u):
    """Room polygon minus walls → proposed rects (cm-rounded), slivers < 15 cm removed."""
    p = room_poly(r).difference(walls_u)
    p = p.buffer(-0.08, join_style=2).buffer(0.08, join_style=2)
    rects = []
    for g in getattr(p, "geoms", [p]):
        if g.is_empty or g.area < 0.3:
            continue
        rects += [tuple(round(v, 2) for v in q) for q in decompose(g) if (q[2] - q[0]) * (q[3] - q[1]) > 0.05]
    rects.sort(key=lambda q: -(q[2] - q[0]) * (q[3] - q[1]))
    return "rects=[" + ", ".join(rr(q) for q in rects) + "]"


def check_rooms():
    cat = "3 Rooms"
    for lvl in LEVELS:
        rs = rooms_on(lvl)
        ws = plan_walls(lvl)
        shaft = []
        if any(w.kind == "shaft" for w in ws):
            shaft = [sbox(M.LIFT["x0"], M.LIFT["y0"], M.LIFT["x1"], M.LIFT["y1"])]
        wu = unary_union([wall_fp(w) for w in ws] + shaft)
        cu = unary_union([col_fp(c) for c in cols_on(lvl)]) if lvl != "R" else Point(-99, -99).buffer(0.01)
        for r in rs:
            p = room_poly(r)
            net = p.area
            if not r.outdoor:
                inter = p.intersection(wu)
                bad = [g for g in getattr(inter, "geoms", [inter]) if not g.is_empty and min_dim(g) > R["tol_room_wall"]]
                if bad:
                    tot = sum(g.area for g in bad)
                    add("ERROR", cat, f"{room_label(r)} ({lvl}) overlaps walls{'/lift shaft' if shaft else ''} by "
                        f"{tot:.2f} m² (max depth {cm(max(min_dim(g) for g in bad))})",
                        fix=f"{room_label(r)}: {wall_trim_fix(r, wu)}", key=f"room_wall:{r.no}")
                net = p.difference(wu).difference(cu).area
                ci = p.intersection(cu)
                for g in getattr(ci, "geoms", [ci]):
                    if not g.is_empty and min_dim(g) > R["tol_room_wall"]:
                        add("WARN" if min_dim(g) >= 0.10 else "INFO", cat,
                            f"Column protrudes {cm(min_dim(g))} into {room_label(r)} ({lvl}) at {rr(g.bounds)} – show "
                            "it in plan / box it into the wall or align the column with the wall faces",
                            key=f"room_col:{r.no}:{g.bounds[0]:.2f}")
            # bedrooms
            if is_bedroom(r) and not r.outdoor:
                biggest = max(r.rects, key=lambda q: (q[2] - q[0]) * (q[3] - q[1]))
                w_ = min(biggest[2] - biggest[0], biggest[3] - biggest[1])
                if net < R["bed_min_area"] - 0.005:
                    add("ERROR", cat, f"{room_label(r)}: bedroom net area {net:.2f} m² < {R['bed_min_area']}")
                if w_ < R["bed_min_w"] - 0.005:
                    add("ERROR", cat, f"{room_label(r)}: bedroom width {w_:.2f} < {R['bed_min_w']}")
            if is_wc(r) and min_dim(p) < 0.80:
                add("ERROR", cat, f"{room_label(r)}: WC narrower than 0.80 m")
            if is_wet(r) and "רחצה" in r.name and (net < 2.5 or min_dim(p) < 1.2):
                add("WARN", cat, f"{room_label(r)}: small bathroom ({net:.2f} m², min dim {min_dim(p):.2f})")
            SECTIONS.setdefault("rooms", []).append((lvl, r.no, r.name, net, min_dim(p), r.ceil, r.service, r.outdoor))
        # room/room overlap
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                ia = room_poly(a).intersection(room_poly(b)).area
                if ia > 0.01:
                    add("ERROR", cat, f"Rooms overlap {ia:.2f} m²: {room_label(a)} & {room_label(b)} ({lvl})")
        # unassigned floor area
        ip = interior_poly(lvl)
        if ip is not None:
            rest = ip.difference(wu).difference(unary_union([room_poly(r) for r in rs] or [Point(0, 0).buffer(0)]))
            hole = None
            if lvl in ("B", "G", "U"):
                hole = None
            rest = rest.buffer(-0.08, join_style=2).buffer(0.08, join_style=2)
            for g in getattr(rest, "geoms", [rest]):
                if g.is_empty or g.area < 0.25 or min_dim(g) < 0.20:
                    continue
                adj = max(rs, key=lambda r: room_poly(r).intersection(g.buffer(0.2, join_style=2)).area, default=None)
                pieces = [rr(tuple(round(v, 2) for v in q)) for q in decompose(g)]
                add("WARN", cat, f"Floor area {g.area:.2f} m² at {rr(g.bounds)} on level {lvl} belongs to no room",
                    fix=(f"add {', '.join(pieces)} to the rects of {room_label(adj)}" if adj else "define the space"),
                    key=f"room_gap:{lvl}:{g.bounds[0]:.1f}:{g.bounds[1]:.1f}")
    # ממ"ד
    for r in M.ROOMS:
        if 'ממ"ד' not in r.name:
            continue
        p = room_poly(r)
        net = p.area
        if net < R["mamad_min_area"]:
            add("ERROR", cat, f'{room_label(r)}: ממ"ד net {net:.2f} m² < 9')
        if net > R["mamad_service_max"]:
            add("WARN", cat, f'{room_label(r)}: ממ"ד net {net:.2f} m² > {R["mamad_service_max"]} m² – the excess is usually '
                "counted as MAIN area (only the standard ממ\"ד area is service) – verify takanon / area sheet",
                key="mamad_big")
        # surrounding walls
        bnd = p.buffer(0.35, join_style=2).difference(p.buffer(0.005, join_style=2))
        sides = {"W": sbox(p.bounds[0] - 0.4, p.bounds[1], p.bounds[0], p.bounds[3]),
                 "E": sbox(p.bounds[2], p.bounds[1], p.bounds[2] + 0.4, p.bounds[3]),
                 "S": sbox(p.bounds[0], p.bounds[1] - 0.4, p.bounds[2], p.bounds[1]),
                 "N": sbox(p.bounds[0], p.bounds[3], p.bounds[2], p.bounds[3] + 0.4)}
        for sname, sz in sides.items():
            cand = [w for w in plan_walls(r.level) if wall_fp(w).intersection(sz).area > 0.05]
            if not cand:
                add("ERROR", cat, f'ממ"ד {sname} side has no wall')
                continue
            rc = [w for w in cand if (w.core == "rc" or w.kind in ("mamad", "rc", "shaft")) and w.t >= R["mamad_wall_min"] - 1e-6]
            # RC thickness = sum of RC layers stacked on that side
            rc_t = sum(w.t for w in cand if w.kind in ("mamad", "rc"))
            rc_t += sum(0.20 for w in cand if w.kind == "ext" and w.core == "rc")
            if rc_t < R["mamad_wall_min"] - 1e-6:
                desc = ", ".join(wid(w) for w in cand)
                add("ERROR", cat, f'ממ"ד {sname} wall is not RC ≥ 25 cm (found: {desc}; RC thickness {cm(rc_t)})',
                    key=f"mamad_wall:{sname}")
        for w, o in OPS:
            if w.level != r.level:
                continue
            if o.kind == "mamad_win":
                if o.end - o.pos > R["mamad_win_max"][0] + 0.005 or o.head - o.sill > R["mamad_win_max"][1] + 0.005:
                    add("ERROR", cat, f'{op_label(w, o)}: ממ"ד window larger than 100/100')
            if o.kind == "mamad_door":
                if o.swing == 0:
                    pass
                inside = room_at(w.level, *side_point(w, o, o.swing))
                if inside is r:
                    add("ERROR", cat, f'{op_label(w, o)}: ממ"ד blast door must open OUTWARD (away from the ממ"ד)')
        # other openings into the ממ"ד (only the blast door & blast window are allowed)
        for w, o in OPS:
            if w.level != r.level or o.kind in ("mamad_door", "mamad_win"):
                continue
            if any(room_at(w.level, *side_point(w, o, s)) is r for s in (1, -1)):
                add("ERROR", cat, f'{op_label(w, o)}: ordinary opening into the ממ"ד')


# =========================================================================== #
#  4. STAIRS & VERTICAL CONSISTENCY
# =========================================================================== #
def check_stairs():
    cat = "4 Stairs & vertical"
    rows = []
    xs = set()
    for s in M.STAIRS:
        lvl = s["level"]
        n = s["nA"] + s["nB"]
        r = s["r"]
        t = s["t"]
        f2 = 2 * r + t
        ftf = s["z1"] - s["z0"]
        rows.append((lvl, n, r, t, f2, s["nA"], s["nB"]))
        if not (R["stair_2rt"][0] - 1e-6 <= f2 <= R["stair_2rt"][1] + 1e-6):
            add("ERROR", cat, f"Stair {lvl}: 2R+T = {f2 * 100:.1f} cm outside 61–63")
        if r > R["riser_max"] + 1e-6:
            add("ERROR", cat, f"Stair {lvl}: riser {r * 100:.2f} cm > 17.5")
        if t < R["tread_min"] - 1e-6:
            add("ERROR", cat, f"Stair {lvl}: tread {t * 100:.1f} cm < 26")
        if abs(n * r - ftf) > 0.001:
            add("ERROR", cat, f"Stair {lvl}: {n}×{r:.4f} ≠ floor-to-floor {ftf:.2f}")
        if len(s["treadsA"]) != s["nA"] - 1 or len(s["treadsB"]) != s["nB"] - 1:
            add("ERROR", cat, f"Stair {lvl}: tread count does not match riser count")
        if M.ST["w"] < R["stair_w_min"]:
            add("ERROR", cat, f"Stair {lvl}: flight width {M.ST['w']:.2f} < 1.00")
        lx0, ly0, lx1, ly1, lz = s["landing"]
        if ly1 - ly0 < M.ST["w"] - 1e-6:
            add("ERROR", cat, f"Stair {lvl}: landing depth {ly1 - ly0:.2f} < flight width {M.ST['w']:.2f}")
        xs.add((round(s["flightA"][0], 3), round(s["flightA"][2], 3), round(s["flightB"][0], 3), round(s["flightB"][2], 3)))
        # flights fit in their plan space (ends of flight A/B)
        if s["nA"] != s["nB"]:
            add("INFO", cat, f"Stair {lvl}: unequal flights {s['nA']}/{s['nB']} risers – flight A starts at "
                f"y={s['yA0']:.2f} while flight B ends at y={s['yB_end']:.2f}; draw the offset in plan")
        # step arrival/departure area (≥ flight width in front of first & last riser)
        for which, (x0, x1, yedge, dirn) in (("bottom of flight A", (s["flightA"][0], s["flightA"][2], s["yA0"], -1)),
                                             ("top of flight B", (s["flightB"][0], s["flightB"][2], s["yB_end"], -1))):
            flvl = lvl if which.startswith("bottom") else NEXT[lvl]
            zone = sbox(x0, yedge - M.ST["w"], x1, yedge)
            ws = plan_walls(flvl)
            blk = [w for w in ws if wall_fp(w).intersection(zone).area > 0.005]
            if blk:
                free = min(yedge - wall_fp(w).bounds[3] for w in blk)
                fix = None
                if flvl == "B":
                    fix = ("open the stair foot to the lounge: "
                           "wall(\"B\", 13.12, 27.58, 19.06, 27.58) → wall(\"B\", 15.60, 27.58, 19.06, 27.58); "
                           "op(\"B\", H, 27.58, 15.70, 17.40, 0, 2.30, \"passage\") → op(\"B\", H, 27.58, 15.80, "
                           "17.40, 0, 2.30, \"passage\"); room B10 rects → [(13.12, 27.64, 15.55, 31.70), "
                           "(15.65, 27.64, 19.00, 29.58)]")
                elif flvl == "R":
                    fix = ("enlarge the roof-exit room southwards: RX_OUT = [(12.90, 26.50), (17.80, 26.50), "
                           "(17.80, Y_N), (12.90, Y_N)] (landing 1.18 m), update op D-31 c=26.65, "
                           "R1 rects → [(13.20, 26.80, 17.50, 31.70)], RX roof slab y0 → 26.60; "
                           "wall(\"R\", 15.6, 27.30, …) → start at 26.80")
                add("ERROR", cat, f"Stair {lvl}: only {cm(max(free, 0))} free in front of the {which} at level "
                    f"{flvl} (need ≥ {M.ST['w']:.2f} landing) – blocked by {wid(blk[0])}",
                    fix=fix, key=f"stair_landing:{lvl}:{which}")
    if len(xs) > 1:
        add("ERROR", cat, f"Stair flights not stacked identically on all storeys: {xs}")
    SECTIONS["stairs"] = rows
    # --- lift shaft identical
    shafts = defaultdict(list)
    for w in M.WALLS:
        if w.kind == "shaft":
            shafts[w.level].append((round(w.c, 3), round(w.a0, 3), round(w.a1, 3), w.horiz))
    ref = sorted(shafts.get("G", []))
    for lvl, lst in shafts.items():
        lst = sorted(lst)
        if lvl != "R" and lst != ref:
            add("ERROR", cat, f"Lift shaft walls on {lvl} differ from GF")
        if lvl == "R" and not set(lst) <= set(ref):
            add("ERROR", cat, "Lift shaft walls at roof level not aligned with the shaft below")
    if shafts:
        # door gap of the lift
        hz = sorted([s for s in ref if s[3]], key=lambda s: s[1])
        if len(hz) >= 2:
            gap = hz[1][1] - hz[0][2]
            if gap < 0.80 - 1e-6:
                add("ERROR", cat, f"Lift landing door opening only {gap:.2f} m (home lift needs ≥ 0.80, 0.90 preferred)",
                    fix="for every level: wall(lvl, LIFT['x0'], LIFT['y0']+0.10, 16.30, …) → …, 16.05, …  and  "
                        "wall(lvl, 16.90, LIFT['y0']+0.10, LIFT['x1'], …) → wall(lvl, 16.95, …) "
                        "(clear 0.90, also the 'R' copies)", key="lift_door")
        inner_w = (M.LIFT["x1"] - 0.20) - (M.LIFT["x0"] + 0.20)
        inner_d = 31.70 - (M.LIFT["y0"] + 0.20)
        add("INFO", cat, f"Lift shaft internal {inner_w:.2f}×{inner_d:.2f} m – OK for a home lift cabin ≈1.00×1.25; "
            "check pit depth below B (−3.50) and overrun above R")
        rx = [s for s in M.SLABS if s.kind == "roof" and s.top > M.LV["R"]]
        if rx:
            ov = rx[0].top - rx[0].t - M.LV["R"]
            if ov < 2.60:
                add("WARN", cat, f"Lift overrun above the top stop (R +{M.LV['R']:.2f}) is only {ov:.2f} m to the "
                    "roof-exit slab soffit – most home lifts need 2.60–3.40 m (low-headroom models ≈2.50)",
                    fix="confirm the lift model, or raise the lift-shaft roof locally (LV['RX'] → 10.20 over the shaft only)")
    # --- slab holes vs stairs + headroom
    check_headroom(cat)
    # --- void edges guarding, stair side gaps, lift shaft closure
    check_void_edges(cat)
    check_stair_sides(cat)
    check_lift_shaft(cat)


def stair_soffits():
    """list of (rect, underside_z) for every stair element and slab."""
    out = []
    for s in M.STAIRS:
        for (x0, y0, x1, y1, z) in s["treadsA"] + s["treadsB"]:
            out.append((sbox(x0, y0, x1, y1), z - 0.25, f"stair {s['level']} tread"))
        x0, y0, x1, y1, z = s["landing"]
        out.append((sbox(x0, y0, x1, y1), z - 0.25, f"stair {s['level']} landing"))
    for sl in M.SLABS:
        if sl.kind in ("deck", "raft", "canopy"):
            continue
        p = unary_union([sbox(*q) for q in sl.rects])
        if sl.holes:
            p = p.difference(unary_union([sbox(*h) for h in sl.holes]))
        out.append((p, sl.top - sl.t, f"slab top {sl.top:+.2f}"))
    return out


def check_headroom(cat):
    soff = stair_soffits()
    rows = []
    for s in M.STAIRS:
        worst = (9, None)
        items = [("A", i, q) for i, q in enumerate(s["treadsA"])] + [("L", 0, s["landing"])] + \
                [("B", i, q) for i, q in enumerate(s["treadsB"])]
        # include the floor at the foot & top
        for fl, i, (x0, y0, x1, y1, z) in items:
            fp = sbox(x0, y0, x1, y1)
            # nosing strip (front 5 cm) – headroom measured vertically from the nosing line
            hmin = 99
            src = ""
            for (p, uz, lab) in soff:
                if uz <= z + 0.01:
                    continue
                if p.intersection(fp).area > 0.002:
                    if uz - z < hmin:
                        hmin, src = uz - z, lab
            rows.append((s["level"], fl, i, z, hmin, src))
            if hmin < worst[0]:
                worst = (hmin, (fl, i, z, src))
        hmin, info = worst
        sev = "ERROR" if hmin < R["headroom_min"] else ("WARN" if hmin < R["headroom_target"] else "INFO")
        fl, i, z, src = info
        add(sev, cat, f"Stair {s['level']} headroom: minimum {hmin:.2f} m (flight {fl} step {i + 1}, z={z:+.2f}, "
            f"under {src}) – required ≥ {R['headroom_min']:.2f}, target {R['headroom_target']:.2f}")
    SECTIONS["headroom"] = rows
    # the slab hole must not be smaller than the stair below in the zone where headroom would fail
    for s in M.STAIRS:
        nxt = NEXT[s["level"]]
        sl = [q for q in M.SLABS if abs(q.top + M.FIN - M.LV[nxt]) < 0.02 and q.kind in ("slab", "roof")]
        if not sl:
            continue
        holes = unary_union([sbox(*h) for h in sl[0].holes]) if sl[0].holes else None
        if holes is None:
            add("ERROR", cat, f"No slab hole above stair {s['level']}")
            continue
        fl = unary_union([sbox(*s["flightA"]), sbox(*s["flightB"]), sbox(*s["landing"][:4])])
        uncovered = fl.difference(holes)
        if uncovered.area > 0.01:
            add("INFO", cat, f"Stair {s['level']}: {uncovered.area:.2f} m² of the stair plan lies under the solid slab "
                f"at {nxt} (bounds {rr(uncovered.bounds)}) – headroom checked above")


def _runs(samples, key):
    """group consecutive samples with the same class"""
    out, cur = [], None
    for p in samples:
        k = key(p)
        if cur and cur[0] == k:
            cur[1].append(p)
        else:
            cur = [k, [p]]
            out.append(cur)
    return out


def check_void_edges(cat):
    """Slab-hole edges at each floor must be closed by a wall, a ≥0.85 rail, or the stair itself
    (departing first tread / arriving last tread / central spine).  Gaps ≤10 cm to a wall are OK."""
    cat = "5 Guards & railings"
    rails = M.RAILS
    lift = sbox(M.LIFT["x0"], M.LIFT["y0"], M.LIFT["x1"], M.LIFT["y1"])
    for sl in M.SLABS:
        if not sl.holes or sl.kind not in ("slab", "roof"):
            continue
        lvl = None
        for k in ("G", "U", "R"):
            if abs(sl.top + M.FIN - M.LV[k]) < 0.02:
                lvl = k
        if not lvl:
            continue
        fz = M.LV[lvl]
        ws = [w for w in M.WALLS if w.level == lvl and z_overlap(w.z0, w.z1, fz + 0.2, fz + 1.0)]
        wfp = unary_union([wall_fp(w) for w in ws])
        rfp = unary_union([sbox(min(r["x0"], r["x1"]) - 0.12, min(r["y0"], r["y1"]) - 0.12,
                                max(r["x0"], r["x1"]) + 0.12, max(r["y0"], r["y1"]) + 0.12)
                           for r in rails if abs(r["z0"] - fz) < 0.3 and r["h"] >= 0.85] or [Point(-99, -99)])
        conn = []
        for s in M.STAIRS:
            if s["level"] == lvl and s["treadsA"]:
                x0, y0, x1, y1, z = s["treadsA"][0]
                conn.append(sbox(x0, y0 - 0.15, x1, y1 + 0.15))
                conn.append(sbox(s["flightA"][2] - 0.01, s["yA0"] - 0.05, s["flightB"][0] + 0.01, M.ST["yl"]))
            if NEXT.get(s["level"]) == lvl and s["treadsB"]:
                x0, y0, x1, y1, z = s["treadsB"][-1]
                conn.append(sbox(x0, y0 - 0.15, x1, y1 + 0.15))
                conn.append(sbox(s["flightA"][2] - 0.01, s["yB_end"] - 0.05, s["flightB"][0] + 0.01, M.ST["yl"]))
        cfp = unary_union(conn) if conn else Point(-99, -99)
        for h in sl.holes:
            hb = sbox(*h)
            if hb.intersection(lift).area > 0.5 * hb.area:
                continue          # lift hole – checked with the shaft walls
            x0, y0, x1, y1 = h
            edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
            for (ax, ay), (bx, by) in edges:
                L = math.hypot(bx - ax, by - ay)
                n = max(int(L / 0.1), 1)
                smp = []
                for k in range(n + 1):
                    px, py = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
                    p = Point(px, py)
                    d = p.distance(wfp)
                    if d <= 0.10 or rfp.contains(p) or cfp.contains(p):
                        cls = "ok"
                    elif d <= 0.35:
                        cls = "gap"
                    else:
                        cls = "open"
                    smp.append((px, py, cls, d))
                vert = abs(ax - bx) < 1e-6
                for cls, pts in _runs(smp, key=lambda q: q[2]):
                    if cls == "ok" or len(pts) < 3:
                        continue
                    seg = (min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts))
                    ln = max(seg[2] - seg[0], seg[3] - seg[1])
                    where = f"{'x' if vert else 'y'}={ax if vert else ay:.2f} {rr(seg)}"
                    if cls == "gap":
                        g = max(q[3] for q in pts)
                        add("WARN", cat, f"Level {lvl}: {cm(g)} fall-through gap between the stair void edge and the "
                            f"wall over {ln:.2f} m at {where} (max 10 cm)",
                            fix="close it: widen the slab edge / add a 10 cm upstand or glass strip, e.g. continue the "
                                "10 cm screen wall x=15.60 (as in B/R) or shift the wall to the stair",
                            key=f"void_gap:{lvl}:{seg[0]:.2f}:{seg[1]:.2f}")
                    else:
                        xx0, yy0, xx1, yy1 = seg
                        if vert:
                            xx0 = xx1 = xx0 + (0.05 if xx0 >= x1 - 1e-6 else -0.05)
                        else:
                            yy0 = yy1 = yy0 + (0.05 if yy0 >= y1 - 1e-6 else -0.05)
                        add("ERROR", cat, f"Unguarded slab-void edge at level {lvl}: {ln:.2f} m at {where} – open drop "
                            "into the stair void",
                            fix=(f"add to RAILS: dict(x0={xx0:.2f}, y0={yy0:.2f}, x1={xx1:.2f}, y1={yy1:.2f}, "
                                 f"z0=LV[\"{lvl}\"], h=1.05, kind=\"glass\")  – or a 10 cm wall like the screen x=15.6 in B/R"),
                            key=f"void_edge:{lvl}:{seg[0]:.2f}:{seg[1]:.2f}")


def check_stair_sides(cat):
    """gaps between the stair flights/landing and the enclosing walls (≤ 10 cm)."""
    for s in M.STAIRS:
        lvl = s["level"]
        ws = [w for w in M.WALLS if w.level in (lvl,) and w.kind != "parapet" and not w.horiz]
        found = defaultdict(list)
        parts = [("flight A", s["flightA"], s["z0"] + 1.0), ("landing", s["landing"][:4], s["zl"]),
                 ("flight B", s["flightB"], s["zl"] + 1.0)]
        for name, (x0, y0, x1, y1), z in parts:
            for side, xe in (("W", x0), ("E", x1)):
                if name == "flight A" and side == "E" or name == "flight B" and side == "W":
                    continue    # spine side
                n = max(int((y1 - y0) / 0.1), 1)
                for k in range(n + 1):
                    y = y0 + (y1 - y0) * k / n
                    best = 9
                    for w in ws:
                        if not (w.a0 - 0.01 <= y <= w.a1 + 0.01):
                            continue
                        face = w.c + w.t / 2 if side == "W" else w.c - w.t / 2
                        g = (xe - face) if side == "W" else (face - xe)
                        if -0.01 <= g < best:
                            best = g
                    found[(name, side)].append((y, best))
        for (name, side), smp in found.items():
            bad = [(y, g) for y, g in smp if 0.10 < g <= 0.60]
            if len(bad) >= 3:
                g = max(b[1] for b in bad)
                add("WARN", "5 Guards & railings", f"Stair {lvl} {name}: {cm(g)} gap on the {side} side between the "
                    f"stair and the wall over y {min(b[0] for b in bad):.2f}–{max(b[0] for b in bad):.2f} "
                    "(child fall-through, max 10 cm)",
                    fix="fill with a stringer/upstand or glass, or bring the wall to the stair (see void-gap fix)",
                    key=f"stair_gap:{lvl}:{name}:{side}")


def check_lift_shaft(cat):
    lx0, ly0, lx1, ly1 = M.LIFT["x0"], M.LIFT["y0"], M.LIFT["x1"], M.LIFT["y1"]
    sides = {"W": sbox(lx0, ly0, lx0 + 0.2, ly1), "E": sbox(lx1 - 0.2, ly0, lx1, ly1),
             "S": sbox(lx0, ly0, lx1, ly0 + 0.2), "N": sbox(lx0, ly1, lx1, ly1 + 0.15)}
    for lvl in LEVELS:
        ws = [w for w in M.WALLS if w.level == lvl and w.kind != "parapet"]
        if not any(w.kind == "shaft" for w in ws):
            continue
        for k, zone in sides.items():
            cov = sum(wall_fp(w).intersection(zone).area for w in ws)
            if cov < 0.55 * zone.area * (0.6 if k == "S" else 1.0):
                fix = None
                if k == "E":
                    fix = (f'add wall("{lvl}", LIFT["x1"] - 0.10, LIFT["y0"], LIFT["x1"] - 0.10, 31.70, t=0.20, '
                           f'kind="shaft", core="rc"{", z=rxz" if lvl == "R" else ""})')
                add("ERROR", "4 Stairs & vertical", f"Lift shaft at level {lvl} is open on its {k} side "
                    f"({cov / zone.area * 100:.0f} % closed)", fix=fix, key=f"lift_open:{lvl}:{k}")


# =========================================================================== #
#  5. CEILING HEIGHTS, SUPPORT
# =========================================================================== #
def check_heights():
    cat = "6 Clear heights"
    for lvl in ("B", "G", "U"):
        nxt = NEXT[lvl]
        clear = M.slab_bot(nxt) - M.LV[lvl]
        for r in rooms_on(lvl):
            if r.outdoor:
                continue
            need = R["clear_hab"] if is_habitable(r) else R["clear_service"]
            if clear - 0.02 < need:
                add("ERROR", cat, f"{room_label(r)} ({lvl}): structural clear {clear:.2f} m (−2 cm plaster) < {need}")
            if r.ceil > clear + 1e-6:
                add("ERROR", cat, f"{room_label(r)}: ceiling {r.ceil:.2f} above slab soffit (clear {clear:.2f})",
                    fix=f"ceil ≤ {clear - 0.10:.2f}")
            elif is_habitable(r) and r.ceil < need:
                add("ERROR", cat, f"{room_label(r)}: suspended ceiling {r.ceil:.2f} < {need}")
            elif r.ceil < 2.05:
                add("ERROR", cat, f"{room_label(r)}: ceiling {r.ceil:.2f} < 2.05")
            elif clear - r.ceil < R["ceil_plenum_min"] - 1e-6:
                add("WARN", cat, f"{room_label(r)} ({lvl}): ceiling {r.ceil:.2f} = slab soffit {clear:.2f} → no plenum "
                    "for AC ducts / downlights", fix=f"{room_label(r)}: ceil={min(clear - 0.25, 2.80):.2f} "
                    "(or note exposed fair-faced slab + split units)", key=f"plenum:{r.no}")
        add("INFO", cat, f"Level {lvl}: floor-to-floor {M.LV[nxt] - M.LV[lvl]:.2f}, slab {M.SLAB:.2f} + finish "
            f"{M.FIN:.2f} → structural clear {clear:.2f} m")
    # roof exit
    rx = [s for s in M.SLABS if s.kind == "roof" and s.top > M.LV["R"] + 1]
    if rx:
        clear = rx[0].top - rx[0].t - M.LV["R"]
        sev = "INFO" if clear >= R["clear_service"] else "WARN"
        add(sev, cat, f"Roof exit room clear height {clear:.2f} m (service, ≥ {R['clear_service']})")


def check_support():
    cat = "7 Load paths"
    pairs = (("U", "G"), ("R", "U"), ("G", "B"))
    cantilever = (M.Y_S_U, M.Y_S_G)
    for up, lo in pairs:
        lows = [w for w in M.WALLS if w.level == lo and w.kind not in ("parapet", "glass") and not is_site_wall(w)]
        lowfp = unary_union([wall_fp(w).buffer(0.08) for w in lows])
        cols = unary_union([col_fp(c).buffer(0.10) for c in M.COLS
                            if z_overlap(c.z0, c.z1, M.LV[lo], M.LV[lo] + 2.0)] or [Point(-99, -99)])
        sup = lowfp.union(cols)
        for w in M.WALLS:
            if w.level != up or w.kind in ("parapet",) or is_site_wall(w):
                continue
            L = w.a1 - w.a0
            n = max(int(L / 0.05), 1)
            runs, cur = [], None
            for k in range(n + 1):
                a = w.a0 + L * k / n
                p = Point(a, w.c) if w.horiz else Point(w.c, a)
                ok = sup.contains(p)
                if not ok:
                    cur = [a, a] if cur is None else [cur[0], a]
                elif cur is not None:
                    runs.append(cur)
                    cur = None
            if cur is not None:
                runs.append(cur)
            runs = [r_ for r_ in runs if r_[1] - r_[0] > 0.30]
            if not runs:
                continue
            tot = sum(r_[1] - r_[0] for r_ in runs)
            txt = ", ".join(f"{r_[0]:.2f}→{r_[1]:.2f}" for r_ in runs)
            # documented cantilever wall-beams (UF west bar over the covered terrace)
            loggia = (up == "U" and w.horiz and abs(w.c - (M.Y_S_U + M.T_EXT / 2)) < 0.01)
            if loggia:
                add("INFO", cat, f"{wid(w)} unsupported {txt} – loggia frame hung between the cantilever wall-beams")
                continue
            docr = [r_ for r_ in runs if up == "U" and not w.horiz and w.kind == "ext"
                    and r_[1] <= cantilever[1] + 0.2 and r_[0] <= cantilever[0] + 0.3]
            for r_ in docr:
                add("INFO", cat, f"{wid(w)}: {r_[0]:.2f}→{r_[1]:.2f} is the documented 5 m cantilever wall-beam (RC, "
                    "back-span to the GF columns on y=21.15/25.15 – show in the structural note)")
            runs = [r_ for r_ in runs if r_ not in docr]
            if not runs:
                continue
            heavy = w.kind in ("ext", "mamad", "rc", "shaft", "retain") or w.core == "rc"
            if w.kind == "mamad":
                add("WARN", cat, f"{wid(w)}: {tot:.2f} m without wall/column below on {lo} ({txt})",
                    fix=('the ממ"ד RC walls must continue down to the foundations (Pikud HaOref) or sit on designed '
                         "transfer beams: add GF+B columns under the free ממ\"ד corner, e.g. for z in ((slab_top('G'), "
                         "slab_bot('U')), (slab_top('B'), slab_bot('G'))): COLS.append(Column(11.05, 27.11, 0.30, 0.30, *z)) "
                         "and RC 30/60 downstand beams along x=11.05 and y=27.11 in the U slab (the B column lands in "
                         "the cinema – shift recliner rows ≥ 0.4 m west); note it in the structural legend"),
                    key=f"support:{up}:mamad:{w.c:.2f}")
                continue
            if not heavy:
                if tot > 2.0:
                    add("INFO", cat, f"{wid(w)}: {tot:.2f} m without wall below on {lo} ({txt}) – light partition on "
                        "slab (OK, slab designed for it)")
                continue
            for r_ in runs:
                span = r_[1] - r_[0]
                cant = r_[0] <= w.a0 + 0.06 or r_[1] >= w.a1 - 0.06
                if up == "R" and w.kind != "shaft":
                    add("INFO", cat, f"{wid(w)}: {span:.2f} m on the roof slab without wall below ({r_[0]:.2f}→{r_[1]:.2f}) – "
                        "roof-exit masonry: provide an upstand/downstand beam in the roof slab")
                elif cant:
                    add("WARN", cat, f"{wid(w)}: free (cantilevered) end {span:.2f} m without support below on {lo} "
                        f"({r_[0]:.2f}→{r_[1]:.2f})",
                        fix="add a column under the free end or align the wall with the wall below",
                        key=f"support:{up}:{w.kind}:{w.c:.2f}:{r_[0]:.1f}")
                elif span > 6.0:
                    add("WARN", cat, f"{wid(w)}: spans {span:.2f} m between supports on {lo} ({r_[0]:.2f}→{r_[1]:.2f}) – "
                        "needs a deep wall-beam/downstand beam or an intermediate column",
                        key=f"support:{up}:{w.kind}:{w.c:.2f}:{r_[0]:.1f}")
                else:
                    add("INFO", cat, f"{wid(w)}: wall-beam/lintel spanning {span:.2f} m between supports on {lo} "
                        f"({r_[0]:.2f}→{r_[1]:.2f}) – OK, show the beam")


# =========================================================================== #
#  6. PLANNING: setbacks, coverage, areas
# =========================================================================== #
def check_planning():
    cat = "8 Planning & areas"
    ex0, ey0, ex1, ey1 = M.ENVELOPE
    env = sbox(ex0, ey0, ex1, ey1)
    lot = sbox(M.LOT["x0"], M.LOT["y0"], M.LOT["x1"], M.LOT["y1"])
    lot_a = lot.area
    gp = {l: gross_poly(l) for l in LEVELS}
    for l, p in gp.items():
        if p is None:
            continue
        out = p.difference(env)
        if out.area > 0.01:
            add("ERROR", cat, f"Level {l} outer walls exceed the building envelope by {out.area:.2f} m² {rr(out.bounds)}")
    # projections
    for f in M.FINS:
        if f["axis"] == "y":
            x0, x1 = f["c"] - f["depth"] / 2, f["c"] + f["depth"] / 2
            p = sbox(x0, f["a0"], x1, f["a1"])
            d = max(ex0 - x0, x1 - ex1, 0)
            if d > 0.001:
                side = "rear (W)" if x0 < ex0 else "front (E)"
                sb = M.SETBACK["rear"] if x0 < ex0 else M.SETBACK["front"]
                add("WARN", cat, f"Louvre field at x={f['c']:.2f} projects {cm(d)} beyond the {side} building line "
                    f"(allowed projections are usually ≤ 40 % of the setback = {0.4 * sb:.1f} m, and fins are "
                    "normally permitted – verify takanon)", key=f"fin_proj:{f['c']:.2f}")
    for s in M.SLABS:
        if s.kind == "canopy":
            for q in s.rects:
                d = max(q[2] - ex1, ex0 - q[0], 0)
                if d > 0:
                    lim = R["canopy_proj_max"] * M.SETBACK["front"]
                    sev = "WARN" if d > lim + 1e-6 else "INFO"
                    add(sev, cat, f"Entrance canopy projects {d:.2f} m into the front setback (limit {lim:.2f} m = 40 % "
                        "of 5 m – verify takanon)",
                        fix=("Slab([(X_E - 0.1, 28.40, X_E + 2.20, 31.80)], 3.05, 0.20, \"canopy\") → "
                             "Slab([(X_E - 0.1, 28.40, X_E + 2.00, 31.80)], 3.05, 0.20, \"canopy\")") if d > lim else None,
                        key="canopy")
    for p in M.PERGOLAS:
        if p["x1"] > ex1 + 0.01:
            add("INFO", cat, f"Pergola {p['x0']:.2f}–{p['x1']:.2f} lies in the front setback (carport pergola) – "
                "allowed as light pergola/carport only if the takanon permits; keep ≥50 % open roof")
    # coverage (projection of roofed building parts)
    proj = unary_union([g for g in (gp["G"], gp["U"]) if g is not None])
    cov = proj.area
    add("INFO" if cov <= R["lot_coverage"] * lot_a else "ERROR", cat,
        f"Coverage (GF ∪ UF projection) {cov:.1f} m² = {100 * cov / lot_a:.1f} % (max {100 * R['lot_coverage']:.0f} % = "
        f"{R['lot_coverage'] * lot_a:.0f} m²)")
    # ---------------- area table ----------------
    table = []
    lift = sbox(M.LIFT["x0"], M.LIFT["y0"], M.LIFT["x1"], M.Y_N)
    tot_main = tot_serv = 0.0
    for l in LEVELS:
        g = gp[l]
        if g is None:
            continue
        gross = g.area
        serv = {}
        # stair cage + lift (service) – gross incl. half walls
        sc = stair_cage_poly(l) if l != "R" else None
        if l == "R":
            serv["חדר יציאה לגג (מדרגות+מעלית)"] = gross
        else:
            if sc is not None:
                serv["חדר מדרגות"] = sc.buffer(0.10, join_style=2).intersection(g).difference(lift).area
            if any(w.kind == "shaft" and w.level == l for w in M.WALLS):
                serv["פיר מעלית"] = lift.intersection(g).area
        balcony = 0.0
        for r in rooms_on(l):
            rp = room_poly(r)
            if r.outdoor:
                if g.contains(rp.buffer(-0.05)):
                    balcony += rp.buffer(0.10, join_style=2).intersection(g).area
                continue
            if 'ממ"ד' in r.name:
                serv['ממ"ד'] = rp.buffer(0.30, join_style=2).intersection(g).area
            elif r.service and l != "R":
                serv[r.name] = serv.get(r.name, 0) + rp.buffer(0.08, join_style=2).intersection(g).area
        s_tot = sum(serv.values())
        main = gross - s_tot - balcony
        table.append((l, gross, serv, balcony, main))
        if l in ("G", "U"):
            tot_main += main
            tot_serv += s_tot
        elif l == "R":
            tot_serv += s_tot
    SECTIONS["areas"] = table
    lim_main = R["main_pct"] * lot_a
    lim_serv = R["service_pct"] * lot_a
    add("INFO" if tot_main <= lim_main else "ERROR", cat,
        f"Main area GF+UF = {tot_main:.1f} m² (max {lim_main:.0f} m² = 35 %) → reserve {lim_main - tot_main:.1f} m²")
    add("INFO" if tot_serv <= lim_serv else "ERROR", cat,
        f"Service area above ground (stairs, lift, ממ\"ד, laundry, roof exit) = {tot_serv:.1f} m² "
        f"(max {lim_serv:.0f} m² = 16 %)")
    b = [t for t in table if t[0] == "B"]
    if b:
        add("INFO", cat, f"Basement gross {b[0][1]:.1f} m² (within the outline of the floor above – counted separately)")
    # basement habitable use
    for r in rooms_on("B"):
        if is_bedroom(r):
            add("WARN", cat, f"{room_label(r)}: bedroom in the basement – many takanot allow basement for service / "
                "recreation only (no dwelling); verify takanon 303-0207092, and keep the patio opening for light & "
                "escape", key="basement_bedroom")
    # roof structures
    rxp = gp.get("R")
    if rxp is not None:
        a = rxp.area
        if a > R["roof_room_max"]:
            add("WARN", cat, f"Roof exit room gross {a:.1f} m² > {R['roof_room_max']} m² typical limit for a roof "
                "exit structure (verify takanon)", fix="trim RX_OUT west edge 12.90 → 13.00 and east 17.80 → 17.70 "
                "only if the takanon limit is 23 m²; otherwise record it as stair+lift service area",
                key="roofroom_area")
        ufp = gp.get("U")
        if ufp is not None:
            bx = rxp.bounds
            ub = ufp.bounds
            dists = dict(N=ub[3] - bx[3], E=ub[2] - bx[2], W=bx[0] - ub[0], S=bx[1] - ub[1])
            flush = [k for k, v in dists.items() if v < R["roof_room_setback"] - 1e-6]
            if flush:
                add("WARN", cat, f"Roof exit room is flush with / closer than {R['roof_room_setback']} m to the "
                    f"façade on side(s) {', '.join(flush)} (distances {', '.join(f'{k}={v:.2f}' for k, v in dists.items())}) – "
                    "many takanot require roof structures to be set back from the façade; it also reads as a 3rd "
                    "storey on the north elevation", key="roofroom_setback")
        top = max(w.skin_z[1] for w in M.WALLS if w.level == "R" and w.kind == "ext" and w.skin_z)
        add("INFO", cat, f"Heights: main roof parapet +{M.LV['R'] + 0.50:.2f}; roof-exit top +{top:.2f} "
            f"(= {top - M.STREET:.2f} m above the sidewalk, {M.PROJECT['abs_zero'] + top:.2f} abs.)")


# =========================================================================== #
#  7. SITE: pool, rails, parking, entrance
# =========================================================================== #
def guard_ref_level(z0):
    cands = [M.GARDEN, -0.02, M.LV["U"], M.LV["R"]]
    return max(c for c in cands if c <= z0 + 0.001)


def check_site():
    cat = "9 Site, pool, parking"
    P = M.POOL
    area = (P["x1"] - P["x0"]) * (P["y1"] - P["y0"])
    if area > R["pool_water_max"]:
        add("ERROR", cat, f"Pool water area {area:.1f} m² > 60")
    if P["depth"] > R["pool_depth_max"]:
        add("ERROR", cat, f"Pool depth {P['depth']:.2f} > 1.80")
    d = min(P["x0"] - M.LOT["x0"], P["y0"] - M.LOT["y0"], M.LOT["x1"] - P["x1"], M.LOT["y1"] - P["y1"])
    add("INFO" if d >= R["pool_boundary_min"] else "ERROR", cat,
        f"Pool {area:.1f} m² water, depth {P['depth']:.2f}, min distance to boundary {d:.2f} m (rule ≥ "
        f"{R['pool_boundary_min']:.1f})")
    add("INFO", cat, "Pool: show the pool-machinery pit/room (not modelled) ≥ 3 m from neighbours, and a child-safety "
        "fence/cover; the shelf zone is shown at the east end")
    # loungers / furniture placed in the pool
    pool = sbox(P["x0"], P["y0"], P["x1"], P["y1"])
    for f in M.FURN:
        if furn_box(f).intersection(pool).area > 0.01:
            add("ERROR", cat, f"Furniture {furn_label(f)} stands in the pool", fix=f"delete {furn_line(f)} "
                "(the pool loungers are already in SITE['loungers'])", key=f"furn_pool:{f.kind}")
    # --- railings
    cat2 = "5 Guards & railings"
    for rl in M.RAILS:
        ref = guard_ref_level(rl["z0"])
        hh = rl["z0"] + rl["h"] - ref
        if hh < R["rail_min"] - 0.005:
            add("ERROR", cat2, f"Railing ({rl['x0']:.2f},{rl['y0']:.2f})→({rl['x1']:.2f},{rl['y1']:.2f}) is "
                f"{hh:.2f} m above the walking level {ref:+.2f} (< 1.05)")
    add("INFO", cat2, "Stairs: only the glass spine between flights is modelled – draw a wall-mounted handrail at "
        "0.90 m along the slope on the wall side and ≤10 cm gaps in all balustrades")
    # roof accessible area without 1.05 guard
    rx_doors = [(w, o) for (w, o) in OPS if w.level == "R" and o.kind == "door"]
    if rx_doors:
        par_top = max((w.z1 for w in M.WALLS if w.kind == "parapet" and w.level == "R"), default=M.LV["R"])
        ph = par_top - M.LV["R"]
        if ph < R["rail_min"]:
            # roof edge segments not covered by a rail
            roof_r = [r for r in M.RAILS if abs(r["z0"] - (M.LV["R"] + 0.5)) < 0.05 or abs(r["z0"] - M.LV["R"]) < 0.05]
            cov = unary_union([sbox(min(r["x0"], r["x1"]) - 0.3, min(r["y0"], r["y1"]) - 0.3,
                                    max(r["x0"], r["x1"]) + 0.3, max(r["y0"], r["y1"]) + 0.3) for r in roof_r]
                              or [Point(-99, -99)])
            par = [w for w in M.WALLS if w.kind == "parapet" and w.level == "R"]
            unc = []
            for w in par:
                fp = wall_fp(w)
                rest = fp.difference(cov)
                if rest.area > 0.05:
                    unc.append((wid(w), rest.area / w.t))
            if unc:
                tl = sum(u[1] for u in unc)
                add("ERROR", cat2, f"Main roof is reachable through the roof-exit door but its parapet is only "
                    f"{ph:.2f} m high; {tl:.1f} m of roof edge has no 1.05 m guard (e.g. the strip in front of the roof "
                    "door, y 25.0–27.0, edge y=25.10) – fall of 3.4 m onto the family terrace",
                    fix=("RAILS: extend the R2 south rail west: dict(x0=17.9, y0=Y_NB + 0.20, …) → dict(x0=13.10, "
                         "y0=Y_NB + 0.20, …) and add a 1.05 rail with a locked maintenance gate separating the "
                         "non-trafficable PV roof: dict(x0=13.10, y0=Y_NB + 0.20, x1=13.10, y1=27.00, z0=LV['R'], h=1.05, "
                         "kind='glass'); extend room R2 rects with (13.20, 25.20, 17.80, 27.00) so the door leads "
                         "into the terrace"), key="roof_guard")
    # --- parking
    for i, (x0, y0, x1, y1) in enumerate(M.CARS):
        L, W = max(x1 - x0, y1 - y0), min(x1 - x0, y1 - y0)
        if L < R["park_l"] - 0.005 or W < R["park_w"] - 0.005:
            add("ERROR", cat, f"Parking space {i + 1} is {W:.2f}×{L:.2f} m (< 2.50×5.00)",
                fix=f"CARS[{i}] = ({M.X_E:.2f}, {y0:.2f}, {M.X_E + R['park_l']:.2f}, {y1:.2f})  (5.00 m from the building "
                    "line x=25.00 to the street boundary x=30.00; the pergola posts at y 15.95/21.65 stay outside "
                    "the 2.5 m bays)", key=f"park:{i}")
        # access from street
        if abs(max(x0, x1) - M.LOT["x1"]) > 0.6:
            add("WARN", cat, f"Parking space {i + 1} does not reach the street boundary (direct access)")
        # obstacles: pergola posts, fence
        for p in M.PERGOLAS:
            for (px, py) in p["posts"]:
                if sbox(px - 0.075, py - 0.075, px + 0.075, py + 0.075).intersects(sbox(x0, y0, x1, y1)):
                    add("ERROR", cat, f"Pergola post ({px},{py}) stands in parking space {i + 1}")
    if len(M.CARS) < 2:
        add("ERROR", cat, "Fewer than 2 parking spaces in the lot")
    gate = M.SITE.get("gate")
    if gate:
        gx, gy0, gy1 = gate
        add("INFO" if gy1 - gy0 >= 1.2 else "WARN", cat, f"Pedestrian gate {gy1 - gy0:.2f} m wide at y {gy0}–{gy1}")
        doors = [(w, o) for (w, o) in OPS if o.kind == "pivot" or o.tag == "D-01"]
        if doors:
            w, o = doors[0]
            ok = gy0 - 0.3 <= (o.pos + o.end) / 2 <= gy1 + 0.3
            path = [q for q in M.SITE.get("paving", []) if q[1] <= o.pos + 0.01 and q[3] >= o.end - 0.01 and q[0] <= w.c + 0.3]
            add("INFO" if (ok and path) else "WARN", cat,
                f"Entrance path: gate → pivot door D-01 straight, paved {'yes' if path else 'NO'}; level difference "
                f"{0 - M.STREET:.2f} m (sidewalk {M.STREET:+.2f} → ±0.00) – draw 2 steps 17.5/30 or a 1:12 ramp in "
                "the 5 m front strip")


# =========================================================================== #
#  8. FURNITURE
# =========================================================================== #
def strip_clear_depth(level, poly_fn, max_d, exclude=(), step=0.05):
    """largest depth d ≤ max_d for which poly_fn(d) is free of walls/furniture/columns and inside rooms."""
    walls = unary_union([wall_fp(w) for w in plan_walls(level, include_parapet=True)]
                        + [col_fp(c) for c in cols_on(level)])
    rooms_u = unary_union([room_poly(r) for r in rooms_on(level)]).buffer(0.08)
    obs = stair_obstacles(level)
    fs = [furn_shapes(f) for f in M.FURN if f.level == level and f not in exclude and f.kind not in NOT_OBSTACLE]
    d = 0.0
    k = step
    while k <= max_d + 1e-6:
        p = poly_fn(k)
        if p.intersection(walls).area > 0.002 or p.difference(rooms_u).area > 0.01:
            break
        if obs is not None and p.intersection(obs).area > 0.01:
            break
        if any(p.intersection(f).area > 0.002 for f in fs):
            break
        d = k
        k += step
    return d


def nearest_wall_side(level, b, only=None):
    """which side of a bbox is closest to a wall: returns ('W'|'E'|'S'|'N', distance)."""
    x0, y0, x1, y1 = b
    walls = unary_union([wall_fp(w) for w in plan_walls(level)])
    probes = {"W": sbox(x0 - 0.01, y0 + 0.05, x0, y1 - 0.05), "E": sbox(x1, y0 + 0.05, x1 + 0.01, y1 - 0.05),
              "S": sbox(x0 + 0.05, y0 - 0.01, x1 - 0.05, y0), "N": sbox(x0 + 0.05, y1, x1 - 0.05, y1 + 0.01)}
    return min(((k, walls.distance(p)) for k, p in probes.items() if not only or k in only), key=lambda t: t[1])


def side_strip(b, side, d):
    x0, y0, x1, y1 = b
    return {"W": sbox(x0 - d, y0, x0, y1), "E": sbox(x1, y0, x1 + d, y1),
            "S": sbox(x0, y0 - d, x1, y0), "N": sbox(x0, y1, x1, y1 + d)}[side]


OPP = {"W": "E", "E": "W", "S": "N", "N": "S"}
PERP = {"W": ("S", "N"), "E": ("S", "N"), "S": ("W", "E"), "N": ("W", "E")}


def check_furniture():
    cat = "10 Furniture & clearances"
    for lvl in LEVELS:
        fl = [f for f in M.FURN if f.level == lvl]
        if not fl:
            continue
        rooms_u = unary_union([room_poly(r) for r in rooms_on(lvl)])
        walls = [(w, wall_fp(w)) for w in plan_walls(lvl, include_parapet=True)]
        for f in fl:
            b = furn_box(f)
            sh = furn_shapes(f)
            out = b.difference(rooms_u.buffer(0.03))
            if out.area > 0.005:
                # suggest the room it overlaps most and clamp
                best = max(rooms_on(lvl), key=lambda r: room_poly(r).intersection(b).area, default=None)
                fix = None
                if best is not None and room_poly(best).intersection(b).area > 0:
                    rx0, ry0, rx1, ry1 = room_poly(best).bounds
                    nx = min(max(f.x, rx0), rx1 - f.w)
                    ny = min(max(f.y, ry0), ry1 - f.d)
                    fix = f"{furn_line(f)} → x={nx:.2f}, y={ny:.2f} (inside {room_label(best)})"
                add("ERROR", cat, f"{furn_label(f)} sticks {out.area:.2f} m² outside the rooms {rr(out.bounds)}",
                    fix=fix, key=f"furn_out:{f.kind}:{f.x}:{f.y}")
            for w, fp in walls:
                ia = sh.intersection(fp).area
                if ia > 0.003 and min_dim(sh.intersection(fp)) > 0.02:
                    add("ERROR", cat, f"{furn_label(f)} collides with wall {wid(w)} ({ia:.3f} m²)",
                        key=f"furn_wall:{f.kind}:{f.x}:{f.y}")
            for c in cols_on(lvl) if lvl != "R" else []:
                if sh.intersection(col_fp(c)).area > 0.003:
                    add("ERROR", cat, f"{furn_label(f)} collides with column ({c.x},{c.y})")
            obs = stair_obstacles(lvl)
            if obs is not None and sh.intersection(obs).area > 0.01:
                add("ERROR", cat, f"{furn_label(f)} stands on the stair / void")
        for i, a in enumerate(fl):
            if a.kind in NOT_OBSTACLE:
                continue
            for b_ in fl[i + 1:]:
                if b_.kind in NOT_OBSTACLE:
                    continue
                ia = furn_shapes(a).intersection(furn_shapes(b_)).area
                if ia > 0.005:
                    add("ERROR", cat, f"Furniture overlap {ia:.2f} m²: {furn_label(a)} & {furn_label(b_)}",
                        key=f"furn_furn:{a.kind}:{a.x}:{b_.kind}:{b_.x}")
        # --- beds: side clearance
        for f in fl:
            b = (f.x, f.y, f.x + f.w, f.y + f.d)
            if f.kind.startswith("bed"):
                head, dist = nearest_wall_side(lvl, b)
                if dist > 0.35:
                    add("WARN", cat, f"{furn_label(f)}: bed head is {dist:.2f} m from the nearest wall (floating bed) – "
                        "put the headboard against a wall", key=f"bed_float:{f.x}:{f.y}")
                sides = PERP[head]
                ex = [g for g in fl if g.kind == "nightstand"]
                deps = {s: strip_clear_depth(lvl, lambda d, s=s: side_strip(b, s, d), R["bed_side"], exclude=ex + [f])
                        for s in sides}
                need_both = f.kind != "bed_s"
                bad = [s for s, d in deps.items() if d < R["bed_side"] - 1e-6]
                if (need_both and bad) or (not need_both and len(bad) == 2):
                    add("WARN", cat, f"{furn_label(f)}: bed side clearance {', '.join(f'{s}={deps[s]:.2f}' for s in sides)} m "
                        f"(head {head}; need {R['bed_side']:.2f} each side)", key=f"bed_side:{f.x}:{f.y}")
                foot = strip_clear_depth(lvl, lambda d: side_strip(b, OPP[head], d), 0.6,
                                         exclude=[f] + [g for g in fl if g.kind == "bench"])
                if foot < 0.6 - 1e-6:
                    add("WARN", cat, f"{furn_label(f)}: only {foot:.2f} m in front of the bed foot (min 0.60)",
                        key=f"bed_foot:{f.x}:{f.y}")
            if f.kind == "closet":
                back, dist = nearest_wall_side(lvl, b, only=("S", "N") if f.w >= f.d else ("W", "E"))
                front = OPP[back]
                dep = strip_clear_depth(lvl, lambda d: side_strip(b, front, d), R["closet_front"], exclude=[f])
                if dep < R["closet_front"] - 1e-6:
                    add("WARN", cat, f"{furn_label(f)}: only {dep:.2f} m free in front of the closet ({front} side; "
                        f"min {R['closet_front']:.2f})", key=f"closet_front:{f.x}:{f.y}")
        # --- kitchen
        isl = [f for f in fl if f.kind == "island"]
        runs = [f for f in fl if f.kind in ("counter", "counter_l", "fridge")]
        for i_ in isl:
            ib = furn_box(i_)
            rm = room_at(lvl, ib.centroid.x, ib.centroid.y)
            for c in runs:
                if room_at(lvl, furn_box(c).centroid.x, furn_box(c).centroid.y) is not rm:
                    continue
                d = furn_shapes(c).distance(ib)
                if d < R["kitchen_aisle"] - 1e-6:
                    sev = "ERROR" if d < 0.9 else "WARN"
                    add(sev, cat, f"Kitchen aisle between island {furn_label(i_)} and {furn_label(c)} is {d:.2f} m "
                        f"(min {R['kitchen_aisle']:.2f})", key=f"kitchen_aisle:{c.kind}:{c.x}")
            x0, y0, x1, y1 = ib.bounds
            for s in "WESN":
                dep = strip_clear_depth(lvl, lambda d, s=s: side_strip((x0, y0, x1, y1), s, d), R["island_clear"],
                                        exclude=[i_])
                if dep < R["island_clear"] - 1e-6:
                    add("WARN", cat, f"Island {furn_label(i_)}: {s} side clearance {dep:.2f} m (< {R['island_clear']:.2f})",
                        key=f"island_clear:{s}")
    # work triangle
    fr = [f for f in M.FURN if f.level == "G" and f.kind == "fridge"]
    isl = [f for f in M.FURN if f.level == "G" and f.kind == "island"]
    kroom = [r for r in rooms_on("G") if "מטבח" == r.name.strip()]
    cnt = [f for f in M.FURN if f.level == "G" and f.kind in ("counter", "counter_l") and kroom
           and room_poly(kroom[0]).contains(furn_box(f).centroid)]
    if fr and isl and cnt:
        hob = max(cnt, key=lambda f: max(f.w, f.d))
        k = [fr[0], isl[0], hob]
        pts = [furn_box(f).centroid for f in k]
        legs = [pts[0].distance(pts[1]), pts[1].distance(pts[2]), pts[2].distance(pts[0])]
        per = sum(legs)
        ok = 3.6 <= per <= 7.9 and all(1.2 <= l_ <= 2.7 for l_ in legs)
        add("INFO" if ok else "WARN", cat, f"Kitchen work triangle (fridge / island-sink / counter-hob centroids): legs "
            f"{', '.join(f'{l_:.2f}' for l_ in legs)} m, perimeter {per:.2f} m (guide 3.6–7.9, legs 1.2–2.7)")


# =========================================================================== #
#  9. ARCHITECTURAL PLANNING REVIEW (daylight, ventilation, wet stacking, circulation)
# =========================================================================== #
def room_glazing(r):
    """area of ext-wall openings (windows/glazed doors) belonging to room r."""
    tot = 0.0
    lst = []
    for w, o in OPS:
        if w.level != r.level or w.kind not in ("ext", "retain") or o.kind in ("door", "mamad_door", "pivot", "passage"):
            continue
        if not w.out:
            continue
        pin = side_point(w, o, -w.out, 0.25)
        if room_at(r.level, *pin, outdoor=False) is r:
            hh = o.head - max(o.sill, 0)
            if o.kind == "open":
                continue
            tot += (o.end - o.pos) * hh
            lst.append(o.tag or o.kind)
    # glazing via an open loggia frame / glass wall (master bedroom)
    for w, o in OPS:
        if w.level == r.level and w.kind == "glass":
            for s in (1, -1):
                if room_at(r.level, *side_point(w, o, s, 0.2), outdoor=False) is r:
                    tot += (o.end - o.pos) * (o.head - o.sill)
                    lst.append(o.tag)
    return tot, lst


def adjacency():
    """room graph: doors / passages / slides + open boundaries + stairs."""
    E = defaultdict(set)
    for w, o in OPS:
        if o.kind in ("window", "fixed", "mamad_win"):
            continue
        a = room_at(w.level, *side_point(w, o, 1))
        b = room_at(w.level, *side_point(w, o, -1))
        if a and b and a is not b:
            E[id(a)].add(id(b))
            E[id(b)].add(id(a))
    for lvl in LEVELS:
        rs = rooms_on(lvl)
        wu = unary_union([wall_fp(w) for w in plan_walls(lvl, include_parapet=True)] or [Point(-99, -99)])
        for i, a in enumerate(rs):
            pa = room_poly(a).buffer(0.20, join_style=2)
            for b in rs[i + 1:]:
                strip = pa.intersection(room_poly(b).buffer(0.20, join_style=2))
                if strip.area < 0.05:
                    continue
                free = strip.difference(wu)
                if free.area > 0.15 and max(free.bounds[2] - free.bounds[0], free.bounds[3] - free.bounds[1]) > 0.7:
                    E[id(a)].add(id(b))
                    E[id(b)].add(id(a))
    # stairs connect the rooms containing the stair core on consecutive levels
    cx = (M.ST["x0"] + M.ST["x0"] + 2 * M.ST["w"] + M.ST["gap"]) / 2
    for s in M.STAIRS:
        a = room_at(s["level"], cx, M.ST["yl"] - 1.0) or room_at(s["level"], cx, s["yA0"] - 0.3)
        b = room_at(NEXT[s["level"]], cx, M.ST["yl"] - 1.0) or room_at(NEXT[s["level"]], cx, s["yB_end"] - 0.3)
        if a and b:
            E[id(a)].add(id(b))
            E[id(b)].add(id(a))
    return E


def check_planning_quality():
    cat = "11 Architectural planning"
    # --- daylight / ventilation
    for r in M.ROOMS:
        if r.outdoor:
            continue
        area = room_poly(r).area
        g, lst = room_glazing(r)
        if is_habitable(r):
            if g == 0:
                sev = "INFO" if "קולנוע" in r.name else "WARN"
                add(sev, cat, f"{room_label(r)} ({r.level}): habitable room with NO window/glazed door to the outside"
                    + (" – acceptable for a cinema, needs fresh-air AHU" if sev == "INFO" else
                       " – needs daylight & natural ventilation (≥10 % of floor area)"), key=f"daylight:{r.no}")
            elif g < R["win_area_ratio"] * area:
                if 'ממ"ד' in r.name:
                    add("INFO", cat, f"{room_label(r)}: glazing {g:.1f} m² = {100 * g / area:.0f} % of floor – the ממ\"ד "
                        "window is capped at 100/100; acceptable for a ממ\"ד used as a child room, note it")
                else:
                    add("WARN", cat, f"{room_label(r)}: glazing {g:.1f} m² = {100 * g / area:.0f} % of floor (< 10 %)",
                        key=f"glazing:{r.no}")
        elif is_wet(r) and g == 0:
            add("INFO", cat, f"{room_label(r)} ({r.level}): wet room without window → note mechanical exhaust "
                "(מפוח + תעלה לגג/חזית) on plans")
    # --- wet-room stacking
    wet = defaultdict(list)
    for r in M.ROOMS:
        if is_wet(r) and not r.outdoor:
            wet[r.level].append(r)
    for up, lo in (("U", "G"), ("G", "B")):
        for r in wet[up]:
            p = room_poly(r)
            below = [q for q in wet[lo] if room_poly(q).intersection(p).area > 0.3]
            if not below:
                under = [q for q in rooms_on(lo) if room_poly(q).intersection(p).area > 0.3]
                add("INFO" if up == "G" else "WARN", cat,
                    f"{room_label(r)} ({up}) is not stacked over a wet room – drains/risers pass over "
                    f"{', '.join(room_label(q) for q in under) or 'nothing'}; provide a riser shaft "
                    "(e.g. in the 13.06 core wall / beside the lift) and a suspended ceiling below",
                    key=f"wetstack:{r.no}")
    # --- circulation reachability from the entrance
    E = adjacency()
    byid = {id(r): r for r in M.ROOMS}
    ent = None
    for w, o in OPS:
        if o.kind == "pivot" or o.tag == "D-01":
            for s in (1, -1):
                q = room_at(w.level, *side_point(w, o, s))
                if q and not q.outdoor:
                    ent = q
    if ent:
        seen = {id(ent)}
        stack = [id(ent)]
        while stack:
            k = stack.pop()
            for n in E[k]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        for r in M.ROOMS:
            if id(r) not in seen:
                add("ERROR", cat, f"{room_label(r)} ({r.level}) cannot be reached from the entrance through doors / "
                    "open plan / stairs", key=f"reach:{r.no}")
    # --- rooms reached only through another private/wet room
    for r in M.ROOMS:
        if r.outdoor:
            continue
        nb = [byid[k] for k in E[id(r)]]
        if nb and all(is_wet(q) for q in nb) and not is_wet(r):
            add("ERROR", cat, f"{room_label(r)} is accessible only through {', '.join(room_label(q) for q in nb)}",
                key=f"through_wet:{r.no}")


# =========================================================================== #
#  Curated architect fixes (shown only while the finding exists)
# =========================================================================== #
CURATED = {
    "op_cut:M-D": ('U corridor wall overlaps the ממ"ד south wall and blocks the blast door: '
                   'wall("U", 6.30, 26.96, 13.12, 26.96) → wall("U", 11.20, 26.96, 13.12, 26.96)  '
                   '(keep it only as bath-3 south wall); corridor U5 rects → [(6.30, 25.36, 13.00, 26.96)] '
                   'minus the bath-3 part, i.e. [(6.30, 25.36, 13.00, 26.90), (6.30, 26.90, 10.90, 26.96)] or simply leave '
                   '(6.30, 25.36, 13.00, 26.90)'),
    "wall_overlap:U:26.96:27.11": 'same fix as the ממ"ד door: wall("U", 6.30, 26.96, 13.12, 26.96) → wall("U", 11.20, 26.96, 13.12, 26.96)',
    "wall_overlap:U:27.11:26.96": 'same fix as the ממ"ד door: wall("U", 6.30, 26.96, 13.12, 26.96) → wall("U", 11.20, 26.96, 13.12, 26.96)',
    "mamad_wall:W": ('ממ"ד west & north walls are the 20 cm block exterior wall. Add 10 cm RC linings bonded to an RC core '
                     '(RC 30 total) right after the ממ"ד walls: wall("U", 6.35, 27.26, 6.35, 31.70, t=0.10, kind="mamad", '
                     'core="rc") and wall("U", 6.40, 31.65, 10.90, 31.65, t=0.10, kind="mamad", core="rc"); room U6 rects → '
                     '[(6.40, 27.26, 10.90, 31.60)]; note "קירות חוץ ממ"ד – בטון מזוין 20+10 ס"מ" (or set the U exterior '
                     'wall core="rc" for those two segments by splitting the outline)'),
    "mamad_wall:N": 'see the ממ"ד west wall fix (10 cm RC lining y=31.65, x 6.40→10.90)',
    "op_stair:D-B2:13.06": ('cinema door opens onto basement stair flight A. Move it south, opening from the lounge: '
                            'op("B", V, 13.06, 28.20, 29.10, 0, 2.20, "door", "D-B2", hinge="b", swing=-1) → '
                            'op("B", V, 13.06, 26.50, 27.40, 0, 2.20, "door", "D-B2", hinge="b", swing=-1)'),
    "swing_furn:D-22:vanity2": ('master bath door: shorten the west dressing closet and swing into the dressing: '
                                'furn("closet", "U", 9.7, 21.8, 0.6, 3.35, rot=90) → furn("closet", "U", 9.7, 23.45, 0.6, 1.70, rot=90); '
                                'op("U", V, 9.56, 22.40, 23.30, …, hinge="b", swing=-1) → swing=1'),
    "swing_furn:D-21:closet": ('master suite entry: op("U", H, 25.30, 11.50, 12.40, 0, 2.20, "door", "D-21", hinge="a", swing=-1) → '
                               'op("U", H, 25.30, 10.70, 11.60, 0, 2.20, "door", "D-21", hinge="a", swing=-1) and delete '
                               'furn("island_s", "U", 10.65, 22.6, 0.9, 1.6) (dressing is 3.08 m wide: 0.6+1.75 aisle+0.6 '
                               'without the island; with it the aisles are 35/50 cm)'),
    "swing_furn:D-03:wc": ('guest WC: the WC pan sits in the door opening. op("G", V, 19.06, 26.30, 27.10, …, "D-03", '
                           'hinge="a", swing=1) → swing=-1 (opens out to the hall) and furn("wc", "G", 19.2, 26.4, 0.4, 0.6, rot=90) → '
                           'furn("wc", "G", 20.30, 25.80, 0.6, 0.4, rot=180) (against the pantry wall)'),
    "swing_furn:D-B3:closet": ('guest bedroom: furn("closet", "B", 19.2, 24.35, 2.2, 0.6, rot=180) → '
                               'furn("closet", "B", 20.05, 24.35, 2.0, 0.6, rot=180)'),
    "swing_furn:D-B4:vanity": 'guest bath: op("B", H, 25.06, 22.20, 23.00, …, "D-B4", hinge="a", swing=1) → swing=-1 (opens into the guest room)',
    "swing_furn:D-B5:sauna": 'spa: op("B", V, 19.06, 26.00, 26.90, …, "D-B5", hinge="a", swing=1) → swing=-1 (opens into the lounge)',
    "swing_furn:D-B5:shower": 'spa: op("B", V, 19.06, 26.00, 26.90, …, "D-B5", hinge="a", swing=1) → swing=-1 (opens into the lounge)',
    "op_block:D-04:counter": ('kitchen re-plan (north wall carries counter + fridge + L-counter on top of each other and blocks '
                              'the pantry door): replace the 4 kitchen furn lines with  furn("counter", "G", 19.20, 24.98, 1.90, 0.62); '
                              'furn("fridge", "G", 22.10, 24.98, 1.98, 0.62, label="tall units");  furn("counter", "G", 24.08, 21.45, 0.62, 3.53);  '
                              'furn("island", "G", 20.28, 22.88, 2.80, 1.10, h=0.92)  → aisles 1.00 m, pantry door D-04 at 21.20→22.00 clear'),
    "through_wet:B8": ('tech room reachable only through the guest bathroom: op("B", H, 27.66, 22.40, 23.30, 0, 2.20, "door", "D-B7", '
                       'hinge="a", swing=1) → op("B", V, 21.56, 28.40, 29.30, 0, 2.20, "door", "D-B7", hinge="a", swing=1) '
                       '(from the storeroom)'),
    "op_block:AL-05:tvunit": ('TV unit stands in front of the west sliding door: furn("tvunit", "G", 6.35, 22.4, 0.45, 2.8, rot=90) → '
                              'furn("tvunit", "G", 12.50, 25.85, 0.45, 2.60, rot=270) (on the core wall) – and turn the sofa_l to face it'),
    "furn_pool:lounger": 'delete furn("lounger", "G", 9.0, 11.0, 0.7, 2.0) – it is inside the pool (SITE loungers already exist at y=14.2)',
    "daylight:B2": ('gym has no daylight: extend the sunken patio west under the covered terrace edge, e.g. an English court '
                    '(חצר אנגלית) 1.2 m wide along the basement west wall x 4.8→6.0, y 21.6→25.0 with a window '
                    'op("B", V, 6.15, 21.80, 24.90, 0.0, 2.60, "slide", "AL-B3") – or record "mechanical ventilation + no '
                    'habitable use" for the gym'),
}


# =========================================================================== #
#  Report
# =========================================================================== #
def write_report(path, quiet=False):
    sev_order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    # de-duplicate identical messages
    seen = set()
    uniq = []
    for f in FINDINGS:
        k = (f["sev"], f["msg"])
        if k in seen:
            continue
        seen.add(k)
        if f.get("key") in CURATED:
            f["fix"] = CURATED[f["key"]]
        uniq.append(f)
    cnt = defaultdict(int)
    for f in uniq:
        cnt[f["sev"]] += 1
    cats = sorted(set(f["cat"] for f in uniq), key=lambda c: int(c.split()[0]))
    L = []
    L.append(f"# QA report – {M.PROJECT['name_en']} ({M.PROJECT['name']})\n")
    L.append("Generated by `src/qa_check.py` from `model.py` – re-run after every model change.\n")
    L.append(f"**Summary:** {cnt['ERROR']} ERROR · {cnt['WARN']} WARN · {cnt['INFO']} INFO\n")
    L.append("Conventions: coordinates in metres (origin lot SW, X east, Y north), levels relative to ±0.00. "
             "Door swing: `swing=+1` opens to +normal (north for horizontal walls, east for vertical), hinge `a` at "
             "`pos`, `b` at `end`; furniture `w` = x-extent, `d` = y-extent.\n")
    # ranked
    L.append("## Ranked list of ERROR/WARN with proposed fixes\n")
    n = 0
    for f in sorted(uniq, key=lambda f: (sev_order[f["sev"]], int(f["cat"].split()[0]))):
        if f["sev"] == "INFO":
            continue
        n += 1
        L.append(f"{n}. **{f['sev']}** [{f['cat']}] {f['msg']}")
        if f.get("fix"):
            L.append(f"   - *Fix:* `{f['fix']}`" if len(f["fix"]) < 160 and "`" not in f["fix"] else f"   - *Fix:* {f['fix']}")
        L.append("")
    if n == 0:
        L.append("No ERROR or WARN findings.\n")
    # all by category
    L.append("\n## All findings by category\n")
    for c in cats:
        L.append(f"### {c}\n")
        for f in sorted([f for f in uniq if f["cat"] == c], key=lambda f: sev_order[f["sev"]]):
            L.append(f"- **{f['sev']}** {f['msg']}")
        L.append("")
    # tables
    if "areas" in SECTIONS:
        L.append("## Area table (טבלת שטחים – gross, outer faces of exterior walls, shapely)\n")
        L.append("| Level | Gross m² | Service items (m²) | Balcony/loggia m² | Main m² |")
        L.append("|---|---:|---|---:|---:|")
        tm = ts = 0
        for (l, gross, serv, bal, main) in SECTIONS["areas"]:
            si = "; ".join(f"{k} {v:.1f}" for k, v in serv.items()) or "–"
            L.append(f"| {LVL_HE[l]} ({l}) | {gross:.1f} | {si} = **{sum(serv.values()):.1f}** | {bal:.1f} | "
                     f"{main:.1f}{' (basement – separate)' if l == 'B' else ''} |")
            if l in ("G", "U"):
                tm += main
            if l in ("G", "U", "R"):
                ts += sum(serv.values())
        lot_a = (M.LOT["x1"] - M.LOT["x0"]) * (M.LOT["y1"] - M.LOT["y0"])
        L.append(f"| **Total above ground** | | **{ts:.1f}** (max {0.16 * lot_a:.0f}) | | **{tm:.1f}** (max {0.35 * lot_a:.0f}) |")
        L.append("\nNotes: stair cage + lift counted as service on each storey (roof-exit room fully service); ממ\"ד "
                 "with its 30 cm walls; balconies/loggia listed apart (check the takanon balcony allowance). "
                 "Covered terrace under the cantilever and the GF-roof terrace are open – not counted, but the cantilever "
                 "counts in the coverage.\n")
    if "rooms" in SECTIONS:
        L.append("## Room schedule (net areas)\n")
        L.append("| Level | No | Room | Net m² | Min dim | Ceiling | Type |")
        L.append("|---|---|---|---:|---:|---:|---|")
        for (l, no, name, net, md, ceil, serv, out) in SECTIONS["rooms"]:
            t = "outdoor" if out else ("service" if serv else "main")
            L.append(f"| {l} | {no} | {name} | {net:.2f} | {md:.2f} | {'' if out else f'{ceil:.2f}'} | {t} |")
        L.append("")
    if "stairs" in SECTIONS:
        L.append("## Stairs\n")
        L.append("| Run | Risers (A+B) | R cm | T cm | 2R+T cm | Min headroom m |")
        L.append("|---|---|---:|---:|---:|---:|")
        hr = defaultdict(lambda: 99)
        for (lvl, fl, i, z, h, src) in SECTIONS.get("headroom", []):
            hr[lvl] = min(hr[lvl], h)
        for (lvl, n_, r, t, f2, nA, nB) in SECTIONS["stairs"]:
            L.append(f"| {lvl}→{NEXT[lvl]} | {n_} ({nA}+{nB}) | {r * 100:.2f} | {t * 100:.0f} | {f2 * 100:.1f} | {hr[lvl]:.2f} |")
        L.append("")
    txt = "\n".join(L)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(txt)
    # console
    print(f"QA {M.PROJECT['name_en']}: {cnt['ERROR']} ERROR, {cnt['WARN']} WARN, {cnt['INFO']} INFO")
    if not quiet:
        for c in cats:
            print(f"\n== {c}")
            for f in sorted([f for f in uniq if f["cat"] == c], key=lambda f: sev_order[f["sev"]]):
                print(f"  {f['sev']:5s} {f['msg']}")
                if f.get("fix") and f["sev"] != "INFO":
                    print(f"        fix: {f['fix']}")
    print(f"\nreport: {path}")
    return cnt


def main():
    quiet = "--quiet" in sys.argv
    for fn in (check_walls, check_openings, check_rooms, check_stairs, check_heights, check_support,
               check_planning, check_site, check_furniture, check_planning_quality):
        try:
            fn()
        except Exception as e:  # keep the checker running if the model changes shape
            import traceback
            add("ERROR", "0 Checker", f"{fn.__name__} crashed: {e!r}")
            traceback.print_exc()
    out = os.path.join(MODEL_DIR, "qa_report.md") if MODEL_DIR else os.path.join(ROOT, "out", "qa_report.md")
    cnt = write_report(out, quiet=quiet)
    return 1 if cnt["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
