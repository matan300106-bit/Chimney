"""Sheet 01 (cover) and the closing 'thanks' sheet – full bleed, no title block.

If the exterior renders exist (out/renders/ext_01.jpg, ext_04.jpg) they are used full bleed;
otherwise a refined placeholder is drawn: warm gradient + a large axonometric of the model.
"""
from __future__ import annotations

import os

import model as M
from concept import CHAR, FR, MUTED, SAND, SAND_D, draw_massing, tw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
W, H = 841, 594
PANEL_X = 548            # left edge of the typography panel
TX = W - 52              # right text edge


def _render(name):
    p = os.path.join(ROOT, "out", "renders", name)
    return os.path.exists(p) and os.path.getsize(p) > 0


def _background(sh, render_name, uid, fallback="axo"):
    """Full-bleed render, or the placeholder (gradient + axonometric). Returns True if a render was used."""
    has = _render(render_name)
    if has:
        sh.image(0, 0, W, H, f"../renders/{render_name}", preserve="xMidYMid slice")
        sh.defs_extra.append(
            f'<linearGradient id="{uid}fade" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="#f6f1e8" stop-opacity="0"/>'
            f'<stop offset="0.35" stop-color="#f6f1e8" stop-opacity="0.82"/>'
            f'<stop offset="1" stop-color="#f6f1e8" stop-opacity="0.92"/></linearGradient>')
        sh.add(f'<rect x="{PANEL_X - 90}" y="0" width="{W - PANEL_X + 90}" height="{H}" fill="url(#{uid}fade)"/>')
        return True
    sh.defs_extra.append(
        f'<linearGradient id="{uid}bg" x1="0" y1="0" x2="0.35" y2="1">'
        f'<stop offset="0" stop-color="#f6f0e5"/><stop offset="0.6" stop-color="#ece0cb"/>'
        f'<stop offset="1" stop-color="#ddc9a8"/></linearGradient>'
        f'<radialGradient id="{uid}glow" cx="0.32" cy="0.42" r="0.55">'
        f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.65"/>'
        f'<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>')
    sh.add(f'<rect x="0" y="0" width="{W}" height="{H}" fill="url(#{uid}bg)"/>')
    sh.add(f'<rect x="0" y="0" width="{PANEL_X}" height="{H}" fill="url(#{uid}glow)"/>')
    if fallback == "axo":
        draw_massing(sh, 18, 52, PANEL_X - 40, 500, 6, detail=True)
    else:  # the six massing steps, from lot to house
        cw, ch, gap = (PANEL_X - 70) / 3, 150, 34
        y0 = (H - 2 * ch - gap) / 2
        for i in range(6):
            col, row = i % 3, i // 3
            x = PANEL_X - 30 - (col + 1) * cw
            y = y0 + row * (ch + gap)
            draw_massing(sh, x, y, cw, ch, i + 1, detail=(i == 5))
            sh.text(x + cw - 4, y + 16, f"{i + 1:02d}", size=9, anchor="right", weight=300, color=SAND_D, font=FR)
    sh.line(PANEL_X, 60, PANEL_X, H - 60, lw=0.25, color=SAND_D)
    return False


def _ridge_mark(sh, xr, y, w=70):
    sh.path(f"M{xr - w},{y + 6} C{xr - w * 0.78},{y - 4} {xr - w * 0.62},{y + 4} {xr - w * 0.45},{y - 1} "
            f"S{xr - w * 0.15},{y - 6} {xr},{y + 2}", lw=0.6, color="#8a6b45")
    sh.line(xr - w, y + 9, xr, y + 9, lw=0.3, color="#8a6b45")


def sheet_cover(sh, box):
    _background(sh, "ext_01.jpg", "cv")
    P = M.PROJECT
    # top line
    sh.text(TX, 66, P["school"].replace("הנדסאים – ", "פרויקט גמר · הנדסאים – "), size=5.0, anchor="right",
            weight=400, color=CHAR)
    sh.text(TX, 74, "FINAL PROJECT  ·  ARCHITECTURE & INTERIOR DESIGN", size=3.0, anchor="right", weight=500,
            color=SAND_D, spacing="1.1")
    sh.line(TX - 160, 81, TX, 81, lw=0.25, color=SAND_D)
    # title block
    _ridge_mark(sh, TX, 186, 96)
    sh.text(TX, 244, P["name"], size=46, anchor="right", weight=700, color=CHAR, font=FR)
    sh.text(TX, 270, P["subtitle"], size=15, anchor="right", weight=300, color=CHAR, font=FR)
    sh.line(TX - 128, 281, TX, 281, lw=0.7, color=SAND_D)
    sh.text(TX, 294, "רכס ואופק  ·  רובע 13 (שכונת הגולף), קיסריה", size=5.6, anchor="right", weight=300, color=CHAR)
    sh.text(TX, 304, P["name_en"] + "  ·  BOUTIQUE VILLA  ·  CAESAREA", size=3.4, anchor="right", weight=500,
            color=SAND_D, spacing="1.6")
    # credits
    y = 488
    sh.line(TX - 160, y - 10, TX, y - 10, lw=0.25, color=SAND_D)
    rows = [("מנחה:", P["instructor"]), ("מגיש/ה:", "________________"), ("תאריך:", P["date"])]
    for lab, val in rows:
        sh.text(TX, y, lab, size=5.0, anchor="right", weight=300, color=MUTED)
        sh.text(TX - tw(lab, 5.0, 300) - 4, y, val, size=5.6, anchor="right", weight=500, color=CHAR)
        y += 11
    sh.text(TX, H - 34, "גיליון 01", size=3.0, anchor="right", weight=400, color=MUTED)


def sheet_thanks(sh, box):
    has = _background(sh, "ext_04.jpg", "th", fallback="steps")
    P = M.PROJECT
    _ridge_mark(sh, TX, 214, 96)
    sh.text(TX, 290, "תודה!", size=72, anchor="right", weight=700, color=CHAR, font=FR)
    sh.line(TX - 128, 306, TX, 306, lw=0.7, color=SAND_D)
    sh.text(TX, 322, f'{P["name"]}  ·  {P["subtitle"]}', size=7.5, anchor="right", weight=300, color=CHAR, font=FR)
    sh.text(TX, 334, "על הליווי, הסבלנות וההשראה – תודה למנחה ולצוות המגמה.", size=4.6, anchor="right", weight=300,
            color=CHAR)
    y = 500
    sh.line(TX - 160, y - 10, TX, y - 10, lw=0.25, color=SAND_D)
    for lab, val in [("מנחה:", P["instructor"]), ("מגיש/ה:", "________________"), ("תאריך:", P["date"])]:
        sh.text(TX, y, lab, size=5.0, anchor="right", weight=300, color=MUTED)
        sh.text(TX - tw(lab, 5.0, 300) - 4, y, val, size=5.6, anchor="right", weight=500, color=CHAR)
        y += 11
    sh.text(TX, H - 34, P["name_en"] + "  ·  " + P["school"], size=3.0, anchor="right", weight=400, color=MUTED)
