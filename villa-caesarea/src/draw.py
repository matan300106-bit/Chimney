"""Drawing primitives with two backends: SVG (paper mm) and DXF (model metres).

Every drawing is composed on a `Sheet` (paper space, millimetres, y down).
A `View` places model geometry (metres, y up) on the sheet at a true scale,
and mirrors everything it draws into an optional DXF document so each
drawing can also be opened in CAD at 1:1.
"""
from __future__ import annotations

import html
import math
import re

HEB = re.compile(r"[֐-׿]")

# line weights (mm on paper)
LW = dict(xxs=0.09, xs=0.13, s=0.18, m=0.25, l=0.35, xl=0.5, xxl=0.7, xxxl=1.0)

FONT = "Heebo"


def esc(t):
    return html.escape(str(t), quote=True)


# --------------------------------------------------------------------------- #
#  SVG hatch patterns (paper mm, userSpaceOnUse)
# --------------------------------------------------------------------------- #
PATTERNS = {
    # concrete: diagonal lines + aggregate dots
    "concrete": ('<pattern id="concrete" patternUnits="userSpaceOnUse" width="3" height="3">'
                 '<rect width="3" height="3" fill="#ffffff"/>'
                 '<path d="M0,3 L3,0" stroke="#000" stroke-width="0.12"/>'
                 '<circle cx="0.8" cy="0.9" r="0.18" fill="#000"/>'
                 '<path d="M2.0,2.0 l0.5,0.15 l-0.35,0.4z" fill="none" stroke="#000" stroke-width="0.08"/>'
                 '</pattern>'),
    "rc": ('<pattern id="rc" patternUnits="userSpaceOnUse" width="1.6" height="1.6" patternTransform="rotate(45)">'
           '<rect width="1.6" height="1.6" fill="#ffffff"/>'
           '<line x1="0" y1="0" x2="0" y2="1.6" stroke="#000" stroke-width="0.35"/></pattern>'),
    "block": ('<pattern id="block" patternUnits="userSpaceOnUse" width="1.4" height="1.4" patternTransform="rotate(45)">'
              '<rect width="1.4" height="1.4" fill="#fff"/>'
              '<line x1="0" y1="0" x2="0" y2="1.4" stroke="#000" stroke-width="0.12"/></pattern>'),
    "partition": ('<pattern id="partition" patternUnits="userSpaceOnUse" width="1.0" height="1.0" patternTransform="rotate(-45)">'
                  '<rect width="1" height="1" fill="#fff"/>'
                  '<line x1="0" y1="0" x2="0" y2="1" stroke="#555" stroke-width="0.08"/></pattern>'),
    "insul": ('<pattern id="insul" patternUnits="userSpaceOnUse" width="2" height="2">'
              '<rect width="2" height="2" fill="#fff"/>'
              '<path d="M0,1 Q0.5,0 1,1 T2,1" fill="none" stroke="#000" stroke-width="0.1"/></pattern>'),
    "earth": ('<pattern id="earth" patternUnits="userSpaceOnUse" width="4" height="4">'
              '<path d="M0,4 L4,0 M-1,1 L1,-1 M3,5 L5,3" stroke="#6b5a45" stroke-width="0.12"/>'
              '<path d="M0,0 L4,4" stroke="#6b5a45" stroke-width="0.06"/></pattern>'),
    "gravel": ('<pattern id="gravel" patternUnits="userSpaceOnUse" width="3" height="3">'
               '<rect width="3" height="3" fill="#efece6"/>'
               '<circle cx="0.6" cy="0.7" r="0.35" fill="none" stroke="#8a8478" stroke-width="0.07"/>'
               '<circle cx="2.1" cy="1.6" r="0.28" fill="none" stroke="#8a8478" stroke-width="0.07"/>'
               '<circle cx="1.1" cy="2.4" r="0.22" fill="none" stroke="#8a8478" stroke-width="0.07"/></pattern>'),
    "sand": ('<pattern id="sand" patternUnits="userSpaceOnUse" width="2" height="2">'
             '<circle cx="0.5" cy="0.5" r="0.08" fill="#777"/><circle cx="1.5" cy="1.3" r="0.08" fill="#777"/></pattern>'),
    "grass": ('<pattern id="grass" patternUnits="userSpaceOnUse" width="4" height="4">'
              '<rect width="4" height="4" fill="#dfe8cf"/>'
              '<path d="M1,2 l0.2,-0.6 l0.2,0.6 M3,3.6 l0.2,-0.6 l0.2,0.6 M2.6,1.2 l0.2,-0.6 l0.2,0.6" '
              'fill="none" stroke="#7d9a5a" stroke-width="0.1"/></pattern>'),
    "deck": ('<pattern id="deck" patternUnits="userSpaceOnUse" width="1.5" height="1.5">'
             '<rect width="1.5" height="1.5" fill="#efe1cc"/>'
             '<line x1="0" y1="0" x2="1.5" y2="0" stroke="#a88a64" stroke-width="0.08"/></pattern>'),
    "deckv": ('<pattern id="deckv" patternUnits="userSpaceOnUse" width="1.5" height="1.5">'
              '<rect width="1.5" height="1.5" fill="#efe1cc"/>'
              '<line x1="0" y1="0" x2="0" y2="1.5" stroke="#a88a64" stroke-width="0.08"/></pattern>'),
    "paving": ('<pattern id="paving" patternUnits="userSpaceOnUse" width="6" height="6">'
               '<rect width="6" height="6" fill="#ece8e0"/>'
               '<path d="M0,0 H6 M0,0 V6" stroke="#b5ada0" stroke-width="0.08"/></pattern>'),
    "tiles": ('<pattern id="tiles" patternUnits="userSpaceOnUse" width="12" height="6">'
              '<path d="M0,0 H12 M0,0 V6 M6,0 V6" stroke="#c9c2b6" stroke-width="0.07" fill="none"/></pattern>'),
    "water": ('<pattern id="water" patternUnits="userSpaceOnUse" width="6" height="3">'
              '<rect width="6" height="3" fill="#cfe6ee"/>'
              '<path d="M0,1.5 q1.5,-0.8 3,0 t3,0" fill="none" stroke="#7fb3c6" stroke-width="0.1"/></pattern>'),
    "stone": ('<pattern id="stone" patternUnits="userSpaceOnUse" width="1.1" height="1.1" patternTransform="rotate(45)">'
              '<rect width="1.1" height="1.1" fill="#fff"/>'
              '<line x1="0" y1="0" x2="0" y2="1.1" stroke="#000" stroke-width="0.1"/>'
              '<line x1="0.55" y1="0" x2="0.55" y2="1.1" stroke="#000" stroke-width="0.05"/></pattern>'),
    "wood": ('<pattern id="wood" patternUnits="userSpaceOnUse" width="2" height="0.8">'
             '<rect width="2" height="0.8" fill="#f3e6d2"/>'
             '<path d="M0,0.4 q0.5,-0.25 1,0 t1,0" fill="none" stroke="#8a6a44" stroke-width="0.06"/></pattern>'),
    "screed": ('<pattern id="screed" patternUnits="userSpaceOnUse" width="1.5" height="1.5">'
               '<rect width="1.5" height="1.5" fill="#fff"/>'
               '<circle cx="0.4" cy="0.4" r="0.1" fill="#000"/><circle cx="1.1" cy="1.0" r="0.06" fill="#000"/></pattern>'),
    "membrane": ('<pattern id="membrane" patternUnits="userSpaceOnUse" width="1" height="1">'
                 '<rect width="1" height="1" fill="#222"/></pattern>'),
    "plaster": ('<pattern id="plaster" patternUnits="userSpaceOnUse" width="1" height="1">'
                '<rect width="1" height="1" fill="#fff"/><circle cx="0.5" cy="0.5" r="0.06" fill="#444"/></pattern>'),
    "pv": ('<pattern id="pv" patternUnits="userSpaceOnUse" width="2" height="2">'
           '<rect width="2" height="2" fill="#4a5a72"/>'
           '<path d="M0,0 H2 M0,0 V2" stroke="#c8d0dc" stroke-width="0.08"/></pattern>'),
    "planting": ('<pattern id="planting" patternUnits="userSpaceOnUse" width="5" height="5">'
                 '<rect width="5" height="5" fill="#d3e0bf"/>'
                 '<circle cx="1.3" cy="1.4" r="0.9" fill="none" stroke="#6f8d4c" stroke-width="0.1"/>'
                 '<circle cx="3.6" cy="3.4" r="1.1" fill="none" stroke="#6f8d4c" stroke-width="0.1"/></pattern>'),
}

# DXF equivalents (pattern name, scale in model units for 1:100-ish)
DXF_HATCH = {
    "concrete": ("AR-CONC", 0.02), "rc": ("ANSI31", 0.4), "block": ("ANSI31", 0.25),
    "partition": ("ANSI37", 0.2), "insul": ("INSUL", 0.05), "earth": ("EARTH", 0.3),
    "gravel": ("GRAVEL", 0.2), "sand": ("AR-SAND", 0.02), "grass": ("GRASS", 0.2),
    "deck": ("LINE", 0.15), "deckv": ("LINE", 0.15), "paving": ("NET", 0.6), "tiles": ("NET", 0.6),
    "water": ("AR-RROOF", 0.05), "stone": ("ANSI32", 0.2), "wood": ("AR-PARQ1", 0.01),
    "screed": ("AR-SAND", 0.02), "membrane": ("SOLID", 1), "plaster": ("AR-SAND", 0.01),
    "pv": ("NET", 0.5), "planting": ("GRASS", 0.3),
}


class Sheet:
    """A paper-space SVG drawing in millimetres."""

    def __init__(self, w=841, h=594):
        self.w, self.h = w, h
        self.items: list[str] = []
        self.used_patterns: set[str] = set()
        self.defs_extra: list[str] = []
        self.clip_id = 0

    # ---- low level -------------------------------------------------------- #
    def add(self, s):
        self.items.append(s)

    def style(self, lw="s", color="#000", fill="none", dash=None, opacity=None, fop=None, cap="butt", join="miter"):
        w = LW.get(lw, lw) if isinstance(lw, str) else lw
        if isinstance(fill, str) and fill.startswith("pat:"):
            name = fill[4:]
            self.used_patterns.add(name)
            fill = f"url(#{name})"
        s = f'stroke="{color}" stroke-width="{w:.3f}" fill="{fill}" stroke-linecap="{cap}" stroke-linejoin="{join}"'
        if color == "none":
            s = f'stroke="none" fill="{fill}"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
        if opacity is not None:
            s += f' opacity="{opacity}"'
        if fop is not None:
            s += f' fill-opacity="{fop}"'
        return s

    def line(self, x1, y1, x2, y2, **kw):
        self.add(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" {self.style(**kw)}/>')

    def polyline(self, pts, closed=False, **kw):
        if len(pts) < 2:
            return
        d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + (" Z" if closed else "")
        self.add(f'<path d="{d}" {self.style(**kw)}/>')

    def path(self, d, **kw):
        self.add(f'<path d="{d}" {self.style(**kw)}/>')

    def rect(self, x, y, w, h, **kw):
        self.add(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" {self.style(**kw)}/>')

    def circle(self, cx, cy, r, **kw):
        self.add(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:.3f}" {self.style(**kw)}/>')

    def text(self, x, y, t, size=3.0, anchor="middle", weight=400, color="#000", rot=0, font=None,
             italic=False, spacing=None, opacity=None):
        """anchor: 'left' | 'middle' | 'right' (visual)."""
        t = str(t)
        rtl = bool(HEB.search(t))
        if anchor in ("left", "start"):
            ta = "end" if rtl else "start"
        elif anchor in ("right", "end"):
            ta = "start" if rtl else "end"
        else:
            ta = "middle"
        extra = ' direction="rtl"' if rtl else ""
        if rot:
            extra += f' transform="rotate({rot:.2f} {x:.3f} {y:.3f})"'
        if italic:
            extra += ' font-style="italic"'
        if spacing:
            extra += f' letter-spacing="{spacing}"'
        if opacity is not None:
            extra += f' opacity="{opacity}"'
        f = font or FONT
        self.add(f'<text x="{x:.3f}" y="{y:.3f}" font-family="{f}" font-size="{size:.2f}" '
                 f'font-weight="{weight}" fill="{color}" text-anchor="{ta}"{extra}>{esc(t)}</text>')

    def image(self, x, y, w, h, href, preserve="xMidYMid slice", clip_r=0):
        self.add(f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" href="{href}" '
                 f'preserveAspectRatio="{preserve}"/>')

    def group(self, inner: list[str], transform=None, clip=None):
        attr = ""
        if transform:
            attr += f' transform="{transform}"'
        if clip:
            attr += f' clip-path="url(#{clip})"'
        self.add(f"<g{attr}>" + "".join(inner) + "</g>")

    def clip_rect(self, x, y, w, h):
        self.clip_id += 1
        cid = f"clp{self.clip_id}"
        self.defs_extra.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>')
        return cid

    def begin_clip(self, x, y, w, h):
        cid = self.clip_rect(x, y, w, h)
        self.add(f'<g clip-path="url(#{cid})">')

    def end_group(self):
        self.add("</g>")

    def svg(self):
        defs = "".join(PATTERNS[p] for p in sorted(self.used_patterns)) + "".join(self.defs_extra)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'width="{self.w}mm" height="{self.h}mm" viewBox="0 0 {self.w} {self.h}">'
                f"<defs>{defs}</defs>" + "\n".join(self.items) + "</svg>")


class View:
    """Places model coordinates (m, y-up) onto a Sheet at a true scale.

    Optionally mirrors primitives into an ezdxf modelspace (in metres).
    """

    def __init__(self, sheet: Sheet, ox, oy, scale, dxf=None, dxf_offset=(0, 0)):
        self.sh = sheet
        self.ox, self.oy = ox, oy  # paper position of model (0,0)
        self.scale = scale
        self.k = 1000.0 / scale  # paper mm per model metre
        self.dxf = dxf
        self.dxo = dxf_offset

    def P(self, x, y):
        return self.ox + x * self.k, self.oy - y * self.k

    def pts(self, pts):
        return [self.P(x, y) for x, y in pts]

    # ---- DXF helpers ---------------------------------------------------- #
    def _d(self, pts):
        return [(x + self.dxo[0], y + self.dxo[1]) for x, y in pts]

    def _layer(self, lw, color, dash, layer):
        if layer:
            return layer
        if dash:
            return "A-HIDDEN"
        w = LW.get(lw, lw) if isinstance(lw, str) else lw
        if w >= 0.5:
            return "A-CUT"
        if w >= 0.25:
            return "A-MAIN"
        return "A-THIN"

    # ---- primitives ------------------------------------------------------- #
    def line(self, x1, y1, x2, y2, layer=None, **kw):
        a, b = self.P(x1, y1), self.P(x2, y2)
        self.sh.line(*a, *b, **kw)
        if self.dxf is not None:
            p = self._d([(x1, y1), (x2, y2)])
            self.dxf.add_line(p[0], p[1], dxfattribs={"layer": self._layer(kw.get("lw", "s"), None, kw.get("dash"), layer)})

    def polyline(self, pts, closed=False, layer=None, **kw):
        self.sh.polyline(self.pts(pts), closed=closed, **kw)
        if self.dxf is not None and len(pts) > 1:
            self.dxf.add_lwpolyline(self._d(pts), close=closed,
                                    dxfattribs={"layer": self._layer(kw.get("lw", "s"), None, kw.get("dash"), layer)})

    def polygon(self, pts, fill="none", layer=None, hatch_layer=None, **kw):
        """Closed polygon with optional fill ('pat:name' for hatch). Supports holes via list of rings."""
        rings = pts if pts and isinstance(pts[0][0], (list, tuple)) else [pts]
        d = ""
        for r in rings:
            pp = self.pts(r)
            d += "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pp) + " Z "
        st = self.sh.style(fill=fill, **kw)
        self.sh.add(f'<path d="{d}" fill-rule="evenodd" {st}/>')
        if self.dxf is not None:
            if isinstance(fill, str) and fill.startswith("pat:"):
                name = fill[4:]
                pat, sc = DXF_HATCH.get(name, ("ANSI31", 0.2))
                try:
                    h = self.dxf.add_hatch(dxfattribs={"layer": hatch_layer or "A-HATCH"})
                    if pat == "SOLID":
                        h.set_solid_fill(color=7)
                    else:
                        h.set_pattern_fill(pat, scale=sc * self.scale / 100.0)
                    for i, r in enumerate(rings):
                        h.paths.add_polyline_path(self._d(r), is_closed=True, flags=1 if i == 0 else 0)
                except Exception:
                    pass
            if kw.get("color", "#000") != "none":
                for r in rings:
                    self.dxf.add_lwpolyline(self._d(r), close=True,
                                            dxfattribs={"layer": self._layer(kw.get("lw", "s"), None, kw.get("dash"), layer)})

    def rect(self, x0, y0, x1, y1, **kw):
        self.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)

    def circle(self, cx, cy, r, layer=None, **kw):
        px, py = self.P(cx, cy)
        self.sh.circle(px, py, r * self.k, **kw)
        if self.dxf is not None:
            self.dxf.add_circle(self._d([(cx, cy)])[0], r,
                                dxfattribs={"layer": self._layer(kw.get("lw", "s"), None, kw.get("dash"), layer)})

    def arc(self, cx, cy, r, a0, a1, layer=None, **kw):
        """Arc from angle a0 to a1 (degrees, CCW, model space)."""
        n = max(8, int(abs(a1 - a0) / 5))
        pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
        self.sh.polyline(self.pts(pts), **kw)
        if self.dxf is not None:
            lo, hi = (a0, a1) if a1 >= a0 else (a1, a0)
            self.dxf.add_arc(self._d([(cx, cy)])[0], r, lo, hi,
                             dxfattribs={"layer": self._layer(kw.get("lw", "s"), None, kw.get("dash"), layer)})

    def text(self, x, y, t, size=2.5, layer="A-TEXT", **kw):
        px, py = self.P(x, y)
        self.sh.text(px, py, t, size=size, **kw)
        if self.dxf is not None:
            try:
                txt = self.dxf.add_text(str(t), height=size * self.scale / 1000.0, dxfattribs={"layer": layer})
                txt.set_placement(self._d([(x, y)])[0])
            except Exception:
                pass

    # ---- annotation helpers ----------------------------------------------- #
    def dim_chain(self, positions, offset, axis="x", at=0.0, lw="xs", size=2.0, tick=1.2, fmt=None,
                  ext_from=None, label_side=1):
        """Dimension chain.

        axis='x': horizontal chain at model y=at, through x positions.
        axis='y': vertical chain at model x=at, through y positions.
        Values written in cm (Israeli convention).
        ext_from: model coordinate where extension lines start (other axis).
        """
        pos = sorted(set(round(p, 4) for p in positions))
        if len(pos) < 2:
            return
        k = self.k
        if axis == "x":
            y = at
            self.line(pos[0], y, pos[-1], y, lw=lw, layer="A-DIMS")
            for p in pos:
                a = self.P(p, y)
                self.sh.line(a[0] - tick / 2, a[1] + tick / 2, a[0] + tick / 2, a[1] - tick / 2, lw="m")
                if ext_from is not None:
                    self.line(p, ext_from, p, y + (0.15 if y > ext_from else -0.15) * 100 / self.scale * 1.0,
                              lw="xxs", color="#444", layer="A-DIMS")
            for a, b in zip(pos, pos[1:]):
                v = (b - a) * 100
                s = fmt(v) if fmt else (f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}")
                px, py = self.P((a + b) / 2, y)
                if (b - a) * k < len(s) * size * 0.55:
                    py -= label_side * (size * 0.4 + 1.2)
                    py -= label_side * size * 0.9
                self.sh.text(px, py - label_side * 0.8 if label_side > 0 else py + size + 0.4, s, size=size)
        else:
            x = at
            self.line(x, pos[0], x, pos[-1], lw=lw, layer="A-DIMS")
            for p in pos:
                a = self.P(x, p)
                self.sh.line(a[0] - tick / 2, a[1] + tick / 2, a[0] + tick / 2, a[1] - tick / 2, lw="m")
                if ext_from is not None:
                    self.line(ext_from, p, x + (0.15 if x > ext_from else -0.15) * 100 / self.scale, p,
                              lw="xxs", color="#444", layer="A-DIMS")
            for a, b in zip(pos, pos[1:]):
                v = (b - a) * 100
                s = fmt(v) if fmt else (f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}")
                px, py = self.P(x, (a + b) / 2)
                tx = px - 0.8
                if (b - a) * k < len(s) * size * 0.55:
                    tx -= size * 1.1
                self.sh.add(f'<text x="{tx:.3f}" y="{py:.3f}" font-family="{FONT}" font-size="{size}" '
                            f'text-anchor="middle" transform="rotate(-90 {tx:.3f} {py:.3f})">{s}</text>')

    def level_mark(self, x, y, value, size=2.2, side="right", plan=False):
        """Elevation level marker (triangle + value), value in metres."""
        px, py = self.P(x, y)
        s = f"{value:+.2f}" if abs(value) > 0.0001 else "±0.00"
        if plan:
            # plan level: circle-cross symbol
            r = 1.4
            self.sh.circle(px, py, r, lw="xs")
            self.sh.path(f"M{px - r},{py} A{r},{r} 0 0 1 {px + r},{py} L{px},{py} Z", lw="xs", fill="#000")
            self.sh.path(f"M{px},{py - r} A{r},{r} 0 0 1 {px},{py + r} ", lw="xs")
            self.sh.text(px + (r + 0.8) * (1 if side == "right" else -1), py - r - 0.3, s, size=size,
                         anchor="left" if side == "right" else "right")
            return
        t = 1.6
        self.sh.path(f"M{px},{py} L{px - t},{py - t * 1.4} L{px + t},{py - t * 1.4} Z", lw="xs", fill="#000")
        dx = 2.4 if side == "right" else -2.4
        self.sh.line(px - (t + 0.5), py, px + dx * 5, py, lw="xxs")
        self.sh.text(px + dx, py - t * 1.6, s, size=size, anchor="left" if side == "right" else "right")


def north_arrow(sh: Sheet, x, y, r=9, rot=0):
    g = []
    g.append(f'<circle cx="0" cy="0" r="{r}" fill="none" stroke="#000" stroke-width="0.25"/>')
    g.append(f'<path d="M0,{-r * 1.25} L{r * 0.38},{r * 0.55} L0,{r * 0.25} Z" fill="#000"/>')
    g.append(f'<path d="M0,{-r * 1.25} L{-r * 0.38},{r * 0.55} L0,{r * 0.25} Z" fill="#fff" stroke="#000" stroke-width="0.25"/>')
    g.append(f'<text x="0" y="{-r * 1.4}" font-family="{FONT}" font-size="{r * 0.55}" font-weight="700" text-anchor="middle">N</text>')
    sh.add(f'<g transform="translate({x},{y}) rotate({rot})">' + "".join(g) + "</g>")


def drawing_title(sh: Sheet, x, y, title, scale_txt, width=95, size=7.5):
    """Underlined drawing title in the Israeli convention: title + scale, right aligned at x."""
    sh.text(x, y, title, size=size, anchor="right", weight=700)
    sh.line(x - width, y + 2.0, x, y + 2.0, lw="l")
    sh.line(x - width, y + 3.0, x, y + 3.0, lw="xs")
    if scale_txt:
        sh.text(x, y + 3.0 + size * 0.95, scale_txt, size=size * 0.7, anchor="right", weight=500)


def section_marker(v: View, x1, y1, x2, y2, label, look=1, size=2.8, r=3.0):
    """Section cut line (x1,y1)->(x2,y2). look=+1: viewing direction = left normal of the line on paper."""
    a, b = v.P(x1, y1), v.P(x2, y2)
    sh = v.sh
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = uy * look, -ux * look   # paper normal toward viewing direction
    sh.line(*a, *b, lw="xs", dash="7 1.5 1.2 1.5")
    for p, s in ((a, 1), (b, -1)):
        sh.line(p[0], p[1], p[0] + ux * s * 8, p[1] + uy * s * 8, lw="xl")
        cx, cy = p[0] - ux * s * (r + 1.0), p[1] - uy * s * (r + 1.0)
        # arrow pointing to the viewing side
        tx, ty = cx + nx * r * 2.1, cy + ny * r * 2.1
        sh.path(f"M{tx:.3f},{ty:.3f} L{cx + ux * r * 0.9:.3f},{cy + uy * r * 0.9:.3f} "
                f"L{cx - ux * r * 0.9:.3f},{cy - uy * r * 0.9:.3f} Z", lw="xs", fill="#000")
        sh.circle(cx, cy, r, lw="m", fill="#fff")
        sh.text(cx, cy + size * 0.36, label, size=size, weight=700)


def elevation_marker(v: View, x, y, label, direction, r=3.2):
    """Elevation view marker; direction = angle (deg, paper, 0=right) toward which the viewer looks."""
    px, py = v.P(x, y)
    sh = v.sh
    sh.circle(px, py, r, lw="m", fill="#fff")
    a = math.radians(direction)
    tx, ty = px + math.cos(a) * r * 1.8, py + math.sin(a) * r * 1.8
    a1, a2 = a + math.radians(90), a - math.radians(90)
    sh.path(f"M{tx},{ty} L{px + math.cos(a1) * r},{py + math.sin(a1) * r} L{px + math.cos(a2) * r},{py + math.sin(a2) * r} Z",
            lw="xs", fill="#000")
    sh.circle(px, py, r, lw="m", fill="#fff")
    sh.text(px, py + 1.0, label, size=2.6, weight=700)


def grid_bubble(v: View, x, y, label, r=3.0):
    px, py = v.P(x, y)
    v.sh.circle(px, py, r, lw="s", fill="#fff")
    v.sh.text(px, py + 1.05, label, size=3.0, weight=500)


def scale_bar(sh: Sheet, x, y, scale, length_m=5, h=1.6):
    k = 1000.0 / scale
    for i in range(length_m):
        sh.rect(x + i * k, y, k, h, lw="xs", fill="#000" if i % 2 == 0 else "#fff")
    for i in range(length_m + 1):
        sh.text(x + i * k, y + h + 2.6, f"{i}", size=2.0)
    sh.text(x + length_m * k + 3, y + h + 0.3, "מ'", size=2.2, anchor="left")


def new_dxf():
    import ezdxf
    doc = ezdxf.new("R2018", setup=True)
    doc.units = 6  # metres
    layers = {
        "A-CUT": (7, 50), "A-MAIN": (7, 35), "A-THIN": (8, 18), "A-HIDDEN": (8, 18),
        "A-HATCH": (8, 9), "A-TEXT": (7, 18), "A-DIMS": (1, 13), "A-FURN": (9, 13),
        "A-GRID": (1, 13), "A-SITE": (3, 18),
    }
    for name, (c, lw) in layers.items():
        if name not in doc.layers:
            l = doc.layers.add(name)
            l.color = c
            l.dxf.lineweight = lw
    doc.layers.get("A-HIDDEN").dxf.linetype = "DASHED"
    return doc
