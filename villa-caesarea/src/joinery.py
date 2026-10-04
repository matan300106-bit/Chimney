"""Sheet – bespoke kitchen island (joinery design): plan / elevations 1:25, section 1:10, details 1:2,
cutting & materials list.

The island size comes from model.FURN ('island'); everything else is parametric on L × D × H.
Local frame: u along the island length (west → east), v across (0 = seating side, D = work side), z up.
Builder: sheet_joinery(sh, box).
"""
from __future__ import annotations

import math

import model as M
from draw import View, drawing_title
from interior import (pat, tw, table, callout_column, code_tag, rrect, furn_g, island_layout, INK, C_BRASS,
                      C_UPH, C_LIGHT, C_GLASS)

T = 0.020          # stone thickness
APRON = 0.12       # seating-side mitred apron (visual thickness of the top)
WEDGE = 0.04       # work-side mitred edge
PL = 0.10          # plinth height
SUB = 0.018        # substrate (marine plywood)


def geom():
    fs = furn_g("island")
    if fs:
        g = island_layout(fs[0])
    else:
        class _F:
            w, d, h = 2.8, 1.1, 0.92
        g = island_layout(_F())
    L, D, H = g["L"], g["D"], g["H"]
    g.update(
        z_top0=H - T, z_sub0=H - T - SUB, z_apron=H - APRON, z_wedge=H - WEDGE,
        v_pan0=g["over"], v_pan1=g["over"] + g["panel"], v_back0=g["carc0"], v_back1=g["carc0"] + 0.018,
        v_front0=g["front"], v_front1=g["front"] + 0.019,
        v_plinth_s=g["over"] + 0.03, v_plinth_w=g["front"] + 0.019 - 0.079,
    )
    # drawer fronts per module (z ranges incl. J-profile lip gap of 22 mm)
    stack3 = [(PL + 0.003, 0.413), (0.431, 0.651), (0.669, 0.852)]
    stack2 = [(PL + 0.003, 0.473), (0.491, 0.852)]
    fronts = {}
    for name, a, b in g["mods"]:
        if name == "מדיח":
            fronts[name] = [(PL + 0.003, 0.852)]
        elif name == "כיור":
            fronts[name] = stack2
        else:
            fronts[name] = stack3
    g["fronts"] = fronts
    return g


# --------------------------------------------------------------------------- #
#  1:25 views
# --------------------------------------------------------------------------- #
def view_plan(sh, ox, oy, g):
    v = View(sh, ox, oy, 25)
    L, D = g["L"], g["D"]
    # stools (seating side)
    n = max(2, int((L - 0.3) / 0.65))
    for i in range(n):
        cu = L * (i + 0.5) / n
        v.circle(cu, -0.12, 0.2, lw="xs", fill=C_UPH, dash="1.2 0.6")
    v.rect(0, 0, L, D, fill=pat(sh, "ix_sint"), lw="l")
    for u0 in (0, L - T):
        v.rect(u0, 0, u0 + T, D, fill="#cdbb9b", lw="s")
    # mitre lines at the corners
    for (u0, u1) in ((0, T), (L, L - T)):
        v.line(u0, 0, u1, T, lw="xxs")
        v.line(u0, D, u1, D - T, lw="xxs")
    v.line(T, T, L - T, T, lw="xxs", color="#777")
    v.line(T, D - T, L - T, D - T, lw="xxs", color="#777")
    # hidden: fluted panel, carcass, module divisions
    for vv, col in ((g["v_pan0"], "#333"), (g["v_back0"], "#777"), (g["v_front1"], "#777")):
        v.line(T, vv, L - T, vv, lw="xxs", color=col, dash="1.4 0.7")
    for name, a, b in g["mods"][1:]:
        v.line(a, g["v_back0"], a, g["v_front1"], lw="xxs", color="#777", dash="1.4 0.7")
    vc = (g["v_back0"] + D) / 2 + 0.02
    for name, a, b in g["mods"]:
        cu = (a + b) / 2
        if name == "כיור":
            v.rect(cu - 0.36, vc - 0.21, cu + 0.36, vc + 0.21, fill="#fff", lw="s")
            v.rect(cu - 0.33, vc - 0.18, cu + 0.33, vc + 0.18, fill="none", lw="xxs", dash="1 0.5")
            v.circle(cu + 0.2, vc, 0.025, lw="xxs")
            v.circle(cu, vc + 0.28, 0.03, lw="xs", fill="#999")
        elif name == "כיריים":
            v.rect(cu - 0.39, vc - 0.26, cu + 0.39, vc + 0.26, fill="#2f2c2a", lw="s")
            v.rect(cu - 0.03, vc - 0.24, cu + 0.03, vc + 0.24, fill="#777", color="none")
            for du in (-0.2, 0.2):
                for dv in (-0.12, 0.12):
                    v.circle(cu + du, vc + dv, 0.09, lw="xxs", color="#cfcfcf")
    # section line A-A
    mod = next((m for m in g["mods"] if m[0] == "מגירות"), g["mods"][1])
    ua = (mod[1] + mod[2]) / 2
    for (y0, y1, s) in ((-0.42, -0.25, 1), (D + 0.25, D + 0.42, -1)):
        pass
    v.line(ua, -0.38, ua, D + 0.38, lw="m", dash="6 1.5 1 1.5")
    for vv in (-0.38, D + 0.38):
        px, py = v.P(ua, vv)
        sh.line(px, py, px - 4, py, lw="m")
        sh.path(f"M{px - 4.8},{py} l1.6,-0.9 l0,1.8 Z", lw="xxs", fill="#000")
        sh.text(px + 2.2, py + 1.0, "A", size=3.0, weight=700)
    # dims
    us = [0, L] + [m[1] for m in g["mods"]] + [g["mods"][-1][2]]
    v.dim_chain(us, 0, axis="x", at=D + 0.55, size=2.0)
    v.dim_chain([0, L], 0, axis="x", at=D + 0.85, size=2.0)
    v.dim_chain([0, g["v_pan0"], g["v_back0"], g["v_front1"], D], 0, axis="y", at=-0.30, size=2.0)
    v.dim_chain([0, D], 0, axis="y", at=-0.62, size=2.0)
    # labels
    for name, a, b in g["mods"]:
        px, py = v.P((a + b) / 2, g["v_back0"] + 0.09)
        sh.text(px, py + 0.7, name, size=2.0, color="#333")
    px, py = v.P(L / 2, 0.15)
    sh.text(px, py + 0.7, "צד ישיבה – תלייה 30", size=2.0, color="#333")
    return v, ua


def view_front(sh, ox, oy, g):
    """seating side (south) – looking north."""
    v = View(sh, ox, oy, 25)
    L, H = g["L"], g["H"]
    v.rect(T, PL, L - T, g["z_apron"], fill=pat(sh, "ix_flute"), lw="xs")
    v.rect(T, 0, L - T, PL, fill=pat(sh, "ix_brass"), lw="xs")
    v.line(T, PL, L - T, PL, lw="xxs")
    v.rect(T, g["z_apron"], L - T, H, fill=pat(sh, "ix_sint"), lw="s")
    for u0 in (0, L - T):
        v.rect(u0, 0, u0 + T, H, fill=pat(sh, "ix_sint"), lw="s")
    v.line(0, H, T, H - T, lw="xxs")
    v.line(L, H, L - T, H - T, lw="xxs")
    # stool silhouettes (dashed)
    n = max(2, int((L - 0.3) / 0.65))
    for i in range(n):
        cu = L * (i + 0.5) / n
        v.polyline([(cu - 0.2, 0.0), (cu - 0.16, 0.65), (cu + 0.16, 0.65), (cu + 0.2, 0.0)], lw="xxs", dash="1 0.6",
                   color="#777")
        v.line(cu - 0.2, 0.65, cu + 0.2, 0.65, lw="xs", dash="1 0.6", color="#777")
        v.line(cu - 0.17, 0.30, cu + 0.17, 0.30, lw="xxs", dash="1 0.6", color="#777")
    v.dim_chain([0, T, L - T, L], 0, axis="x", at=-0.22, size=2.0)
    v.dim_chain([0, PL, g["z_apron"], H], 0, axis="y", at=L + 0.18, size=2.0)
    return v


def view_back(sh, ox, oy, g):
    """work side (north) – looking south: u mirrored."""
    v = View(sh, ox, oy, 25)
    L, H, D = g["L"], g["H"], g["D"]
    X = lambda u: L - u
    v.rect(X(L - T), 0, X(T), PL, fill=pat(sh, "ix_brass"), lw="xs")
    for name, a, b in g["mods"]:
        for (z0, z1) in g["fronts"][name]:
            v.rect(X(b) + 0.0015, z0, X(a) - 0.0015, z1, fill=pat(sh, "ix_oak"), lw="xs")
            v.rect(X(b) + 0.0015, z1, X(a) - 0.0015, z1 + 0.015, fill=pat(sh, "ix_brass"), lw="xxs")
        if name == "כיור":
            cu = (a + b) / 2
            v.rect(X(cu + 0.36), H - T - 0.20, X(cu - 0.36), H - T, fill="none", lw="xxs", dash="1 0.5")
        if name == "כיריים":
            cu = (a + b) / 2
            v.rect(X(cu + 0.39), H - T - 0.06, X(cu - 0.39), H - T, fill="none", lw="xxs", dash="1 0.5")
            v.rect(X(cu + 0.12), 0.45, X(cu - 0.12), H - T - 0.06, fill="none", lw="xxs", dash="1 0.5")
    v.rect(X(L - T), g["z_wedge"], X(T), H, fill=pat(sh, "ix_sint"), lw="s")
    for u0 in (0, L - T):
        v.rect(X(u0 + T), 0, X(u0), H, fill=pat(sh, "ix_sint"), lw="s")
    xs = [0, L] + [X(m[1]) for m in g["mods"]] + [X(g["mods"][-1][2])]
    v.dim_chain(xs, 0, axis="x", at=-0.22, size=2.0)
    zs = [0, PL] + [z for f in g["fronts"]["מגירות" if "מגירות" in g["fronts"] else "כיור"] for z in f] + [g["z_wedge"], H]
    v.dim_chain([0, PL, g["z_wedge"], H], 0, axis="y", at=-0.18, size=2.0)
    return v


def view_side(sh, ox, oy, g):
    """east end – waterfall leg, looking west (v = 0 seating side at left)."""
    v = View(sh, ox, oy, 25)
    D, H = g["D"], g["H"]
    v.rect(0, 0, D, H, fill=pat(sh, "ix_sint"), lw="l")
    # book-matched veining
    for i, (a, b) in enumerate(((0.10, 0.25), (0.35, 0.55), (0.62, 0.80))):
        pts = [(D * 0.5 + (D * 0.48) * (j / 10) * (1 if a < 0.5 else -1) * 0 + 0.0, 0) for j in range(1)]
    for s in (-1, 1):
        for k0 in (0.18, 0.44, 0.71):
            pts = []
            for j in range(13):
                t = j / 12
                pts.append((D / 2 + s * (0.04 + t * 0.48), k0 * H + 0.12 * math.sin(t * 3 + k0 * 5) * H * 0.3 + t * 0.06))
            v.polyline(pts, lw="xxs", color="#b9a37f")
    v.line(D / 2, 0, D / 2, H, lw="xxs", color="#b9a37f", dash="2 1")
    v.line(0, H - T, T, H, lw="xxs")
    v.dim_chain([0, D], 0, axis="x", at=-0.22, size=2.0)
    v.dim_chain([0, H], 0, axis="y", at=D + 0.18, size=2.0)
    return v


# --------------------------------------------------------------------------- #
#  Section A-A 1:10
# --------------------------------------------------------------------------- #
def section_AA(sh, ox, oy, g, items_l, items_r):
    v = View(sh, ox, oy, 10)
    D, H = g["D"], g["H"]
    P = v.P
    # floor
    v.rect(-0.05, -0.06, D + 0.05, -0.009, fill=pat(sh, "ix_screed"), lw="xs")
    v.rect(-0.05, -0.009, D + 0.05, 0.0, fill="#e2d6c2", lw="s")
    # plinths with brass kick
    vs = g["v_plinth_s"]
    v.rect(vs, 0.004, vs + 0.016, PL - 0.003, fill=pat(sh, "ix_mdf"), lw="s")
    v.rect(vs - 0.0015, 0.004, vs, PL - 0.003, fill=C_BRASS, lw="xs")
    vw = g["v_plinth_w"]
    v.rect(vw - 0.016, 0.004, vw, PL - 0.003, fill=pat(sh, "ix_mdf"), lw="s")
    v.rect(vw, 0.004, vw + 0.0015, PL - 0.003, fill=C_BRASS, lw="xs")
    # levelling feet
    for vf in (g["v_back0"] + 0.06, vw - 0.06):
        v.rect(vf - 0.025, 0.0, vf + 0.025, 0.006, fill="#555", lw="xxs")
        v.rect(vf - 0.01, 0.006, vf + 0.01, PL - 0.012, fill="#888", lw="xxs")
        v.rect(vf - 0.02, PL - 0.012, vf + 0.02, PL, fill="#555", lw="xxs")
    # LED under carcass (work side)
    v.rect(vw + 0.01, PL - 0.014, vw + 0.026, PL, fill=pat(sh, "ix_alu"), lw="xs")
    for dv in (-0.02, 0.02, 0.06):
        v.line(vw + 0.018, PL - 0.014, vw + 0.018 + dv, 0.005, lw="xxs", color=C_LIGHT, dash="0.8 0.6")
    # carcass: bottom, back, top rail, side beyond
    b0, b1 = g["v_back0"], g["v_back1"]
    f0 = g["v_front0"]
    v.rect(b0, PL, f0, PL + 0.018, fill=pat(sh, "ix_mdf"), lw="m")
    v.rect(b0, PL + 0.018, b1, g["z_sub0"], fill=pat(sh, "ix_plyv"), lw="m")
    v.rect(f0 - 0.10, g["z_sub0"] - 0.018, f0 - 0.02, g["z_sub0"], fill=pat(sh, "ix_mdf"), lw="s")
    v.rect(b1, g["z_sub0"] - 0.018, b1 + 0.10, g["z_sub0"], fill=pat(sh, "ix_mdf"), lw="s")
    v.rect(b0, PL, f0, g["z_sub0"], fill="none", lw="xxs", color="#999")       # side panel beyond
    # drawers (module 'מגירות')
    fr = g["fronts"]["מגירות" if "מגירות" in g["fronts"] else "כיור"]
    for (z0, z1) in fr:
        v.rect(f0, z0, g["v_front1"], z1, fill=pat(sh, "ix_oak"), lw="m")
        # J-profile (simplified): web + lip
        v.polygon([(f0 - 0.0015, z1 - 0.03), (f0, z1 - 0.03), (f0, z1), (g["v_front1"], z1), (g["v_front1"], z1 + 0.015),
                   (g["v_front1"] - 0.0015, z1 + 0.015), (g["v_front1"] - 0.0015, z1 + 0.0015), (f0 - 0.0015, z1 + 0.0015)],
                  fill=C_BRASS, lw="xxs")
        # drawer box
        bx0, bx1 = b1 + 0.07, f0 - 0.015
        hb = min(0.20, (z1 - z0) - 0.06)
        zb = z0 + 0.03
        v.rect(bx0, zb, bx1, zb + 0.016, fill=pat(sh, "ix_mdf"), lw="s")
        v.rect(bx0, zb + 0.016, bx0 + 0.016, zb + hb, fill=pat(sh, "ix_mdf"), lw="s")
        v.rect(bx1 - 0.012, zb, bx1, zb + hb, fill="#9aa1a6", lw="s")
        v.rect(bx0, zb, bx1, zb + hb, fill="none", lw="xxs", color="#888", dash="1.2 0.6")
    # fluted panel + Z clips + soffit
    p0, p1 = g["v_pan0"], g["v_pan1"]
    v.rect(p0, PL + 0.003, p0 + 0.018, g["z_apron"] - 0.005, fill=pat(sh, "ix_oak"), lw="m")
    v.rect(p0 + 0.018, PL + 0.003, p1, g["z_apron"] - 0.005, fill=pat(sh, "ix_mdf"), lw="s")
    for zc in (0.26, 0.62):
        v.polyline([(p1, zc), (p1 + 0.012, zc), (p1 + 0.012, zc - 0.02), (b0, zc - 0.02)], lw="s", color="#555")
        v.polyline([(p1, zc + 0.012), (p1 + 0.006, zc + 0.012), (p1 + 0.006, zc - 0.008)], lw="s", color="#555")
    v.rect(T, g["z_apron"], p1 + 0.02, g["z_apron"] + 0.012, fill=pat(sh, "ix_oak"), lw="s")
    # steel cantilever bar (seen)
    v.rect(T + 0.01, g["z_sub0"] - 0.06, b0 + 0.40, g["z_sub0"], fill="none", lw="xs", dash="2 0.8", color="#333")
    # substrate & stone
    v.rect(T, g["z_sub0"], D - T, g["z_top0"], fill=pat(sh, "ix_ply"), lw="s")
    v.polygon([(0, H), (D, H), (D - T, H - T), (T, H - T)], fill=pat(sh, "ix_trav"), lw="m")
    v.polygon([(0, H), (T, H - T), (T, g["z_apron"]), (0, g["z_apron"])], fill=pat(sh, "ix_trav"), lw="m")
    v.polygon([(D, H), (D, g["z_wedge"]), (D - T, g["z_wedge"]), (D - T, H - T)], fill=pat(sh, "ix_trav"), lw="m")
    v.line(0, H, T, H - T, lw="s", color="#6b5a3e")
    v.line(D, H, D - T, H - T, lw="s", color="#6b5a3e")
    # waterfall leg beyond
    v.rect(0, 0, D, g["z_apron"], fill="none", lw="xxs", color="#aaa", dash="3 1")
    # dims
    v.dim_chain([0, p0, b0, f0, D], 0, axis="x", at=-0.10, size=2.0)
    v.dim_chain([0, D], 0, axis="x", at=-0.16, size=2.0)
    v.dim_chain([0, PL, g["z_apron"], g["z_sub0"], H], 0, axis="y", at=-0.10, size=2.0)
    zs = [0, PL] + [z for f in fr for z in f] + [g["z_wedge"], H]
    v.dim_chain(zs, 0, axis="y", at=D + 0.10, size=2.0)
    # callouts
    items_l += [
        (*P(0.006, 0.86), ["אפרון אבן 12 ס\"מ, מיטר 45°", "SS-01 20 מ\"מ, אפוקסי בגוון"]),
        (*P(0.15, g["z_apron"] + 0.006), ["תקרת תלייה – MDF 12 + פורניר WD-01"]),
        (*P(0.15, g["z_sub0"] - 0.03), ["פס פלדה 8/60 לתמיכת התלייה, @60"]),
        (*P(p0 + 0.009, 0.45), ["פאנל אלון מעושן מחורץ WD-02 18 מ\"מ", "על גב MDF 12 (סה\"כ 30)"]),
        (*P(p1 + 0.006, 0.62), ["תפסני Z מאלומיניום – תלייה ופירוק"]),
        (*P(vs - 0.001, 0.05), ["סוקל שקוע 3 ס\"מ, פח פליז MT-01 1.2 מ\"מ"]),
    ]
    items_r += [
        (*P(D / 2, H - 0.01), ["משטח אבן סינטר SS-01 20 מ\"מ"]),
        (*P(0.6, g["z_sub0"] + 0.009), ["מצע דיקט ימי WBP 18 מ\"מ"]),
        (*P(D - 0.01, H - 0.02), ["קנט צד עבודה 4 ס\"מ במיטר"]),
        (*P(g["v_front1"] - 0.001, fr[-1][1] + 0.01), ["פרופיל J – אלומיניום אנודייז פליז"]),
        (*P(g["v_front0"] + 0.009, fr[1][0] + 0.08), ["חזית MDF 19 + פורניר אלון מעושן WD-01"]),
        (*P(g["v_front0"] - 0.15, fr[0][0] + 0.04), ["מגירה מתכתית, מסילות 600 טריקה שקטה"]),
        (*P(b0 + 0.009, 0.45), ["גב גוף – דיקט ליבנה 18 מ\"מ"]),
        (*P(0.6, PL + 0.009), ["תחתית גוף MDF-MR 18 + ציפוי HPL"]),
        (*P(vw + 0.018, PL - 0.007), ["פרופיל LED 2700K מתחת לגוף"]),
        (*P(vw - 0.06, 0.05), ["רגלי פילוס 100–130 מ\"מ"]),
    ]
    return v


# --------------------------------------------------------------------------- #
#  Details 1:2
# --------------------------------------------------------------------------- #
def _frame(sh, v, xa, xb, za, zb):
    px0, py0 = v.P(xa, zb)
    px1, py1 = v.P(xb, za)
    return px0, py0, px1 - px0, py1 - py0


def detail_mitre(sh, ox, oy, g, items):
    """waterfall leg / top mitre – section along the length near the west end."""
    v = View(sh, ox, oy, 2)
    H = g["H"]
    xa, xb, za, zb = -0.03, 0.13, 0.74, H + 0.015
    fx, fy, fw, fh = _frame(sh, v, xa, xb, za, zb)
    sh.begin_clip(fx, fy, fw, fh)
    leg = [(0, za - 0.1), (T, za - 0.1), (T, H - T), (0, H)]
    top = [(0, H), (xb + 0.1, H), (xb + 0.1, H - T), (T, H - T)]
    v.polygon(leg, fill=pat(sh, "ix_trav"), lw="l")
    v.polygon(top, fill=pat(sh, "ix_trav"), lw="l")
    v.line(0, H, T, H - T, lw="xl", color="#6b5a3e")
    # arris
    # stainless reinforcement angle bonded in the corner
    v.polygon([(T, H - T - 0.03), (T + 0.003, H - T - 0.03), (T + 0.003, H - T - 0.003), (T + 0.03, H - T - 0.003),
               (T + 0.03, H - T), (T, H - T)], fill=pat(sh, "ix_steel"), lw="xs")
    # substrate + carcass end panel
    gap = 0.005
    cs = T + gap
    v.rect(cs + 0.018, g["z_sub0"], xb + 0.1, g["z_top0"], fill=pat(sh, "ix_ply"), lw="s")
    v.rect(cs, za - 0.1, cs + 0.018, g["z_top0"], fill=pat(sh, "ix_mdf"), lw="s")
    v.rect(cs + 0.018, g["z_sub0"] - 0.018, cs + 0.118, g["z_sub0"], fill=pat(sh, "ix_mdf"), lw="s")
    for zz in (0.80, 0.86):
        v.rect(T, zz, cs, zz + 0.012, fill="#6b5a3e", color="none")
    # screw / insert
    v.rect(cs + 0.018, 0.83, cs + 0.05, 0.834, fill="#555", color="none")
    sh.end_group()
    sh.rect(fx, fy, fw, fh, lw="xxs", color="#999")
    v.dim_chain([0, T, cs, cs + 0.018], 0, axis="x", at=za + 0.01, size=2.0)
    v.dim_chain([g["z_top0"], H], 0, axis="y", at=xb - 0.01, size=2.0)
    items += [
        (*v.P(0.008, H - 0.006), ["מיטר 45°, הדבקת אפוקסי בגוון האבן,", "פאזה 1 מ\"מ בקצה"]),
        (*v.P(0.01, 0.78), ["רגל מפל – SS-01 20 מ\"מ"]),
        (*v.P(T + 0.002, H - T - 0.02), ["זווית נירוסטה 30/30/3 מודבקת"]),
        (*v.P(cs + 0.009, 0.77), ["דופן גוף MDF-MR 18"]),
        (*v.P(T + 0.0025, 0.806), ["נקודות דבק מבני, מרווח 5 מ\"מ"]),
        (*v.P(0.08, g["z_sub0"] + 0.009), ["מצע דיקט ימי 18"]),
    ]
    return v


def detail_j(sh, ox, oy, g, items):
    """J-profile handle – top drawer front under the work-side edge."""
    v = View(sh, ox, oy, 2)
    H, D = g["H"], g["D"]
    f0, f1 = g["v_front0"], g["v_front1"]
    zt = g["fronts"]["מגירות" if "מגירות" in g["fronts"] else "כיור"][-1][1]
    xa, xb, za, zb = D - 0.13, D + 0.02, zt - 0.075, H + 0.012
    fx, fy, fw, fh = _frame(sh, v, xa, xb, za, zb)
    sh.begin_clip(fx, fy, fw, fh)
    v.polygon([(xa - 0.1, H), (D, H), (D - T, H - T), (xa - 0.1, H - T)], fill=pat(sh, "ix_trav"), lw="l")
    v.polygon([(D, H), (D, g["z_wedge"]), (D - T, g["z_wedge"]), (D - T, H - T)], fill=pat(sh, "ix_trav"), lw="l")
    v.line(D, H, D - T, H - T, lw="xl", color="#6b5a3e")
    v.rect(xa - 0.1, g["z_sub0"], D - T, g["z_top0"], fill=pat(sh, "ix_ply"), lw="s")
    v.rect(f0 - 0.10, g["z_sub0"] - 0.018, f0 - 0.03, g["z_sub0"], fill=pat(sh, "ix_mdf"), lw="s")
    # front
    v.rect(f0, za - 0.1, f1, zt, fill=pat(sh, "ix_oak"), lw="l")
    # J-profile 1.5 mm: web on the inner face, over the top, lip up at the outer face, hook inwards
    t = 0.0015
    pts = [(f0 - t, zt - 0.03), (f0, zt - 0.03), (f0, zt), (f1 - t, zt), (f1 - t, zt + 0.0135), (f1 - 0.006, zt + 0.0135),
           (f1 - 0.006, zt + 0.015), (f1, zt + 0.015), (f1, zt + t * 0 - 0.0), (f1, zt - 0.0), (f1, zt + 0.0)]
    v.polygon([(f0 - t, zt - 0.03), (f0, zt - 0.03), (f0, zt), (f1 - t, zt), (f1 - t, zt + 0.0135),
               (f1 - 0.007, zt + 0.0135), (f1 - 0.007, zt + 0.015), (f1, zt + 0.015), (f1, zt + 0.0 - 0.0), (f1, zt - 0.0)]
              if False else
              [(f0 - t, zt - 0.03), (f0, zt - 0.03), (f0, zt - t), (f1, zt - t), (f1, zt + 0.015), (f1 - 0.008, zt + 0.015),
               (f1 - 0.008, zt + 0.0135), (f1 - t, zt + 0.0135), (f1 - t, zt), (f0 - t, zt)],
              fill=C_BRASS, lw="xs")
    # screws
    for zz in (zt - 0.02,):
        v.rect(f0 - 0.012, zz - 0.0015, f0 + 0.008, zz + 0.0015, fill="#444", color="none")
    # finger
    pts = []
    for i in range(13):
        a = math.radians(200 + i * 12)
        pts.append((f1 - 0.004 + 0.012 * math.cos(a) * 0.9 + 0.006, zt + 0.03 + 0.02 * math.sin(a)))
    v.polyline([(D + 0.03, zt + 0.06), (f1 + 0.004, zt + 0.035), (f1 - 0.005, zt + 0.02), (f1 - 0.004, zt + 0.0145)],
               lw="xs", color="#999", dash="1.2 0.6")
    sh.end_group()
    sh.rect(fx, fy, fw, fh, lw="xxs", color="#999")
    v.dim_chain([zt, zt + 0.015, g["z_wedge"], H], 0, axis="y", at=xa + 0.012, size=2.0)
    v.dim_chain([f0, f1, D], 0, axis="x", at=za + 0.008, size=2.0)
    items += [
        (*v.P(f1 - 0.004, zt + 0.014), ["פרופיל J אלומיניום 1.5 מ\"מ,", "אנודייז פליז מוברש MT-01"]),
        (*v.P(f0 + 0.009, zt - 0.05), ["חזית MDF 19 + פורניר WD-01"]),
        (*v.P(f0 - 0.006, zt - 0.02), ["הברגה נסתרת מגב החזית"]),
        (*v.P(D - 0.008, g["z_wedge"] + 0.01), ["קנט אבן 40 מ\"מ במיטר"]),
        (*v.P(f0 - 0.06, g["z_sub0"] - 0.009), ["פס עליון MDF-MR 18"]),
        (*v.P(D - 0.06, H - 0.01), ["SS-01 20 מ\"מ על דיקט ימי 18"]),
    ]
    return v


def detail_fluted(sh, ox, oy, g, items, plan_ox, plan_oy):
    """fluted panel fixing – vertical section + horizontal section of the flutes."""
    v = View(sh, ox, oy, 2)
    p0, p1, b0 = g["v_pan0"], g["v_pan1"], g["v_back0"]
    za, zb = g["z_apron"] - 0.135, g["z_apron"] + 0.03
    xa, xb = p0 - 0.035, b0 + 0.035
    fx, fy, fw, fh = _frame(sh, v, xa, xb, za, zb)
    sh.begin_clip(fx, fy, fw, fh)
    v.rect(xa - 0.1, g["z_apron"], p1 + 0.02, g["z_apron"] + 0.012, fill=pat(sh, "ix_oak"), lw="m")
    v.rect(xa - 0.1, g["z_apron"] + 0.012, b0 + 0.1, zb + 0.1, fill="#fff", color="none")
    v.rect(b0 - 0.0, za - 0.1, b0 + 0.018, zb + 0.1, fill=pat(sh, "ix_plyv"), lw="l")
    zt = g["z_apron"] - 0.005
    v.rect(p0, za - 0.1, p0 + 0.018, zt, fill=pat(sh, "ix_oakv"), lw="l")
    v.rect(p0 + 0.018, za - 0.1, p1, zt, fill=pat(sh, "ix_mdf"), lw="s")
    zc = g["z_apron"] - 0.07
    t = 0.0015
    alu = pat(sh, "ix_alu")
    # panel-side Z clip (hangs down)
    for r in ((p1, zc - 0.035, p1 + t, zc), (p1, zc - t, p1 + 0.011, zc), (p1 + 0.011 - t, zc - 0.012, p1 + 0.011, zc)):
        v.rect(*r, fill=alu, lw="xs")
    # carcass-side Z clip (hooks up)
    for r in ((b0 - t, zc - 0.03, b0, zc + 0.01), (p1 + 0.0125, zc - 0.0145, b0, zc - 0.0145 + t),
              (p1 + 0.0125, zc - 0.0145, p1 + 0.0125 + t, zc - 0.003)):
        v.rect(*r, fill=alu, lw="xs")
    v.rect(p1 - 0.008, zc - 0.0255, p1 + t, zc - 0.0235, fill="#444", color="none")
    v.rect(b0 - t, zc - 0.021, b0 + 0.010, zc - 0.019, fill="#444", color="none")
    sh.end_group()
    sh.rect(fx, fy, fw, fh, lw="xxs", color="#999")
    v.dim_chain([p0, p0 + 0.018, p1, b0], 0, axis="x", at=za + 0.008, size=2.0)
    v.dim_chain([zt, g["z_apron"]], 0, axis="y", at=xa + 0.006, size=2.0)
    items += [
        (*v.P(p0 + 0.009, za + 0.04), ["אלון מעושן מלא WD-02 18 מ\"מ,", "חריצים R6 @20"]),
        (*v.P(p0 + 0.024, za + 0.06), ["גב MDF-MR 12, הדבקה בלחץ"]),
        (*v.P(p1 + 0.012, zc - 0.014), ["תפסני Z אלומיניום (זוג), כל 60 ס\"מ"]),
        (*v.P(b0 + 0.009, za + 0.03), ["גב גוף – דיקט ליבנה 18"]),
        (*v.P(p0 + 0.01, zt + 0.0025), ["מישק צל 5 מ\"מ"]),
    ]
    # horizontal section of the flutes (plan) 1:2
    vp = View(sh, plan_ox, plan_oy, 2)
    w = 0.10
    pts = [(0, p0 + 0.018)]
    pitch, r = 0.02, 0.006
    u = 0.0
    pts = [(0, p1)]
    pts.append((0, p0))
    while u < w - 1e-9:
        c = u + pitch / 2
        pts.append((c - r, p0))
        for i in range(1, 12):
            a = math.pi * i / 12
            pts.append((c - r * math.cos(a), p0 + r * math.sin(a) * 0.9))
        pts.append((c + r, p0))
        u += pitch
    pts.append((w, p0))
    pts.append((w, p0 + 0.018))
    pts.append((0, p0 + 0.018))
    vp.polygon(pts[1:], fill=pat(sh, "ix_oak"), lw="s")
    vp.rect(0, p0 + 0.018, w, p1, fill=pat(sh, "ix_mdf"), lw="s")
    vp.dim_chain([0, 0.02, 0.04], 0, axis="x", at=p0 - 0.01, size=2.0)
    px, py = vp.P(w / 2, p1 + 0.012)
    sh.text(px, py, "חתך אופקי בחריצים", size=2.0, weight=600)
    return v


def detail_plinth(sh, ox, oy, g, items):
    v = View(sh, ox, oy, 2)
    f0, f1 = g["v_front0"], g["v_front1"]
    vw = g["v_plinth_w"]
    xa, xb, za, zb = vw - 0.10, g["D"] + 0.03, -0.035, 0.16
    fx, fy, fw, fh = _frame(sh, v, xa, xb, za, zb)
    sh.begin_clip(fx, fy, fw, fh)
    v.rect(xa - 0.1, -0.06, xb + 0.1, -0.009, fill=pat(sh, "ix_screed"), lw="s")
    v.rect(xa - 0.1, -0.009, xb + 0.1, 0.0, fill="#e2d6c2", lw="m")
    vf = vw - 0.05
    v.rect(vf - 0.025, 0.0, vf + 0.025, 0.006, fill="#555", lw="xs")
    v.rect(vf - 0.009, 0.006, vf + 0.009, PL - 0.012, fill="#999", lw="xs")
    for zz in [0.01 + i * 0.006 for i in range(12)]:
        v.line(vf - 0.009, zz, vf + 0.009, zz + 0.003, lw="xxs", color="#555")
    v.rect(vf - 0.022, PL - 0.012, vf + 0.022, PL, fill="#555", lw="xs")
    # plinth clip + plinth with brass face
    v.rect(vf + 0.009, 0.04, vw - 0.016, 0.046, fill="#777", color="none")
    v.rect(vw - 0.016, 0.004, vw, PL - 0.003, fill=pat(sh, "ix_mdf"), lw="m")
    v.rect(vw, 0.004, vw + 0.0012, PL - 0.003, fill=C_BRASS, lw="xs")
    v.rect(vw - 0.016, 0.0, vw + 0.0012, 0.004, fill="#333", color="none")
    # carcass bottom + front
    v.rect(xa - 0.1, PL, f0, PL + 0.018, fill=pat(sh, "ix_mdf"), lw="m")
    v.rect(f0, PL + 0.003, f1, zb + 0.1, fill=pat(sh, "ix_oak"), lw="m")
    # LED profile & light
    v.rect(vw + 0.008, PL - 0.016, vw + 0.024, PL, fill=pat(sh, "ix_alu"), lw="xs")
    v.rect(vw + 0.01, PL - 0.016, vw + 0.022, PL - 0.013, fill="#fff6dc", lw="xxs")
    for dv in (-0.01, 0.02, 0.05, 0.08):
        v.line(vw + 0.016, PL - 0.016, vw + 0.016 + dv, 0.001, lw="xxs", color=C_LIGHT, dash="0.8 0.6")
    sh.end_group()
    sh.rect(fx, fy, fw, fh, lw="xxs", color="#999")
    v.dim_chain([0, PL, PL + 0.018], 0, axis="y", at=xb - 0.008, size=2.0)
    v.dim_chain([vw, f0, f1], 0, axis="x", at=zb - 0.012, size=2.0)
    items += [
        (*v.P(vw + 0.0006, 0.07), ["סוקל MDF-MR 16 + פח פליז מוברש", "MT-01 1.2 מ\"מ, נשלף בתפסנים"]),
        (*v.P(vw + 0.016, PL - 0.008), ["פרופיל LED 15/15, 2700K, מפזר אופל"]),
        (*v.P(vf, 0.05), ["רגל פילוס מתכווננת 100–130 מ\"מ"]),
        (*v.P(xa + 0.03, PL + 0.009), ["תחתית גוף MDF-MR 18"]),
        (*v.P(f0 + 0.009, 0.13), ["חזית מגירה – מרווח 3 מ\"מ מעל הסוקל"]),
        (*v.P(xa + 0.03, -0.004), ["ריצוף פורצלן FL-01"]),
    ]
    return v


# --------------------------------------------------------------------------- #
#  Axonometric (not to scale)
# --------------------------------------------------------------------------- #
def axo(sh, ox, oy, s, g):
    L, D, H = g["L"], g["D"], g["H"]
    c = math.cos(math.radians(30))

    def P(u, v, z):
        return ox + (u - v) * c * s, oy - (u + v) * 0.5 * s - z * s

    def poly(pts, **kw):
        sh.polyline([P(*p) for p in pts], closed=True, **kw)

    # floor shadow
    poly([(-0.1, -0.15, 0), (L + 0.15, -0.15, 0), (L + 0.15, D + 0.1, 0), (-0.1, D + 0.1, 0)], color="none",
         fill="#e9e3d9")
    # fluted panel & brass plinth (recessed)
    p0 = g["v_pan0"]
    poly([(T, p0, PL), (L - T, p0, PL), (L - T, p0, g["z_apron"]), (T, p0, g["z_apron"])], fill=pat(sh, "ix_flute10"), lw="xs")
    poly([(T, p0 + 0.03, 0), (L - T, p0 + 0.03, 0), (L - T, p0 + 0.03, PL), (T, p0 + 0.03, PL)], fill=pat(sh, "ix_brass"), lw="xs")
    # soffit (dark, seen from below? no) – apron front
    poly([(T, 0, g["z_apron"]), (L - T, 0, g["z_apron"]), (L - T, 0, H), (T, 0, H)], fill=pat(sh, "ix_sint"), lw="s")
    # legs
    poly([(0, 0, 0), (0, D, 0), (0, D, H), (0, 0, H)], fill="#e6dccb", lw="s")
    poly([(0, 0, 0), (T, 0, 0), (T, 0, H), (0, 0, H)], fill="#d9ccb5", lw="s")
    poly([(L - T, 0, 0), (L, 0, 0), (L, 0, H), (L - T, 0, H)], fill="#d9ccb5", lw="s")
    # veining on the west leg
    for k0 in (0.25, 0.5, 0.75):
        pts = [P(0, D * t, H * (k0 + 0.08 * math.sin(t * 5 + k0 * 4))) for t in [i / 12 for i in range(13)]]
        sh.polyline(pts, lw="xxs", color="#b9a37f")
    # top
    poly([(0, 0, H), (L, 0, H), (L, D, H), (0, D, H)], fill="#f1e9dc", lw="s")
    vc = (g["v_back0"] + D) / 2 + 0.02
    for name, a, b in g["mods"]:
        cu = (a + b) / 2
        if name == "כיור":
            poly([(cu - 0.36, vc - 0.21, H), (cu + 0.36, vc - 0.21, H), (cu + 0.36, vc + 0.21, H), (cu - 0.36, vc + 0.21, H)],
                 fill="#fff", lw="xs")
            x, y = P(cu, vc + 0.30, H)
            sh.line(x, y, x, y - 0.25 * s, lw="m", color="#888")
            sh.line(x, y - 0.25 * s, x + 0.1 * s, y - 0.25 * s + 0.05 * s, lw="m", color="#888")
        elif name == "כיריים":
            poly([(cu - 0.39, vc - 0.26, H), (cu + 0.39, vc - 0.26, H), (cu + 0.39, vc + 0.26, H), (cu - 0.39, vc + 0.26, H)],
                 fill="#2f2c2a", lw="xs")
    # stools
    n = max(2, int((L - 0.3) / 0.65))
    for i in range(n):
        cu = L * (i + 0.5) / n
        cv = -0.22
        for (du, dv) in ((-0.15, -0.15), (0.15, -0.15), (0.15, 0.15), (-0.15, 0.15)):
            a = P(cu + du, cv + dv, 0)
            b = P(cu + du * 0.8, cv + dv * 0.8, 0.63)
            sh.line(*a, *b, lw="s", color="#5b4636")
        pts = [P(cu + 0.2 * math.cos(t), cv + 0.2 * math.sin(t), 0.65) for t in [k * math.pi / 12 for k in range(24)]]
        sh.polyline(pts, closed=True, lw="xs", fill=pat(sh, "ix_leather"))
        ring = [P(cu + 0.15 * math.cos(t), cv + 0.15 * math.sin(t), 0.25) for t in [k * math.pi / 12 for k in range(25)]]
        sh.polyline(ring, lw="xs", color=C_BRASS)


# --------------------------------------------------------------------------- #
#  Cutting list
# --------------------------------------------------------------------------- #
def cutting_rows(g):
    L, D, H = [round(x * 1000) for x in (g["L"], g["D"], g["H"])]
    t = round(T * 1000)
    inner = L - 2 * t
    carc_d = round((g["v_front0"] - g["v_back0"]) * 1000)
    carc_h = round((g["z_sub0"] - PL) * 1000)
    pan_h = round((g["z_apron"] - 0.005 - PL - 0.003) * 1000)
    n_fronts = sum(len(f) for f in g["fronts"].values())
    n_draw = sum(len(f) for n, f in g["fronts"].items() if n != "מדיח")
    n_sides = len([m for m in g["mods"] if m[0] != "מדיח"]) + 1
    rows = [
        ["1", "משטח עליון", "אבן סינטר SS-01", "20", f"{L}×{D}", "1", "קנטים במיטר 45°, פתחי CNC"],
        ["2", "רגלי מפל (Waterfall)", "אבן סינטר SS-01", "20", f"{H}×{D}", "2", "מיטר 45° לעליון, הדבקת אפוקסי"],
        ["3", "אפרון צד ישיבה", "אבן סינטר SS-01", "20", f"{inner}×{round(APRON * 1000) - t}", "1", "מיטר 45°, המשך ורידים"],
        ["4", "קנט צד עבודה", "אבן סינטר SS-01", "20", f"{inner}×{round(WEDGE * 1000) - t}", "1", "מיטר 45°"],
        ["5", "מצע למשטח", "דיקט ימי WBP", "18", f"{inner - 4}×{D - 40}", "1", "הדבקה+בורגי ריתום לגוף"],
        ["6", "דפנות גוף", "MDF-MR + HPL פנים", "18", f"{carc_h}×{carc_d}", f"{n_sides}", "קנט ABS 1 מ\"מ"],
        ["7", "תחתיות גוף", "MDF-MR + HPL", "18", f"רוחב מודול×{carc_d}", f"{n_sides - 1}", "לפי מודולים"],
        ["8", "גב גוף (צד ישיבה)", "דיקט ליבנה", "18", f"{inner // 2}×{carc_h}", "2", "חיבור בשגם במרכז"],
        ["9", "פסי חיזוק עליונים", "MDF-MR", "18", f"רוחב מודול×100", f"{2 * (n_sides - 1)}", "קדמי + אחורי"],
        ["10", "חזיתות מגירות / מדיח", "MDF 19 + פורניר WD-01", "19", "לפי חזית אחורית", f"{n_fronts}", "מישק 3 מ\"מ, שמן-לכה מט"],
        ["11", "פרופיל J", "אלומיניום אנודייז פליז", "1.5", "רוחב חזית×30", f"{n_fronts}", "MT-01, הברגה נסתרת"],
        ["12", "מגירות מתכת", "מערכת מגירות, טריקה שקטה", "—", "600", f"{n_draw}", "פתיחה מלאה, 70 ק\"ג"],
        ["13", "פאנל מחורץ", "אלון מעושן מלא WD-02", "18", f"{inner // 2}×{pan_h}", "2", "חריצים R6 @20, שמן מט"],
        ["14", "גב לפאנל המחורץ", "MDF-MR", "12", f"{inner // 2}×{pan_h}", "2", "הדבקה בלחץ"],
        ["15", "תקרת תלייה (סופיט)", "MDF-MR 12 + פורניר WD-01", "12", f"{inner}×{round(g['v_pan1'] * 1000) + 20 - t}", "1", "נשלף לתחזוקה"],
        ["16", "פסי פלדה לתלייה", "פלדה שטוחה מגולוונת", "8", "60×700", "4", "@600, מעוגנים בגוף"],
        ["17", "תפסני Z", "אלומיניום", "2", f"{inner - 100}", "2", "זוג פסים לפאנל"],
        ["18", "סוקל (2 צדדים)", "MDF-MR 16 + פליז MT-01 1.2", "16", f"{inner}×94", "2", "תפסני סוקל + רצועת איטום"],
        ["19", "פרופיל LED", "אלומיניום + מפזר אופל", "—", f"{inner - 100}", "1", "2700K, 6W/מ', ספק 24V"],
        ["20", "רגלי פילוס", "PP מחוזק, 100–130", "—", "—", "12", "עומס 150 ק\"ג/יח'"],
        ["21", "בטנת תא כיור", "HPL לבן עמיד מים", "0.8", "800×700", "1", "+ מגש איסוף מאלומיניום"],
    ]
    return rows


# --------------------------------------------------------------------------- #
#  Sheet
# --------------------------------------------------------------------------- #
def sheet_joinery(sh, box):
    bx, by, bw, bh = box
    g = geom()
    L, D, H = g["L"], g["D"], g["H"]
    k25 = 40.0
    # ---------------- row 1, left: 1:25 set (plan above front elevation, work side & end to the right)
    x_pl = bx + 30
    oy_pl = by + 8 + (0.95 + D) * k25
    vp, ua = view_plan(sh, x_pl, oy_pl, g)
    t_y = oy_pl + 0.6 * k25 + 6
    drawing_title(sh, x_pl + L * k25 + 4, t_y, "תכנית אי", 'קנ"מ 1:25', width=60, size=4.6)
    oy_fr = t_y + 20 + H * k25
    view_front(sh, x_pl, oy_fr, g)
    drawing_title(sh, x_pl + L * k25 + 4, oy_fr + 16, "חזית צד ישיבה (דרום)", 'קנ"מ 1:25', width=60, size=4.6)
    x2 = x_pl + L * k25 + 34
    oy_bk = oy_pl - 0.04 * k25
    view_back(sh, x2, oy_bk, g)
    drawing_title(sh, x2 + L * k25 + 4, t_y, "חזית צד עבודה (צפון)", 'קנ"מ 1:25', width=60, size=4.6)
    view_side(sh, x2 + 10, oy_fr, g)
    drawing_title(sh, x2 + L * k25 + 4, oy_fr + 16, "חזית קצה – רגל מפל", 'קנ"מ 1:25', width=60, size=4.6)
    right1 = x2 + L * k25 + 8

    # ---------------- row 1, right: section 1:10
    k10 = 100.0
    sx = bx + bw - 98 - D * k10
    s_oy = by + 12 + (H + 0.02) * k10
    il, ir = [], []
    section_AA(sh, sx, s_oy, g, il, ir)
    callout_column(sh, il, sx - 16, by + 8, s_oy, size=2.0, lh=2.5, gap=1.6, side="left", elbow=5)
    callout_column(sh, ir, sx + D * k10 + 18, by + 8, s_oy, size=2.0, lh=2.5, gap=1.2, side="right", elbow=5)
    drawing_title(sh, bx + bw, s_oy + 28, "חתך A-A דרך מודול המגירות", 'קנ"מ 1:10', width=95, size=5.0)
    # ---------------- row 1, middle: axonometric
    ax_l, ax_r = right1 + 6, sx - 16 - 92
    s_ax = min((ax_r - ax_l) / ((L + D + 0.3) * 0.866), 150 / ((L + D) * 0.5 + H + 0.4))
    ax_ox = ax_l + (D + 0.2) * 0.866 * s_ax
    ax_oy = by + 22 + (L + D) * 0.5 * s_ax + H * s_ax
    axo(sh, ax_ox, ax_oy, s_ax, g)
    sh.text((ax_l + ax_r) / 2, by + 10, "מבט איזומטרי – ללא קנ\"מ", size=3.6, weight=700)
    sh.line((ax_l + ax_r) / 2 - 28, by + 12, (ax_l + ax_r) / 2 + 28, by + 12, lw="s")
    row1_bot = max(oy_fr + 32, s_oy + 42)

    # ---------------- row 2: details 1:2
    cw = bw / 4
    k2 = 500.0
    y2 = row1_bot + 4
    sh.line(bx, y2 - 2, bx + bw, y2 - 2, lw="xxs", color="#bbb")
    ttl_y = y2 + 6 + 0.245 * k2 + 12
    # 1 mitre
    c0 = bx + 3 * cw
    items = []
    oxd = c0 + cw - 6 - 0.13 * k2
    oyd = y2 + 6 + (H + 0.015) * k2
    detail_mitre(sh, oxd, oyd, g, items)
    callout_column(sh, items, oxd - 0.03 * k2 - 6, y2 + 6, oyd - 0.74 * k2 + 4, size=2.0, lh=2.5, gap=1.2, side="left", elbow=4)
    drawing_title(sh, c0 + cw - 4, ttl_y, "פרט 1 – מיטר משטח/מפל", 'קנ"מ 1:2', width=72, size=4.4)
    # 2 J-profile
    c1 = bx + 2 * cw
    items = []
    zt = g["fronts"]["מגירות" if "מגירות" in g["fronts"] else "כיור"][-1][1]
    oxd = c1 + cw - 6 - (D + 0.02) * k2
    oyd = y2 + 6 + (H + 0.012) * k2
    detail_j(sh, oxd, oyd, g, items)
    callout_column(sh, items, oxd + (D - 0.13) * k2 - 14, y2 + 6, oyd - (zt - 0.075) * k2, size=2.0, lh=2.5, gap=1.2,
                   side="left", elbow=4)
    drawing_title(sh, c1 + cw - 4, ttl_y, "פרט 2 – ידית פרופיל J", 'קנ"מ 1:2', width=72, size=4.4)
    # 3 fluted panel
    c2 = bx + cw
    items = []
    oxd = c2 + cw - 6 - (g["v_back0"] + 0.035) * k2
    oyd = y2 + 6 + (g["z_apron"] + 0.03) * k2
    fb = oyd - (g["z_apron"] - 0.135) * k2
    detail_fluted(sh, oxd, oyd, g, items, c2 + 16, fb + 12 + g["v_pan1"] * k2)
    callout_column(sh, items, oxd + (g["v_pan0"] - 0.035) * k2 - 8, y2 + 6, fb - 4,
                   size=2.0, lh=2.5, gap=1.2, side="left", elbow=4)
    drawing_title(sh, c2 + cw - 4, ttl_y, "פרט 3 – קיבוע פאנל מחורץ", 'קנ"מ 1:2', width=72, size=4.4)
    # 4 plinth
    c3 = bx
    items = []
    oxd = c3 + cw - 6 - (D + 0.03) * k2
    oyd = y2 + 6 + 0.16 * k2
    detail_plinth(sh, oxd, oyd, g, items)
    callout_column(sh, items, oxd + (g["v_plinth_w"] - 0.10) * k2 - 6, y2 + 6, oyd + 0.035 * k2, size=2.0, lh=2.5, gap=1.2,
                   side="left", elbow=4)
    drawing_title(sh, c3 + cw - 4, ttl_y, "פרט 4 – סוקל, LED ורגלי פילוס", 'קנ"מ 1:2', width=72, size=4.4)
    for i in range(1, 4):
        sh.line(bx + i * cw, y2 + 2, bx + i * cw, ttl_y + 10, lw="xxs", color="#ddd")
    row2_bot = ttl_y + 14

    # ---------------- row 3: cutting list + axo + notes
    y3 = row2_bot + 2
    sh.line(bx, y3 - 2, bx + bw, y3 - 2, lw="xxs", color="#bbb")
    cols = [("מס'", 11), ("פריט", 58), ("חומר", 80), ("עובי", 15), ("מידות (מ\"מ)", 44), ("כמות", 14), ("הערות", 92)]
    W = sum(c[1] for c in cols)
    xr_t = bx + bw
    sh.text(xr_t, y3 + 4, "רשימת חיתוך וחומרים – אי מטבח", size=3.8, anchor="right", weight=700)
    sh.line(xr_t - 80, y3 + 5.8, xr_t, y3 + 5.8, lw="m")
    rows = cutting_rows(g)
    rh = min(7.4, (by + bh - (y3 + 9) - 10) / (len(rows) + 1))
    yb = table(sh, xr_t, y3 + 9, cols, rows, size=2.15, rh=rh, align=["c", "r", "r", "c", "c", "c", "r"])
    sh.text(xr_t, yb + 4, f"מידות כלליות: {round(L * 100)}×{round(D * 100)}×{round(H * 100)} ס\"מ (לפי המודל). "
            "מידות לייצור – לאחר מדידה באתר ואישור דוגמאות.", size=2.0, anchor="right", color="#444")
    left_w = xr_t - W - bx - 12
    # island material swatches
    from interior import PALETTE
    sw = [p for p in PALETTE if p[0] in ("SS-01", "WD-01", "WD-02", "MT-01", "LT-01")]
    sh.text(bx + left_w, y3 + 4, "חומרי האי", size=3.4, anchor="right", weight=700)
    sy = y3 + 10
    swc = left_w / len(sw)
    for i, (code, pn, name, spec, use, sup) in enumerate(sw):
        x0 = bx + left_w - (i + 1) * swc
        sh.rect(x0 + 2, sy, swc - 4, 22, lw="xs", fill=pat(sh, pn))
        sh.text(x0 + swc - 2, sy + 27, code, size=2.6, weight=700, anchor="right")
        sh.text(x0 + swc - 2, sy + 30.5, name, size=2.1, anchor="right")
        sh.text(x0 + swc - 2, sy + 33.8, spec, size=2.0, anchor="right", color="#555")
    notes = [
        "מפרט אביזרים וגמרים",
        "• כיור אינטגרלי תחתון 70/40 נירוסטה,",
        "   ברז נשלף פליז מוברש",
        "• כיריים אינדוקציה 80 ס\"מ + קולט אדים",
        "   משולב (Downdraft), מנוע בסוקל",
        "• מדיח אינטגרלי 60 ס\"מ, פתיחת לחיצה",
        "• 3 כסאות בר עור LT-01, ישיבה +65",
        "• אבן: אימפרגנציה נגד כתמים",
        "• עץ: שמן-לכה מט 10% (WD-01/02)",
        "• מתכת: פליז מוברש PVD (MT-01)",
        "",
        "הערות ייצור",
        "1. כל המידות במ\"מ אלא אם צוין.",
        "2. מיטר אבן – חיתוך CNC במפעל,",
        "   הרכבה באתר ע\"י מתקין מוסמך.",
        "3. פאנל מחורץ נשלף (Z) לגישה",
        "   לצנרת ולחשמל.",
        "4. התאמת ורידים (Book-match) בין",
        "   רגלי המפל והמשטח.",
    ]
    ny = sy + 46
    half = notes.index("")
    for col, chunk in enumerate((notes[:half], notes[half + 1:])):
        nx = bx + left_w - col * (left_w / 2)
        for i, t in enumerate(chunk):
            head = t in ("מפרט אביזרים וגמרים", "הערות ייצור")
            sh.text(nx, ny + i * 3.4, t, size=2.8 if head else 2.2, anchor="right", weight=700 if head else 400,
                    color="#333")
