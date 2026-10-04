"""Helpers for construction-detail sheets (stair sheet, wall section & details).

* A small "scene" renderer: shapely geometry in model metres (x horizontal, z up)
  is clipped into kept vertical bands (to allow break lines in tall sections) and
  drawn on a Sheet at true scale.
* Annotation helpers in paper mm: leaders, build-up callouts, dimensions,
  level tags, detail bubbles, break lines.
* Extra hatch patterns kept in this module (registered in sh.defs_extra).
"""
from __future__ import annotations

import math

from shapely.geometry import (GeometryCollection, LineString, MultiLineString, MultiPolygon, Polygon,
                              box as sbox)
from shapely.ops import unary_union

import draw as D

# --------------------------------------------------------------------------- #
#  extra hatch patterns (paper mm)
# --------------------------------------------------------------------------- #
XPAT = {
    "glass": ('<pattern id="dx_glass" patternUnits="userSpaceOnUse" width="4" height="4">'
              '<rect width="4" height="4" fill="#e2f0f5"/>'
              '<path d="M0.6,3.4 L1.8,2.2 M2.3,1.7 L2.9,1.1" stroke="#7fa9ba" stroke-width="0.07"/></pattern>'),
    "xps": ('<pattern id="dx_xps" patternUnits="userSpaceOnUse" width="1.4" height="1.4">'
            '<rect width="1.4" height="1.4" fill="#f7eef4"/>'
            '<path d="M0,0 L1.4,1.4 M1.4,0 L0,1.4" stroke="#7d5670" stroke-width="0.06"/></pattern>'),
    "wool": ('<pattern id="dx_wool" patternUnits="userSpaceOnUse" width="1.6" height="1.6">'
             '<rect width="1.6" height="1.6" fill="#fffbea"/>'
             '<path d="M0,0.8 L0.4,0.2 L0.8,0.8 L1.2,1.4 L1.6,0.8" stroke="#8b7a35" stroke-width="0.07" fill="none"/></pattern>'),
    "woolv": ('<pattern id="dx_woolv" patternUnits="userSpaceOnUse" width="1.6" height="1.6">'
              '<rect width="1.6" height="1.6" fill="#fffbea"/>'
              '<path d="M0.8,0 L0.2,0.4 L0.8,0.8 L1.4,1.2 L0.8,1.6" stroke="#8b7a35" stroke-width="0.07" fill="none"/></pattern>'),
    "eps": ('<pattern id="dx_eps" patternUnits="userSpaceOnUse" width="1.5" height="1.5">'
            '<rect width="1.5" height="1.5" fill="#f4f7fb"/>'
            '<circle cx="0.4" cy="0.45" r="0.25" fill="none" stroke="#6d7d90" stroke-width="0.05"/>'
            '<circle cx="1.15" cy="1.1" r="0.22" fill="none" stroke="#6d7d90" stroke-width="0.05"/></pattern>'),
    "alu": ('<pattern id="dx_alu" patternUnits="userSpaceOnUse" width="2" height="2">'
            '<rect width="2" height="2" fill="#c9ced4"/></pattern>'),
    "aluwood": ('<pattern id="dx_aluwood" patternUnits="userSpaceOnUse" width="2" height="1">'
                '<rect width="2" height="1" fill="#c99a63"/>'
                '<path d="M0,0.5 q0.5,-0.2 1,0 t1,0" fill="none" stroke="#8a5f30" stroke-width="0.06"/></pattern>'),
    "ss": ('<pattern id="dx_ss" patternUnits="userSpaceOnUse" width="2" height="2">'
           '<rect width="2" height="2" fill="#8e969e"/></pattern>'),
    "porc": ('<pattern id="dx_porc" patternUnits="userSpaceOnUse" width="2" height="2">'
             '<rect width="2" height="2" fill="#e4ded2"/></pattern>'),
    "fill": ('<pattern id="dx_fill" patternUnits="userSpaceOnUse" width="2.2" height="2.2">'
             '<rect width="2.2" height="2.2" fill="#fbfaf6"/>'
             '<circle cx="0.6" cy="0.6" r="0.32" fill="none" stroke="#777" stroke-width="0.05"/>'
             '<circle cx="1.6" cy="1.55" r="0.22" fill="none" stroke="#777" stroke-width="0.05"/>'
             '<circle cx="1.5" cy="0.4" r="0.07" fill="#777"/></pattern>'),
    "mortar": ('<pattern id="dx_mortar" patternUnits="userSpaceOnUse" width="1" height="1">'
               '<rect width="1" height="1" fill="#f1efea"/>'
               '<circle cx="0.3" cy="0.3" r="0.06" fill="#555"/><circle cx="0.8" cy="0.75" r="0.05" fill="#555"/></pattern>'),
    "gyps": ('<pattern id="dx_gyps" patternUnits="userSpaceOnUse" width="1" height="1">'
             '<rect width="1" height="1" fill="#fafafa"/><circle cx="0.5" cy="0.5" r="0.07" fill="#777"/></pattern>'),
    "drain": ('<pattern id="dx_drain" patternUnits="userSpaceOnUse" width="1.2" height="1.2">'
              '<rect width="1.2" height="1.2" fill="#d6d6d6"/>'
              '<path d="M0.6,0 L0.2,0.6 L0.6,1.2" stroke="#333" stroke-width="0.07" fill="none"/></pattern>'),
    "led": ('<pattern id="dx_led" patternUnits="userSpaceOnUse" width="2" height="2">'
            '<rect width="2" height="2" fill="#ffd23f"/></pattern>'),
    "rubber": ('<pattern id="dx_rubber" patternUnits="userSpaceOnUse" width="2" height="2">'
               '<rect width="2" height="2" fill="#3a3a3a"/></pattern>'),
    "plast": ('<pattern id="dx_plast" patternUnits="userSpaceOnUse" width="1" height="1">'
              '<rect width="1" height="1" fill="#fdfdfd"/><circle cx="0.5" cy="0.5" r="0.08" fill="#555"/></pattern>'),
    "teak": ('<pattern id="dx_teak" patternUnits="userSpaceOnUse" width="2" height="0.8">'
             '<rect width="2" height="0.8" fill="#d9b48a"/>'
             '<path d="M0,0.4 q0.5,-0.25 1,0 t1,0" fill="none" stroke="#7d5530" stroke-width="0.06"/></pattern>'),
    "water": ('<pattern id="dx_water" patternUnits="userSpaceOnUse" width="5" height="2.5">'
              '<rect width="5" height="2.5" fill="#d5eaf1"/>'
              '<path d="M0,1.2 q1.25,-0.7 2.5,0 t2.5,0" fill="none" stroke="#6fa6ba" stroke-width="0.08"/></pattern>'),
    "rcd": ('<pattern id="dx_rcd" patternUnits="userSpaceOnUse" width="2.4" height="2.4">'
            '<rect width="2.4" height="2.4" fill="#ffffff"/>'
            '<path d="M0,2.4 L2.4,0 M-0.6,0.6 L0.6,-0.6 M1.8,3 L3,1.8" stroke="#000" stroke-width="0.1"/>'
            '<circle cx="0.7" cy="0.8" r="0.14" fill="#000"/>'
            '<path d="M1.5,1.6 l0.4,0.12 l-0.28,0.32z" fill="none" stroke="#000" stroke-width="0.06"/></pattern>'),
    "blk": ('<pattern id="dx_blk" patternUnits="userSpaceOnUse" width="1.5" height="1.5" patternTransform="rotate(45)">'
            '<rect width="1.5" height="1.5" fill="#fff"/>'
            '<line x1="0" y1="0" x2="0" y2="1.5" stroke="#000" stroke-width="0.11"/></pattern>'),
    "lime": ('<pattern id="dx_lime" patternUnits="userSpaceOnUse" width="3" height="3">'
             '<rect width="3" height="3" fill="#efe3c9"/>'
             '<circle cx="0.8" cy="0.7" r="0.12" fill="#9c8358"/><circle cx="2.2" cy="2.0" r="0.09" fill="#9c8358"/>'
             '<path d="M1.6,0.5 l0.5,0.25" stroke="#9c8358" stroke-width="0.06"/></pattern>'),
    "sandx": ('<pattern id="dx_sandx" patternUnits="userSpaceOnUse" width="1.6" height="1.6">'
              '<rect width="1.6" height="1.6" fill="#f6f1e4"/>'
              '<circle cx="0.4" cy="0.4" r="0.07" fill="#8a7d64"/><circle cx="1.2" cy="1.1" r="0.07" fill="#8a7d64"/></pattern>'),
    "pv": ('<pattern id="dx_pv" patternUnits="userSpaceOnUse" width="2" height="2">'
           '<rect width="2" height="2" fill="#3f4f68"/></pattern>'),
}


def fill_ref(sh, f):
    """'dx:name' → url to a module pattern (registered once); other fills pass through."""
    if isinstance(f, str) and f.startswith("dx:"):
        name = f[3:]
        reg = sh.__dict__.setdefault("_dx_pats", set())
        if name not in reg:
            reg.add(name)
            sh.defs_extra.append(XPAT[name])
        return f"url(#dx_{name})"
    return f


def tw(t, size):
    """approximate text width (mm)"""
    n = 0.0
    for ch in str(t):
        if ch in " .,:;'\"|()-/×":
            n += 0.32
        elif ch.isdigit():
            n += 0.55
        else:
            n += 0.56
    return n * size


# --------------------------------------------------------------------------- #
#  frame with kept bands (vertical breaks)
# --------------------------------------------------------------------------- #
class Frame:
    """Model (x, z) metres → paper mm.

    ox, oy: paper position of model point (x0, 0) in the lowest band.
    bands: kept z-intervals (ascending). Between consecutive bands the removed
    height is replaced by `gap` mm of paper (break lines).
    flip: mirror x (model x grows to the paper-left).
    clip: (xmin, xmax) model x range drawn.
    """

    def __init__(self, sh, ox, oy, scale, x0=0.0, bands=None, gap=5.0, flip=False, clip=None):
        self.sh = sh
        self.ox, self.oy = ox, oy
        self.k = 1000.0 / scale
        self.scale = scale
        self.x0 = x0
        self.flip = flip
        self.bands = bands or [(-1e3, 1e3)]
        self.gap = gap
        self.clip = clip
        offs = [0.0]
        for (a, b), (c, d) in zip(self.bands, self.bands[1:]):
            offs.append(offs[-1] + (c - b) - gap / self.k)
        self.offs = offs

    def band_of(self, z):
        for i, (a, b) in enumerate(self.bands):
            if a - 1e-9 <= z <= b + 1e-9:
                return i
        # nearest
        best, bi = 1e9, 0
        for i, (a, b) in enumerate(self.bands):
            d = min(abs(z - a), abs(z - b))
            if d < best:
                best, bi = d, i
        return bi

    def X(self, x):
        return self.ox + (-(x - self.x0) if self.flip else (x - self.x0)) * self.k

    def Y(self, z, band=None):
        i = self.band_of(z) if band is None else band
        return self.oy - (z - self.offs[i]) * self.k

    def P(self, x, z, band=None):
        return self.X(x), self.Y(z, band)

    def L(self, d):
        """model length → paper mm"""
        return d * self.k

    # -------------------------------------------------------------- render
    def render(self, items):
        """items: list of (geom, style dict)."""
        for bi, (a, b) in enumerate(self.bands):
            xmin, xmax = self.clip if self.clip else (-1e4, 1e4)
            cb = sbox(xmin, a, xmax, b)
            for g, st in items:
                if g is None or g.is_empty:
                    continue
                gg = g.intersection(cb) if (a > -999 or self.clip) else g
                if gg.is_empty:
                    continue
                self._draw(gg, st, bi)

    def _draw(self, g, st, bi):
        sh = self.sh
        st = dict(st)
        fill = fill_ref(sh, st.pop("fill", "none"))
        if isinstance(g, (Polygon, MultiPolygon)):
            polys = [g] if isinstance(g, Polygon) else list(g.geoms)
            for p in polys:
                d = ""
                for ring in [p.exterior] + list(p.interiors):
                    pts = [self.P(x, z, bi) for x, z in ring.coords]
                    d += "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + " Z "
                s = sh.style(fill=fill, **st)
                sh.add(f'<path d="{d}" fill-rule="evenodd" {s}/>')
        elif isinstance(g, (LineString, MultiLineString)):
            lines = [g] if isinstance(g, LineString) else list(g.geoms)
            for l in lines:
                sh.polyline([self.P(x, z, bi) for x, z in l.coords], **st)
        elif isinstance(g, GeometryCollection):
            for gg in g.geoms:
                self._draw(gg, dict(st, fill=fill), bi)

    def breaks(self, x_from, x_to, amp=1.6):
        """break lines between bands across model x range"""
        for i in range(len(self.bands) - 1):
            ya = self.Y(self.bands[i][1], i)
            yb = self.Y(self.bands[i + 1][0], i + 1)
            for y in (ya, yb):
                breakline(self.sh, self.X(x_from) - 3, y, self.X(x_to) + 3, y, amp=amp)


# --------------------------------------------------------------------------- #
#  geometry helpers (model space)
# --------------------------------------------------------------------------- #
def R(x0, z0, x1, z1):
    return sbox(min(x0, x1), min(z0, z1), max(x0, x1), max(z0, z1))


def PG(pts):
    return Polygon(pts)


def LN(pts):
    return LineString(pts)


def U(*gs):
    return unary_union([g for g in gs if g is not None])


def circle_poly(cx, cz, r, n=40):
    return Polygon([(cx + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)])


def ring(cx, cz, r, t, n=40):
    return circle_poly(cx, cz, r, n).difference(circle_poly(cx, cz, r - t, n))


# --------------------------------------------------------------------------- #
#  paper annotation helpers
# --------------------------------------------------------------------------- #
def breakline(sh, x1, y1, x2, y2, amp=1.6, lw="xs"):
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    m = L / 2
    pts = [(x1, y1), (x1 + ux * (m - amp * 0.6), y1 + uy * (m - amp * 0.6)),
           (x1 + ux * (m - amp * 0.2) + nx * amp, y1 + uy * (m - amp * 0.2) + ny * amp),
           (x1 + ux * (m + amp * 0.2) - nx * amp, y1 + uy * (m + amp * 0.2) - ny * amp),
           (x1 + ux * (m + amp * 0.6), y1 + uy * (m + amp * 0.6)), (x2, y2)]
    sh.polyline(pts, lw=lw)


def text_lines(sh, x, y, lines, size=2.2, anchor="left", lh=1.32, weight=400, color="#000"):
    for i, t in enumerate(lines):
        sh.text(x, y + i * size * lh, t, size=size, anchor=anchor, weight=weight, color=color)


def leader(sh, tx, ty, ex, ey, lines, side="right", size=2.2, shoulder=3.0, dot=True, arrow=False, lw="xs",
           num=None, weight=400):
    """Leader from target (tx,ty) to elbow (ex,ey), shoulder, text block.

    side: 'right' → text to the right of the elbow; 'left' → to the left.
    The first text line sits on the shoulder line; further lines below.
    """
    if isinstance(lines, str):
        lines = [lines]
    sgn = 1 if side == "right" else -1
    sh.line(tx, ty, ex, ey, lw=lw)
    sx = ex + sgn * shoulder
    sh.line(ex, ey, sx, ey, lw=lw)
    if dot:
        sh.circle(tx, ty, 0.45, lw="xxs", fill="#000")
    if arrow:
        a = math.atan2(ty - ey, tx - ex)
        L = 1.8
        p1 = (tx - L * math.cos(a - 0.28), ty - L * math.sin(a - 0.28))
        p2 = (tx - L * math.cos(a + 0.28), ty - L * math.sin(a + 0.28))
        sh.polyline([p1, (tx, ty), p2], closed=True, lw="xxs", fill="#000")
    x = sx + sgn * 0.8
    if num is not None:
        r = size * 0.62
        cx = x + sgn * r
        sh.circle(cx, ey, r, lw="xs", fill="#fff")
        sh.text(cx, ey + size * 0.33, str(num), size=size * 0.8, weight=700)
        x = cx + sgn * (r + 0.8)
    anchor = "left" if side == "right" else "right"
    for i, t in enumerate(lines):
        sh.text(x, ey + size * 0.35 + i * size * 1.3, t, size=size, anchor=anchor,
                weight=weight if i == 0 else 400)
    w = max(tw(t, size) for t in lines)
    return (x, ey, x + sgn * w)


def stack_callout(sh, targets, ex, ey, lines, side="right", size=2.2, lh=1.38, lw="xs", head=True):
    """Build-up callout: a straight leader through several layer targets (paper pts), ending at
    (ex,ey); text lines stacked from ey downward (one per layer, top-down)."""
    if isinstance(lines, str):
        lines = [lines]
    sgn = 1 if side == "right" else -1
    pts = list(targets)
    far = pts[0]
    sh.line(far[0], far[1], ex, ey, lw=lw)
    for (x, y) in pts:
        sh.circle(x, y, 0.4, lw="xxs", fill="#000")
    sx = ex + sgn * 3
    sh.line(ex, ey, sx, ey, lw=lw)
    x = sx + sgn * 0.8
    anchor = "left" if side == "right" else "right"
    for i, t in enumerate(lines):
        sh.text(x, ey + size * 0.35 + i * size * lh, t, size=size, anchor=anchor)


def dimh(sh, x1, x2, y, text=None, ext=None, size=2.0, tick=1.1, lw="xs", above=True, color="#000"):
    """horizontal dimension at paper y between x1, x2. ext: paper y where extension lines start
    (scalar or (y_for_x1, y_for_x2))."""
    if x2 < x1:
        x1, x2 = x2, x1
    sh.line(x1 - 1.0, y, x2 + 1.0, y, lw=lw, color=color)
    for x in (x1, x2):
        sh.line(x - tick / 2, y + tick / 2, x + tick / 2, y - tick / 2, lw="m", color=color)
    if ext is not None:
        e = ext if isinstance(ext, (tuple, list)) else (ext, ext)
        for x, ey in zip((x1, x2), e):
            if ey is None:
                continue
            d = 1.2 if y > ey else -1.2
            sh.line(x, ey + (0.8 if y > ey else -0.8), x, y + d, lw="xxs", color="#444")
    if text is None:
        return
    w = tw(text, size)
    tx = (x1 + x2) / 2
    if w + 1.0 > (x2 - x1):
        tx = x2 + 1.5 + w / 2
    sh.text(tx, y - 0.7 if above else y + size + 0.3, text, size=size, color=color)


def dimv(sh, y1, y2, x, text=None, ext=None, size=2.0, tick=1.1, lw="xs", left=True, color="#000"):
    """vertical dimension at paper x between y1, y2; text rotated, left of the line."""
    if y2 < y1:
        y1, y2 = y2, y1
    sh.line(x, y1 - 1.0, x, y2 + 1.0, lw=lw, color=color)
    for y in (y1, y2):
        sh.line(x - tick / 2, y + tick / 2, x + tick / 2, y - tick / 2, lw="m", color=color)
    if ext is not None:
        e = ext if isinstance(ext, (tuple, list)) else (ext, ext)
        for y, ex in zip((y1, y2), e):
            if ex is None:
                continue
            d = 1.2 if x > ex else -1.2
            sh.line(ex + (0.8 if x > ex else -0.8), y, x + d, y, lw="xxs", color="#444")
    if text is None:
        return
    w = tw(text, size)
    ty = (y1 + y2) / 2
    if w + 1.0 > (y2 - y1):
        ty = y1 - 1.5 - w / 2
    tx = x - 0.7 if left else x + size + 0.1
    sh.add(f'<text x="{tx:.3f}" y="{ty:.3f}" font-family="{D.FONT}" font-size="{size}" text-anchor="middle" '
           f'fill="{color}" transform="rotate(-90 {tx:.3f} {ty:.3f})">{D.esc(text)}</text>')


def dim_chain_h(sh, xs, y, texts=None, ext=None, size=2.0, alt=True):
    xs = list(xs)
    for i in range(len(xs) - 1):
        t = texts[i] if texts else None
        dimh(sh, xs[i], xs[i + 1], y, None, ext=ext, size=size)
    if texts:
        last_r = -1e9
        for i in range(len(xs) - 1):
            t = texts[i]
            if not t:
                continue
            x1, x2 = sorted((xs[i], xs[i + 1]))
            w = tw(t, size)
            tx = (x1 + x2) / 2
            ty = y - 0.7
            if w + 0.6 > x2 - x1:
                ty = y + size + 0.4 if alt else y - 0.7 - size - 0.3
            sh.text(tx, ty, t, size=size)


def dim_chain_v(sh, ys, x, texts=None, ext=None, size=2.0, left=True):
    ys = list(ys)
    for i in range(len(ys) - 1):
        dimv(sh, ys[i], ys[i + 1], x, None, ext=ext, size=size)
    if texts:
        for i in range(len(ys) - 1):
            t = texts[i]
            if not t:
                continue
            y1, y2 = sorted((ys[i], ys[i + 1]))
            w = tw(t, size)
            ty = (y1 + y2) / 2
            tx = x - 0.7 if left else x + size + 0.1
            if w + 0.6 > y2 - y1:
                tx = x + size + 0.3 if left else x - 0.9
            sh.add(f'<text x="{tx:.3f}" y="{ty:.3f}" font-family="{D.FONT}" font-size="{size}" text-anchor="middle" '
                   f'transform="rotate(-90 {tx:.3f} {ty:.3f})">{D.esc(t)}</text>')


def level_tag(sh, x, y, text, side="right", size=2.2, line=8.0, filled=True, note=None, bg=False):
    """section level marker: triangle with apex on (x,y), horizontal line, value above."""
    t = 1.4
    if bg:
        sgn_ = 1 if side == "right" else -1
        wbg = tw(text, size) + 1.2
        x0_ = x + sgn_ * (t + 0.2) if sgn_ > 0 else x - (t + 0.2) - wbg
        sh.rect(x0_, y - t * 1.35 - 0.5 - size * 0.85, wbg, size * 1.05, color="none", fill="#fff", opacity=0.9)
    sh.path(f"M{x:.3f},{y:.3f} L{x - t:.3f},{y - t * 1.35:.3f} L{x + t:.3f},{y - t * 1.35:.3f} Z", lw="xs",
            fill="#000" if filled else "#fff")
    sgn = 1 if side == "right" else -1
    sh.line(x - sgn * 1.6, y, x + sgn * line, y, lw="xxs")
    sh.text(x + sgn * (t + 0.6), y - t * 1.35 - 0.5, text, size=size, anchor="left" if side == "right" else "right",
            weight=500)
    if note:
        sh.text(x + sgn * (t + 0.6), y + size + 0.3, note, size=max(2.0, size * 0.85), anchor="left" if side == "right" else "right",
                color="#333")


def fmt_lv(z, dec=2):
    if abs(z) < 0.0005:
        return "±0.00"
    return f"{z:+.{dec}f}"


def bubble(sh, x, y, label, sheet=None, r=4.2, size=None):
    """detail bubble: circle with label (and sheet number in the lower half)."""
    sh.circle(x, y, r, lw="m", fill="#fff")
    if sheet is not None:
        sh.line(x - r, y, x + r, y, lw="xs")
        sh.text(x, y - 0.8, label, size=size or r * 0.75, weight=700)
        sh.text(x, y + r * 0.66, str(sheet), size=max(2.0, r * 0.48))
    else:
        sh.text(x, y + (size or r * 0.9) * 0.36, label, size=size or r * 0.9, weight=700)


def detail_ref(sh, cx, cy, r, label, sheet=None, ang=-40, br=4.0):
    """dashed circle around a region + bubble on its rim."""
    sh.circle(cx, cy, r, lw="s", dash="1.6 0.9")
    a = math.radians(ang)
    bx, by = cx + (r + br) * math.cos(a), cy + (r + br) * math.sin(a)
    bubble(sh, bx, by, label, sheet, r=br)


def detail_title(sh, x_right, y, label, title, scale_txt, width=None, size=4.6, sheet=None):
    """Detail title: bubble with label at right, underlined title to its left + scale."""
    r = 4.6
    bx = x_right - r
    bubble(sh, bx, y - 1.2, label, sheet, r=r)
    xr = x_right - 2 * r - 2.5
    w = width or max(tw(title, size) + 4, 40)
    sh.text(xr, y, title, size=size, anchor="right", weight=700)
    sh.line(xr - w, y + 1.6, xr, y + 1.6, lw="l")
    sh.line(xr - w, y + 2.4, xr, y + 2.4, lw="xs")
    if scale_txt:
        sh.text(xr, y + 2.4 + size * 0.95, scale_txt, size=size * 0.62, anchor="right", weight=500)


def north_tick(sh, x, y):
    pass


def arrow_line(sh, pts, lw="s", head=1.8):
    """polyline ending with a filled arrow head"""
    sh.polyline(pts, lw=lw)
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    a = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - head * math.cos(a - 0.35), y2 - head * math.sin(a - 0.35))
    p2 = (x2 - head * math.cos(a + 0.35), y2 - head * math.sin(a + 0.35))
    sh.polyline([p1, (x2, y2), p2], closed=True, lw="xxs", fill="#000")


def ltr(s):
    """isolate a left-to-right run (levels, dims) inside Hebrew text"""
    return "⁦" + str(s) + "⁩"


def callout_col(sh, items, x_text, side="right", y_min=None, y_max=None, size=2.0, gap=1.6, lh=1.3,
                elbow=3.0, dot=True):
    """Place a column of leader callouts without crossings.

    items: (tx, ty, lines) for a single target, or (targets, lines) for a build-up
    stack (one leader through several layer points, one text line per layer).
    Blocks are pushed apart top-down and kept inside [y_min, y_max].
    """
    norm = []
    for it in items:
        if len(it) == 2:
            pts, lines = it
            norm.append((pts, lines, min(p[1] for p in pts)))
        else:
            tx, ty, lines = it
            norm.append(([(tx, ty)], lines, ty))
    norm.sort(key=lambda it: it[2])
    hs = [size * lh * (len(it[1]) - 1) + size * 0.9 for it in norm]
    ys = []
    cur = -1e9
    for it, h in zip(norm, hs):
        y = max(it[2], cur)
        if y_min is not None:
            y = max(y, y_min)
        ys.append(y)
        cur = y + h + gap
    if y_max is not None and ys:
        over = ys[-1] + hs[-1] - y_max
        if over > 0:
            ys[-1] -= over
            for i in range(len(ys) - 2, -1, -1):
                ys[i] = min(ys[i], ys[i + 1] - hs[i] - gap)
    sgn = 1 if side == "right" else -1
    for (pts, lines, _), y in zip(norm, ys):
        ex = x_text - sgn * elbow
        if len(pts) == 1:
            leader(sh, pts[0][0], pts[0][1], ex, y, lines, side=side, size=size, shoulder=elbow - 0.8, dot=dot)
        else:
            # leader through all layer points (ordered from the elbow outward)
            far = max(pts, key=lambda p: abs(p[0] - ex) + abs(p[1] - y))
            sh.line(far[0], far[1], ex, y, lw="xs")
            for (px, py) in pts:
                sh.circle(px, py, 0.4, lw="xxs", fill="#000")
            sh.line(ex, y, ex + sgn * (elbow - 0.8), y, lw="xs")
            for i, t in enumerate(lines):
                sh.text(x_text, y + size * 0.35 + i * size * lh, t, size=size,
                        anchor="left" if side == "right" else "right")
    return ys
