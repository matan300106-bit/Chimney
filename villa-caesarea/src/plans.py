"""Floor plans (1:100 & 1:50) generated from the model."""
from __future__ import annotations

import math

from shapely.geometry import box as sbox, Polygon, MultiPolygon, LineString
from shapely.ops import unary_union

import model as M
import furniture2d
from draw import (View, drawing_title, north_arrow, section_marker, grid_bubble, elevation_marker, scale_bar,
                  new_dxf)

CUT = 1.20

# section lines (shared with elev.py)
SECTIONS = {
    "A": dict(axis="x", c=29.05, a0=4.0, a1=29.0, look=+1, label="A"),   # along x at y=29.05, looking north
    "B": dict(axis="y", c=10.05, a0=6.5, a1=34.5, look=-1, label="B"),   # along y at x=10.05, looking west
    "C": dict(axis="y", c=16.40, a0=13.0, a1=34.5, look=+1, label="C"),  # along y at x=16.40, looking east
}

DXF_DOCS = {}


def level_floor(level):
    return M.LV[level] if level != "R" else M.LV["R"]


def polys(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]


def ring_pts(p):
    return [list(p.exterior.coords)] + [list(i.coords) for i in p.interiors]


def wall_layers(w):
    """[(polygon, material)] in plan for a wall, openings removed. Ext walls split core/skin."""
    half = w.t / 2
    ext = w.kind in ("ext", "retain")
    a0, a1 = (w.a0 - half, w.a1 + half) if ext else (w.a0, w.a1)
    if ext and w.out:
        s = w.out
        core = (-half, half - M.T_SKIN) if s > 0 else (-half + M.T_SKIN, half)
        skin = (half - M.T_SKIN, half) if s > 0 else (-half, -half + M.T_SKIN)
        core_mat = "rc" if (w.core == "rc" or w.kind == "retain") else "block"
        skin_mat = {"stone": "stone", "plaster": "plaster", "rc_fair": "membrane"}.get(w.skin, "plaster")
        layers = [(core, core_mat), (skin, skin_mat)]
    else:
        mat = {"rc": "rc", "mamad": "rc", "shaft": "rc", "retain": "rc", "parapet": "block", "glass": "partition"}.get(w.kind, "partition")
        if w.core == "rc":
            mat = "rc"
        layers = [((-half, half), mat)]
    out = []
    gaps = []
    for o in w.openings:
        gaps.append((o.pos, o.end))
    for (o0, o1), mat in layers:
        if w.horiz:
            g = sbox(a0, w.c + o0, a1, w.c + o1)
            for (p, e) in gaps:
                g = g.difference(sbox(p, w.c - 1, e, w.c + 1))
        else:
            g = sbox(w.c + o0, a0, w.c + o1, a1)
            for (p, e) in gaps:
                g = g.difference(sbox(w.c - 1, p, w.c + 1, e))
        out.append((g, mat))
    return out


def is_cut(w, level):
    zc = level_floor(level) + CUT
    return w.z0 - 1e-6 <= zc <= w.z1 + 1e-6


FILL = {"block": "pat:block", "rc": "pat:rc", "stone": "pat:stone", "plaster": "#ffffff", "membrane": "#222",
        "partition": "pat:partition"}


def draw_walls(v: View, level, scale):
    lvl_walls = [w for w in M.WALLS if w.level == level]
    cut = [w for w in lvl_walls if is_cut(w, level)]
    below = [w for w in lvl_walls if w.z1 < level_floor(level) + CUT - 1e-6]
    # projections of low walls (parapets, patio walls) – outline only
    for w in below:
        for g, mat in wall_layers(w):
            for p in polys(g):
                v.polygon(ring_pts(p), fill="#f4f1ea", lw="s")
    allg = []
    for w in cut:
        for g, mat in wall_layers(w):
            for p in polys(g):
                v.polygon(ring_pts(p), fill=FILL.get(mat, "#fff"), color="none", lw="xs")
                allg.append(p)
                if mat in ("stone", "plaster", "membrane"):
                    v.polygon(ring_pts(p), fill="none", lw="xxs", color="#000")
    # columns (cut)
    for c in M.COLS:
        if c.z0 <= level_floor(level) + CUT <= c.z1:
            r = sbox(c.x - c.w / 2, c.y - c.d / 2, c.x + c.w / 2, c.y + c.d / 2)
            v.polygon(ring_pts(r), fill="#1a1a1a", color="none")
            allg.append(r)
    u = unary_union(allg)
    for p in polys(u):
        v.polygon(ring_pts(p), fill="none", lw="xl" if scale >= 100 else "xxl")
    return cut


def draw_openings(v: View, level, scale):
    fl = level_floor(level)
    for w in M.WALLS:
        if w.level != level or not is_cut(w, level):
            continue
        half = w.t / 2
        for o in w.openings:
            L = o.end - o.pos
            if w.horiz:
                def P(a, n):
                    return (a, w.c + n)
            else:
                def P(a, n):
                    return (w.c + n, a)
            # jamb lines across the gap at both wall faces (sill lines)
            if o.kind in ("window", "fixed", "slide", "mamad_win"):
                gpos = 0.0
                if w.kind == "ext" and w.out:
                    gpos = (half - M.T_SKIN - 0.07) * w.out
                lw_g = "s"
                # outer & inner sill lines
                v.line(*P(o.pos, -half), *P(o.end, -half), lw="xs")
                v.line(*P(o.pos, half), *P(o.end, half), lw="xs")
                if o.kind == "slide":
                    n = max(2, round(L / 2.2))
                    pw = L / n
                    for i in range(n):
                        off = gpos + (0.03 if i % 2 else -0.03)
                        a0 = o.pos + i * pw - (0.05 if i else 0)
                        a1 = o.pos + (i + 1) * pw + (0.05 if i < n - 1 else 0)
                        v.line(*P(a0, off), *P(a1, off), lw="m")
                    # sliding arrow
                    if scale <= 50:
                        am = o.pos + pw * 0.5
                        v.line(*P(am - 0.3, gpos - 0.12 * w.out if w.out else gpos - 0.12),
                               *P(am + 0.3, gpos - 0.12 * w.out if w.out else gpos - 0.12), lw="xxs")
                elif o.kind == "mamad_win":
                    v.line(*P(o.pos, gpos), *P(o.end, gpos), lw="m")
                    v.line(*P(o.pos - 0.05, -half + 0.03), *P(o.end + 0.05, -half + 0.03), lw="m")
                else:
                    v.line(*P(o.pos, gpos - 0.02), *P(o.end, gpos - 0.02), lw=lw_g)
                    v.line(*P(o.pos, gpos + 0.02), *P(o.end, gpos + 0.02), lw=lw_g)
                    if o.sill >= 1.4:  # high window: dashed head line inside
                        pass
            elif o.kind in ("door", "mamad_door", "pivot"):
                hinge = o.pos if o.hinge == "a" else o.end
                other = o.end if o.hinge == "a" else o.pos
                sgn = o.swing
                face = half * sgn
                # leaf
                if o.kind == "pivot":
                    pv = o.pos + 0.25 * (1 if o.hinge == "a" else -1) if False else o.pos + L * 0.18
                    ang = 75
                    lx0, ly0 = P(pv, 0)
                    # leaf rotated ang degrees around pivot
                    if w.horiz:
                        dx, dy = (L - (pv - o.pos)), 0
                    else:
                        dx, dy = 0, (L - (pv - o.pos))
                    ca, sa = math.cos(math.radians(ang * -sgn)), math.sin(math.radians(ang * -sgn))
                    if not w.horiz:
                        ca, sa = math.cos(math.radians(ang * sgn)), math.sin(math.radians(ang * sgn))
                    ex, ey = lx0 + dx * ca - dy * sa, ly0 + dx * sa + dy * ca
                    v.line(lx0, ly0, ex, ey, lw="m")
                    r = L - (pv - o.pos)
                    a_start = math.degrees(math.atan2(ey - ly0, ex - lx0))
                    a_end = 0 if w.horiz else 90
                    v.arc(lx0, ly0, r, min(a_start, a_end), max(a_start, a_end), lw="xxs", color="#555")
                    # back part of leaf
                    v.line(lx0, ly0, lx0 - (ex - lx0) * (pv - o.pos) / r, ly0 - (ey - ly0) * (pv - o.pos) / r, lw="m")
                    continue
                hx, hy = P(hinge, face)
                if w.horiz:
                    ex, ey = hx, hy + sgn * L
                    a_closed = 0 if other > hinge else 180
                    a_open = 90 if sgn > 0 else 270
                else:
                    ex, ey = hx + sgn * L, hy
                    a_closed = 90 if other > hinge else 270
                    a_open = 0 if sgn > 0 else 180
                v.line(hx, hy, ex, ey, lw="l" if o.kind == "mamad_door" else "m")
                a0, a1 = a_closed, a_open
                if abs(a1 - a0) > 180:
                    if a0 < a1:
                        a0 += 360
                    else:
                        a1 += 360
                v.arc(hx, hy, L, min(a0, a1), max(a0, a1), lw="xxs", color="#555")
                # threshold line
                v.line(*P(o.pos, -half), *P(o.pos, half), lw="xxs")
                v.line(*P(o.end, -half), *P(o.end, half), lw="xxs")
            elif o.kind == "open":
                v.line(*P(o.pos, 0), *P(o.end, 0), lw="xs", dash="2 1")
            elif o.kind == "passage":
                v.line(*P(o.pos, 0), *P(o.end, 0), lw="xxs", dash="1.5 1", color="#777")
            # tags at 1:50
            if scale <= 50 and o.tag:
                n_out = (half + 0.55) * (w.out if w.out else 1)
                if w.kind != "ext":
                    n_out = half + 0.35
                tx, ty = P((o.pos + o.end) / 2, n_out)
                px, py = v.P(tx, ty)
                tw = len(o.tag) * 1.35 + 2
                v.sh.rect(px - tw / 2, py - 1.9, tw, 3.2, lw="xs", fill="#fff")
                v.sh.text(px, py + 0.75, o.tag, size=2.0, weight=600)


def draw_stairs(v: View, level, scale):
    fl = level_floor(level)
    st_up = next((s for s in M.STAIRS if s["level"] == level), None)
    st_dn = next((s for s in M.STAIRS if abs(s["z1"] - fl) < 1e-6), None)
    sty = dict(lw="s")
    if st_up:
        # flight A: treads up to cut, then break line
        zc = fl + CUT + 0.4
        brk_y = None
        for (x0, y0, x1, y1, z) in st_up["treadsA"]:
            if z <= zc:
                v.rect(x0, y0, x1, y1, fill="#fff", **sty)
            else:
                if brk_y is None:
                    brk_y = y0
                v.rect(x0, y0, x1, y1, fill="none", lw="xxs", dash="1 0.8", color="#666")
        # first riser line
        fx0, fy0, fx1, fy1 = st_up["flightA"]
        v.line(fx0, fy0 - 0.28, fx1, fy0 - 0.28, lw="s") if False else None
        if brk_y:
            v.polyline([(fx0 - 0.05, brk_y - 0.25), (fx0 + 0.4, brk_y - 0.25), (fx0 + 0.55, brk_y - 0.05),
                        (fx0 + 0.6, brk_y - 0.45), (fx0 + 0.75, brk_y - 0.25), (fx1 + 0.05, brk_y - 0.25)], lw="s")
        # landing & flight B above cut – dashed
        lx0, ly0, lx1, ly1, lz = st_up["landing"]
        v.rect(lx0, ly0, lx1, ly1, fill="none", lw="xxs", dash="1 0.8", color="#666")
        for (x0, y0, x1, y1, z) in st_up["treadsB"]:
            v.rect(x0, y0, x1, y1, fill="none", lw="xxs", dash="1 0.8", color="#666")
        # up arrow along flight A
        cx = (fx0 + fx1) / 2
        v.polyline([(cx, fy0 + 0.1), (cx, (brk_y or fy1) - 0.5)], lw="xs")
        tip = (brk_y or fy1) - 0.5
        v.polygon([(cx - 0.09, tip - 0.18), (cx + 0.09, tip - 0.18), (cx, tip)], fill="#000", lw="xs")
        v.circle(cx, fy0 + 0.1, 0.05, fill="#000", lw="xs")
        v.text(cx, fy0 - 0.30, "עולה", size=1.8 if scale >= 100 else 2.2)
        if scale <= 50:
            v.text(cx + 0.65, fy0 + 0.9, f'{st_up["nA"] + st_up["nB"]}×{st_up["r"] * 100:.1f}/{st_up["t"] * 100:.0f}',
                   size=1.8, rot=-90)
    if st_dn:
        # flight B of the run below is visible (descending)
        for (x0, y0, x1, y1, z) in st_dn["treadsB"]:
            v.rect(x0, y0, x1, y1, fill="#fff", **sty)
        bx0, by0, bx1, by1 = st_dn["flightB"]
        if not st_up:
            lx0, ly0, lx1, ly1, lz = st_dn["landing"]
            v.rect(lx0, ly0, lx1, ly1, fill="#fff", **sty)
            for (x0, y0, x1, y1, z) in st_dn["treadsA"]:
                v.rect(x0, y0, x1, y1, fill="#fff", **sty)
        cx = (bx0 + bx1) / 2
        v.polyline([(cx, by0 + 0.1), (cx, by1 - 0.3)], lw="xs")
        v.polygon([(cx - 0.09, by1 - 0.48), (cx + 0.09, by1 - 0.48), (cx, by1 - 0.3)], fill="#000", lw="xs")
        v.text(cx, by0 - 0.30, "יורד", size=1.8 if scale >= 100 else 2.2)
    # glass spine between flights
    if st_up or st_dn:
        gx = M.ST["x0"] + M.ST["w"] + M.ST["gap"] / 2
        s = st_up or st_dn
        v.line(gx, s["yA0"], gx, M.ST["yl"], lw="m")
    # lift
    if level in ("B", "G", "U", "R"):
        x0, y0, x1, y1 = M.LIFT["x0"] + 0.2, M.LIFT["y0"] + 0.2, M.LIFT["x1"] - 0.2, M.LIFT["y1"]
        v.rect(x0 + 0.05, y0 + 0.08, x1 - 0.05, y1 - 0.05, fill="none", lw="xs")
        v.line(x0 + 0.05, y0 + 0.08, x1 - 0.05, y1 - 0.05, lw="xxs")
        v.line(x1 - 0.05, y0 + 0.08, x0 + 0.05, y1 - 0.05, lw="xxs")
        v.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.25, "מעלית", size=1.8 if scale >= 100 else 2.2,
               weight=500)


def draw_patio_stair(v: View, level, scale):
    ps = getattr(M, "PATIO_STAIR", None)
    if not ps or level not in ("B", "G"):
        return
    for i in range(ps["n"] - 1):
        x0 = ps["x0"] + i * ps["t"]
        v.rect(x0, ps["y0"], x0 + ps["t"], ps["y1"], fill="#fff", lw="xs")
    xl = ps["x0"] + (ps["n"] - 1) * ps["t"]
    v.rect(xl, ps["y0"], xl + 1.0, ps["y1"], fill="#fff", lw="xs")
    cy = (ps["y0"] + ps["y1"]) / 2
    v.line(ps["x0"] + 0.1, cy, xl - 0.15, cy, lw="xs")
    v.polygon([(xl - 0.35, cy - 0.09), (xl - 0.35, cy + 0.09), (xl - 0.15, cy)], fill="#000", lw="xs")
    if level == "B":
        v.text(ps["x0"] + 1.4, cy + 0.12, f'עולה לגן  {ps["n"]}×{(ps["z1"] - ps["z0"]) / ps["n"] * 100:.1f}/28',
               size=1.7 if scale >= 100 else 2.1)


def draw_risers(v: View, level, scale):
    for (x0, y0, x1, y1) in getattr(M, "RISERS", []):
        v.rect(x0, y0, x1, y1, fill="#fff", lw="s")
        v.line(x0, y0, x1, y1, lw="xxs")
        v.line(x0, y1, x1, y0, lw="xxs")


def room_area(r):
    return unary_union([sbox(*q) for q in r.rects]).area


def draw_room_tags(v: View, level, scale):
    for r in M.ROOMS:
        if r.level != level:
            continue
        u = unary_union([sbox(*q) for q in r.rects])
        if r.tag_at:
            cx, cy = r.tag_at
        else:
            c = u.representative_point() if not u.centroid.within(u) else u.centroid
            cx, cy = c.x, c.y
        px, py = v.P(cx, cy)
        sz = 2.5 if scale >= 100 else 3.2
        area = u.area
        v.sh.text(px, py - 0.4, r.name, size=sz, weight=700)
        v.sh.text(px, py + sz * 0.95, f'{area:.1f} מ"ר', size=sz * 0.78, weight=400)
        if scale <= 50:
            v.sh.text(px, py + sz * 1.85, f"ריצוף: {r.floor}", size=sz * 0.62, color="#444")
            if not r.outdoor:
                v.sh.text(px, py + sz * 2.6, f"ג.ת. {r.ceil:.2f}", size=sz * 0.62, color="#444")


def draw_furniture(v: View, level, scale):
    for f in M.FURN:
        if f.level == level:
            furniture2d.draw(v, f, scale)


def draw_level_marks(v: View, level, scale):
    fl = level_floor(level)
    for r in M.ROOMS:
        if r.level != level:
            continue
        u = unary_union([sbox(*q) for q in r.rects])
        minx, miny, maxx, maxy = u.bounds
        z = fl
        if r.outdoor:
            z = fl - 0.02 if level != "B" else M.LV["B"] - 0.02
        if r.name.startswith("פטיו"):
            z = M.LV["B"] - 0.02
        x, y = minx + 0.45, miny + 0.45
        if u.contains(sbox(x - 0.1, y - 0.1, x + 0.1, y + 0.1)):
            v.level_mark(x, y, z, size=1.8 if scale >= 100 else 2.2, plan=True)


def ext_dims(v: View, level, scale, extra_x=(), extra_y=()):
    out = M.OUTLINES[level]
    xs = [p[0] for p in out]
    ys = [p[1] for p in out]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    ex0, ey0, ex1, ey1 = plan_extent(level)
    gap = 0.75 * scale / 100 * (1.0 if scale >= 100 else 1.6)
    k = scale / 100
    clear = {"S": miny - ey0, "N": ey1 - maxy, "W": minx - ex0, "E": ex1 - maxx}
    for side in ("S", "N", "W", "E"):
        horiz = side in ("S", "N")
        pts_open = set()
        for w in M.WALLS:
            if w.level != level or w.kind not in ("ext",) or not is_cut(w, level):
                continue
            if horiz and w.horiz:
                outer = w.c + w.out * w.t / 2
                if (side == "S" and w.out == -1) or (side == "N" and w.out == 1):
                    pts_open.add(round(w.a0 - w.t / 2, 3))
                    pts_open.add(round(w.a1 + w.t / 2, 3))
                    for o in w.openings:
                        pts_open.add(round(o.pos, 3))
                        pts_open.add(round(o.end, 3))
            if not horiz and not w.horiz:
                if (side == "W" and w.out == -1) or (side == "E" and w.out == 1):
                    pts_open.add(round(w.a0 - w.t / 2, 3))
                    pts_open.add(round(w.a1 + w.t / 2, 3))
                    for o in w.openings:
                        pts_open.add(round(o.pos, 3))
                        pts_open.add(round(o.end, 3))
        if horiz:
            base = miny if side == "S" else maxy
            sgn = -1 if side == "S" else 1
            base += sgn * clear[side]
            outer_pts = sorted(set(xs))
            v.dim_chain(sorted(pts_open | {minx, maxx}), 0, axis="x", at=base + sgn * (1.0 * k + gap), size=1.9 if scale >= 100 else 2.3,
                        ext_from=base + sgn * 0.3, label_side=1)
            if len(set(outer_pts) | set(extra_x)) > 2:
                v.dim_chain(sorted(set(outer_pts) | set(extra_x)), 0, axis="x", at=base + sgn * (1.0 * k + 2 * gap),
                            size=1.9 if scale >= 100 else 2.3, label_side=1)
            v.dim_chain([minx, maxx], 0, axis="x", at=base + sgn * (1.0 * k + 3 * gap), size=2.1 if scale >= 100 else 2.6,
                        label_side=1)
        else:
            base = minx if side == "W" else maxx
            sgn = -1 if side == "W" else 1
            base += sgn * clear[side]
            outer_pts = sorted(set(ys))
            v.dim_chain(sorted(pts_open | {miny, maxy}), 0, axis="y", at=base + sgn * (1.0 * k + gap), size=1.9 if scale >= 100 else 2.3,
                        ext_from=base + sgn * 0.3)
            if len(set(outer_pts) | set(extra_y)) > 2:
                v.dim_chain(sorted(set(outer_pts) | set(extra_y)), 0, axis="y", at=base + sgn * (1.0 * k + 2 * gap),
                            size=1.9 if scale >= 100 else 2.3)
            v.dim_chain([miny, maxy], 0, axis="y", at=base + sgn * (1.0 * k + 3 * gap), size=2.1 if scale >= 100 else 2.6)


def scan_dims(v: View, level, axis, c, a0, a1, scale, size=None):
    """internal dimension chain along a scan line: faces of cut walls crossing it."""
    pts = set()
    for w in M.WALLS:
        if w.level != level or not is_cut(w, level):
            continue
        if axis == "x" and not w.horiz and w.a0 - 1e-6 <= c <= w.a1 + 1e-6 and a0 <= w.c <= a1:
            # skip if scan line passes through an opening in that wall
            if any(o.pos <= c <= o.end for o in w.openings):
                continue
            pts.add(round(w.c - w.t / 2, 3))
            pts.add(round(w.c + w.t / 2, 3))
        if axis == "y" and w.horiz and w.a0 - 1e-6 <= c <= w.a1 + 1e-6 and a0 <= w.c <= a1:
            if any(o.pos <= c <= o.end for o in w.openings):
                continue
            pts.add(round(w.c - w.t / 2, 3))
            pts.add(round(w.c + w.t / 2, 3))
    pts = sorted(p for p in pts if a0 - 0.2 <= p <= a1 + 0.2)
    if len(pts) >= 2:
        v.dim_chain(pts, 0, axis=axis, at=c, size=size or (1.7 if scale >= 100 else 2.1), lw="xxs")


def grid_lines(v: View, level, scale, ext=(1.6, 1.6)):
    ex0, ey0, ex1, ey1 = plan_extent(level)
    k = scale / 100
    gap = 0.75 * k * (1.0 if scale >= 100 else 1.6)
    y_lo = ey0 - (1.0 * k + 3 * gap) - 1.1 * k - 0.6
    x_lo = ex0 - (1.0 * k + 3 * gap) - 1.1 * k - 0.6
    y_hi = ey1 + 0.6
    x_hi = ex1 + 0.6
    for name, x in M.GRID_X:
        v.line(x, y_lo + 0.35 * k * 3, x, y_hi, lw="xxs", color="#b03030", dash="6 1 1 1")
        grid_bubble(v, x, y_lo, name, r=2.6 if scale >= 100 else 3.2)
    for name, y in M.GRID_Y:
        if level in ("B", "G", "R") and y < 20 and level != "R":
            continue
        v.line(x_lo + 0.35 * k * 3, y, x_hi, y, lw="xxs", color="#b03030", dash="6 1 1 1")
        grid_bubble(v, x_lo, y, name, r=2.6 if scale >= 100 else 3.2)


def plan_extent(level):
    xs = [p[0] for p in M.OUTLINES[level]]
    ys = [p[1] for p in M.OUTLINES[level]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if level in ("B", "G"):
        y0 = min(y0, 16.0)
        y1 = max(y1, M.COURT_N[3] + 0.3)
        x1 = max(x1, 27.7 if level == "G" else x1)
    if level == "U":
        y0 = min(y0, 16.0)
    if level == "R":
        x0, x1, y0, y1 = 6.0, 25.0, 16.0, 32.0
    return x0, y0, x1, y1


def section_marks(v: View, level, which=("A", "B", "C"), scale=100):
    x0, y0, x1, y1 = plan_extent(level)
    m = 2.2 * scale / 100 + (1.2 if scale < 100 else 0)
    for key in which:
        s = SECTIONS[key]
        if s["axis"] == "x":   # cut along x, looking north (+y) -> paper up
            section_marker(v, x0 - m, s["c"], x1 + m * 0.6, s["c"], key, look=1)
        else:                  # cut along y; look west(-1) / east(+1)
            # line drawn bottom->top on paper; left normal = west
            section_marker(v, s["c"], y0 - m, s["c"], y1 + m * 0.6, key, look=1 if s["look"] < 0 else -1)


def draw_overheads(v: View, level):
    """dashed outlines of elements above (cantilever, canopy, pergolas)."""
    if level == "G":
        from shapely.geometry import Polygon as P
        up = P(M.OUTLINES["U"])
        g = P(M.OUTLINES["G"])
        d = up.difference(g)
        for p in polys(d):
            v.polygon(ring_pts(p), fill="none", lw="xs", dash="3 1.5", color="#333")
        for s in M.SLABS:
            if s.kind == "canopy":
                for r in s.rects:
                    v.rect(*r, fill="none", lw="xs", dash="3 1.5", color="#333")
        for p in M.PERGOLAS:
            if p["z"] < 4:
                v.rect(p["x0"], p["y0"], p["x1"], p["y1"], fill="none", lw="xxs", dash="2 1", color="#555")


def draw_terraces(v: View, level, scale):
    """outdoor surfaces adjacent to the plan (GF deck/patio; UF terrace; roof)."""
    if level == "G":
        # covered terrace deck + BBQ + deck bridge
        v.rect(M.X_W, M.Y_S_U, M.X_M, M.Y_S_G, fill="pat:deckv", lw="xs")
        v.rect(13.0, 19.6, M.PATIO[2] + 0.3, M.Y_S_G, fill="pat:deckv", lw="xs")
        v.rect(21.80, 16.80, 25.0, 21.0, fill="pat:paving", lw="xs")
        # patio void
        v.rect(M.PATIO[0], M.PATIO[1], M.PATIO[2], 19.6, fill="#f6f3ee", lw="xs")
        v.line(M.PATIO[0], M.PATIO[1], M.PATIO[2], 19.6, lw="xxs", color="#999")
        v.line(M.PATIO[0], 19.6, M.PATIO[2], M.PATIO[1], lw="xxs", color="#999")
        v.text((M.PATIO[0] + M.PATIO[2]) / 2, 18.1, "חלל פטיו שקוע", size=2.0 if scale >= 100 else 2.6, weight=500)
        v.level_mark(M.PATIO[0] + 0.5, 17.5, M.LV["B"] - 0.02, size=1.8 if scale >= 100 else 2.2, plan=True)
        # pool edge (partial)
        # English court void (north)
        cx0, cy0, cx1, cy1 = M.COURT_N
        v.rect(cx0, cy0, cx1, cy1, fill="#f6f3ee", lw="xs")
        v.line(cx0, cy0, cx1, cy1, lw="xxs", color="#999")
        v.line(cx0, cy1, cx1, cy0, lw="xxs", color="#999")
        v.text((cx0 + cx1) / 2, cy1 + 0.35, "חצר אנגלית – חלל", size=1.9 if scale >= 100 else 2.4)
        # entrance path & canopy
        v.rect(M.X_E, 28.8, M.X_E + 2.6, 30.8, fill="pat:paving", lw="xs")
    if level == "U":
        v.rect(M.X_M, M.Y_S_G + 0.2, M.X_E - 0.2, M.Y_NB, fill="pat:deckv", lw="xs")
        # planter strip along south parapet
        v.rect(M.X_M + 0.05, M.Y_S_G + 0.2, M.X_E - 0.2, M.Y_S_G + 0.8, fill="pat:planting", lw="xxs")
        v.rect(M.X_W + 0.3, M.Y_S_U + 0.3, M.X_M - 0.3, M.LOGGIA - 0.1, fill="pat:deckv", lw="xxs")
    if level == "R":
        # roof surfaces
        v.rect(M.X_W + 0.2, M.Y_S_U + 0.2, M.X_M - 0.2, M.Y_N - 0.2, fill="#efede8", lw="xxs")
        v.rect(M.X_M - 0.2, M.Y_NB + 0.2, 12.9, M.Y_N - 0.2, fill="#efede8", lw="xxs")
        v.rect(17.8, M.Y_NB + 0.2, M.X_E - 0.2, M.Y_N - 0.2, fill="pat:deckv", lw="xs")
        v.rect(12.9, M.Y_NB + 0.2, 17.8, 27.0, fill="#efede8", lw="xxs")
        # PV array on west-bar roof
        x = M.X_W + 0.7
        while x + 1.05 <= M.X_M - 0.6:
            y = M.Y_S_U + 0.8
            while y + 1.75 <= 26.2:
                v.rect(x, y, x + 1.05, y + 1.75, fill="pat:pv", lw="xxs")
                y += 1.85
            x += 1.15
        # HVAC units in screened area
        for i in range(3):
            v.rect(M.X_W + 0.8 + i * 1.6, 27.4, M.X_W + 2.0 + i * 1.6, 28.2, fill="#ddd", lw="xs")
        v.rect(M.X_W + 0.5, 27.1, M.X_W + 5.6, 28.5, fill="none", lw="xxs", dash="2 1")
        v.text(M.X_W + 3.05, 29.1, "מעבים – מסתור אקוסטי", size=1.8 if scale >= 100 else 2.2)
        v.text(9.5, 25.9, 'מערכת פוטו-וולטאית ~15 קוט"ש', size=1.9 if scale >= 100 else 2.4, weight=500)
        # slopes
        for (x, y) in [(9.5, 20.0), (21.0, 28.0)]:
            pass


def plan(v: View, level, scale=100, dims=True, grid=True, sections=True, terraces=True, furniture=True):
    if terraces:
        draw_terraces(v, level, scale)
    if furniture:
        draw_furniture(v, level, scale)
    draw_stairs(v, level, scale)
    draw_patio_stair(v, level, scale)
    draw_walls(v, level, scale)
    if level in ("B", "G", "U"):
        draw_risers(v, level, scale)
    draw_openings(v, level, scale)
    draw_overheads(v, level)
    draw_room_tags(v, level, scale)
    draw_level_marks(v, level, scale)
    if grid:
        grid_lines(v, level, scale)
    if dims:
        ext_dims(v, level, scale, extra_x=[g[1] for g in M.GRID_X] if False else (), extra_y=())
    if sections:
        section_marks(v, level, scale=scale)


def _view(sh, ox, oy, scale, key):
    doc = DXF_DOCS.get(key)
    if doc is None:
        doc = new_dxf()
        DXF_DOCS[key] = doc
    return View(sh, ox, oy, scale, dxf=doc.modelspace())


def save_dxf(key):
    import os
    doc = DXF_DOCS.get(key)
    if doc is None:
        return
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "dxf")
    os.makedirs(d, exist_ok=True)
    doc.saveas(os.path.join(d, f"{key}.dxf"))


# ----------------------------------------------------------------------------- sheets
def _place(box, bx0, by0, bx1, by1, scale, cx, cy):
    """paper origin so that model bbox centre lands at (cx, cy)."""
    k = 1000 / scale
    ox = cx - (bx0 + bx1) / 2 * k
    oy = cy + (by0 + by1) / 2 * k
    return ox, oy


def sheet_plans_bg(sh, box):
    x, y, w, h = box
    sc = 100
    # basement (left) & ground (right)  — Hebrew sheets read right-to-left: ground on the right
    for i, (lvl, title) in enumerate([("G", "תכנית קומת קרקע"), ("B", "תכנית קומת מרתף")]):
        cx = x + w * (0.75 if i == 0 else 0.27)
        cy = y + h * 0.46
        ox, oy = _place(box, 6, 13.5, 25, 32, sc, cx, cy)
        v = _view(sh, ox, oy, sc, f"plan_{lvl}_100")
        plan(v, lvl, sc, terraces=(lvl == "G"))
        drawing_title(sh, cx + 70, y + h - 40, title, 'קנ"מ 1:100', width=80)
        room_table(sh, cx + 72, y + h * 0.70, lvl)
        save_dxf(f"plan_{lvl}_100")
    north_arrow(sh, x + w - 18, y + 22, r=8)
    scale_bar(sh, x + 14, y + h - 14, 100, 10)


def sheet_plans_ur(sh, box):
    x, y, w, h = box
    sc = 100
    for i, (lvl, title) in enumerate([("U", "תכנית קומה א'"), ("R", "תכנית גג")]):
        cx = x + w * (0.75 if i == 0 else 0.27)
        cy = y + h * 0.46
        ox, oy = _place(box, 6, 13.5, 25, 32, sc, cx, cy)
        v = _view(sh, ox, oy, sc, f"plan_{lvl}_100")
        if lvl == "R":
            # show UF outline below for reference
            plan(v, "R", sc, sections=True)
            roof_notes(v, sc)
        else:
            plan(v, lvl, sc)
        drawing_title(sh, cx + 70, y + h - 40, title, 'קנ"מ 1:100', width=80)
        room_table(sh, cx + 72, y + h * 0.70, lvl)
        save_dxf(f"plan_{lvl}_100")
    north_arrow(sh, x + w - 18, y + 22, r=8)
    scale_bar(sh, x + 14, y + h - 14, 100, 10)


def roof_notes(v: View, sc):
    # parapets drawn as cut walls (level R). Add slope arrows & levels
    for (x0, y0, x1, y1, val) in [(9.5, 22.0, 9.5, 18.5, None), (21.0, 28.5, 21.0, 26.0, None)]:
        pass
    v.level_mark(7.0, 17.0, M.LV["R"] + 0.05, size=1.8, plan=True)
    v.level_mark(18.5, 26.0, M.LV["R"] + 0.10, size=1.8, plan=True)
    v.level_mark(13.6, 27.6, M.LV["RX"] + 0.20, size=1.8, plan=True)
    # roof exit roof outline (above) – dashed
    v.text(15.3, 31.2, 'גג יציאה +10.00', size=1.7, color="#444")
    # drainage points
    for (x, y) in [(6.7, 16.7), (12.3, 16.7), (24.3, 25.7), (6.7, 31.3)]:
        v.circle(x, y, 0.12, lw="xs")
    v.text(9.5, 17.0, "שיפוע 1.5% לנקזים", size=1.6, color="#444")


def sheet_ground_50(sh, box):
    x, y, w, h = box
    sc = 50
    cx, cy = x + w * 0.50, y + h * 0.47
    ox, oy = _place(box, 6, 15.5, 25, 32, sc, cx, cy)
    v = _view(sh, ox, oy, sc, "plan_G_50")
    plan(v, "G", sc)
    for (yy) in (23.3, 28.9):
        scan_dims(v, "G", "x", yy, 6.0, 25.0, sc)
    for (xx) in (9.0, 21.9):
        scan_dims(v, "G", "y", xx, 21.0, 32.0, sc)
    drawing_title(sh, x + w - 20, y + h - 30, "תכנית קומת קרקע", 'קנ"מ 1:50', width=95, size=9)
    north_arrow(sh, x + w - 22, y + 24, r=9)
    scale_bar(sh, x + 16, y + h - 16, 50, 5)
    notes_block(sh, x + 8, y + 8)
    save_dxf("plan_G_50")


def sheet_upper_50(sh, box):
    x, y, w, h = box
    sc = 50
    cx, cy = x + w * 0.50, y + h * 0.50
    ox, oy = _place(box, 6, 15.0, 25, 32, sc, cx, cy)
    v = _view(sh, ox, oy, sc, "plan_U_50")
    plan(v, "U", sc)
    for (yy) in (19.5, 23.5, 28.0, 30.8):
        scan_dims(v, "U", "x", yy, 6.0, 25.0, sc)
    for (xx) in (8.0, 22.0):
        scan_dims(v, "U", "y", xx, 16.0, 32.0, sc)
    drawing_title(sh, x + w - 20, y + h - 30, "תכנית קומה א'", 'קנ"מ 1:50', width=95, size=9)
    north_arrow(sh, x + w - 22, y + 24, r=9)
    scale_bar(sh, x + 16, y + h - 16, 50, 5)
    notes_block(sh, x + 8, y + 8, upper=True)
    save_dxf("plan_U_50")


def notes_block(sh, x, y, upper=False):
    lines = [
        "הערות כלליות:",
        "1. המידות בס\"מ, המפלסים במטרים. ±0.00 = +18.50 מעל פני הים.",
        "2. קירות חוץ: בלוק בטון 20 + בידוד צמר סלעים 5 + חיפוי אבן/טיח תרמי.",
        "3. קירות פנים: בלוק 10 מטויח / גבס דו-צדדי לפי סימון.",
        "4. כל מידות הפתחים לבדיקה ואישור בשטח לפני ייצור.",
        "5. ממ\"ד לפי הנחיות פיקוד העורף – קירות ותקרה בטון מזוין 30.",
        "6. אלומיניום: פרופיל תרמי, צבע תנור דרגת ים, זיגוג בידודי Low-E.",
    ]
    for i, t in enumerate(lines):
        sh.text(x + 120, y + 4 + i * 4.4, t, size=2.6 if i else 3.0, anchor="right", weight=700 if i == 0 else 400)


def room_table(sh, x_right, y, level, width=150):
    from siteplan import table
    rows = []
    for r in M.ROOMS:
        if r.level != level:
            continue
        a = unary_union([sbox(*q) for q in r.rects]).area
        rows.append([r.no, r.name, f"{a:.1f}", r.floor, "—" if r.outdoor else f"{r.ceil:.2f}"])
    tot = sum(float(rw[2]) for rw in rows if rw[4] != "—")
    rows.append(["", 'סה"כ פנים (נטו)', f"{tot:.1f}", "", ""])
    table(sh, x_right, y, ["מס'", "חלל", 'שטח מ"ר', "ריצוף", "ג. תקרה"], rows, [12, 46, 18, 50, 18],
          title=f"טבלת חללים – {M.LEVEL_NAMES[level]}", row_h=5.2, size=2.3, bold_last=True)
