"""Elevations & sections by orthographic projection of the 3-D box model.

Painter's algorithm over parallel faces is exact for axis-aligned boxes, so the
drawings are consistent with the plans and the renders by construction.
"""
from __future__ import annotations

import math

from shapely.geometry import box as sbox, Polygon, MultiPolygon
from shapely.ops import unary_union

import model as M
import geom
from draw import View, drawing_title, grid_bubble, scale_bar, new_dxf
from plans import SECTIONS, polys, ring_pts, DXF_DOCS, save_dxf

# ----------------------------------------------------------------------------- materials
EL_FILL = {
    "stone": "#e8d9bd", "plaster": "#fbfaf6", "white": "#fbfaf6", "rc": "#d9d6d0", "rc_fair": "#d6d3cc",
    "block": "#efefef", "glass": "#b9cdd4", "glass_frosted": "#d5dfe2", "frame": "#4a4540", "alu_wood": "#b07a4a",
    "wood": "#c79a6b", "wood_dark": "#6b4a32", "steel": "#6f6f6f", "deck": "#c49a6c", "paving": "#e3ded4",
    "floor": "#e6e1d8", "roofing": "#cfcac0", "furn": "#e9e4dc", "fabric": "#d8cfc2", "fabric_dark": "#8d8378",
    "furn_dark": "#6b5a4a", "stone_white": "#f1ede6", "car": "#cfd5da", "car_glass": "#7d8c96", "water": "#9cc9d6",
    "grass": "#cfdcb9", "planting": "#b9cc9a", "asphalt": "#77777a", "pv": "#3f4f68",
}
CUT_FILL_100 = {"water": "#a9d3df", "stone_white": "#f1ede6", "paving": "#e3ded4", "rc": "#2b2b2b", "rc_fair": "#2b2b2b", "block": "pat:block", "stone": "pat:stone", "plaster": "#ffffff",
                "white": "pat:partition", "floor": "#ffffff", "roofing": "pat:insul", "glass": "#bcd3db", "frame": "#333",
                "deck": "pat:wood", "wood": "pat:wood", "steel": "#333", "alu_wood": "#7a5534"}
CUT_FILL_50 = dict(CUT_FILL_100, rc="pat:concrete", rc_fair="pat:concrete", floor="pat:screed", plaster="#ffffff")

SKIP_CLS_ELEV = {"site"}


def view_spec(kind, c=None):
    """Returns (keep(b), cut(b), depth(b), h(b)->(h0,h1), flip)."""
    if kind == "S":
        return dict(keep=lambda b: True, cut=lambda b: False, depth=lambda b: b["y0"], h=lambda b: (b["x0"], b["x1"]))
    if kind == "N":
        return dict(keep=lambda b: True, cut=lambda b: False, depth=lambda b: -b["y1"], h=lambda b: (-b["x1"], -b["x0"]))
    if kind == "E":
        return dict(keep=lambda b: True, cut=lambda b: False, depth=lambda b: -b["x1"], h=lambda b: (b["y0"], b["y1"]))
    if kind == "W":
        return dict(keep=lambda b: True, cut=lambda b: False, depth=lambda b: b["x0"], h=lambda b: (-b["y1"], -b["y0"]))
    if kind == "secN":   # cut at y=c looking north
        return dict(keep=lambda b: b["y1"] > c + 1e-6, cut=lambda b: b["y0"] < c - 1e-6 < b["y1"],
                    depth=lambda b: max(b["y0"], c), h=lambda b: (b["x0"], b["x1"]))
    if kind == "secW":   # cut at x=c looking west (viewer east): left = south
        return dict(keep=lambda b: b["x0"] < c - 1e-6, cut=lambda b: b["x0"] < c - 1e-6 < b["x1"],
                    depth=lambda b: -min(b["x1"], c), h=lambda b: (b["y0"], b["y1"]))
    if kind == "secE":   # cut at x=c looking east (viewer west): left = north
        return dict(keep=lambda b: b["x1"] > c + 1e-6, cut=lambda b: b["x0"] < c - 1e-6 < b["x1"],
                    depth=lambda b: max(b["x0"], c), h=lambda b: (-b["y1"], -b["y0"]))
    raise ValueError(kind)


def _hrange(kind):
    if kind in ("S", "secN"):
        return M.LOT["x0"] - 2, M.LOT["x1"] + 4
    if kind == "N":
        return -(M.LOT["x1"] + 4), -(M.LOT["x0"] - 2)
    if kind in ("E", "secW"):
        return M.LOT["y0"] - 1, M.LOT["y1"] + 1
    return -(M.LOT["y1"] + 1), -(M.LOT["y0"] - 1)


def stone_pattern(v: View, pid):
    """stone joints 120×60 cm aligned to model origin."""
    k = v.k
    w, h = 1.2 * k, 0.6 * k
    x0, y0 = v.P(0, 0)
    pat = (f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="{w:.3f}" height="{2 * h:.3f}" '
           f'x="{x0:.3f}" y="{y0:.3f}"><rect width="{w:.3f}" height="{2 * h:.3f}" fill="{EL_FILL["stone"]}"/>'
           f'<path d="M0,0 H{w:.3f} M0,{h:.3f} H{w:.3f} M0,0 V{h:.3f} M{w / 2:.3f},{h:.3f} V{2 * h:.3f}" '
           f'stroke="#b9a684" stroke-width="0.07" fill="none"/></pattern>')
    v.sh.defs_extra.append(pat)
    return f"url(#{pid})"


def louvre_pattern(v: View, pid):
    k = v.k
    w = 0.18 * k
    pat = (f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="{w:.3f}" height="10">'
           f'<rect width="{w:.3f}" height="10" fill="#c48d5c"/><rect width="{0.05 * k:.3f}" height="10" fill="#8f6038"/></pattern>')
    v.sh.defs_extra.append(pat)
    return f"url(#{pid})"


_pid = [0]


def project(v: View, kind, c=None, scale=100, boxes=None, beyond_fade=True, depth_limit=None, zclip=None):
    spec = view_spec(kind, c)
    bx = boxes if boxes is not None else geom.all_boxes(include_site=True, include_furn=True)
    faces = []
    cuts = []
    casters = []
    elev_view = kind in ("S", "N", "E", "W")
    for b in bx:
        if b["cls"] == "fence":
            continue
        if b["cls"] == "site" and (elev_view or b["mat"] in ("grass", "planting", "asphalt")):
            continue
        if b["cls"] == "site" and b["x0"] < M.LOT["x0"] - 1:
            continue
        if not spec["keep"](b):
            continue
        h0, h1 = spec["h"](b)
        z0, z1 = b["z0"], b["z1"]
        if elev_view:
            if z1 <= M.GARDEN + 1e-6:
                continue
            z0 = max(z0, M.GARDEN)
        if h1 - h0 < 1e-4 or z1 - z0 < 1e-4:
            continue
        if zclip and (z1 < zclip[0] or z0 > zclip[1]):
            continue
        d = spec["depth"](b)
        if depth_limit is not None and d > depth_limit:
            continue
        rec = (round(d, 3), b["mat"], b["cls"], h0, h1, z0, z1)
        if elev_view and b["cls"] not in ("site", "car") and not b["mat"].startswith("glass"):
            casters.append((d, far_depth(kind, b), h0, h1, z0, z1))
        if spec["cut"](b):
            cuts.append(rec)
        else:
            faces.append(rec)
    # group faces by (depth, mat)
    groups = {}
    for (d, mat, cls, h0, h1, z0, z1) in faces:
        key = (d, mat, "fin" if cls == "fin" else ("glass" if mat.startswith("glass") else "x"))
        groups.setdefault(key, []).append(sbox(h0, z0, h1, z1))
    order = sorted(groups.items(), key=lambda kv: -kv[0][0])
    _pid[0] += 1
    stone_url = stone_pattern(v, f"stj{_pid[0]}")
    louv_url = louvre_pattern(v, f"lvr{_pid[0]}")
    dmin = min((k[0] for k, _ in order), default=0)
    dmax = max((k[0] for k, _ in order), default=1)
    is_section = kind.startswith("sec")
    for (d, mat, g), rects in order:
        u = unary_union(rects)
        fill = EL_FILL.get(mat, "#eee")
        if mat == "stone":
            fill = stone_url
        if mat == "alu_wood" and g == "fin":
            fill = EL_FILL["alu_wood"]
        rel = (d - dmin) / max(1e-6, dmax - dmin)
        far = is_section and beyond_fade
        stroke = "#1d1d1d" if not far else "#555"
        lw = 0.13 if mat not in ("glass", "glass_frosted") else 0.09
        if mat in ("frame",):
            lw = 0.09
        op = None
        if mat.startswith("glass"):
            op = 0.82
        shadow = None
        if elev_view and casters and mat not in ("water",) and g != "glassx":
            shadow = cast_shadow(u, d, casters)
        for p in polys(u):
            pts = [[v.P(x, y) for x, y in ring] for ring in ring_pts(p)]
            dd = " ".join("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in r) + " Z" for r in pts)
            extra = f' fill-opacity="{op}"' if op else ""
            v.sh.add(f'<path d="{dd}" fill="{fill}" fill-rule="evenodd" stroke="{stroke}" stroke-width="{lw}"{extra}/>')
            if v.dxf is not None:
                for r in ring_pts(p):
                    v.dxf.add_lwpolyline([(x, y) for x, y in r], close=True, dxfattribs={"layer": "A-THIN"})
            if mat.startswith("glass") and not is_section and (p.bounds[2] - p.bounds[0]) > 0.4:
                # reflection strokes
                x0, z0, x1, z1 = p.bounds
                for t in (0.22, 0.30, 0.62):
                    a = x0 + (x1 - x0) * t
                    hh = min(1.2, z1 - z0) * 0.6
                    if a + hh * 0.6 < x1:
                        v.sh.line(*v.P(a, z0 + (z1 - z0) * 0.25), *v.P(a + hh * 0.6, z0 + (z1 - z0) * 0.25 + hh),
                                  lw=0.09, color="#ffffff")
            pass
        if shadow is not None and not shadow.is_empty:
            for sp in polys(shadow):
                if sp.area < 1e-4:
                    continue
                v.polygon(ring_pts(sp), fill="#1b1b1b", color="none", fop=0.17)
    # cut faces
    if cuts:
        cf = CUT_FILL_50 if scale <= 50 else CUT_FILL_100
        cg = {}
        for (d, mat, cls, h0, h1, z0, z1) in cuts:
            if cls in ("furn", "car"):
                continue
            cg.setdefault(mat, []).append(sbox(h0, z0, h1, z1))
        allc = []
        for mat, rects in cg.items():
            u = unary_union(rects)
            for p in polys(u):
                v.polygon(ring_pts(p), fill=cf.get(mat, "#2b2b2b"), color="#000", lw=0.09)
                if mat not in ("glass", "frame", "steel"):
                    allc.append(p)
        U = unary_union(allc)
        for p in polys(U):
            v.polygon(ring_pts(p), fill="none", lw="xl" if scale >= 100 else "xxl")
        bb = [p for p in polys(U) if p.bounds[3] > M.GARDEN]
        if bb:
            v.cut_bounds = unary_union(bb).bounds


def far_depth(kind, b):
    return {"S": b["y1"], "N": -b["y0"], "E": -b["x0"], "W": b["x1"]}[kind]


def cast_shadow(face_poly, d, casters, max_dist=7.0):
    """45° shadows (sun upper-left, in front) cast onto a face plane at depth d."""
    from shapely.geometry import MultiPoint
    fb = face_poly.bounds
    shapes = []
    for (dn, df, h0, h1, z0, z1) in casters:
        if dn >= d - 1e-3 or d - dn > max_dist:
            continue
        s2 = d - dn
        s1 = d - min(df, d)
        # quick reject: shifted bbox vs face bbox
        if h1 + s2 < fb[0] or h0 + s1 > fb[2] or z1 - s1 < fb[1] or z0 - s2 > fb[3]:
            continue
        pts = [(h0 + s, z + 0) for s in (s1, s2) for z in ()]
        corners = []
        for s in (s1, s2):
            corners += [(h0 + s, z0 - s), (h1 + s, z0 - s), (h1 + s, z1 - s), (h0 + s, z1 - s)]
        shapes.append(MultiPoint(corners).convex_hull)
    if not shapes:
        return None
    sh = unary_union(shapes)
    return sh.intersection(face_poly)


# ----------------------------------------------------------------------------- ground / soil
EXCAV = [  # (x0,y0,x1,y1,z0,z1) volumes without soil
    (M.X_W - 0.35, M.Y_S_G - 0.35, M.X_E + 0.35, M.Y_N + 0.35, M.slab_top("B") - M.RAFT, 5),
    (M.PATIO[0] - 0.3, M.PATIO[1] - 0.3, M.PATIO[2] + 0.3, M.Y_S_G, M.LV["B"] - 0.4, 5),
    (M.POOL["x0"], M.POOL["y0"], M.POOL["x1"], M.POOL["y1"], M.POOL["water"] - M.POOL["depth"] - 0.3, 5),
]


def ground(v: View, kind, c=None, scale=100, depth=5.5):
    h0, h1 = _hrange(kind)
    g = M.GARDEN
    soil = sbox(h0, g - depth, h1, g)
    if kind.startswith("sec"):
        spec = view_spec(kind, c)
        holes = []
        for (x0, y0, x1, y1, z0, z1) in EXCAV:
            b = dict(x0=x0, y0=y0, x1=x1, y1=y1, z0=z0, z1=z1)
            if spec["cut"](b):
                a, bb = spec["h"](b)
                holes.append(sbox(a, z0, bb, z1))
        if holes:
            soil = soil.difference(unary_union(holes))
    else:
        soil = sbox(h0, g - 0.9, h1, g)
    # street side lower
    for p in polys(soil):
        v.polygon(ring_pts(p), fill="pat:earth", color="none")
    v.line(h0, g, h1, g, lw="xl" if scale >= 100 else "xxl")


def tree_sprite(v: View, h, z0, r, kind, sh_color="#5e6f45"):
    """stylised tree in elevation (transparent line art)."""
    if kind == "palm":
        top = z0 + 7.5
        v.line(h, z0, h + 0.15, top, lw="s", color=sh_color)
        for a in range(-80, 260, 30):
            ang = math.radians(a)
            ex, ez = h + 0.15 + 2.2 * math.cos(ang), top + 0.9 * math.sin(ang) - 0.6
            mx, mz = h + 0.15 + 1.2 * math.cos(ang), top + 0.8
            v.sh.path(f"M{v.P(h + 0.15, top)[0]:.2f},{v.P(h + 0.15, top)[1]:.2f} "
                      f"Q{v.P(mx, mz)[0]:.2f},{v.P(mx, mz)[1]:.2f} {v.P(ex, ez)[0]:.2f},{v.P(ex, ez)[1]:.2f}",
                      lw="xs", color=sh_color)
        return
    H = 3.2 + r * 0.9 if kind != "olive_s" else 3.0
    v.line(h, z0, h - 0.1, z0 + H * 0.45, lw="s", color=sh_color)
    v.line(h - 0.1, z0 + H * 0.45, h - 0.6, z0 + H * 0.7, lw="xs", color=sh_color)
    v.line(h - 0.1, z0 + H * 0.45, h + 0.5, z0 + H * 0.75, lw="xs", color=sh_color)
    import random
    rnd = random.Random(int(h * 100) + int(r * 10))
    cx, cz = h, z0 + H * 0.75
    for i in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(0.2, 0.6) * r
        px, pz = cx + math.cos(a) * rr, cz + math.sin(a) * rr * 0.55
        v.circle(px, pz, r * rnd.uniform(0.35, 0.55), lw="xxs", color=sh_color, fill="#9fb07f", fop=0.18)


def person(v: View, h, z0, scale=1.0, color="#444"):
    H = 1.75 * scale
    v.circle(h, z0 + H - 0.12, 0.11, lw="xxs", color=color, fill=color)
    v.sh.path("M" + " L".join(f"{v.P(x, y)[0]:.2f},{v.P(x, y)[1]:.2f}" for x, y in [
        (h - 0.2, z0 + H - 0.28), (h + 0.2, z0 + H - 0.28), (h + 0.17, z0 + H * 0.5), (h + 0.12, z0),
        (h + 0.03, z0), (h, z0 + H * 0.45), (h - 0.03, z0), (h - 0.12, z0), (h - 0.17, z0 + H * 0.5)]) + " Z",
        lw="xxs", color=color, fill=color, fop=0.55)


def people(v: View, kind):
    pts = {"S": [10.5, 17.2], "W": [-19.0], "E": [27.2], "N": []}.get(kind, [])
    for i, h in enumerate(pts):
        person(v, h, M.GARDEN, scale=0.98 + 0.04 * i)


def trees_in_view(v: View, kind, c=None, front_only=True):
    spec = view_spec(kind, c)
    for (x, y, r, k) in M.SITE["trees"]:
        b = dict(x0=x - 0.1, x1=x + 0.1, y0=y - 0.1, y1=y + 0.1, z0=0, z1=1)
        if not spec["keep"](b):
            continue
        h0, h1 = spec["h"](b)
        tree_sprite(v, (h0 + h1) / 2, M.GARDEN, r, k)


# ----------------------------------------------------------------------------- annotation
LEVELS = [(M.LV["B"], "קומת מרתף"), (0.0, "קומת קרקע"), (M.LV["U"], "קומה א'"), (M.LV["R"], "גג"),
          (M.LV["RX"] + 0.20, "גג יציאה")]
LEVELS_50 = [(M.LV["B"], "קומת מרתף"), (0.0, "קומת קרקע"), (M.LV["U"], "קומה א'"), (M.LV["R"], "גג"),
             (M.LV["R"] + 0.50, "ראש מעקה"), (M.LV["RX"] + 0.20, "גג יציאה")]


def level_column(v: View, hpos, side="left", levels=None, scale=100):
    lv = levels or LEVELS
    for z, name in lv:
        px, py = v.P(hpos, z)
        sh = v.sh
        t = 1.4 if scale >= 100 else 1.7
        sh.path(f"M{px},{py} L{px - t},{py - t * 1.3} L{px + t},{py - t * 1.3} Z", lw="xs", fill="#000")
        sh.line(px - 9, py, px + 9, py, lw="xxs")
        val = "±0.00" if abs(z) < 1e-6 else f"{z:+.2f}"
        sz = 2.0 if scale >= 100 else 2.5
        if side == "left":
            sh.text(px - 2.5, py - t * 1.7, val, size=sz, anchor="right", weight=600)
            sh.text(px - 2.5, py + sz + 0.4, name, size=sz * 0.85, anchor="right", color="#444")
        else:
            sh.text(px + 2.5, py - t * 1.7, val, size=sz, anchor="left", weight=600)
            sh.text(px + 2.5, py + sz + 0.4, name, size=sz * 0.85, anchor="left", color="#444")
    # extension lines faint
    return


def boundary_lines(v: View, kind, z_top=11.0, scale=100):
    """vertical lines: lot boundary (blue) & building lines (red) with labels."""
    L = M.LOT
    E = M.ENVELOPE
    if kind in ("S", "secN"):
        items = [(L["x0"], "גבול מגרש", "#2b4fa8"), (E[0], "קו בניין", "#c0392b"), (E[2], "קו בניין", "#c0392b"),
                 (L["x1"], "גבול מגרש", "#2b4fa8")]
    elif kind == "N":
        items = [(-L["x1"], "גבול מגרש", "#2b4fa8"), (-E[2], "קו בניין", "#c0392b"), (-E[0], "קו בניין", "#c0392b"),
                 (-L["x0"], "גבול מגרש", "#2b4fa8")]
    elif kind in ("E", "secW"):
        items = [(L["y0"], "גבול מגרש", "#2b4fa8"), (E[1], "קו בניין", "#c0392b"), (E[3], "קו בניין", "#c0392b"),
                 (L["y1"], "גבול מגרש", "#2b4fa8")]
    else:
        items = [(-L["y1"], "גבול מגרש", "#2b4fa8"), (-E[3], "קו בניין", "#c0392b"), (-E[1], "קו בניין", "#c0392b"),
                 (-L["y0"], "גבול מגרש", "#2b4fa8")]
    for h, label, col in items:
        v.line(h, M.GARDEN - 0.5, h, z_top, lw="xs", color=col, dash="5 1.2 1 1.2")
        px, py = v.P(h, z_top)
        v.sh.text(px, py - 1.5, label, size=2.0 if scale >= 100 else 2.4, color=col, weight=500)


def grid_marks(v: View, kind, z, scale=100):
    if kind in ("S", "secN"):
        items = [(n, x) for n, x in M.GRID_X]
    elif kind == "N":
        items = [(n, -x) for n, x in M.GRID_X]
    elif kind in ("E", "secW"):
        items = [(n, y) for n, y in M.GRID_Y]
    else:
        items = [(n, -y) for n, y in M.GRID_Y]
    for n, h in items:
        v.line(h, z + 0.35 * scale / 100 * 1.0 + 0.2, h, z + 1.2, lw="xxs", color="#b03030", dash="4 1 1 1")
        grid_bubble(v, h, z, n, r=2.4 if scale >= 100 else 3.0)


def height_dims(v: View, hpos, zs, scale=100):
    v.dim_chain(zs, 0, axis="y", at=hpos, size=1.9 if scale >= 100 else 2.3)


def callouts(v: View, items, scale=50, side="right", hx=None):
    """material call-outs: list of (h, z, text) → leader to a text column."""
    sz = 2.3 if scale <= 50 else 1.9
    items = sorted(items, key=lambda t: -t[1])
    lasty = None
    for (h, z, text) in items:
        px, py = v.P(h, z)
        tx = v.P(hx, 0)[0]
        ty = py
        if lasty is not None and ty < lasty + sz * 1.6:
            ty = lasty + sz * 1.6
        lasty = ty
        v.sh.circle(px, py, 0.45, lw="xxs", fill="#000")
        v.sh.polyline([(px, py), (tx + (-3 if side == "right" else 3), ty), (tx, ty)], lw="xxs")
        v.sh.text(tx + (1 if side == "right" else -1), ty + sz * 0.35, text, size=sz, anchor="left" if side == "right" else "right")


# ----------------------------------------------------------------------------- drawings
ELEV_TITLES = {"S": "חזית דרומית", "N": "חזית צפונית", "E": "חזית מזרחית", "W": "חזית מערבית"}


def elevation(sh, kind, ox, oy, scale, key, notes=False):
    doc = DXF_DOCS.setdefault(key, new_dxf())
    v = View(sh, ox, oy, scale, dxf=doc.modelspace())
    ground(v, kind, scale=scale)
    trees_in_view(v, kind)
    project(v, kind, scale=scale)
    people(v, kind)
    h0, h1 = _hrange(kind)
    boundary_lines(v, kind, z_top=11.2, scale=scale)
    return v


def section(sh, key_sec, ox, oy, scale, key):
    s = SECTIONS[key_sec]
    if s["axis"] == "x":
        kind = "secN"
    else:
        kind = "secW" if s["look"] < 0 else "secE"
    doc = DXF_DOCS.setdefault(key, new_dxf())
    v = View(sh, ox, oy, scale, dxf=doc.modelspace())
    ground(v, kind, s["c"], scale=scale)
    project(v, kind, s["c"], scale=scale)
    boundary_lines(v, kind, z_top=11.2, scale=scale)
    section_rooms(v, kind, s["c"], scale)
    section_dims(v, kind, s["c"], scale)
    return v, kind


def section_rooms(v: View, kind, c, scale):
    for r in M.ROOMS:
        for (x0, y0, x1, y1) in r.rects:
            b = dict(x0=x0, y0=y0, x1=x1, y1=y1)
            if kind == "secN" and y0 < c < y1:
                hm = (x0 + x1) / 2
            elif kind == "secW" and x0 < c < x1:
                hm = (y0 + y1) / 2
            elif kind == "secE" and x0 < c < x1:
                hm = -(y0 + y1) / 2
            else:
                continue
            zf = M.LV[r.level] if r.level in M.LV else M.LV["R"]
            if r.name.startswith("פטיו"):
                zf = M.LV["B"]
            wdt = abs(x1 - x0) if kind == "secN" else abs(y1 - y0)
            sz = (1.9 if scale >= 100 else 2.6) if wdt > 2.2 else (1.5 if scale >= 100 else 2.0)
            px, py = v.P(hm, zf + 1.45)
            v.sh.text(px, py, r.name, size=sz, weight=600, color="#333")
            if not r.outdoor and r.ceil:
                if kind == "secN":
                    a0, a1 = x0, x1
                elif kind == "secW":
                    a0, a1 = y0, y1
                else:
                    a0, a1 = -y1, -y0
                v.line(a0 + 0.02, zf + r.ceil, a1 - 0.02, zf + r.ceil, lw="xs", dash="2 0.8", color="#555")
                cx_, cy_ = v.P(a0 + 0.15, zf + r.ceil)
                v.sh.text(cx_, cy_ + 2.6, f"ת.ת. {r.ceil:.2f}+", size=sz * 0.7, anchor="left", color="#555")
            break


def section_dims(v: View, kind, c, scale):
    hs0, hs1 = building_hspan(kind)
    if getattr(v, "cut_bounds", None):
        hs1 = v.cut_bounds[2]
    zs = [M.slab_top("B") - M.RAFT, M.LV["B"], M.slab_bot("G"), 0.0, M.slab_bot("U"), M.LV["U"], M.slab_bot("R"),
          M.LV["R"], M.LV["R"] + 0.50]
    v.dim_chain(zs, 0, axis="y", at=hs1 + (1.6 if scale >= 100 else 1.2), size=1.7 if scale >= 100 else 2.2, lw="xxs")
    v.dim_chain([M.LV["B"], 0.0, M.LV["U"], M.LV["R"], M.LV["RX"] + 0.20], 0, axis="y",
                at=hs1 + (3.0 if scale >= 100 else 2.2), size=1.8 if scale >= 100 else 2.3, lw="xxs")


def building_hspan(kind):
    xs = [p[0] for p in M.OUTLINES["U"]] + [M.X_E]
    ys = [p[1] for p in M.OUTLINES["U"]]
    if kind in ("S", "secN"):
        return min(xs), max(xs)
    if kind == "N":
        return -max(xs), -min(xs)
    if kind in ("E", "secW"):
        return min(ys), max(ys)
    return -max(ys), -min(ys)


def place(cx, cy_ground, kind, scale):
    h0, h1 = _hrange(kind)
    k = 1000 / scale
    ox = cx - (h0 + h1) / 2 * k
    oy = cy_ground + M.GARDEN * k
    return ox, oy


def sheet_elevations_100(sh, box):
    x, y, w, h = box
    sc = 100
    cells = [("S", 0.75, 0.30), ("W", 0.27, 0.30), ("N", 0.75, 0.74), ("E", 0.27, 0.74)]
    for kind, fx, fy in cells:
        cx, gy = x + w * fx, y + h * fy
        ox, oy = place(cx, gy, kind, sc)
        v = elevation(sh, kind, ox, oy, sc, f"elev_{kind}_100")
        h0, h1 = _hrange(kind)
        level_column(v, h0 + 1.0, "left", levels=LEVELS[1:], scale=sc)
        drawing_title(sh, cx + 90, gy + 30, ELEV_TITLES[kind], 'קנ"מ 1:100', width=70, size=6.5)
        save_dxf(f"elev_{kind}_100")


def sheet_sections_100(sh, box):
    x, y, w, h = box
    sc = 100
    cells = [("A", 0.70, 0.36), ("B", 0.24, 0.36), ("C", 0.50, 0.86)]
    for key, fx, fy in cells:
        s = SECTIONS[key]
        kind = "secN" if s["axis"] == "x" else ("secW" if s["look"] < 0 else "secE")
        cx, gy = x + w * fx, y + h * fy - 60
        ox, oy = place(cx, gy, kind, sc)
        v, kind = section(sh, key, ox, oy, sc, f"section_{key}_100")
        h0, h1 = _hrange(kind)
        level_column(v, h0 + 1.0, "left", scale=sc)
        drawing_title(sh, cx + 90, gy + 60 + 2, f"חתך {key}-{key}", 'קנ"מ 1:100', width=60, size=6.5)
        save_dxf(f"section_{key}_100")


def sheet_elevations_50(sh, box):
    x, y, w, h = box
    sc = 50
    for kind, fy, crop in [("S", 0.43, None), ("W", 0.93, None)]:
        hs0, hs1 = building_hspan(kind)
        cx = x + w * 0.52
        gy = y + h * fy - 12
        k = 1000 / sc
        ox = cx - (hs0 + hs1) / 2 * k
        oy = gy + M.GARDEN * k
        sh.begin_clip(x, y + (0 if kind == "S" else h * 0.5), w, h * 0.5)
        v = elevation(sh, kind, ox, oy, sc, f"elev_{kind}_50")
        level_column(v, hs0 - 3.0, "left", levels=LEVELS_50[1:], scale=sc)
        sh.end_group()
        drawing_title(sh, x + w - 6, gy + 16, ELEV_TITLES[kind], 'קנ"מ 1:50', width=80, size=7.5)
        save_dxf(f"elev_{kind}_50")


def _section_sheet_50(sh, box, key):
    x, y, w, h = box
    sc = 50
    s = SECTIONS[key]
    kind = "secN" if s["axis"] == "x" else ("secW" if s["look"] < 0 else "secE")
    hs0, hs1 = building_hspan(kind)
    if key == "B":
        hs0 -= 4.0
    cx = x + w * 0.50
    gy = y + h * 0.68
    k = 1000 / sc
    ox = cx - (hs0 + hs1) / 2 * k
    oy = gy + M.GARDEN * k
    sh.begin_clip(x, y, w, h - 4)
    v, kind = section(sh, key, ox, oy, sc, f"section_{key}_50")
    level_column(v, hs0 - 1.3, "left", levels=LEVELS_50, scale=sc)
    sh.end_group()
    callouts(v, CALLOUTS[key], scale=sc, side="left", hx=(x + 118 - ox) / k)
    drawing_title(sh, x + w - 6, y + h - 22, f"חתך {key}-{key}", 'קנ"מ 1:50', width=80, size=8)
    scale_bar(sh, x + 14, y + h - 14, 50, 5)
    save_dxf(f"section_{key}_50")


CALLOUT_X = {"A": 0.6, "B": 0.4}
CALLOUTS = {
    "A": [(6.05, 7.30, "מעקה גג: טיח תרמי לבן + קופינג אלומיניום"),
          (8.0, 7.05, "גג: בטון שיפועים, איטום ביטומני 2 שכבות, XPS 5 ס\"מ, חצץ / PV"),
          (6.05, 5.2, "קיר חוץ ק' א': בלוק 20 + EIFS 6 ס\"מ + טיח תרמי לבן"),
          (9.0, 3.45, "תקרה ב\"מ 30 + מילוי 7 + פרקט/פורצלן 3"),
          (6.05, 1.6, "קיר חוץ ק\"ק: בלוק 20 + צמר סלעים 5 + אבן כורכר 3 בתלייה יבשה"),
          (6.30, 0.35, "סף ויטרינה שקוע, תעלת ניקוז נירוסטה"),
          (6.05, -1.8, "קיר תמך ב\"מ 30 + איטום 2×4 מ\"מ + לוח הגנה + ניקוז"),
          (8.5, -3.85, "רפסודה ב\"מ 50 על בטון רזה 5"),
          (14.4, 3.0, "מדרגות: פלטה מקופלת ב\"מ 18 + מדרך אלון 5 – ראה גיליון 16")],
    "B": [(16.0, 6.2, "לוג'יה: מסגרת בטון בגמר טיח תרמי, מעקה זכוכית 105"),
          (17.0, 7.05, "גג: איטום ביטומני + XPS + חצץ/PV"),
          (18.0, 3.32, "זיז 5.00 מ' – נישא ע\"י קירות-קורה בגובה קומה"),
          (17.0, 3.12, "תקרה תלויה בזיז + פס תאורה לינארי שקוע"),
          (21.0, 1.6, "ויטרינת הרמה-הזזה תרמית, זיגוג 6+16+44.2"),
          (21.15, -1.8, "קיר תמך ב\"מ 30 + איטום + ניקוז היקפי"),
          (11.0, -0.9, "בריכה: מעטפת ב\"מ 25, פסיפס זכוכית, גלישה"),
          (24.0, -3.85, "רפסודה ב\"מ 50")],
}


def sheet_section_a_50(sh, box):
    _section_sheet_50(sh, box, "A")


def sheet_section_b_50(sh, box):
    _section_sheet_50(sh, box, "B")
