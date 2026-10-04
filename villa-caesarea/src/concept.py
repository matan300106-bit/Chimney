"""Sheets 02 (concept & research) and 03 (site & climate analysis).

Also hosts the shared presentation helpers used by the cover pages:
text measuring / wrapping (real font metrics via fontTools), section headings,
and a small axonometric engine that draws the massing of the model.
"""
from __future__ import annotations

import math
import os
import random

from fontTools.ttLib import TTFont
from shapely.geometry import MultiPoint, Polygon
from shapely.geometry import box as sbox
from shapely.ops import unary_union

import model as M
from draw import north_arrow

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------- palette
SAND = "#cbb89a"
STONE = "#e9dcc4"
CHAR = "#2b2b2b"
OLIVE = "#7d8a5a"
SEA = "#6fa4b8"
INK = "#34302b"
MUTED = "#776e62"
RULE = "#c9bda9"
PAPER = "#fbf9f5"
SAND_D = "#9c8460"
FR = "Frank Ruhl Libre"

BODY = 2.85          # body text size (mm)
LH = 1.58            # line height factor

# =========================================================================== #
#  Typography helpers
# =========================================================================== #
_FONTS = {}


def _font(font, weight):
    fam = "Frank" if (font or "").startswith("Frank") else "Heebo"
    avail = [300, 500, 700] if fam == "Frank" else [300, 400, 500, 700, 800]
    w = min(avail, key=lambda a: (abs(a - weight), a))
    key = (fam, w)
    if key not in _FONTS:
        f = TTFont(os.path.join(ROOT, "fonts", f"{fam}-{w}.ttf"))
        _FONTS[key] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    return _FONTS[key]


def tw(t, size, weight=400, font=None, spacing=0.0):
    """Text width in mm using the real font advances."""
    cmap, hm, upm = _font(font, weight)
    tot = 0
    for ch in str(t):
        g = cmap.get(ord(ch))
        tot += hm[g][0] if g in hm else upm * 0.55
    return tot / upm * size + spacing * len(str(t))


def wrap(text, width, size, weight=400, font=None):
    words = str(text).split()
    lines, cur = [], ""
    for wd in words:
        cand = (cur + " " + wd).strip()
        if cur and tw(cand, size, weight, font) > width:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def para(sh, xr, y, w, text, size=BODY, lh=LH, weight=400, color=INK, font=None, gap=None):
    """Right-aligned RTL paragraph(s). y = first baseline. Returns next baseline."""
    gap = size * 0.7 if gap is None else gap
    for k, p in enumerate(str(text).split("\n")):
        for ln in wrap(p, w, size, weight, font):
            sh.text(xr, y, ln, size=size, anchor="right", weight=weight, color=color, font=font)
            y += size * lh
        y += gap
    return y - gap


def heading(sh, xr, y, w, num, title, size=4.1):
    """Section heading: sand number + bold title + rule. y = top. Returns top of body."""
    nw = 0
    if num:
        sh.text(xr, y + 5.2, num, size=5.6, anchor="right", weight=500, color=SAND_D, font=FR)
        nw = tw(num, 5.6, 500, FR) + 2.8
    sh.text(xr - nw, y + 5.0, title, size=size, anchor="right", weight=700, color=CHAR)
    sh.line(xr - w, y + 8.4, xr, y + 8.4, lw=0.3, color=CHAR)
    return y + 14.5


def labelled(sh, xr, y, w, label, text, size=BODY, lcolor=CHAR):
    """Paragraph starting with a bold label on its own line."""
    sh.text(xr, y, label, size=size * 1.02, anchor="right", weight=700, color=lcolor)
    return para(sh, xr, y + size * LH, w, text, size=size)


def check(sh, x, y, s=2.2, color=OLIVE):
    sh.polyline([(x - s * 0.5, y - s * 0.05), (x - s * 0.15, y + s * 0.35), (x + s * 0.55, y - s * 0.45)],
                lw=0.35, color=color, cap="round", join="round")


def arrow(sh, x1, y1, x2, y2, lw=0.3, color=CHAR, head=1.8, dash=None):
    sh.line(x1, y1, x2, y2, lw=lw, color=color, dash=dash)
    a = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - head * math.cos(a - 0.4), y2 - head * math.sin(a - 0.4))
    p2 = (x2 - head * math.cos(a + 0.4), y2 - head * math.sin(a + 0.4))
    sh.path(f"M{x2:.2f},{y2:.2f} L{p1[0]:.2f},{p1[1]:.2f} L{p2[0]:.2f},{p2[1]:.2f} Z", lw=0.1, color=color, fill=color)


def clip_path(sh, pts):
    sh.clip_id += 1
    cid = f"cpp{sh.clip_id}"
    d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + " Z"
    sh.defs_extra.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
    return cid


class Grid:
    """6-column board grid inside the sheet's free box (columns numbered from the right)."""

    def __init__(self, box, margin=6.0, gutter=10.0, n=6):
        x, y, w, h = box
        self.x0, self.x1 = x + margin, x + w - margin
        self.y0, self.y1 = y + margin, y + h - margin
        self.g = gutter
        self.n = n
        self.cw = (self.x1 - self.x0 - (n - 1) * gutter) / n

    def col(self, i, span=1):
        """return (x_left, x_right, width) of columns i..i+span-1 counted from the right"""
        xr = self.x1 - i * (self.cw + self.g)
        w = span * self.cw + (span - 1) * self.g
        return xr - w, xr, w


def board_header(sh, G: Grid, title, subtitle, en):
    y = G.y0
    sh.text(G.x1, y + 12.5, title, size=13, anchor="right", weight=700, color=CHAR, font=FR)
    tws = tw(title, 13, 700, FR)
    sh.text(G.x1 - tws - 6, y + 12.5, subtitle, size=4.6, anchor="right", weight=300, color=MUTED)
    sh.text(G.x0, y + 12.5, en, size=3.0, anchor="left", weight=500, color=SAND_D, spacing="0.9")
    sh.line(G.x0, y + 18, G.x1, y + 18, lw=0.45, color=CHAR)
    sh.line(G.x0, y + 19.4, G.x1, y + 19.4, lw=0.15, color=SAND_D)
    return y + 27


# =========================================================================== #
#  Axonometric engine (isometric, viewed from the south-west)
# =========================================================================== #
C30 = math.cos(math.radians(30))

MATS = {  # top, south face, west face
    "stone": ("#e6d6b6", "#d6c29c", "#c1ab84"),
    "plaster": ("#fdfcf9", "#f1ede6", "#dfd9cf"),
    "ghost": ("#f6efe1", "#f6efe1", "#f6efe1"),
    "rc": ("#ddd9d2", "#cdc8c0", "#bab4aa"),
    "glass": ("#cfe2e8", "#bcd6df", "#a8c7d2"),
    "alu": ("#b48a5d", "#a07a50", "#8a6844"),
    "dark": ("#6e665c", "#5f584f", "#4f4942"),
}
GLASS = "#9fc0cb"
GLASS_D = "#7fa3b0"


class Axo:
    def __init__(self, sh, ox, oy, k):
        self.sh, self.ox, self.oy, self.k = sh, ox, oy, k

    @staticmethod
    def unit(x, y, z):
        return (x - y) * C30, -((x + y) * 0.5 + z)

    @classmethod
    def fit(cls, sh, x, y, w, h, pts3, pad=2.0):
        us = [cls.unit(*p) for p in pts3]
        mnx, mxx = min(u[0] for u in us), max(u[0] for u in us)
        mny, mxy = min(u[1] for u in us), max(u[1] for u in us)
        k = min((w - 2 * pad) / (mxx - mnx), (h - 2 * pad) / (mxy - mny))
        ox = x + w / 2 - k * (mnx + mxx) / 2
        oy = y + h / 2 - k * (mny + mxy) / 2
        return cls(sh, ox, oy, k)

    def P(self, x, y, z):
        u = self.unit(x, y, z)
        return self.ox + self.k * u[0], self.oy + self.k * u[1]

    def poly(self, pts3, **kw):
        self.sh.polyline([self.P(*p) for p in pts3], closed=True, **kw)

    def line(self, a, b, **kw):
        self.sh.line(*self.P(*a), *self.P(*b), **kw)


def Bx(x0, y0, z0, x1, y1, z1, mat="plaster", **kw):
    d = dict(kind="box", b=(x0, y0, z0, x1, y1, z1), mat=mat)
    d.update(kw)
    return d


def _faces(b):
    x0, y0, z0, x1, y1, z1 = b
    west = [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)]
    south = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]
    top = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return west, south, top


def _draw_decal(ax, it, d):
    x0, y0, z0, x1, y1, z1 = it["b"]
    sh = ax.sh
    lw = it.get("dlw", 0.12)
    t = d[0]
    if t == "S":
        _, a0, a1, za, zb, fill = d
        ax.poly([(a0, y0, za), (a1, y0, za), (a1, y0, zb), (a0, y0, zb)], fill=fill, lw=lw, color=CHAR)
    elif t == "W":
        _, a0, a1, za, zb, fill = d
        ax.poly([(x0, a0, za), (x0, a1, za), (x0, a1, zb), (x0, a0, zb)], fill=fill, lw=lw, color=CHAR)
    elif t == "T":
        _, xa, ya, xb, yb, fill = d
        ax.poly([(xa, ya, z1), (xb, ya, z1), (xb, yb, z1), (xa, yb, z1)], fill=fill, lw=lw, color=CHAR)
    elif t == "PV":  # rows of panels on the roof
        _, xa, ya, xb, yb, step = d
        y = ya
        while y + step * 0.7 <= yb:
            ax.poly([(xa, y, z1 + 0.05), (xb, y, z1 + 0.05), (xb, y + step * 0.7, z1 + 0.35), (xa, y + step * 0.7, z1 + 0.35)],
                    fill="#55657c", lw=0.08, color="#2f3a4a")
            y += step
    elif t == "fins":
        _, ya, yb, za, zb, off, step = d
        x = x0 - off
        n = int((yb - ya) / step)
        for i in range(n + 1):
            yy = ya + i * step
            ax.line((x, yy, za), (x, yy, zb), lw=it.get("finlw", 0.16), color="#8f6c45")
        ax.line((x, ya, zb), (x, yb, zb), lw=0.15, color="#8f6c45")
        ax.line((x, ya, za), (x, yb, za), lw=0.15, color="#8f6c45")
    elif t == "loggia":
        _, a0, a1, za, zb, dep = d
        frame = [ax.P(a0, y0, za), ax.P(a1, y0, za), ax.P(a1, y0, zb), ax.P(a0, y0, zb)]
        cid = clip_path(sh, frame)
        sh.add(f'<g clip-path="url(#{cid})">')
        sh.polyline(frame, closed=True, color="none", fill="#8c8276")
        yd = y0 + dep
        ax.poly([(a0, yd, za), (a1, yd, za), (a1, yd, zb), (a0, yd, zb)], fill=GLASS_D, lw=0.1, color=CHAR)
        for xx in (a0 + (a1 - a0) / 3, a0 + 2 * (a1 - a0) / 3):
            ax.line((xx, yd, za), (xx, yd, zb), lw=0.1, color=CHAR)
        ax.poly([(a1, y0, za), (a1, yd, za), (a1, yd, zb), (a1, y0, zb)], fill="#e4ded4", lw=0.1, color=CHAR)
        ax.poly([(a0, y0, za), (a1, y0, za), (a1, yd, za), (a0, yd, za)], fill="#c9ab82", lw=0.1, color=CHAR)
        sh.add("</g>")
        sh.polyline(frame, closed=True, lw=lw * 1.4, color=CHAR)
        # glass balustrade
        ax.poly([(a0, y0 + 0.15, za), (a1, y0 + 0.15, za), (a1, y0 + 0.15, za + 1.05), (a0, y0 + 0.15, za + 1.05)],
                fill="#ffffff", fop=0.25, lw=0.08, color="#5d7f8b")


def draw_item(ax: Axo, it):
    k = it["kind"]
    sh = ax.sh
    if k == "box":
        b = it["b"]
        top, south, west = MATS[it.get("mat", "plaster")]
        lw = it.get("lw", 0.18)
        col = it.get("stroke", CHAR)
        w, s, t = _faces(b)
        if it.get("ghost"):
            for f in (w, s, t):
                ax.poly(f, fill=MATS["ghost"][0], fop=0.35, lw=0.14, color="#8c7f6b", dash="0.9 0.6")
            # hidden back edges
            x0, y0, z0, x1, y1, z1 = b
            for a, c in [((x1, y1, z0), (x0, y1, z0)), ((x1, y1, z0), (x1, y0, z0)), ((x1, y1, z0), (x1, y1, z1))]:
                ax.line(a, c, lw=0.1, color="#a99c87", dash="0.6 0.6")
            return
        fop = it.get("fop")
        ax.poly(w, fill=west, lw=lw, color=col, fop=fop)
        ax.poly(s, fill=south, lw=lw, color=col, fop=fop)
        ax.poly(t, fill=top, lw=lw, color=col, fop=fop)
        for d in it.get("decals", []):
            _draw_decal(ax, it, d)
    elif k == "tree":
        x, y, r, kind = it["t"]
        if kind == "palm":
            h = 7.5
            ax.line((x, y, 0), (x, y, h), lw=0.3, color="#7a6650")
            cx, cy = ax.P(x, y, h)
            for i in range(8):
                a = math.radians(i * 45 + 10)
                ex, ey = cx + math.cos(a) * r * ax.k, cy + math.sin(a) * r * ax.k * 0.55 + r * ax.k * 0.25
                mx, my = (cx + ex) / 2, (cy + ey) / 2 - r * ax.k * 0.35
                sh.path(f"M{cx:.2f},{cy:.2f} Q{mx:.2f},{my:.2f} {ex:.2f},{ey:.2f}", lw=0.25, color="#6f7d4e")
        else:
            h = {"olive": 4.2, "olive_s": 3.4, "carob": 5.2}.get(kind, 4.0)
            ax.line((x, y, 0), (x, y, h - r * 0.7), lw=0.35, color="#7a6650")
            cx, cy = ax.P(x, y, h)
            fill = "#a8b287" if kind.startswith("olive") else "#8f9c6b"
            sh.circle(cx, cy, r * ax.k * 0.85, lw=0.15, color="#5f6b43", fill=fill, fop=0.92)
            sh.circle(cx - r * ax.k * 0.25, cy - r * ax.k * 0.3, r * ax.k * 0.38, color="none", fill="#ffffff", fop=0.18)
    elif k == "perg":
        x0, y0, x1, y1, z, base, beam, step = it["p"]
        for (px, py) in it.get("posts", []):
            ax.line((px, py, base), (px, py, z), lw=0.3, color="#55504a")
        ax.poly([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], fill="#ffffff", fop=0.15, lw=0.22, color="#55504a")
        if beam == "x":
            yy = y0
            while yy <= y1:
                ax.line((x0, yy, z), (x1, yy, z), lw=0.12, color="#6b5a46")
                yy += step
        else:
            xx = x0
            while xx <= x1:
                ax.line((xx, y0, z), (xx, y1, z), lw=0.12, color="#6b5a46")
                xx += step


def _sbbox(ax, it):
    x0, y0, z0, x1, y1, z1 = it["b"]
    pts = [ax.P(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def _before(A, B):
    a, b = A["b"], B["b"]
    e = 1e-6
    if a[0] >= b[3] - e:
        return True
    if b[0] >= a[3] - e:
        return False
    if a[1] >= b[4] - e:
        return True
    if b[1] >= a[4] - e:
        return False
    if a[5] <= b[2] + e:
        return True
    if b[5] <= a[2] + e:
        return False
    return (a[2] + a[5], -(a[0] + a[3] + a[1] + a[4])) < (b[2] + b[5], -(b[0] + b[3] + b[1] + b[4]))


def depth_sort(ax, items):
    n = len(items)
    bb = [_sbbox(ax, it) for it in items]
    succ = [[] for _ in range(n)]
    indeg = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            p, q = bb[i], bb[j]
            if p[2] <= q[0] or q[2] <= p[0] or p[3] <= q[1] or q[3] <= p[1]:
                continue
            if _before(items[i], items[j]):
                succ[i].append(j)
                indeg[j] += 1
            else:
                succ[j].append(i)
                indeg[i] += 1
    key = lambda i: (items[i]["b"][2], -(items[i]["b"][0] + items[i]["b"][4]))
    ready = sorted([i for i in range(n) if indeg[i] == 0], key=key)
    out, done = [], set()
    while len(out) < n:
        if not ready:
            rest = sorted([i for i in range(n) if i not in done], key=key)
            ready = [rest[0]]
            indeg[rest[0]] = 0
        i = ready.pop(0)
        if i in done:
            continue
        out.append(i)
        done.add(i)
        for j in succ[i]:
            indeg[j] -= 1
            if indeg[j] == 0 and j not in done:
                ready.append(j)
        ready.sort(key=key)
    return [items[i] for i in out]


SUN_AZ, SUN_ALT = 250.0, 50.0


def shadows(ax, items, ground=0.0):
    t = 1.0 / math.tan(math.radians(SUN_ALT))
    a = math.radians(SUN_AZ + 180)
    sx, sy = math.sin(a) * t, math.cos(a) * t
    polys = []
    for it in items:
        if it.get("ghost") or it.get("noshadow"):
            continue
        if it["kind"] == "tree":
            x, y, r, kind = it["t"]
            h = 7.5 if kind == "palm" else 4.0
            from shapely.geometry import Point
            polys.append(Point(x + h * sx, y + h * sy).buffer(r * (0.6 if kind == "palm" else 0.85)))
            continue
        if it["kind"] != "box":
            continue
        x0, y0, z0, x1, y1, z1 = it["b"]
        if z1 <= ground + 0.2:
            continue
        pts = []
        for z in (max(z0, ground), z1):
            for x in (x0, x1):
                for y in (y0, y1):
                    h = z - ground
                    pts.append((x + h * sx, y + h * sy))
        polys.append(MultiPoint(pts).convex_hull)
    if not polys:
        return
    u = unary_union(polys)
    geoms = getattr(u, "geoms", [u])
    for g in geoms:
        if g.is_empty or g.geom_type != "Polygon":
            continue
        ax.sh.polyline([ax.P(x, y, ground) for x, y in g.exterior.coords], closed=True, color="none", fill=CHAR, fop=0.11)


# ---------------------------------------------------------------- massing
LOTPTS = [(M.LOT["x0"], M.LOT["y0"]), (M.LOT["x1"], M.LOT["y0"]), (M.LOT["x1"], M.LOT["y1"]), (M.LOT["x0"], M.LOT["y1"])]
TOP_Z = M.LV["R"] + 0.50          # parapet top of the light volume
RX_Z = M.LV["RX"] + 0.20          # roof-exit parapet top
BASE_Z = M.LV["U"]                # top of the stone base (GF roof / terrace)
CANT_Z = M.slab_bot("U") - 0.05   # underside of the cantilever


def _openings_decals(boxes):
    """Project model openings onto the visible (south / west) faces of the massing boxes."""
    for w in M.WALLS:
        if w.kind not in ("ext",) or not w.openings or w.level not in ("G", "U"):
            continue
        if w.out != -1:
            continue
        f = w.c + w.out * w.t / 2
        lv = M.LV[w.level]
        for o in w.openings:
            if o.kind in ("open",):
                continue
            za, zb = lv + max(o.sill, 0.0), lv + o.head
            for it in boxes:
                x0, y0, z0, x1, y1, z1 = it["b"]
                if w.horiz and abs(y0 - f) < 0.06 and x0 - 0.05 <= o.pos and o.end <= x1 + 0.05 and z0 - 0.05 <= za and zb <= z1 + 0.6:
                    it.setdefault("decals", []).append(("S", o.pos, o.end, za, min(zb, z1 - 0.1), GLASS))
                    break
                if (not w.horiz) and abs(x0 - f) < 0.06 and y0 - 0.05 <= o.pos and o.end <= y1 + 0.05 and z0 - 0.05 <= za and zb <= z1 + 0.6:
                    it.setdefault("decals", []).append(("W", o.pos, o.end, za, min(zb, z1 - 0.1), GLASS))
                    break


def massing_scene(step, detail=False):
    X_W, X_M, X_E = M.X_W, M.X_M, M.X_E
    Y_S_G, Y_N, Y_S_U, Y_NB = M.Y_S_G, M.Y_N, M.Y_S_U, M.Y_NB
    sc = dict(ground=[], items=[], void=False, notes=[])
    g = sc["ground"]
    g.append(dict(pts=LOTPTS, fill="#efe7d6" if step < 6 else "#e8e3d2", lw=0.2, color=CHAR))
    if step < 6:
        ex0, ey0, ex1, ey1 = M.ENVELOPE
        g.append(dict(pts=[(ex0, ey0), (ex1, ey0), (ex1, ey1), (ex0, ey1)], fill="none", lw=0.13, color="#8c7f6b", dash="1 0.7"))
    else:
        S = M.SITE
        for r in S["lawn"]:
            g.append(dict(pts=_rp(r), fill="#d9dfc2", lw=0.0, color="none"))
        for r in S["planting"]:
            g.append(dict(pts=_rp(r), fill="#c4cfa6", lw=0.0, color="none"))
        for r in S["deck"]:
            g.append(dict(pts=_rp(r), fill="#d8bf98", lw=0.06, color="#a88a64"))
        for r in S["paving"]:
            g.append(dict(pts=_rp(r), fill="#e5dfd3", lw=0.06, color="#a9a196"))
        P = M.POOL
        g.append(dict(pts=_rp((P["x0"], P["y0"], P["x1"], P["y1"])), fill="#9cc6d4", lw=0.2, color="#4f8397"))
        g.append(dict(pts=_rp((P["x0"] + 0.4, P["y0"] + 0.4, P["x1"] - 0.4, P["y1"] - 0.4)), fill="#b9dbe5", lw=0.0,
                      color="none"))
        g.append(dict(pts=LOTPTS, fill="none", lw=0.2, color=CHAR))
    it = sc["items"]
    if step == 1:
        ex0, ey0, ex1, ey1 = M.ENVELOPE
        it.append(Bx(ex0, ey0, 0, ex1, ey1, TOP_Z, ghost=True))
        return sc
    base = Bx(X_W, Y_S_G, 0, X_E, Y_N, BASE_Z, "stone")
    it.append(base)
    if step == 2:
        return sc
    if step == 3:
        it.append(Bx(X_W, Y_S_G, BASE_Z, X_M, Y_N, TOP_Z, "plaster"))
        it.append(Bx(X_M, Y_NB, BASE_Z, X_E, Y_N, TOP_Z, "plaster"))
        return sc
    wing = Bx(X_W, Y_S_U, CANT_Z, X_M, Y_N, TOP_Z, "plaster")
    bar = Bx(X_M, Y_NB, BASE_Z, X_E, Y_N, TOP_Z, "plaster")
    it += [wing, bar]
    if step == 4:
        it.append(Bx(X_W, Y_S_U + 0.02, CANT_Z, X_M, Y_S_G, TOP_Z, ghost=True))  # placeholder removed below
        it.pop()
        sc["notes"].append("cant")
        return sc
    # step 5+: carving
    sc["void"] = True
    rx = M.RX_OUT
    it.append(Bx(rx[0][0] + 0.1, rx[0][1], TOP_Z, rx[1][0], rx[2][1], RX_Z, "plaster"))
    wing["decals"] = [("loggia", X_W + 0.3, X_M - 0.3, M.LV["U"], M.LV["U"] + 3.0, M.LOGGIA - Y_S_U)]
    _openings_decals([base, wing, bar])
    fin = M.FINS[0]
    wing["decals"].append(("fins", fin["a0"], fin["a1"], fin["z0"], fin["z1"], X_W - fin["c"],
                           fin["step"] if detail else fin["step"] * 3))
    # GF-roof terrace glass railing
    it.append(Bx(X_M + 0.1, Y_S_G + 0.1, BASE_Z, X_E - 0.1, Y_S_G + 0.18, BASE_Z + 0.95, "glass", fop=0.35, lw=0.1,
                 noshadow=True))
    # column at cantilever corners (covered terrace)
    if step >= 6:
        wing["decals"].append(("PV", X_W + 0.8, 17.0, X_M - 0.8, 24.6, 1.25))
        for p in M.PERGOLAS:
            base_z = p.get("base", 0.0 if p["z"] < 3.2 else 0.0)
            if p.get("base") is not None:
                base_z = p["base"] + 0.5
            it.append(dict(kind="perg", b=(p["x0"], p["y0"], base_z, p["x1"], p["y1"], p["z"]),
                           p=(p["x0"], p["y0"], p["x1"], p["y1"], p["z"], base_z, p["beam"], p["step"] * (1 if detail else 2)),
                           posts=p["posts"]))
        for (x, y, r, kind) in M.SITE["trees"]:
            h = 7.5 if kind == "palm" else 5.0
            it.append(dict(kind="tree", b=(x - r * 0.5, y - r * 0.5, 0, x + r * 0.5, y + r * 0.5, h), t=(x, y, r, kind)))
    return sc


def _rp(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def massing_extent(crop=False):
    if crop:
        return [(x, y, z) for x in (2.0, 29.0) for y in (7.0, 35.0) for z in (0.0, RX_Z + 0.3)]
    pts = [(x, y, 0) for x, y in LOTPTS] + [(x, y, RX_Z + 0.5) for x, y in LOTPTS] + [(M.X_W, M.Y_S_G, -1.5)]
    return pts


def draw_patio_void(ax):
    x0, y0, x1, y1 = M.PATIO
    zf = M.LV["B"]
    top = [ax.P(x0, y0, 0), ax.P(x1, y0, 0), ax.P(x1, y1, 0), ax.P(x0, y1, 0)]
    cid = clip_path(ax.sh, top)
    ax.sh.add(f'<g clip-path="url(#{cid})">')
    ax.poly([(x0, y0, zf), (x1, y0, zf), (x1, y1, zf), (x0, y1, zf)], fill="#cdb894", lw=0.1, color=CHAR)
    ax.poly([(x0, y1, zf), (x1, y1, zf), (x1, y1, 0), (x0, y1, 0)], fill="#d2bf9c", lw=0.1, color=CHAR)
    # basement glazing to the patio
    for w in M.WALLS:
        if w.level == "B" and w.horiz and abs(w.c - 21.15) < 0.05:
            for o in w.openings:
                a0, a1 = max(o.pos, x0), min(o.end, x1)
                if a1 > a0:
                    ax.poly([(a0, y1, zf), (a1, y1, zf), (a1, y1, zf + o.head), (a0, y1, zf + o.head)], fill=GLASS, lw=0.1,
                            color=CHAR)
    ax.poly([(x1, y0, zf), (x1, y1, zf), (x1, y1, 0), (x1, y0, 0)], fill="#b8a27c", lw=0.1, color=CHAR)
    ax.sh.add("</g>")
    ax.sh.polyline(top, closed=True, lw=0.18, color=CHAR)


def draw_massing(sh, x, y, w, h, step, detail=False, shadow=True, ax=None, crop=False):
    sc = massing_scene(step, detail)
    if ax is None:
        ax = Axo.fit(sh, x, y, w, h, massing_extent(crop), pad=0.0 if crop else 2.0)
    if crop:
        sh.begin_clip(x, y, w, h)
    for gd in sc["ground"]:
        ax.sh.polyline([ax.P(px, py, 0) for px, py in gd["pts"]], closed=True, fill=gd["fill"],
                       lw=gd.get("lw", 0.1) or 0.01, color=gd.get("color", "none"), dash=gd.get("dash"))
    if sc["void"]:
        draw_patio_void(ax)
    if shadow:
        shadows(ax, sc["items"])
    for it in depth_sort(ax, sc["items"]):
        draw_item(ax, it)
    if "cant" in sc["notes"]:
        # dimension of the cantilever, hung west of its underside
        z = CANT_Z
        xd = M.X_W - 2.2
        for yy in (M.Y_S_G, M.Y_S_U):
            sh.line(*ax.P(M.X_W - 0.2, yy, z), *ax.P(xd - 0.6, yy, z), lw=0.12, color="#a5492f")
        a, b = ax.P(xd, M.Y_S_G, z), ax.P(xd, M.Y_S_U, z)
        arrow(sh, *a, *b, lw=0.25, color="#a5492f", head=1.4)
        arrow(sh, *b, *a, lw=0.25, color="#a5492f", head=1.4)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        sh.text(mx - 1.5, my + 3.6, f"שלוחה {M.Y_S_G - M.Y_S_U:.2f} מ'", size=2.4, anchor="right", weight=700,
                color="#a5492f")
    if crop:
        sh.end_group()
    return ax


# =========================================================================== #
#  SHEET 02 – Concept & research
# =========================================================================== #
def _areas():
    """net room areas (shapely) per level, gross per level from the model outlines"""
    rooms = []
    for r in M.ROOMS:
        a = unary_union([sbox(*q) for q in r.rects]).area
        rooms.append((r, a))
    gross = {
        "B": Polygon(_rp((M.X_W, M.Y_S_G, M.X_E, M.Y_N))).area,
        "G": Polygon(_rp((M.X_W, M.Y_S_G, M.X_E, M.Y_N))).area,
        "U": Polygon(M.UF_OUT).area,
        "R": Polygon(M.RX_OUT).area,
    }
    return rooms, gross


CAT = {
    "public": ("מגורים ואירוח", "#d2bf9e"),
    "private": ("שינה ופרטיות", "#ece2d0"),
    "leisure": ("פנאי וספא", "#bcc4a0"),
    "circ": ("מבואות ותנועה", "#f6f2ea"),
    "service": ("שירות וטכני", "#d9d6d0"),
}
ROOM_CAT = {
    "G1": "public", "G2": "public", "G3": "public", "B3": "public", "U8": "public",
    "U1": "private", "U3": "private", "U4": "private", "U6": "private", "U7": "private", "U10": "private",
    "U11": "private", "B4": "private", "B5": "private",
    "B1": "leisure", "B2": "leisure", "B6": "leisure", "B9": "leisure",
    "B7": "service", "B8": "service", "G5": "service", "G6": "service", "U9": "service", "R1": "service",
    "B10": "circ", "G4": "circ", "G7": "circ", "U5": "circ",
}


def squarify(vals, x, y, w, h):
    """Squarified treemap. vals: list of (key, value) sorted desc. Returns {key: (x,y,w,h)}."""
    out = {}
    tot = sum(v for _, v in vals)
    if tot <= 0:
        return out
    items = [(k, v * w * h / tot) for k, v in vals]

    def worst(row, side):
        s = sum(a for _, a in row)
        return max(max(side * side * a / (s * s), s * s / (side * side * a)) for _, a in row)

    def layout(row, x, y, w, h):
        s = sum(a for _, a in row)
        if w >= h:  # column on the right side (RTL feel) – place at x+w-cw
            cw = s / h
            yy = y
            for k, a in row:
                hh = a / cw
                out[k] = (x + w - cw, yy, cw, hh)
                yy += hh
            return x, y, w - cw, h
        rh = s / w
        xx = x + w
        for k, a in row:
            ww = a / rh
            xx -= ww
            out[k] = (xx, y, ww, rh)
        return x, y + rh, w, h - rh

    row = []
    while items:
        side = min(w, h)
        c = items[0]
        if not row or worst(row + [c], side) <= worst(row, side):
            row.append(c)
            items.pop(0)
        else:
            x, y, w, h = layout(row, x, y, w, h)
            row = []
    if row:
        layout(row, x, y, w, h)
    return out


def programme_panel(sh, xl, xr, y, ybot):
    """Area diagram: one squarified treemap per storey (area ∝ m², computed from model.ROOMS) + table."""
    w = xr - xl
    y = heading(sh, xr, y, w, "07", "פרוגרמה ושטחים")
    rooms, gross = _areas()
    levels = [("B", "קומת מרתף", M.LV["B"]), ("G", "קומת קרקע", M.LV["G"]), ("U", "קומה א'", M.LV["U"]),
              ("R", "גג", M.LV["R"])]
    net = {lv: sum(a for r, a in rooms if r.level == lv and not r.outdoor) for lv, _, _ in levels}
    outdoor = [(r, a) for r, a in rooms if r.outdoor]
    # legend
    lx = xr
    for key in ("public", "private", "leisure", "circ", "service"):
        name, col = CAT[key]
        sh.rect(lx - 4, y - 0.4, 4, 3.2, fill=col, lw=0.12, color=CHAR)
        sh.text(lx - 5.5, y + 2.4, name, size=2.5, anchor="right", color=INK)
        lx -= 4 + 1.5 + tw(name, 2.5) + 6
    sh.text(xl, y + 2.4, 'גודל כל תא יחסי לשטחו (מ"ר נטו)', size=2.4, anchor="left", color=MUTED)
    y += 9
    gap = 8
    tmw = (w - 2 * gap) / 3
    table_h, chips_h = 46, 22
    hmax = ybot - y - 12 - table_h - chips_h - 8
    kA = hmax * tmw / max(net[l] for l in ("B", "G", "U"))
    for i, (lv, lname, z) in enumerate(levels[:3][::-1]):   # U | G | B from right to left
        x1 = xr - i * (tmw + gap)
        x0 = x1 - tmw
        lvl = f"{z:+.2f}" if abs(z) > 1e-6 else "±0.00"
        sh.text(x1, y + 3.6, lname, size=3.4, anchor="right", weight=700, color=CHAR)
        sh.text(x1 - tw(lname, 3.4, 700) - 2.5, y + 3.6, f"מפלס {lvl}", size=2.4, anchor="right", color=MUTED)
        sh.text(x0, y + 3.6, f'{net[lv]:.0f} מ"ר', size=3.4, anchor="left", weight=700, color=SAND_D)
        ty = y + 7
        hh = net[lv] * kA / tmw
        rs = sorted([(r, a) for r, a in rooms if r.level == lv and not r.outdoor], key=lambda t: -t[1])
        rects = squarify([(r.no, a) for r, a in rs], x0, ty, tmw, hh)
        for r, a in rs:
            rx, ry, rw, rh = rects[r.no]
            sh.rect(rx, ry, rw, rh, fill=CAT[ROOM_CAT.get(r.no, "service")][1], lw=0.35, color="#ffffff")
            area_t = f"{a:.1f}"
            nm = r.name.replace("ספא – סאונה ומקלחת", "ספא").replace("מזווה / מטבח אחורי", "מזווה") \
                .replace("חדר כושר / יוגה", "כושר / יוגה").replace('ממ"ד / חדר ילד', 'ממ"ד / ילד')
            if rw > 9 and rh > 7:
                lines = wrap(nm, rw - 2.6, 2.35, 500)
                if len(lines) * 3.0 + 4 > rh or any(tw(l, 2.35, 500) > rw - 2 for l in lines):
                    lines = []
                ty2 = ry + 4.0
                for l in lines:
                    sh.text(rx + rw - 1.4, ty2, l, size=2.35, anchor="right", weight=500, color=INK)
                    ty2 += 3.0
                sh.text(rx + rw - 1.4, ty2 + (0.3 if lines else 0), area_t, size=2.6, anchor="right", weight=700,
                        color=CHAR)
            elif rw > 5 and rh > 3.6:
                sh.text(rx + rw / 2, ry + rh / 2 + 0.9, f"{a:.0f}", size=2.1, weight=700, color=CHAR)
        sh.rect(x0, ty, tmw, hh, fill="none", lw=0.3, color=CHAR)
        sh.text(x1, ty + hh + 4.2, f'ברוטו {gross[lv]:.0f} מ"ר', size=2.4, anchor="right", color=MUTED)
    y += 7 + hmax + 9
    # roof + outdoor chips
    sh.text(xr, y + 2.5, "גג ושטחי חוץ:", size=2.8, anchor="right", weight=700, color=CHAR)
    cx = xr - tw("גג ושטחי חוץ:", 2.8, 700) - 4
    chips = [(f"יציאה לגג {net['R']:.0f}", "#d9d6d0", "#9a958c")]
    chips += [(f"{r.name}  {a:.0f}", "#e3eef1", "#7fa8b6") for r, a in outdoor]
    P = M.POOL
    chips.append((f"בריכה – שטח מים  {(P['x1'] - P['x0']) * (P['y1'] - P['y0']):.0f}", "#cfe4ec", "#5f97ab"))
    yc = y - 1.2
    for t, f, c in chips:
        cw = tw(t, 2.45, 400) + 6
        if cx - cw < xl:
            cx = xr
            yc += 7
        sh.rect(cx - cw, yc, cw, 5.2, fill=f, lw=0.12, color=c)
        sh.text(cx - 3, yc + 3.6, t, size=2.45, anchor="right", color=INK)
        cx -= cw + 2.5
    y = yc + 12
    # summary table
    cols = [("קומה", xr), ('נטו (מ"ר)', xr - 50), ('ברוטו (מ"ר)', xr - 88), ("שימושים עיקריים", xr - 128)]
    sh.line(xl, y, xr, y, lw=0.3, color=CHAR)
    for t, x in cols:
        sh.text(x, y + 4.0, t, size=2.55, anchor="right", weight=700, color=CHAR)
    y += 5.8
    sh.line(xl, y, xr, y, lw=0.12, color=CHAR)
    use = {"B": "קולנוע, כושר, טרקלין ובר, ספא, יחידת אורחים, יין",
           "G": "סלון, פינת אוכל, מטבח ומזווה, לובי כניסה, מרפסת מקורה",
           "U": "סוויטת הורים ולוג'יה, ממ\"ד / חדר ילד, חדר שינה 2, גלריה",
           "R": "יציאה לגג, מרפסת גג עם פרגולה, מערכת PV"}
    tn = tg = 0
    for lv, lname, z in levels:
        y += 4.7
        sh.text(cols[0][1], y, lname, size=2.55, anchor="right", color=INK)
        sh.text(cols[1][1], y, f"{net[lv]:.1f}", size=2.55, anchor="right", color=INK)
        sh.text(cols[2][1], y, f"{gross[lv]:.1f}", size=2.55, anchor="right", color=INK)
        sh.text(cols[3][1], y, use[lv], size=2.45, anchor="right", color=MUTED)
        tn += net[lv]
        tg += gross[lv]
    y += 2.3
    sh.line(xl, y, xr, y, lw=0.12, color=CHAR)
    y += 4.6
    sh.text(cols[0][1], y, 'סה"כ', size=2.65, anchor="right", weight=700)
    sh.text(cols[1][1], y, f"{tn:.1f}", size=2.65, anchor="right", weight=700)
    sh.text(cols[2][1], y, f"{tg:.1f}", size=2.65, anchor="right", weight=700)
    sh.text(cols[3][1], y, "שטחים מחושבים מן המודל; טבלת שטחים להיתר – גיליון 04", size=2.4, anchor="right",
            color=MUTED)
    y += 2.3
    sh.line(xl, y, xr, y, lw=0.3, color=CHAR)
    return y


# ---------------------------------------------------------------- material swatches
def _swatch(sh, x, y, s, kind, seed=1, hs=None):
    rnd = random.Random(seed)
    s_w, s_h = s, (hs or s)
    s = max(s_w, s_h)
    cid = sh.clip_rect(x, y, s_w, s_h)
    sh.add(f'<g clip-path="url(#{cid})">')
    if kind == "stone":
        sh.rect(x, y, s, s, fill="#d9c49e", color="none")
        rows = 4
        hh = s / rows
        for i in range(rows):
            off = (i % 2) * s * 0.33
            xx = x - off
            while xx < x + s:
                ww = s * rnd.choice([0.45, 0.55, 0.65])
                tone = rnd.choice(["#dcc8a3", "#d4be96", "#e0cea9", "#cfb88e"])
                sh.rect(xx + 0.25, y + i * hh + 0.25, ww - 0.5, hh - 0.5, fill=tone, color="none")
                xx += ww
        for _ in range(int(s * s * 0.35)):
            sh.circle(x + rnd.random() * s, y + rnd.random() * s, rnd.random() * 0.28 + 0.05,
                      fill=rnd.choice(["#b39f7a", "#efe2c8", "#a8916b"]), color="none", fop=0.8)
    elif kind == "plaster":
        sh.rect(x, y, s, s, fill="#f5f2ec", color="none")
        for _ in range(int(s * s * 0.5)):
            sh.circle(x + rnd.random() * s, y + rnd.random() * s, rnd.random() * 0.18 + 0.04,
                      fill=rnd.choice(["#e4dfd6", "#ffffff", "#dcd6cb"]), color="none")
        sh.path(f"M{x},{y + s * 0.75} Q{x + s * 0.5},{y + s * 0.62} {x + s},{y + s * 0.8} L{x + s},{y + s} L{x},{y + s} Z",
                color="none", fill="#e9e4da", fop=0.6)
    elif kind == "oak":
        sh.rect(x, y, s, s, fill="#caa477", color="none")
        pw = s / 3.0
        for i in range(3):
            tone = ["#c89f70", "#d1ab7e", "#c29868"][i]
            sh.rect(x + i * pw + 0.15, y, pw - 0.3, s, fill=tone, color="none")
            for j in range(9):
                xx = x + i * pw + 1 + j * (pw - 2) / 8 + rnd.uniform(-0.3, 0.3)
                sh.path(f"M{xx:.2f},{y} C{xx + rnd.uniform(-1, 1):.2f},{y + s * 0.3} {xx + rnd.uniform(-1, 1):.2f},{y + s * 0.6} "
                        f"{xx + rnd.uniform(-0.6, 0.6):.2f},{y + s}", lw=0.09, color="#a27a4d", fop=None)
        sh.line(x, y + s * 0.42, x + pw, y + s * 0.42, lw=0.2, color="#9b7448")
        sh.line(x + 2 * pw, y + s * 0.7, x + s, y + s * 0.7, lw=0.2, color="#9b7448")
    elif kind == "aluwood":
        sh.rect(x, y, s, s, fill="#3d3a36", color="none")
        n = 9
        st = s / n
        for i in range(n):
            xx = x + i * st + st * 0.18
            sh.rect(xx, y, st * 0.64, s, fill="#b0875a", color="none")
            sh.rect(xx, y, st * 0.18, s, fill="#c79e70", color="none")
            for j in range(3):
                gx = xx + st * (0.25 + 0.15 * j)
                sh.line(gx, y, gx + rnd.uniform(-0.2, 0.2), y + s, lw=0.06, color="#8a6640")
    elif kind == "glass":
        sh.add(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="url(#bkglass)"/>')
        for i in range(3):
            o = s * (0.15 + i * 0.22)
            sh.path(f"M{x + o},{y + s} L{x + o + s * 0.5},{y} L{x + o + s * 0.5 + 1.6 + i},{y} L{x + o + 1.6 + i},{y + s} Z",
                    color="none", fill="#ffffff", fop=0.28)
        sh.line(x + s * 0.5, y, x + s * 0.5, y + s, lw=0.5, color="#6c7c82")
    elif kind == "teak":
        sh.rect(x, y, s, s, fill="#8c5f38", color="none")
        n = 6
        ph = s / n
        for i in range(n):
            tone = rnd.choice(["#9a6b42", "#93633b", "#a3744a", "#8a5c35"])
            sh.rect(x, y + i * ph + 0.2, s, ph - 0.4, fill=tone, color="none")
            for j in range(3):
                yy = y + i * ph + ph * (0.3 + 0.2 * j)
                sh.path(f"M{x},{yy:.2f} Q{x + s * 0.5},{yy + rnd.uniform(-0.4, 0.4):.2f} {x + s},{yy:.2f}", lw=0.07,
                        color="#6e4626")
            jx = x + rnd.uniform(0.2, 0.8) * s
            sh.line(jx, y + i * ph, jx, y + (i + 1) * ph, lw=0.25, color="#5b3a1f")
    sh.add("</g>")
    sh.rect(x, y, s_w, s_h, lw=0.2, color=CHAR)


MATERIALS = [
    ("stone", "אבן גיר טבעית – גוון כורכר",
     "אבן מסותתת בגימור מוברש, נדבכים אופקיים. מחפה את הבסיס ואת קירות הפיתוח – זיכרון אבן הכורכר של הורדוס.",
     "חיפוי קומת הקרקע, גדרות, פטיו"),
    ("plaster", "טיח מינרלי לבן",
     "טיח סיליקט נושם בגוון לבן-חם, עמיד לקרינה ולאוויר מלוח. מבטא את ה'קליפה' הלבנה של העיר העתיקה.",
     "הנפח העליון והשלוחה"),
    ("oak", "פרקט עץ אלון",
     "לוחות רחבים בגימור שמן מט. מחמם את חללי השינה ואת הגלריה המשפחתית.",
     "קומה א', חדרי שינה, הלבשה"),
    ("aluwood", "אלומיניום בגימור עץ",
     "רפפות אנכיות 50/200 מ\"מ במרווח 180, צבע בתנור בגימור ימי – מקצב קשתות האמה.",
     "חזיתות מערב ומזרח, פרגולות"),
    ("glass", "זכוכית בידודית Low-E",
     "פרופיל אלומיניום דק, זיגוג כפול מחוסם ומבודד; ויטרינות הזזה רחבות אל הגן.",
     "ויטרינות דרום ומערב"),
    ("teak", "עץ טיק / דק",
     "דק עץ טיק טבעי סביב הבריכה, בלוג'יה ובמרפסת המקורה – מגע חם לרגל יחפה.",
     "דקים, לוג'יה, ספסלים"),
]


def materials_panel(sh, xl, xr, y, ybot):
    """Horizontal strip of six material swatches."""
    w = xr - xl
    sh.defs_extra.append('<linearGradient id="bkglass" x1="0" y1="0" x2="1" y2="1">'
                         '<stop offset="0" stop-color="#cfe3ea"/><stop offset="0.55" stop-color="#9fc2cf"/>'
                         '<stop offset="1" stop-color="#7ea6b4"/></linearGradient>')
    y = heading(sh, xr, y, w, "08", "פלטת חומרים")
    n = len(MATERIALS)
    g = 6
    sw = (w - (n - 1) * g) / n
    s = min(sw, ybot - y - 40)
    for i, (kind, name, desc, use) in enumerate(MATERIALS):
        x1 = xr - i * (sw + g)
        _swatch(sh, x1 - sw, y, sw, kind, seed=11 + i, hs=s)
        yy = y + s + 5
        sh.text(x1, yy, name, size=2.85, anchor="right", weight=700, color=CHAR)
        yb = para(sh, x1, yy + 4.4, sw, desc, size=2.35, lh=1.48, color=INK)
        sh.text(x1, yb + 0.8, use, size=2.3, anchor="right", weight=500, color=OLIVE)


# ---------------------------------------------------------------- inspiration pictograms
def _picto(sh, x, y, w, h, kind):
    cx = x + w / 2
    if kind == "kurkar":
        # a stone block with a thin white stucco skin → heavy base + light volume
        sh.rect(x + 3, y + h * 0.52, w - 6, h * 0.36, fill="#d6c29c", lw=0.2, color=CHAR)
        for i in range(1, 3):
            sh.line(x + 3, y + h * 0.52 + i * h * 0.12, x + w - 3, y + h * 0.52 + i * h * 0.12, lw=0.1, color="#9c8460")
        sh.rect(x + 3, y + h * 0.22, w * 0.62, h * 0.3, fill="#fdfcf9", lw=0.2, color=CHAR)
        sh.line(x + 3, y + h * 0.52, x + 3 + w * 0.62, y + h * 0.52, lw=0.45, color=CHAR)
    elif kind == "harbour":
        sh.rect(x + 1, y + h * 0.18, w - 2, h * 0.7, fill="#dcebf0", color="none")
        sh.line(x + 1, y + h * 0.32, x + w - 1, y + h * 0.32, lw=0.2, color=SEA, dash="1 0.6")
        sh.path(f"M{x + 4},{y + h * 0.88} C{x + 3},{y + h * 0.5} {cx - 6},{y + h * 0.42} {cx - 2},{y + h * 0.45}",
                lw=1.2, color="#a58f6c", cap="round")
        sh.path(f"M{x + w - 4},{y + h * 0.88} C{x + w - 3},{y + h * 0.55} {cx + 7},{y + h * 0.5} {cx + 3},{y + h * 0.52}",
                lw=1.2, color="#a58f6c", cap="round")
        sh.rect(x + 1, y + h * 0.86, w - 2, h * 0.06, fill="#d6c29c", color="none")
    elif kind == "arches":
        n = 4
        aw = (w - 6) / n
        base = y + h * 0.88
        top = y + h * 0.3
        sh.rect(x + 3, top, w - 6, base - top, fill="#e6d6b6", lw=0.2, color=CHAR)
        for i in range(n):
            ax0 = x + 3 + i * aw + aw * 0.18
            ax1 = ax0 + aw * 0.64
            r = (ax1 - ax0) / 2
            sh.path(f"M{ax0:.2f},{base} L{ax0:.2f},{top + h * 0.22 + r:.2f} A{r:.2f},{r:.2f} 0 0 1 {ax1:.2f},{top + h * 0.22 + r:.2f} "
                    f"L{ax1:.2f},{base} Z", fill="#fbf9f5", lw=0.18, color=CHAR)
        # louvre rhythm below
        for i in range(17):
            xx = x + 3 + i * (w - 6) / 16
            sh.line(xx, y + h * 0.08, xx, y + h * 0.22, lw=0.3, color="#a07a50")


INSPIRE = [
    ("kurkar", "כורכר + טיח לבן", "בסיס אבן ונפח לבן"),
    ("harbour", "נמל סבסטוס", "מסגור הים – השלוחה"),
    ("arches", "קשתות האמה", "מקצב הרפפות"),
]


def sequence_diagram(sh, xl, xr, y):
    nodes = ["הגעה", "חצר מים", "מבואה כפולה", "מגורים", "גן ובריכה", "ספא ופטיו"]
    n = len(nodes)
    st = (xr - xl - 12) / (n - 1)
    cy = y + 4
    sh.line(xr - 6, cy, xl + 6, cy, lw=0.3, color=SAND_D)
    for i, t in enumerate(nodes):
        cx = xr - 6 - i * st
        sh.circle(cx, cy, 3.0 if i in (0, n - 1) else 2.4, fill=SAND if i % 2 == 0 else "#fff", lw=0.3, color=SAND_D)
        sh.text(cx, cy + 0.9, str(i + 1), size=2.2, weight=700, color=CHAR)
        sh.text(cx, cy + 8.2, t, size=2.35, weight=500, color=INK)
    return y + 14


PRINCIPLES = [
    ("רכס ואופק", "בסיס אבן כבד ונפח לבן קל – ניגוד של חומר, משקל ואור."),
    ("פתיחות דרומה", "חללי המגורים נפתחים לגן ולבריכה; חזית הרחוב סגורה, שקטה ומוגנת."),
    ("מסגור הנוף", "השלוחה והלוג'יה ממסגרות את קו האופק ומצלות על המרפסת המקורה."),
    ("אקלים פסיבי", "הצללה דרומית, רפפות מערביות, אוורור צולב ופליטת אוויר חם דרך חדר המדרגות."),
    ("רצף חוויות", "הגעה, מבואה בגובה כפול, מגורים, גן וספא – סדר החוויה של מלון בוטיק."),
    ("אור למרתף", "פטיו שקוע הופך את המרתף לקומת פנאי מוארת ומאווררת."),
    ("חומר מקומי ועמיד", "אבן, טיח מינרלי, עץ ואלומיניום ימי – מותאמים לאוויר המלוח."),
]

REFS = [
    ("Villa C", "גל מרום אדריכלים", "2012", "510", "מוצב לפי כיווני הרוח לאוורור טבעי"),
    ("LVR House", "עופר ארז אדריכלים", "2018", "350", "חידוש בית משנות ה-80 בהשראת האמה"),
    ("בית בקיסריה", "רז מלמד אדריכל", "2025", "—", "בית רב-מפלסי סביב בריכה מרכזית"),
    ("AB House*", "פיצו קדם אדריכלים", "—", "—", "קופסת טיח לבנה מעל חצר שקועה"),
]


def concept_section(sh, xl, xr, y0, y1):
    """Schematic N–S 'ridge & horizon' section (looking west) – real model levels, climate logic."""
    w = xr - xl
    y = heading(sh, xr, y0, w, "06", "חתך רעיוני – רכס ואופק")
    sh.text(xr - tw("06", 5.6, 500, FR) - 2.8 - tw("חתך רעיוני – רכס ואופק", 4.1, 700) - 4, y0 + 5.0,
            "סכמה, מבט מערבה · מפלסים מן המודל", size=2.6, anchor="right", color=MUTED)
    ya, yb_ = -3.0, 37.0          # model y range (south → north, left → right)
    za, zb = -5.6, 11.2
    k = min((w - 4) / (yb_ - ya), (y1 - y - 2) / (zb - za))
    ox = xl + (w - (yb_ - ya) * k) / 2 - ya * k
    gy = y + zb * k + 1

    def P(yy, z):
        return ox + yy * k, gy - z * k

    def R(y_0, z_0, y_1, z_1, **kw):
        a, b = P(y_0, z_1), P(y_1, z_0)
        sh.rect(a[0], a[1], b[0] - a[0], b[1] - a[1], **kw)

    GL = M.GARDEN
    # sky / sea haze
    R(ya, GL, yb_, zb, fill="#f6f1e7", color="none")
    # ground & kurkar strata
    R(ya, za, yb_, GL, fill="#e8dcc3", color="none")
    rnd = random.Random(5)
    for i in range(int(w * 1.4)):
        px = xl + rnd.random() * w
        py = gy - GL * k + 1.0 + rnd.random() * ((GL - za) * k - 1.5)
        sh.circle(px, py, rnd.random() * 0.25 + 0.08, fill="#bba57f", color="none")
    for zz in (-2.2, -4.4):
        pts = [P(ya + i * 0.5, zz + 0.25 * math.sin(i * 0.7)) for i in range(int((yb_ - ya) / 0.5) + 1)]
        sh.polyline(pts, lw=0.15, color="#b29b74", dash="2 1")
    sh.text(*P(ya + 0.4, -5.0), "שכבת כורכר וחול – מישור החוף", size=2.4, anchor="left", color="#8a7453")
    # excavation (basement + patio) cleared
    R(M.PATIO[1] - 0.3, M.LV["B"] - 0.55, M.Y_N, GL, fill="#f6f1e7", color="none")
    # pool
    P_ = M.POOL
    R(P_["y0"], P_["water"] - P_["depth"], P_["y1"], P_["water"], fill="#b8dbe6", color="none")
    R(P_["y0"] - 0.25, P_["water"] - P_["depth"] - 0.3, P_["y0"], GL, fill=CHAR, color="none")
    R(P_["y1"], P_["water"] - P_["depth"] - 0.3, P_["y1"] + 0.25, GL, fill=CHAR, color="none")
    R(P_["y0"], P_["water"] - P_["depth"] - 0.3, P_["y1"], P_["water"] - P_["depth"], fill=CHAR, color="none")
    # spaces (tints)
    zB, zG, zU, zR = M.LV["B"], M.LV["G"], M.LV["U"], M.LV["R"]
    R(M.Y_S_G, zB, M.Y_N, M.slab_bot("G"), fill="#ece9e3", color="none")                 # basement
    R(M.PATIO[1], zB, M.Y_S_G, GL, fill="#efe6d4", color="none")                         # patio
    R(M.Y_S_G, zG, M.Y_N, M.slab_bot("U"), fill="#eadcc0", color="none")                 # GF
    R(M.Y_S_U, zU, M.Y_N, M.slab_bot("R"), fill="#ffffff", color="none")                 # UF
    R(M.Y_S_U, zU - 0.1, M.LOGGIA, M.slab_bot("R"), fill="#f1ede6", color="none")        # loggia
    # roof exit beyond (elevation, light)
    rx = M.RX_OUT
    R(rx[0][1], zR, rx[2][1], M.LV["RX"] + 0.2, fill="#faf8f4", lw=0.2, color="#8d857a")
    tx, ty = P((rx[0][1] + rx[2][1]) / 2 - 1.2, zR + 1.6)
    sh.text(tx, ty, "יציאה לגג (מעבר)", size=2.3, color=MUTED)
    # cut slabs & walls (poché)
    cut = dict(fill=CHAR, color="none")
    R(M.Y_S_G - 0.35, M.slab_top("B") - M.RAFT, M.Y_N + 0.35, M.slab_top("B"), **cut)
    R(M.Y_S_G, M.slab_bot("G"), M.Y_N, M.slab_top("G"), **cut)
    R(M.Y_S_U, M.slab_bot("U"), M.Y_N, M.slab_top("U"), **cut)
    R(M.Y_S_U, M.slab_bot("R"), M.Y_N, M.slab_top("R"), **cut)
    R(M.Y_N - 0.3, M.slab_top("B"), M.Y_N, M.slab_bot("G"), **cut)                 # basement N wall
    R(M.PATIO[1] - 0.3, M.LV["B"] - 0.4, M.PATIO[1], GL + 0.1, **cut)                # patio retaining
    R(M.PATIO[1] - 0.3, M.LV["B"] - 0.55, M.Y_S_G, M.LV["B"] - 0.02, **cut)          # patio slab
    # GF north wall with stone skin
    R(M.Y_N - 0.3, M.slab_top("G"), M.Y_N - 0.1, M.slab_bot("U"), **cut)
    R(M.Y_N - 0.1, GL, M.Y_N, M.slab_top("U") + 0.05, fill=SAND, lw=0.12, color=CHAR)
    # UF north wall + parapets (white plaster)
    R(M.Y_N - 0.3, M.slab_top("U"), M.Y_N, zR + 0.5, **cut)
    R(M.Y_S_U, M.slab_top("R"), M.Y_S_U + 0.2, zR + 0.5, **cut)
    R(M.Y_S_U, M.slab_bot("U") - 0.05, M.Y_S_U + 0.3, M.slab_top("U"), **cut)
    # glazing lines
    for (yy, z0_, z1_) in [(M.Y_S_G + 0.15, zB, zB + 2.9), (M.Y_S_G + 0.15, zG, zG + 3.0), (M.LOGGIA, zU, zU + 3.0)]:
        a, b = P(yy, z0_), P(yy, z1_)
        sh.line(a[0], a[1], b[0], b[1], lw=0.6, color=SEA)
    # loggia balustrade
    a, b = P(M.Y_S_U + 0.15, zU), P(M.Y_S_U + 0.15, zU + 1.05)
    sh.line(*a, *b, lw=0.35, color=SEA)
    # stair (schematic zig-zag in the core)
    for (z0_, z1_) in [(zB, zG), (zG, zU), (zU, zR)]:
        n = 10
        y_0, y_1 = M.ST["ys"], M.ST["yl"]
        pts = []
        for i in range(n):
            yy = y_0 + (y_1 - y_0) * i / n
            zz = z0_ + (z1_ - z0_) * i / n
            pts += [P(yy, zz), P(yy, zz + (z1_ - z0_) / n)]
        sh.polyline(pts, lw=0.25, color="#6d665c")
    # outline of volumes
    sh.polyline([P(M.Y_S_G, GL), P(M.Y_S_G, zU - 0.4), P(M.Y_S_U, zU - 0.4), P(M.Y_S_U, zR + 0.5), P(M.Y_N, zR + 0.5),
                 P(M.Y_N, GL)], lw=0.35, color=CHAR)
    # ground line
    sh.line(*P(ya, GL), *P(M.PATIO[1] - 0.3, GL), lw=0.45, color=CHAR)
    sh.line(*P(M.Y_N, GL), *P(yb_, GL), lw=0.45, color=CHAR)
    # trees
    for (yy, hgt, r) in [(3.0, 4.6, 1.8), (34.0, 7.5, 0)]:
        bx, by = P(yy, GL)
        if r:
            sh.line(bx, by, bx, by - (hgt - r) * k, lw=0.35, color="#7a6650")
            sh.circle(bx, by - hgt * k, r * k, fill="#b6bf97", fop=0.85, lw=0.2, color="#6f7a52")
        else:
            sh.line(bx, by, bx, by - hgt * k, lw=0.35, color="#7a6650")
            for a_ in range(-60, 241, 50):
                aa = math.radians(a_)
                sh.path(f"M{bx:.2f},{by - hgt * k:.2f} q{math.cos(aa) * 4:.2f},{-3:.2f} {math.cos(aa) * 9:.2f},{1.5 - math.sin(aa) * 2:.2f}",
                        lw=0.3, color="#6f7d4e")
    # ---- climate overlays
    def ray(alt, yy, zz, length, color, label, lab_side=1):
        a = math.radians(alt)
        y_s, z_s = yy - math.cos(a) * length, zz + math.sin(a) * length
        p1, p2 = P(y_s, z_s), P(yy, zz)
        arrow(sh, *p1, *p2, lw=0.35, color=color, head=1.8)
        sh.circle(*p1, 1.6, fill=color, color="none")
        sh.text(p1[0] + 2.6 * lab_side, p1[1] + 0.9, label, size=2.5, anchor="left" if lab_side > 0 else "right",
                weight=600, color=color)
    zl = M.slab_bot("R")
    ray(81, M.Y_S_U + 3.0 / math.tan(math.radians(81)), zl - 3.0, 6.2, "#c27c2c", "קיץ 21.6 · 81°")
    a34 = math.tan(math.radians(34))
    ray(34, M.LOGGIA, zl - 1.6 * a34, 8.6, "#8a6a3c", "חורף 21.12 · 34°", -1)
    # horizon line from the loggia
    eye = zU + 1.6
    sh.line(*P(ya + 0.5, eye), *P(M.Y_S_U + 0.6, eye), lw=0.3, color=SEA, dash="2.2 1.2")
    sh.text(*P(ya + 0.6, eye + 0.45), "קו האופק – מבט מן הלוג'יה", size=2.5, anchor="left", color="#4f8397",
            weight=600)
    # stack ventilation through the stair
    sx = (M.ST["ys"] + M.ST["yl"]) / 2
    for z0_ in (zB + 0.8, zG + 0.8, zU + 0.8):
        a, b = P(sx + 1.2, z0_), P(sx + 1.2, z0_ + 2.2)
        arrow(sh, *a, *b, lw=0.3, color="#a5492f", head=1.4)
    a, b = P(sx + 1.2, zR + 0.4), P(sx + 1.2, M.LV["RX"] + 1.0)
    arrow(sh, *a, *b, lw=0.3, color="#a5492f", head=1.4)
    sh.text(*P(sx + 0.6, M.LV["RX"] + 0.7), "אפקט ארובה", size=2.45, anchor="right", color="#a5492f", weight=600)
    # light into the patio
    arrow(sh, *P(11.0, 8.0), *P(M.PATIO[1] + 2.0, zB + 0.3), lw=0.3, color="#c9a34a", head=1.6, dash="1.2 0.8")

    def inside(yy, zz, lines, size=2.5, bold_first=True):
        px, py = P(yy, zz)
        for i, t in enumerate(lines):
            sh.text(px, py + i * size * 1.45, t, size=size, weight=700 if (i == 0 and bold_first) else 400,
                    color=CHAR if i == 0 else INK)
    inside(23.5, zU + 1.9, ["נפח עליון קל", "טיח מינרלי לבן"])
    inside(24.0, zG + 2.0, ["בסיס כבד", "אבן בגוון כורכר"])
    inside(24.0, zB + 2.0, ["מרתף פנאי", "קולנוע · כושר · ספא"])
    inside((M.Y_S_U + M.Y_S_G) / 2, 1.9, ["מרפסת מקורה", f"שלוחה {M.Y_S_G - M.Y_S_U:.0f} מ'"])
    inside((M.PATIO[1] + M.Y_S_G) / 2, zB + 2.0, ["פטיו שקוע", "אור ואוויר"])
    inside((P_["y0"] + P_["y1"]) / 2, P_["water"] - P_["depth"] - 1.1,
           [f"בריכה {P_['x1'] - P_['x0']:.0f}×{P_['y1'] - P_['y0']:.0f} מ'"])
    a = P(M.Y_S_U + 0.9, zU + 2.2)
    b = P(12.2, zU + 2.9)
    sh.line(*a, *b, lw=0.12, color=MUTED)
    sh.circle(*a, 0.55, fill=CHAR, color="none")
    sh.text(b[0] - 1, b[1] - 0.6, "לוג'יה ממסגרת את האופק", size=2.5, anchor="right", color=INK, weight=600)
    for z_, t in [(zR, "+7.00"), (zU, "+3.60"), (zG, "±0.00"), (zB, "-3.50")]:
        px, py = P(yb_ - 0.2, z_)
        sh.line(px - 9, py, px, py, lw=0.12, color=MUTED)
        sh.path(f"M{px - 9},{py} l-1.2,-1.6 l2.4,0 z", lw=0.1, color=CHAR, fill=CHAR)
        sh.text(px, py - 0.9, t, size=2.3, anchor="right", color=INK)
    sh.text(*P(ya + 0.4, GL + 0.5), "דרום", size=2.6, anchor="left", weight=700, color=CHAR)
    sh.text(*P(yb_ - 0.4, GL - 1.2), "צפון", size=2.6, anchor="right", weight=700, color=CHAR)
    return gy - za * k


def sheet_concept(sh, box):
    G = Grid(box)
    y = board_header(sh, G, "קונספט ומחקר", "בית כורכר: רכס ואופק  ·  וילת בוטיק בקיסריה, רובע 13",
                     "BEIT KURKAR  ·  RIDGE & HORIZON  ·  CONCEPT")
    # ------------------------------------------------ massing evolution strip
    xl, xr, w = G.col(0, 6)
    sh.text(xr, y + 4.5, "התפתחות המסה", size=4.1, anchor="right", weight=700, color=CHAR)
    sh.text(xr - tw("התפתחות המסה", 4.1, 700) - 4, y + 4.5,
            "שישה שלבים – מן המגרש אל הבית. מידות אמיתיות מן המודל הפרמטרי, מבט איזומטרי מדרום-מערב.",
            size=2.7, anchor="right", color=MUTED)
    ys = y + 9
    cell_h = 100
    L = M.LOT
    steps = [
        ("מגרש ומעטפת", f"מגרש {L['x1'] - L['x0']:.0f}×{L['y1'] - L['y0']:.0f} מ' (1,080 מ\"ר), קווי בניין "
                        f"{M.SETBACK['front']:.0f}/{M.SETBACK['side']:.0f}/{M.SETBACK['rear']:.0f} מ'; גולף ממערב, רחוב ממזרח."),
        ("בסיס אבן – הרכס", f"נפח כבד {M.X_E - M.X_W:.0f}×{M.Y_N - M.Y_S_G:.0f} מ' לאורך הגבול הצפוני, מחופה אבן "
                            "בגוון כורכר; משחרר את הגן הדרומי."),
        ("נפח קל מונח לרוחב", "נפח בטיח לבן בצורת L מונח על הבסיס – 'הקל על הכבד', כמו טיח על אבן."),
        ("שלוחה אל האופק", f"האגף המערבי נשלח {M.Y_S_G - M.Y_S_U:.0f} מ' דרומה, מקרה מרפסת וממסגר את קו האופק."),
        ("חציבה וסינון", "לוג'יית הורים, פטיו שקוע למרתף, רפפות אנכיות במערב ויציאה לגג."),
        ("בית, גן ומים", f"בריכה {M.POOL['x1'] - M.POOL['x0']:.0f}×{M.POOL['y1'] - M.POOL['y0']:.0f} מ', דקי טיק, "
                         "עצי זית וחרוב, פרגולות ומערכת PV על הגג."),
    ]
    for i, (t, d) in enumerate(steps):
        cxl, cxr, cw = G.col(i)
        if i > 0:
            sh.line(cxr + G.g / 2, ys + 2, cxr + G.g / 2, ys + cell_h + 24, lw=0.12, color=RULE)
        draw_massing(sh, cxl, ys, cw, cell_h, i + 1, detail=False, crop=True)
        sh.text(cxr, ys + 7, f"{i + 1:02d}", size=8, anchor="right", weight=300, color=SAND_D, font=FR)
        yy = ys + cell_h + 5
        sh.text(cxr, yy, t, size=3.3, anchor="right", weight=700, color=CHAR)
        para(sh, cxr, yy + 4.8, cw, d, size=2.5, lh=1.45, color=INK)
    y = ys + cell_h + 31
    sh.line(G.x0, y - 4, G.x1, y - 4, lw=0.15, color=RULE)
    ybot = G.y1
    mat_top = ybot - 84
    bottoms = []
    # ------------------------------------------------ column 1: statement + history
    xl, xr, w = G.col(0)
    yt = heading(sh, xr, y, w, "01", "הצהרת פרויקט")
    sh.text(xr, yt + 4.6, "רכס ואופק", size=7, anchor="right", weight=500, color=CHAR, font=FR)
    yb = para(sh, xr, yt + 12.5, w,
              "בית כורכר הוא וילת בוטיק למשפחה בשכונת הגולף (רובע 13) בקיסריה – הנקודה הגבוהה בעיר, הצופה אל "
              "מרחבי הגולף ואל קו האופק של הים. הבית נולד משני דימויים מקומיים: רכס הכורכר – שלד האבן של מישור "
              "החוף, וקו האופק – המתח האופקי בין שמיים לים. בסיס כבד מחופה אבן בגוון כורכר נטוע בקרקע; מעליו "
              "מונח נפח קל בטיח לבן, הנשלח 5 מ' דרומה אל הגן והבריכה וממסגר את האופק דרך לוג'יית ההורים.")
    yt = heading(sh, xr, yb + 6, w, "02", "קיסריה – היסטוריה וחומר")
    yb = para(sh, xr, yt + 3, w,
              "הורדוס ייסד את קיסריה בשנים 22–10 לפנה\"ס על אתר 'מגדל סטרטון' וקרא לה על שם הקיסר אוגוסטוס. "
              "העיר נבנתה מאבן הכורכר המקומית – אבן חול גירית ונקבובית – שצופתה בטיח לבן מבריק, כך שנראתה מן הים "
              "כעיר של שיש. בלבה נבנה נמל סבסטוס, מן הנמלים המלאכותיים הגדולים בעולם העתיק, ששוברי הגלים שלו "
              "נוצקו בבטון הידראולי בתוך הים. אמת המים הובילה מים ממעיינות הכרמל, ושורת קשתותיה לאורך החוף "
              "יוצרת מקצב חוזר של אור וצל.")
    yb += 4
    sh.text(xr, yb + 2, "מן העבר אל הבית:", size=2.9, anchor="right", weight=700, color=CHAR)
    pw = (w - 8) / 3
    for i, (k, a, b) in enumerate(INSPIRE):
        px = xr - (i + 1) * pw - i * 4
        _picto(sh, px, yb + 5, pw, 25, k)
        sh.text(px + pw / 2, yb + 34.5, a, size=2.5, weight=700, color=CHAR)
        sh.text(px + pw / 2, yb + 38.3, b, size=2.4, color=OLIVE, weight=500)
    bottoms.append(yb + 40)
    # ------------------------------------------------ column 2: boutique idea + principles
    xl, xr, w = G.col(1)
    yt = heading(sh, xr, y, w, "03", "וילת בוטיק – הרעיון")
    yb = para(sh, xr, yt + 3, w,
              "וילת בוטיק היא בית פרטי המתוכנן בהשראת מלונאות בוטיק: מעט חללים, לכל אחד זהות ברורה, איכות ביצוע "
              "גבוהה ותשומת לב לפרט. הבית מאורגן כרצף חוויות – הגעה דרך חצר מים, מבואה בגובה כפול ודלת ציר, "
              "חלל מגורים הנפתח לגן ולבריכה, ספא, קולנוע ובר במרתף הפונים לפטיו שקוע, וסוויטת הורים עם לוג'יה "
              "פרטית. העיצוב מוביל: פלטת חומרים מצומצמת, נגרות בהתאמה ותאורה מדורגת – כמו במלון, בקנה מידה של משפחה.")
    yb = sequence_diagram(sh, xl, xr, yb + 3)
    yt = heading(sh, xr, yb + 5, w, "04", "עקרונות תכנון")
    yy = yt + 1
    for i, (t, d) in enumerate(PRINCIPLES):
        sh.circle(xr - 2.7, yy + 0.1, 2.7, fill=STONE, lw=0.2, color=SAND_D)
        sh.text(xr - 2.7, yy + 1.05, str(i + 1), size=2.7, weight=700, color=CHAR)
        sh.text(xr - 7.8, yy + 1.1, t, size=2.9, anchor="right", weight=700, color=CHAR)
        yy = para(sh, xr - 7.8, yy + 5.6, w - 7.8, d, size=2.65, lh=1.5, color=INK) + 3.6
    bottoms.append(yy)
    # ------------------------------------------------ column 3: research
    xl, xr, w = G.col(2)
    yt = heading(sh, xr, y, w, "05", "מחקר: וילות עכשוויות בקיסריה")
    yb = para(sh, xr, yt + 3, w,
              "קיסריה מנוהלת בידי החברה לפיתוח קיסריה ומאופיינת במגרשים גדולים, בנייה צמודת קרקע בצפיפות נמוכה "
              "והנחיות עיצוב מחמירות. סקירת וילות מהעשור האחרון העלתה את המגמות הבאות:", size=2.75)
    yb += 1
    for lab, txt in [
        ("סגנון", "מודרניזם ים-תיכוני: נפחים אורתוגונליים וגגות שטוחים, שילוב אבן וטיח לבן, ויטרינות רחבות אל הגן; "
                  "לצידם בתי שנות ה-80 בהשראת קשתות האמה."),
        ("חומרים", "אבן גיר טבעית (כורכר, טרוורטין), טיח מינרלי לבן, בטון חשוף, אלומיניום בגימור עץ, דקי טיק."),
        ("פרוגרמה", "מרתף פנאי (קולנוע, כושר, ספא, יין), חלל ציבורי פתוח, מטבח ומזווה, סוויטת הורים, ממ\"ד, "
                    "יחידת אורחים, בריכה וחניה מקורה."),
        ("היקפים", "מגרשים של 1,000–2,000 מ\"ר (ברובע 13: 1,000–1,200); בתים של 350–800 מ\"ר כולל מרתף; "
                   "בריכות של 40–60 מ\"ר."),
    ]:
        sh.rect(xr - 1.3, yb + 1.5, 1.3, 1.3, fill=SAND_D, color="none")
        sh.text(xr - 3.4, yb + 3.2, lab, size=2.8, anchor="right", weight=700, color=CHAR)
        lw_ = tw(lab, 2.8, 700) + 2.2
        yb = para(sh, xr - 3.4 - lw_, yb + 3.2, w - 3.4 - lw_, txt, size=2.65, lh=1.5)
        yb += 1.6
    yb += 3
    sh.text(xr, yb + 1, "פרויקטים לעיון", size=2.95, anchor="right", weight=700, color=CHAR)
    yb += 4
    sh.line(xl, yb, xr, yb, lw=0.3, color=CHAR)
    cx = [xr, xr - 22, xr - 52, xr - 63]
    for t, x in zip(["פרויקט", "משרד", "שנה", 'מ"ר'], cx):
        sh.text(x, yb + 3.8, t, size=2.35, anchor="right", weight=700, color=MUTED)
    sh.text(xl + 33, yb + 3.8, "מאפיין", size=2.35, anchor="right", weight=700, color=MUTED)
    yb += 5.6
    sh.line(xl, yb, xr, yb, lw=0.12, color=CHAR)
    for p, a, yr, ar, note in REFS:
        lines = wrap(note, 33, 2.3)
        sh.text(cx[0], yb + 4, p, size=2.4, anchor="right", weight=600, color=CHAR)
        sh.text(cx[1], yb + 4, a, size=2.35, anchor="right", color=INK)
        sh.text(cx[2], yb + 4, yr, size=2.35, anchor="right", color=INK)
        sh.text(cx[3], yb + 4, ar, size=2.35, anchor="right", color=INK)
        for j, l in enumerate(lines):
            sh.text(xl + 33, yb + 4 + j * 3.2, l, size=2.3, anchor="right", color=MUTED)
        yb += 3.2 * max(1, len(lines)) + 2.4
        sh.line(xl, yb, xr, yb, lw=0.08, color=RULE)
    sh.text(xr, yb + 3.4, "* בית בכפר שמריהו – מובא כהשראה לחצר השקועה.", size=2.2, anchor="right", color=MUTED)
    yb += 10
    sh.text(xr, yb, "מסקנות לפרויקט", size=2.95, anchor="right", weight=700, color=CHAR)
    yb += 5.2
    for t in ["בסיס אבן ונפח לבן – שפה מקומית מוכרת בפרשנות עכשווית.",
              "מרתף פנאי עם פטיו שקוע – אור ואוויר לקומה התחתונה.",
              "פתיחה מערבה לגולף ולבריזה, סגירות כלפי הרחוב.",
              "פרוגרמת אירוח בסגנון מלון בוטיק בהיקף של כ-640 מ\"ר ברוטו."]:
        check(sh, xr - 1.5, yb - 0.9)
        yb = para(sh, xr - 5, yb, w - 5, t, size=2.65, lh=1.5) + 1.4
    bottoms.append(yb)
    # ------------------------------------------------ concept section (bottom right)
    xl, xr, w = G.col(0, 3)
    concept_section(sh, xl, xr, max(bottoms) + 6, ybot)
    # ------------------------------------------------ programme + materials (left half)
    xl, xr, w = G.col(3, 3)
    programme_panel(sh, xl, xr, y, mat_top - 8)
    materials_panel(sh, xl, xr, mat_top, ybot)


# =========================================================================== #
#  SHEET 03 – Site & climate analysis
# =========================================================================== #
def _wave_arrow(sh, x1, y1, x2, y2, color, lw=0.45, amp=0.8, n=4, head=2.2):
    """wavy wind arrow from (x1,y1) to (x2,y2)"""
    L = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = -uy, ux
    pts = []
    m = 40
    for i in range(m + 1):
        t = i / m
        s = math.sin(t * n * 2 * math.pi) * amp * (1 - t * 0.6) if t < 0.85 else 0
        pts.append((x1 + ux * L * t * 0.97 + nx * s, y1 + uy * L * t * 0.97 + ny * s))
    sh.polyline(pts, lw=lw, color=color, cap="round", join="round")
    arrow(sh, pts[-3][0], pts[-3][1], x2, y2, lw=lw, color=color, head=head)


def caesarea_map(sh, xl, xr, y0, y1):
    w = xr - xl
    y = heading(sh, xr, y0, w, "01", "קיסריה – סכמת העיר וסביבתה")
    sh.text(xl, y0 + 5.0, "סכמה – לא בקנה מידה", size=2.6, anchor="left", color=MUTED, weight=500)
    fx0, fy0, fw, fh = xl, y, w, y1 - y
    sh.rect(fx0, fy0, fw, fh, fill="#f7f3ea", lw=0.25, color=CHAR)
    cid = sh.clip_rect(fx0, fy0, fw, fh)
    sh.add(f'<g clip-path="url(#{cid})">')

    def Q(u, v):
        return fx0 + u * fw, fy0 + v * fh

    def poly(pts, **kw):
        sh.polyline([Q(*p) for p in pts], closed=True, **kw)

    def smooth(pts, closed=True, **kw):
        P_ = [Q(*p) for p in pts]
        n = len(P_)
        d = f"M{P_[0][0]:.2f},{P_[0][1]:.2f} "
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            p0, p1, p2, p3 = P_[(i - 1) % n], P_[i], P_[(i + 1) % n], P_[(i + 2) % n]
            if not closed:
                p0 = P_[max(i - 1, 0)]
                p3 = P_[min(i + 2, n - 1)]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += f"C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f} "
        if closed:
            d += "Z"
        sh.path(d, **kw)

    coast = [(0.31, -0.02), (0.30, 0.10), (0.285, 0.21), (0.27, 0.32), (0.255, 0.41), (0.245, 0.46), (0.25, 0.52),
             (0.245, 0.58), (0.232, 0.68), (0.22, 0.79), (0.205, 0.9), (0.195, 1.02)]
    # sea
    sea = [(-0.02, -0.02)] + coast + [(-0.02, 1.02)]
    poly(sea, fill="#d5e7ed", color="none")
    for i in range(14):
        v = 0.05 + i * 0.07
        u0 = 0.03 + (i % 3) * 0.04
        x_, y_ = Q(u0, v)
        sh.path(f"M{x_:.1f},{y_:.1f} q2,-1.1 4,0 t4,0 t4,0", lw=0.18, color="#8fbccb")
    sh.polyline([Q(*p) for p in coast], lw=0.45, color="#5f97ab")
    sh.text(*Q(0.11, 0.30), "הים התיכון", size=4.2, color="#4f8397", weight=300, font=FR, rot=-80)
    # beach strip
    sh.polyline([Q(u + 0.012, v) for u, v in coast], lw=1.6, color="#eadfc6", cap="round")
    # national park
    park = [(0.252, 0.41), (0.33, 0.40), (0.345, 0.50), (0.335, 0.62), (0.30, 0.72), (0.232, 0.70), (0.246, 0.58),
            (0.25, 0.50)]
    poly(park, fill="#e3e6cf", lw=0.3, color=OLIVE, dash="1.2 0.8")
    # crusader walls + harbour
    poly([(0.252, 0.445), (0.30, 0.44), (0.305, 0.52), (0.254, 0.525)], fill="none", lw=0.35, color="#8a7453")
    sh.path(f"M{Q(0.248, 0.535)[0]:.2f},{Q(0.248, 0.535)[1]:.2f} Q{Q(0.17, 0.56)[0]:.2f},{Q(0.17, 0.56)[1]:.2f} "
            f"{Q(0.175, 0.47)[0]:.2f},{Q(0.175, 0.47)[1]:.2f}", lw=1.4, color="#a58f6c", cap="round")
    sh.path(f"M{Q(0.247, 0.455)[0]:.2f},{Q(0.247, 0.455)[1]:.2f} Q{Q(0.215, 0.44)[0]:.2f},{Q(0.215, 0.44)[1]:.2f} "
            f"{Q(0.195, 0.462)[0]:.2f},{Q(0.195, 0.462)[1]:.2f}", lw=1.4, color="#a58f6c", cap="round")
    # theatre & hippodrome
    tx, ty = Q(0.245, 0.68)
    sh.path(f"M{tx - 3.2:.2f},{ty:.2f} A3.2,3.2 0 0 1 {tx + 3.2:.2f},{ty:.2f} Z", fill="#d8c8a6", lw=0.25, color="#8a7453")
    hx, hy = Q(0.287, 0.57)
    sh.rect(hx - 2.0, hy - 7, 4.0, 14, fill="#e8dcc3", lw=0.25, color="#8a7453")
    # aqueduct
    aq = [(0.272, 0.40), (0.285, 0.30), (0.30, 0.18), (0.315, 0.06)]
    sh.polyline([Q(*p) for p in aq], lw=0.5, color="#8a7453")
    for i in range(18):
        t = i / 17
        seg = min(int(t * 3), 2)
        tt = t * 3 - seg
        a_, b_ = aq[seg], aq[seg + 1]
        u, v = a_[0] + (b_[0] - a_[0]) * tt, a_[1] + (b_[1] - a_[1]) * tt
        px, py = Q(u, v)
        sh.path(f"M{px - 1.1:.2f},{py:.2f} A1.1,1.1 0 0 1 {px + 1.1:.2f},{py:.2f}", lw=0.25, color="#8a7453")
    # villages
    for pts, lab, at in [
        ([(0.30, 0.0), (0.37, 0.0), (0.37, 0.07), (0.305, 0.08)], "ג'סר א-זרקא", (0.385, 0.04)),
        ([(0.22, 0.75), (0.27, 0.74), (0.275, 0.82), (0.215, 0.83)], "שדות ים", (0.29, 0.80)),
    ]:
        poly(pts, fill="#ebe5d8", lw=0.2, color="#9a9184")
        sh.text(*Q(*at), lab, size=2.6, anchor="left", color=INK)
    # golf course
    golf = [(0.42, 0.22), (0.53, 0.20), (0.585, 0.27), (0.575, 0.40), (0.53, 0.49), (0.45, 0.50), (0.405, 0.40),
            (0.40, 0.30)]
    smooth(golf, fill="#cfdcb3", lw=0.3, color="#7d8a5a")
    for (u, v, r) in [(0.46, 0.27, 2.6), (0.52, 0.33, 2.2), (0.47, 0.42, 2.4), (0.54, 0.43, 1.8)]:
        px, py = Q(u, v)
        sh.add(f'<ellipse cx="{px:.2f}" cy="{py:.2f}" rx="{r * 2.2:.2f}" ry="{r:.2f}" fill="#e2ebcf" '
               f'transform="rotate(-30 {px:.2f} {py:.2f})"/>')
    sh.text(*Q(0.49, 0.36), "מגרש הגולף", size=3.0, weight=700, color="#4f5a35")
    # neighbourhoods (schematic blobs, numbered)
    hoods = {
        1: (0.38, 0.62), 2: (0.43, 0.70), 3: (0.37, 0.75), 4: (0.47, 0.80), 5: (0.55, 0.74), 6: (0.62, 0.66),
        7: (0.53, 0.60), 8: (0.62, 0.55), 9: (0.37, 0.52), 10: (0.37, 0.14), 11: (0.47, 0.12), 12: (0.62, 0.17),
        13: (0.645, 0.36),
    }
    for n_, (u, v) in hoods.items():
        px, py = Q(u, v)
        rw, rh = (fw * 0.055, fh * 0.07) if n_ != 13 else (fw * 0.06, fh * 0.11)
        sh.add(f'<rect x="{px - rw / 2:.2f}" y="{py - rh / 2:.2f}" width="{rw:.2f}" height="{rh:.2f}" rx="2.2" '
               f'fill="{"#ead9b8" if n_ == 13 else "#efe8da"}" stroke="{"#a5492f" if n_ == 13 else "#a99f90"}" '
               f'stroke-width="{0.45 if n_ == 13 else 0.2}"/>')
        sh.text(px, py + 1.2, str(n_), size=3.2 if n_ == 13 else 2.8, weight=700 if n_ == 13 else 500,
                color="#a5492f" if n_ == 13 else MUTED)
    # site marker
    px, py = Q(0.645, 0.36)
    sh.circle(px - 4.2, py - 4.0, 1.6, fill="#a5492f", color="#ffffff", lw=0.3)
    sh.line(px - 4.2, py - 4.0, px - 11, py - 12, lw=0.2, color="#a5492f")
    sh.text(px - 11.5, py - 12.6, "האתר – רובע 13 (שכונת הגולף)", size=2.7, anchor="right", weight=700, color="#a5492f")
    sh.text(px - 11.5, py - 9.1, "הנקודה הגבוהה בקיסריה", size=2.4, anchor="right", color="#a5492f")
    # roads
    r2 = [(0.74, -0.02), (0.745, 0.3), (0.75, 0.6), (0.755, 1.02)]
    sh.polyline([Q(*p) for p in r2], lw=2.2, color="#ffffff")
    sh.polyline([Q(*p) for p in r2], lw=1.4, color="#c9a34a")
    sh.text(*Q(0.762, 0.12), "כביש 2", size=2.8, anchor="left", weight=700, color=CHAR)
    sh.polyline([Q(0.748, 0.47), Q(0.69, 0.47), Q(0.62, 0.48), Q(0.55, 0.54), Q(0.40, 0.58), Q(0.34, 0.57)], lw=0.9,
                color="#d7c08a")
    ix, iy = Q(0.748, 0.47)
    sh.circle(ix, iy, 2.2, fill="#ffffff", lw=0.4, color=CHAR)
    sh.text(ix + 3.4, iy + 1.0, "מחלף קיסריה", size=2.5, anchor="left", color=INK)
    # Or Akiva + industrial park + railway
    smooth([(0.80, 0.38), (0.90, 0.36), (0.93, 0.48), (0.90, 0.60), (0.82, 0.62), (0.79, 0.50)], fill="#ece6dc",
           lw=0.25, color="#9a9184")
    sh.text(*Q(0.86, 0.49), "אור עקיבא", size=3.0, weight=700, color=INK)
    poly([(0.775, 0.68), (0.88, 0.67), (0.885, 0.80), (0.78, 0.81)], fill="#e4e1db", lw=0.2, color="#9a9184")
    sh.text(*Q(0.83, 0.735), "פארק תעשיות", size=2.5, color=INK)
    sh.text(*Q(0.83, 0.765), "קיסריה", size=2.5, color=INK)
    rl = [(0.955, -0.02), (0.955, 1.02)]
    sh.polyline([Q(*p) for p in rl], lw=0.9, color=CHAR)
    sh.polyline([Q(*p) for p in rl], lw=0.5, color="#ffffff", dash="2 2")
    sx_, sy_ = Q(0.955, 0.24)
    sh.rect(sx_ - 2, sy_ - 3, 4, 6, fill="#ffffff", lw=0.35, color=CHAR)
    sh.text(sx_ - 3.2, sy_ - 0.2, "רכבת ישראל –", size=2.4, anchor="right", color=INK)
    sh.text(sx_ - 3.2, sy_ + 3.0, "תחנת קיסריה–פ\"ח", size=2.4, anchor="right", color=INK)
    sh.text(*Q(0.93, 0.92), "קו החוף", size=2.3, anchor="right", color=MUTED)
    # labels on the historic coast
    for (u, v, t, anc) in [(0.165, 0.52, "נמל סבסטוס", "right"), (0.31, 0.335, "אמת המים", "left"),
                           (0.30, 0.66, "התיאטרון", "left"), (0.30, 0.575, "ההיפודרום", "left"),
                           (0.27, 0.43, "העיר הצלבנית", "left")]:
        sh.text(*Q(u, v), t, size=2.45, anchor=anc, color="#6b5536", weight=600)
    sh.text(*Q(0.31, 0.71), "גן לאומי קיסריה", size=2.6, anchor="left", color="#4f5a35", weight=700)
    # destinations
    sh.text(*Q(0.745, 0.025), "חיפה", size=2.5, anchor="right", color=MUTED)
    sh.text(*Q(0.745, 0.985), "חדרה · תל אביב", size=2.5, anchor="right", color=MUTED)
    sh.add("</g>")
    north_arrow(sh, fx0 + fw - 10, fy0 + 14, r=4.5)
    # scale-free note
    sh.text(fx0 + 3, fy0 + fh - 3, "מיקום השכונות והגולף סכמטי בלבד", size=2.2, anchor="left", color=MUTED)


def site_diagram(sh, xl, xr, y0, y1):
    w = xr - xl
    y = heading(sh, xr, y0, w, "02", "ניתוח המגרש – רובע 13")
    leg_w = 66
    gx0, gx1, gy0_, gy1_ = -15.0, 42.0, -7.0, 43.0
    k = min((w - leg_w - 4) / (gx1 - gx0), (y1 - y - 2) / (gy1_ - gy0_))
    ox = xr - (gx1 - gx0) * k - gx0 * k
    oy = y + 1 + gy1_ * k

    def P(x, yy):
        return ox + x * k, oy - yy * k

    def R(x0, y0_, x1, y1_, **kw):
        a, b = P(x0, y1_), P(x1, y0_)
        sh.rect(a[0], a[1], b[0] - a[0], b[1] - a[1], **kw)

    cid = sh.clip_rect(*P(gx0, gy1_), (gx1 - gx0) * k, (gy1_ - gy0_) * k)
    sh.add(f'<g clip-path="url(#{cid})">')
    R(gx0, gy0_, gx1, gy1_, fill="#f7f3ea", color="none")
    # golf
    R(gx0, gy0_, 0, gy1_, fill="#d3ddb8", color="none")
    fair = [P(-11, gy0_), P(-6, 5), P(-9, 18), P(-4.5, 30), P(-8, gy1_), P(-2.5, gy1_), P(-1.5, 30), P(-4, 18),
            P(-1.5, 5), P(-5, gy0_)]
    sh.polyline(fair, closed=True, fill="#e3ebd0", color="none")
    bx, by = P(-10.5, 24)
    sh.add(f'<ellipse cx="{bx:.2f}" cy="{by:.2f}" rx="{2.2 * k:.2f}" ry="{1.2 * k:.2f}" fill="#efe2c4"/>')
    for (tx, ty, r) in [(-13, 8, 1.8), (-12.5, 34, 2.0), (-3, -4, 1.5), (-13.5, 15, 1.4)]:
        sh.circle(*P(tx, ty), r * k, fill="#aab88a", lw=0.15, color="#6f7a52", fop=0.9)
    # neighbours
    for yy0, yy1 in ((36, gy1_), (gy0_, 0)):
        R(0, yy0, 30, yy1, fill="#f1ece2", color="none")
    R(6, 39, 24, gy1_ + 1, fill="pat:block", lw=0.2, color="#9a9184")
    R(5, gy0_ - 1, 23, -3, fill="pat:block", lw=0.2, color="#9a9184")
    # street
    R(30, gy0_, 32.5, gy1_, fill="#e2ddd3", color="none")
    R(32.5, gy0_, gx1, gy1_, fill="#cfcac2", color="none")
    sh.line(*P(37.5, gy0_), *P(37.5, gy1_), lw=0.3, color="#ffffff", dash="3 2")
    sh.add("</g>")
    # lot & setbacks
    L = M.LOT
    ex0, ey0, ex1, ey1 = M.ENVELOPE
    R(ex0, ey0, ex1, ey1, fill=STONE, fop=0.45, lw=0.2, color=SAND_D, dash="1.5 1")
    R(L["x0"], L["y0"], L["x1"], L["y1"], fill="none", lw=0.5, color=CHAR, dash="5 1 1 1")
    # privacy planting along N & S boundaries
    for yy0, yy1 in ((L["y1"] - 1.2, L["y1"]), (L["y0"], L["y0"] + 1.2)):
        R(0.3, yy0, 29.7, yy1, fill="#b9c59a", fop=0.8, color="none")
        for i in range(30):
            sh.circle(*P(0.8 + i * 0.98, (yy0 + yy1) / 2), 0.5 * k, fill="#9aab78", color="none", fop=0.85)
    # building footprint
    R(M.X_W, M.Y_S_G, M.X_E, M.Y_N, fill="#d9c49e", lw=0.35, color=CHAR)
    sh.polyline([P(*p) for p in M.UF_OUT], closed=True, lw=0.3, color=CHAR, dash="2 1")
    R(M.X_W, M.Y_S_U, M.X_M, M.Y_S_G, fill="#ffffff", fop=0.7, lw=0.25, color=CHAR, dash="2 1")
    R(*M.PATIO, fill="#e8dcc3", lw=0.2, color=CHAR)
    P_ = M.POOL
    R(P_["x0"], P_["y0"], P_["x1"], P_["y1"], fill="#b8dbe6", lw=0.3, color="#4f8397")
    cx, cy = P((M.X_W + M.X_E) / 2, (M.Y_S_G + M.Y_N) / 2)
    sh.text(cx, cy + 1.2, "הבית", size=3.0, weight=700, color=CHAR)
    sh.text(*P((M.X_W + M.X_M) / 2, (M.Y_S_U + M.Y_S_G) / 2 - 0.4), "שלוחה", size=2.2, color=MUTED)
    sh.text(*P((P_["x0"] + P_["x1"]) / 2, (P_["y0"] + P_["y1"]) / 2 - 0.5), "בריכה", size=2.4, color="#2f6577")
    # setback dims
    def dim(a, b, txt, off=(0, 0), rot=0):
        pa, pb = P(*a), P(*b)
        sh.line(*pa, *pb, lw=0.18, color=SAND_D)
        for p in (pa, pb):
            sh.line(p[0] - 0.7, p[1] + 0.7, p[0] + 0.7, p[1] - 0.7, lw=0.35, color=SAND_D)
        mx, my = (pa[0] + pb[0]) / 2 + off[0], (pa[1] + pb[1]) / 2 + off[1]
        sh.text(mx, my, txt, size=2.4, weight=700, color=SAND_D, rot=rot)
    dim((0, 9.5), (ex0, 9.5), f"{M.SETBACK['rear']:.0f} מ'", (0, -1.2))
    dim((ex1, 9.5), (30, 9.5), f"{M.SETBACK['front']:.0f} מ'", (0, -1.2))
    dim((27.5, 0), (27.5, ey0), f"{M.SETBACK['side']:.0f} מ'", (2.2, 0.8))
    dim((27.5, ey1), (27.5, 36), f"{M.SETBACK['side']:.0f} מ'", (2.2, 0.8))
    sh.text(*P(15, 37.6), "מגרש שכן", size=2.5, color=MUTED, weight=500)
    sh.text(*P(15, -1.6), "מגרש שכן", size=2.5, color=MUTED, weight=500)
    # street label & access
    sh.text(*P(36.0, 18), "רחוב גישה – מזרח", size=3.0, weight=700, color="#ffffff", rot=-90)
    arrow(sh, *P(35.5, 29.8), *P(26.0, 29.8), lw=0.45, color=CHAR, head=2.0)
    sh.text(*P(31.0, 31.0), "כניסה", size=2.4, weight=700, color=CHAR)
    arrow(sh, *P(35.5, 18.8), *P(27.0, 18.8), lw=0.45, color=CHAR, head=2.0, dash="1.5 1")
    sh.text(*P(31.0, 20.0), "חניה", size=2.4, weight=700, color=CHAR)
    # noise
    for yy in (8.0, 12.0, 25.0, 34.0):
        pts = [P(41.0 - i * 0.55, yy + (0.5 if i % 2 else -0.5)) for i in range(17)]
        sh.polyline(pts, lw=0.3, color="#7a7268")
    sh.text(*P(39.5, 4.5), "רעש תנועה", size=2.4, anchor="middle", color="#5d564d", weight=600)
    # view fan to golf / sunset
    vx, vy = P(M.X_W, 23.5)
    sh.polyline([(vx, vy), P(-14, 37), P(-14, 7)], closed=True, fill=OLIVE, fop=0.16, color="none")
    sh.line(vx, vy, *P(-14, 37), lw=0.25, color=OLIVE, dash="1.5 1")
    sh.line(vx, vy, *P(-14, 7), lw=0.25, color=OLIVE, dash="1.5 1")
    sh.text(*P(-7.5, 21.0), "מבט פתוח", size=2.6, weight=700, color="#4f5a35")
    sh.text(*P(-7.5, 19.0), "לגולף ולשקיעה", size=2.4, color="#4f5a35")
    # winds
    for i in range(3):
        a = P(-14.5, 41.5 - i * 4.6)
        b = P(-4.5, 37.0 - i * 4.6)
        _wave_arrow(sh, *a, *b, SEA, lw=0.5)
    sh.text(*P(-14.3, 42.4), "בריזת ים מערב–צ\"מ", size=2.4, anchor="left", weight=700, color="#4f8397")
    for i in range(2):
        a = P(-14.5, -3.0 + i * 4.0)
        b = P(-6.5, 3.0 + i * 4.0)
        _wave_arrow(sh, *a, *b, "#5d564d", lw=0.5, amp=1.0)
    sh.text(*P(-14.3, -5.6), "סערות חורף מדרום-מערב", size=2.4, anchor="left", weight=700, color="#5d564d")
    for yy in (40.0,):
        _wave_arrow(sh, *P(41.5, yy), *P(32.8, yy), "#c27c2c", lw=0.5, amp=0.6)
    sh.text(*P(41.6, 42.2), "שרב ממזרח", size=2.4, anchor="right", weight=700, color="#c27c2c")
    # sun arc (summer & winter, plan)
    cxm, cym = (M.X_W + M.X_E) / 2, (M.Y_S_G + M.Y_N) / 2 - 2

    def arc(r, a0, a1, color, dash):
        pts = []
        for i in range(41):
            az = math.radians(a0 + (a1 - a0) * i / 40)
            pts.append(P(cxm + r * math.sin(az), cym + r * math.cos(az)))
        sh.polyline(pts, lw=0.35, color=color, dash=dash)
        return pts
    sp = arc(29.0, 62, 298, "#c27c2c", "2 1.2")
    wp = arc(23.0, 118, 242, "#8a6a3c", "0.8 1")
    for p_, t, anc, dx in [(sp[0], "זריחת קיץ 62°", "left", 1.5), (sp[-1], "שקיעת קיץ 298°", "right", -1.5)]:
        sh.circle(*p_, 1.3, fill="#e2a34a", color="none")
    sh.text(*P(cxm, cym - 29.0 + 1.6), "", size=2)
    noon = sp[20]
    sh.circle(*noon, 1.6, fill="#e2a34a", color="none")
    sh.text(noon[0] + 2.4, noon[1] + 1.0, "שמש קיץ 81°", size=2.3, anchor="left", color="#a35f17", weight=600)
    wn = wp[20]
    sh.circle(*wn, 1.3, fill="#b48a4c", color="none")
    sh.text(wn[0] + 2.2, wn[1] + 1.0, "חורף 34°", size=2.3, anchor="left", color="#7a5a2c", weight=600)
    # level
    lx, ly = P(20.5, 33.2)
    sh.text(lx, ly, "±0.00 = +18.50", size=2.3, color=CHAR, weight=600)
    north_arrow(sh, *P(gx0 + 2.6, gy1_ - 10.5), r=4.0)
    # ------------- legend
    lx1 = ox + gx0 * k - 5
    ly = y + 4
    sh.text(lx1, ly, "מקרא", size=2.9, anchor="right", weight=700, color=CHAR)
    ly += 5.5
    items = [
        ("wave", SEA, "בריזת ים קיצית מערב–צפון-מערב"),
        ("wave", "#5d564d", "סערות חורף מדרום-מערב"),
        ("wave", "#c27c2c", "שרב – רוח מזרחית חמה ויבשה"),
        ("dash", "#c27c2c", "מסלול שמש – קיץ (21.6)"),
        ("dot", "#8a6a3c", "מסלול שמש – חורף (21.12)"),
        ("fan", OLIVE, "מבט פתוח לגולף ולשקיעה"),
        ("zig", "#7a7268", "רעש תנועה מן הרחוב"),
        ("hedge", "#9aab78", "מיסוך צמחייה – פרטיות"),
        ("env", SAND_D, "קווי בניין – תחום בנייה"),
        ("lot", CHAR, "גבול מגרש 30×36 מ'"),
    ]
    for kind, col, t in items:
        sx = lx1 - 9
        if kind == "wave":
            _wave_arrow(sh, sx - 1, ly - 1, sx + 7, ly - 1, col, lw=0.4, amp=0.5, n=2, head=1.4)
        elif kind in ("dash", "dot"):
            sh.line(sx, ly - 1, sx + 8, ly - 1, lw=0.4, color=col, dash="2 1.2" if kind == "dash" else "0.8 1")
        elif kind == "fan":
            sh.polyline([(sx, ly - 1), (sx + 8, ly - 3), (sx + 8, ly + 1)], closed=True, fill=col, fop=0.25, color=col, lw=0.15)
        elif kind == "zig":
            sh.polyline([(sx + i, ly - 1 + (0.6 if i % 2 else -0.6)) for i in range(9)], lw=0.3, color=col)
        elif kind == "hedge":
            for i in range(4):
                sh.circle(sx + 1 + i * 2, ly - 1, 0.9, fill=col, color="none")
        elif kind == "env":
            sh.rect(sx, ly - 2.6, 8, 3.2, fill=STONE, lw=0.2, color=col, dash="1.5 1")
        elif kind == "lot":
            sh.line(sx, ly - 1, sx + 8, ly - 1, lw=0.5, color=col, dash="3 0.8 0.8 0.8")
        for j, l in enumerate(wrap(t, leg_w - 16, 2.4)):
            sh.text(lx1 - 11, ly + j * 3.3, l, size=2.4, anchor="right", color=INK)
        ly += 3.3 * len(wrap(t, leg_w - 16, 2.4)) + 3.4
    # key facts under the legend
    ly += 3
    sh.line(lx1 - leg_w + 6, ly, lx1, ly, lw=0.2, color=CHAR)
    ly += 5
    for lab, val in [("שטח המגרש", "1,080 מ\"ר"), ("חזית לרחוב", "30 מ' (מזרח)"), ("עומק", "36 מ'"),
                     ("גבול מערבי", "מגרש הגולף"), ("מפלס ±0.00", "+18.50 מעל פני הים")]:
        sh.text(lx1, ly, lab, size=2.4, anchor="right", color=MUTED)
        sh.text(lx1 - 22, ly, val, size=2.45, anchor="right", weight=600, color=CHAR)
        ly += 4.2


# ---------------------------------------------------------------- climate
CLIMATE = dict(  # approximate long-term means, northern Sharon coastal plain (Hadera / Caesarea)
    tmax=[18, 18.5, 20.5, 23.5, 26, 28.5, 30.5, 31, 30, 27.5, 23.5, 19.5],
    tmin=[8.5, 8.5, 10.5, 13, 16.5, 20, 22.5, 23, 21.5, 18, 13.5, 10],
    rain=[140, 95, 60, 20, 5, 0, 0, 0, 2, 30, 90, 140],
)


def climate_panel(sh, xl, xr, y0, y1):
    w = xr - xl
    y = heading(sh, xr, y0, w, "04", "נתוני אקלים")
    cx0, cx1 = xl + 8, xr - 8
    cy0, cy1 = y + 4, y + 62
    sh.rect(cx0, cy0, cx1 - cx0, cy1 - cy0, fill="#fbf8f2", color="none")
    for t in (0, 10, 20, 30):
        yy = cy1 - t / 35 * (cy1 - cy0)
        sh.line(cx0, yy, cx1, yy, lw=0.08, color=RULE)
        sh.text(cx0 - 1.2, yy + 0.8, f"{t}°", size=2.0, anchor="right", color=MUTED)
    for r in (50, 100, 150):
        yy = cy1 - r / 175 * (cy1 - cy0)
        sh.text(cx1 + 1.2, yy + 0.8, f"{r}", size=2.0, anchor="left", color="#4f8397")
    bw = (cx1 - cx0) / 12
    months = "ינ פב מר אפ מא יונ יול או ספ אוק נו דצ".split()
    for i in range(12):
        r = CLIMATE["rain"][i]
        hgt = r / 175 * (cy1 - cy0)
        sh.rect(cx0 + i * bw + bw * 0.2, cy1 - hgt, bw * 0.6, hgt, fill="#a9cbd7", color="none")
        sh.text(cx0 + i * bw + bw / 2, cy1 + 3.2, months[i], size=2.0, color=MUTED)
    for key, col in (("tmax", "#a5492f"), ("tmin", SAND_D)):
        pts = [(cx0 + i * bw + bw / 2, cy1 - v / 35 * (cy1 - cy0)) for i, v in enumerate(CLIMATE[key])]
        sh.polyline(pts, lw=0.45, color=col)
        for p in pts:
            sh.circle(*p, 0.55, fill=col, color="none")
    sh.line(cx0, cy1, cx1, cy1, lw=0.25, color=CHAR)
    ly = cy1 + 8
    for col, t, kind in (("#a5492f", "טמפ' מקסימום", "l"), (SAND_D, "טמפ' מינימום", "l"), ("#a9cbd7", 'משקעים (מ"מ)', "b")):
        if kind == "l":
            sh.line(xr - 5, ly - 0.9, xr, ly - 0.9, lw=0.5, color=col)
        else:
            sh.rect(xr - 4, ly - 2.4, 3, 3, fill=col, color="none")
        sh.text(xr - 6.5, ly, t, size=2.3, anchor="right", color=INK)
        xr_ = xr
        ly += 0
        xr = xr - 6.5 - tw(t, 2.3) - 5
    xr = xl + w
    y = cy1 + 13
    rows = [("טמפ' ממוצעת יולי–אוגוסט", "31° / 23°"), ("טמפ' ממוצעת ינואר", "18° / 8.5°"),
            ("לחות יחסית", "65%–75% (גבוהה בקיץ)"), ("משקעים שנתיים", 'כ-580 מ"מ, נוב׳–מרץ'),
            ("רוח שלטת", "מערב–צ\"מ, 3–5 מ'/ש'"), ("קרינת שמש", 'כ-2,000 קוט"ש/מ"ר·שנה'),
            ("אוויר", "מלוח – כ-2 ק\"מ מן הים")]
    sh.line(xl, y, xr, y, lw=0.25, color=CHAR)
    for a, b in rows:
        y += 4.5
        sh.text(xr, y, a, size=2.35, anchor="right", color=MUTED)
        sh.text(xl + 46, y, b, size=2.4, anchor="right", weight=600, color=CHAR)
        sh.line(xl, y + 1.6, xr, y + 1.6, lw=0.06, color=RULE)
    sh.text(xr, y + 6.2, "ערכים משוערים – מישור החוף הצפוני (חדרה/קיסריה), לפי ממוצעי השירות המטאורולוגי.",
            size=2.1, anchor="right", color=MUTED)


PLANNING = [
    ("שטח מגרש", '1,080 מ"ר', '1,080 מ"ר'),
    ("שטח עיקרי", '35% = 378 מ"ר', "גיליון 04"),
    ("שטחי שירות", '16% = 173 מ"ר', "גיליון 04"),
    ("תכסית", '40% = 432 מ"ר', None),
    ("קומות", "2 + מרתף", "2 + מרתף + יציאה לגג"),
    ("מרתף", "בקונטור קומה מעל", "בקונטור"),
    ("קו בניין קדמי (מזרח)", "5 מ'", "5 מ'"),
    ("קווי בניין צדדיים", "4 מ'", "4 מ'"),
    ("קו בניין אחורי (מערב)", "6 מ'", "6 מ'"),
    ("חניה", "2 בתחום המגרש", "2 מקורות"),
    ("בריכה – שטח מים", 'עד 60 מ"ר', None),
    ("בריכה – עומק", "עד 1.8 מ'", None),
    ("מערכת PV על הגג", "חובה", "מתוכנן"),
]


def planning_panel(sh, xl, xr, y0, y1):
    w = xr - xl
    y = heading(sh, xr, y0, w, "05", "נתוני תכנון – הנחת בסיס")
    cov = (M.X_E - M.X_W) * (M.Y_N - M.Y_S_G) + (M.X_M - M.X_W) * (M.Y_S_G - M.Y_S_U)
    P_ = M.POOL
    vals = {"תכסית": f'{cov:.0f} מ"ר = {cov / 1080 * 100:.1f}%',
            "בריכה – שטח מים": f'{(P_["x1"] - P_["x0"]) * (P_["y1"] - P_["y0"]):.0f} מ"ר',
            "בריכה – עומק": f'{P_["depth"]:.2f} מ\''}
    c1, c2, c3 = xr, xr - 40, xr - 74
    sh.line(xl, y, xr, y, lw=0.3, color=CHAR)
    for t, x in ((("נושא", c1), ("רובע 13", c2), ("מוצע", c3))):
        sh.text(x, y + 4, t, size=2.4, anchor="right", weight=700, color=MUTED)
    y += 5.8
    sh.line(xl, y, xr, y, lw=0.12, color=CHAR)
    for a, b, c in PLANNING:
        c = vals.get(a, c)
        y += 4.6
        sh.text(c1, y, a, size=2.35, anchor="right", color=INK)
        sh.text(c2, y, b, size=2.35, anchor="right", weight=600, color=CHAR)
        sh.text(c3, y, c, size=2.3, anchor="right", color=OLIVE if c != "גיליון 04" else MUTED, weight=500)
        sh.line(xl, y + 1.7, xr, y + 1.7, lw=0.06, color=RULE)
    y += 6
    sh.rect(xl, y, w, 15, fill="#f6eadf", lw=0.25, color="#a5492f")
    sh.text(xr - 3, y + 5, "יש לאמת מול תב\"ע 303-0207092", size=2.8, anchor="right", weight=700, color="#a5492f")
    para(sh, xr - 3, y + 9.6, w - 6, "ונספח הבינוי של רובע 13 לפני הגשה לוועדה המקומית חוף הכרמל.",
         size=2.3, lh=1.4, color="#7d3a24")
    y += 21
    para(sh, xr, y, w, "תקנות: מדרגות 2R+T = 61–63 ס\"מ, רום עד 17.5; מעקה 105 ס\"מ; ממ\"ד נטו 9 מ\"ר לפחות; "
                       "גובה חדר מגורים 2.50 מ' לפחות.", size=2.25, lh=1.45, color=MUTED)


# ---------------------------------------------------------------- sun path
LAT = 32.5


def sun_pos(decl, hour, lat=LAT):
    H = math.radians(15 * (hour - 12))
    d, p = math.radians(decl), math.radians(lat)
    alt = math.asin(math.sin(p) * math.sin(d) + math.cos(p) * math.cos(d) * math.cos(H))
    az = math.degrees(math.atan2(math.sin(H), math.cos(H) * math.sin(p) - math.tan(d) * math.cos(p))) + 180
    return math.degrees(alt), az % 360


def sunpath_panel(sh, xl, xr, y0, y1):
    w = xr - xl
    y = heading(sh, xr, y0, w, "06", "מסלול השמש – 32.5° צפון")
    R = min(w / 2 - 9, (y1 - y - 40) / 2)
    cx, cy = (xl + xr) / 2, y + R + 7

    def P(alt, az):
        r = R * (90 - alt) / 90
        return cx + r * math.sin(math.radians(az)), cy - r * math.cos(math.radians(az))
    sh.circle(cx, cy, R, fill="#fbf8f2", lw=0.35, color=CHAR)
    for a in (30, 60):
        sh.circle(cx, cy, R * (90 - a) / 90, lw=0.1, color=RULE)
        sh.text(cx + 0.8, cy - R * (90 - a) / 90 - 0.6, f"{a}°", size=1.9, anchor="left", color=MUTED)
    for az in range(0, 360, 30):
        a, b = P(0, az), P(84, az)
        sh.line(*a, *b, lw=0.08, color=RULE)
        ox_, oy_ = P(-9, az)
        lab = {0: "N", 90: "E", 180: "S", 270: "W"}.get(az, f"{az}°")
        sh.text(ox_, oy_ + 0.9, lab, size=2.6 if az % 90 == 0 else 1.9, weight=700 if az % 90 == 0 else 400,
                color=CHAR if az % 90 == 0 else MUTED)
    # lot footprint in the centre
    s = R * 0.012
    fx, fy = cx - 15.5 * s * 1.0, cy
    sh.rect(cx - (M.X_E - M.X_W) / 2 * s, cy - (M.Y_N - M.Y_S_G) / 2 * s - 2 * s, (M.X_E - M.X_W) * s,
            (M.Y_N - M.Y_S_G) * s, fill=SAND, lw=0.15, color=CHAR)
    sh.rect(cx - (M.X_E - M.X_W) / 2 * s, cy + (M.Y_N - M.Y_S_G) / 2 * s - 2 * s, (M.X_M - M.X_W) * s,
            (M.Y_S_G - M.Y_S_U) * s, fill="#ffffff", lw=0.15, color=CHAR)
    curves = [(23.44, "21.6", "#c27c2c"), (0.0, "21.3 / 23.9", "#9c8460"), (-23.44, "21.12", "#6d5a3c")]
    for decl, lab, col in curves:
        pts = []
        h = 3.0
        while h <= 21.0:
            alt, az = sun_pos(decl, h)
            if alt >= -0.5:
                pts.append(P(max(alt, 0), az))
            h += 0.1
        sh.polyline(pts, lw=0.5, color=col)
        for hr in range(5, 20):
            alt, az = sun_pos(decl, hr)
            if alt > 0:
                sh.circle(*P(alt, az), 0.65, fill=col, color="#ffffff", lw=0.15)
                if decl > 0 and hr in (6, 9, 12, 15, 18):
                    px, py = P(alt, az)
                    sh.text(px, py - 1.4, f"{hr}:00", size=1.8, color=col)
        alt, az = sun_pos(decl, 12)
        px, py = P(alt, az)
        sh.text(px + 1.5, py + (3.0 if decl < 0 else 2.6), f"{alt:.0f}°", size=2.1, anchor="left", weight=700, color=col)
    # sunrise / sunset azimuths (summer)
    p_ = math.radians(LAT)
    for decl, col in ((23.44, "#c27c2c"), (-23.44, "#6d5a3c")):
        az = math.degrees(math.acos(math.sin(math.radians(decl)) / math.cos(p_)))
        for a in (az, 360 - az):
            sh.line(cx, cy, *P(0, a), lw=0.15, color=col, dash="1 0.8")
    ly = cy + R + 9
    az_s = math.degrees(math.acos(math.sin(math.radians(23.44)) / math.cos(p_)))
    az_w = math.degrees(math.acos(math.sin(math.radians(-23.44)) / math.cos(p_)))
    for decl, lab, col in curves:
        alt, _ = sun_pos(decl, 12)
        sh.line(xr - 5, ly - 0.9, xr, ly - 0.9, lw=0.6, color=col)
        extra = {23.44: f" · זריחה {az_s:.0f}° / שקיעה {360 - az_s:.0f}°",
                 -23.44: f" · זריחה {az_w:.0f}° / שקיעה {360 - az_w:.0f}°"}.get(decl, " · זריחה 90° / שקיעה 270°")
        sh.text(xr - 6.5, ly, f"{lab} – שיא {alt:.1f}°{extra}", size=2.25, anchor="right", color=INK)
        ly += 4.2
    sh.text(xr, ly + 0.6, "היטל קוטבי – אזימוט מצפון, רדיוס = 90° פחות גובה השמש.", size=2.05, anchor="right",
            color=MUTED)


# ---------------------------------------------------------------- wind rose
WIND = dict(  # % frequency, 16 sectors from N clockwise – schematic values for the coastal plain
    summer=[6, 3, 2, 2, 3, 2, 2, 2, 3, 4, 8, 12, 20, 15, 10, 6],
    winter=[5, 4, 5, 7, 12, 8, 7, 5, 6, 9, 12, 8, 5, 3, 2, 2],
)


def windrose_panel(sh, xl, xr, y0, y1):
    w = xr - xl
    y = heading(sh, xr, y0, w, "07", "שושנת רוחות")
    R = min(w / 2 - 9, (y1 - y - 40) / 2)
    cx, cy = (xl + xr) / 2, y + R + 7
    vmax = 22.0
    for f in (5, 10, 15, 20):
        sh.circle(cx, cy, R * f / vmax, lw=0.1, color=RULE, dash="0.8 0.6" if f % 10 else None)
        sh.text(cx + 0.6, cy - R * f / vmax - 0.5, f"{f}%", size=1.8, anchor="left", color=MUTED)
    lab16 = ["N", "", "NE", "", "E", "", "SE", "", "S", "", "SW", "", "W", "", "NW", ""]
    for i in range(16):
        a = math.radians(i * 22.5)
        sh.line(cx, cy, cx + R * math.sin(a), cy - R * math.cos(a), lw=0.08, color=RULE)
        if lab16[i]:
            sh.text(cx + (R + 4.5) * math.sin(a), cy - (R + 4.5) * math.cos(a) + 0.9, lab16[i], size=2.4,
                    weight=700 if len(lab16[i]) == 1 else 400, color=CHAR if len(lab16[i]) == 1 else MUTED)

    def petals(vals, fill, stroke, fop, width=0.36):
        for i, v in enumerate(vals):
            a = math.radians(i * 22.5)
            r = R * v / vmax
            a0, a1 = a - math.radians(22.5 * width), a + math.radians(22.5 * width)
            pts = [(cx, cy), (cx + r * math.sin(a0), cy - r * math.cos(a0)), (cx + r * math.sin(a1), cy - r * math.cos(a1))]
            sh.polyline(pts, closed=True, fill=fill, fop=fop, lw=0.2, color=stroke)
    petals(WIND["winter"], "#5d564d", "#3c3833", 0.25, 0.42)
    petals(WIND["summer"], SEA, "#3f7a8f", 0.75, 0.3)
    sh.circle(cx, cy, 1.4, fill="#ffffff", lw=0.2, color=CHAR)
    # sharav note
    a = math.radians(90)
    px, py = cx + R * 0.62 * math.sin(a), cy - R * 0.62 * math.cos(a)
    ly = cy + R + 9
    for fill, fop, t in ((SEA, 0.75, "קיץ – בריזת ים מערב–צפון-מערב (צהריים)"),
                         ("#5d564d", 0.25, "חורף – סערות מדרום-מערב, רוח יבשה מזרחית"),
                         ("#c27c2c", 1.0, "שרב – מזרח/דרום-מזרח, אביב וסתיו")):
        sh.rect(xr - 4, ly - 2.5, 3.5, 3.2, fill=fill, fop=fop, color="none")
        sh.text(xr - 6, ly, t, size=2.25, anchor="right", color=INK)
        ly += 4.2
    sh.text(xr, ly + 0.6, "תדירות משוערת לפי עונה – סכמה להמחשה.", size=2.05, anchor="right", color=MUTED)
    # sharav arrow on the rose
    _wave_arrow(sh, cx + R + 1, cy - R * 0.55, cx + R * 0.45, cy - R * 0.22, "#c27c2c", lw=0.45, amp=0.5, n=2, head=1.6)


# ---------------------------------------------------------------- strategy icons
def _icon(sh, x, y, s, kind):
    sh.rect(x, y, s, s, fill="#f6f1e7", lw=0.2, color=SAND_D)
    c = (x + s / 2, y + s / 2)
    if kind == "orient":
        sh.rect(x + s * 0.18, y + s * 0.4, s * 0.64, s * 0.24, fill=SAND, lw=0.25, color=CHAR)
        sh.circle(x + s * 0.5, y + s * 0.86, s * 0.07, fill="#e2a34a", color="none")
        for i in range(-2, 3):
            sh.line(x + s * 0.5 + i * s * 0.12, y + s * 0.78, x + s * 0.5 + i * s * 0.08, y + s * 0.68, lw=0.25, color="#e2a34a")
        arrow(sh, x + s * 0.85, y + s * 0.3, x + s * 0.85, y + s * 0.1, lw=0.3, color=CHAR, head=1.4)
        sh.text(x + s * 0.85, y + s * 0.38, "N", size=2.0, weight=700)
    elif kind == "overhang":
        g = y + s * 0.85
        sh.line(x + s * 0.08, g, x + s * 0.92, g, lw=0.3, color=CHAR)
        sh.rect(x + s * 0.55, y + s * 0.35, s * 0.3, s * 0.5, fill=SAND, lw=0.2, color=CHAR)
        sh.rect(x + s * 0.25, y + s * 0.28, s * 0.6, s * 0.07, fill=CHAR, color="none")
        sh.line(x + s * 0.1, y + s * 0.08, x + s * 0.27, y + s * 0.3, lw=0.35, color="#c27c2c")
        sh.line(x + s * 0.05, y + s * 0.45, x + s * 0.58, y + s * 0.72, lw=0.35, color="#8a6a3c")
    elif kind == "fins":
        for i in range(7):
            xx = x + s * 0.2 + i * s * 0.08
            sh.line(xx, y + s * 0.5, xx + s * 0.06, y + s * 0.38, lw=0.6, color="#a07a50")
        sh.line(x + s * 0.18, y + s * 0.62, x + s * 0.8, y + s * 0.62, lw=0.5, color=CHAR)
        for i in range(3):
            arrow(sh, x + s * 0.05, y + s * (0.12 + i * 0.08), x + s * 0.3, y + s * (0.3 + i * 0.04), lw=0.3, color="#e2a34a", head=1.2)
    elif kind == "vent":
        sh.polyline([(x + s * 0.15, y + s * 0.85), (x + s * 0.15, y + s * 0.4), (x + s * 0.5, y + s * 0.4),
                     (x + s * 0.5, y + s * 0.2), (x + s * 0.7, y + s * 0.2), (x + s * 0.7, y + s * 0.4),
                     (x + s * 0.85, y + s * 0.4), (x + s * 0.85, y + s * 0.85)], lw=0.3, color=CHAR)
        arrow(sh, x + s * 0.02, y + s * 0.72, x + s * 0.55, y + s * 0.72, lw=0.35, color=SEA, head=1.3)
        sh.path(f"M{x + s * 0.55},{y + s * 0.72} Q{x + s * 0.6},{y + s * 0.5} {x + s * 0.6},{y + s * 0.1}", lw=0.35, color="#a5492f")
        arrow(sh, x + s * 0.6, y + s * 0.2, x + s * 0.6, y + s * 0.06, lw=0.35, color="#a5492f", head=1.2)
    elif kind == "salt":
        for i in range(3):
            yy = y + s * (0.62 + i * 0.1)
            sh.path(f"M{x + s * 0.1},{yy} q{s * 0.1},{-s * 0.06} {s * 0.2},0 t{s * 0.2},0 t{s * 0.2},0 t{s * 0.2},0",
                    lw=0.3, color=SEA)
        sh.path(f"M{c[0]},{y + s * 0.12} L{c[0] + s * 0.2},{y + s * 0.2} L{c[0] + s * 0.17},{y + s * 0.42} "
                f"Q{c[0]},{y + s * 0.55} {c[0]},{y + s * 0.55} Q{c[0] - s * 0.17},{y + s * 0.42} {c[0] - s * 0.17},{y + s * 0.42} "
                f"L{c[0] - s * 0.2},{y + s * 0.2} Z", fill=STONE, lw=0.3, color=CHAR)
    elif kind == "pv":
        sh.circle(x + s * 0.78, y + s * 0.22, s * 0.1, fill="#e2a34a", color="none")
        sh.rect(x + s * 0.15, y + s * 0.62, s * 0.7, s * 0.25, fill="#ffffff", lw=0.25, color=CHAR)
        sh.polyline([(x + s * 0.2, y + s * 0.6), (x + s * 0.58, y + s * 0.42), (x + s * 0.62, y + s * 0.5),
                     (x + s * 0.26, y + s * 0.62)], closed=True, fill="#55657c", lw=0.2, color=CHAR)


STRATEGIES = [
    ("orient", "אוריינטציה", "ציר ארוך מזרח–מערב; חללי המגורים והוויטרינות פונים דרומה אל הגן, חזית הרחוב במזרח "
                             "סגורה ושקטה."),
    ("overhang", "הצללה דרומית", "שלוחה של 5 מ' ולוג'יה שקועה 1.6 מ' – חוסמות את שמש הקיץ (81°) ומכניסות את שמש "
                                 "החורף (34°)."),
    ("fins", "רפפות מערביות", "רפפות אנכיות 50/200 מ\"מ במרווח 180 בחזית המערבית חוסמות את שמש אחר-הצהריים "
                              "הנמוכה ושומרות על המבט לגולף."),
    ("vent", "אוורור צולב וארובה", "פתחים מנוגדים בכיוון בריזת הים, ופליטת אוויר חם דרך חדר המדרגות והיציאה לגג; "
                                   "פטיו שקוע מאוורר את המרתף."),
    ("salt", "חומרים לאוויר מלוח", "אלומיניום בגימור ימי, נירוסטה 316, אבן טבעית ספוגה, טיח סיליקט; פרטי איטום "
                                   "וניקוז מוגברים."),
    ("pv", "אנרגיה ומים", "מערכת PV על הגג (חובה), דוד שמש, השקיה בטפטוף וצמחייה ים-תיכונית חסכונית במים."),
]


def strategies_panel(sh, xl, xr, y0, y1):
    w = xr - xl
    y = heading(sh, xr, y0, w, "03", "אסטרטגיות תכנון – מן הניתוח אל הבית")
    g = 10
    cw = (w - g) / 2
    rh = (y1 - y) / 3
    s = 22
    for i, (kind, t, d) in enumerate(STRATEGIES):
        col, row = i % 2, i // 2
        x1 = xr - col * (cw + g)
        yy = y + row * rh
        _icon(sh, x1 - s, yy, s, kind)
        sh.text(x1 - s - 4, yy + 3.6, f"{i + 1:02d}  {t}", size=3.0, anchor="right", weight=700, color=CHAR)
        para(sh, x1 - s - 4, yy + 8.6, cw - s - 4, d, size=2.55, lh=1.5, color=INK)
        if row < 2:
            sh.line(x1 - cw, yy + rh - 4, x1, yy + rh - 4, lw=0.08, color=RULE)


def sheet_site_analysis(sh, box):
    G = Grid(box)
    y = board_header(sh, G, "ניתוח אתר וסביבה", "קיסריה · רובע 13 (שכונת הגולף) · אקלים, תכנון ואסטרטגיות",
                     "BEIT KURKAR  ·  SITE & CLIMATE ANALYSIS")
    yA1 = y + 268
    xl, xr, w = G.col(0, 3)
    caesarea_map(sh, xl, xr, y, yA1)
    xl, xr, w = G.col(3, 3)
    site_diagram(sh, xl, xr, y, yA1)
    sh.line(G.x0, yA1 + 6, G.x1, yA1 + 6, lw=0.15, color=RULE)
    yB = yA1 + 11
    ybot = G.y1
    xl, xr, w = G.col(0, 2)
    strategies_panel(sh, xl, xr, yB, ybot)
    xl, xr, w = G.col(2)
    climate_panel(sh, xl, xr, yB, ybot)
    xl, xr, w = G.col(3)
    planning_panel(sh, xl, xr, yB, ybot)
    xl, xr, w = G.col(4)
    sunpath_panel(sh, xl, xr, yB, ybot)
    xl, xr, w = G.col(5)
    windrose_panel(sh, xl, xr, yB, ybot)
