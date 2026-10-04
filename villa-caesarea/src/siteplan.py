"""Site plan (1:250) with area/rights tables, and development plan (1:100)."""
from __future__ import annotations

import math

from shapely.geometry import box as sbox, Polygon
from shapely.ops import unary_union

import model as M
import plans as PL
from draw import View, drawing_title, north_arrow, scale_bar, new_dxf
from plans import DXF_DOCS, save_dxf, polys, ring_pts

L = M.LOT


# ----------------------------------------------------------------------------- areas
def areas():
    G = Polygon(M.OUTLINES["G"]).area
    U = Polygon(M.OUTLINES["U"]).area
    RX = Polygon(M.OUTLINES["R"]).area
    B = Polygon(M.OUTLINES["B"]).area
    stair = (M.ST["x1"] - M.ST["x0"] + 0.2) * (M.ST["yn"] - M.ST["ys"] + 0.1) + \
            (M.LIFT["x1"] - M.LIFT["x0"]) * (M.LIFT["y1"] - M.LIFT["y0"])
    mamad_room = next(r for r in M.ROOMS if r.name.startswith('ממ"ד'))
    mx0, my0, mx1, my1 = mamad_room.rects[0]
    mamad_gross = (mx1 - mx0 + 0.45) * (my1 - my0 + 0.45)
    mamad_service = min(12.5, mamad_gross)
    cover = unary_union([Polygon(M.OUTLINES["G"]), Polygon(M.OUTLINES["U"])]).area
    lot = (L["x1"] - L["x0"]) * (L["y1"] - L["y0"])
    service = dict(stairs=2 * stair, mamad=mamad_service, roofexit=RX)
    main_g = G - stair
    main_u = U - stair - mamad_service
    soft = sum((r[2] - r[0]) * (r[3] - r[1]) for r in M.SITE["lawn"] + M.SITE["planting"])
    P = M.POOL
    return dict(lot=lot, G=G, U=U, RX=RX, B=B, stair=stair, mamad_gross=mamad_gross, mamad_service=mamad_service,
                main_g=main_g, main_u=main_u, main=main_g + main_u, service=sum(service.values()),
                service_d=service, cover=cover, soft=soft, pool=(P["x1"] - P["x0"]) * (P["y1"] - P["y0"]))


def table(sh, x, y, cols, rows, widths, title=None, row_h=6.2, size=2.6, head_fill="#e8dcc8", bold_last=False):
    """RTL table: x = right edge."""
    if title:
        sh.text(x, y - 2.5, title, size=3.6, anchor="right", weight=700)
    tw = sum(widths)
    yy = y
    sh.rect(x - tw, yy, tw, row_h, lw="xs", fill=head_fill)
    cx = x
    for c, w in zip(cols, widths):
        sh.text(cx - w / 2, yy + row_h * 0.68, c, size=size * 0.95, weight=700)
        cx -= w
    yy += row_h
    for i, r in enumerate(rows):
        last = bold_last and i == len(rows) - 1
        sh.rect(x - tw, yy, tw, row_h, lw="xs", fill="#f7f3ec" if last else ("#fff" if i % 2 == 0 else "#fbfaf7"))
        cx = x
        for c, w in zip(r, widths):
            sh.text(cx - w / 2, yy + row_h * 0.68, c, size=size, weight=700 if last else 400)
            cx -= w
        yy += row_h
    cx = x
    for w in widths[:-1]:
        cx -= w
        sh.line(cx, y, cx, yy, lw="xxs")
    return yy


# ----------------------------------------------------------------------------- site drawing
def neighbours(v: View):
    # neighbouring lots & houses (schematic)
    for (x0, y0, x1, y1) in [(0, 36, 30, 72), (0, -36, 30, 0)]:
        v.rect(x0, y0, x1, y1, fill="none", lw="xs", color="#777")
    for (x0, y0, x1, y1) in [(6, 40, 24, 50), (8, -14, 24, -4)]:
        v.rect(x0, y0, x1, y1, fill="#e7e4de", lw="xs", color="#666")
        v.text((x0 + x1) / 2, (y0 + y1) / 2, "מבנה קיים", size=2.2, color="#555")


def lot_and_lines(v: View, scale):
    v.rect(L["x0"], L["y0"], L["x1"], L["y1"], fill="none", lw="l", color="#2b4fa8", dash="8 2 1.5 2")
    E = M.ENVELOPE
    v.rect(E[0], E[1], E[2], E[3], fill="none", lw="s", color="#c0392b", dash="4 1.5")


def sheet_site(sh, box):
    x, y, w, h = box
    sc = 200
    doc = DXF_DOCS.setdefault("site_250", new_dxf())
    k = 1000 / sc
    ox = x + 62 - (-8) * k
    oy = y + h * 0.5 + 18 * k
    v = View(sh, ox, oy, sc, dxf=doc.modelspace())
    sh.begin_clip(x, y, w * 0.48, h)
    # golf course to the west
    v.rect(-30, -40, -6, 80, fill="pat:grass", lw="xs", color="#7d9a5a")
    v.text(-17, 18, "מגרש הגולף", size=3.4, weight=700, color="#4f6b34", rot=-90)
    v.rect(-6, -40, 0, 80, fill="#f2efe8", lw="xxs")
    v.text(-3, 30, "שביל הליכה ציבורי", size=2.2, rot=-90, color="#555")
    # street
    v.rect(30, -40, 32.5, 80, fill="#ece8e0", lw="xs")
    v.rect(32.5, -40, 42, 80, fill="#d8d6d2", lw="xs")
    v.line(37.25, -40, 37.25, 80, lw="xs", dash="4 3", color="#fff")
    v.rect(42, -40, 44.5, 80, fill="#ece8e0", lw="xs")
    v.text(37.25, 52, "רחוב השקמה (שכונה 13)", size=3.0, weight=600, rot=-90)
    neighbours(v)
    lot_and_lines(v, sc)
    # landscape
    for r in M.SITE["lawn"]:
        v.rect(*r, fill="pat:grass", lw="xxs", color="#9bb07a")
    for r in M.SITE["planting"]:
        v.rect(*r, fill="pat:planting", lw="xxs", color="#9bb07a")
    for r in M.SITE["deck"]:
        v.rect(*r, fill="#ead9bf", lw="xxs")
    for r in M.SITE["paving"]:
        v.rect(*r, fill="#e6e1d7", lw="xxs")
    P = M.POOL
    v.rect(P["x0"], P["y0"], P["x1"], P["y1"], fill="#bfe0ea", lw="s")
    # building: UF roof outline (filled) + GF outline
    g = Polygon(M.OUTLINES["G"])
    u = Polygon(M.OUTLINES["U"])
    v.polygon(list(g.exterior.coords), fill="#cbb89a", lw="m")
    v.polygon(list(u.exterior.coords), fill="#f4f1ea", lw="l")
    v.polygon(M.OUTLINES["R"], fill="#e0dbd2", lw="m")
    v.text(9.5, 22.5, "+7.00", size=2.2, weight=600)
    v.text(15.3, 29.6, "+10.00", size=2.0, weight=600)
    v.text(21.0, 28.5, "+7.00", size=2.2, weight=600)
    v.text(19.0, 23.0, "+3.60", size=2.0, weight=600)
    v.text(17.5, 34.4, "בית כורכר", size=3.0, weight=700)
    for (tx, ty, r, kd) in M.SITE["trees"]:
        v.circle(tx, ty, r, lw="xxs", color="#5e6f45", fill="#b9c99a", fop=0.6)
    for (x0, y0, x1, y1) in M.CARS:
        v.rect(x0 + 0.2, y0 + 0.2, x1 - 0.2, y1 - 0.2, fill="#ddd", lw="xxs")
    # dims to boundaries
    v.dim_chain([L["x0"], M.X_W, M.X_E, L["x1"]], 0, axis="x", at=L["y0"] - 3.0, size=2.2)
    v.dim_chain([L["y0"], M.Y_S_U, M.Y_N, L["y1"]], 0, axis="y", at=L["x0"] - 8.5, size=2.2)
    v.dim_chain([L["x0"], L["x1"]], 0, axis="x", at=L["y0"] - 6.0, size=2.4)
    v.dim_chain([L["y0"], L["y1"]], 0, axis="y", at=L["x0"] - 11.0, size=2.4)
    # lot info
    v.text(3.0, 1.6, "גוש 10xxx  חלקה xx  (לימודי)", size=2.2, anchor="left", color="#444")
    v.text(15.0, -1.8, 'שטח מגרש 1,080 מ"ר', size=2.6, weight=700)
    for (xx, yy, val) in [(0.6, 0.6, "+18.20"), (29.4, 0.6, "+18.10"), (0.6, 35.4, "+18.35"), (29.4, 35.4, "+18.15")]:
        v.circle(xx, yy, 0.25, lw="xxs", fill="#000")
        v.text(xx + (0.6 if xx < 15 else -0.6), yy + 0.5, val, size=1.8, anchor="left" if xx < 15 else "right", color="#555")
    sh.end_group()
    north_arrow(sh, x + 30, y + 25, r=9)
    drawing_title(sh, x + w * 0.46, y + h - 16, "תכנית העמדה", 'קנ"מ 1:200', width=75)
    save_dxf("site_250")
    # ---- legend
    lx = x + w * 0.46
    ly = y + h - 75
    leg = [("#2b4fa8", "גבול מגרש", True), ("#c0392b", "קו בניין", True), ("#cbb89a", "קומת קרקע", False),
           ("#f4f1ea", "קומה א' (גג +7.00)", False), ("#bfe0ea", "בריכה", False), ("#b9c99a", "עצים לשימור/נטיעה", False)]
    for i, (col, t, line) in enumerate(leg):
        yy = ly + i * 6
        if line:
            sh.line(lx - 12, yy - 1, lx - 2, yy - 1, lw="m", color=col, dash="3 1")
        else:
            sh.rect(lx - 12, yy - 3, 10, 4, lw="xs", fill=col)
        sh.text(lx - 15, yy, t, size=2.6, anchor="right")

    # ---- tables (right half)
    A = areas()
    tx = x + w - 6
    ty = y + 18
    rows = [
        ["קומת מרתף", "-3.50", f'{A["B"]:.1f}', "—", f'{A["B"]:.1f}', "מרתף בקונטור הבניין*"],
        ["קומת קרקע", "±0.00", f'{A["main_g"]:.1f}', f'{A["stair"]:.1f}', f'{A["G"]:.1f}', "מדרגות ומעלית – שירות"],
        ["קומה א'", "+3.60", f'{A["main_u"]:.1f}', f'{A["stair"] + A["mamad_service"]:.1f}', f'{A["U"]:.1f}',
         f'ממ"ד {A["mamad_service"]:.1f} שירות'],
        ["חדר יציאה לגג", "+7.00", "—", f'{A["RX"]:.1f}', f'{A["RX"]:.1f}', "מדרגות + מעלית"],
        ['סה"כ מעל הקרקע', "", f'{A["main"]:.1f}', f'{A["service"]:.1f}', f'{A["main"] + A["service"]:.1f}', ""],
    ]
    yy = table(sh, tx, ty, ["קומה", "מפלס", 'עיקרי מ"ר', 'שירות מ"ר', 'סה"כ מ"ר', "הערות"], rows,
               [44, 22, 30, 30, 30, 70], title='טבלת שטחים (מ"ר ברוטו)', bold_last=True, row_h=8, size=3.1)
    sh.text(tx, yy + 5, '* שטח המרתף לפי הוראות התכנית החלה – מרתף בקונטור הקומה שמעליו; יש לאמת מול התב"ע.', size=2.2, anchor="right", color="#555")
    lot = A["lot"]
    rows2 = [
        ["שטח עיקרי", '35% = 378.0 מ"ר', f'{A["main"]:.1f} מ"ר ({A["main"] / lot * 100:.1f}%)', "✓"],
        ["שטחי שירות (מעל הקרקע)", '16% = 172.8 מ"ר', f'{A["service"]:.1f} מ"ר ({A["service"] / lot * 100:.1f}%)', "✓"],
        ["תכסית", '40% = 432.0 מ"ר', f'{A["cover"]:.1f} מ"ר ({A["cover"] / lot * 100:.1f}%)', "✓"],
        ["מספר קומות", "2 + מרתף", "2 + מרתף + יציאה לגג", "✓"],
        ["גובה מבנה (ראש מעקה)", "לפי תב\"ע", "+7.50 / ראש חדר יציאה +10.00", "לאימות"],
        ["קווי בניין ק/צ/א", "5 / 4 / 6 מ'", "5.00 / 4.00 / 6.00 מ'", "✓"],
        ["מקומות חניה", "2", "2 (חניה מקורה בפרגולה)", "✓"],
        ["בריכת שחייה", 'עד 60 מ"ר, עומק ≤1.8', f'{A["pool"]:.0f} מ"ר, עומק 1.20–1.60', "✓"],
        ["שטח מחלחל / גינון", "≥15%", f'{A["soft"]:.0f} מ"ר ({A["soft"] / lot * 100:.0f}%)', "✓"],
        ["מערכת סולארית", "חובה", 'PV ~15 קוט"ש על הגג', "✓"],
    ]
    yy = table(sh, tx, yy + 24, ["פרמטר", "מותר (תב\"ע – הנחת בסיס)", "מתוכנן", "עמידה"], rows2, [62, 62, 80, 22],
               title="טבלת זכויות ועמידה בהוראות (שכונה 13 – הנחת בסיס, לאימות מול תב\"ע 303-0207092)", size=3.0, row_h=7.6)
    # room schedule summary
    rows3 = []
    for lvl in ("B", "G", "U", "R"):
        for r in M.ROOMS:
            if r.level != lvl:
                continue
            a = unary_union([sbox(*q) for q in r.rects]).area
            rows3.append([r.no, r.name, f"{a:.1f}", r.floor])
    half = (len(rows3) + 1) // 2
    yt = yy + 22
    t1 = table(sh, tx, yt, ["מס'", "חלל", 'נטו מ"ר', "ריצוף"], rows3[:half], [14, 48, 20, 40],
               title="פרוגרמה – שטחים נטו", row_h=6.2, size=2.6)
    table(sh, tx - 128, yt, ["מס'", "חלל", 'נטו מ"ר', "ריצוף"], rows3[half:], [14, 48, 20, 40], row_h=6.2, size=2.6)


# ----------------------------------------------------------------------------- development plan
PLANT_LEGEND = [
    ("olive", "עץ זית עתיק (העתקה)", "Olea europaea"),
    ("carob", "חרוב מצוי", "Ceratonia siliqua"),
    ("palm", "וושינגטוניה חסונה", "Washingtonia robusta"),
    ("olive_s", "זית בפטיו", "Olea europaea"),
]


def tree_symbol(v: View, x, y, r, kind):
    if kind == "palm":
        v.circle(x, y, r, lw="xxs", color="#5e6f45", fill="#d9e3c4", fop=0.8)
        for a in range(0, 360, 30):
            v.line(x, y, x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a)), lw="xxs", color="#5e6f45")
    else:
        pts = []
        for i in range(24):
            a = math.radians(i * 15)
            rr = r * (0.88 + 0.12 * math.sin(i * 2.3))
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        v.polygon(pts, fill="#c7d6ab" if kind != "carob" else "#aebf8c", lw="xxs", color="#5e6f45", fop=0.75)
        v.circle(x, y, 0.12, lw="xxs", fill="#5e6f45")


def sheet_development(sh, box):
    x, y, w, h = box
    sc = 100
    k = 1000 / sc
    doc = DXF_DOCS.setdefault("site_100", new_dxf())
    ox = x + w * 0.60 - 15 * k
    oy = y + h * 0.5 + 18 * k
    v = View(sh, ox, oy, sc, dxf=doc.modelspace())
    # street & sidewalk
    v.rect(30, -0.5, 32.5, 36.5, fill="pat:paving", lw="xs")
    v.rect(32.5, -0.5, 34.5, 36.5, fill="#d8d6d2", lw="xs")
    v.text(31.25, 10, "מדרכה", size=2.4, rot=-90, color="#555")
    v.text(33.5, 18, "רחוב", size=2.6, rot=-90, color="#555", weight=600)
    # lawns / planting / decks / paving
    for r in M.SITE["lawn"]:
        v.rect(*r, fill="pat:grass", lw="xxs", color="#7d9a5a")
    for r in M.SITE["planting"]:
        v.rect(*r, fill="pat:planting", lw="xxs", color="#7d9a5a")
    for r in M.SITE["deck"]:
        v.rect(*r, fill="pat:deckv", lw="xs")
    for r in M.SITE["paving"]:
        v.rect(*r, fill="pat:paving", lw="xs")
    # covered terrace & deck bridge
    v.rect(M.X_W, M.Y_S_U, M.X_M, M.Y_S_G, fill="pat:deckv", lw="xs")
    v.rect(13.0, 19.6, M.PATIO[2] + 0.3, M.Y_S_G, fill="pat:deckv", lw="xs")
    # patio
    v.rect(M.PATIO[0], M.PATIO[1], M.PATIO[2], 19.6, fill="pat:paving", lw="s")
    v.text((M.PATIO[0] + M.PATIO[2]) / 2, 18.0, "פטיו שקוע -3.52", size=2.4, weight=500)
    # pool
    P = M.POOL
    v.rect(P["x0"] - 0.3, P["y0"] - 0.3, P["x1"] + 0.3, P["y1"] + 0.3, fill="#f1ede6", lw="s")
    v.rect(P["x0"], P["y0"], P["x1"], P["y1"], fill="pat:water", lw="m")
    sx0, sy0, sx1, sy1 = P["shelf"]
    v.rect(sx0, sy0, sx1, sy1, fill="#d9eef3", lw="xs", dash="2 1")
    v.text(20.8, 11.5, "מדף שיזוף", size=2.0, rot=-90)
    v.text(14.0, 11.8, "בריכת שחייה 14.00×4.00", size=2.8, weight=700)
    v.text(14.0, 10.9, "מפלס מים -0.22 | עומק 1.20–1.60 | גלישה לאורך הדופן הדרומית", size=2.1)
    v.line(P["x0"], P["y0"] + 0.15, P["x1"] - 2.4, P["y0"] + 0.15, lw="xxs", dash="1 0.6")
    # pool fence (safety) – glass 1.20 around the pool deck towards the garden
    v.polyline([(6.5, 7.6), (24.5, 7.6), (24.5, 13.5)], lw="m", color="#2a6f8f", dash="3 1")
    v.text(15.0, 7.1, "גדר בטיחות לבריכה – זכוכית 1.20 עם שער ננעל", size=2.0, color="#2a6f8f")
    # building footprint (GF walls)
    PL.draw_walls(v, "G", sc)
    PL.draw_openings(v, "G", sc)
    PL.draw_overheads(v, "G")
    for r in M.ROOMS:
        if r.level == "G" and not r.outdoor:
            u = unary_union([sbox(*q) for q in r.rects])
    v.rect(6.3, 21.3, 24.7, 31.7, fill="#f7f3ec", lw="xxs", color="#f7f3ec")
    PL.draw_walls(v, "G", sc)
    PL.draw_openings(v, "G", sc)
    v.text(15.5, 27.0, "בית כורכר", size=4.5, weight=700, font="Frank Ruhl Libre")
    v.text(15.5, 25.9, "קומת קרקע ±0.00 = +18.50", size=2.4)
    # fences & gates
    S = M.SITE
    for (x0, y0, x1, y1) in [(L["x0"], L["y0"], L["x1"], L["y0"] + 0.2), (L["x0"], L["y1"] - 0.2, L["x1"], L["y1"])]:
        v.rect(x0, y0, x1, y1, fill="pat:stone", lw="s")
    v.rect(L["x0"], L["y0"], L["x0"] + 0.2, L["y1"], fill="#cfe3ea", lw="s")
    gx, gy0, gy1 = S["gate"]
    for (y0, y1) in [(L["y0"], 15.8), (21.8, gy0), (gy1, L["y1"])]:
        v.rect(L["x1"] - 0.2, y0, L["x1"], y1, fill="pat:stone", lw="s")
    v.line(L["x1"] - 0.1, 15.8, L["x1"] - 0.1, 21.8, lw="xs", dash="2 1")
    v.text(31.0, 18.8, "שער חשמלי הזזה", size=2.0, rot=-90)
    v.arc(L["x1"], gy0, gy1 - gy0, 90, 180, lw="xxs")
    v.text(31.0, 29.8, "שער כניסה", size=2.0, rot=-90)
    mx0, my0, mx1, my1 = S["meters"]
    v.rect(mx0 - 0.4, my0, mx1, my1, fill="#ddd", lw="s")
    v.text(mx0 - 1.0, (my0 + my1) / 2, "נישת מונים ואשפה", size=1.9, anchor="right")
    # parking
    for (x0, y0, x1, y1) in M.CARS:
        v.rect(x0, y0, x1, y1, fill="none", lw="xs")
        v.rect(x0 + 0.35, y0 + 0.3, x1 - 0.35, y1 - 0.3, fill="#eee", lw="xxs")
    v.text(27.6, 15.3, "חניה מקורה ל-2 רכבים (פרגולת אלומיניום)", size=2.0)
    # water feature, firepit, shower, bbq
    wx0, wy0, wx1, wy1 = S["water_feature"]
    v.rect(wx0, wy0, wx1, wy1, fill="pat:water", lw="s")
    v.text((wx0 + wx1) / 2, wy1 + 0.4, "בריכת נוי / מפל מים", size=2.0)
    fx, fy, fr = S["firepit"]
    v.circle(fx, fy, fr + 1.2, fill="pat:gravel", lw="xs")
    v.circle(fx, fy, 0.5, fill="#c47a3a", lw="s")
    v.text(fx, fy - fr - 1.7, "פינת מדורה – חצץ", size=2.0)
    v.circle(*S["outdoor_shower"], 0.3, lw="s")
    v.text(S["outdoor_shower"][0] + 0.5, S["outdoor_shower"][1], "מקלחת חוץ", size=1.9, anchor="left")
    bx0, by0, bx1, by1 = S["bbq"]
    v.rect(bx0, by0, bx1, by1, fill="#ddd", lw="s")
    v.text((bx0 + bx1) / 2, by0 - 0.5, "מטבח חוץ / ברביקיו", size=1.9)
    for (lx, ly) in S["loungers"]:
        v.rect(lx, ly, lx + 0.7, ly + 1.9, fill="#fff", lw="xxs")
    # trees
    for (tx, ty, r, kd) in S["trees"]:
        tree_symbol(v, tx, ty, r, kd)
    # levels
    for (xx, yy, z) in [(3.0, 3.0, M.GARDEN), (15.0, 15.2, M.GARDEN + 0.13), (27.0, 30.0, M.GARDEN + 0.10),
                        (27.0, 17.0, M.STREET + 0.05), (31.2, 2.0, M.STREET), (9.0, 18.0, -0.02),
                        (16.0, 8.4, M.GARDEN), (3.0, 28.0, M.GARDEN - 0.05)]:
        v.level_mark(xx, yy, z, size=2.0, plan=True)
    # boundary/building lines
    lot_and_lines(v, sc)
    v.dim_chain([L["x0"], M.X_W, M.X_E, L["x1"]], 0, axis="x", at=L["y0"] - 1.6, size=2.2)
    v.dim_chain([L["y0"], 4.0, M.Y_S_U, M.Y_S_G, M.Y_N, 32.0, L["y1"]], 0, axis="y", at=L["x0"] - 1.6, size=2.2)
    v.text(M.ENVELOPE[0] + 0.3, M.ENVELOPE[3] - 0.5, "קו בניין", size=2.0, anchor="left", color="#c0392b")
    north_arrow(sh, x + w - 20, y + 22, r=9)
    drawing_title(sh, x + w - 8, y + h - 22, "תכנית פיתוח שטח", 'קנ"מ 1:100', width=85, size=8)
    save_dxf("site_100")
    # legends
    lx, ly = x + 98, y + 20
    sh.text(lx, ly, "מקרא חומרים:", size=3.2, anchor="right", weight=700)
    mats = [("pat:grass", "מדשאה – דשא סינטטי/טבעי חסכוני במים"), ("pat:planting", "ערוגות צמחייה ים-תיכונית (לבנדר, רוזמרין, דגניים)"),
            ("pat:deckv", "דק עץ טיק / IPE על קורות אלומיניום"), ("pat:paving", "ריצוף אבן גיר בהירה 60/90 – חספוס R11"),
            ("pat:water", "בריכה – פסיפס זכוכית בגוון חול"), ("pat:stone", "גדר בנויה בחיפוי אבן כורכר 1.50/1.80"),
            ("#cfe3ea", "גדר מערבית – קיר נמוך 0.60 + זכוכית לנוף הגולף")]
    for i, (f, t) in enumerate(mats):
        yy = ly + 6 + i * 7
        sh.rect(lx - 12, yy - 4, 10, 5, lw="xs", fill=f if not f.startswith("pat:") else "none")
        if f.startswith("pat:"):
            sh.used_patterns.add(f[4:])
            sh.rect(lx - 12, yy - 4, 10, 5, lw="xs", fill=f"url(#{f[4:]})")
        sh.text(lx - 15, yy, t, size=2.4, anchor="right")
    yy = ly + 6 + len(mats) * 7 + 8
    sh.text(lx, yy, "מקרא צמחייה:", size=3.2, anchor="right", weight=700)
    for i, (kd, he, la) in enumerate(PLANT_LEGEND):
        y2 = yy + 7 + i * 8
        vv = View(sh, lx - 7, y2 - 1, 100)
        tree_symbol(vv, 0, 0, 0.3, kd)
        sh.text(lx - 15, y2, he, size=2.4, anchor="right")
        sh.text(lx - 15, y2 + 3.2, la, size=2.0, anchor="right", color="#666", italic=True)
    yy = yy + 7 + len(PLANT_LEGEND) * 8 + 8
    notes = ["הערות פיתוח:", "1. ניקוז עילי בשיפוע 1.5% הרחק מהמבנה, אל ערוגות חלחול.",
             "2. השקיה בטפטוף ממוחשבת, צמחייה חסכונית במים.",
             "3. תאורת גינה LED נמוכה (Dark-Sky), גופי שקיעה במדרגות.",
             "4. גדר בטיחות לבריכה לפי הנחיות משרד הבריאות.",
             "5. גדר דרומית/צפונית 1.80 לאורך הבריכה, 1.50 ביתר."]
    for i, t in enumerate(notes):
        sh.text(lx, yy + i * 4.6, t, size=2.4 if i else 3.0, anchor="right", weight=700 if i == 0 else 400)
