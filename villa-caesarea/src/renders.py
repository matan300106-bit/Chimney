"""Render sheets (exterior / interior visualisations)."""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RDIR = os.path.join(ROOT, "out", "renders")


def frame(sh, x, y, w, h, name, caption):
    p = os.path.join(RDIR, f"{name}.jpg")
    if os.path.exists(p):
        sh.image(x, y, w, h, f"../renders/{name}.jpg", preserve="xMidYMid slice")
        sh.rect(x, y, w, h, lw="xs", color="#888")
    else:
        sh.rect(x, y, w, h, lw="s", fill="#efe9df", dash="3 2", color="#aaa")
        sh.text(x + w / 2, y + h / 2, f"הדמיה {name}", size=6, color="#aaa")
    sh.text(x + w - 2, y + h + 5.0, caption, size=3.2, anchor="right", weight=600)


def sheet_ext_renders(sh, box):
    x, y, w, h = box
    g = 6
    big_w = w * 0.62
    big_h = big_w / 1.6
    frame(sh, x + w - big_w, y, big_w, big_h, "ext_01", "מבט מדרום-מערב בשעת בין ערביים – הזיז, הלוג'יה והבריכה")
    sw = w - big_w - g
    sh_h = (big_h - g - 7) / 2
    frame(sh, x, y, sw, sh_h, "ext_02", "ציר הגינה והבריכה – מבט צפונה")
    frame(sh, x, y + sh_h + g + 7, sw, sh_h, "ext_03", "חזית הרחוב – כניסה וחניה מקורה")
    y2 = y + big_h + 14
    h2 = h - big_h - 20
    w2 = (w - g) / 2
    frame(sh, x + w - w2, y2, w2, h2, "ext_04", "מבט על – מרפסת הגג, מערכת PV והמגרש")
    frame(sh, x, y2, w2, h2, "ext_05", "הפטיו השקוע והמרפסת המקורה")


def sheet_int_renders(sh, box):
    x, y, w, h = box
    g = 6
    top_h = h * 0.56
    frame(sh, x + w * 0.38 + g / 2, y, w * 0.62 - g / 2, top_h, "int_01", "הסלון – פתיחה מלאה אל המרפסת והגן")
    frame(sh, x, y, w * 0.38 - g / 2, top_h, "int_03", "סוויטת ההורים – מבט אל הלוג'יה")
    y2 = y + top_h + 14
    frame(sh, x, y2, w, h - top_h - 20, "int_02", "המטבח, אי האבן ופינת האוכל")
