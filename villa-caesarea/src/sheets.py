"""Sheet framework: A1 landscape sheets with the project title block.

Each sheet builder has the signature  fn(sh: Sheet, box: tuple[x, y, w, h]) -> None
where `box` is the free drawing area (paper mm, y down) left of the title block.
"""
from __future__ import annotations

import importlib

import model as M
from draw import Sheet, LW

W, H = 841, 594
TB_W = 78           # title block width
MARGIN = 10
AREA = (MARGIN + 2, MARGIN + 2, W - TB_W - 2 * MARGIN - 6, H - 2 * MARGIN - 4)

# (number, title, scale text, "module:function")
SHEETS = [
    (1, "שער", "", "cover:sheet_cover"),
    (2, "קונספט ומחקר", "", "concept:sheet_concept"),
    (3, "ניתוח אתר וסביבה", "", "concept:sheet_site_analysis"),
    (4, "תכנית העמדה וטבלת שטחים", "1:200", "siteplan:sheet_site"),
    (5, "תכנית פיתוח שטח", "1:100", "siteplan:sheet_development"),
    (6, "תכניות מרתף וקרקע", "1:100", "plans:sheet_plans_bg"),
    (7, "תכניות קומה א' וגג", "1:100", "plans:sheet_plans_ur"),
    (8, "חזיתות", "1:100", "elev:sheet_elevations_100"),
    (9, "חתכים", "1:100", "elev:sheet_sections_100"),
    (10, "סכמות סטטיות", "1:100", "structure:sheet_structure"),
    (11, "תכנית קומת קרקע", "1:50", "plans:sheet_ground_50"),
    (12, "תכנית קומה א'", "1:50", "plans:sheet_upper_50"),
    (13, "חזיתות", "1:50", "elev:sheet_elevations_50"),
    (14, "חתך A-A", "1:50", "elev:sheet_section_a_50"),
    (15, "חתך B-B", "1:50", "elev:sheet_section_b_50"),
    (16, "גיליון מדרגות", "1:25, 1:5", "details:sheet_stairs"),
    (17, "פרטי בניין", "1:20, 1:5", "details:sheet_details"),
    (18, "רשימת אלומיניום ונגרות", "1:50", "schedule:sheet_schedule"),
    (19, "עיצוב פנים – חלל המגורים", "1:50", "interior:sheet_interior"),
    (20, "עיצוב ריהוט – אי המטבח", "1:25, 1:10, 1:2", "joinery:sheet_joinery"),
    (21, "הדמיות חוץ", "", "renders:sheet_ext_renders"),
    (22, "הדמיות פנים", "", "renders:sheet_int_renders"),
    (23, "תודה", "", "cover:sheet_thanks"),
]

FULLBLEED = {1, 23}  # sheets without title block


def title_block(sh: Sheet, no: int, title: str, scale: str):
    x0 = W - MARGIN - TB_W
    y0 = MARGIN
    w = TB_W
    h = H - 2 * MARGIN
    sh.rect(MARGIN, MARGIN, W - 2 * MARGIN, H - 2 * MARGIN, lw="l")
    sh.rect(x0, y0, w, h, lw="l", fill="#fbfaf7")
    xr = x0 + w - 4  # right text edge
    y = y0 + 4
    # logo block – project mark
    sh.rect(x0 + 3, y, w - 6, 46, lw="s", fill="#efe7da")
    # kurkar-ridge mark
    sh.path(f"M{x0 + 8},{y + 34} C{x0 + 20},{y + 22} {x0 + 30},{y + 30} {x0 + 40},{y + 24} "
            f"S{x0 + 60},{y + 18} {x0 + w - 8},{y + 26}", lw="m", color="#8a6b45")
    sh.line(x0 + 8, y + 38, x0 + w - 8, y + 38, lw="s", color="#8a6b45")
    sh.text(x0 + w / 2, y + 14, M.PROJECT["name"], size=9.5, weight=700, font="Frank Ruhl Libre")
    sh.text(x0 + w / 2, y + 44, M.PROJECT["name_en"], size=3.2, weight=500, spacing="1.6")
    y += 50

    def field(label, value, hh=11, vsize=4.2, bold=False):
        nonlocal y
        sh.rect(x0 + 3, y, w - 6, hh, lw="xs", fill="#fff")
        sh.text(xr - 1, y + 3.8, label, size=2.5, anchor="right", color="#555")
        sh.text(xr - 1, y + hh - 2.4, value, size=vsize, anchor="right", weight=700 if bold else 500)
        y += hh + 1.5

    field("שם הפרויקט:", f'{M.PROJECT["subtitle"]}')
    field("מיקום הפרויקט:", M.PROJECT["location"], vsize=3.6)
    field("מנחה:", M.PROJECT["instructor"], bold=True)
    field("שם הגיליון:", title, vsize=4.4 if len(title) < 22 else 3.4, bold=True)
    sh.rect(x0 + 3, y, (w - 7.5) / 2, 11, lw="xs", fill="#fff")
    sh.rect(x0 + 3 + (w - 7.5) / 2 + 1.5, y, (w - 7.5) / 2, 11, lw="xs", fill="#fff")
    sh.text(xr - 1, y + 3.8, "מס' גיליון:", size=2.5, anchor="right", color="#555")
    sh.text(xr - 1, y + 9.2, f"{no:02d}", size=5, anchor="right", weight=700)
    xm = x0 + 3 + (w - 7.5) / 2 - 1
    sh.text(xm, y + 3.8, 'קנ"מ:', size=2.5, anchor="right", color="#555")
    sh.text(xm, y + 9.2, scale or "—", size=3.6 if len(scale) < 9 else 2.8, anchor="right", weight=600)
    y += 12.5
    # sheet list
    lh = 4.15
    top = y
    n = len(SHEETS)
    sh.rect(x0 + 3, y, w - 6, n * lh + 9, lw="xs", fill="#fff")
    sh.text(xr - 1, y + 4.5, "רשימת גיליונות:", size=2.8, anchor="right", weight=700)
    y += 8
    for (k, t, s, _) in SHEETS:
        cur = k == no
        if cur:
            sh.rect(x0 + 4, y - 3.0, w - 8, lh - 0.2, color="none", fill="#e8dcc8")
        sh.text(xr - 1, y, f"{k:02d}", size=2.4, anchor="right", weight=700 if cur else 400)
        sh.text(xr - 8, y, t, size=2.4, anchor="right", weight=700 if cur else 400)
        if s:
            sh.text(x0 + 6, y, s, size=2.1, anchor="left", color="#444")
        y += lh
    y = top + n * lh + 9 + 1.5
    field("מגמה:", M.PROJECT["school"], vsize=3.0)
    field("שם המגיש/ה ות.ז.:", f'{M.PROJECT["student"]}   {M.PROJECT["student_id"]}', vsize=3.4)
    field("תאריך:", M.PROJECT["date"], vsize=3.6)
    # small key plan / north
    from draw import north_arrow
    ky = y + 2
    rem = y0 + h - ky - 4
    if rem > 20:
        sh.rect(x0 + 3, ky, w - 6, rem, lw="xs", fill="#fff")
        # mini site key
        k = min((w - 20) / 30.0, (rem - 8) / 36.0)
        ox, oy = x0 + 6, ky + 4 + 36 * k
        sh.rect(ox, oy - 36 * k, 30 * k, 36 * k, lw="xs", dash="1 0.6")
        sh.rect(ox + 6 * k, oy - 32 * k, 19 * k, 11 * k, lw="xs", fill="#cbb89a")
        sh.polyline([(ox + 6 * k, oy - 16 * k), (ox + 13 * k, oy - 16 * k), (ox + 13 * k, oy - 25 * k), (ox + 25 * k, oy - 25 * k)],
                    lw="xs", dash="0.8 0.5")
        sh.rect(ox + 8 * k, oy - 13.5 * k, 14 * k, 4 * k, lw="xs", fill="#cfe6ee")
        north_arrow(sh, x0 + w - 12, ky + 12, r=5)


def build_sheet(no, title, scale, fn_path):
    sh = Sheet(W, H)
    sh.add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    mod_name, fn_name = fn_path.split(":")
    ok = True
    try:
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, fn_name)
    except (ImportError, AttributeError) as e:
        fn = None
        ok = False
        err = str(e)
    if no not in FULLBLEED:
        title_block(sh, no, title, scale)
    if fn is None:
        x, y, w, h = AREA
        sh.rect(x, y, w, h, lw="s", dash="4 2", color="#bbb")
        sh.text(x + w / 2, y + h / 2, f"[{title}] – בהכנה", size=12, color="#bbb")
        sh.text(x + w / 2, y + h / 2 + 12, err[:120], size=4, color="#ccc")
    else:
        fn(sh, AREA)
    return sh, ok
