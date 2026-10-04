"""Converts the semantic model into axis-aligned 3-D boxes.

Every box: dict(x0,y0,z0,x1,y1,z1, mat, cls, level).
Used by elevations, sections and the Blender renderer, so all views agree.

Materials (mat): stone, plaster, rc, rc_fair, block, glass, frame, alu_wood, wood, deck,
  paving, water, grass, planting, steel, white, furn, furn_dark, fabric, pv, soil, gravel
Classes (cls):   wall, skin, slab, column, glass, frame, fin, rail, stair, pergola, site,
  furn, parapet, door, pool, fence, car, tree
"""
from __future__ import annotations

import model as M


def B(x0, y0, z0, x1, y1, z1, mat, cls, level="", **kw):
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    if z0 > z1:
        z0, z1 = z1, z0
    d = dict(x0=x0, y0=y0, z0=z0, x1=x1, y1=y1, z1=z1, mat=mat, cls=cls, level=level)
    d.update(kw)
    return d


def _wall_rect(w, a0, a1, off0, off1):
    """rectangle in plan for a slice of wall w between axis a0..a1 and normal offsets off0..off1"""
    if w.horiz:
        return a0, w.c + off0, a1, w.c + off1
    return w.c + off0, a0, w.c + off1, a1


def wall_boxes(w):
    """Split wall into solid pieces around openings; add glazing/frames/doors."""
    out = []
    lvl_floor = M.LV.get(w.level, 0.0) if w.level != "R" else M.LV["R"]
    ext = w.kind in ("ext", "retain")
    ext_a0, ext_a1 = w.a0, w.a1
    if ext:  # extend exterior walls to close corners
        ext_a0, ext_a1 = w.a0 - w.t / 2, w.a1 + w.t / 2
    # layers across thickness: for ext walls outer skin + core
    half = w.t / 2
    if ext and w.out:
        s = w.out
        # core occupies inner 0.20, skin outer 0.10
        core = (-half, half - M.T_SKIN) if s > 0 else (-half + M.T_SKIN, half)
        skin = (half - M.T_SKIN, half) if s > 0 else (-half, -half + M.T_SKIN)
        layers = [("core", core, w.z0, w.z1, "rc" if w.core == "rc" else "block"),
                  ("skin", skin, w.skin_z[0], w.skin_z[1], w.skin or "plaster")]
    else:
        mat = {"rc": "rc", "mamad": "rc", "shaft": "rc", "retain": "rc_fair", "parapet": w.skin or "plaster",
               "glass": "plaster"}.get(w.kind, "plaster")
        if w.kind == "int":
            mat = "white"
        layers = [("core", (-half, half), w.z0, w.z1, mat)]

    ops = sorted(w.openings, key=lambda o: o.pos)
    for lname, (o0, o1), z0, z1, mat in layers:
        # wall pieces between openings
        cur = ext_a0
        for o in ops:
            oz0 = lvl_floor + o.sill if o.kind not in ("passage",) else lvl_floor - M.FIN
            oz1 = lvl_floor + o.head
            if o.kind == "open":
                oz0 = lvl_floor - M.FIN
            # piece before opening
            if o.pos > cur + 1e-6:
                x0, y0, x1, y1 = _wall_rect(w, cur, o.pos, o0, o1)
                out.append(B(x0, y0, z0, x1, y1, z1, mat, "skin" if lname == "skin" else "wall", w.level, kind=w.kind))
            # below sill
            if oz0 > z0 + 1e-6:
                x0, y0, x1, y1 = _wall_rect(w, o.pos, o.end, o0, o1)
                out.append(B(x0, y0, z0, x1, y1, min(oz0, z1), mat, "skin" if lname == "skin" else "wall", w.level, kind=w.kind))
            # above head
            if oz1 < z1 - 1e-6:
                x0, y0, x1, y1 = _wall_rect(w, o.pos, o.end, o0, o1)
                out.append(B(x0, y0, max(oz1, z0), x1, y1, z1, mat, "skin" if lname == "skin" else "wall", w.level, kind=w.kind))
            cur = max(cur, o.end)
        if ext_a1 > cur + 1e-6:
            x0, y0, x1, y1 = _wall_rect(w, cur, ext_a1, o0, o1)
            out.append(B(x0, y0, z0, x1, y1, z1, mat, "skin" if lname == "skin" else "wall", w.level, kind=w.kind))

    # glazing & frames
    for o in ops:
        oz0 = lvl_floor + o.sill
        oz1 = lvl_floor + o.head
        if o.kind in ("open", "passage"):
            continue
        # glass plane position: centre of core for ext walls (≈ outer third)
        if ext and w.out:
            gpos = (half - M.T_SKIN - 0.07) * w.out
        else:
            gpos = 0.0
        ft = 0.06  # frame depth (normal)
        fw = 0.05 if o.kind in ("slide", "fixed") else 0.07  # frame face width
        if o.kind in ("door", "mamad_door"):
            mat = "steel" if o.kind == "mamad_door" else "wood"
            x0, y0, x1, y1 = _wall_rect(w, o.pos, o.end, gpos - 0.025, gpos + 0.025)
            out.append(B(x0, y0, lvl_floor, x1, y1, oz1, mat, "door", w.level))
            continue
        if o.kind == "pivot":
            x0, y0, x1, y1 = _wall_rect(w, o.pos, o.end, gpos - 0.04, gpos + 0.04)
            out.append(B(x0, y0, lvl_floor, x1, y1, oz1, "wood_dark", "door", w.level))
            continue
        gmat = "glass_frosted" if o.frosted else "glass"
        if o.kind == "mamad_win":
            gmat = "glass"
        x0, y0, x1, y1 = _wall_rect(w, o.pos + fw, o.end - fw, gpos - 0.012, gpos + 0.012)
        out.append(B(x0, y0, oz0 + fw, x1, y1, oz1 - fw, gmat, "glass", w.level))
        # frame: sill, head, jambs
        for (a0, a1, z0_, z1_) in [(o.pos, o.end, oz0, oz0 + fw), (o.pos, o.end, oz1 - fw, oz1),
                                   (o.pos, o.pos + fw, oz0, oz1), (o.end - fw, o.end, oz0, oz1)]:
            x0, y0, x1, y1 = _wall_rect(w, a0, a1, gpos - ft / 2, gpos + ft / 2)
            out.append(B(x0, y0, z0_, x1, y1, z1_, "frame", "frame", w.level))
        # mullions for sliding doors (panels ≈ 2.2 m) / fixed large panes (≈ 1.6 m)
        L = o.end - o.pos
        n = 1
        if o.kind == "slide":
            n = max(2, round(L / 2.2))
        elif o.kind == "fixed" and L > 2.5:
            n = max(2, round(L / 1.6))
        elif o.kind == "window" and L > 1.8:
            n = max(2, round(L / 1.2))
        for i in range(1, n):
            a = o.pos + L * i / n
            x0, y0, x1, y1 = _wall_rect(w, a - 0.03, a + 0.03, gpos - ft / 2, gpos + ft / 2)
            out.append(B(x0, y0, oz0, x1, y1, oz1, "frame", "frame", w.level))
        if o.kind == "mamad_win":  # steel blast shutter frame
            x0, y0, x1, y1 = _wall_rect(w, o.pos - 0.05, o.end + 0.05, gpos - 0.08, gpos - 0.05)
            out.append(B(x0, y0, oz0 - 0.05, x1, y1, oz0, "steel", "frame", w.level))
    return out


def rect_boxes(rects, holes, z0, z1, mat, cls, level=""):
    """Boxes for union(rects) minus holes, decomposed into strips."""
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union
    poly = unary_union([sbox(*r) for r in rects])
    if holes:
        poly = poly.difference(unary_union([sbox(*h) for h in holes]))
    return [B(*r[:2], z0, *r[2:], z1, mat, cls, level) for r in decompose(poly)]


def decompose(poly):
    """Decompose an orthogonal (multi)polygon into rectangles (x0,y0,x1,y1)."""
    from shapely.geometry import box as sbox
    geoms = getattr(poly, "geoms", [poly])
    out = []
    for g in geoms:
        if g.is_empty:
            continue
        xs = sorted(set(round(c[0], 5) for ring in [g.exterior, *g.interiors] for c in ring.coords))
        strips = []
        for a, b in zip(xs, xs[1:]):
            cut = g.intersection(sbox(a, -1e4, b, 1e4))
            for p in getattr(cut, "geoms", [cut]):
                if p.is_empty or p.area < 1e-8:
                    continue
                if p.geom_type != "Polygon":
                    continue
                # vertical runs within strip
                minx, miny, maxx, maxy = p.bounds
                ys = sorted(set(round(c[1], 5) for ring in [p.exterior, *p.interiors] for c in ring.coords))
                for c, d in zip(ys, ys[1:]):
                    mid = sbox(a, c, b, d)
                    if p.intersection(mid).area > 0.999 * mid.area:
                        strips.append([a, c, b, d])
        # merge vertically adjacent then horizontally adjacent equal runs
        strips.sort(key=lambda r: (r[0], r[1]))
        merged = []
        for r in strips:
            if merged and abs(merged[-1][0] - r[0]) < 1e-6 and abs(merged[-1][2] - r[2]) < 1e-6 and abs(merged[-1][3] - r[1]) < 1e-6:
                merged[-1][3] = r[3]
            else:
                merged.append(r)
        merged.sort(key=lambda r: (r[1], r[3], r[0]))
        m2 = []
        for r in merged:
            if m2 and abs(m2[-1][1] - r[1]) < 1e-6 and abs(m2[-1][3] - r[3]) < 1e-6 and abs(m2[-1][2] - r[0]) < 1e-6:
                m2[-1][2] = r[2]
            else:
                m2.append(r)
        out += [tuple(r) for r in m2]
    return out


def stair_boxes(st):
    out = []
    zb = st["z0"]
    lv = st["level"]
    for (x0, y0, x1, y1, z) in st["treadsA"] + st["treadsB"]:
        out.append(B(x0, y0, z - 0.05, x1, y1, z, "wood", "stair", lv))           # oak tread 5 cm
        out.append(B(x0, y0, z - 0.25, x1, y1, z - 0.05, "rc", "stair", lv))      # folded plate
    x0, y0, x1, y1, z = st["landing"]
    out.append(B(x0, y0, z - 0.25, x1, y1, z, "rc", "stair", lv))
    out.append(B(x0, y0, z - 0.02, x1, y1, z, "wood", "stair", lv))
    # central steel spine/glass balustrade between flights
    gx0 = M.ST["x0"] + M.ST["w"]
    out.append(B(gx0 + 0.035, st["yA0"], zb, gx0 + M.ST["gap"] - 0.035, M.ST["yl"], st["z1"] + 0.9, "glass", "rail", lv))
    return out


def all_boxes(include_site=True, include_furn=True):
    bx = []
    for w in M.WALLS:
        bx += wall_boxes(w)
    for s in M.SLABS:
        mat = {"raft": "rc", "slab": "rc", "roof": "rc", "canopy": "rc_fair", "deck": "deck"}.get(s.kind, "rc")
        lvl = "S"
        bx += rect_boxes(s.rects, s.holes, s.top - s.t, s.top, mat, "slab", lvl)
        if s.kind == "slab":  # floor finish layer
            bx += rect_boxes(s.rects, s.holes, s.top, s.top + M.FIN, "floor", "slab", lvl)
        if s.kind == "roof":
            bx += rect_boxes(s.rects, s.holes, s.top, s.top + 0.12, "roofing", "slab", lvl)
    # slab edge cladding band at the UF cantilever underside & sides handled by skins
    for c in M.COLS:
        bx.append(B(c.x - c.w / 2, c.y - c.d / 2, c.z0, c.x + c.w / 2, c.y + c.d / 2, c.z1, "rc", "column"))
    for st in M.STAIRS:
        bx += stair_boxes(st)
    for r in M.RAILS:
        t = 0.02
        if abs(r["y0"] - r["y1"]) < 1e-6:
            bx.append(B(r["x0"], r["y0"] - t / 2, r["z0"], r["x1"], r["y0"] + t / 2, r["z0"] + r["h"], "glass", "rail"))
            bx.append(B(r["x0"], r["y0"] - 0.03, r["z0"] + r["h"] - 0.03, r["x1"], r["y0"] + 0.03, r["z0"] + r["h"], "steel", "rail"))
        else:
            bx.append(B(r["x0"] - t / 2, r["y0"], r["z0"], r["x0"] + t / 2, r["y1"], r["z0"] + r["h"], "glass", "rail"))
            bx.append(B(r["x0"] - 0.03, r["y0"], r["z0"] + r["h"] - 0.03, r["x0"] + 0.03, r["y1"], r["z0"] + r["h"], "steel", "rail"))
    for f in M.FINS:
        a = f["a0"]
        while a + f["w"] <= f["a1"] + 1e-6:
            if f["axis"] == "y":
                bx.append(B(f["c"] - f["depth"] / 2, a, f["z0"], f["c"] + f["depth"] / 2, a + f["w"], f["z1"], "alu_wood", "fin"))
            else:
                bx.append(B(a, f["c"] - f["depth"] / 2, f["z0"], a + f["w"], f["c"] + f["depth"] / 2, f["z1"], "alu_wood", "fin"))
            a += f["step"]
        # top & bottom carrier rails
        if f["axis"] == "y":
            for z in (f["z0"], f["z1"] - 0.06):
                bx.append(B(f["c"] - 0.03, f["a0"], z, f["c"] + 0.03, f["a1"], z + 0.06, "frame", "fin"))
    for p in M.PERGOLAS:
        base = p.get("base", M.GARDEN if p["z"] < 4 else M.LV["R"])
        if p["x0"] > 25:
            base = M.STREET
        for (px, py) in p["posts"]:
            bx.append(B(px - 0.075, py - 0.075, base, px + 0.075, py + 0.075, p["z"], "frame", "pergola"))
        # perimeter beams
        bx.append(B(p["x0"], p["y0"], p["z"], p["x1"], p["y0"] + 0.12, p["z"] + 0.22, "frame", "pergola"))
        bx.append(B(p["x0"], p["y1"] - 0.12, p["z"], p["x1"], p["y1"], p["z"] + 0.22, "frame", "pergola"))
        bx.append(B(p["x0"], p["y0"], p["z"], p["x0"] + 0.12, p["y1"], p["z"] + 0.22, "frame", "pergola"))
        bx.append(B(p["x1"] - 0.12, p["y0"], p["z"], p["x1"], p["y1"], p["z"] + 0.22, "frame", "pergola"))
        # louvres
        if p["beam"] == "x":
            y = p["y0"] + 0.2
            while y < p["y1"] - 0.15:
                bx.append(B(p["x0"] + 0.12, y, p["z"] + 0.04, p["x1"] - 0.12, y + 0.05, p["z"] + 0.20, "alu_wood", "pergola"))
                y += p["step"]
        else:
            x = p["x0"] + 0.2
            while x < p["x1"] - 0.15:
                bx.append(B(x, p["y0"] + 0.12, p["z"] + 0.04, x + 0.05, p["y1"] - 0.12, p["z"] + 0.20, "alu_wood", "pergola"))
                x += p["step"]
    if include_furn:
        bx += furniture_boxes()
    if include_site:
        bx += site_boxes()
    return bx


FURN_H = dict(sofa=0.75, sofa_l=0.75, armchair=0.75, coffee=0.35, table_rect=0.75, table_round=0.75, island=0.92,
              counter=0.92, counter_l=0.92, fridge=2.2, bed_k=0.55, bed_q=0.55, bed_s=0.55, nightstand=0.5, desk=0.75,
              closet=2.6, lounger=0.4, tub=0.6, vanity=0.85, vanity2=0.85, wc=0.45, basin=0.85, bench=0.45,
              tvunit=0.5, piano=1.0, island_s=0.9, recliner_row=1.0, bar=1.05, pool_table=0.8, sauna=2.1,
              gym=1.2, mat=0.02, rack=2.0, tech=1.8, fireplace=1.0, screen=2.4, shower=0.02, rug=0.01)
FURN_MAT = dict(sofa="fabric", sofa_l="fabric", armchair="fabric", coffee="furn_dark", table_rect="wood", table_round="wood",
                island="stone_white", counter="furn", counter_l="furn", fridge="furn", bed_k="fabric", bed_q="fabric",
                bed_s="fabric", closet="wood", lounger="white", tub="white", fireplace="rc_fair", rug="fabric_dark",
                recliner_row="fabric_dark", screen="white")


def furniture_boxes():
    out = []
    for f in M.FURN:
        if f.kind in ("wc", "basin", "shower", "mat", "gym"):
            continue
        h = FURN_H.get(f.kind, 0.5)
        z0 = M.LV[f.level] if f.level in M.LV else 0.0
        x0, y0 = f.x, f.y
        # w/d are given in plan already (x-extent, y-extent)
        x1, y1 = x0 + f.w, y0 + f.d
        out.append(B(x0, y0, z0, x1, y1, z0 + h, FURN_MAT.get(f.kind, "furn"), "furn", f.level, kind=f.kind))
    return out


def site_boxes():
    S = M.SITE
    out = []
    L = M.LOT
    g = M.GARDEN
    # terrain plate (outside basement + patio)
    out.append(B(L["x0"] - 15, L["y0"] - 15, g - 0.6, L["x1"] + 15, L["y1"] + 15, g - 0.05, "grass", "site"))
    for r in S["deck"]:
        out.append(B(*r[:2], g - 0.05, *r[2:], g + 0.0, "deck", "site"))
    for r in S["paving"]:
        out.append(B(*r[:2], g - 0.05, *r[2:], g + 0.01, "paving", "site"))
    for r in S["planting"]:
        out.append(B(*r[:2], g - 0.05, *r[2:], g + 0.03, "planting", "site"))
    # pool
    P = S["pool"]
    out.append(B(P["x0"], P["y0"], P["water"] - P["depth"], P["x1"], P["y1"], P["water"], "water", "pool"))
    zb = P["water"] - P["depth"]
    # RC pool shell 25 cm walls / 30 cm floor
    out.append(B(P["x0"] - 0.25, P["y0"] - 0.25, zb - 0.30, P["x1"] + 0.25, P["y1"] + 0.25, zb, "rc", "pool"))
    for (x0, y0, x1, y1) in [(P["x0"] - 0.25, P["y0"] - 0.25, P["x1"] + 0.25, P["y0"]),
                             (P["x0"] - 0.25, P["y1"], P["x1"] + 0.25, P["y1"] + 0.25),
                             (P["x0"] - 0.25, P["y0"], P["x0"], P["y1"]), (P["x1"], P["y0"], P["x1"] + 0.25, P["y1"])]:
        out.append(B(x0, y0, zb, x1, y1, g - 0.05, "rc", "pool"))
    for (x0, y0, x1, y1) in [(P["x0"] - 0.3, P["y0"] - 0.3, P["x1"] + 0.3, P["y0"]),
                             (P["x0"] - 0.3, P["y1"], P["x1"] + 0.3, P["y1"] + 0.3),
                             (P["x0"] - 0.3, P["y0"], P["x0"], P["y1"]), (P["x1"], P["y0"], P["x1"] + 0.3, P["y1"])]:
        out.append(B(x0, y0, g - 0.05, x1, y1, g + 0.01, "stone_white", "pool"))
    # fences (boundary walls)
    h = S["fence_h"]
    gx, gy0, gy1 = S["gate"]
    fences = [(L["x0"], L["y0"], L["x1"], L["y0"] + 0.2), (L["x0"], L["y1"] - 0.2, L["x1"], L["y1"]),
              (L["x0"], L["y0"], L["x0"] + 0.2, L["y1"]),
              (L["x1"] - 0.2, L["y0"], L["x1"], 15.8), (L["x1"] - 0.2, 21.8, L["x1"], gy0),
              (L["x1"] - 0.2, gy1, L["x1"], L["y1"])]
    for i, (x0, y0, x1, y1) in enumerate(fences):
        hh = 0.6 if i == 2 else h  # west: low wall + glass towards the golf course
        out.append(B(x0, y0, g - 0.05, x1, y1, g + hh, "stone", "fence"))
        if i == 2:
            out.append(B(x0 + 0.09, y0, g + hh, x1 - 0.09, y1, g + 1.20, "glass", "fence"))
    # street & sidewalk
    st = S["street"]
    out.append(B(L["x1"], L["y0"] - 15, M.STREET - 0.1, L["x1"] + st["sidewalk"], L["y1"] + 15, M.STREET, "paving", "site"))
    out.append(B(L["x1"] + st["sidewalk"], L["y0"] - 15, M.STREET - 0.25, L["x1"] + st["sidewalk"] + 7.5, L["y1"] + 15,
                 M.STREET - 0.15, "asphalt", "site"))
    # loungers by pool
    for (x, y) in S["loungers"]:
        out.append(B(x, y, g, x + 0.7, y + 1.9, g + 0.38, "white", "furn"))
    # BBQ / outdoor kitchen
    out.append(B(*S["bbq"][:2], g, *S["bbq"][2:], g + 0.92, "stone", "furn"))
    # cars
    for (x0, y0, x1, y1) in M.CARS:
        out.append(B(x0 + 0.2, y0 + 0.2, M.STREET + 0.15, x1 - 0.2, y1 - 0.2, M.STREET + 0.9, "car", "car"))
        out.append(B(x0 + 1.2, y0 + 0.3, M.STREET + 0.9, x1 - 1.0, y1 - 0.3, M.STREET + 1.45, "car_glass", "car"))
    return out


def trees():
    return M.SITE["trees"]


if __name__ == "__main__":
    bx = all_boxes()
    from collections import Counter
    print(len(bx), Counter(b["cls"] for b in bx))
