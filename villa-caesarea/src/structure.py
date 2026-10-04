"""Structural schemes (סכמות סטטיות) 1:100 – derived from the model's bearing elements."""
from __future__ import annotations

from shapely.geometry import box as sbox, Polygon
from shapely.ops import unary_union

import model as M
from draw import View, drawing_title, north_arrow, grid_bubble, new_dxf
from plans import wall_layers, polys, ring_pts, DXF_DOCS, save_dxf

# beams per slab: (name, x0, y0, x1, y1, width, depth_cm, kind)
BEAMS = {
    "G": [  # GF slab (basement ceiling)
        ("ק-1", 13.30, 21.15, 21.40, 21.15, 0.30, 60, "down"),        # over basement glazing to patio
        ("ק-2", 12.85, 25.15, 19.06, 25.15, 0.30, 50, "down"),
    ],
    "U": [  # UF slab (GF ceiling)
        ("ק-3", 6.15, 21.15, 24.85, 21.15, 0.30, 60, "down"),         # south façade – carries UF walls
        ("ק-4", 12.85, 25.15, 19.06, 25.15, 0.30, 60, "down"),        # grid 3 – carries UF façade wall
        ("ק-5", 19.06, 21.15, 19.06, 25.15, 0.30, 50, "down"),
        ("ק-7", 6.15, 27.11, 12.85, 27.11, 0.30, 80, "down"),        # transfer beam under the ממ"ד south wall
        ("ק-8", 11.05, 27.11, 11.05, 31.85, 0.30, 70, "down"),       # transfer beam under the ממ"ד east wall
    ],
    "R": [  # roof slab (UF ceiling) – storey-high wall beams
        ("קק-1", 6.15, 16.15, 6.15, 31.85, 0.20, 340, "wall"),       # west wall-beam (cantilever 5.0 m)
        ("קק-2", 12.85, 16.15, 12.85, 25.15, 0.20, 340, "wall"),     # east wall-beam of the cantilever
        ("ק-6", 6.15, 16.15, 12.85, 16.15, 0.30, 60, "up"),           # loggia frame head beam (upstand)
        ("ק-9", 12.90, 26.60, 17.80, 26.60, 0.30, 50, "down"),       # carries the roof-exit south wall
    ],
    "RX": [],
}
SLAB_TAGS = {
    "G": [(9.6, 28.5, 'ת. 30 – שתי כיוונים'), (16.0, 23.4, "ת. 30"), (22.0, 23.2, "ת. 30")],
    "U": [(9.6, 26.8, 'ת. 30 – שתי כיוונים'), (16.0, 23.0, "ת. 30"), (22.0, 28.0, "ת. 30"), (9.6, 18.4, "זיז 5.00 מ' – ת. 30")],
    "R": [(9.6, 21.0, "ת. 30"), (19.0, 28.0, "ת. 30"), (15.3, 29.3, "")],
    "RX": [(15.3, 29.5, "ת. 25")],
}
TITLES = {"F": "תכנית יסודות – רפסודה", "G": "סכמה סטטית תקרה ±0.00", "U": "סכמה סטטית תקרה +3.60",
          "R": "סכמה סטטית תקרה +7.00", "RX": "סכמה סטטית תקרה +9.80"}
BELOW = {"G": "B", "U": "G", "R": "U", "RX": "R"}


def bearing(level):
    """bearing walls of the storey below a slab."""
    out = []
    for w in M.WALLS:
        if w.level != level:
            continue
        if w.kind in ("int", "glass", "parapet"):
            if not (w.kind == "int" and w.t >= 0.20):
                continue
        out.append(w)
    return out


def slab_poly(level):
    for s in M.SLABS:
        if level == "G" and s.kind == "slab" and abs(s.top - M.slab_top("G")) < 1e-6:
            return s
        if level == "U" and s.kind == "slab" and abs(s.top - M.slab_top("U")) < 1e-6:
            return s
        if level == "R" and s.kind == "roof" and abs(s.top - M.slab_top("R")) < 1e-6:
            return s
        if level == "RX" and s.kind == "roof" and s.top > 8:
            return s
    return None


def scheme(v: View, level):
    s = slab_poly(level)
    if s:
        poly = unary_union([sbox(*r) for r in s.rects])
        if s.holes:
            poly = poly.difference(unary_union([sbox(*h) for h in s.holes]))
        for p in polys(poly):
            v.polygon(ring_pts(p), fill="#f6f2ea", lw="m")
        for h in s.holes:
            v.rect(*h, fill="#fff", lw="s")
            v.line(h[0], h[1], h[2], h[3], lw="xxs")
            v.line(h[0], h[3], h[2], h[1], lw="xxs")
    lvl_below = BELOW[level]
    for w in bearing(lvl_below):
        for g, mat in wall_layers(w):
            if mat in ("stone", "plaster", "membrane"):
                continue
            # bearing walls drawn without openings (lintels) – use full rectangle for clarity
            for p in polys(g):
                v.polygon(ring_pts(p), fill="#3a3a3a" if mat == "rc" else "pat:block", lw="xs")
    for c in M.COLS:
        lv_z = {"G": M.slab_bot("G"), "U": M.slab_bot("U")}.get(level)
        if lv_z is not None and abs(c.z1 - lv_z) < 0.01:
            v.rect(c.x - c.w / 2, c.y - c.d / 2, c.x + c.w / 2, c.y + c.d / 2, fill="#000", lw="xs")
            v.text(c.x + 0.45, c.y + 0.35, "ע 30/30", size=1.7, anchor="left")
    for (name, x0, y0, x1, y1, wd, dp, kind) in BEAMS.get(level, []):
        if abs(y0 - y1) < 1e-6:
            r = (x0, y0 - wd / 2, x1, y0 + wd / 2)
            tx, ty, rot = (x0 + x1) / 2, y0 + wd / 2 + 0.25, 0
        else:
            r = (x0 - wd / 2, y0, x0 + wd / 2, y1)
            tx, ty, rot = x0 + wd / 2 + 0.35, (y0 + y1) / 2, -90
        col = "#b03030" if kind == "wall" else "#000"
        v.rect(*r, fill="none" if kind != "wall" else "#f1c9c9", lw="s", color=col, dash=None if kind == "up" else "2.2 1")
        lbl = f"{name} {int(wd * 100)}/{dp}" + (" קורה-קיר בגובה קומה" if kind == "wall" else (" עליונה" if kind == "up" else ""))
        v.text(tx, ty, lbl, size=1.8, rot=rot, color=col, weight=600)
    for (tx, ty, t) in SLAB_TAGS.get(level, []):
        if not t:
            continue
        px, py = v.P(tx, ty)
        v.sh.circle(px, py - 0.9, 0.0001)
        # two-way span cross
        v.line(tx - 0.9, ty, tx + 0.9, ty, lw="xs")
        v.line(tx, ty - 0.9, tx, ty + 0.9, lw="xs")
        for (dx, dy) in [(-0.9, 0), (0.9, 0), (0, -0.9), (0, 0.9)]:
            v.circle(tx + dx, ty + dy, 0.06, lw="xxs", fill="#000")
        v.text(tx + 1.1, ty + 0.25, t, size=1.9, anchor="left", weight=600)
    # grid
    for n, x in M.GRID_X:
        v.line(x, 14.2, x, 33.0, lw="xxs", color="#b03030", dash="5 1 1 1")
        grid_bubble(v, x, 13.3, n, r=2.3)
    for n, y in M.GRID_Y:
        v.line(4.9, y, 26.0, y, lw="xxs", color="#b03030", dash="5 1 1 1")
        grid_bubble(v, 4.0, y, n, r=2.3)
    v.dim_chain([g[1] for g in M.GRID_X], 0, axis="x", at=33.6, size=1.8, lw="xxs")
    v.dim_chain([g[1] for g in M.GRID_Y], 0, axis="y", at=26.6, size=1.8, lw="xxs")


def foundations(v: View):
    raft = next(s for s in M.SLABS if s.kind == "raft")
    for r in raft.rects:
        v.rect(*r, fill="#ece7dd", lw="m")
    for w in M.WALLS:
        if w.level == "B" and w.kind in ("retain", "shaft", "rc", "mamad"):
            for g, mat in wall_layers(w):
                if mat == "membrane":
                    continue
                for p in polys(g):
                    v.polygon(ring_pts(p), fill="#3a3a3a", lw="xs")
    for c in M.COLS:
        if abs(c.z0 - M.slab_top("B")) < 0.01:
            v.rect(c.x - c.w / 2, c.y - c.d / 2, c.x + c.w / 2, c.y + c.d / 2, fill="#000", lw="xs")
    # lift pit
    v.rect(M.LIFT["x0"], M.LIFT["y0"], M.LIFT["x1"], M.LIFT["y1"], fill="#fff", lw="s", dash="2 1")
    v.text((M.LIFT["x0"] + M.LIFT["x1"]) / 2, M.LIFT["y0"] - 0.5, "בור מעלית -4.70", size=1.7)
    # patio slab & pool shell (separate)
    v.rect(M.PATIO[0] - 0.3, M.PATIO[1] - 0.3, M.PATIO[2] + 0.3, M.Y_S_G, fill="#ece7dd", lw="s")
    v.text(17.75, 18.6, "רפסודת פטיו 35", size=1.9, weight=600)
    v.text(15.5, 25.5, 'רפסודה ב"מ ת. 50 על בטון רזה 5', size=2.1, weight=700)
    v.text(15.5, 24.6, "קירות תמך ב\"מ 30 + איטום ביטומני 2×4 מ\"מ", size=1.9)
    v.text(15.5, 23.8, "תחתית רפסודה -4.10 | יש לבצע דיפון זמני לפי יועץ קרקע", size=1.8, color="#444")
    for n, x in M.GRID_X:
        v.line(x, 14.2, x, 33.0, lw="xxs", color="#b03030", dash="5 1 1 1")
        grid_bubble(v, x, 13.3, n, r=2.3)
    for n, y in M.GRID_Y:
        v.line(4.9, y, 26.0, y, lw="xxs", color="#b03030", dash="5 1 1 1")
        grid_bubble(v, 4.0, y, n, r=2.3)


def sheet_structure(sh, box):
    x, y, w, h = box
    sc = 100
    k = 1000 / sc
    cells = [("G", 0.83, 0.30), ("U", 0.50, 0.30), ("R", 0.17, 0.30), ("F", 0.83, 0.78), ("RX", 0.50, 0.78)]
    for lvl, fx, fy in cells:
        cx, cy = x + w * fx, y + h * fy
        ox = cx - 15.3 * k
        oy = cy + 24.5 * k
        doc = DXF_DOCS.setdefault(f"struct_{lvl}", new_dxf())
        v = View(sh, ox, oy, sc, dxf=doc.modelspace())
        if lvl == "F":
            foundations(v)
        else:
            scheme(v, lvl)
        drawing_title(sh, cx + 55, cy + 120, TITLES[lvl], 'קנ"מ 1:100', width=78, size=5.5)
        save_dxf(f"struct_{lvl}")
    # legend + notes in the free cell
    lx = x + w * 0.33
    ly = y + h * 0.58
    sh.text(lx, ly, "מקרא:", size=3.4, anchor="right", weight=700)
    items = [("#3a3a3a", "קיר בטון מזוין נושא (קירות תמך, פיר מעלית, ממ\"ד, קיר גז\"ק)"),
             ("pat:block", "קיר בלוק נושא 20"),
             ("#000", "עמוד ב\"מ 30/30"),
             ("dash", "קורה תחתונה (ק-xx רוחב/גובה ס\"מ)"),
             ("#f1c9c9", "קורה-קיר בגובה קומה – נושאת את הזיז"),
             ("#f6f2ea", "תקרה ב\"מ מלאה ת. 30")]
    for i, (f, t) in enumerate(items):
        yy = ly + 7 + i * 7
        if f == "dash":
            sh.rect(lx - 12, yy - 3.5, 10, 4, lw="s", dash="2 1")
        elif f.startswith("pat:"):
            sh.used_patterns.add(f[4:])
            sh.rect(lx - 12, yy - 3.5, 10, 4, lw="xs", fill=f"url(#{f[4:]})")
        else:
            sh.rect(lx - 12, yy - 3.5, 10, 4, lw="xs", fill=f)
        sh.text(lx - 15, yy, t, size=2.6, anchor="right")
    notes = ["עקרונות המערכת הקונסטרוקטיבית:",
             "• שלד בטון מזוין יצוק באתר: רפסודה 50, קירות תמך 30, תקרות מלאות 30.",
             "• הזיז הדרומי (5.00 מ') נישא ע\"י שני קירות-קורה בגובה קומה (קק-1, קק-2)",
             "  הפועלים כקורות בגובה 3.40 מ' וממשיכים 10.7 מ' לאחור עד ציר 4 – יחס עוגן 1:2.",
             "• קיר הליבה (פיר מעלית + קיר האח) משמש קיר גזירה לכוחות אופקיים (ת\"י 413).",
             "• כיסוי בטון מוגבר 4–5 ס\"מ ובטון ב-40 לסביבה ימית (ת\"י 466).",
             "• כל המידות והזיונים לפי חישוב סטטי של מהנדס הקונסטרוקציה."]
    for i, t in enumerate(notes):
        sh.text(lx, ly + 58 + i * 5.2, t, size=2.6 if i else 3.0, anchor="right", weight=700 if i == 0 else 400)
    north_arrow(sh, x + w - 16, y + 18, r=7)
