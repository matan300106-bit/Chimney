"""Sheet 18 – interior design of the ground-floor great room (living + dining + kitchen + hall).

Concept: "quiet luxury / warm minimalism" – sand & mocha, travertine & kurkar-tone limestone,
smoked oak, brushed brass, linen; seamless porcelain 120/120 continuing to the terrace,
hidden pocket sliding glass, bioethanol fireplace wall in stone, coffered ceiling with coves.

Everything is read from model.py at build time (walls, openings, rooms, FURN), so the
drawings follow the model; designer additions (stone wall, shelving, ceiling, lighting)
are placed relative to the model's rooms and furniture.

Builder: sheet_interior(sh, box).
"""
from __future__ import annotations

import math
import os

from shapely.geometry import box as sbox
from shapely.ops import unary_union

import model as M
from draw import View, drawing_title, section_marker, LW, FONT

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --------------------------------------------------------------------------- #
#  Palette (plan & elevation colours)
# --------------------------------------------------------------------------- #
INK = "#2a2622"
FUR = "#3b352f"          # furniture outline
FUR_L = "#8a8076"        # secondary furniture lines
C_UPH = "#f4efe6"        # linen upholstery
C_RUG = "#ece3d3"
C_OAK = "#d8c3a2"        # smoked oak in plan (light rendering)
C_OAK_D = "#7b5d45"      # smoked oak in elevation
C_TRAV = "#e6d7bb"
C_SINT = "#efe8dc"
C_BRASS = "#b8955a"
C_POCHE = "#3b3733"
C_PART = "#6b655e"
C_GLASS = "#dbe9ee"
C_LIGHT = "#c0781c"      # lighting symbols
C_HVAC = "#2f6f9a"
C_SAFE = "#b03a2e"

# --------------------------------------------------------------------------- #
#  Custom hatch patterns (paper mm) – added to sh.defs_extra once per sheet
# --------------------------------------------------------------------------- #
IX_PATTERNS = {
    "ix_trav": ('<pattern id="ix_trav" patternUnits="userSpaceOnUse" width="14" height="6">'
                '<rect width="14" height="6" fill="#e8dabf"/>'
                '<path d="M0,1.6 C3,1.2 5,2.1 8,1.7 S12,1.3 14,1.6 M0,4.3 C2.5,4.6 6,3.9 9,4.4 S12.5,4.7 14,4.3" '
                'fill="none" stroke="#c9b089" stroke-width="0.11"/>'
                '<path d="M2,3 h3 M9,2.8 h2.4 M5,5.3 h2" stroke="#d6c19e" stroke-width="0.08"/></pattern>'),
    "ix_kurkar": ('<pattern id="ix_kurkar" patternUnits="userSpaceOnUse" width="4" height="4">'
                  '<rect width="4" height="4" fill="#d6bf98"/>'
                  '<circle cx="0.7" cy="0.8" r="0.22" fill="#b89c70"/><circle cx="2.6" cy="1.9" r="0.16" fill="#b89c70"/>'
                  '<circle cx="1.5" cy="3.2" r="0.12" fill="#a88c62"/><circle cx="3.4" cy="3.5" r="0.2" fill="#c4aa80"/></pattern>'),
    "ix_oak": ('<pattern id="ix_oak" patternUnits="userSpaceOnUse" width="6" height="2.4">'
               '<rect width="6" height="2.4" fill="#7d5f47"/>'
               '<path d="M0,0.6 q1.5,-0.3 3,0 t3,0 M0,1.5 q1.5,0.25 3,0 t3,0 M0,2.1 q2,-0.2 6,0" fill="none" '
               'stroke="#5e4533" stroke-width="0.1"/></pattern>'),
    "ix_oakl": ('<pattern id="ix_oakl" patternUnits="userSpaceOnUse" width="6" height="2.4">'
                '<rect width="6" height="2.4" fill="#dcc6a6"/>'
                '<path d="M0,0.6 q1.5,-0.3 3,0 t3,0 M0,1.6 q1.5,0.25 3,0 t3,0" fill="none" '
                'stroke="#b89a74" stroke-width="0.08"/></pattern>'),
    "ix_oakv": ('<pattern id="ix_oakv" patternUnits="userSpaceOnUse" width="2.4" height="6">'
                '<rect width="2.4" height="6" fill="#7d5f47"/>'
                '<path d="M0.6,0 q-0.3,1.5 0,3 t0,3 M1.6,0 q0.25,1.5 0,3 t0,3" fill="none" '
                'stroke="#5e4533" stroke-width="0.1"/></pattern>'),
    "ix_brass": ('<pattern id="ix_brass" patternUnits="userSpaceOnUse" width="3" height="0.6">'
                 '<rect width="3" height="0.6" fill="#bf9c5e"/>'
                 '<line x1="0" y1="0.15" x2="3" y2="0.15" stroke="#d8bb82" stroke-width="0.07"/>'
                 '<line x1="0" y1="0.45" x2="3" y2="0.45" stroke="#a5834a" stroke-width="0.06"/></pattern>'),
    "ix_linen": ('<pattern id="ix_linen" patternUnits="userSpaceOnUse" width="1.2" height="1.2">'
                 '<rect width="1.2" height="1.2" fill="#ebe3d5"/>'
                 '<path d="M0,0.3 H1.2 M0,0.9 H1.2" stroke="#d3c7b2" stroke-width="0.12"/>'
                 '<path d="M0.3,0 V1.2 M0.9,0 V1.2" stroke="#ddd2bf" stroke-width="0.1"/></pattern>'),
    "ix_mocha": ('<pattern id="ix_mocha" patternUnits="userSpaceOnUse" width="3" height="3">'
                 '<rect width="3" height="3" fill="#b39a82"/>'
                 '<circle cx="0.8" cy="0.7" r="0.35" fill="#a88f77"/><circle cx="2.2" cy="2.1" r="0.45" fill="#bba38b"/></pattern>'),
    "ix_sint": ('<pattern id="ix_sint" patternUnits="userSpaceOnUse" width="16" height="7">'
                '<rect width="16" height="7" fill="#efe6d6"/>'
                '<path d="M0,2 C4,1.5 7,2.6 10,2.1 S14,1.8 16,2 M0,5.2 C3,5.6 7,4.8 11,5.3 S14,5.5 16,5.2" '
                'fill="none" stroke="#d4c3a6" stroke-width="0.1"/></pattern>'),
    "ix_leather": ('<pattern id="ix_leather" patternUnits="userSpaceOnUse" width="2" height="2">'
                   '<rect width="2" height="2" fill="#7c5a44"/>'
                   '<circle cx="0.5" cy="0.6" r="0.18" fill="#6c4d3a"/><circle cx="1.5" cy="1.4" r="0.14" fill="#8a6650"/></pattern>'),
    "ix_por": ('<pattern id="ix_por" patternUnits="userSpaceOnUse" width="5" height="5">'
               '<rect width="5" height="5" fill="#ece3d4"/>'
               '<circle cx="1.2" cy="1.5" r="0.1" fill="#d8ccb8"/><circle cx="3.6" cy="3.4" r="0.12" fill="#d8ccb8"/></pattern>'),
    "ix_flute": ('<pattern id="ix_flute" patternUnits="userSpaceOnUse" width="0.8" height="4">'
                 '<rect width="0.8" height="4" fill="#7d5f47"/>'
                 '<rect x="0" width="0.22" height="4" fill="#5c4434"/>'
                 '<rect x="0.5" width="0.14" height="4" fill="#94735a"/></pattern>'),
    "ix_flute10": ('<pattern id="ix_flute10" patternUnits="userSpaceOnUse" width="2" height="4">'
                   '<rect width="2" height="4" fill="#7d5f47"/>'
                   '<rect x="0" width="0.5" height="4" fill="#5c4434"/>'
                   '<rect x="1.2" width="0.4" height="4" fill="#94735a"/></pattern>'),
    "ix_gyp": ('<pattern id="ix_gyp" patternUnits="userSpaceOnUse" width="1" height="1">'
               '<rect width="1" height="1" fill="#fbfbfa"/><circle cx="0.5" cy="0.5" r="0.07" fill="#666"/></pattern>'),
    "ix_mdf": ('<pattern id="ix_mdf" patternUnits="userSpaceOnUse" width="1.4" height="1.4">'
               '<rect width="1.4" height="1.4" fill="#efe2cf"/>'
               '<circle cx="0.35" cy="0.4" r="0.09" fill="#a08566"/><circle cx="1.05" cy="1.0" r="0.07" fill="#a08566"/>'
               '<circle cx="0.95" cy="0.25" r="0.05" fill="#a08566"/></pattern>'),
    "ix_ply": ('<pattern id="ix_ply" patternUnits="userSpaceOnUse" width="4" height="1.2">'
               '<rect width="4" height="1.2" fill="#ead8b8"/>'
               '<line x1="0" y1="0.3" x2="4" y2="0.3" stroke="#9c7f58" stroke-width="0.09"/>'
               '<line x1="0" y1="0.9" x2="4" y2="0.9" stroke="#9c7f58" stroke-width="0.09"/></pattern>'),
    "ix_plyv": ('<pattern id="ix_plyv" patternUnits="userSpaceOnUse" width="1.2" height="4">'
                '<rect width="1.2" height="4" fill="#ead8b8"/>'
                '<line x1="0.3" y1="0" x2="0.3" y2="4" stroke="#9c7f58" stroke-width="0.09"/>'
                '<line x1="0.9" y1="0" x2="0.9" y2="4" stroke="#9c7f58" stroke-width="0.09"/></pattern>'),
    "ix_steel": ('<pattern id="ix_steel" patternUnits="userSpaceOnUse" width="0.8" height="0.8" patternTransform="rotate(45)">'
                 '<rect width="0.8" height="0.8" fill="#9aa3aa"/>'
                 '<line x1="0" y1="0" x2="0" y2="0.8" stroke="#3c4248" stroke-width="0.18"/></pattern>'),
    "ix_alu": ('<pattern id="ix_alu" patternUnits="userSpaceOnUse" width="1" height="1">'
               '<rect width="1" height="1" fill="#d5dade"/></pattern>'),
    "ix_epoxy": ('<pattern id="ix_epoxy" patternUnits="userSpaceOnUse" width="1" height="1">'
                 '<rect width="1" height="1" fill="#6b5a3e"/></pattern>'),
    "ix_wood": ('<pattern id="ix_wood" patternUnits="userSpaceOnUse" width="5" height="1.6">'
                '<rect width="5" height="1.6" fill="#a98463"/>'
                '<path d="M0,0.4 q1.2,-0.25 2.5,0 t2.5,0 M0,1.1 q1.2,0.2 2.5,0 t2.5,0" fill="none" '
                'stroke="#7b5b40" stroke-width="0.09"/></pattern>'),
    "ix_screed": ('<pattern id="ix_screed" patternUnits="userSpaceOnUse" width="1.5" height="1.5">'
                  '<rect width="1.5" height="1.5" fill="#f3f1ec"/>'
                  '<circle cx="0.4" cy="0.4" r="0.1" fill="#555"/><circle cx="1.1" cy="1.0" r="0.06" fill="#555"/></pattern>'),
}


def pat(sh, name):
    have = getattr(sh, "_ix_pats", None)
    if have is None:
        have = sh._ix_pats = set()
    if name not in have:
        have.add(name)
        sh.defs_extra.append(IX_PATTERNS[name])
    return f"url(#{name})"


# --------------------------------------------------------------------------- #
#  Small paper helpers
# --------------------------------------------------------------------------- #
def tw(t, size):
    """rough text width (mm)"""
    return len(str(t)) * size * 0.53


def rrect(sh, x, y, w, h, r, **kw):
    sh.add(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" rx="{r}" ry="{r}" {sh.style(**kw)}/>')


def code_tag(sh, x, y, code, size=2.0, fill="#fff", color=INK):
    """material code tag (rounded box) centred at x, y"""
    w = tw(code, size) + 2.2
    rrect(sh, x - w / 2, y - size * 0.85, w, size * 1.45, 0.7, lw="xs", color=color, fill=fill)
    sh.text(x, y + size * 0.3, code, size=size, weight=700, color=color)
    return w


def leader(sh, px, py, tx, ty, end_x, dot=True, color=INK):
    sh.polyline([(px, py), (tx, ty), (end_x, ty)], lw="xxs", color=color)
    if dot:
        sh.circle(px, py, 0.45, lw="xxs", color=color, fill=color)


def callout_column(sh, items, x_text, y_min, y_max, size=2.1, gap=None, elbow=5.0, side="right", lh=None, x_edge=None, keep_order=False):
    """items: [(px, py, [lines])] – texts stacked in a column at x_text (left edge of text when side='right')."""
    if not items:
        return
    lh = lh or size * 1.25
    if not keep_order:
        items = sorted(items, key=lambda it: it[1])
    hs = [len(it[2]) * lh + (gap if gap is not None else size * 0.9) for it in items]
    ys = []
    cur = y_min
    for it, h in zip(items, hs):
        y = max(it[1] - (len(it[2]) - 1) * lh / 2, cur)
        ys.append(y)
        cur = y + h
    over = cur - (y_max + hs[-1] - len(items[-1][2]) * lh)
    if over > 0:
        ys = [y - over for y in ys]
        for i in range(len(ys)):
            lo = y_min if i == 0 else ys[i - 1] + hs[i - 1]
            if ys[i] < lo:
                ys[i] = lo
    for (px, py, lines), y in zip(items, ys):
        ty = y
        if side == "right":
            if x_edge is not None:
                sh.polyline([(px, py), (x_edge, py), (x_text - elbow, ty), (x_text - 0.8, ty)], lw="xxs", color=INK)
                sh.circle(px, py, 0.45, lw="xxs", color=INK, fill=INK)
            else:
                leader(sh, px, py, x_text - elbow, ty, x_text - 0.8)
            for i, ln in enumerate(lines):
                sh.text(x_text, ty + size * 0.35 + i * lh, ln, size=size, anchor="left",
                        weight=600 if i == 0 and len(lines) > 1 else 400)
        else:
            leader(sh, px, py, x_text + elbow, ty, x_text + 0.8)
            for i, ln in enumerate(lines):
                sh.text(x_text, ty + size * 0.35 + i * lh, ln, size=size, anchor="right",
                        weight=600 if i == 0 and len(lines) > 1 else 400)


def table(sh, x_right, y, cols, rows, size=2.0, rh=5.0, head_fill="#efe7da", head_size=None, wrap=None,
          zebra=True, bold_first=False):
    """Hebrew table laid out right-to-left. cols = [(title, width)], first col at the right.
    rows: list of lists (str or callable(sh, x0, y0, w, h) for symbols). Returns bottom y."""
    head_size = head_size or size
    W = sum(c[1] for c in cols)
    x0 = x_right - W
    hh = rh + 0.6
    sh.rect(x0, y, W, hh, lw="xs", fill=head_fill)
    xr = x_right
    for title, w in cols:
        sh.text(xr - w / 2, y + hh / 2 + head_size * 0.36, title, size=head_size, weight=700)
        xr -= w
    yy = y + hh
    for ri, row in enumerate(rows):
        if zebra and ri % 2 == 1:
            sh.rect(x0, yy, W, rh, color="none", fill="#faf7f2")
        xr = x_right
        for ci, ((title, w), cell) in enumerate(zip(cols, row)):
            if callable(cell):
                cell(sh, xr - w, yy, w, rh)
            else:
                s = str(cell)
                rtl = any("֐" <= ch <= "׿" for ch in s)
                if rtl or ci == 0:
                    sh.text(xr - 1.2, yy + rh / 2 + size * 0.36, s, size=size, anchor="right",
                            weight=700 if (bold_first and ci == 0) else 400)
                else:
                    sh.text(xr - w / 2, yy + rh / 2 + size * 0.36, s, size=size, anchor="middle")
            xr -= w
        sh.line(x0, yy + rh, x_right, yy + rh, lw="xxs", color="#bbb")
        yy += rh
    sh.rect(x0, y, W, yy - y, lw="xs")
    xr = x_right
    for title, w in cols[:-1]:
        xr -= w
        sh.line(xr, y, xr, yy, lw="xxs", color="#999")
    return yy


def spread(a0, a1, step, min_n=1):
    n = max(min_n, int(round((a1 - a0) / step)))
    return [a0 + (i + 0.5) * (a1 - a0) / n for i in range(n)]


# --------------------------------------------------------------------------- #
#  Model queries
# --------------------------------------------------------------------------- #
def room(no):
    return next(r for r in M.ROOMS if r.no == no)


def rrect_of(no):
    return room(no).rects[0]


def room_area(r):
    return sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in r.rects)


def furn_g(kind=None, within=None):
    out = []
    for f in M.FURN:
        if f.level != "G":
            continue
        if kind and f.kind != kind:
            continue
        if within:
            x0, y0, x1, y1 = within
            cx, cy = f.x + f.w / 2, f.y + f.d / 2
            if not (x0 - 0.05 <= cx <= x1 + 0.05 and y0 - 0.05 <= cy <= y1 + 0.05):
                continue
        out.append(f)
    return out


def frect(f):
    return (f.x, f.y, f.x + f.w, f.y + f.d)


def north_wall_g():
    ext = [w for w in M.walls_on("G") if w.kind == "ext" and w.horiz]
    return max(ext, key=lambda w: w.c)


def south_wall_g():
    ext = [w for w in M.walls_on("G") if w.kind == "ext" and w.horiz]
    return min(ext, key=lambda w: w.c)


def west_wall_g():
    ext = [w for w in M.walls_on("G") if w.kind == "ext" and not w.horiz]
    return min(ext, key=lambda w: w.c)


def east_wall_g():
    ext = [w for w in M.walls_on("G") if w.kind == "ext" and not w.horiz]
    return max(ext, key=lambda w: w.c)


def fireplace_geom():
    """Fireplace wall layout from the model: living rect, slot windows, fireplace FURN."""
    lv = rrect_of("G1")
    nw = north_wall_g()
    slots = sorted([o for o in nw.openings if lv[0] - 0.01 <= o.pos and o.end <= lv[2] + 0.01], key=lambda o: o.pos)
    fp = furn_g("fireplace", lv)
    fp = fp[0] if fp else None
    face = nw.c - nw.t / 2
    if fp:
        fx0, fx1 = fp.x, fp.x + fp.w
    else:
        fx0, fx1 = (lv[0] + lv[2]) / 2 - 1.2, (lv[0] + lv[2]) / 2 + 1.2
    if len(slots) >= 2:
        sx0, sx1 = slots[0].end, slots[-1].pos
    else:
        sx0, sx1 = fx0 - 0.6, fx1 + 0.6
    return dict(lv=lv, face=face, slots=slots, fx0=fx0, fx1=fx1, sx0=sx0, sx1=sx1, axis=(fx0 + fx1) / 2,
                breast_d=0.40, bench_d=0.35)


def interior_rect():
    ww, ew, sw, nw = west_wall_g(), east_wall_g(), south_wall_g(), north_wall_g()
    return (ww.c + ww.t / 2, sw.c + sw.t / 2, ew.c - ew.t / 2, nw.c - nw.t / 2)


def tile_origin():
    """Porcelain 120/120 start point: tile centred on the fireplace axis, full row at the garden glazing."""
    g = fireplace_geom()
    return g["axis"] - 0.60, g["lv"][1]


# --------------------------------------------------------------------------- #
#  Walls / openings (interior style poché)
# --------------------------------------------------------------------------- #
def _polys(g):
    if g.is_empty:
        return []
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def _ring(p):
    return [list(p.exterior.coords)] + [list(i.coords) for i in p.interiors]


def wall_layers(w):
    half = w.t / 2
    ext = w.kind in ("ext", "retain")
    a0, a1 = (w.a0 - half, w.a1 + half) if ext else (w.a0, w.a1)
    if ext and w.out:
        s = w.out
        core = (-half, half - M.T_SKIN) if s > 0 else (-half + M.T_SKIN, half)
        skin = (half - M.T_SKIN, half) if s > 0 else (-half, -half + M.T_SKIN)
        layers = [(core, "core"), (skin, "skin")]
    else:
        layers = [((-half, half), "rc" if (w.core == "rc" or w.kind in ("rc", "shaft", "mamad")) else "part")]
    out = []
    for (o0, o1), mat in layers:
        if w.horiz:
            g = sbox(a0, w.c + o0, a1, w.c + o1)
            for o in w.openings:
                g = g.difference(sbox(o.pos, w.c - 1, o.end, w.c + 1))
        else:
            g = sbox(w.c + o0, a0, w.c + o1, a1)
            for o in w.openings:
                g = g.difference(sbox(w.c - 1, o.pos, w.c + 1, o.end))
        out.append((g, mat))
    return out


def cut_walls():
    z = M.LV["G"] + 1.1
    return [w for w in M.walls_on("G") if w.z0 - 1e-6 <= z <= w.z1 + 1e-6 and w.kind not in ("parapet",)]


def draw_walls(v, outline="xl", skin_fill="pat:stone"):
    allg = []
    skins = []
    for w in cut_walls():
        for g, mat in wall_layers(w):
            for p in _polys(g):
                if mat == "skin":
                    skins.append(p)
                else:
                    fill = {"core": C_POCHE, "rc": "#22201d", "part": C_PART}[mat]
                    v.polygon(_ring(p), fill=fill, color="none")
                allg.append(p)
    for p in skins:
        v.polygon(_ring(p), fill=skin_fill, color="none")
        v.polygon(_ring(p), fill="none", lw="xxs", color="#000")
    for c in M.COLS:
        if c.z0 <= M.LV["G"] + 1.1 <= c.z1:
            r = sbox(c.x - c.w / 2, c.y - c.d / 2, c.x + c.w / 2, c.y + c.d / 2)
            v.polygon(_ring(r), fill="#151311", color="none")
            allg.append(r)
    u = unary_union(allg)
    for p in _polys(u):
        v.polygon(_ring(p), fill="none", lw=outline, color="#000")


def draw_openings(v, swings=True, tags=False, glass_only=False):
    for w in cut_walls():
        half = w.t / 2
        for o in w.openings:
            L = o.end - o.pos
            if w.horiz:
                P = (lambda a, n, w=w: (a, w.c + n))
            else:
                P = (lambda a, n, w=w: (w.c + n, a))
            if o.kind in ("window", "fixed", "slide", "mamad_win"):
                gpos = (half - M.T_SKIN - 0.07) * w.out if (w.kind == "ext" and w.out) else 0.0
                v.line(*P(o.pos, -half), *P(o.end, -half), lw="xxs")
                v.line(*P(o.pos, half), *P(o.end, half), lw="xxs")
                if o.kind == "slide" and not glass_only:
                    n = max(2, round(L / 2.2))
                    pw = L / n
                    for i in range(n):
                        off = gpos + (0.035 if i % 2 else -0.035)
                        a0 = o.pos + i * pw - (0.06 if i else 0)
                        a1 = o.pos + (i + 1) * pw + (0.06 if i < n - 1 else 0)
                        v.polygon([P(a0, off - 0.018), P(a1, off - 0.018), P(a1, off + 0.018), P(a0, off + 0.018)],
                                  fill=C_GLASS, lw="xs")
                else:
                    v.line(*P(o.pos, gpos - 0.02), *P(o.end, gpos - 0.02), lw="s")
                    v.line(*P(o.pos, gpos + 0.02), *P(o.end, gpos + 0.02), lw="s")
            elif o.kind in ("door", "mamad_door") and swings:
                hinge = o.pos if o.hinge == "a" else o.end
                other = o.end if o.hinge == "a" else o.pos
                sgn = o.swing
                face = half * sgn
                d = 1 if other > hinge else -1
                leaf = [P(hinge, face), P(hinge + d * 0.04, face), P(hinge + d * 0.04, face + sgn * L), P(hinge, face + sgn * L)]
                v.polygon(leaf, fill="#fff", lw="s")
                pts = []
                for i in range(19):
                    t = math.radians(90 * i / 18)
                    pts.append(P(hinge + (other - hinge) * math.cos(t), face + sgn * L * math.sin(t)))
                v.polyline(pts, lw="xxs", color="#555")
                v.line(*P(o.pos, -half), *P(o.pos, half), lw="xxs")
                v.line(*P(o.end, -half), *P(o.end, half), lw="xxs")
            elif o.kind == "pivot" and swings:
                sgn = -(w.out or 1)        # opens inward
                pv = o.pos + 0.25 * L
                r1, r2 = o.end - pv, pv - o.pos
                v.polygon([P(pv - 0.03, sgn * r1), P(pv + 0.03, sgn * r1), P(pv + 0.03, -sgn * r2), P(pv - 0.03, -sgn * r2)],
                          fill="#fff", lw="s")
                pts = [P(pv + r1 * math.cos(math.radians(a)), sgn * r1 * math.sin(math.radians(a))) for a in range(0, 91, 5)]
                v.polyline(pts, lw="xxs", color="#555")
                pts = [P(pv - r2 * math.cos(math.radians(a)), -sgn * r2 * math.sin(math.radians(a))) for a in range(0, 91, 10)]
                v.polyline(pts, lw="xxs", color="#555")
                v.circle(*P(pv, 0), 0.03, lw="xs", fill="#000")
            elif o.kind in ("door", "mamad_door", "pivot"):
                v.line(*P(o.pos, 0), *P(o.end, 0), lw="xxs", color="#666", dash="1 0.8")
            elif o.kind in ("open", "passage"):
                v.line(*P(o.pos, 0), *P(o.end, 0), lw="xxs", dash="1.5 1", color="#777")
            if tags and o.tag:
                n_out = (half + 0.42) * (w.out if w.out else 1)
                if w.kind != "ext":
                    n_out = half + 0.3
                tx, ty = v.P(*P((o.pos + o.end) / 2, n_out))
                code_tag(v.sh, tx, ty, o.tag, size=2.0)


def draw_stairs(v, light=False):
    st = next((s for s in M.STAIRS if s["level"] == "G"), None)
    dn = next((s for s in M.STAIRS if abs(s["z1"] - M.LV["G"]) < 1e-6), None)
    col = "#888" if light else INK
    if st:
        x0, y0, x1, y1 = st["flightA"]
        v.rect(x0, y0, x1, y1, fill="#fff", lw="xs", color=col)
        cut_i = 6
        for i, (a, b, c, d, z) in enumerate(st["treadsA"]):
            if i < cut_i:
                v.line(a, d, c, d, lw="xs", color=col)
        yc = st["treadsA"][cut_i][1] if len(st["treadsA"]) > cut_i else y1
        v.line(x0, yc - 0.05, x1, yc + 0.25, lw="xs", color=col)
        if not light:
            xm = (x0 + x1) / 2
            v.line(xm, y0 + 0.1, xm, yc - 0.2, lw="xxs")
            ax, ay = v.P(xm, yc - 0.2)
            v.sh.path(f"M{ax},{ay - 1.2} L{ax - 0.7},{ay + 0.3} L{ax + 0.7},{ay + 0.3} Z", lw="xxs", fill="#000")
            v.text(xm, y0 + 0.28, "עולה", size=2.0)
    if dn:
        x0, y0, x1, y1 = dn["flightB"]
        v.rect(x0, y0, x1, y1, fill="#fff", lw="xs", color=col)
        for (a, b, c, d, z) in dn["treadsB"]:
            v.line(a, b, c, b, lw="xs", color=col)
        if not light:
            xm = (x0 + x1) / 2
            v.line(xm, y0 + 0.1, xm, y1 - 0.4, lw="xxs")
            ax, ay = v.P(xm, y1 - 0.4)
            v.sh.path(f"M{ax},{ay + 1.2} L{ax - 0.7},{ay - 0.3} L{ax + 0.7},{ay - 0.3} Z", lw="xxs", fill="#000")
            v.text(xm, y0 + 0.28, "יורד", size=2.0)
    if st:
        x0, y0, x1, y1, _ = st["landing"]
        v.rect(x0, y0, x1, y1, fill="#fff", lw="xs", color=col)


def draw_lift(v):
    L = M.LIFT
    x0, y0, x1, y1 = L["x0"] + 0.22, L["y0"] + 0.22, L["x1"] - 0.22, L["y1"] - 0.05
    v.rect(x0, y0, x1, y1, fill="#fff", lw="xs")
    v.line(x0, y0, x1, y1, lw="xxs")
    v.line(x0, y1, x1, y0, lw="xxs")


# --------------------------------------------------------------------------- #
#  Furniture – detailed symbols (Local frame: rot = direction the front faces)
# --------------------------------------------------------------------------- #
class Local:
    def __init__(self, f):
        self.box = (f.x, f.y, f.x + f.w, f.y + f.d)
        r = f.rot % 360
        self.r = r
        if r in (270, 90):
            self.W, self.D = f.w, f.d
        else:
            self.W, self.D = f.d, f.w

    def P(self, u, v):
        x0, y0, x1, y1 = self.box
        r = self.r
        if r == 270:
            return x0 + u, y0 + v
        if r == 90:
            return x1 - u, y1 - v
        if r == 0:
            return x1 - v, y0 + u
        return x0 + v, y1 - u


def _lp(v, L, pts, closed=True, fill="none", lw="xs", color=FUR, **kw):
    P = [L.P(a, b) for a, b in pts]
    if closed:
        v.polygon(P, fill=fill, lw=lw, color=color, **kw)
    else:
        v.polyline(P, lw=lw, color=color, **kw)


def _lr(v, L, u0, v0, u1, v1, **kw):
    _lp(v, L, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], **kw)


def _lrr(v, L, u0, v0, u1, v1, r, **kw):
    pts = []
    r = min(r, (u1 - u0) / 2, (v1 - v0) / 2)
    for (cu, cv, a0) in [(u1 - r, v0 + r, 270), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)]:
        for i in range(7):
            a = math.radians(a0 + i * 15)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    _lp(v, L, pts, **kw)


def _lell(v, L, cu, cv, ru, rv, **kw):
    pts = [(cu + ru * math.cos(math.radians(a)), cv + rv * math.sin(math.radians(a))) for a in range(0, 360, 12)]
    _lp(v, L, pts, **kw)


def _cushions(v, L, u0, u1, v0, v1, n):
    for i in range(1, n):
        u = u0 + (u1 - u0) * i / n
        _lp(v, L, [(u, v0 + 0.03), (u, v1)], closed=False, lw="xxs", color=FUR_L)


def sym_sofa(v, L, W, D):
    _lrr(v, L, 0, 0, W, D, 0.07, fill=C_UPH)
    _lrr(v, L, 0.16, D - 0.24, W - 0.16, D - 0.02, 0.05, lw="xxs", color=FUR_L)
    _lrr(v, L, 0.0, 0.0, 0.16, D, 0.06, lw="xxs", color=FUR_L)
    _lrr(v, L, W - 0.16, 0.0, W, D, 0.06, lw="xxs", color=FUR_L)
    n = max(2, round((W - 0.32) / 0.85))
    _cushions(v, L, 0.16, W - 0.16, 0.0, D - 0.24, n)
    for i in range(n):           # scatter cushions
        cu = 0.16 + (W - 0.32) * (i + 0.5) / n
        if i in (0, n - 1):
            _lrr(v, L, cu - 0.2, D - 0.42, cu + 0.2, D - 0.26, 0.05, lw="xxs", color=FUR_L, fill="url(#ix_linen)")


def sym_sofa_l(v, L, W, D):
    dd = 1.0
    pts = [(0, 0), (dd, 0), (dd, D - dd), (W, D - dd), (W, D), (0, D)]
    _lp(v, L, pts, fill=C_UPH)
    # back rest along v=D and along u=0 is open (chaise end); arm at u=W
    _lp(v, L, [(0.04, D - 0.24), (W - 0.16, D - 0.24), (W - 0.16, D - dd + 0.02)], closed=False, lw="xxs", color=FUR_L)
    _lr(v, L, W - 0.16, D - dd, W, D, lw="xxs", color=FUR_L)
    _lp(v, L, [(0.06, 0.12), (dd - 0.06, 0.12)], closed=False, lw="xxs", color=FUR_L)
    _lp(v, L, [(0.04, D - dd), (dd, D - dd)], closed=False, lw="xxs", color=FUR_L)
    n = max(2, round((W - dd - 0.16) / 0.85))
    for i in range(1, n):
        u = dd + (W - dd - 0.16) * i / n
        _lp(v, L, [(u, D - dd + 0.03), (u, D - 0.24)], closed=False, lw="xxs", color=FUR_L)
    _lp(v, L, [(dd * 0.5, 0.12), (dd * 0.5, D - 0.24)], closed=False, lw="xxs", color=FUR_L, dash="0.8 0.6")
    for cu in (dd + 0.35, W - 0.55):
        _lrr(v, L, cu - 0.22, D - 0.42, cu + 0.22, D - 0.26, 0.05, lw="xxs", color=FUR_L, fill="url(#ix_linen)")


def sym_armchair(v, L, W, D):
    _lrr(v, L, 0, 0, W, D, 0.14, fill=C_UPH)
    _lrr(v, L, 0.13, 0.06, W - 0.13, D - 0.2, 0.08, lw="xxs", color=FUR_L)
    _lp(v, L, [(0.1, D - 0.12), (W - 0.1, D - 0.12)], closed=False, lw="xxs", color=FUR_L)


def sym_coffee(v, L, W, D, sh):
    _lrr(v, L, 0, 0, W, D, min(W, D) * 0.48, fill=pat(sh, "ix_trav"), lw="xs")
    _lrr(v, L, 0.06, 0.06, W - 0.06, D - 0.06, min(W, D) * 0.42, lw="xxs", color=FUR_L)
    # styling: tray + vase
    _lell(v, L, W * 0.62, D * 0.5, 0.09, 0.09, lw="xxs", color=FUR_L, fill="#fff")


def sym_table(v, L, W, D, seats, sh):
    _lrr(v, L, 0, 0, W, D, 0.08, fill=pat(sh, "ix_oakl"), lw="xs")
    n = max(1, int(round((W - 0.2) / 0.72)))
    if seats and int(seats) < 2 * n:
        n = int(seats) // 2
    step = (W - 0.2) / n
    for side in (-1, 1):
        for i in range(n):
            cu = 0.1 + step * (i + 0.5)
            vv = -0.3 if side < 0 else D + 0.3
            _lrr(v, L, cu - 0.23, vv - 0.22, cu + 0.23, vv + 0.22, 0.08, fill=C_UPH, lw="xs")
            bv = vv - 0.22 if side < 0 else vv + 0.22
            _lp(v, L, [(cu - 0.2, bv + side * 0.0), (cu + 0.2, bv)], closed=False, lw="s")
    if seats and int(seats) > 2 * n:
        for uu, s in ((-0.32, -1), (W + 0.32, 1)):
            _lrr(v, L, uu - 0.22, D / 2 - 0.23, uu + 0.22, D / 2 + 0.23, 0.08, fill=C_UPH, lw="xs")
            _lp(v, L, [(uu + s * 0.22, D / 2 - 0.2), (uu + s * 0.22, D / 2 + 0.2)], closed=False, lw="s")
    # centrepiece
    _lell(v, L, W / 2, D / 2, 0.35, 0.12, lw="xxs", color=FUR_L)


def sym_piano(v, L, W, D):
    # grand piano: keyboard at the front (v=0), straight bass side at u=0, curved tail
    kb = 0.22
    tail = [(W, kb), (W, kb + (D - kb) * 0.30)]
    for i in range(1, 13):
        t = i / 12
        # S-curve from (W, 0.3 of body) to (0.12W, D)
        u = W - (W * 0.88) * (0.5 - 0.5 * math.cos(math.pi * t))
        vv = kb + (D - kb) * (0.30 + 0.70 * (t ** 0.8))
        tail.append((u, vv))
    pts = [(0, kb)] + tail + [(0, D)]
    _lp(v, L, pts, fill="#efe9e1")
    _lr(v, L, 0, 0, W, kb, fill="#fff", lw="xs")
    for i in range(1, 16):
        u = W * i / 16
        _lp(v, L, [(u, 0.02), (u, kb - 0.02)], closed=False, lw="xxs", color=FUR_L)
    _lp(v, L, [(0.08, kb + 0.1), (W * 0.85, kb + (D - kb) * 0.35), (W * 0.3, D - 0.12)], closed=False,
        lw="xxs", color=FUR_L)
    _lrr(v, L, W / 2 - 0.35, -0.48, W / 2 + 0.35, -0.12, 0.06, fill=C_UPH, lw="xs")


def sym_bookcase(v, L, W, D, sh):
    _lr(v, L, 0, 0, W, D, fill=pat(sh, "ix_oakl"), lw="xs")
    n = max(2, round(W / 0.8))
    for i in range(1, n):
        u = W * i / n
        _lp(v, L, [(u, 0), (u, D)], closed=False, lw="xxs", color=FUR_L)
    _lp(v, L, [(0, 0.03), (W, 0.03)], closed=False, lw="xxs", color=FUR_L, dash="0.8 0.5")


def sym_closet(v, L, W, D):
    _lr(v, L, 0, 0, W, D, fill="#fff", lw="xs")
    _lp(v, L, [(0.03, D / 2), (W - 0.03, D / 2)], closed=False, lw="xxs", color=FUR_L)
    n = max(1, round(W / 0.5))
    for i in range(1, n):
        u = W * i / n
        _lp(v, L, [(u, 0), (u, 0.05)], closed=False, lw="xxs", color=FUR_L)
    for i in range(int(W / 0.14)):
        u = 0.08 + i * 0.14
        _lp(v, L, [(u, D / 2 - 0.13), (u + 0.03, D / 2 + 0.13)], closed=False, lw="xxs", color="#999")


def sym_tall(v, L, W, D, label, sh):
    _lr(v, L, 0, 0, W, D, fill=pat(sh, "ix_oakl"), lw="xs")
    _lp(v, L, [(0, 0), (W, D)], closed=False, lw="xxs", color=FUR_L)
    _lp(v, L, [(0, 0.02), (W, 0.02)], closed=False, lw="xxs", color=FUR)
    if label:
        x, y = L.P(W / 2, D * 0.62)
        v.text(x, y - 0.04, label, size=2.0)


def sym_counter(v, L, W, D, sh, wall_unit=False):
    _lr(v, L, 0, 0, W, D, fill=pat(sh, "ix_sint"), lw="xs")
    _lp(v, L, [(0, 0.06), (W, 0.06)], closed=False, lw="xxs", color=FUR_L, dash="0.9 0.6")
    if wall_unit:      # upper cabinets (dashed, above)
        _lp(v, L, [(0, D - 0.35), (W, D - 0.35)], closed=False, lw="xxs", color=FUR_L, dash="2 0.8")


def island_layout(f):
    """Island geometry in its own frame: length L (u), depth D (v, front = seating side)."""
    L = max(f.w, f.d)
    D = min(f.w, f.d)
    leg = 0.02
    inner = L - 2 * leg
    dw, sink, hob = 0.60, 0.80, 0.80
    mid = max(0.30, inner - dw - sink - hob)
    mods = [("מדיח", dw), ("כיור", sink), ("מגירות", mid), ("כיריים", hob)]
    x = leg
    out = []
    for n, w in mods:
        out.append((n, x, x + w))
        x += w
    over = 0.32            # seating overhang
    panel = 0.03           # fluted oak panel
    return dict(L=L, D=D, leg=leg, mods=out, over=over, panel=panel, carc0=over + panel, front_gap=0.021)


def sym_island(v, f, sh, stools=True):
    """Island seen in plan. Model rot = direction of the SEATING (front) side."""
    Lc = Local(f)
    W, D = Lc.W, Lc.D
    g = island_layout(f)
    # Local: u along length, v from seating side (0) to work side (D)
    _lr(v, Lc, 0, 0, W, D, fill=pat(sh, "ix_sint"), lw="s")
    # waterfall legs
    for u0 in (0, W - g["leg"]):
        _lr(v, Lc, u0, 0, u0 + g["leg"], D, fill="#cdbb9b", lw="xs")
    # hidden lines: fluted panel / carcass under the overhang
    _lp(v, Lc, [(g["leg"], g["over"]), (W - g["leg"], g["over"])], closed=False, lw="xxs", color=FUR, dash="1.2 0.7")
    _lp(v, Lc, [(g["leg"], g["carc0"]), (W - g["leg"], g["carc0"])], closed=False, lw="xxs", color=FUR_L, dash="1.2 0.7")
    vc = (g["carc0"] + D) / 2 + 0.02
    for name, a, b in g["mods"]:
        if name == "כיור":
            cu = (a + b) / 2
            _lrr(v, Lc, cu - 0.36, vc - 0.21, cu + 0.36, vc + 0.21, 0.05, lw="xs", color=FUR, fill="#fff")
            _lrr(v, Lc, cu - 0.33, vc - 0.18, cu + 0.33, vc + 0.18, 0.04, lw="xxs", color=FUR_L)
            _lell(v, Lc, cu + 0.2, vc, 0.025, 0.025, lw="xxs")
            _lell(v, Lc, cu, vc + 0.27, 0.03, 0.03, lw="xs", fill="#999")   # tap
        elif name == "כיריים":
            cu = (a + b) / 2
            _lr(v, Lc, cu - 0.39, vc - 0.26, cu + 0.39, vc + 0.26, fill="#2f2c2a", lw="xs")
            _lr(v, Lc, cu - 0.03, vc - 0.24, cu + 0.03, vc + 0.24, fill="#777", color="none")   # downdraft
            for du in (-0.2, 0.2):
                for dv in (-0.12, 0.12):
                    _lell(v, Lc, cu + du, vc + dv, 0.09, 0.09, lw="xxs", color="#cfcfcf")
    if stools:
        n = max(2, int((W - 0.3) / 0.65))
        for i in range(n):
            cu = W * (i + 0.5) / n
            _lell(v, Lc, cu, -0.05, 0.21, 0.21, fill=C_UPH, lw="xs")
            _lell(v, Lc, cu, -0.05, 0.15, 0.15, lw="xxs", color=FUR_L)
    return Lc


def sym_wc(v, L, W, D):
    _lr(v, L, 0, D - 0.16, W, D, fill="#fff", lw="xs")
    _lell(v, L, W / 2, (D - 0.16) / 2 + 0.02, W * 0.45, (D - 0.16) / 2 + 0.02, fill="#fff", lw="xs")


def sym_basin(v, L, W, D, sh):
    _lr(v, L, 0, 0, W, D, fill=pat(sh, "ix_trav"), lw="xs")
    _lell(v, L, W / 2, D * 0.48, W * 0.33, D * 0.28, fill="#fff", lw="xxs")


def sym_bench(v, L, W, D, sh):
    _lr(v, L, 0, 0, W, D, fill=pat(sh, "ix_oakl"), lw="xs")
    _lrr(v, L, 0.05, 0.05, W - 0.05, D - 0.05, 0.04, fill=C_UPH, lw="xxs", color=FUR_L)


def plant(v, cx, cy, r=0.3):
    v.circle(cx, cy, r * 0.45, lw="xs", fill="#efe6d6")
    for i in range(9):
        a = math.radians(i * 40 + 10)
        ex, ey = cx + r * math.cos(a), cy + r * math.sin(a)
        mx, my = cx + r * 0.6 * math.cos(a + 0.25), cy + r * 0.6 * math.sin(a + 0.25)
        v.polyline([(cx + r * 0.3 * math.cos(a), cy + r * 0.3 * math.sin(a)), (mx, my), (ex, ey)], lw="xxs", color="#6f7d55")
    v.circle(cx, cy, r, lw="xxs", color="#6f7d55", dash="0.6 0.5")


def floor_lamp(v, cx, cy, r=0.2):
    v.circle(cx, cy, r, lw="xs", fill="#fff")
    v.circle(cx, cy, r * 0.35, lw="xxs", fill=C_BRASS)


def draw_furniture(v, sh, region):
    for f in furn_g(within=region):
        L = Local(f)
        W, D = L.W, L.D
        k = f.kind
        if k == "rug":
            continue
        if k == "sofa":
            sym_sofa(v, L, W, D)
        elif k == "sofa_l":
            sym_sofa_l(v, L, W, D)
        elif k == "armchair":
            sym_armchair(v, L, W, D)
        elif k == "coffee":
            sym_coffee(v, L, W, D, sh)
        elif k == "table_rect":
            sym_table(v, L, W, D, f.label, sh)
        elif k == "piano":
            sym_piano(v, L, W, D)
        elif k == "closet":
            if "ספרי" in (f.label or ""):
                sym_bookcase(v, L, W, D, sh)
            elif f.label:
                sym_tall(v, L, W, D, f.label, sh)
            else:
                sym_closet(v, L, W, D)
        elif k == "fridge":
            sym_tall(v, L, W, D, "מקרר", sh)
        elif k in ("counter", "counter_l"):
            sym_counter(v, L, W, D, sh)
            kr = rrect_of("G3")
            if W > 2.5 and kr[0] - 0.1 <= f.x <= kr[2] and kr[1] - 0.1 <= f.y <= kr[3]:
                # main sink + dishwasher in the long kitchen run (under the window)
                cu = W * 0.5
                _lrr(v, L, cu - 0.40, 0.10, cu + 0.40, D - 0.12, 0.05, lw="xs", color=FUR, fill="#fff")
                _lrr(v, L, cu - 0.36, 0.14, cu + 0.36, D - 0.16, 0.04, lw="xxs", color=FUR_L)
                _lell(v, L, cu, D - 0.07, 0.03, 0.03, lw="xs", fill="#999")
                _lr(v, L, cu + 0.45, 0.0, cu + 1.05, 0.04, lw="xxs", color=FUR_L)
                x, y = L.P(cu + 0.75, D * 0.5)
                v.text(x, y, "מדיח", size=2.0, rot=-90 if L.r in (0, 180) else 0)
        elif k == "island":
            sym_island(v, f, sh)
        elif k == "wc":
            sym_wc(v, L, W, D)
        elif k == "basin":
            sym_basin(v, L, W, D, sh)
        elif k == "bench":
            sym_bench(v, L, W, D, sh)
        elif k == "fireplace":
            pass       # drawn with the stone wall
        elif k == "tvunit":
            _lr(v, L, 0, 0, W, D, fill=pat(sh, "ix_oakl"), lw="xs")
        else:
            _lrr(v, L, 0, 0, W, D, 0.04, fill="#fff", lw="xs")


def draw_rugs(v, sh, region):
    for f in furn_g("rug", region):
        x0, y0, x1, y1 = frect(f)
        v.rect(x0, y0, x1, y1, fill=pat(sh, "ix_linen"), lw="xs", color="#9a8e7c")
        v.rect(x0 + 0.1, y0 + 0.1, x1 - 0.1, y1 - 0.1, fill="none", lw="xxs", color="#9a8e7c", dash="1 0.7")


def free_spot(x, y, r, pad=0.05):
    """True if a circle at (x,y) does not hit any GF furniture (except rugs)."""
    for f in furn_g():
        if f.kind == "rug":
            continue
        x0, y0, x1, y1 = frect(f)
        if x0 - r - pad < x < x1 + r + pad and y0 - r - pad < y < y1 + r + pad:
            return False
    return True


def draw_fireplace_wall_plan(v, sh):
    g = fireplace_geom()
    face = g["face"]
    lv = g["lv"]
    # stone breast between the slot windows
    v.rect(g["sx0"], face - g["breast_d"], g["sx1"], face, fill=pat(sh, "ix_trav"), lw="s")
    # floating hearth bench
    v.rect(g["sx0"], face - g["breast_d"] - g["bench_d"], g["sx1"], face - g["breast_d"],
           fill=pat(sh, "ix_trav"), lw="xs", dash=None)
    v.line(g["sx0"] + 0.04, face - g["breast_d"] - g["bench_d"] + 0.04, g["sx1"] - 0.04,
           face - g["breast_d"] - g["bench_d"] + 0.04, lw="xxs", color=FUR_L)
    # bioethanol burner (in the breast)
    bx0, bx1 = g["fx0"] + 0.15, g["fx1"] - 0.15
    v.rect(bx0, face - g["breast_d"] + 0.06, bx1, face - 0.12, fill="#2f2c2a", lw="xs")
    pts = [(bx0 + 0.1 + i * (bx1 - bx0 - 0.2) / 12, face - g["breast_d"] + 0.15 + (0.06 if i % 2 else 0)) for i in range(13)]
    v.polyline(pts, lw="xs", color="#e0913a")
    # shelving bays outside the slots
    slots = g["slots"]
    bays = []
    if slots:
        if slots[0].pos - lv[0] > 0.3:
            bays.append((lv[0], slots[0].pos))
        if lv[2] - slots[-1].end > 0.3:
            bays.append((slots[-1].end, lv[2]))
    for a, b in bays:
        v.rect(a, face - 0.38, b, face, fill=pat(sh, "ix_oakl"), lw="xs")
        v.line(a, face - 0.36, b, face - 0.36, lw="xxs", color=FUR_L, dash="0.8 0.5")
    return g, bays


def draw_curtains(v, walls_sides):
    """linen sheers inside the glazing (recessed track)"""
    for w in cut_walls():
        if w.kind != "ext":
            continue
        for o in w.openings:
            if o.kind not in ("slide", "fixed") or o.end - o.pos < 1.5:
                continue
            if not walls_sides(w, o):
                continue
            inner = w.c - w.out * (w.t / 2 + 0.10)
            n = int((o.end - o.pos) / 0.12)
            pts = []
            for i in range(n + 1):
                a = o.pos + 0.05 + (o.end - o.pos - 0.1) * i / n
                pts.append((a, inner + 0.035 * math.sin(i * math.pi / 2)))
            if not w.horiz:
                pts = [(b, a) for a, b in pts]
            v.polyline(pts, lw="xxs", color="#8e7f6a")


# --------------------------------------------------------------------------- #
#  Room tags and dims
# --------------------------------------------------------------------------- #
def room_tag(v, x, y, r, lines_extra=(), size=2.8):
    sh = v.sh
    px, py = v.P(x, y)
    name = r.name
    a = room_area(r)
    l1 = f"{name}"
    l2 = f"{r.no}  |  {a:.1f} מ\"ר"
    w = max(tw(l1, size), tw(l2, 2.1), *[tw(t, 2.0) for t in lines_extra]) + 4
    h = size + 2.1 * 1.3 + len(lines_extra) * 2.6 + 2.4
    sh.rect(px - w / 2, py - size - 0.9, w, h, lw="xs", fill="#fffdf9", fop=0.92)
    sh.text(px, py, l1, size=size, weight=700)
    sh.text(px, py + 2.1 * 1.35, l2, size=2.1)
    yy = py + 2.1 * 1.35
    for t in lines_extra:
        yy += 2.6
        sh.text(px, yy, t, size=2.0, color="#4a4038")


# --------------------------------------------------------------------------- #
#  (a) Furniture & finishes plan 1:50
# --------------------------------------------------------------------------- #
CROP = (6.0, 21.0, 25.0, 32.0)


def floor_tint(v, sh, grid=True, strong=False):
    X0, Y0 = tile_origin()
    por = [interior_rect()]
    for r in por:
        v.rect(*r, fill="#fbf8f2" if not strong else pat(sh, "ix_por"), color="none")
    lob = rrect_of("G7")
    v.rect(*lob, fill="#f3ebde" if not strong else pat(sh, "ix_kurkar"), color="none")
    for n in ("G5", "G6"):
        v.rect(*rrect_of(n), fill="#f4f3f0", color="none")
    if grid:
        col = "#e3d9c9" if not strong else "#b9a88e"
        lw = 0.05 if not strong else 0.09
        for (x0, y0, x1, y1) in por:
            k = math.ceil((x0 - X0) / 1.2)
            while X0 + k * 1.2 < x1 - 1e-6:
                xx = X0 + k * 1.2
                v.line(xx, y0, xx, y1, lw=lw, color=col)
                k += 1
            k = math.ceil((y0 - Y0) / 1.2)
            while Y0 + k * 1.2 < y1 - 1e-6:
                yy = Y0 + k * 1.2
                v.line(x0, yy, x1, yy, lw=lw, color=col)
                k += 1


def plan_furniture(sh, ox, oy, sc=50):
    v = View(sh, ox, oy, sc)
    region = (CROP[0], CROP[1], CROP[2], CROP[3])
    floor_tint(v, sh)
    draw_rugs(v, sh, region)
    g, bays = draw_fireplace_wall_plan(v, sh)
    draw_furniture(v, sh, region)
    # designer accessories (only where free)
    lv = g["lv"]
    for (x, y, kind) in [(lv[0] + 0.35, lv[1] + 0.45, "plant"), (lv[2] - 0.35, lv[1] + 0.40, "plant"),
                         (lv[0] + 0.35, lv[3] - 0.85, "lamp"), (rrect_of("G2")[0] + 0.35, rrect_of("G2")[1] + 0.40, "plant"),
                         (rrect_of("G4")[2] - 0.45, rrect_of("G4")[1] + 0.55, "plant"),
                         (rrect_of("G7")[2] - 0.45, rrect_of("G7")[1] + 0.40, "plant")]:
        r = 0.3 if kind == "plant" else 0.2
        if free_spot(x, y, r):
            plant(v, x, y, r) if kind == "plant" else floor_lamp(v, x, y, r)
    draw_curtains(v, lambda w, o: (w.horiz and w.c < 25) or (not w.horiz and w.c < 10))
    draw_walls(v)
    draw_openings(v, swings=True, tags=False)
    draw_stairs(v)
    draw_lift(v)
    return v, g, bays


def annotate_furniture_plan(v, g, bays):
    sh = v.sh
    k = v.k
    # room tags
    tags = {
        "G1": ["רצפה FL-01 | קירות PT-01", "ת.ת. +2.95 / +3.10"],
        "G2": ["רצפה FL-01 | ת.ת. +2.95 / +3.10"],
        "G3": ["רצפה FL-01 | ת.ת. +2.95 / +3.10"],
        "G4": ["רצפה FL-01 | ת.ת. +3.10"],
        "G7": ["רצפה ST-02 | תקרת WD-01"],
    }
    for no, extra in tags.items():
        r = room(no)
        x, y = r.tag_at or ((r.rects[0][0] + r.rects[0][2]) / 2, (r.rects[0][1] + r.rects[0][3]) / 2)
        if no == "G1":
            x, y = _living_tag_spot(r)
        if no == "G7":
            x, y = (r.rects[0][0] + r.rects[0][2]) / 2 - 0.4, (r.rects[0][1] + r.rects[0][3]) / 2 - 0.2
        if no == "G3":
            isl = furn_g("island")
            if isl:
                f = isl[0]
                x = (r.rects[0][0] + f.x) / 2
                y = f.y + f.d / 2 + 0.1
                extra = []
        if no == "G2":
            t = furn_g("table_rect", r.rects[0])
            if t:
                f = t[0]
                x = f.x + f.w / 2
                y = (f.y + f.d + 0.6 + r.rects[0][3]) / 2 + 0.25
                extra = []
        room_tag(v, x, y, r, extra, size=2.8 if no in ("G1", "G2", "G3") else 2.5)
    for no in ("G5", "G6"):
        r = room(no)
        x0, y0, x1, y1 = r.rects[0]
        px, py = v.P((x0 + x1) / 2, (y0 + y1) / 2 + 0.55)
        nm = r.name.split("/")[0].strip()
        sh.text(px, py, nm, size=2.2, weight=700)
        sh.text(px, py + 2.7, r.no, size=2.0)
    # material code tags
    face = g["face"]
    px, py = v.P((g["sx0"] + g["sx1"]) / 2 + 0.75, face - g["breast_d"] - g["bench_d"] - 0.22)
    code_tag(sh, px, py, "ST-01")
    for a, b in bays:
        px, py = v.P((a + b) / 2, face - 0.55)
        code_tag(sh, px, py, "WD-01")
    # notes with leaders (outside the building on the plan where space allows)
    return


def _living_tag_spot(r):
    x0, y0, x1, y1 = r.rects[0]
    # find the largest free horizontal band between furniture in the living room
    ys = sorted([(f.y, f.y + f.d) for f in furn_g(within=r.rects[0]) if f.kind not in ("rug",)])
    best = None
    cur = y0 + 0.9
    for a, b in ys:
        if a - cur > 0.8 and (best is None or a - cur > best[1] - best[0]):
            best = (cur, a)
        cur = max(cur, b)
    if best is None:
        return (x0 + x1) / 2, (y0 + y1) / 2
    return (x0 + x1) / 2, (best[0] + best[1]) / 2 + 0.15


def plan_dims(v):
    ww = west_wall_g()
    sw = south_wall_g()
    x_out = CROP[0]
    # west chain (openings)
    ys = [CROP[1], CROP[3]] + [p for o in ww.openings for p in (o.pos, o.end)]
    v.dim_chain(ys, 0, axis="y", at=x_out - 0.38, size=2.0)
    v.dim_chain([CROP[1], CROP[3]], 0, axis="y", at=x_out - 0.68, size=2.0)
    xs = [CROP[0], CROP[2]] + [p for o in sw.openings for p in (o.pos, o.end)]
    v.dim_chain(xs, 0, axis="x", at=CROP[1] - 0.36, size=2.0)
    axes = [CROP[0], CROP[2]] + [r for r in (rrect_of("G1")[2], rrect_of("G2")[2]) if r]
    v.dim_chain(axes, 0, axis="x", at=CROP[1] - 0.66, size=2.0)


def kitchen_dims(v):
    isl = furn_g("island")
    if not isl:
        return
    f = isl[0]
    kr = rrect_of("G3")
    ix0, iy0, ix1, iy1 = frect(f)
    north = [ff for ff in furn_g(within=kr) if ff.kind in ("fridge", "counter", "closet") and ff.y > iy1]
    east = [ff for ff in furn_g(within=kr) if ff.kind in ("counter",) and ff.x > ix1]
    yn = min([ff.y for ff in north], default=kr[3])
    xe = min([ff.x for ff in east], default=kr[2])
    yd = iy1 + 0.22
    v.dim_chain([ix0, ix1, xe], 0, axis="x", at=yd, size=2.0)
    xd = (ix1 + xe) / 2
    v.dim_chain([kr[1], iy0, iy1, yn], 0, axis="y", at=xd, size=2.0)


# --------------------------------------------------------------------------- #
#  (b) Reflected ceiling & lighting plan 1:50
# --------------------------------------------------------------------------- #
CEIL_FILL = {3.10: "#ffffff", 3.00: "#f7f5f1", 2.95: "#f1ede6", 2.80: "#e6dfd3", 2.60: "#ddd5c8"}


class RCP:
    def __init__(self, v):
        self.v = v
        self.sh = v.sh
        self.count = {}

    def n(self, key, k=1):
        self.count[key] = self.count.get(key, 0) + k

    # ---- planes
    def plane(self, x0, y0, x1, y1, h, cove=False, edge=True):
        v = self.v
        v.rect(x0, y0, x1, y1, fill=CEIL_FILL.get(h, "#fff"), lw="s" if edge else "xxs", color=INK if edge else "#bbb")
        if cove:
            d = 0.06
            v.rect(x0 + d, y0 + d, x1 - d, y1 - d, fill="none", lw="m", color=C_LIGHT, dash="2.2 0.8")
            self.n("L3", 2 * ((x1 - x0) + (y1 - y0)))

    def htag(self, x, y, h, size=2.0):
        sh = self.sh
        px, py = self.v.P(x, y)
        t = f"+{h:.2f}"
        w = tw(t, size) + 3.2
        rrect(sh, px - w / 2, py - 1.9, w, 3.4, 1.6, lw="xs", fill="#fff")
        sh.path(f"M{px - w / 2 + 1.0},{py - 0.9} l1.0,1.5 l1.0,-1.5 Z", lw="xxs", fill="#000")
        sh.text(px + 1.0, py + 0.75, t, size=size, weight=600)

    # ---- symbols
    def downlight(self, x, y):
        px, py = self.v.P(x, y)
        self.sh.circle(px, py, 1.15, lw="xs", fill="#fff")
        self.sh.circle(px, py, 0.45, lw="xxs", fill=C_LIGHT, color=C_LIGHT)
        self.n("L1")

    def spot(self, x, y, ang=90):
        px, py = self.v.P(x, y)
        self.sh.circle(px, py, 1.15, lw="xs", fill="#fff")
        a = math.radians(-ang)
        self.sh.line(px, py, px + 2.0 * math.cos(a), py + 2.0 * math.sin(a), lw="xs", color=C_LIGHT)
        self.sh.circle(px, py, 0.4, lw="xxs", fill=C_LIGHT, color=C_LIGHT)
        self.n("L2")

    def linear(self, x0, y0, x1, y1, key="L4"):
        v = self.v
        if abs(y1 - y0) < 1e-6:
            v.rect(x0, y0 - 0.025, x1, y0 + 0.025, fill="#f3d9ad", lw="xs", color=C_LIGHT)
        else:
            v.rect(x0 - 0.025, y0, x0 + 0.025, y1, fill="#f3d9ad", lw="xs", color=C_LIGHT)
        self.n(key, math.hypot(x1 - x0, y1 - y0))

    def grazer(self, x0, y0, x1, y1):
        v = self.v
        v.line(x0, y0, x1, y1, lw="l", color=C_LIGHT)
        L = math.hypot(x1 - x0, y1 - y0)
        n = int(L / 0.25)
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            y = y0 + (y1 - y0) * i / n
            v.line(x, y, x, y + 0.08, lw="xxs", color=C_LIGHT)
        self.n("L5", L)

    def pendant(self, x, y):
        px, py = self.v.P(x, y)
        self.sh.circle(px, py, 2.4, lw="xs", fill="#fff", color=INK)
        self.sh.circle(px, py, 1.3, lw="xxs", fill=C_BRASS, color=INK)
        self.sh.line(px - 2.4, py, px + 2.4, py, lw="xxs")
        self.sh.line(px, py - 2.4, px, py + 2.4, lw="xxs")
        self.n("L6")

    def lin_pendant(self, x0, x1, y):
        v = self.v
        v.rect(x0, y - 0.05, x1, y + 0.05, fill=C_BRASS, lw="xs")
        for x in (x0 + 0.1, x1 - 0.1):
            px, py = v.P(x, y)
            self.sh.circle(px, py, 0.5, lw="xxs", fill="#fff")
        self.n("L7")

    def cluster(self, x, y):
        px, py = self.v.P(x, y)
        self.sh.circle(px, py, 6.0, lw="xxs", color=C_LIGHT, dash="1 0.7")
        for i, (dx, dy) in enumerate([(0, 0), (2.6, 1.2), (-2.4, 1.6), (1.4, -2.6), (-1.6, -2.2), (3.4, -1.0), (-3.6, -0.4)]):
            self.sh.circle(px + dx, py + dy, 0.9, lw="xxs", fill=C_BRASS)
        self.n("L9")

    def diffuser(self, x0, y0, x1, y1):
        v = self.v
        v.rect(x0, y0, x1, y1, fill="#e7f0f6", lw="xs", color=C_HVAC)
        if (x1 - x0) > (y1 - y0):
            ym = (y0 + y1) / 2
            v.line(x0 + 0.05, ym - 0.02, x1 - 0.05, ym - 0.02, lw="xxs", color=C_HVAC)
            v.line(x0 + 0.05, ym + 0.02, x1 - 0.05, ym + 0.02, lw="xxs", color=C_HVAC)
        else:
            xm = (x0 + x1) / 2
            v.line(xm - 0.02, y0 + 0.05, xm - 0.02, y1 - 0.05, lw="xxs", color=C_HVAC)
            v.line(xm + 0.02, y0 + 0.05, xm + 0.02, y1 - 0.05, lw="xxs", color=C_HVAC)
        self.n("M1")

    def grille(self, x0, y0, x1, y1):
        v = self.v
        v.rect(x0, y0, x1, y1, fill="#fff", lw="xs", color=C_HVAC)
        n = 6
        for i in range(1, n):
            x = x0 + (x1 - x0) * i / n
            v.line(x, y0, x, y1, lw="xxs", color=C_HVAC)
        self.n("M2")

    def ac_unit(self, x0, y0, x1, y1):
        v = self.v
        v.rect(x0, y0, x1, y1, fill="none", lw="xs", color=C_HVAC, dash="1.5 0.8")
        v.line(x0, y0, x1, y1, lw="xxs", color=C_HVAC, dash="1.5 0.8")
        self.n("M3")

    def access(self, x, y, s=0.6):
        v = self.v
        v.rect(x - s / 2, y - s / 2, x + s / 2, y + s / 2, fill="#fff", lw="xs", color=INK)
        v.rect(x - s / 2 + 0.04, y - s / 2 + 0.04, x + s / 2 - 0.04, y + s / 2 - 0.04, fill="none", lw="xxs", color=INK)
        self.n("M4")

    def smoke(self, x, y, heat=False):
        px, py = self.v.P(x, y)
        self.sh.circle(px, py, 1.5, lw="xs", fill="#fff", color=C_SAFE)
        self.sh.text(px, py + 0.75, "H" if heat else "S", size=2.0, weight=700, color=C_SAFE)
        self.n("S2" if heat else "S1")

    def speaker(self, x, y):
        px, py = self.v.P(x, y)
        self.sh.circle(px, py, 1.4, lw="xs", fill="#fff", color="#555")
        self.sh.circle(px, py, 0.7, lw="xxs", fill="none", color="#555")
        self.sh.circle(px, py, 0.2, lw="xxs", fill="#555", color="#555")
        self.n("A1")

    def keypad(self, x, y, horiz=True):
        px, py = self.v.P(x, y)
        w, h = (2.4, 1.4) if horiz else (1.4, 2.4)
        self.sh.rect(px - w / 2, py - h / 2, w, h, lw="xs", fill="#2a2622")
        for i in (-1, 0, 1):
            if horiz:
                self.sh.circle(px + i * 0.65, py, 0.22, lw="xxs", fill="#fff", color="#fff")
            else:
                self.sh.circle(px, py + i * 0.65, 0.22, lw="xxs", fill="#fff", color="#fff")
        self.n("K1")

    def curtain(self, x0, y0, x1, y1):
        self.v.line(x0, y0, x1, y1, lw="xs", color="#8e7f6a", dash="2.5 0.6 0.6 0.6")
        self.n("C1", math.hypot(x1 - x0, y1 - y0))

    def joinery_led(self, x0, y0, x1, y1):
        self.v.line(x0, y0, x1, y1, lw="s", color=C_LIGHT, dash="0.4 0.6", cap="round")
        self.n("L8", math.hypot(x1 - x0, y1 - y0))


def plan_rcp(sh, ox, oy, sc=50):
    v = View(sh, ox, oy, sc)
    R = RCP(v)
    G1, G2, G3, G4 = (rrect_of(n) for n in ("G1", "G2", "G3", "G4"))
    G5, G6, G7 = (rrect_of(n) for n in ("G5", "G6", "G7"))
    B = 0.90             # perimeter soffit width along the glazing
    HB, HC, HK = 2.95, 3.10, 2.80
    tags = []
    v.rect(*interior_rect(), fill=CEIL_FILL[HB], color="none")
    # ---------------- living
    x0, y0, x1, y1 = G1
    col_y = next((c.y for c in M.COLS if abs(c.x - x1 - 0.15) < 0.3 and y0 + 1 < c.y < y1 - 1), (y0 + y1) / 2)
    R.plane(x0, y0, x1, y1, HB)
    eb = 0.60
    c1 = (x0 + B, y0 + B, x1 - eb, col_y - 0.30)
    c2 = (x0 + B, col_y + 0.30, x1 - eb, y1)
    R.plane(*c1, HC, cove=True)
    R.plane(*c2, HC, cove=False)
    v.rect(c2[0] + 0.06, c2[1] + 0.06, c2[2] - 0.06, c2[3], fill="none", lw="m", color=C_LIGHT, dash="2.2 0.8")
    R.n("L3", 2 * (c2[2] - c2[0]) + 2 * (c2[3] - c2[1]))
    wdl = spread(y0 + B, y1, 2.0)
    tags += [((c1[0] + c1[2]) / 2 + 1.3, c1[3] - 0.45, HC), ((c2[0] + c2[2]) / 2 + 1.3, c2[1] + 0.55, HC),
             (x0 + 0.45, (wdl[-1] + wdl[-2]) / 2, HB)]
    # soffit lights
    for yy in wdl:
        R.downlight(x0 + 0.55, yy)
    for xx in spread(x0 + B, x1 - eb, 2.1):
        R.downlight(xx, y0 + 0.6)
    for yy in spread(col_y + 0.3, y1 - 0.5, 1.6):
        R.spot(x1 - 0.30, yy, ang=0)         # wash the bookcase / RC wall
    for yy in spread(y0 + B, col_y - 0.3, 1.6):
        R.downlight(x1 - 0.30, yy)
    R.curtain(x0 + 0.12, y0 + 0.15, x0 + 0.12, y1 - 0.2)
    R.curtain(x0 + 0.15, y0 + 0.12, x1 - 0.1, y0 + 0.12)
    R.diffuser(x0 + 1.4, y0 + 0.24, x1 - 1.0, y0 + 0.36)
    R.diffuser(x0 + 0.24, col_y + 0.9, x0 + 0.36, col_y + 3.3)
    R.grille(x1 - 0.45, col_y - 0.25, x1 - 0.15, col_y + 0.35)
    # beam band – linear profile
    R.linear(c1[0] + 0.3, col_y, c1[2] - 0.3, col_y)
    # coffers
    cx = (c1[0] + c1[2]) / 2
    for xx in (c1[0] + 1.0, c1[2] - 1.0):
        for yy in (c1[1] + 0.9, c1[3] - 0.9):
            R.downlight(xx, yy)
    g = fireplace_geom()
    R.grazer(g["sx0"] + 0.1, g["face"] - 0.10, g["sx1"] - 0.1, g["face"] - 0.10)
    for xx in (c2[0] + 1.0, c2[2] - 1.0):
        R.downlight(xx, c2[1] + 1.2)
        R.speaker(xx, (c2[1] + c2[3]) / 2 + 0.2)
    R.smoke(cx, (c2[1] + c2[3]) / 2 + 0.2)
    for a, b in [(x0, g["slots"][0].pos)] if g["slots"] else []:
        R.joinery_led(a + 0.05, g["face"] - 0.30, b - 0.05, g["face"] - 0.30)
    if g["slots"]:
        R.joinery_led(g["slots"][-1].end + 0.05, g["face"] - 0.30, x1 - 0.05, g["face"] - 0.30)
    R.joinery_led(g["sx0"] + 0.3, g["face"] - 0.42, g["sx1"] - 0.3, g["face"] - 0.42)   # TV niche
    R.keypad(x1 - 0.06, col_y - 0.75, horiz=False)
    # ---------------- dining
    x0, y0, x1, y1 = G2
    R.plane(x0, y0, x1, y1, HB)
    t = furn_g("table_rect", G2)
    if t:
        f = t[0]
        tc = (f.x + f.w / 2, f.y + f.d / 2)
        tl = max(f.w, f.d)
        horiz = f.w >= f.d
    else:
        tc, tl, horiz = ((x0 + x1) / 2, (y0 + y1) / 2), 3.0, True
    cw, chh = (tl + 1.0, 2.0) if horiz else (2.0, tl + 1.0)
    d1 = (max(x0 + 0.5, tc[0] - cw / 2), max(y0 + B, tc[1] - chh / 2), min(x1 - 0.5, tc[0] + cw / 2), min(y1 - 0.45, tc[1] + chh / 2))
    R.plane(*d1, HC, cove=True)
    v._coffers = [(d1[0], d1[2])]
    pl = tl * 0.55
    R.lin_pendant(tc[0] - pl / 2, tc[0] + pl / 2, tc[1])
    for xx in spread(x0 + 0.5, x1 - 0.5, 1.5):
        R.downlight(xx, y0 + 0.6)
    for xx in (d1[0] + 0.5, d1[2] - 0.5):
        R.speaker(xx, d1[1] + 0.45)
    R.curtain(x0 + 0.2, y0 + 0.12, x1 - 0.2, y0 + 0.12)
    R.diffuser(x0 + 0.8, y0 + 0.24, x1 - 0.8, y0 + 0.36)
    tags += [(d1[2] - 0.75, d1[3] - 0.32, HC), (x0 + 0.75, y1 - 0.30, HB)]
    # ---------------- kitchen
    x0, y0, x1, y1 = G3
    R.plane(x0, y0, x1, y1, HB)
    isl = furn_g("island", G3)
    north_run = [f for f in furn_g(within=G3) if f.kind in ("fridge", "counter", "closet") and f.y + f.d > y1 - 0.1 and f.d < 1.0]
    east_run = [f for f in furn_g(within=G3) if f.kind == "counter" and f.x + f.w > x1 - 0.1 and f.w < 1.0]
    yn = min([f.y for f in north_run], default=y1 - 0.62)
    R.plane(x0, yn, x1, y1, HK)
    tags.append((x0 + 0.65, (yn + y1) / 2, HK))
    if isl:
        f = isl[0]
        ix0, iy0, ix1, iy1 = frect(f)
        k1 = (ix0 - 0.30, max(y0 + B, iy0 - 0.30), ix1 + 0.30, min(yn - 0.15, iy1 + 0.30))
        R.plane(*k1, HC, cove=True)
        v._coffers.append((k1[0], k1[2]))
        Ln = max(f.w, f.d)
        horiz = f.w >= f.d
        for i in range(3):
            if horiz:
                R.pendant(ix0 + Ln * (i + 1) / 4, (iy0 + iy1) / 2)
            else:
                R.pendant((ix0 + ix1) / 2, iy0 + Ln * (i + 1) / 4)
        ya = (iy1 + yn) / 2
        for xx in spread(x0 + 0.2, (min([e.x for e in east_run], default=x1)) - 0.1, 1.2):
            R.downlight(xx, ya + 0.05)
        tags.append(((k1[0] + k1[2]) / 2, k1[1] + 0.25, HC))
    for e in east_run:
        R.linear(e.x - 0.12, max(e.y, y0 + B) + 0.1, e.x - 0.12, yn - 0.2)
    R.joinery_led(x0 + 0.1, yn + 0.05, x1 - 0.1, yn + 0.05)
    R.smoke(x0 + 0.55, y0 + 1.65, heat=True)
    R.diffuser(x0 + 2.9, y0 + 0.24, x1 - 0.5, y0 + 0.36)
    R.curtain(x0 + 0.25, y0 + 0.12, x0 + 2.75, y0 + 0.12)
    for xx in spread(x0 + 0.2, x1 - 0.8, 1.6):
        R.downlight(xx, y0 + 0.62)
    R.keypad(x0 + 1.1, y1 + 0.02)
    # ---------------- hall
    x0, y0, x1, y1 = G4
    R.plane(x0, y0, x1, y1, HC)
    st = next((s for s in M.STAIRS if s["level"] == "G"), None)
    if st:
        sx0, sy0, sx1, sy1 = M.ST["x0"], 27.98, M.ST["x1"], M.ST["yn"]
        for hole in [s for s in M.SLABS if abs(s.top - M.slab_top("U")) < 1e-6][0].holes:
            if hole[0] <= M.ST["x0"] + 0.01 and hole[2] >= M.ST["x1"] - 0.01:
                sx0, sy0, sx1, sy1 = hole
        v.rect(sx0, sy0, sx1, sy1, fill="#fff", lw="s", dash="3 1")
        v.line(sx0, sy0, sx1, sy1, lw="xxs", dash="3 1")
        v.line(sx0, sy1, sx1, sy0, lw="xxs", dash="3 1")
        R.cluster((sx0 + sx1) / 2, (sy0 + sy1) / 2 + 0.3)
        R.linear(sx1 + 0.12, y0 + 0.5, sx1 + 0.12, sy1 - 0.4)
        px, py = v.P((sx0 + sx1) / 2, sy0 + 0.35)
        sh.text(px, py, "חלל מדרגות", size=2.0, color="#555")
    L = M.LIFT
    v.rect(L["x0"] + 0.2, L["y0"] + 0.2, L["x1"] - 0.2, L["y1"], fill="pat:partition", lw="xs")
    for xx in spread(M.ST["x1"] + 0.4, x1 - 0.2, 1.4):
        R.downlight(xx, y0 + 0.75)
        R.downlight(xx, (y0 + L["y0"]) / 2 + 0.55)
    R.smoke(x1 - 0.9, (y0 + L["y0"]) / 2 - 0.25)
    R.grille(x1 - 0.95, L["y0"] - 0.55, x1 - 0.35, L["y0"] - 0.25)
    tags.append((x1 - 1.85, (y0 + L["y0"]) / 2 - 0.25, HC))
    # ---------------- lobby – smoked-oak slatted ceiling
    x0, y0, x1, y1 = G7
    v.rect(x0, y0, x1, y1, fill="#f2e8da", lw="s")
    yy = y0 + 0.12
    while yy < y1 - 0.05:
        v.line(x0 + 0.05, yy, x1 - 0.05, yy, lw=0.07, color="#9b7d60")
        yy += 0.15
    for yy in (y0 + 1.0, y1 - 1.0):
        R.linear(x0 + 0.4, yy, x1 - 0.6, yy)
    pv = [o for o in east_wall_g().openings if o.kind == "pivot"]
    if pv:
        R.downlight(x1 - 0.8, (pv[0].pos + pv[0].end) / 2)
    R.smoke((x0 + x1) / 2 - 0.6, (y0 + y1) / 2)
    R.joinery_led(x0 + 0.2, y1 - 0.66, x0 + 3.7, y1 - 0.66)
    R.keypad(x1 - 0.06, (pv[0].pos - 0.35) if pv else y0 + 1.5, horiz=False)
    tags.append((x0 + 1.1, (y0 + y1) / 2 - 0.15, HC))
    # ---------------- WC / pantry
    for rr, h in ((G5, 2.60), (G6, 2.60)):
        R.plane(*rr, h)
    x0, y0, x1, y1 = G5
    R.downlight((x0 + x1) / 2, (y0 + y1) / 2 + 0.3)
    R.joinery_led(x0 + 0.5, y0 + 0.15, x1 - 0.5, y0 + 0.15)
    tags.append(((x0 + x1) / 2, (y0 + y1) / 2 - 0.45, 2.60))
    x0, y0, x1, y1 = G6
    R.linear(x0 + 0.5, (y0 + y1) / 2, x1 - 0.5, (y0 + y1) / 2)
    R.ac_unit(x0 + 0.3, y0 + 0.25, x0 + 1.6, y0 + 0.95)
    R.ac_unit(x1 - 1.6, y0 + 0.25, x1 - 0.3, y0 + 0.95)
    R.access(x0 + 1.95, y0 + 0.6, 0.5)
    tags.append((x1 - 0.8, y1 - 0.45, 2.60))
    # walls on top
    draw_walls(v, outline="xl")
    draw_openings(v, swings=False, glass_only=True)
    for (x, y, h) in tags:
        R.htag(x, y, h)
    return v, R


def rcp_dims(v, R=None):
    G1 = rrect_of("G1")
    x0, y0, x1, y1 = G1
    col_y = next((c.y for c in M.COLS if abs(c.x - x1 - 0.15) < 0.3 and y0 + 1 < c.y < y1 - 1), (y0 + y1) / 2)
    v.dim_chain([CROP[1], y0, y0 + 0.9, col_y - 0.3, col_y + 0.3, y1, CROP[3]], 0, axis="y", at=CROP[0] - 0.38, size=2.0)
    xs = [CROP[0], x0, x0 + 0.9, x1 - 0.6, x1, CROP[2]]
    for (a, b) in getattr(v, "_coffers", []):
        xs += [a, b]
    v.dim_chain(xs, 0, axis="x", at=CROP[1] - 0.36, size=2.0)


# --------------------------------------------------------------------------- #
#  (c) Flooring plan 1:100
# --------------------------------------------------------------------------- #
def plan_flooring(sh, ox, oy, sc=100):
    v = View(sh, ox, oy, sc)
    X0, Y0 = tile_origin()
    G1 = rrect_of("G1")
    # outdoor porcelain continuing to the covered terrace (south of living) – same grid
    sw = south_wall_g()
    ter = (CROP[0], 19.2, G1[2] + 0.3, sw.c - sw.t / 2)
    v.rect(*ter, fill="#efe6d7", color="none")
    _grid(v, ter, X0, Y0, "#b9a88e", 0.07)
    v.rect(*ter, fill="none", lw="xxs", color="#777", dash="1.2 0.8")
    deck = (G1[2] + 0.3, 19.6, 21.8, sw.c - sw.t / 2)
    v.rect(*deck, fill="pat:deck", lw="xxs", color="#777")
    # interior
    r = interior_rect()
    v.rect(*r, fill=pat(sh, "ix_por"), color="none")
    _grid(v, r, X0, Y0, "#a8977c", 0.08)
    lob = rrect_of("G7")
    v.rect(*lob, fill=pat(sh, "ix_kurkar"), color="none")
    _bond(v, lob, 1.20, 0.60, "#8b7457")
    wc = rrect_of("G5")
    v.rect(*wc, fill="#e9e6e1", color="none")
    _bond(v, wc, 0.60, 1.20, "#9b948a", stack=True)
    pa = rrect_of("G6")
    v.rect(*pa, fill="#e4e1db", color="none")
    _grid(v, pa, pa[0], pa[1], "#9b948a", 0.06, step=0.6)
    # stair / lift
    draw_stairs(v, light=True)
    L = M.LIFT
    v.rect(L["x0"] + 0.2, L["y0"] + 0.2, L["x1"] - 0.2, L["y1"], fill="pat:partition", lw="xs")
    draw_walls(v, outline="l")
    draw_openings(v, swings=True, glass_only=True)
    # thresholds – brushed brass T-profile between floor finishes
    G4 = rrect_of("G4")
    yy0 = max(lob[1], G4[1])
    v.line(lob[0] - 0.06, yy0, lob[0] - 0.06, lob[3], lw="l", color=C_BRASS)
    for w in cut_walls():
        if w.kind == "ext":
            continue
        for o in w.openings:
            if o.kind == "door":
                if w.horiz:
                    v.line(o.pos, w.c, o.end, w.c, lw="l", color=C_BRASS)
                else:
                    v.line(w.c, o.pos, w.c, o.end, lw="l", color=C_BRASS)
    # flush threshold + linear drain at the garden sliders
    for o in sw.openings:
        if o.kind == "slide":
            y_out = sw.c - sw.t / 2 - 0.08
            v.line(o.pos, y_out, o.end, y_out, lw="m", color="#555", dash="0.6 0.4")
    # start point
    px, py = v.P(X0, Y0)
    sh.circle(px, py, 1.6, lw="s", fill="#fff", color=C_SAFE)
    sh.circle(px, py, 0.5, lw="xxs", fill=C_SAFE, color=C_SAFE)
    sh.line(px, py, px + 7, py - 7, lw="xs", color=C_SAFE)
    sh.line(px, py, px - 7, py - 7, lw="xs", color=C_SAFE)
    for ex, ey in ((px + 7, py - 7), (px - 7, py - 7)):
        pass
    sh.text(px, py - 8.3, "נקודת התחלה", size=2.0, weight=700, color=C_SAFE)
    # axis of fireplace
    g = fireplace_geom()
    ax0 = v.P(g["axis"], Y0 + 0.2)
    ax1 = v.P(g["axis"], g["face"] - 0.1)
    sh.line(ax0[0], ax0[1], ax1[0], ax1[1], lw="xxs", color=C_SAFE, dash="3 0.8 0.6 0.8")
    tx, ty = v.P(g["axis"], g["face"] - 3.2)
    sh.text(tx + 1.2, ty, "ציר האח = מרכז אריח", size=2.0, color=C_SAFE, anchor="left", rot=-90)
    # labels
    for n, t in (("G1", "FL-01"), ("G2", "FL-01"), ("G3", "FL-01"), ("G4", "FL-01"), ("G7", "ST-02"), ("G5", "FL-03"),
                 ("G6", "FL-04")):
        r = rrect_of(n)
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        if n == "G4":
            cx, cy = r[2] - 1.3, r[1] + 1.0
        if n == "G1":
            cy = r[1] + 2.4
        px, py = v.P(cx, cy)
        code_tag(sh, px, py, t, fill="#fffdf8")
    px, py = v.P((ter[0] + ter[2]) / 2, (ter[1] + ter[3]) / 2)
    code_tag(sh, px, py, "FL-02", fill="#fffdf8")
    px, py = v.P((deck[0] + deck[2]) / 2, (deck[1] + deck[3]) / 2)
    sh.text(px, py + 0.7, "דק (לפי תכנית פיתוח)", size=2.0, color="#555")
    return v


def _grid(v, r, X0, Y0, col, lw, step=1.2):
    x0, y0, x1, y1 = r
    k = math.ceil((x0 - X0) / step - 1e-9)
    while X0 + k * step < x1 - 1e-6:
        xx = X0 + k * step
        v.line(xx, y0, xx, y1, lw=lw, color=col)
        k += 1
    k = math.ceil((y0 - Y0) / step - 1e-9)
    while Y0 + k * step < y1 - 1e-6:
        yy = Y0 + k * step
        v.line(x0, yy, x1, yy, lw=lw, color=col)
        k += 1


def _bond(v, r, a, b, col, stack=False):
    """running bond a (along x) × b (along y)"""
    x0, y0, x1, y1 = r
    yy = y0
    row = 0
    while yy < y1 - 1e-6:
        y2 = min(y1, yy + b)
        v.line(x0, yy, x1, yy, lw=0.07, color=col)
        off = 0 if (stack or row % 2 == 0) else a / 2
        xx = x0 + off
        while xx < x1 - 1e-6:
            if xx > x0 + 1e-6:
                v.line(xx, yy, xx, y2, lw=0.07, color=col)
            xx += a
        yy += b
        row += 1


# --------------------------------------------------------------------------- #
#  (d) Elevations 1-1 / 2-2 at 1:50
# --------------------------------------------------------------------------- #
def _sec_frame(v, sh, xa, xb, cut_left=None, cut_right=None, ceil=None):
    """floor & upper slab in section, end walls cut."""
    z_fin_u = M.LV["U"]
    sb = M.slab_bot("U")
    st = M.slab_top("U")
    # floor
    v.rect(xa, -0.40, xb, -0.10, fill="pat:rc", lw="m")
    v.rect(xa, -0.10, xb, 0.0, fill=pat(sh, "ix_screed"), lw="xs")
    v.line(xa, 0.0, xb, 0.0, lw="m")
    # upper slab
    v.rect(xa, sb, xb, st, fill="pat:rc", lw="m")
    v.rect(xa, st, xb, z_fin_u, fill=pat(sh, "ix_screed"), lw="xs")
    # break lines at the ends
    for x in (xa, xb):
        for (z0, z1) in ((-0.48, 0.05), (sb - 0.05, z_fin_u + 0.08)):
            pass
    if cut_left:
        cut_left()
    if cut_right:
        cut_right()


def _ext_wall_cut(v, sh, x_out, x_in, z0, z1, openings=()):
    """exterior wall (vertical in section) between x_out (outer face) and x_in (inner face)."""
    sk = M.T_SKIN if x_in > x_out else -M.T_SKIN
    xo, xi = sorted((x_out, x_in))
    xs0, xs1 = sorted((x_out, x_out + sk))
    xc0, xc1 = sorted((x_out + sk, x_in))
    segs = [(z0, z1)]
    for (a, b) in openings:
        new = []
        for (s0, s1) in segs:
            if b <= s0 or a >= s1:
                new.append((s0, s1))
            else:
                if a > s0:
                    new.append((s0, a))
                if b < s1:
                    new.append((b, s1))
        segs = new
    for (s0, s1) in segs:
        v.rect(xc0, s0, xc1, s1, fill="pat:block", lw="l")
        v.rect(xs0, s0, xs1, s1, fill="pat:stone", lw="s")
    for (a, b) in openings:
        v.rect(xo, a, xi, b, fill=C_GLASS, lw="xs")
        v.line((xo + xi) / 2, a, (xo + xi) / 2, b, lw="xs")


def elevation_fireplace(sh, ox, oy, items_out):
    """1-1: fireplace wall (living, north), looking north."""
    v = View(sh, ox, oy, 50)
    g = fireplace_geom()
    lv = g["lv"]
    x0, x1 = lv[0], lv[2]
    ww = west_wall_g()
    xa = ww.c - ww.t / 2
    # east boundary: wall right of living
    ewall = [w for w in M.walls_on("G") if not w.horiz and abs((w.c - w.t / 2) - x1) < 0.05]
    xb = (ewall[0].c + ewall[0].t / 2) if ewall else x1 + 0.12
    HB, HC = 2.95, 3.10
    col_y = None
    # back wall finish
    v.rect(x0, 0, x1, HC, fill="#f1e9de", lw="xs")
    # slots
    for o in g["slots"]:
        v.rect(o.pos, o.sill, o.end, o.head, fill=C_GLASS, lw="s")
        v.rect(o.pos + 0.03, o.sill + 0.03, o.end - 0.03, o.head - 0.03, fill="none", lw="xxs")
        v.line(o.pos + 0.08, o.sill + 0.25, o.end - 0.25, o.sill + 0.9, lw="xxs", color="#9ab")
        v.line(o.pos + 0.2, o.sill + 1.2, o.end - 0.1, o.sill + 1.6, lw="xxs", color="#9ab")
    # stone breast with large-format book-matched slabs
    sx0, sx1 = g["sx0"], g["sx1"]
    v.rect(sx0, 0, sx1, HC, fill=pat(sh, "ix_trav"), lw="s")
    ncol = 3
    for i in range(1, ncol):
        x = sx0 + (sx1 - sx0) * i / ncol
        v.line(x, 0, x, HC, lw="xxs", color="#8d7556")
    zj = 0.40 + (HC - 0.40) / 2
    v.line(sx0, zj, sx1, zj, lw="xxs", color="#8d7556")
    # firebox
    fx0, fx1 = g["fx0"], g["fx1"]
    v.rect(fx0, 0.55, fx1, 0.95, fill="#1f1c1a", lw="s")
    flame = []
    for i in range(25):
        x = fx0 + 0.15 + (fx1 - fx0 - 0.3) * i / 24
        z = 0.62 + (0.18 if i % 2 else 0.05) + 0.04 * math.sin(i)
        flame.append((x, z))
    v.polygon([(fx0 + 0.15, 0.6)] + flame + [(fx1 - 0.15, 0.6)], fill="#e2913c", color="#c0661e", lw="xxs")
    v.rect(fx0 + 0.12, 0.57, fx1 - 0.12, 0.62, fill="#555", color="none")
    # TV niche (oak-lined) + TV
    ax = g["axis"]
    nz0, nz1 = 1.45, 2.50
    nw = 1.80
    v.rect(ax - nw / 2, nz0, ax + nw / 2, nz1, fill=pat(sh, "ix_oak"), lw="s")
    v.rect(ax - 0.84, nz0 + 0.045, ax + 0.84, nz0 + 0.045 + 0.96, fill="#1d1c1b", lw="xs")
    v.line(ax - nw / 2 + 0.03, nz1 - 0.03, ax + nw / 2 - 0.03, nz1 - 0.03, lw="xs", color=C_LIGHT, dash="0.4 0.5")
    # floating hearth bench
    v.rect(sx0, 0.32, sx1, 0.40, fill=pat(sh, "ix_trav"), lw="s")
    v.line(sx0 + 0.05, 0.31, sx1 - 0.05, 0.31, lw="xs", color=C_LIGHT, dash="0.4 0.5")
    # shelving bays
    bays = []
    if g["slots"]:
        if g["slots"][0].pos - x0 > 0.3:
            bays.append((x0, g["slots"][0].pos))
        if x1 - g["slots"][-1].end > 0.3:
            bays.append((g["slots"][-1].end, x1))
    for a, b in bays:
        v.rect(a, 0.0, b, 0.45, fill=pat(sh, "ix_oak"), lw="s")
        v.rect(a, 0.0, b, 0.06, fill="#2a2622", color="none")
        v.line((a + b) / 2, 0.08, (a + b) / 2, 0.43, lw="xxs", color="#d9c2a2")
        for zs in (0.90, 1.35, 1.80, 2.25, 2.70):
            v.rect(a, zs, b, zs + 0.04, fill=pat(sh, "ix_oak"), lw="xs")
            v.line(a + 0.03, zs - 0.01, b - 0.03, zs - 0.01, lw="xxs", color=C_LIGHT, dash="0.4 0.5")
        # styling objects
        w = b - a
        v.rect(a + 0.08, 0.94, a + 0.08 + w * 0.35, 1.20, fill="#e9e0d1", lw="xxs")
        v.polygon([(b - 0.25, 1.39), (b - 0.12, 1.39), (b - 0.1, 1.62), (b - 0.27, 1.62)], fill="#cdb79a", lw="xxs")
        v.circle(a + w * 0.5, 1.92, 0.07, fill="#b29c80", lw="xxs")
        for i in range(5):
            v.rect(a + 0.1 + i * 0.05, 2.29, a + 0.14 + i * 0.05, 2.29 + 0.22 - 0.02 * (i % 2), fill="#d9cdb9", lw="xxs")
    # ceiling (cut at the section line, x-direction): soffit W & E, coffer between
    eb = 0.60
    v.rect(x0, HB, x0 + 0.90, HB + 0.0125, fill="#000", color="none")
    v.rect(x1 - eb, HB, x1, HB + 0.0125, fill="#000", color="none")
    v.rect(x0 + 0.90, HC, x1 - eb, HC + 0.0125, fill="#000", color="none")
    for xx in (x0 + 0.90, x1 - eb):
        v.line(xx, HB, xx, HB + 0.07, lw="m")
        v.line(xx, HB + 0.07, xx + (0.06 if xx < ax else -0.06), HB + 0.07, lw="s")
        px, py = v.P(xx + (0.03 if xx < ax else -0.03), HB + 0.05)
        sh.circle(px, py, 0.5, lw="xxs", fill=C_LIGHT, color=C_LIGHT)
        v.line(xx, HB + 0.07, xx, HC, lw="xxs", dash="0.8 0.5")
    for xx in spread(x0 + 0.4, x1 - 0.4, 0.9):
        v.line(xx, HC + 0.013 if x0 + 0.9 < xx < x1 - eb else HB + 0.013, xx, M.slab_bot("U"), lw="xxs", color="#888")
    # grazer
    px, py = v.P(sx0 + 0.1, HC)
    v.line(sx0 + 0.1, HC - 0.02, sx1 - 0.1, HC - 0.02, lw="l", color=C_LIGHT)
    # end walls (cut)
    _ext_wall_cut(v, sh, xa - M.T_SKIN * 0 if False else ww.c - ww.t / 2, x0, -0.10, M.slab_bot("U"))
    if ewall:
        w = ewall[0]
        v.rect(w.c - w.t / 2, -0.10, w.c + w.t / 2, M.slab_bot("U"), fill="pat:rc", lw="l")
    _sec_frame(v, sh, xa, xb)
    # dims
    xs = [x0, x1, sx0, sx1, fx0, fx1] + [p for o in g["slots"] for p in (o.pos, o.end)]
    v.dim_chain(xs, 0, axis="x", at=-0.70, size=2.0)
    v.dim_chain([0, 0.40, 0.95, nz0, nz1, HB, HC], 0, axis="y", at=xb + 0.35, size=2.0)
    v.level_mark(xa - 0.05, 0.0, 0.0, side="left")
    v.level_mark(xa - 0.05, HC, HC, side="left")
    v.level_mark(xa - 0.05, M.LV["U"], M.LV["U"], side="left")
    # callouts
    P = v.P
    items_out += [
        (*P(sx1 - 0.3, 2.85), ["ST-01 חיפוי טרוורטין 3 ס\"מ, לוחות בפורמט גדול", "הנחת ספר-פתוח (Book-match), מישק 2 מ\"מ"]),
        (*P(fx1 - 0.2, 0.80), ["אח ביו-אתנול – פתח 240/40, מבער 180 ס\"מ", "תא אש מבודד, זכוכית מגן, שלט חכם"]),
        (*P(ax + nw / 2 - 0.08, 2.2), ["נישת TV 180/105 מצופה WD-01, LED עקיף"]),
        (*P(sx1 - 0.1, 0.36), ["ספסל אח צף – טרוורטין 4 ס\"מ, LED בחריץ"]),
        (*P(x1 - 0.2, 2.25), ["מדפי אלון מעושן WD-01 4 ס\"מ צפים + LED"]),
        (*P(x1 - 0.2, 0.25), ["ארון בסיס – חזיתות WD-01, פתיחת לחיצה"]),
        (*P(g["slots"][-1].pos + 0.3 if g["slots"] else x1 - 1, 1.2), ["חלון צר AL-07, פרופיל נסתר"]),
        (*P(x1 - 0.3, HB + 0.006), ["סינר גבס +2.95 | תקרה מורמת +3.10 + קוב LED"]),
        (*P((sx0 + sx1) / 2 - 0.6, HC - 0.02), ["Wall-grazer לינארי לקיר האבן"]),
    ]
    return v, xb


def elevation_kitchen(sh, ox, oy, items_out, y_cut):
    """2-2: kitchen wall (north run), looking north."""
    v = View(sh, ox, oy, 50)
    kr = rrect_of("G3")
    x0, x1 = kr[0], kr[2]
    ew = east_wall_g()
    xb = ew.c + ew.t / 2
    xa = x0 - 0.4
    HB, HK = 2.95, 2.80
    run = sorted([f for f in furn_g(within=kr) if f.kind in ("fridge", "counter", "closet") and f.y + f.d > kr[3] - 0.1
                  and f.d < 1.0], key=lambda f: f.x)
    east = [f for f in furn_g(within=kr) if f.kind == "counter" and f.x + f.w > x1 - 0.1 and f.w < 1.0]
    # back wall
    nwall = [w for w in M.walls_on("G") if w.horiz and abs((w.c - w.t / 2) - kr[3]) < 0.08]
    v.rect(x0, 0, x1, HK, fill="#f1e9de", lw="xs")
    # pantry door in the back wall
    if nwall:
        for o in nwall[0].openings:
            if o.kind == "door":
                v.rect(o.pos - 0.05, 0, o.end + 0.05, o.head + 0.05, fill=pat(sh, "ix_oak"), lw="s")
                v.rect(o.pos, 0, o.end, o.head, fill="#a58668", lw="xs")
                hx = o.end - 0.08 if o.hinge == "a" else o.pos + 0.08
                v.line(hx, 1.0, hx, 1.12, lw="m", color=C_BRASS)
                v.polyline([(o.pos, o.head), ((o.pos + o.end) / 2 if o.hinge == "b" else o.end, 0.0 if False else o.head / 2),
                            (o.pos, 0)] if o.hinge == "b" else [(o.end, o.head), (o.pos, o.head / 2), (o.end, 0)],
                           lw="xxs", dash="1 0.6", color="#555")
                items_out.append((*v.P((o.pos + o.end) / 2, 1.6), ["מעבר למזווה – משקוף עמוק מחופה WD-01,", f"דלת {o.tag} נגררת לגמר אלון"]))
                # bridge cabinet over the passage
                v.rect(o.pos - 0.10, o.head + 0.12, o.end + 0.10, HK, fill=pat(sh, "ix_oak"), lw="s")
                v.line(o.pos - 0.10, o.head + 0.12, o.end + 0.10, o.head + 0.12, lw="xs")
    for f in run:
        a, b = f.x, f.x + f.w
        if f.kind in ("fridge", "closet"):
            v.rect(a, 0.10, b, HK, fill=pat(sh, "ix_oak"), lw="s")
            v.rect(a + 0.02, 0.0, b - 0.02, 0.10, fill="#2a2622", color="none")
            if f.kind == "fridge":
                v.line(a, 2.17, b, 2.17, lw="xs")
                v.line(a + 0.01, 2.14, b - 0.01, 2.14, lw="xxs", color="#d9c2a2")
                items_out.append((*v.P((a + b) / 2, 1.4), ["מקרר אינטגרלי, חזית WD-01 ללא ידית"]))
            else:
                # oven tower: drawers, oven, compact steam, door
                n = max(1, round((b - a) / 0.6))
                for i in range(n + 1):
                    pass
                v.line(a, 0.70, b, 0.70, lw="xs")
                v.line(a, 0.40, b, 0.40, lw="xs")
                v.rect(a + 0.03, 0.72, b - 0.03, 1.32, fill="#2b2a29", lw="xs")
                v.rect(a + 0.08, 0.80, b - 0.08, 1.18, fill="#4a4846", color="none")
                v.line(a + 0.1, 1.26, b - 0.1, 1.26, lw="s", color=C_BRASS)
                v.rect(a + 0.03, 1.34, b - 0.03, 1.79, fill="#2b2a29", lw="xs")
                v.rect(a + 0.08, 1.40, b - 0.08, 1.66, fill="#4a4846", color="none")
                v.line(a + 0.1, 1.73, b - 0.1, 1.73, lw="s", color=C_BRASS)
                v.line(a, 2.17, b, 2.17, lw="xs")
                items_out.append((*v.P((a + b) / 2, 1.05), ["תנור + תנור קיטור קומפקטי בגובה עבודה"]))
            v.line(a, 0.10, a, HK, lw="s")
            v.line(b, 0.10, b, HK, lw="s")
        elif f.kind == "counter":
            # base run with drawers, travertine splash, floating shelf, upper pocket-door unit
            v.rect(a, 0.10, b, 0.90, fill=pat(sh, "ix_oak"), lw="s")
            v.rect(a + 0.02, 0.0, b - 0.02, 0.10, fill="#2a2622", color="none")
            v.rect(a, 0.90, b, 0.92, fill=pat(sh, "ix_sint"), lw="s")
            for z in (0.40, 0.66):
                v.line(a, z, b, z, lw="xs")
                v.line(a + 0.02, z - 0.025, b - 0.02, z - 0.025, lw="xxs", color="#d9c2a2")
            n = max(1, round((b - a) / 0.6))
            for i in range(1, n):
                xx = a + (b - a) * i / n
                v.line(xx, 0.10, xx, 0.90, lw="xs")
            v.line(a + 0.02, 0.875, b - 0.02, 0.875, lw="xxs", color="#d9c2a2")
            v.rect(a, 0.92, b, 1.55, fill=pat(sh, "ix_trav"), lw="xs")
            v.rect(a, 1.55, b, HK, fill=pat(sh, "ix_oak"), lw="s")
            v.line(a, 1.57, b, 1.57, lw="xs", color=C_LIGHT, dash="0.4 0.5")
            for i in range(1, n):
                xx = a + (b - a) * i / n
                v.line(xx, 1.55, xx, HK, lw="xs")
            items_out.append((*v.P(a + 0.3, 1.25), ["נישת קפה/בוקר – חיפוי ST-01, LED,", "ארונות עליונים בדלתות כיס"]))
            items_out.append((*v.P(a + 0.35, 0.91), ["משטח אבן סינטר SS-01 2 ס\"מ"]))
            items_out.append((*v.P(a + 0.2, 0.30), ["מגירות ללא ידיות (פרופיל J), WD-01"]))
    # east counter in section at the corner
    for f in east:
        a = f.x
        v.rect(a, 0.10, x1, 0.90, fill=pat(sh, "ix_mdf"), lw="l")
        v.rect(a - 0.02, 0.90, x1, 0.92, fill=pat(sh, "ix_sint"), lw="l")
        v.rect(a + 0.06, 0.0, x1, 0.10, fill="#2a2622", lw="s")
        v.rect(x1 - 0.02, 0.92, x1, 1.05, fill=pat(sh, "ix_trav"), lw="s")
    # bulkhead
    v.rect(x0, HK, x1, HB, fill="#fff", lw="s")
    # ceiling cut
    v.rect(xa, HB, x1, HB + 0.0125, fill="#000", color="none")
    for xx in spread(xa + 0.2, x1 - 0.2, 0.9):
        v.line(xx, HB + 0.013, xx, M.slab_bot("U"), lw="xxs", color="#888")
    # east wall cut with window (at the cut line)
    win = [(o.sill, o.head) for o in ew.openings if o.pos <= y_cut <= o.end]
    _ext_wall_cut(v, sh, xb, ew.c - ew.t / 2, -0.10, M.slab_bot("U"), openings=win)
    # west – open to dining: break line
    _sec_frame(v, sh, xa, xb)
    v.line(xa, -0.5, xa, M.LV["U"] + 0.1, lw="xxs", dash="4 1 1 1")
    # dims
    xs = sorted(set(round(p, 3) for p in [x0, x1] + [p for f in run for p in (f.x, f.x + f.w)] + [f.x for f in east]))
    xs = [p for i, p in enumerate(xs) if i == 0 or p - xs[i - 1] > 0.15 or i == len(xs) - 1]
    v.dim_chain(xs, 0, axis="x", at=-0.70, size=2.0)
    v.dim_chain([0, 0.10, 0.92, 1.55, 2.17, HK, HB], 0, axis="y", at=xa - 0.30, size=2.0)
    v.level_mark(xa - 0.5, 0.0, 0.0, side="left")
    v.level_mark(xa - 0.5, HB, HB, side="left")
    v.level_mark(xa - 0.5, M.LV["U"], M.LV["U"], side="left")
    items_out += [
        (*v.P(x1 - 0.8, HK + 0.07), ["סינר גבס +2.80, צללית 10 מ\"מ, תקרה +2.95"]),
        (*v.P(x1 - 0.1, 1.7), ["חלון AL-10, אדן +1.05"]),
        (*v.P(x1 - 0.35, 0.05), ["סוקל שקוע 10 ס\"מ – פליז מוברש MT-01"]),
    ]
    return v, xa, xb


def threshold_detail(sh, x_right, y_top):
    """Flush threshold at the pocket slider – section 1:10 (indoor porcelain continues outside)."""
    k = 100.0
    xa, xb, za, zb = -0.30, 0.30, -0.30, 0.12
    ox = x_right - xb * k
    oy = y_top + 9 + zb * k
    v = View(sh, ox, oy, 10)
    sh.text(x_right, y_top + 3.5, "פרט סף ויטרינה שטוח (פנים-חוץ)", size=3.0, anchor="right", weight=700)
    sh.text(x_right - tw("פרט סף ויטרינה שטוח (פנים-חוץ)", 3.0) - 3, y_top + 3.5, 'קנ"מ 1:10', size=2.2, anchor="right")
    sh.begin_clip(ox + xa * k, oy - zb * k, (xb - xa) * k, (zb - za) * k)
    # slabs
    v.polygon([(xa, -0.40), (0.06, -0.40), (0.06, -0.45), (xb, -0.45), (xb, -0.15), (0.06, -0.15), (0.06, -0.10), (xa, -0.10)],
              fill="pat:rc", lw="m")
    v.rect(xa, -0.10, -0.06, -0.009, fill=pat(sh, "ix_screed"), lw="xs")
    v.rect(xa, -0.009, -0.06, 0.0, fill="#d9ccb6", lw="s")
    for xx in (-0.06 - 1.2 * i for i in range(1)):
        pass
    # membrane up-stand
    v.polyline([(xb, -0.15), (0.06, -0.15), (0.06, -0.10), (0.065, -0.02)], lw="l", color="#111")
    # recessed bottom track
    v.rect(-0.06, -0.075, 0.06, 0.0, fill=pat(sh, "ix_alu"), lw="s")
    v.rect(-0.05, -0.065, 0.05, -0.005, fill="#fff", lw="xxs")
    for gx in (-0.03, 0.012):
        v.rect(gx, 0.012, gx + 0.018, zb + 0.01, fill=C_GLASS, lw="xs")
        v.circle(gx + 0.009, -0.005, 0.008, lw="xxs", fill="#555")
    # outdoor build-up + linear drain
    v.polygon([(0.08, -0.15), (xb, -0.15), (xb, -0.035), (0.18, -0.038), (0.18, -0.10), (0.08, -0.10)],
              fill=pat(sh, "ix_screed"), lw="xs")
    v.rect(0.065, -0.11, 0.17, 0.0, fill="#fff", lw="s")
    v.rect(0.075, -0.10, 0.16, -0.01, fill="#eee", lw="xxs")
    v.line(0.065, -0.004, 0.17, -0.004, lw="m", color="#555", dash="0.6 0.4")
    v.rect(0.17, -0.02, xb, 0.0, fill="#e2d6c2", lw="s")
    sh.end_group()
    sh.rect(ox + xa * k, oy - zb * k, (xb - xa) * k, (zb - za) * k, lw="xxs", color="#999")
    v.line(0.0, za, 0.0, zb, lw="xxs", color="#999", dash="3 0.8 0.6 0.8")
    v.text(-0.15, za + 0.035, "פנים", size=2.2, weight=700, color="#fff")
    v.text(0.22, za + 0.035, "חוץ", size=2.2, weight=700, color="#fff")
    items = [
        (*v.P(-0.02, 0.09), ["ויטרינה הזזה לכיס – זכוכית בידודית"]),
        (*v.P(0.25, -0.01), ["פורצלן חוץ FL-02 20 מ\"מ R11, מפלס זהה"]),
        (*v.P(-0.20, -0.004), ["פורצלן FL-01 9 מ\"מ, דבק C2TE"]),
        (*v.P(-0.00, -0.04), ["מסילה תחתונה שקועה, נירוסטה 316"]),
        (*v.P(0.12, -0.05), ["תעלת ניקוז לינארית + רשת פליז"]),
        (*v.P(0.064, -0.08), ["איטום מוגבה עד תחתית המסילה"]),
        (*v.P(-0.2, -0.25), ["תקרת בטון מזוין + מדה"]),
    ]
    callout_column(sh, items, ox + xa * k - 7, y_top + 7, oy - za * k, size=2.0, lh=2.5, gap=0.6, side="left", elbow=4,
                   keep_order=True)


# --------------------------------------------------------------------------- #
#  (e) Material palette
# --------------------------------------------------------------------------- #
PALETTE = [
    ("ST-01", "ix_trav", "טרוורטין קלאסי", "מושחז, ממולא | 3 ס\"מ", "קיר האח, ספסל", "TRV-CL-H30"),
    ("ST-02", "ix_kurkar", "אבן גיר גוון כורכר", "מוברש | 60/120/2", "רצפת לובי", "LMS-KR-B20"),
    ("FL-01", "ix_por", "פורצלן Sand Stone", "120/120 מט R10 / R11", "רצפות + מרפסת", "POR-SND-1212"),
    ("SS-01", "ix_sint", "אבן סינטר טרוורטין", "20 מ\"מ, מט", "משטחים, אי", "SNT-TRV-20"),
    ("WD-01", "ix_oak", "אלון מעושן", "פורניר, שמן-לכה מט", "נגרות, תקרת לובי", "OAK-SMK-V06"),
    ("WD-02", "ix_flute10", "אלון מעושן מחורץ", "מלא 22 מ\"מ, חריץ 20", "חזית אי המטבח", "OAK-FLT-22"),
    ("MT-01", "ix_brass", "פליז מוברש", "PVD, לכה מגינה", "פרופילים, סוקל", "BRS-BR-PVD"),
    ("TX-01", "ix_linen", "פשתן טבעי – חול", "וילון שקוף + ריפוד", "וילונות, ספות", "LIN-SND-280"),
    ("PT-01", "ix_mocha", "טיח סיד – מוקה בהיר", "Lime-wash, מט", "קירות", "LMW-MCH-02"),
    ("LT-01", "ix_leather", "עור נאפה מוקה", "עובי 1.2 מ\"מ", "כסאות, ידיות", "NAP-MCH-12"),
]


def palette_strip(sh, x, y, w, h):
    n = len(PALETTE)
    head = 30
    cw = (w - head) / n
    sh.rect(x, y, w, h, lw="xs", fill="#fbf8f3")
    # header block at the right
    hx = x + w - head
    sh.rect(hx, y, head, h, lw="xs", fill="#efe7da")
    sh.text(hx + head / 2, y + h / 2 - 2.5, "פלטת", size=4.0, weight=700, font="Frank Ruhl Libre")
    sh.text(hx + head / 2, y + h / 2 + 2.5, "חומרים", size=4.0, weight=700, font="Frank Ruhl Libre")
    sh.text(hx + head / 2, y + h / 2 + 7.5, "Quiet luxury", size=2.2, color="#6a5a48", italic=True)
    for i, (code, p, name, spec, use, sup) in enumerate(PALETTE):
        cx = hx - (i + 1) * cw
        sw_h = h * 0.40
        sh.rect(cx + 2, y + 2, cw - 4, sw_h, lw="xs", fill=pat(sh, p))
        sh.rect(cx + 2, y + 2, cw - 4, sw_h, lw="xs", fill="#ffffff", fop=0.0)
        xr = cx + cw - 2.5
        yy = y + 2 + sw_h + 4.0
        sh.text(xr, yy, code, size=2.6, weight=700, anchor="right")
        sh.text(cx + 2.5, yy, sup, size=2.0, anchor="left", color="#6a5a48")
        sh.text(xr, yy + 3.4, name, size=2.2, weight=600, anchor="right")
        sh.text(xr, yy + 6.5, spec, size=2.0, anchor="right", color="#333")
        sh.text(xr, yy + 9.4, use, size=2.0, anchor="right", color="#6a5a48")
        if i:
            sh.line(cx + cw, y + 2, cx + cw, y + h - 2, lw="xxs", color="#cfc5b5")


# --------------------------------------------------------------------------- #
#  Legends
# --------------------------------------------------------------------------- #
def lighting_legend(sh, x_right, y, R, w_total):
    c = R.count

    def sym(fn):
        return fn

    def s_down(sh, x0, y0, w, h):
        sh.circle(x0 + w / 2, y0 + h / 2, 1.15, lw="xs", fill="#fff")
        sh.circle(x0 + w / 2, y0 + h / 2, 0.45, lw="xxs", fill=C_LIGHT, color=C_LIGHT)

    def s_spot(sh, x0, y0, w, h):
        cx, cy = x0 + w / 2, y0 + h / 2
        sh.circle(cx, cy, 1.15, lw="xs", fill="#fff")
        sh.line(cx, cy, cx + 2, cy, lw="xs", color=C_LIGHT)
        sh.circle(cx, cy, 0.4, lw="xxs", fill=C_LIGHT, color=C_LIGHT)

    def s_cove(sh, x0, y0, w, h):
        sh.line(x0 + 2, y0 + h / 2, x0 + w - 2, y0 + h / 2, lw="m", color=C_LIGHT, dash="2.2 0.8")

    def s_lin(sh, x0, y0, w, h):
        sh.rect(x0 + 2, y0 + h / 2 - 0.5, w - 4, 1.0, lw="xs", color=C_LIGHT, fill="#f3d9ad")

    def s_graz(sh, x0, y0, w, h):
        sh.line(x0 + 2, y0 + h / 2, x0 + w - 2, y0 + h / 2, lw="l", color=C_LIGHT)
        for i in range(5):
            xx = x0 + 2 + (w - 4) * i / 4
            sh.line(xx, y0 + h / 2, xx, y0 + h / 2 - 1.2, lw="xxs", color=C_LIGHT)

    def s_pend(sh, x0, y0, w, h):
        cx, cy = x0 + w / 2, y0 + h / 2
        sh.circle(cx, cy, 2.0, lw="xs", fill="#fff")
        sh.circle(cx, cy, 1.1, lw="xxs", fill=C_BRASS)
        sh.line(cx - 2, cy, cx + 2, cy, lw="xxs")
        sh.line(cx, cy - 2, cx, cy + 2, lw="xxs")

    def s_lpend(sh, x0, y0, w, h):
        sh.rect(x0 + 2, y0 + h / 2 - 0.9, w - 4, 1.8, lw="xs", fill=C_BRASS)

    def s_led(sh, x0, y0, w, h):
        sh.line(x0 + 2, y0 + h / 2, x0 + w - 2, y0 + h / 2, lw="s", color=C_LIGHT, dash="0.4 0.6", cap="round")

    def s_clu(sh, x0, y0, w, h):
        cx, cy = x0 + w / 2, y0 + h / 2
        for dx, dy in [(0, 0), (1.8, 0.8), (-1.8, 0.9), (0.9, -1.3), (-1.0, -1.2)]:
            sh.circle(cx + dx, cy + dy, 0.6, lw="xxs", fill=C_BRASS)

    def s_diff(sh, x0, y0, w, h):
        sh.rect(x0 + 2, y0 + h / 2 - 0.9, w - 4, 1.8, lw="xs", color=C_HVAC, fill="#e7f0f6")
        sh.line(x0 + 3, y0 + h / 2 - 0.25, x0 + w - 3, y0 + h / 2 - 0.25, lw="xxs", color=C_HVAC)
        sh.line(x0 + 3, y0 + h / 2 + 0.25, x0 + w - 3, y0 + h / 2 + 0.25, lw="xxs", color=C_HVAC)

    def s_gr(sh, x0, y0, w, h):
        sh.rect(x0 + w / 2 - 3, y0 + h / 2 - 1.2, 6, 2.4, lw="xs", color=C_HVAC, fill="#fff")
        for i in range(1, 6):
            sh.line(x0 + w / 2 - 3 + i, y0 + h / 2 - 1.2, x0 + w / 2 - 3 + i, y0 + h / 2 + 1.2, lw="xxs", color=C_HVAC)

    def s_ac(sh, x0, y0, w, h):
        sh.rect(x0 + w / 2 - 4, y0 + h / 2 - 1.3, 8, 2.6, lw="xs", color=C_HVAC, dash="1.5 0.8")
        sh.line(x0 + w / 2 - 4, y0 + h / 2 - 1.3, x0 + w / 2 + 4, y0 + h / 2 + 1.3, lw="xxs", color=C_HVAC, dash="1.5 0.8")

    def s_sm(letter):
        def f(sh, x0, y0, w, h):
            sh.circle(x0 + w / 2, y0 + h / 2, 1.5, lw="xs", fill="#fff", color=C_SAFE)
            sh.text(x0 + w / 2, y0 + h / 2 + 0.75, letter, size=2.0, weight=700, color=C_SAFE)
        return f

    def s_spk(sh, x0, y0, w, h):
        cx, cy = x0 + w / 2, y0 + h / 2
        sh.circle(cx, cy, 1.4, lw="xs", fill="#fff", color="#555")
        sh.circle(cx, cy, 0.7, lw="xxs", color="#555")

    def s_key(sh, x0, y0, w, h):
        cx, cy = x0 + w / 2, y0 + h / 2
        sh.rect(cx - 1.2, cy - 0.7, 2.4, 1.4, lw="xs", fill="#2a2622")

    def s_cur(sh, x0, y0, w, h):
        sh.line(x0 + 2, y0 + h / 2, x0 + w - 2, y0 + h / 2, lw="xs", color="#8e7f6a", dash="2.5 0.6 0.6 0.6")

    def s_h(sh, x0, y0, w, h):
        cx, cy = x0 + w / 2, y0 + h / 2
        ww = 9
        rrect(sh, cx - ww / 2, cy - 1.6, ww, 3.2, 1.5, lw="xs", fill="#fff")
        sh.path(f"M{cx - ww / 2 + 0.9},{cy - 0.7} l0.9,1.3 l0.9,-1.3 Z", lw="xxs", fill="#000")
        sh.text(cx + 1.0, cy + 0.7, "+2.95", size=2.0, weight=600)

    def q(key, unit="יח'"):
        val = c.get(key, 0)
        if unit == "מ'":
            return f"{val:.0f} מ'"
        return f"{val}"

    rows = [
        (s_down, "L1", "ספוט שקוע Trimless Ø75, מוחשך", "10W 2700K CRI≥95 UGR<16, 36°", q("L1")),
        (s_spot, "L2", "ספוט שקוע מתכוונן (wall-wash)", "10W 2700K, 24°, הטיה 30°", q("L2")),
        (s_cove, "L3", "תאורת קוב LED בתקרה מורמת", "14W/מ' Dim-to-warm 3000→1800K", q("L3", "מ'")),
        (s_lin, "L4", "פרופיל לינארי שקוע 35 מ\"מ", "12W/מ' 3000K, מפזר אופל", q("L4", "מ'")),
        (s_graz, "L5", "Wall-grazer לינארי לקיר האבן", "15W/מ' 2700K, אופטיקה 10×60", q("L5", "מ'")),
        (s_pend, "L6", "גוף תלוי מעל האי – זכוכית מעושנת/פליז", "Ø25, 8W 2700K, גובה +1.65", q("L6")),
        (s_lpend, "L7", "גוף תלוי לינארי מעל שולחן האוכל", "פליז מוברש, 30W, גובה +1.60", q("L7")),
        (s_led, "L8", "פס LED בנגרות (מדפים, נישות, סוקל)", "6W/מ' 2700K, פרופיל אלומ'", q("L8", "מ'")),
        (s_clu, "L9", "גוף תלוי פיסולי בחלל המדרגות", "7 גופים, זכוכית + פליז", q("L9")),
        (s_diff, "M1", "מפזר אוויר לינארי (Slot) – אספקה", "2 חריצים, צבע לבן", q("M1")),
        (s_gr, "M2", "תריס אוויר חוזר", "60/30, בגוון התקרה", q("M2")),
        (s_ac, "M3", "יח' מיזוג מוסתרת (ת.ת. +2.60)", "מעל מזווה, גישה 50/50", q("M3")),
        (s_sm("S"), "S1", "גלאי עשן אופטי", "מחובר למערכת הבית החכם", q("S1")),
        (s_sm("H"), "S2", "גלאי חום (מטבח)", "", q("S2")),
        (s_spk, "A1", "רמקול תקרה שקוע", "Ø20, גריל דק בגוון התקרה", q("A1")),
        (s_key, "K1", "לוח סצנות חכם (KNX/DALI)", "גובה +1.10, זכוכית/פליז", q("K1")),
        (s_cur, "C1", "מסילת וילון שקועה (מנוע)", "פשתן TX-01, מסילה בסינר", q("C1", "מ'")),
        (s_h, "—", "גובה תחתית תקרה (ת.ת.) מ-±0.00", "", ""),
    ]
    cols = [("סמל", 14), ("קוד", 9), ("תיאור", 62), ("מפרט", 56), ("כמות", 13)]
    trs = [[r[0], r[1], r[2], r[3], r[4]] for r in rows]
    return table(sh, x_right, y, cols, trs, size=2.0, rh=5.0)


def scenes_table(sh, x_right, y):
    cols = [("סצנה", 16), ("תאורה פעילה", 60), ("עוצמה / גוון", 30)]
    rows = [
        ["בוקר", "L1 + L4 + L3 מטבח, וילונות פתוחים", "70% | 3000K"],
        ["ארוחה", "L7 + L6 + L3 פינת אוכל, L1 נמוך", "60% | 2700K"],
        ["ערב רגוע", "L3 + L5 + L8 + אח, L1 כבוי", "35% | 2200K"],
        ["קולנוע", "L8 נישת TV בלבד, וילונות סגורים", "10% | 1800K"],
        ["יציאה", "הכל כבוי, L4 לובי 10%, מיזוג Eco", "—"],
    ]
    return table(sh, x_right, y, cols, rows, size=2.0, rh=5.0, bold_first=True)


def flooring_legend(sh, x_right, y):
    def sw(fill, extra=None):
        def f(sh, x0, y0, w, h):
            sh.rect(x0 + 1.5, y0 + 0.8, w - 3, h - 1.6, lw="xs", fill=fill(sh) if callable(fill) else fill)
            if extra:
                extra(sh, x0, y0, w, h)
        return f

    def grid(sh, x0, y0, w, h):
        sh.line(x0 + w / 2, y0 + 0.8, x0 + w / 2, y0 + h - 0.8, lw="xxs", color="#8a7a62")

    def brass(sh, x0, y0, w, h):
        sh.line(x0 + 2, y0 + h / 2, x0 + w - 2, y0 + h / 2, lw="l", color=C_BRASS)

    def drain(sh, x0, y0, w, h):
        sh.line(x0 + 2, y0 + h / 2, x0 + w - 2, y0 + h / 2, lw="m", color="#555", dash="0.6 0.4")

    def start(sh, x0, y0, w, h):
        cx, cy = x0 + w / 2, y0 + h / 2
        sh.circle(cx, cy, 1.4, lw="s", fill="#fff", color=C_SAFE)
        sh.circle(cx, cy, 0.45, lw="xxs", fill=C_SAFE, color=C_SAFE)

    rows = [
        [sw(lambda s: pat(s, "ix_por"), grid), "FL-01", "פורצלן 120/120/0.9 מט R10, מישק 2 מ\"מ"],
        [sw("#efe6d7", grid), "FL-02", "פורצלן 120/120/2.0 R11 חוץ – המשך המישקים"],
        [sw(lambda s: pat(s, "ix_kurkar")), "ST-02", "אבן גיר כורכר 60/120 מוברשת, חצי-קשר"],
        [sw("#e9e6e1"), "FL-03", "פורצלן 60/120 – שירותי אורחים"],
        [sw("#e4e1db"), "FL-04", "פורצלן 60/60 – מזווה"],
        [brass, "TH-01", "פס מעבר פליז מוברש T-12, מפלס אחיד"],
        [drain, "DR-01", "סף שטוח + תעלת ניקוז לינארית (חוץ)"],
        [start, "SP", "נקודת התחלה – אריח שלם בויטרינה"],
    ]
    cols = [("סמל", 11), ("קוד", 11), ("תיאור", 76)]
    return table(sh, x_right, y, cols, rows, size=2.0, rh=4.8)


# --------------------------------------------------------------------------- #
#  Renders
# --------------------------------------------------------------------------- #
def render_frame(sh, x, y, w, h, fname, caption):
    path = os.path.join(ROOT, "out", "renders", fname)
    if os.path.exists(path):
        cid = sh.clip_rect(x, y, w, h)
        sh.add(f'<g clip-path="url(#{cid})">')
        sh.image(x, y, w, h, f"../renders/{fname}")
        sh.add("</g>")
        sh.rect(x, y, w, h, lw="s")
        sh.rect(x, y + h - 5.0, w, 5.0, color="none", fill="#ffffff", fop=0.82)
        sh.text(x + w - 2, y + h - 1.5, caption, size=2.4, anchor="right", weight=600)
    else:
        sh.rect(x, y, w, h, lw="s", fill="#f6f2ec")
        sh.line(x, y, x + w, y + h, lw="xxs", color="#d8cfc2")
        sh.line(x, y + h, x + w, y, lw="xxs", color="#d8cfc2")
        sh.rect(x + w / 2 - 32, y + h / 2 - 6, 64, 12, color="none", fill="#f6f2ec")
        sh.text(x + w / 2, y + h / 2 - 0.5, caption, size=3.0, weight=600, color="#8a7a66")
        sh.text(x + w / 2, y + h / 2 + 4.0, "הדמיה – בהכנה", size=2.4, color="#a89884")


# --------------------------------------------------------------------------- #
#  Sheet builder
# --------------------------------------------------------------------------- #
def sheet_interior(sh, box):
    bx, by, bw, bh = box
    k = 20.0
    # ---------------- left column: plans 1:50
    lx = bx + 18                    # paper x of model CROP x0
    ox = lx - CROP[0] * k
    top_a = by + 8
    oy_a = top_a + CROP[3] * k
    v, g, bays = plan_furniture(sh, ox, oy_a)
    annotate_furniture_plan(v, g, bays)
    plan_dims(v)
    kitchen_dims(v)
    # section markers
    face = g["face"]
    y1 = face - g["breast_d"] - g["bench_d"] - 0.55
    section_marker(v, CROP[0] - 0.15, y1, rrect_of("G1")[2] + 0.45, y1, "1", look=-1, size=2.6, r=2.8)
    kr = rrect_of("G3")
    isl = furn_g("island", kr)
    north_run = [f for f in furn_g(within=kr) if f.kind in ("fridge", "counter", "closet") and f.y > kr[1] + 2]
    yn = min([f.y for f in north_run], default=kr[3] - 0.62)
    y2 = ((isl[0].y + isl[0].d) + yn) / 2 if isl else yn - 0.6
    y2 = y2 + 0.18
    section_marker(v, kr[0] - 0.55, y2, CROP[2] + 0.45, y2, "2", look=-1, size=2.6, r=2.8)
    xr_plan = lx + (CROP[2] - CROP[0]) * k
    drawing_title(sh, xr_plan, oy_a - CROP[1] * k + 30, "תכנית ריהוט וגמרים – חלל המגורים", 'קנ"מ 1:50', width=110, size=6.0)
    # north arrow & notes left of title
    from draw import north_arrow
    north_arrow(sh, lx + 8, oy_a - CROP[1] * k + 32, r=5)
    _plan_note(sh, lx + 20, oy_a - CROP[1] * k + 25)

    # RCP
    top_b = oy_a - CROP[1] * k + 46
    oy_b = top_b + CROP[3] * k
    vb, R = plan_rcp(sh, ox, oy_b)
    rcp_dims(vb)
    drawing_title(sh, xr_plan, oy_b - CROP[1] * k + 22, "תכנית תקרה מוחזרת ותאורה", 'קנ"מ 1:50', width=110, size=6.0)
    _rcp_note(sh, lx - 6, oy_b - CROP[1] * k + 17)

    # palette strip
    py0 = oy_b - CROP[1] * k + 36
    palette_strip(sh, bx, py0, xr_plan - bx + 0.0 if False else (lx + 380 + 2 - bx), by + bh - py0)

    # ---------------- right column
    rx0 = xr_plan + 16
    rx1 = bx + bw
    # elevation 1-1
    items = []
    e1_left = rx0 + 30
    ve1, xb1 = elevation_fireplace(sh, e1_left - fireplace_geom()["lv"][0] * k + (fireplace_geom()["lv"][0] - west_wall_g().c + west_wall_g().t / 2) * k,
                                   by + 6 + M.LV["U"] * k + 0.1 * k, items)
    xt = ve1.P(xb1 + 1.25, 0)[0]
    callout_column(sh, items, xt, by + 5, by + 6 + 3.9 * k, size=2.1, lh=2.7, gap=1.6, x_edge=ve1.P(xb1 + 0.6, 0)[0])
    ybot1 = ve1.P(0, -0.95)[1]
    drawing_title(sh, rx1, ybot1 + 2, "חתך-חזית 1-1 – קיר האח", 'קנ"מ 1:50', width=80, size=5.0)

    # elevation 2-2
    items2 = []
    kr = rrect_of("G3")
    top2 = ybot1 + 16
    ox2 = rx0 + 40 - (kr[0] - 0.4) * k
    oy2 = top2 + M.LV["U"] * k + 2
    y_cut = y2
    ve2, xa2, xb2 = elevation_kitchen(sh, ox2, oy2, items2, y_cut)
    xt2 = ve2.P(xb2 + 0.85, 0)[0]
    callout_column(sh, items2, xt2, top2 - 2, top2 + 3.9 * k, size=2.1, lh=2.7, gap=1.4, x_edge=ve2.P(xb2 + 0.25, 0)[0])
    ybot2 = ve2.P(0, -0.95)[1]
    drawing_title(sh, rx1, ybot2 + 2, "חתך-חזית 2-2 – קיר המטבח", 'קנ"מ 1:50', width=80, size=5.0)

    # flooring plan 1:100
    topf = ybot2 + 18
    kf = 10.0
    oxf = rx1 - 2 - CROP[2] * kf
    oyf = topf + CROP[3] * kf
    vf = plan_flooring(sh, oxf, oyf)
    yfb = oyf - 19.2 * kf
    lx_leg = oxf + CROP[0] * kf - 4
    ybl = flooring_legend(sh, lx_leg, topf)
    drawing_title(sh, lx_leg, yfb - 8, "תכנית ריצוף", 'קנ"מ 1:100', width=70, size=5.0)
    threshold_detail(sh, lx_leg - 2, ybl + 14)
    sh.text(lx_leg, yfb + 6.2, "* קנ\"מ מוקטן לשם התאמה לגיליון; מידות בס\"מ.", size=2.0, anchor="right", color="#555")

    # lighting legend + scenes
    topl = yfb + 12
    sh.text(rx1, topl + 3, "מקרא תאורה ומערכות תקרה", size=3.6, anchor="right", weight=700)
    sh.line(rx1 - 70, topl + 4.6, rx1, topl + 4.6, lw="m")
    yl = lighting_legend(sh, rx1, topl + 7, R, 154)
    sx_r = rx1 - 154 - 6
    sh.text(sx_r, topl + 3, "סצנות תאורה חכמה", size=3.0, anchor="right", weight=700)
    ys = scenes_table(sh, sx_r, topl + 7)
    _general_notes(sh, sx_r, ys + 6, rx0)

    # renders
    top_r = yl + 5
    hr = by + bh - top_r
    wr = (rx1 - rx0 - 4) / 2
    render_frame(sh, rx1 - wr, top_r, wr, hr, "int_01.jpg", "הדמיה 1 – סלון ואח")
    render_frame(sh, rx0, top_r, wr, hr, "int_02.jpg", "הדמיה 2 – מטבח ופינת אוכל")


def _plan_note(sh, x, y):
    lines = ["ריהוט לפי מודל; גמרים לפי פלטת החומרים.",
             "ויטרינות הזזה לכיס נסתר, פרופיל צר, סף שטוח."]
    for i, t in enumerate(lines):
        sh.text(x, y + i * 3.0, t, size=2.0, anchor="left", color="#444")


def _rcp_note(sh, x, y):
    lines = ["תקרות גבס: סינר +2.95 לאורך הויטרינות (מסילות וילון, מיזוג),",
             "תקרות מורמות +3.10 עם קוב LED; מטבח – סינר +2.80 מעל הארונות."]
    for i, t in enumerate(lines):
        sh.text(x + 24, y + i * 3.0, t, size=2.0, anchor="left", color="#444")


def _general_notes(sh, x_right, y, x_left):
    lines = ["הערות:",
             "1. כל המידות בס\"מ, מפלסים במ'. יש לאמת מידות באתר.",
             "2. גופי תאורה עמעום DALI-2, בקרת סצנות KNX.",
             "3. תיאום תקרות עם יועץ מיזוג וחשמל לפני ביצוע.",
             "4. ריצוף 120/120 – ריצוף רטוב-רזה, פילוס ±1 מ\"מ."]
    for i, t in enumerate(lines):
        sh.text(x_right, y + i * 3.0, t, size=2.0, anchor="right", weight=700 if i == 0 else 400, color="#333")
