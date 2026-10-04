"""2-D furniture & sanitary symbols for plans (model metres).

Orientation convention: Furn.rot = direction the FRONT faces (0=E, 90=N, 180=W, 270=S).
Local frame: u along the front edge (0..W), v from front (0) to back (D).
"""
from __future__ import annotations

import math

STY = dict(lw="xs", color="#3a3a3a")
STY_L = dict(lw="xxs", color="#6a6a6a")


class Local:
    def __init__(self, f):
        self.f = f
        x0, y0, x1, y1 = f.x, f.y, f.x + f.w, f.y + f.d
        self.box = (x0, y0, x1, y1)
        r = f.rot % 360
        self.r = r
        if r in (270, 90):
            self.W, self.D = f.w, f.d
        else:
            self.W, self.D = f.d, f.w

    def P(self, u, v):
        x0, y0, x1, y1 = self.box
        r = self.r
        if r == 270:   # front south
            return x0 + u, y0 + v
        if r == 90:    # front north
            return x1 - u, y1 - v
        if r == 0:     # front east
            return x1 - v, y0 + u
        return x0 + v, y1 - u  # 180 front west


def _poly(v, L, pts, closed=True, fill="none", **kw):
    st = dict(STY)
    st.update(kw)
    v.polygon([L.P(u, w) for u, w in pts], fill=fill, layer="A-FURN", **st) if closed else \
        v.polyline([L.P(u, w) for u, w in pts], layer="A-FURN", **st)


def _rect(v, L, u0, v0, u1, v1, **kw):
    _poly(v, L, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], **kw)


def _rrect(v, L, u0, v0, u1, v1, r, **kw):
    pts = []
    for (cu, cv, a0) in [(u1 - r, v0 + r, 270), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)]:
        for i in range(7):
            a = math.radians(a0 + i * 15)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    _poly(v, L, pts, **kw)


def _ellipse(v, L, cu, cv, ru, rv, **kw):
    pts = [(cu + ru * math.cos(math.radians(a)), cv + rv * math.sin(math.radians(a))) for a in range(0, 360, 15)]
    _poly(v, L, pts, **kw)


def _circle(v, L, cu, cv, r, **kw):
    _ellipse(v, L, cu, cv, r, r, **kw)


def chairs_row(v, L, u0, u1, vv, n, facing_back=True):
    if n <= 0:
        return
    step = (u1 - u0) / n
    for i in range(n):
        cu = u0 + step * (i + 0.5)
        _rrect(v, L, cu - 0.22, vv - 0.21, cu + 0.22, vv + 0.21, 0.06, fill="#fff")
        bv = vv + (0.21 if facing_back else -0.21)
        _poly(v, L, [(cu - 0.2, bv), (cu + 0.2, bv)], closed=False, lw="s")


def draw(v, f, detail=100):
    L = Local(f)
    W, D = L.W, L.D
    k = f.kind
    fill = "#fff"
    if k in ("bed_k", "bed_q", "bed_s"):
        _rect(v, L, 0, 0, W, D, fill=fill)
        _rect(v, L, 0, D - 0.08, W, D, fill="#e9e3d8")
        n = 1 if k == "bed_s" else 2
        pw = (W - 0.3) / n
        for i in range(n):
            _rrect(v, L, 0.15 + i * pw + 0.03, D - 0.55, 0.15 + (i + 1) * pw - 0.03, D - 0.15, 0.07, fill=fill, **STY_L)
        _poly(v, L, [(0, D * 0.62), (W, D * 0.62)], closed=False, **STY_L)
        _poly(v, L, [(0, D * 0.62), (W * 0.25, D * 0.5), (W, D * 0.62)], closed=False, **STY_L)
    elif k == "sofa":
        _rrect(v, L, 0, 0, W, D, 0.06, fill=fill)
        _rect(v, L, 0.18, D - 0.22, W - 0.18, D, **STY_L)
        _rect(v, L, 0, 0, 0.18, D, **STY_L)
        _rect(v, L, W - 0.18, 0, W, D, **STY_L)
        n = max(2, round((W - 0.36) / 0.9))
        for i in range(1, n):
            u = 0.18 + (W - 0.36) * i / n
            _poly(v, L, [(u, 0.05), (u, D - 0.22)], closed=False, **STY_L)
    elif k == "sofa_l":
        dd = 1.0
        _poly(v, L, [(0, 0), (dd, 0), (dd, D - dd), (W, D - dd), (W, D), (0, D)], fill=fill)
        _poly(v, L, [(0.22, 0.05), (0.22, D - 0.22), (W - 0.05, D - 0.22)], closed=False, **STY_L)
        for u in (W * 0.4, W * 0.7):
            _poly(v, L, [(u, D - dd + 0.05), (u, D - 0.22)], closed=False, **STY_L)
        _poly(v, L, [(0.25, D - dd), (dd, D - dd)], closed=False, **STY_L)
    elif k == "armchair":
        _rrect(v, L, 0, 0, W, D, 0.08, fill=fill)
        _rect(v, L, 0.12, D - 0.2, W - 0.12, D, **STY_L)
        _rect(v, L, 0, 0.05, 0.12, D, **STY_L)
        _rect(v, L, W - 0.12, 0.05, W, D, **STY_L)
    elif k in ("coffee", "nightstand", "bench", "tvunit", "island_s"):
        _rrect(v, L, 0, 0, W, D, 0.04, fill=fill)
        if k == "nightstand":
            _circle(v, L, W / 2, D / 2, min(W, D) * 0.25, **STY_L)
    elif k == "rug":
        _rect(v, L, 0, 0, W, D, lw="xxs", color="#999", dash="1.2 0.8")
    elif k == "table_rect":
        _rect(v, L, 0, 0, W, D, fill=fill)
        n = max(1, int(round((W - 0.2) / 0.68)))
        chairs_row(v, L, 0.1, W - 0.1, -0.32, n, facing_back=False)
        chairs_row(v, L, 0.1, W - 0.1, D + 0.32, n, facing_back=True)
        if f.label and int(f.label) > 2 * n:
            for uu in (-0.32, W + 0.32):
                _rrect(v, L, uu - 0.21, D / 2 - 0.22, uu + 0.21, D / 2 + 0.22, 0.06, fill="#fff")
    elif k == "table_round":
        _circle(v, L, W / 2, D / 2, W / 2, fill=fill)
        for a in range(0, 360, 90):
            cu = W / 2 + (W / 2 + 0.3) * math.cos(math.radians(a + 45))
            cv = D / 2 + (W / 2 + 0.3) * math.sin(math.radians(a + 45))
            _circle(v, L, cu, cv, 0.21, fill="#fff")
    elif k == "island":
        _rect(v, L, 0, 0, W, D, fill="#f2eee6")
        _rect(v, L, 0.05, 0.05, W - 0.05, D - 0.05, **STY_L)
        # sink + hob
        _rrect(v, L, W * 0.5 - 0.4, D - 0.5, W * 0.5 + 0.4, D - 0.12, 0.04, **STY_L)
        _circle(v, L, W * 0.5, D - 0.06, 0.025, **STY_L)
        for i in range(4):
            stool_u = W * (i + 0.5) / 4
            _circle(v, L, stool_u, -0.3, 0.18, fill="#fff", **STY_L)
    elif k in ("counter", "counter_l"):
        _rect(v, L, 0, 0, W, D, fill="#f2eee6")
        _poly(v, L, [(0, 0.05), (W, 0.05)], closed=False, lw="xxs", color="#888", dash="1 0.6")
        if k == "counter_l" or W > 2.5:
            # sink & hob
            _rrect(v, L, W * 0.3 - 0.35, 0.1, W * 0.3 + 0.35, D - 0.1, 0.04, **STY_L)
            for (du, dv) in [(-0.15, -0.12), (0.15, -0.12), (-0.15, 0.12), (0.15, 0.12)]:
                _circle(v, L, W * 0.72 + du, D / 2 + dv, 0.08, **STY_L)
    elif k == "fridge":
        _rect(v, L, 0, 0, W, D, fill=fill)
        _poly(v, L, [(0, 0), (W, D)], closed=False, **STY_L)
        _poly(v, L, [(W, 0), (0, D)], closed=False, **STY_L)
    elif k in ("closet", "rack"):
        _rect(v, L, 0, 0, W, D, fill=fill)
        _poly(v, L, [(0.03, D / 2), (W - 0.03, D / 2)], closed=False, **STY_L)
        n = max(1, round(W / 0.5))
        for i in range(n + 1):
            u = W * i / n
            _poly(v, L, [(u, 0), (u, 0.06)], closed=False, **STY_L)
        for i in range(int(W / 0.12)):
            u = 0.06 + i * 0.12
            _poly(v, L, [(u, D / 2 - 0.12), (u + 0.02, D / 2 + 0.12)], closed=False, lw="xxs", color="#999")
    elif k == "wc":
        _rect(v, L, 0, D - 0.18, W, D, fill=fill)
        _ellipse(v, L, W / 2, (D - 0.18) / 2 + 0.02, W * 0.45, (D - 0.18) / 2 + 0.02, fill=fill)
    elif k == "basin":
        _rect(v, L, 0, 0, W, D, fill=fill)
        _ellipse(v, L, W / 2, D / 2, W * 0.35, D * 0.3, **STY_L)
    elif k in ("vanity", "vanity2"):
        _rect(v, L, 0, 0, W, D, fill="#f2eee6")
        n = 2 if (k == "vanity2" or W > 1.5) else 1
        for i in range(n):
            cu = W * (i + 0.5) / n
            _ellipse(v, L, cu, D * 0.45, min(0.25, W / n * 0.3), D * 0.28, **STY_L)
    elif k == "tub":
        _rrect(v, L, 0, 0, W, D, 0.12, fill=fill)
        _rrect(v, L, 0.07, 0.07, W - 0.07, D - 0.07, 0.25, **STY_L)
        _circle(v, L, W / 2, D - 0.25, 0.03, **STY_L)
    elif k == "shower":
        _rect(v, L, 0, 0, W, D, lw="xxs", color="#777")
        _poly(v, L, [(0, 0), (W, D)], closed=False, lw="xxs", color="#aaa")
        _poly(v, L, [(W, 0), (0, D)], closed=False, lw="xxs", color="#aaa")
        _circle(v, L, W / 2, D / 2, 0.05, **STY_L)
    elif k == "desk":
        _rect(v, L, 0, 0, W, D, fill=fill)
        _rrect(v, L, W / 2 - 0.25, -0.55, W / 2 + 0.25, -0.08, 0.1, fill="#fff", **STY_L)
    elif k == "fireplace":
        _rect(v, L, 0, 0, W, D, fill="#e9dcc4")
        _rect(v, L, 0.2, 0.06, W - 0.2, D * 0.5, **STY_L)
        pts = [(0.3 + i * (W - 0.6) / 10, 0.12 + (0.12 if i % 2 else 0)) for i in range(11)]
        _poly(v, L, pts, closed=False, lw="xxs", color="#a25b2a")
    elif k == "piano":
        pts = [(0, D)]
        for i in range(13):
            t = i / 12
            pts.append((W * (1 - 0.5 * (1 - math.cos(math.pi * t))) * 1.0 if False else W * (1 - t * 0.0), 0))
        _poly(v, L, [(0, D), (W, D), (W, D * 0.45), (W * 0.75, D * 0.1), (W * 0.35, 0), (0, D * 0.35)], fill=fill)
        _rect(v, L, 0.05, D - 0.18, W - 0.05, D - 0.03, **STY_L)
    elif k == "lounger":
        _rrect(v, L, 0, 0, W, D, 0.06, fill=fill)
        _poly(v, L, [(0, D * 0.7), (W, D * 0.7)], closed=False, **STY_L)
    elif k == "recliner_row":
        n = max(2, int(W / 0.9))
        sw = W / n
        for i in range(n):
            _rrect(v, L, i * sw + 0.04, 0, (i + 1) * sw - 0.04, D, 0.08, fill=fill)
            _rect(v, L, i * sw + 0.12, D - 0.25, (i + 1) * sw - 0.12, D - 0.05, **STY_L)
    elif k == "bar":
        _rect(v, L, 0, 0, W, D, fill="#f2eee6")
        for i in range(4):
            _circle(v, L, W * (i + 0.5) / 4, -0.32, 0.18, fill="#fff", **STY_L)
    elif k == "pool_table":
        _rect(v, L, 0, 0, W, D, fill=fill)
        _rect(v, L, 0.12, 0.12, W - 0.12, D - 0.12, fill="#e6efe0", **STY_L)
    elif k == "sauna":
        _rect(v, L, 0, 0, W, D, fill="#f3e6d2")
        for vv in (D * 0.35, D * 0.7):
            _poly(v, L, [(0.05, vv), (W - 0.05, vv)], closed=False, **STY_L)
    elif k in ("gym", "mat", "tech"):
        _rrect(v, L, 0, 0, W, D, 0.05, fill=fill)
        if k == "gym":
            _rect(v, L, 0.1, 0.15, W - 0.4, D - 0.15, **STY_L)
    elif k == "screen":
        _rect(v, L, 0, 0, W, D, fill="#333")
    else:
        _rect(v, L, 0, 0, W, D, fill=fill)
