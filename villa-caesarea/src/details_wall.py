"""Sheet 'פרטי בניין': wall section 1:20 through the west façade + building details.

Wall section location: west façade (x = X_W = 6.00), cut at y = 23.00 looking north
(exterior on the paper-left): basement retaining wall & raft, GF lift-and-slide door
AL-05 in the stone-clad base, UF bathroom window AL-23 in the white EIFS volume with
the aluminium wood-look louvres, roof slab, parapet and coping.
"""
from __future__ import annotations

import model as M
import draw as D
from details_lib import (Frame, R, PG, LN, U, breakline, callout_col, circle_poly, detail_title, dim_chain_h,
                         dim_chain_v, dimh, dimv, fmt_lv, level_tag, ltr, ring, stack_callout, tw, bubble,
                         detail_ref, fill_ref)
from details import (S_RC, S_BLINDING, S_OAK, S_FILL, S_PORC, S_MORTAR, S_EARTH, S_GRAVEL, S_MEMB, S_GLASS,
                     S_ALU, S_SS, S_GYPS, S_BLOCK, S_PLAST, S_WOOLV, S_WOOL, S_XPS, S_EPS, S_LIME, S_DRAIN,
                     SZ, SZS, sheet_no)

SN = ""
XF = M.X_W                      # façade outer face (6.00)
XC0, XC1 = XF + M.T_SKIN, XF + M.T_EXT     # wall core 6.10 – 6.30
Y_CUT = 23.00

S_ALUW = dict(fill="dx:aluwood", lw="s")
S_TEAK = dict(fill="dx:teak", lw="s")
S_EARTHL = dict(fill="pat:earth", lw="none", color="none")
S_GRAV = dict(fill="pat:gravel", lw="xxs")
S_WATER = dict(fill="dx:water", lw="xs")
S_RUB = dict(fill="dx:rubber", lw="xxs")
S_SAND = dict(fill="dx:sandx", lw="xxs")


def _op(level, tag):
    for w in M.walls_on(level):
        for o in w.openings:
            if o.tag == tag:
                return o
    return None


# =========================================================================== #
def build_sheet16(sh, box):
    global SN
    SN = sheet_no("sheet_details")
    bx, by, bw, bh = box
    col = 288
    wall_section(sh, bx, by, col, bh)
    # details 2 columns × 3 rows
    dx0 = bx + col + 4
    cw = (bx + bw - dx0) / 2
    rows = [180, 190, bh - 370]
    y = by
    cells = []
    for rh in rows:
        cells.append(((dx0 + cw, y, cw, rh), (dx0, y, cw, rh)))
        y += rh
    (c1, c2), (c3, c4), (c5, c6) = cells
    det_parapet(sh, *c1)
    det_soffit(sh, *c2)
    det_threshold(sh, *c3)
    det_anchor(sh, *c4)
    det_patio(sh, *c5)
    det_pool(sh, *c6)
    # light cell separators
    for (a, b) in cells[:-1]:
        sh.line(dx0 + 2, a[1] + a[3] - 1, bx + bw - 2, a[1] + a[3] - 1, lw="xxs", color="#bbb")
    sh.line(dx0 + cw, by + 2, dx0 + cw, by + bh - 2, lw="xxs", color="#bbb")
    sh.line(dx0 - 2, by + 2, dx0 - 2, by + bh - 2, lw="xxs", color="#bbb")


# =========================================================================== #
#  WALL SECTION 1:20
# =========================================================================== #
def wall_section(sh, x0, y0, w, h):
    LV = M.LV
    sB, sG, sU, sR = M.slab_top("B"), M.slab_top("G"), M.slab_top("U"), M.slab_top("R")
    raft_b = sB - M.RAFT
    gard = M.GARDEN
    door = _op("G", "AL-05")
    win = _op("U", "AL-23")
    d_head = LV["G"] + (door.head if door else 3.0)
    w_sill = LV["U"] + (win.sill if win else 1.0)
    w_head = LV["U"] + (win.head if win else 2.7)
    par_top = LV["R"] + 0.50
    fin = next((f for f in M.FINS if f["axis"] == "y" and f["c"] < XF), None)
    fx0 = fin["c"] - fin["depth"] / 2 if fin else 5.58
    fx1 = fin["c"] + fin["depth"] / 2 if fin else 5.78
    ceil_B = LV["B"] + 2.90
    ceil_G = LV["G"] + 3.10
    ceil_U = w_head

    xa, xb = 4.95, 7.45
    bands = [(raft_b - 0.15, -2.70), (-1.45, 0.95), (2.15, 4.95), (5.60, par_top + 0.12)]
    k = 50.0
    ox = x0 + 66
    fr = Frame(sh, ox, 0, 20, x0=xa, bands=bands, gap=5.0, clip=(xa, xb))
    fr.oy = y0 + 14 + (bands[-1][1] - fr.offs[-1]) * k
    items = []
    # ---------------------------------------------------------------- ground
    items.append((R(xa, raft_b - 0.15, xb, raft_b - 0.05), S_EARTHL))
    items.append((R(xa, raft_b - 0.05, XF - 0.03, gard - 0.35), S_EARTHL))
    items.append((R(xa, gard - 0.35, XF - 0.03, -0.20), dict(fill="pat:earth", color="none")))
    # drainage gravel (footing + vertical strip)
    grav = U(R(5.12, raft_b - 0.05, XF - 0.03, raft_b + 0.42), R(XF - 0.28, raft_b + 0.42, XF - 0.03, -0.55))
    items.append((grav, S_GRAV))
    items.append((LN(list(grav.exterior.coords)), dict(lw="xxs", dash="1 0.6", color="#555")))
    # blinding + membranes
    items.append((R(5.55, raft_b - 0.05, xb, raft_b), S_BLINDING))
    items.append((R(5.62, raft_b - 0.008, xb, raft_b), S_MEMB))
    items.append((R(5.642, raft_b - 0.008, 5.65, sB), S_MEMB))
    items.append((R(5.65, sB, XF - 0.008, sB + 0.008), S_MEMB))
    items.append((R(XF - 0.008, sB, XF, -0.06), S_MEMB))
    items.append((R(XF - 0.028, sB + 0.008, XF - 0.008, -0.22), S_DRAIN))
    # exterior terrace at the GF door: paving 3 + bed 3 + RC 12 on compacted base
    items.append((R(xa, -0.50, XF - 0.03, -0.20), dict(fill="pat:gravel", lw="xxs")))
    items.append((R(xa, -0.20, XF - 0.15, -0.08), S_RC))
    items.append((R(xa, -0.08, XF - 0.15, -0.05), S_MORTAR))
    items.append((R(xa, -0.05, XF - 0.155, -0.02), S_LIME))
    # slot drainage channel (polymer concrete + SS grate) against the frame
    ch = PG([(XF - 0.15, -0.20), (XF - 0.008, -0.20), (XF - 0.008, -0.02), (XF - 0.02, -0.02), (XF - 0.02, -0.17),
             (XF - 0.135, -0.17), (XF - 0.135, -0.02), (XF - 0.15, -0.02)])
    items.append((ch, dict(fill="#d9d6cf", lw="s")))
    items.append((R(XF - 0.14, -0.035, XF - 0.022, -0.02), S_SS))
    # ---------------------------------------------------------------- structure (RC)
    raft = R(5.65, raft_b, xb, sB)
    wallB = R(XF, sB, XC1, sG)
    slabG = R(XC1, M.slab_bot("G"), xb, sG)
    beamU = R(XC0, d_head, XC1, M.slab_bot("U"))
    slabU = R(XC0, M.slab_bot("U"), xb, sU)
    beamR = R(XC0, w_head, XC1, M.slab_bot("R"))
    slabR = R(XC0, M.slab_bot("R"), xb, sR)
    parapet = R(XC0, sR, XC1, par_top - 0.06)
    rc = U(raft, wallB, slabG, beamU, slabU, beamR, slabR, parapet)
    # ---------------------------------------------------------------- finishes inside
    for zt, x_from, z_floor in ((sB, XC1 + 0.015, LV["B"]), (sG, XC1, LV["G"]), (sU, XC1 + 0.015, LV["U"])):
        items.append((R(x_from, zt, xb, z_floor - 0.03), S_FILL))
        items.append((R(x_from, z_floor - 0.03, xb, z_floor - 0.02), S_MORTAR))
        items.append((R(x_from + 0.003, z_floor - 0.02, xb, z_floor), S_PORC))
    # interior plaster
    items.append((R(XC1, LV["B"], XC1 + 0.015, ceil_B), S_PLAST))
    items.append((R(XC1, LV["U"], XC1 + 0.015, w_sill - 0.02), S_PLAST))
    # ceilings
    for zc, xs in ((ceil_B, XC1 + 0.015), (ceil_G, XC1 + 0.12), (ceil_U, XC1 + 0.05)):
        items.append((R(xs, zc, xb, zc + 0.0125), S_GYPS))
        for xh in (xs + 0.45, xs + 0.95):
            items.append((LN([(xh, zc + 0.0125), (xh, zc + 0.12)]), dict(lw="xs")))
    # AC ducts in ceiling voids
    for (zc, zs_, x1_, x2_) in ((ceil_B, M.slab_bot("G"), 6.75, 7.30), (ceil_U, M.slab_bot("R"), 6.70, 7.35)):
        dz0, dz1 = zc + 0.03, min(zs_ - 0.03, zc + 0.22)
        items.append((R(x1_, dz0, x2_, dz1), dict(fill="#f6f6f6", lw="s")))
        items.append((LN([(x1_, dz0), (x2_, dz1)]), dict(lw="xxs")))
        items.append((LN([(x1_, dz1), (x2_, dz0)]), dict(lw="xxs")))
    # linear slot diffuser near the window (UF)
    items.append((R(XC1 + 0.07, ceil_U - 0.005, XC1 + 0.17, ceil_U + 0.0125), S_ALU))
    # curtain pocket at the GF door head
    items.append((LN([(XC1 + 0.12, ceil_G), (XC1 + 0.12, M.slab_bot("U"))]), dict(lw="s")))
    items.append((R(XC1 + 0.03, ceil_G + 0.02, XC1 + 0.06, ceil_G + 0.06), S_ALU))
    # ---------------------------------------------------------------- GF door (lift & slide) – cut
    # thermal sub-sill + threshold profile
    items.append((R(XC0 - 0.04, sG, XC1, -0.03), dict(fill="dx:xps", lw="xs")))
    items.append((R(XC0 - 0.04, -0.03, XC1, 0.0), S_ALU))
    items.append((R(XF - 0.008, -0.06, XC0 - 0.04, -0.05), S_MEMB))
    for (gx0, gx1) in ((XC0 + 0.005, XC0 + 0.075), (XC0 + 0.10, XC0 + 0.17)):
        items.append((R(gx0, 0.0, gx1, 0.11), S_ALU))
        items.append((R(gx0, d_head - 0.12, gx1, d_head), S_ALU))
        gm = (gx0 + gx1) / 2
        items.append((R(gm - 0.017, 0.11, gm + 0.017, d_head - 0.12), S_GLASS))
    items.append((R(XC0 - 0.02, d_head, XC1, d_head + 0.03), S_ALU))
    # ---------------------------------------------------------------- GF stone cladding above the door
    zst0, zst1 = d_head - 0.03, sU + 0.05
    items.append((R(XF + 0.05, d_head, XC0, zst1), S_WOOLV))
    items.append((R(XF, zst0, XF + 0.03, zst1), S_LIME))
    items.append((R(XF, zst0, XC0 - 0.02, zst0 + 0.03), S_LIME))            # soffit return
    # projection beyond: stone jamb edge of the door opening
    items.append((LN([(XF, 0.0), (XF, d_head)]), dict(lw="xs", color="#666")))
    items.append((LN([(XF + 0.03, 0.0), (XF + 0.03, d_head)]), dict(lw="xxs", color="#888")))
    # ---------------------------------------------------------------- UF wall: block + EIFS + window
    blockU = R(XC0, LV["U"] - M.FIN, XC1, w_sill - 0.03)
    z_e0 = zst1 + 0.012
    items.append((R(XF + 0.01, z_e0, XC0, w_sill - 0.04), S_EPS))
    items.append((R(XF, z_e0, XF + 0.01, w_sill - 0.04), S_PLAST))
    items.append((R(XF + 0.01, w_head + 0.02, XC0, par_top - 0.06), S_EPS))
    items.append((R(XF, w_head + 0.02, XF + 0.01, par_top - 0.06), S_PLAST))
    # stone / plaster transition: alu drip profile
    items.append((PG([(XF - 0.015, zst1), (XC0, zst1), (XC0, zst1 + 0.003), (XF - 0.012, zst1 + 0.003),
                      (XF - 0.012, zst1 + 0.012), (XF - 0.015, zst1 + 0.012)]), S_ALU))
    # window frame + DGU + sills
    items.append((R(XC0, w_sill, XC0 + 0.075, w_sill + 0.07), S_ALU))
    items.append((R(XC0, w_head - 0.07, XC0 + 0.075, w_head), S_ALU))
    items.append((R(XC0 + 0.02, w_sill + 0.07, XC0 + 0.052, w_head - 0.07), S_GLASS))
    items.append((PG([(XF - 0.04, w_sill - 0.035), (XC0 + 0.005, w_sill - 0.01), (XC0 + 0.005, w_sill),
                      (XF - 0.04, w_sill - 0.025), (XF - 0.04, w_sill - 0.06), (XF - 0.035, w_sill - 0.06)]), S_ALU))
    items.append((R(XC0 + 0.075, w_sill - 0.03, XC1 + 0.04, w_sill - 0.01), dict(fill="dx:lime", lw="s")))
    items.append((R(XF, w_head, XC0, w_head + 0.02), S_PLAST))
    items.append((R(XC0 - 0.002, w_sill - 0.03, XC0 + 0.004, w_sill), S_MEMB))
    # ---------------------------------------------------------------- roof build-up & parapet
    xr0 = XC1
    z = sR
    roof = [(0.06, dict(fill="pat:concrete", lw="xs")), (0.008, S_MEMB), (0.05, S_XPS), (0.003, dict(fill="#999", lw="xxs")),
            (0.05, S_GRAV)]
    zz = []
    for t, st in roof:
        items.append((R(xr0 + (0.03 if st is not roof[0][1] else 0.0), z, xb, z + t), st))
        zz.append((z, z + t))
        z += t
    # parapet inner: XPS 3 + membrane upturn + protection
    items.append((R(XC1, sR + 0.068, XC1 + 0.03, par_top - 0.20), S_XPS))
    items.append((R(XC1 + 0.03, sR + 0.06, XC1 + 0.038, par_top - 0.16), S_MEMB))
    items.append((PG([(XC1, sR + 0.06), (XC1 + 0.03, sR + 0.06), (XC1, sR + 0.03)]), dict(fill="pat:concrete", lw="xs")))
    items.append((R(XC1 + 0.03, par_top - 0.17, XC1 + 0.045, par_top - 0.15), S_SS))
    # coping (alu folded, sloped inward)
    cop = PG([(XF - 0.035, par_top - 0.045), (XF - 0.035, par_top - 0.005), (XC1 + 0.035, par_top - 0.020),
              (XC1 + 0.035, par_top - 0.075), (XC1 + 0.031, par_top - 0.075), (XC1 + 0.031, par_top - 0.024),
              (XF - 0.031, par_top - 0.009), (XF - 0.031, par_top - 0.045)])
    items.append((cop, S_ALU))
    items.append((R(XC0, par_top - 0.06, XC1, par_top - 0.04), dict(fill="dx:teak", lw="xxs")))
    # ---------------------------------------------------------------- louvres (beyond) + brackets (cut)
    if fin:
        items.append((R(fx0, fin["z0"], fx1, fin["z1"]), dict(fill="dx:aluwood", lw="s", color="#6b4a26", fop=0.65)))
    for zb in (fin["z0"] + 0.06, LV["U"] + 0.70, w_head + 0.15, par_top - 0.15):
        items.append((R(fx1 - 0.10, zb - 0.02, XC0 + 0.02, zb + 0.02), S_SS))
        items.append((R(XC0 - 0.004, zb - 0.06, XC0 + 0.004, zb + 0.06), S_SS))
        items.append((R(fx0 + 0.02, zb - 0.035, fx1 - 0.02, zb + 0.035), S_ALU))
    # ---------------------------------------------------------------- render
    fr.render(items)
    fr.render([(rc, S_RC), (blockU, S_BLOCK)])
    # stone anchors (dry fix) – small symbols
    for za in (zst0 + 0.10, zst1 - 0.08):
        sh.line(*fr.P(XF + 0.015, za), *fr.P(XC0 + 0.06, za), lw="m", color="#333")
    # drainage pipe
    px, pz = fr.P(5.38, raft_b + 0.12)
    sh.circle(px, pz, 0.055 * k, lw="m", fill="#fff")
    for a in range(0, 360, 45):
        import math
        sh.circle(px + 1.7 * math.cos(math.radians(a)), pz + 1.7 * math.sin(math.radians(a)), 0.25, lw="xxs", fill="#000")
    # ground line
    sh.line(*fr.P(xa, -0.02), *fr.P(XF - 0.15, -0.02), lw="m")
    fr.breaks(xa, xb, amp=1.4)
    # side break lines (interior crop)
    for z0_, z1_ in ((raft_b - 0.02, sB + 0.30), (M.slab_bot("G") - 0.05, LV["G"] + 0.05),
                     (M.slab_bot("U") - 0.05, LV["U"] + 0.05), (M.slab_bot("R") - 0.05, sR + 0.20)):
        breakline(sh, fr.X(xb), fr.Y(z1_), fr.X(xb), fr.Y(z0_), amp=1.1)

    # ---------------------------------------------------------------- annotations
    P = fr.P
    # level tags inside
    xl = fr.X(7.12)
    for zz_, txt in ((raft_b, fmt_lv(raft_b)), (LV["B"], fmt_lv(LV["B"])), (LV["G"], "±0.00"), (LV["U"], fmt_lv(LV["U"])),
                     (w_sill, fmt_lv(w_sill)), (sR, fmt_lv(sR)), (par_top, fmt_lv(par_top))):
        level_tag(sh, xl, fr.Y(zz_), txt, side="right", size=SZS, line=5)
    level_tag(sh, fr.X(5.15), fr.Y(-0.02), fmt_lv(-0.02), side="right", size=SZS, line=4, filled=False)
    # vertical dim chains (right of the crop)
    xd1 = fr.X(xb) + 5
    pos = [raft_b, sB, LV["B"], ceil_B, M.slab_bot("G"), sG, LV["G"], d_head, M.slab_bot("U"), sU, LV["U"], w_sill,
           w_head, M.slab_bot("R"), sR, par_top]
    txt = [f"{(b - a) * 100:.0f}" for a, b in zip(pos, pos[1:])]
    dim_chain_v(sh, [fr.Y(p) for p in pos], xd1, texts=txt, size=SZS, left=False, ext=fr.X(xb) + 1)
    xd2 = xd1 + 7
    pos2 = [LV["B"], LV["G"], LV["U"], LV["R"]]
    dim_chain_v(sh, [fr.Y(p) for p in pos2], xd2, texts=[f"{(b - a) * 100:.0f}" for a, b in zip(pos2, pos2[1:])],
                size=SZS, left=False)
    # horizontal dims (top)
    yt = fr.Y(par_top + 0.12) - 3
    dim_chain_h(sh, [fr.X(fx0), fr.X(fx1), fr.X(XF), fr.X(XC0), fr.X(XC1)], yt,
                texts=[f"{(fx1 - fx0) * 100:.0f}", f"{(XF - fx1) * 100:.0f}", "10", "20"], size=SZS)
    # horizontal dims (bottom)
    yb_ = fr.Y(raft_b - 0.15) + 5
    dim_chain_h(sh, [fr.X(5.65), fr.X(XF), fr.X(XC1)], yb_, texts=["35", "30"], size=SZS)
    # callouts – exterior (left)
    xL = x0 + 63
    left = [
        (*P(XF + 0.05, par_top - 0.012), ["קופינג אלומיניום 2 מ\"מ, שיפוע", "פנימה + אף מים (פרט 1)"]),
        (*P(fx0 + 0.05, par_top - 0.45), ["רפפות אלומיניום 50×200 @180", "גמר דמוי עץ (מראה כורכר)"]),
        (*P(XF - 0.10, w_head + 0.15), ["זרוע נירוסטה 316 + רפידה", "תרמית, עוגן כימי M10"]),
        (*P(XF + 0.006, 6.05), ["טיח תרמי לבן (EIFS): בידוד", "צמר סלעים 9 + רשת + טיח"]),
        (*P(XC0 + 0.036, w_sill + 0.20), ["חלון אלומיניום תרמי AL-23", "זיגוג בידודי כפול"]),
        (*P(XF - 0.03, w_sill - 0.04), ["אדן אלומיניום עם אף מים"]),
        (*P(XF - 0.012, zst1 + 0.006), ["פרופיל מעבר אבן/טיח + אף מים"]),
        (*P(XF + 0.015, zst1 - 0.15), ["אבן גיר טבעית 3 ס\"מ, עיגון", "יבש בעוגני נירוסטה (פרט 4)"]),
        (*P(XF + 0.075, zst0 + 0.06), ["צמר סלעים 5 + מרווח אוויר 2", "(גשר תרמי בשפת התקרה)"]),
        (*P(XC0 + 0.04, 0.55), ["דלת הרמה-הזזה אלומיניום", "תרמית AL-05, סף שטוח"]),
        (*P(XF - 0.08, -0.03), ["תעלת ניקוז + רשת נירוסטה", "(פרט 3)"]),
        (*P(5.30, -0.035), ["ריצוף חוץ אבן כורכר 3 על", "מצע + משטח בטון 12"]),
        (*P(XF - 0.004, -0.90), ["יריעות ביטומניות 2×4 מ\"מ"]),
        (*P(XF - 0.018, -1.25), ["לוח הגנה וניקוז (ממברנה", "מחוררת HDPE)"]),
        (*P(5.30, -0.80), ["מילוי חוזר מהודק"]),
        (*P(XF - 0.15, -2.95), ["חצץ ניקוז עטוף בד גיאוטכני"]),
        (px, pz, ["צינור ניקוז מחורר Ø110"]),
        (*P(5.80, raft_b - 0.025), ["בטון רזה 5 + יריעה ביטומנית"]),
    ]
    left = [(a, b, c) for (a, b, c) in left]
    callout_col(sh, left, xL, side="left", y_min=y0 + 8, y_max=fr.Y(raft_b - 0.15), size=SZS, gap=1.3)
    # callouts – interior (right): build-up stacks
    xR = xd2 + 8
    xs_ = 7.30
    # roof stack
    stack_callout(sh, [P(xs_, (a + b) / 2) for a, b in reversed(zz)] + [P(xs_, sR - 0.15)], xR - 3, fr.Y(par_top + 0.05),
                  ["חצץ 5 / פאנלים PV על קונסטרוקציה", "יריעה גיאוטכנית", "בידוד XPS 5 ס\"מ", "יריעות ביטומניות 2×4 מ\"מ",
                   "בטון שיפועים מינ' 3 ס\"מ, 1.5%", "תקרת גג ב\"מ 30 ס\"מ"], size=SZS, lh=1.3)
    for (zf, ztop, name, yy, slab_txt) in ((LV["U"], sU, "U", None, "תקרה ב\"מ 30"), (LV["G"], sG, "G", None, "תקרה ב\"מ 30"),
                                           (LV["B"], sB, "B", None, "רפסודת ב\"מ 50")):
        tz = [P(xs_, zf - 0.01), P(xs_, zf - 0.025), P(xs_, zf - 0.065), P(xs_, ztop - 0.15)]
        ty = tz[0][1] - 9
        stack_callout(sh, tz, xR - 3, ty, ["ריצוף פורצלן 120/120 – 2", "דבק 1", "מילוי בטון קל/חול 7", slab_txt],
                      size=SZS, lh=1.3)
    right = [
        (*P(XC1 + 0.015, par_top - 0.25), ["הגבהת איטום 20+ מעל החצץ,", "XPS 3 + פס קיבוע נירוסטה"]),
        (*P(7.0, ceil_U + 0.15), ["תעלת מיזוג בחלל תקרה 30"]),
        (*P(7.25, ceil_U + 0.006), ["תקרה מונמכת גבס 1.25"]),
        (*P(XC1 + 0.02, w_sill - 0.02), ["אדן פנים אבן 2 ס\"מ"]),
        (*P(XC1 + 0.007, LV["U"] + 0.45), ["טיח פנים 1.5 + צבע"]),
        (*P(XC1 + 0.12, ceil_G + 0.06), ["כיס וילון + תקרת גבס"]),
        (*P(7.0, ceil_B + 0.12), ["תעלת מיזוג, תקרת גבס", "(חלל 20 ס\"מ)"]),
        (*P(XC1 + 0.007, -1.0), ["קיר מרתף ב\"מ 30 אטום", "+ טיח פנים"]),
    ]
    callout_col(sh, right, xR, side="right", size=SZS, gap=1.3)
    # detail references
    detail_ref(sh, *P(XF + 0.12, par_top - 0.08), 5.5, "1", SN, ang=-150)
    detail_ref(sh, *P(XF - 0.05, -0.02), 5.0, "3", SN, ang=140)
    detail_ref(sh, *P(XF + 0.02, zst1 - 0.25), 4.0, "4", SN, ang=-160)
    # room labels
    for zz_, lab in ((LV["U"] + 0.35, "רחצת הורים"), (LV["G"] + 0.35, "סלון"), (LV["B"] + 0.35, "קולנוע / חדר כושר")):
        sh.text(fr.X(6.95), fr.Y(zz_), lab, size=SZ, color="#555")
    sh.text(fr.X(5.25), fr.Y(LV["U"] + 0.20), "חוץ", size=SZ, color="#555")
    # title
    yt_ = yb_ + 18
    D.drawing_title(sh, x0 + w - 6, yt_, "חתך קיר – חזית מערבית", 'קנ"מ 1:20', width=92, size=6.0)
    sh.text(x0 + w - 6, yt_ + 11.5, f"(חתך ב-y={Y_CUT:.2f} דרך דלת AL-05 וחלון AL-23, מבט צפונה)", size=SZS,
            anchor="right", color="#444")
    legend(sh, x0 + 2, yt_ + 15, w - 4, y0 + h - (yt_ + 15))


def legend(sh, x, y, w, h):
    """material hatch legend"""
    mats = [("dx:rcd", "בטון מזוין"), ("dx:blk", "בלוק בטון"), ("dx:lime", "אבן גיר / כורכר"),
            ("dx:woolv", "צמר סלעים"), ("dx:eps", "בידוד EIFS"), ("dx:xps", "XPS"),
            ("dx:fill", "מילוי בטון קל"), ("pat:gravel", "חצץ"), ("pat:earth", "קרקע"),
            ("dx:alu", "אלומיניום"), ("dx:ss", "נירוסטה 316"), ("dx:glass", "זכוכית")]
    if h < 14:
        return
    sh.text(x + w - 2, y + 4, "מקרא חומרים:", size=2.4, anchor="right", weight=700)
    ncol = 4
    cw = (w - 4) / ncol
    for i, (f, n) in enumerate(mats):
        r_, c_ = divmod(i, ncol)
        xx = x + w - 2 - c_ * cw
        yy = y + 7 + r_ * 5.6
        if yy + 4 > y + h:
            break
        sh.rect(xx - 9, yy, 9, 4, lw="xs", fill=fill_ref(sh, f))
        sh.text(xx - 10.5, yy + 3.1, n, size=SZS, anchor="right")


# =========================================================================== #
#  DETAILS
# =========================================================================== #
def _frame_in(sh, cell, scale, xmin, xmax, zmin, zmax, frac=0.52, bands=None, top_pad=6, bot_pad=16, dx=0):
    """Frame placing the model window in the left part of the cell (callouts to the right)."""
    x, y, w, h = cell
    k = 1000.0 / scale
    hh = (sum(b - a for a, b in bands) * k + 5 * (len(bands) - 1)) if bands else (zmax - zmin) * k
    ww = (xmax - xmin) * k
    ox = x + 4 + max(0, (w * frac - ww) / 2) + dx
    avail = h - top_pad - bot_pad
    top = y + top_pad + max(0, (avail - hh) / 2)
    fr = Frame(sh, ox, 0, scale, x0=xmin, bands=bands or [(zmin, zmax)], clip=(xmin, xmax))
    fr.oy = top + (fr.bands[-1][1] - fr.offs[-1]) * k
    return fr


def det_parapet(sh, x, y, w, h):
    """1 – roof parapet & coping, louvre top fixing (1:10)."""
    LV = M.LV
    sR = M.slab_top("R")
    par_top = LV["R"] + 0.50
    win = _op("U", "AL-23")
    w_head = LV["U"] + (win.head if win else 2.7)
    xa, xb = 5.45, 6.85
    fr = _frame_in(sh, (x, y, w, h), 10, xa, xb, w_head - 0.12, par_top + 0.08, frac=0.55)
    it = []
    rc = U(R(XC0, w_head, XC1, M.slab_bot("R")), R(XC0, M.slab_bot("R"), xb, sR), R(XC0, sR, XC1, par_top - 0.06))
    it.append((R(XF + 0.01, w_head + 0.02, XC0, par_top - 0.06), S_EPS))
    it.append((R(XF, w_head + 0.02, XF + 0.01, par_top - 0.06), S_PLAST))
    it.append((R(XF, w_head, XC0, w_head + 0.02), S_PLAST))
    it.append((R(XC0, w_head - 0.07, XC0 + 0.075, w_head), S_ALU))
    it.append((R(XC0 + 0.02, w_head - 0.12, XC0 + 0.052, w_head - 0.07), S_GLASS))
    it.append((R(XC1 + 0.05, w_head, xb, w_head + 0.0125), S_GYPS))
    z = sR
    layers = [(0.06, dict(fill="pat:concrete", lw="xs")), (0.008, S_MEMB), (0.05, S_XPS), (0.003, dict(fill="#999", lw="xxs")),
              (0.05, S_GRAV)]
    zz = []
    for i, (t, st) in enumerate(layers):
        it.append((R(XC1 + (0.03 if i else 0.0), z, xb, z + t), st))
        zz.append((z, z + t))
        z += t
    it.append((R(XC1, sR + 0.068, XC1 + 0.03, par_top - 0.20), S_XPS))
    it.append((R(XC1 + 0.03, sR + 0.06, XC1 + 0.038, par_top - 0.16), S_MEMB))
    it.append((PG([(XC1, sR + 0.06), (XC1 + 0.03, sR + 0.06), (XC1, sR + 0.03)]), dict(fill="pat:concrete", lw="xs")))
    it.append((R(XC1 + 0.03, par_top - 0.17, XC1 + 0.045, par_top - 0.15), S_SS))
    it.append((R(XC1 + 0.038, par_top - 0.20, XC1 + 0.046, par_top - 0.08), dict(fill="#ddd", lw="xxs")))
    cop = PG([(XF - 0.035, par_top - 0.045), (XF - 0.035, par_top - 0.005), (XC1 + 0.035, par_top - 0.020),
              (XC1 + 0.035, par_top - 0.075), (XC1 + 0.031, par_top - 0.075), (XC1 + 0.031, par_top - 0.024),
              (XF - 0.031, par_top - 0.009), (XF - 0.031, par_top - 0.045)])
    it.append((R(XC0, par_top - 0.06, XC1, par_top - 0.04), dict(fill="dx:teak", lw="xxs")))
    it.append((cop, S_ALU))
    fin = next((f for f in M.FINS if f["axis"] == "y" and f["c"] < XF), None)
    fx0, fx1 = fin["c"] - fin["depth"] / 2, fin["c"] + fin["depth"] / 2
    it.append((R(fx0, w_head - 0.2, fx1, fin["z1"]), dict(fill="dx:aluwood", lw="s", color="#6b4a26", fop=0.6)))
    for zb in (w_head + 0.15, par_top - 0.15):
        it.append((R(fx1 - 0.10, zb - 0.02, XC0 + 0.02, zb + 0.02), S_SS))
        it.append((R(XC0 - 0.004, zb - 0.06, XC0 + 0.004, zb + 0.06), S_SS))
        it.append((R(fx0 + 0.02, zb - 0.035, fx1 - 0.02, zb + 0.035), S_ALU))
        it.append((R(XF - 0.002, zb - 0.03, XF + 0.008, zb + 0.03), dict(fill="#555", lw="xxs")))
    fr.render(it)
    fr.render([(rc, S_RC)])
    for zb in (w_head + 0.15, par_top - 0.15):
        sh.line(*fr.P(XC0, zb), *fr.P(XC0 + 0.10, zb), lw="m")
    breakline(sh, fr.X(xb), fr.Y(par_top - 0.25), fr.X(xb), fr.Y(w_head - 0.05), amp=1.2)
    breakline(sh, fr.X(xa) - 2, fr.Y(w_head - 0.12), fr.X(xb) + 2, fr.Y(w_head - 0.12), amp=1.2)
    P = fr.P
    # dims
    xd = fr.X(xb) + 4
    dim_chain_v(sh, [fr.Y(sR), fr.Y(zz[-1][1]), fr.Y(par_top)], xd,
                texts=[f"{(zz[-1][1] - sR) * 100:.0f}", f"{(par_top - zz[-1][1]) * 100:.0f}"], size=SZS, left=False,
                ext=fr.X(xb - 0.05))
    dim_chain_v(sh, [fr.Y(M.slab_bot("R")), fr.Y(sR)], xd, texts=["30"], size=SZS, left=False)
    dimh(sh, fr.X(XF), fr.X(XC1), fr.Y(par_top + 0.06) - 2, "30", ext=fr.Y(par_top), size=SZS)
    dimh(sh, fr.X(fx0), fr.X(fx1), fr.Y(par_top + 0.06) - 2, "20", ext=fr.Y(fin["z1"]), size=SZS)
    level_tag(sh, fr.X(6.55), fr.Y(par_top), fmt_lv(par_top), size=SZS, line=4)
    level_tag(sh, fr.X(6.55), fr.Y(sR), fmt_lv(sR), size=SZS, line=4)
    callout_col(sh, [
        (*P(XF + 0.02, par_top - 0.01), ["קופינג אלומיניום 2 מ\"מ צבוע", "בתנור, שיפוע 5% פנימה"]),
        (*P(XC1 + 0.033, par_top - 0.06), ["אף מים 3 ס\"מ משני הצדדים"]),
        (*P(XC0 + 0.05, par_top - 0.05), ["משטח עץ מוגן לקיבוע הקופינג"]),
        (*P(XC1 + 0.042, par_top - 0.16), ["פס קיבוע נירוסטה + מסטיק"]),
        (*P(XC1 + 0.034, sR + 0.22), ["הגבהת יריעות ≥20 מעל החצץ"]),
        (*P(XC1 + 0.015, sR + 0.30), ["XPS 3 ס\"מ על פנים המעקה"]),
        (*P(6.60, zz[4][0] + 0.03), ["חצץ שטוף 5 / פאנלים PV"]),
        (*P(6.66, zz[2][0] + 0.025), ["XPS 5 + יריעה גיאוטכנית"]),
        (*P(6.72, zz[1][0] + 0.004), ["יריעות ביטומניות 2×4 מ\"מ"]),
        (*P(6.78, sR + 0.03), ["בטון שיפועים מינ' 3, 1.5%"]),
        (*P(6.60, sR - 0.15), ["תקרת גג ב\"מ 30"]),
        (*P(fx0 + 0.02, par_top - 0.40), ["רפפה 50×200 דמוי עץ"]),
        (*P(5.95, par_top - 0.15), ["זרוע נירוסטה 316 + רפידה"]),
        (*P(XF + 0.005, sR - 0.05), ["EIFS: צמר סלעים 9 + טיח"]),
    ], x + w * 0.58 + 6, side="right", y_min=y + 5, y_max=y + h - 18, size=SZS, gap=1.0)
    detail_title(sh, x + w - 3, y + h - 7, "1", "מעקה גג וקופינג", 'קנ"מ 1:10', size=4.0)


def det_soffit(sh, x, y, w, h):
    """2 – cantilever edge: soffit with recessed linear light, drip, loggia deck & glass (1:5).
    Section along y through the UF cantilever end (y = Y_S_U), looking west; south on the left."""
    ys = M.Y_S_U                        # 16.00 façade line of the cantilever
    ye = ys + 0.10                      # slab edge (slab rect inset 10 cm)
    zt, zb = M.slab_top("U"), M.slab_bot("U")
    zf = M.LV["U"]
    xa, xb = ys - 0.10, ys + 0.50
    fr = _frame_in(sh, (x, y, w, h), 5, xa, xb, zb - 0.20, zf + 0.20, frac=0.56)
    it = []
    rc = R(ye, zb, xb, zt)
    # top: loggia deck on pedestals over membrane & slope screed
    it.append((PG([(ye, zt), (xb, zt), (xb, zt + 0.035), (ye, zt + 0.025)]), dict(fill="pat:screed", lw="xs")))
    it.append((PG([(ye, zt + 0.025), (xb, zt + 0.035), (xb, zt + 0.043), (ye, zt + 0.033)]), S_MEMB))
    for px_ in (ye + 0.20, ye + 0.38):
        it.append((R(px_ - 0.03, zt + 0.04, px_ + 0.03, zf - 0.065), dict(fill="#777", lw="xxs")))
    it.append((R(ye + 0.10, zf - 0.065, xb, zf - 0.025), S_TEAK))
    it.append((R(ye + 0.10, zf - 0.025, xb, zf), S_TEAK))
    # glass channel cast in the slab edge + glass 12+12
    chan = PG([(ye + 0.01, zt - 0.11), (ye + 0.09, zt - 0.11), (ye + 0.09, zt + 0.04), (ye + 0.083, zt + 0.04),
               (ye + 0.083, zt - 0.103), (ye + 0.017, zt - 0.103), (ye + 0.017, zt + 0.04), (ye + 0.01, zt + 0.04)])
    gl = R(ye + 0.0375, zt - 0.09, ye + 0.0625, zf + 0.30)
    # fascia: insulation band + white plaster + alu cap flashing with drip
    it.append((R(ys + 0.012, zb - 0.10, ye, zt + 0.04), S_EPS))
    it.append((R(ys, zb - 0.10, ys + 0.012, zt + 0.04), S_PLAST))
    cap = PG([(ys - 0.012, zt + 0.02), (ys - 0.012, zt + 0.05), (ye + 0.012, zt + 0.05), (ye + 0.012, zt + 0.045),
              (ys - 0.007, zt + 0.045), (ys - 0.007, zt + 0.02)])
    it.append((cap, S_ALU))
    # soffit: suspended cement board on alu frame, recessed LED, drip profile
    zc = zb - 0.10
    it.append((R(ys + 0.012, zc, xb, zc + 0.0125), dict(fill="dx:plast", lw="s")))
    it.append((R(ys + 0.012, zc - 0.004, xb, zc), S_PLAST))
    for hx in (ye + 0.12, ye + 0.33):
        it.append((R(hx - 0.004, zc + 0.0125, hx + 0.004, zb), S_ALU))
    it.append((R(ye + 0.06, zc + 0.0125, xb, zc + 0.04), dict(fill="none", lw="xs")))
    led_x0 = ye + 0.07
    led = PG([(led_x0, zc - 0.004), (led_x0 + 0.06, zc - 0.004), (led_x0 + 0.06, zc + 0.035), (led_x0, zc + 0.035)])
    it.append((led, S_ALU))
    it.append((R(led_x0 + 0.005, zc - 0.004, led_x0 + 0.055, zc + 0.002), dict(fill="#fffbe0", lw="xxs")))
    it.append((R(led_x0 + 0.02, zc + 0.012, led_x0 + 0.04, zc + 0.02), dict(fill="#ffd23f", lw="xxs")))
    drip = PG([(ys - 0.005, zc - 0.018), (ys + 0.003, zc - 0.018), (ys + 0.003, zc + 0.012), (ys + 0.03, zc + 0.012),
               (ys + 0.03, zc + 0.016), (ys - 0.005, zc + 0.016)])
    it.append((drip, S_ALU))
    fr.render(it)
    fr.render([(rc, S_RC), (chan, S_SS), (gl, S_GLASS), (R(ye + 0.017, zt - 0.103, ye + 0.083, zt - 0.09), S_RUB)])
    # light cone
    p0, p1, p2 = fr.P(led_x0 + 0.03, zc - 0.004), fr.P(led_x0 - 0.06, zb - 0.20), fr.P(led_x0 + 0.12, zb - 0.20)
    sh.polyline([p0, p1, p2], closed=True, lw="xxs", color="#e2b400", fill="#fff3b0", fop=0.5)
    breakline(sh, fr.X(xb), fr.Y(zf + 0.08), fr.X(xb), fr.Y(zb - 0.08), amp=1.2)
    breakline(sh, fr.X(ye + 0.0) - 2, fr.Y(zf + 0.20), fr.X(ye + 0.10) + 2, fr.Y(zf + 0.20), amp=1.0)
    P = fr.P
    dim_chain_v(sh, [fr.Y(zc), fr.Y(zb), fr.Y(zt), fr.Y(zf)], fr.X(xb) + 4,
                texts=[f"{(zb - zc) * 100:.0f}", "30", "10"], size=SZS, left=False, ext=fr.X(xb - 0.02))
    dimh(sh, fr.X(ys), fr.X(ye), fr.Y(zc) + 9, "10", ext=fr.Y(zc - 0.02), size=SZS, above=False)
    level_tag(sh, fr.X(ye + 0.30), fr.Y(zf), fmt_lv(zf), size=SZS, line=4)
    sh.text(fr.X(ys + 0.30), fr.Y(zb - 0.17), "מרפסת מקורה (חוץ)", size=SZS, color="#555")
    sh.text(fr.X(ys + 0.30), fr.Y(zf + 0.12), "לוג'יה", size=SZS, color="#555")
    callout_col(sh, [
        (*P(ye + 0.05, zf + 0.15), ["מעקה זכוכית 12+12, גובה 105"]),
        (*P(ye + 0.086, zt - 0.05), ["פרופיל U נירוסטה יצוק בשפה"]),
        (*P(ys + 0.0, zt + 0.048), ["כיסוי אלומיניום + אף מים"]),
        (*P(ye + 0.30, zf - 0.01), ["דק עץ טיק על פדסטלים"]),
        (*P(ye + 0.42, zt + 0.039), ["יריעת איטום + מדה בשיפוע"]),
        (*P(ye + 0.25, zt - 0.15), ["זיז תקרה ב\"מ 30"]),
        (*P(ys + 0.006, zb + 0.10), ["פס בידוד + טיח לבן"]),
        (*P(led_x0 + 0.03, zc + 0.016), ["פרופיל לד שקוע IP67 3000K"]),
        (*P(ye + 0.30, zc + 0.006), ["תקרת לוחות צמנטבורד 12.5", "+ טיח לבן, על פרופילי אלו'"]),
        (*P(ys - 0.001, zc - 0.012), ["פרופיל אף מים בשפת התקרה"]),
    ], x + w * 0.60 + 6, side="right", y_min=y + 5, y_max=y + h - 18, size=SZS, gap=1.2)
    detail_title(sh, x + w - 3, y + h - 7, "2", "שפת זיז ותקרת חוץ", 'קנ"מ 1:5', size=4.0)


def det_threshold(sh, x, y, w, h):
    """3 – lift & slide threshold flush to the exterior paving with drainage channel (1:5)."""
    sG = M.slab_top("G")
    xa, xb = XF - 0.32, XC1 + 0.26
    fr = _frame_in(sh, (x, y, w, h), 5, xa, xb, -0.36, 0.20, frac=0.62)
    it = []
    rc = U(R(XF, -0.36, XC1, sG), R(XC1, -0.36 + 0.06, xb, sG))
    # outside: base, RC 12, bed, paving + channel
    it.append((R(xa, -0.36, XF - 0.03, -0.20), dict(fill="pat:gravel", lw="xxs")))
    it.append((R(xa, -0.20, XF - 0.15, -0.08), S_RC))
    it.append((R(xa, -0.08, XF - 0.15, -0.05), S_MORTAR))
    it.append((R(xa, -0.05, XF - 0.155, -0.02), S_LIME))
    ch = PG([(XF - 0.15, -0.20), (XF - 0.008, -0.20), (XF - 0.008, -0.02), (XF - 0.02, -0.02), (XF - 0.02, -0.17),
             (XF - 0.135, -0.17), (XF - 0.135, -0.02), (XF - 0.15, -0.02)])
    it.append((ch, dict(fill="#d9d6cf", lw="s")))
    it.append((R(XF - 0.14, -0.035, XF - 0.022, -0.02), S_SS))
    for gx in range(6):
        xx = XF - 0.135 + 0.01 + gx * 0.02
        it.append((R(xx, -0.035, xx + 0.008, -0.02), dict(fill="#fff", lw="xxs")))
    # waterproofing: up the wall, under the sub-sill
    it.append((R(XF - 0.008, -0.36, XF, -0.06), S_MEMB))
    it.append((R(XF - 0.028, -0.36, XF - 0.008, -0.21), S_DRAIN))
    it.append((R(XF - 0.008, -0.06, XC0 + 0.10, -0.052), S_MEMB))
    # inside floor
    it.append((R(XC1, sG, xb, -0.03), S_FILL))
    it.append((R(XC1, -0.03, xb, -0.02), S_MORTAR))
    it.append((R(XC1 + 0.004, -0.02, xb, 0.0), S_PORC))
    # thermal sub-sill + threshold frame (thermally broken)
    it.append((R(XC0 - 0.04, -0.052, XC1, -0.03), dict(fill="dx:xps", lw="xs")))
    it.append((R(XF - 0.008, sG, XC0 - 0.04, -0.052), dict(fill="dx:xps", lw="xs")))
    frm = U(R(XC0 - 0.04, -0.03, XC1, -0.022), R(XC0 - 0.04, -0.022, XC0 - 0.032, -0.0),
            R(XC0 + 0.03, -0.022, XC0 + 0.04, 0.0), R(XC0 + 0.12, -0.022, XC0 + 0.13, 0.0), R(XC1 - 0.008, -0.022, XC1, 0.0))
    it.append((frm, S_ALU))
    it.append((R(XC0 + 0.04, -0.022, XC0 + 0.12, -0.016), dict(fill="#555", lw="xxs")))     # thermal break
    for (gx0, gx1) in ((XC0 - 0.025, XC0 + 0.025), (XC0 + 0.065, XC0 + 0.115)):
        it.append((R(gx0, 0.004, gx1, 0.10), S_ALU))
        gm = (gx0 + gx1) / 2
        it.append((R(gm - 0.016, 0.10, gm + 0.016, 0.20), S_GLASS))
        it.append((circle_poly(gm, 0.012, 0.008), S_SS))
    # brush seal
    it.append((R(XC0 + 0.03, 0.0, XC0 + 0.04, 0.004), S_RUB))
    fr.render(it)
    fr.render([(rc, S_RC)])
    breakline(sh, fr.X(xa) - 2, fr.Y(-0.36), fr.X(xb) + 2, fr.Y(-0.36), amp=1.2)
    breakline(sh, fr.X(xa) - 2, fr.Y(0.20), fr.X(xb) + 2, fr.Y(0.20), amp=1.2)
    # drainage arrows / slope
    sh.text(fr.X(xa + 0.08), fr.Y(-0.02) - 1.5, "1.5% ←", size=SZS)
    P = fr.P
    level_tag(sh, fr.X(XC1 + 0.12), fr.Y(0.0), "±0.00", size=SZS, line=4)
    level_tag(sh, fr.X(xa + 0.04), fr.Y(-0.02), "-0.02", size=SZS, line=4)
    dimv(sh, fr.Y(-0.02), fr.Y(0.0), fr.X(XF - 0.15) - 0.5, "2", size=SZS)
    dimh(sh, fr.X(XF - 0.15), fr.X(XF - 0.008), fr.Y(-0.36) + 5, "14", ext=fr.Y(-0.20), size=SZS, above=False)
    dimh(sh, fr.X(XC0 - 0.04), fr.X(XC1), fr.Y(-0.36) + 5, "24", ext=fr.Y(-0.052), size=SZS, above=False)
    callout_col(sh, [
        (*P(XC0 + 0.09, 0.15), ["כנפי הרמה-הזזה, זיגוג בידודי"]),
        (*P(XC0 + 0.09, 0.012), ["גלגלות נירוסטה על מסילה"]),
        (*P(XC0 + 0.08, -0.019), ["סף אלומיניום מבודד תרמית", "שטוח – ללא מדרגה בפנים"]),
        (*P(XC1 + 0.12, -0.01), ["ריצוף פורצלן 120/120"]),
        (*P(XC1 + 0.14, -0.07), ["מילוי בטון קל 7"]),
        (*P(XC0 - 0.02, -0.04), ["תת-סף בידודי קשיח (XPS)"]),
        (*P(XC0 + 0.06, -0.056), ["יריעת איטום מתחת לסף, עולה", "15 ס\"מ מעל מפלס החוץ"]),
        (*P(XF - 0.08, -0.028), ["תעלת ניקוז פולימר-בטון", "+ רשת חריצים נירוסטה 316"]),
        (*P(XF - 0.24, -0.035), ["אבן כורכר 3 על מצע 3"]),
        (*P(XF - 0.24, -0.15), ["משטח בטון 12 + מצע מהודק"]),
        (*P(XC1 - 0.10, -0.25), ["קיר מרתף ב\"מ 30 / תקרה"]),
    ], x + w * 0.66 + 4, side="right", y_min=y + 5, y_max=y + h - 18, size=SZS, gap=1.2)
    detail_title(sh, x + w - 3, y + h - 7, "3", "סף דלת הרמה-הזזה", 'קנ"מ 1:5', size=4.0)


def det_anchor(sh, x, y, w, h):
    """4 – natural limestone dry-fix anchor (vertical section at a horizontal joint) 1:5."""
    xa, xb = XF - 0.06, XC1 + 0.10
    zj = 0.0
    fr = _frame_in(sh, (x, y, w, h), 5, xa, xb, -0.26, 0.26, frac=0.52)
    it = []
    blk = R(XC0, -0.26, XC1, 0.26)
    it.append((R(XC1, -0.26, XC1 + 0.015, 0.26), S_PLAST))
    it.append((R(XF + 0.05, -0.26, XC0, 0.26), S_WOOLV))
    st_up = R(XF, zj + 0.003, XF + 0.03, 0.26)
    st_lo = R(XF, -0.26, XF + 0.03, zj - 0.003)
    it.append((st_up, S_LIME))
    it.append((st_lo, S_LIME))
    # anchor: SS316 bracket (vertical plate on block, horizontal arm into the joint) + pin
    plate = R(XC0 - 0.006, zj - 0.06, XC0, zj + 0.04)
    arm = R(XF + 0.012, zj - 0.003, XC0, zj + 0.003)
    it.append((R(XC0 - 0.012, zj - 0.06, XC0 - 0.006, zj + 0.04), dict(fill="#444", lw="xxs")))  # thermal pad
    it.append((U(plate, arm), S_SS))
    pin = R(XF + 0.013, zj - 0.03, XF + 0.017, zj + 0.03)
    it.append((pin, S_SS))
    it.append((R(XF + 0.011, zj + 0.003, XF + 0.019, zj + 0.035), dict(fill="#bbb", lw="xxs")))
    it.append((R(XF + 0.011, zj - 0.035, XF + 0.019, zj - 0.003), dict(fill="#bbb", lw="xxs")))
    # insulation dowel
    it.append((R(XF + 0.05, 0.15, XC0 + 0.05, 0.156), dict(fill="#999", lw="xxs")))
    it.append((R(XF + 0.048, 0.13, XF + 0.052, 0.176), dict(fill="#999", lw="xxs")))
    fr.render(it)
    fr.render([(blk, S_BLOCK)])
    # chemical anchor bolt
    sh.line(*fr.P(XC0 - 0.012, zj - 0.03), *fr.P(XC0 + 0.09, zj - 0.03), lw="l")
    sh.rect(fr.X(XC0 - 0.02), fr.Y(zj - 0.03) - 1.2, fr.L(0.008), 2.4, lw="xs", fill="#8e969e")
    for zz in (-0.26, 0.26):
        breakline(sh, fr.X(xa) - 2, fr.Y(zz), fr.X(xb) + 2, fr.Y(zz), amp=1.2)
    P = fr.P
    yb_ = fr.Y(-0.26) + 5
    dim_chain_h(sh, [fr.X(XF), fr.X(XF + 0.03), fr.X(XF + 0.05), fr.X(XC0), fr.X(XC1)], yb_,
                texts=["3", "2", "5", "20"], size=SZS)
    dimv(sh, fr.Y(zj - 0.003), fr.Y(zj + 0.003), fr.X(xa) - 2, None, size=SZS)
    sh.text(fr.X(xa) - 4, fr.Y(zj) + 0.7, "6 מ\"מ", size=SZS, anchor="right")
    callout_col(sh, [
        (*P(XF + 0.015, 0.20), ["אבן גיר טבעית 3 ס\"מ, גמר", "מסותת עדין, גוון כורכר חם"]),
        (*P(XF + 0.04, 0.10), ["מרווח אוויר מאוורר 2 ס\"מ"]),
        (*P(XF + 0.075, 0.20), ["צמר סלעים 5 ס\"מ, צפיפות 100"]),
        (*P(XF + 0.05, 0.153), ["דיבל בידוד"]),
        (*P(XF + 0.015, zj + 0.02), ["פין נירוסטה Ø5 בקדח", "באבן + אפוקסי גמיש"]),
        (*P(XF + 0.03, zj), ["מישק פתוח 6 מ\"מ"]),
        (*P(XC0 - 0.02, zj + 0.002), ["עוגן נירוסטה 316 מתכוונן"]),
        (*P(XC0 - 0.009, zj + 0.03), ["רפידה תרמית"]),
        (*P(XC0 + 0.05, zj - 0.03), ["בורג עיגון כימי M8"]),
        (*P(XC0 + 0.10, -0.15), ["בלוק בטון 20 (חלול)"]),
        (*P(XC1 + 0.007, -0.20), ["טיח פנים + צבע"]),
    ], x + w * 0.56 + 6, side="right", y_min=y + 5, y_max=y + h - 18, size=SZS, gap=1.2)
    detail_title(sh, x + w - 3, y + h - 7, "4", "עיגון יבש לחיפוי אבן", 'קנ"מ 1:5', size=4.0)


def det_patio(sh, x, y, w, h):
    """5 – sunken-patio retaining-wall top with glass balustrade (1:10)."""
    gard = M.GARDEN
    ztop = gard + 0.10                      # wall top (model) -0.05
    rail = next((r for r in M.RAILS if abs(r["z0"] - ztop) < 1e-6), None)
    hrail = rail["h"] if rail else 0.95
    # local x: 0 = patio-side face of the wall; garden at x<0? → garden left, patio right
    xw0, xw1 = -0.30, 0.0
    xa, xb = -0.75, 0.45
    bands = [(-0.85, 0.12), (ztop + hrail - 0.17, ztop + hrail + 0.06)]
    fr = _frame_in(sh, (x, y, w, h), 10, xa, xb, -0.85, ztop + hrail + 0.06, frac=0.55, bands=bands)
    it = []
    it.append((R(xa, -0.85, xw0 - 0.03, gard - 0.25), S_EARTHL))
    it.append((R(xa, gard - 0.25, xw0 - 0.03, gard), dict(fill="dx:sandx", lw="none", color="none")))
    it.append((R(xw0 - 0.25, -0.85, xw0 - 0.03, gard - 0.30), S_GRAV))
    it.append((R(xw0 - 0.008, -0.85, xw0, gard + 0.02), S_MEMB))
    it.append((R(xw0 - 0.028, -0.85, xw0 - 0.008, gard - 0.02), S_DRAIN))
    # coping stone 4 cm, kurkar cladding 3 cm on patio face
    cop = R(xw0 - 0.03, ztop - 0.04, xw1 + 0.035, ztop)
    it.append((R(xw1, -0.85, xw1 + 0.03, ztop - 0.045), S_LIME))
    it.append((R(xw1 + 0.03, -0.85, xw1 + 0.035, ztop - 0.045), dict(fill="#fff", lw="xxs")))
    # planting edge
    it.append((LN([(xa, gard), (xw0 - 0.03, gard)]), dict(lw="m")))
    # glass shoe (alu) recessed in the wall top
    shoe = PG([(-0.20, ztop - 0.13), (-0.10, ztop - 0.13), (-0.10, ztop + 0.005), (-0.11, ztop + 0.005),
               (-0.11, ztop - 0.12), (-0.19, ztop - 0.12), (-0.19, ztop + 0.005), (-0.20, ztop + 0.005)])
    gl = R(-0.1625, ztop - 0.11, -0.1375, ztop + hrail - 0.01)
    fr.render(it)
    wall = R(xw0, -0.85, xw1, ztop - 0.04)
    fr.render([(wall.difference(R(-0.21, ztop - 0.14, -0.09, ztop)), S_RC), (cop.difference(R(-0.20, ztop - 0.05, -0.10, ztop + 0.01)), S_LIME),
               (shoe, S_ALU), (gl, S_GLASS), (R(-0.19, ztop - 0.12, -0.11, ztop - 0.11), S_RUB),
               (PG([(-0.19, ztop - 0.01), (-0.1625, ztop - 0.01), (-0.1625, ztop - 0.08), (-0.19, ztop - 0.07)]), S_RUB),
               (PG([(-0.1375, ztop - 0.01), (-0.11, ztop - 0.01), (-0.11, ztop - 0.07), (-0.1375, ztop - 0.08)]), S_RUB),
               (ring(-0.15, ztop + hrail + 0.011, 0.021, 0.0025), S_SS),
               (R(-0.168, ztop + hrail - 0.015, -0.132, ztop + hrail - 0.004), S_SS)])
    fr.breaks(xa, xb, amp=1.2)
    breakline(sh, fr.X(xa) - 2, fr.Y(-0.85), fr.X(xb) + 2, fr.Y(-0.85), amp=1.2)
    P = fr.P
    xd = fr.X(xb) + 3
    dimv(sh, fr.Y(ztop), fr.Y(0.12), xd, None, size=SZS, left=False)
    dimv(sh, fr.Y(ztop + hrail - 0.17, 1), fr.Y(ztop + hrail + 0.021, 1), xd, None, size=SZS, left=False)
    sh.text(xd + 1.5, (fr.Y(0.12) + fr.Y(ztop + hrail - 0.17, 1)) / 2 + 1, f"{hrail * 100:.0f}", size=SZS,
            weight=700, anchor="left")
    dimv(sh, fr.Y(gard), fr.Y(ztop), fr.X(xa) + 2, "10", size=SZS)
    sh.text(fr.X(xa) + 4, (fr.Y(0.12) + fr.Y(ztop + hrail - 0.17, 1)) / 2 + 1,
            f"{(ztop + hrail - gard) * 100:.0f} מעל הגינה", size=SZS, anchor="left", color="#333")
    dimh(sh, fr.X(xw0), fr.X(xw1), fr.Y(-0.85) + 5, "30", ext=fr.Y(-0.80), size=SZS, above=False)
    level_tag(sh, fr.X(-0.62), fr.Y(gard), fmt_lv(gard), size=SZS, line=4)
    level_tag(sh, fr.X(0.15), fr.Y(ztop), fmt_lv(ztop), size=SZS, line=4)
    sh.text(fr.X(-0.52), fr.Y(-0.62), "גינה", size=SZ, color="#555")
    sh.text(fr.X(0.25), fr.Y(-0.50), "חלל הפטיו", size=SZ, color="#555")
    sh.text(fr.X(0.25), fr.Y(-0.50) + 3.0, f"(רצפה {ltr(fmt_lv(M.LV['B'] - 0.02))})", size=SZS, color="#555")
    callout_col(sh, [
        (*P(-0.15, ztop + hrail + 0.02, 1), ["מאחז יד נירוסטה 316 Ø42"]),
        (*P(-0.145, ztop + hrail - 0.10, 1), ["זכוכית מחוסמת שכבתית 12+12"]),
        (*P(-0.105, ztop - 0.03), ["פרופיל בסיס אלומיניום שקוע", "+ טריזי EPDM"]),
        (*P(-0.26, ztop - 0.02), ["קופינג אבן כורכר 4 ס\"מ"]),
        (*P(0.015, -0.35), ["חיפוי כורכר 3 בצד הפטיו"]),
        (*P(-0.15, -0.45), ["קיר תומך ב\"מ 30"]),
        (*P(xw0 - 0.004, -0.55), ["איטום ביטומני + לוח ניקוז"]),
        (*P(xw0 - 0.15, -0.70), ["חצץ ניקוז + צינור בתחתית"]),
        (*P(-0.55, gard - 0.10), ["אדמת גן + צמחייה"]),
    ], x + w * 0.58 + 6, side="right", y_min=y + 5, y_max=y + h - 18, size=SZS, gap=1.2)
    detail_title(sh, x + w - 3, y + h - 7, "5", "ראש קיר פטיו שקוע + מעקה", 'קנ"מ 1:10', size=4.0)


def det_pool(sh, x, y, w, h):
    """6 – deck-level overflow pool edge (1:10)."""
    P_ = M.POOL
    zw = P_["water"]
    zd = M.GARDEN                      # deck level
    xa, xb = -0.55, 0.85               # x<0: pool, 0 = inner face of pool wall
    fr = _frame_in(sh, (x, y, w, h), 10, xa, xb, -0.85, zd + 0.10, frac=0.58)
    it = []
    # water
    it.append((R(xa, -0.85, -0.012, zw), S_WATER))
    # pool wall RC 25 + overflow channel
    wallp = U(R(0.0, -0.85, 0.25, zd - 0.06), R(0.25, -0.85, 0.55, -0.55), R(0.55, -0.85, 0.75, zd - 0.06))
    chan_void = R(0.25, -0.55, 0.55, zd - 0.06)
    # tiles / mosaic + waterproofing (cementitious)
    it.append((R(-0.012, -0.85, 0.0, zd - 0.03), dict(fill="#9cc7d6", lw="xxs")))
    it.append((R(0.25, -0.55, 0.55, -0.542), dict(fill="#9cc7d6", lw="xxs")))
    it.append((R(0.242, -0.542, 0.25, zd - 0.06), dict(fill="#9cc7d6", lw="xxs")))
    it.append((R(0.55, -0.542, 0.558, zd - 0.06), dict(fill="#9cc7d6", lw="xxs")))
    # overflow lip stone (rounded), grating
    lip = PG([(-0.03, zd - 0.06), (0.25, zd - 0.06), (0.25, zd - 0.03), (0.0, zd - 0.025), (-0.02, zd - 0.03),
              (-0.03, zd - 0.04)])
    it.append((lip, S_LIME))
    it.append((R(0.25, zd - 0.03, 0.55, zd), dict(fill="#e8e8e8", lw="s")))
    for gx in range(10):
        xx = 0.26 + gx * 0.03
        it.append((R(xx, zd - 0.03, xx + 0.012, zd), dict(fill="#fff", lw="xxs")))
    # deck: stone on bed on slab on compacted fill
    it.append((R(0.75, -0.85, xb, -0.45), S_EARTHL))
    it.append((R(0.75, -0.45, xb, -0.20), dict(fill="pat:gravel", lw="xxs")))
    it.append((R(0.55, -0.20, xb, -0.20 + 0.0), dict(fill="none", lw="xxs")))
    it.append((R(0.75, -0.30, xb, zd - 0.06), S_RC))
    it.append((R(0.55, zd - 0.06, xb, zd - 0.03), S_MORTAR))
    it.append((R(0.555, zd - 0.03, xb, zd), S_LIME))
    # return pipe to the balance tank
    fr.render(it)
    fr.render([(wallp, S_RC)])
    px, pz = fr.P(0.40, -0.50)
    sh.circle(px, pz, fr.L(0.04), lw="m", fill="#fff")
    # water level line + waves
    sh.line(*fr.P(xa, zw), *fr.P(-0.012, zw), lw="s", color="#2b6c86")
    level_tag(sh, fr.X(-0.42), fr.Y(zw), f"מפלס מים {ltr(fmt_lv(zw))}", size=SZS, line=4)
    level_tag(sh, fr.X(0.70), fr.Y(zd), fmt_lv(zd), size=SZS, line=3)
    breakline(sh, fr.X(xa) - 2, fr.Y(-0.85), fr.X(xb) + 2, fr.Y(-0.85), amp=1.2)
    breakline(sh, fr.X(xb), fr.Y(zd + 0.04), fr.X(xb), fr.Y(-0.84), amp=1.1)
    P = fr.P
    dimh(sh, fr.X(0.0), fr.X(0.25), fr.Y(zd) - 6, "25", ext=fr.Y(zd), size=SZS)
    dimh(sh, fr.X(0.25), fr.X(0.55), fr.Y(zd) - 6, "30", ext=fr.Y(zd), size=SZS)
    dimv(sh, fr.Y(zw), fr.Y(zd), fr.X(-0.08), f"{(zd - zw) * 100:.0f}", size=SZS)
    sh.text(fr.X(-0.30), fr.Y(-0.55), "בריכה", size=SZ, color="#2b6c86")
    callout_col(sh, [
        (*P(0.40, zd - 0.01), ["רשת גלישה PP לבנה 30 ס\"מ"]),
        (*P(0.05, zd - 0.04), ["אבן שפה מעוגלת – שפת גלישה"]),
        (*P(0.70, zd - 0.015), ["דק אבן כורכר 3 על מצע"]),
        (*P(0.40, -0.30), ["תעלת גלישה ב\"מ מצופה פסיפס"]),
        (px, pz, ["ניקוז לבור איזון Ø110"]),
        (*P(-0.006, -0.30), ["פסיפס זכוכית + איטום צמנטי"]),
        (*P(0.12, -0.70), ["קיר בריכה ב\"מ 25 אטום (ב-40)"]),
        (*P(0.80, -0.25), ["משטח בטון 15 + מצע מהודק"]),
    ], x + w * 0.62 + 6, side="right", y_min=y + 5, y_max=y + h - 18, size=SZS, gap=1.2)
    detail_title(sh, x + w - 3, y + h - 7, "6", "שפת בריכה בגלישה", 'קנ"מ 1:10', size=4.0)
