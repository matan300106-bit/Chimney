"""Sheets 15 (stair sheet, 1:25 & 1:5) and 16 (wall section 1:20 & building details 1:5/1:10).

All geometry is derived from model.py (levels, stair runs, core walls, lift);
construction layers follow the BRIEF (slab 30 + finishes 10, ext. wall 30, etc.).
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

import draw as D
import model as M
from details_lib import (Frame, R, PG, LN, U, bubble, breakline, circle_poly, detail_ref, detail_title,
                         dim_chain_h, dim_chain_v, dimh, dimv, fill_ref, fmt_lv, leader, level_tag,
                         stack_callout, text_lines, tw, arrow_line, ring, ltr, callout_col)

SZ = 2.2          # standard annotation text (mm)
SZS = 2.0         # small text
GREY = "#555"
SN = ""
PROJ = dict(lw="xs", color="#444")        # projection lines
CUT = dict(lw="xl")                       # cut outline
FINE = dict(lw="s")

# material styles (fill + outline)
S_RC = dict(fill="dx:rcd", lw="xl")
S_RAFT = dict(fill="dx:rcd", lw="xl")
S_BLINDING = dict(fill="pat:concrete", lw="s")
S_OAK = dict(fill="pat:wood", lw="m")
S_FILL = dict(fill="dx:fill", lw="xs")
S_PORC = dict(fill="dx:porc", lw="s")
S_MORTAR = dict(fill="dx:mortar", lw="xxs")
S_EARTH = dict(fill="pat:earth", color="none")
S_GRAVEL = dict(fill="pat:gravel", lw="xxs")
S_MEMB = dict(fill="#111", lw="xxs")
S_GLASS = dict(fill="dx:glass", lw="s")
S_ALU = dict(fill="dx:alu", lw="s")
S_SS = dict(fill="dx:ss", lw="s")
S_GYPS = dict(fill="dx:gyps", lw="s")
S_BLOCK = dict(fill="dx:blk", lw="xl")
S_PLAST = dict(fill="dx:plast", lw="xs")
S_WOOLV = dict(fill="dx:woolv", lw="xs")
S_WOOL = dict(fill="dx:wool", lw="xs")
S_XPS = dict(fill="dx:xps", lw="xs")
S_EPS = dict(fill="dx:eps", lw="xs")
S_LIME = dict(fill="dx:lime", lw="m")
S_DRAIN = dict(fill="dx:drain", lw="xxs")


def _glass_proj(op=0.55):
    return dict(fill="dx:glass", lw="xs", color="#5b8fa3", fop=op)


def sheet_no(fn):
    """current sheet number of a builder (sheet list is edited by others)."""
    try:
        import sheets as S
        for no, _t, _s, path in S.SHEETS:
            if path.endswith(":" + fn):
                return no
    except Exception:
        pass
    return ""


# =========================================================================== #
#  STAIR GEOMETRY (from model)
# =========================================================================== #
C_NOSE = 0.03     # oak nosing overhang beyond RC riser face
T_PLATE = 0.18    # RC folded plate
T_OAK = 0.05      # oak tread
T_LAND = 0.20     # RC landing slab
HOLE_Y0 = 27.98   # slab-hole south edge (from model slab holes)
Y_WALL_N = M.ST["yn"]          # 31.70 north wall inner face
X_CUT = 13.75                  # section A-A through flight A
LAND_LIP = 31.84               # landing / slab lip at the curtain wall


def slab_hole(level):
    """stair hole rectangle (x0,y0,x1,y1) of the slab whose top is at `level`."""
    for sl in M.SLABS:
        if abs(sl.top - M.slab_top(level)) < 1e-6:
            for h in sl.holes:
                if h[0] <= M.ST["x0"] + 0.25 and h[2] >= M.ST["x1"] - 0.01:
                    return h
    return (M.ST["x0"], HOLE_Y0, M.ST["x1"], M.ST["yn"])


ISSUES = []


def _hole_y0():
    for s in M.SLABS:
        for h in s.holes:
            if abs(h[0] - M.ST["x0"]) < 1e-6:
                return h[1]
    return HOLE_Y0


def run_data(st):
    """Useful numbers of a stair run (model dict)."""
    t = st["t"]
    r = st["r"]
    yA = [st["yA0"] + (k - 1) * t for k in range(1, st["nA"] + 1)]   # riser k (1..nA) y (flight A, going north)
    yB = [M.ST["yl"] - (j - 1) * t for j in range(1, st["nB"] + 1)]  # riser j of flight B (going south)
    return t, r, yA, yB


def nosing_A(st, y):
    """flight-A nosing line height at y."""
    t, r, yA, _ = run_data(st)
    return st["z0"] + r + (y - yA[0]) / t * r


def nosing_B(st, y):
    """flight-B nosing line height at y (rises toward south)."""
    t, r, _, yB = run_data(st)
    return st["zl"] + r + (yB[0] - y) / t * r


def plateA_poly(st, lip):
    """RC folded plate of flight A + landing (y, z).

    Runs that start on the raft stand on it; runs that start at a slab edge spring
    from the slab with a haunch (slab bottom corner → plate soffit).
    """
    t, r, yA, _ = run_data(st)
    z0, zl, nA = st["z0"], st["zl"], st["nA"]
    zs = z0 - M.FIN                       # structural top of the floor
    c = C_NOSE
    hole = _hole_y0()
    on_raft = st["level"] == "B"
    y_start = yA[0] + c if on_raft else hole - 0.30
    top = [(y_start, zs), (yA[0] + c, zs), (yA[0] + c, z0 + r - T_OAK)]
    for k in range(1, nA):
        top.append((yA[k] + c, z0 + k * r - T_OAK))
        top.append((yA[k] + c, z0 + (k + 1) * r - T_OAK if k + 1 < nA else zl - T_OAK))
    top.append((lip, zl - T_OAK))
    bot = [(lip, zl - T_OAK - T_LAND), (yA[-1] + c + T_PLATE, zl - T_OAK - T_LAND)]
    corners = []
    for k in range(nA - 1, 0, -1):
        zb = z0 + k * r - T_OAK - T_PLATE
        corners.append((yA[k] + c + T_PLATE, zb))
        corners.append((yA[k - 1] + c + T_PLATE, zb))
    if on_raft:
        kept = [p for p in corners if p[1] >= z0 + 0.02]
        bot += kept
        bot.append((kept[-1][0], zs))
    else:
        kept = [p for p in corners if p[0] >= hole + 0.40]
        bot += kept
        bot += [(hole, M.slab_bot(st["level"])), (hole - 0.30, M.slab_bot(st["level"]))]
    return Polygon(top + bot).buffer(0)


def plateB_profile(st):
    """flight B (beyond the cut) – top step line, oak lines and underside (lines)."""
    t, r, _, yB = run_data(st)
    zl, z1, nB = st["zl"], st["z1"], st["nB"]
    c = C_NOSE
    top = [(yB[0] - c, zl - T_OAK)]
    oak = []
    for j in range(1, nB):
        top.append((yB[j - 1] - c, zl + j * r - T_OAK))
        top.append((yB[j] - c, zl + j * r - T_OAK))
        oak.append([(yB[j - 1], zl + j * r - T_OAK), (yB[j - 1], zl + j * r), (yB[j] - c, zl + j * r)])
    top.append((yB[-1] - c, z1 - M.FIN))
    bot = [(yB[0] - c - T_PLATE, zl - T_OAK - T_LAND)]
    for j in range(1, nB):
        zb = zl + j * r - T_OAK - T_PLATE
        bot.append((yB[j - 1] - c - T_PLATE, zb))
        bot.append((yB[j] - c - T_PLATE, zb))
    bot.append((yB[-1] - c - T_PLATE + 0.02, z1 - M.FIN - M.SLAB))
    return top, oak, bot


def headroom_report():
    """Minimum vertical clearance above the nosing lines of each flight (m)."""
    hole = _hole_y0()
    out = []
    levels_above = {"B": "G", "G": "U", "U": "R"}
    for i, st in enumerate(M.STAIRS):
        up = levels_above[st["level"]]
        slab_bot_above = M.slab_bot(up)
        nxt = M.STAIRS[i + 1] if i + 1 < len(M.STAIRS) else None
        t, r, yA, yB = run_data(st)
        # flight A
        mA = 9.9
        for y in [yA[0] + j * 0.01 for j in range(int((M.ST["yl"] - yA[0]) / 0.01) + 1)]:
            zn = nosing_A(st, y)
            if y < hole:
                above = slab_bot_above
            elif nxt:
                above = nosing_A(nxt, y) - T_OAK - T_PLATE - 0.12
            else:
                above = M.LV["RX"] - 0.35
            mA = min(mA, above - zn)
        mB = 9.9
        for y in [hole + j * 0.01 for j in range(int((M.ST["yl"] - hole) / 0.01) + 1)]:
            zn = nosing_B(st, y)
            if nxt:
                above = nosing_B(nxt, y) - T_OAK - T_PLATE - 0.12
            else:
                above = M.LV["RX"] - 0.35
            mB = min(mB, above - zn)
        out.append((st["level"], round(mA, 2), round(mB, 2)))
    return out


# =========================================================================== #
#  SHEET 15 – STAIRS
# =========================================================================== #
def sheet_stairs(sh: D.Sheet, box):
    global SN
    SN = sheet_no("sheet_stairs")
    bx, by, bw, bh = box
    sec_w = 300
    # ---- section A-A (left column)
    stair_section(sh, bx, by, sec_w)
    # ---- plans 2x2 (right), read right-to-left
    px0 = bx + sec_w + 6
    cw = (bx + bw - px0) / 2
    ch = 219
    for lvl, ci, ri in (("B", 0, 0), ("G", 1, 0), ("U", 0, 1), ("R", 1, 1)):
        stair_plan(sh, lvl, px0 + (1 - ci) * cw, by + ri * ch, cw, ch)
    # ---- details row
    dy = by + 2 * ch + 3
    dh = by + bh - dy
    dw = (bx + bw - px0) / 3
    detail_A(sh, px0 + 2 * dw, dy, dw, dh)
    detail_B(sh, px0 + dw, dy, dw, dh)
    detail_C(sh, px0, dy, dw, dh)
    # ---- handrail detail + notes under the section
    detail_D(sh, bx, by + 514, sec_w, bh - 514)


# --------------------------------------------------------------------------- #
#  section A-A
# --------------------------------------------------------------------------- #
def stair_section(sh, x0, y0, w):
    k = 40.0
    y_n = 32.45          # north crop (earth)
    y_s = 26.85          # south crop
    z_top, z_bot = 7.60, -4.22
    ox = x0 + 25
    oy = y0 + 6 + z_top * k
    fr = Frame(sh, ox, oy, 25, x0=y_n, flip=True, bands=[(z_bot, z_top)], clip=(y_s, y_n))
    hole = _hole_y0()
    LV = M.LV
    items, proj = [], []
    stB, stG, stU = M.STAIRS[0], M.STAIRS[1], M.STAIRS[2]
    # ---------------- earth / basement envelope (north)
    raft_t, raft_b = M.slab_top("B"), M.slab_top("B") - M.RAFT
    items.append((R(y_s, z_bot, y_n, raft_b - 0.05), S_EARTH))
    items.append((R(32.33, raft_b - 0.05, y_n, M.GARDEN), S_EARTH))
    items.append((R(32.03, raft_b, 32.33, M.GARDEN - 0.30), dict(fill="pat:gravel", lw="xxs")))
    items.append((R(32.03, M.GARDEN - 0.30, 32.33, M.GARDEN), dict(fill="pat:earth", lw="xxs")))
    items.append((LN([(32.0, M.GARDEN), (y_n, M.GARDEN)]), dict(lw="m")))
    # blinding + membrane + raft
    items.append((R(y_s, raft_b - 0.05, 32.40, raft_b), S_BLINDING))
    items.append((R(y_s, raft_b - 0.008, 32.35, raft_b), S_MEMB))
    wall_n = U(R(Y_WALL_N, raft_t, 32.0, M.slab_bot("G")), R(Y_WALL_N, M.slab_bot("G"), 32.0, M.slab_top("G")))
    rc_struct = [U(R(y_s, raft_b, 32.35, raft_t), wall_n)]
    items.append((R(32.0, raft_b, 32.008, M.GARDEN + 0.05), S_MEMB))
    items.append((R(32.008, raft_b, 32.03, M.GARDEN + 0.05), S_DRAIN))
    pipe_c = (32.20, raft_b + 0.10)
    # ---------------- floors (south part, y < hole)
    for lv in ("G", "U", "R"):
        st_, sb = M.slab_top(lv), M.slab_bot(lv)
        rc_struct.append(R(y_s, sb, hole, st_))
        if lv != "G":
            rc_struct.append(R(Y_WALL_N, sb, LAND_LIP, st_))
    yA_G = run_data(stG)[2][0]
    rxw = [wl for wl in M.walls_on("R") if wl.horiz and wl.kind == "ext" and wl.out == -1]
    rx_out = rxw[0].c - rxw[0].t / 2 if rxw else 27.0
    rx_in = rx_out + 0.30
    fin = [R(y_s, LV["B"] - M.FIN, Y_WALL_N, LV["B"] - 0.03),
           R(y_s, LV["G"] - M.FIN, yA_G + C_NOSE, LV["G"] - 0.03),
           R(y_s, LV["U"] - M.FIN, hole + C_NOSE, LV["U"] - 0.03),
           R(max(y_s, rx_in), LV["R"] - M.FIN, hole, LV["R"] - 0.03)]
    fin_p = [R(y_s, LV["B"] - 0.03, Y_WALL_N, LV["B"]),
             R(y_s, LV["G"] - 0.03, yA_G + C_NOSE, LV["G"]),
             R(y_s, LV["U"] - 0.03, hole + C_NOSE, LV["U"]),
             R(max(y_s, rx_in), LV["R"] - 0.03, hole, LV["R"])]
    items += [(g, S_FILL) for g in fin] + [(g, S_PORC) for g in fin_p]
    # roof build-up outside the roof exit + roof-exit south wall (if inside the crop)
    zr = M.slab_top("R")
    if rx_out > y_s:
        items.append((R(y_s, zr, rx_out, zr + 0.06), dict(fill="pat:concrete", lw="xs")))
        items.append((R(y_s, zr + 0.06, rx_out, zr + 0.068), S_MEMB))
        items.append((R(y_s, zr + 0.068, rx_out, zr + 0.118), S_XPS))
        items.append((R(y_s, zr + 0.118, rx_out, zr + 0.17), dict(fill="pat:gravel", lw="xs")))
    if rx_in > y_s:
        items.append((R(rx_out + 0.10, zr, rx_in, z_top + 1), S_BLOCK))
        items.append((R(rx_out + 0.02, zr + 0.17, rx_out + 0.10, z_top + 1), S_EPS))
        items.append((R(rx_out, zr + 0.17, rx_out + 0.02, z_top + 1), S_PLAST))
    cut_walls = []
    for wl in M.WALLS:
        if wl.horiz and wl.kind in ("int",) and wl.a0 <= X_CUT <= wl.a1 and y_s < wl.c < hole:
            nxt = {"B": "G", "G": "U", "U": "R"}.get(wl.level)
            if nxt:
                cut_walls.append((wl, R(wl.c - wl.t / 2, M.slab_top(wl.level), wl.c + wl.t / 2, M.slab_bot(nxt))))
    for wl, g in cut_walls:
        items.append((g, S_BLOCK))
    # ---------------- ceilings (gypsum) south part
    ceil_pts = []
    for zc in (M.LV["B"] + 2.90, M.LV["G"] + 3.10):
        yend = hole - 0.08
        items.append((R(y_s, zc, yend, zc + 0.0125), S_GYPS))
        items.append((LN([(yend, zc + 0.0125), (yend, zc + 0.10)]), dict(lw="xs")))
        for wl, g in cut_walls:
            pass
        ceil_pts.append(zc)
    # ---------------- stair runs (cut flight A + landings)
    plates, oak, land_fin = [], [], []
    for st in M.STAIRS:
        lip = Y_WALL_N if st["level"] == "B" else LAND_LIP
        plates.append(plateA_poly(st, lip))
        t, r, yA, yB = run_data(st)
        for kk in range(1, st["nA"]):
            zt = st["z0"] + kk * r
            oak.append(R(yA[kk - 1], zt - T_OAK, yA[kk] + C_NOSE, zt))
        land_fin.append(R(M.ST["yl"], st["zl"] - T_OAK, lip, st["zl"]))
    rc_all = unary_union(rc_struct + plates)
    # ---------------- projection: flight B, lift shaft, slab edges beyond
    for st in M.STAIRS:
        top, oakl, bot = plateB_profile(st)
        proj.append((LN(top), PROJ))
        for o in oakl:
            proj.append((LN(o), PROJ))
        proj.append((LN(bot), dict(lw="xs", color="#777")))
    proj.append((LN([(M.LIFT["y0"], M.LV["B"]), (M.LIFT["y0"], z_top + 1)]), dict(lw="xs", color="#777")))
    for lv in ("G", "U", "R"):
        proj.append((R(hole, M.slab_bot(lv), M.LIFT["y0"], M.LV[lv]), dict(fill="none", lw="xs", color="#777")))
    # east guard glass (x=15.50) – top at upper floor + 1.05
    glass_items = []
    for st in M.STAIRS:
        zt = st["z1"] + 1.05
        g = PG([(hole, zt), (M.ST["yl"], zt), (M.ST["yl"], nosing_B(st, M.ST["yl"]) - 0.30), (hole, st["z1"] - 0.40)])
        glass_items.append((g, dict(fill="#dceef5", lw="xxs", color="#7aa", fop=0.35)))
        glass_items.append((LN([(hole, zt), (M.ST["yl"], zt)]), dict(lw="s", color="#555")))
    # central spine glass per run: bottom on flight A, top = flight B nosing line + 0.90
    spines = []
    for st in M.STAIRS:
        t, r, yA, yB = run_data(st)
        ya, yb = max(hole, yA[0]), M.ST["yl"]
        g = PG([(ya, max(st["z0"], nosing_A(st, ya) - 0.32)), (yb, nosing_A(st, yb) - 0.32),
                (yb, nosing_B(st, yb) + 0.90), (ya, nosing_B(st, ya) + 0.90)])
        spines.append((st, g))
    spine_all = unary_union([g for _, g in spines])
    glass_items.append((spine_all, dict(fill="#cfe6ef", lw="xs", color="#6a9fb3", fop=0.30)))
    for st, g in spines:
        ya, yb = max(hole, st["yA0"]), M.ST["yl"]
        glass_items.append((LN([(ya, nosing_B(st, ya) + 0.90), (yb, nosing_B(st, yb) + 0.90)]), dict(lw="l", color="#222")))
    # ---------------- render order
    fr.render(items)
    fr.render(proj)
    fr.render(glass_items)
    fr.render([(rc_all, S_RC)])
    fr.render([(g, S_OAK) for g in oak + land_fin])
    # curtain wall (stair glazing)
    cw_y0, cw_y1 = 31.90, 31.97
    cw = [(R(cw_y0, M.LV["G"], cw_y1, z_top + 1), dict(fill="dx:glass", lw="s"))]
    for zt in (M.LV["G"], M.LV["U"] - 0.40, M.LV["R"] - 0.40):
        cw.append((R(31.86, zt - (0.10 if zt <= 0 else 0.06), 32.02, zt + 0.06), S_ALU))
    for lv in ("U", "R"):
        cw.append((R(LAND_LIP, M.slab_bot(lv), cw_y0, M.LV[lv]), dict(fill="dx:wool", lw="xs")))
    fr.render(cw)
    # R-level edge guard (cut, at y = hole): glass in side channel on the slab edge
    zr = M.LV["R"]
    fr.render([(R(hole + 0.035, M.slab_bot("R") + 0.06, hole + 0.06, z_top + 1), S_GLASS),
               (R(hole, M.slab_bot("R") + 0.04, hole + 0.08, M.slab_bot("R") + 0.20), S_SS)])
    # drainage pipe
    px, pz = fr.P(*pipe_c)
    sh.circle(px, pz, 0.05 * k, lw="m", fill="#fff")
    sh.circle(px, pz, 0.05 * k - 0.6, lw="xxs", dash="0.4 0.4")
    # wall handrail on the west wall (behind the cutting plane) – dashed
    for st in M.STAIRS:
        t, r, yA, yB = run_data(st)
        a, b = yA[0] - 0.30, M.ST["yl"]
        za = nosing_A(st, yA[0]) + 0.90
        sh.polyline([fr.P(a, za), fr.P(yA[0], za), fr.P(b, nosing_A(st, b) + 0.90)], lw="m", dash="2.2 0.8",
                    color="#333")
    # break lines
    breakline(sh, fr.X(y_n) - 2, fr.Y(z_top), fr.X(y_s) + 2, fr.Y(z_top), amp=1.6)
    for lv in ("G", "U", "R"):
        breakline(sh, fr.X(y_s), fr.Y(M.LV[lv] + 0.12), fr.X(y_s), fr.Y(M.slab_bot(lv) - 0.12), amp=1.2)
    breakline(sh, fr.X(y_s), fr.Y(raft_t + 0.12), fr.X(y_s), fr.Y(raft_b - 0.12), amp=1.2)

    # ------------------------------------------------------------------ annotations
    xl = fr.X(y_n) - 1.0
    lv_list = [(M.LV["B"], fmt_lv(M.LV["B"]), "ריצוף מרתף", 32.0), (stB["zl"], fmt_lv(stB["zl"], 3), "משטח ביניים", Y_WALL_N),
               (M.LV["G"], "±0.00", "ריצוף ק. קרקע", 31.86), (stG["zl"], fmt_lv(stG["zl"], 3), "משטח ביניים", 31.86),
               (M.LV["U"], fmt_lv(M.LV["U"]), "ריצוף קומה א'", 31.86), (stU["zl"], fmt_lv(stU["zl"], 3), "משטח ביניים", 31.86),
               (M.LV["R"], fmt_lv(M.LV["R"]), "ריצוף יציאה לגג", 31.86)]
    for z, s_, note, yfrom in lv_list:
        yy = fr.Y(z)
        level_tag(sh, xl - 8, yy, s_, side="left", size=2.2, line=0.5, note=note)
        sh.line(xl - 7, yy, fr.X(yfrom) - 0.5, yy, lw="xxs", color="#777", dash="0.6 0.6")
    level_tag(sh, xl - 8, fr.Y(raft_b), fmt_lv(raft_b), side="left", size=2.0, line=0.5, filled=False,
              note="תחתית רפסודה")
    level_tag(sh, fr.X(32.40), fr.Y(M.GARDEN), fmt_lv(M.GARDEN), side="right", size=2.0, line=3, filled=False)
    # ---- vertical dims (south side): risers per flight + floor to floor
    xd = fr.X(y_s) + 6.0
    for st in M.STAIRS:
        t, r, yA, yB = run_data(st)
        dim_chain_v(sh, [fr.Y(st["z0"]), fr.Y(st["zl"]), fr.Y(st["z1"])], xd,
                    texts=[f"{st['nA']}×{r * 100:.1f}={(st['zl'] - st['z0']) * 100:.1f}",
                           f"{st['nB']}×{r * 100:.1f}={(st['z1'] - st['zl']) * 100:.1f}"],
                    ext=fr.X(y_s) + 1, size=SZS)
    zs_ = [M.LV["B"], M.LV["G"], M.LV["U"], M.LV["R"]]
    dim_chain_v(sh, [fr.Y(z) for z in zs_], xd + 5.5, texts=[f"{(b - a) * 100:.0f}" for a, b in zip(zs_, zs_[1:])],
                size=SZS)
    # ---- horizontal dims at bottom
    yb1 = fr.Y(z_bot) + 5.0
    t, r, yA, yB = run_data(stB)
    dim_chain_h(sh, [fr.X(32.0), fr.X(Y_WALL_N), fr.X(M.ST["yl"]), fr.X(yA[0])], yb1,
                texts=["30", "120", f"{stB['nA'] - 1}×28={(stB['nA'] - 1) * 28}"], size=SZS)
    sh.text(fr.X(yA[0]) + 2, yb1 + 0.8, "מרתף, קומה א'", size=SZS, anchor="left", color=GREY)
    t, r, yA, yB = run_data(stG)
    yb2 = yb1 + 6.0
    dim_chain_h(sh, [fr.X(M.ST["yl"]), fr.X(yA[0])], yb2, texts=[f"{stG['nA'] - 1}×28={(stG['nA'] - 1) * 28}"],
                size=SZS)
    sh.text(fr.X(yA[0]) + 2, yb2 + 0.8, "קומת קרקע", size=SZS, anchor="left", color=GREY)
    # ---- headroom dims at the slab edges
    for st in M.STAIRS:
        up = {"B": "G", "G": "U", "U": "R"}[st["level"]]
        zn = nosing_A(st, hole)
        zsb = M.slab_bot(up)
        xh = fr.X(hole) + 2.2
        dimv(sh, fr.Y(zn), fr.Y(zsb), xh, None, size=SZS)
        tx, ty = xh + 2.6, (fr.Y(zn) + fr.Y(zsb)) / 2
        sh.add(f'<text x="{tx:.2f}" y="{ty:.2f}" font-family="{D.FONT}" font-size="{SZS}" text-anchor="middle" '
               f'transform="rotate(-90 {tx:.2f} {ty:.2f})">{D.esc("גובה חופשי " + ltr(f"{(zsb - zn) * 100:.0f} ≥ 210"))}</text>')
    for a, b in zip(M.STAIRS, M.STAIRS[1:]):
        za, zb = a["zl"], b["zl"] - T_OAK - T_LAND
        dimv(sh, fr.Y(za), fr.Y(zb), fr.X(31.15), f"{(zb - za) * 100:.0f}", size=SZS)
    # ---- 0.90 / 1.05 guard dims
    yq = 29.10
    zq = nosing_B(stG, yq)
    dimv(sh, fr.Y(zq), fr.Y(zq + 0.90), fr.X(yq), "90", size=SZS, left=False)
    dimv(sh, fr.Y(M.LV["U"]), fr.Y(M.LV["U"] + 1.05), fr.X(hole + 0.32), "105", size=SZS, left=False)
    zqa = nosing_A(stU, 29.4)
    dimv(sh, fr.Y(zqa), fr.Y(zqa + 0.90), fr.X(29.4), "90", size=SZS, left=False)
    # ---- detail references
    t, r, yA, yB = run_data(stG)
    detail_ref(sh, *fr.P(yA[4] + 0.02, stG["z0"] + 5 * stG["r"] - 0.04), 5.0, "A", SN, ang=200)
    t, r, yA, yB = run_data(stB)
    detail_ref(sh, *fr.P(yA[0] + 0.10, stB["z0"] + 0.05), 6.5, "C", SN, ang=160)
    detail_ref(sh, *fr.P(30.05, nosing_A(stB, 30.05) + 0.90), 3.6, "D", SN, ang=200)
    detail_ref(sh, *fr.P(hole + 0.05, M.LV["R"] - 0.12), 5.5, "B", SN, ang=-35)
    # ---- room labels
    for z, lab in ((M.LV["G"] + 1.6, "מבואה"), (M.LV["U"] + 1.6, "גלריה"), (M.LV["B"] + 1.6, "מבואה")):
        sh.text(fr.X(27.35), fr.Y(z), lab, size=SZ, color=GREY)
    sh.text(fr.X(27.65), fr.Y(M.LV["R"] + 0.35), "יציאה לגג", size=SZS, color=GREY)
    # ---- material callouts – right column
    tR = fr.X(y_s) + 18.5
    t, r, yA, yB = run_data(stU)
    P = fr.P
    right = [
        (*P(yA[1] + 0.14, stU["z0"] + 2 * stU["r"] - 0.025), ["מדרך עץ אלון מלא 5 ס\"מ", "חוטם 3 ס\"מ + פס לד (A)"]),
        (*P(yA[2] + 0.30, stU["z0"] + 2 * stU["r"] - 0.16), ["מדרגות ב\"מ מקופלות", "עובי 18 ס\"מ"]),
        (*P(27.55, M.LV["U"] - 0.20), ["תקרה ב\"מ 30 ס\"מ + ריצוף 10:", "מילוי 7, פורצלן 120/120"]),
        (*P(27.55, M.LV["G"] + 3.106), ["תקרה מונמכת גבס"]),
        (*P(28.45, nosing_B(stG, 28.45) + 0.90), ["מאחז יד נירוסטה 316 Ø42", "90 מעל קו החוטמים"]),
        (*P(28.75, nosing_B(stG, 28.75) + 0.45), ["קיר זכוכית מרכזי בין המהלכים", "מחוסמת שכבתית 12+12"]),
        (*P(28.30, M.LV["G"] + 1.05), ["מעקה זכוכית 105 בשפת התקרה", "פרופיל U נירוסטה (B)"]),
        (*P(28.05, M.LV["G"] - 0.30), ["חיבור מהלך לשפת התקרה", "(זיזון לפי מהנדס)"]),
        (*P(27.55, M.LV["B"] + 2.906), ["תקרה מונמכת גבס,", "חלל מיזוג 20 ס\"מ"]),
        (*P(27.40, M.LV["B"] + 1.0), ["קיר בלוק 12 (מבואת מרתף)"]),
        (*P(28.5, raft_t - 0.25), ["רפסודת ב\"מ 50 ס\"מ"]),
        (*P(28.9, raft_b - 0.03), ["בטון רזה 5 + יריעה ביטומנית"]),
    ]
    callout_col(sh, right, tR, side="right", y_min=y0 + 30, y_max=fr.Y(z_bot), size=SZS)
    # ---- left column (north)
    xL = fr.X(32.0) + 0.5
    left = [
        (*P(31.935, M.LV["G"] + 0.9), ["קיר מסך – זיגוג", "AL-08/34/35"]),
        (*P(30.9, stG["zl"] - 0.15), ["משטח ביניים ב\"מ 20", "+ פרקט אלון 5"]),
        (*P(32.004, -1.4), ["קיר דיפון ב\"מ 30,", "איטום 2×4 מ\"מ,", "לוח הגנה וניקוז"]),
    ]
    callout_col(sh, left, fr.X(y_n) - 1.5, side="left", size=SZS)
    callout_col(sh, [(*P(pipe_c[0], pipe_c[1]), ["צינור ניקוז", "מחורר Ø100"])], fr.X(y_n) - 1.5, side="left",
                size=SZS, y_max=fr.Y(raft_b) - 7)
    # title
    D.drawing_title(sh, x0 + w - 4, yb2 + 14, "חתך א-א – מדרגות", 'קנ"מ 1:25', width=88, size=6.0)


# --------------------------------------------------------------------------- #
#  stair plans 1:25
# --------------------------------------------------------------------------- #
def _wall_rect(w, ext=False):
    t = w.t / 2
    a0, a1 = (w.a0 - t, w.a1 + t) if ext else (w.a0, w.a1)
    if w.horiz:
        return a0, w.c - t, a1, w.c + t
    return w.c - t, a0, w.c + t, a1


def stair_plan(sh, lvl, cx, cy, cw, ch):
    k = 40.0
    xa, xb = 12.62, 17.62
    ya, yb = 27.10, 32.08
    pw, ph = (xb - xa) * k, (yb - ya) * k
    ox = cx + 2 - xa * k
    oy = cy + 2 + yb * k
    v = D.View(sh, ox, oy, 25)
    hole = _hole_y0()
    up = next((s for s in M.STAIRS if s["level"] == lvl), None)
    dn = next((s for s in M.STAIRS if abs(s["z1"] - M.LV[lvl]) < 1e-6), None)
    zc = M.LV[lvl] + 1.20
    sh.begin_clip(cx + 2, cy + 2, pw, ph)
    # floor tone
    v.rect(xa, ya, xb, yb, fill="#ffffff", color="none")
    hz = slab_hole(lvl) if lvl != "B" else None
    hup = slab_hole({"B": "G", "G": "U", "U": "R"}[lvl]) if lvl != "R" else None
    # slab hole of this floor (void) – light tone
    if hz:
        v.rect(hz[0], hz[1], hz[2], Y_WALL_N, fill="#f2f2f2", color="none")
    # ---------------- stair elements
    t = 0.28
    x0A, x1A = M.ST["x0"], M.ST["x0"] + M.ST["w"]
    x0B, x1B = x1A + M.ST["gap"], M.ST["x1"]
    yl, yn = M.ST["yl"], Y_WALL_N

    def treads(st, flight, style, from_k=1, to_k=None, dash=None, color="#000"):
        tt, r, yA, yB = run_data(st)
        if flight == "A":
            ks = range(1, st["nA"] + 1)
            for kk in ks:
                if kk < from_k or (to_k and kk > to_k):
                    continue
                y = yA[kk - 1]
                v.line(x0A, y, x1A, y, lw=style, dash=dash, color=color)
        else:
            for j in range(1, st["nB"] + 1):
                if j < from_k or (to_k and j > to_k):
                    continue
                y = yB[j - 1]
                v.line(x0B, y, x1B, y, lw=style, dash=dash, color=color)

    def flight_outline(y0_, y1_, xa_, xb_, dash=None, lw="m", color="#000"):
        v.line(xa_, y0_, xa_, y1_, lw=lw, dash=dash, color=color)
        v.line(xb_, y0_, xb_, y1_, lw=lw, dash=dash, color=color)

    if up:
        tt, r, yA, yB = run_data(up)
        kcut = int((zc - up["z0"]) / up["r"])          # last riser below the cut
        ycut = yA[kcut - 1] + 0.14
        # visible part of flight A (below cut)
        treads(up, "A", "s", 1, kcut)
        flight_outline(yA[0], ycut + 0.10, x0A, x1A)
        # numbers
        for kk in range(1, up["nA"]):
            y = yA[kk - 1] + t / 2
            col = "#000" if kk <= kcut else "#999"
            sh.text(*v.P(x0A + 0.22, y - 0.05), str(kk), size=SZS, color=col)
        # cut line (zig-zag)
        p1, p2 = v.P(x0A - 0.05, ycut - 0.12), v.P(x1A + 0.10, ycut + 0.18)
        sh.line(*p1, *p2, lw="m")
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        # walking line (up)
        wl = x0A + M.ST["w"] / 2 + 0.12
        arrow_line(sh, [v.P(wl, yA[0] + 0.05), v.P(wl, ycut - 0.05)], lw="s")
        sh.circle(*v.P(wl, yA[0] + 0.05), 0.6, lw="xs", fill="#000")
        sh.text(*v.P(wl + 0.0, yA[0] - 0.16), "עולה", size=SZ, weight=700)
        # continuation above the cut (dashed): rest of flight A, landing, flight B
        if lvl == "B":
            treads(up, "A", "xs", kcut + 1, None, dash="1.2 0.8", color="#555")
            flight_outline(ycut, yl, x0A, x1A, dash="1.2 0.8", lw="xs", color="#555")
            treads(up, "B", "xs", 1, None, dash="1.2 0.8", color="#555")
            flight_outline(yB[-1], yl, x0B, x1B, dash="1.2 0.8", lw="xs", color="#555")
            v.line(x0A, yl, x1B, yl, lw="xs", dash="1.2 0.8", color="#555")
        # numbers on flight B (grey, run continues)
        for j in range(1, up["nB"]):
            y = yB[j - 1] - t / 2
            sh.text(*v.P(x0B + 0.22, y - 0.05), str(up["nA"] + j), size=SZS, color="#999")
        # total risers at the top
        sh.text(*v.P(x0B + 0.22, yB[-1] - 0.16), str(up["nA"] + up["nB"]), size=SZS, color="#999")
        # dashed walking line to the top
        pts = [v.P(wl, ycut + 0.05), v.P(wl, yl + 0.55), v.P(x0B + M.ST["w"] / 2 - 0.12, yl + 0.55),
               v.P(x0B + M.ST["w"] / 2 - 0.12, yB[-1] + 0.06)]
        sh.polyline(pts, lw="xs", dash="1.5 0.8", color="#666")
        arrow_line(sh, pts[-2:], lw="xs", head=1.5)
    if dn and lvl != "B":
        tt, r, yA, yB = run_data(dn)
        # lower run is visible below the cut: flight B (down from this floor), landing, flight A beyond the cut
        treads(dn, "B", "s")
        flight_outline(yB[-1], yl, x0B, x1B)
        if up is None:
            treads(dn, "A", "s")
            flight_outline(yA[0], yl, x0A, x1A)
            for kk in range(1, dn["nA"]):
                sh.text(*v.P(x0A + 0.22, yA[kk - 1] + t / 2 - 0.05), str(kk), size=SZS)
            for j in range(1, dn["nB"]):
                sh.text(*v.P(x0B + 0.22, yB[j - 1] - t / 2 - 0.05), str(dn["nA"] + j), size=SZS)
        else:
            tu, ru, yAu, yBu = run_data(up)
            kcut = int((zc - up["z0"]) / up["r"])
            ycut = yAu[kcut - 1] + 0.14
            for kk in range(1, dn["nA"] + 1):
                y = yA[kk - 1]
                if y > ycut + 0.18:
                    v.line(x0A, y, x1A, y, lw="xs", color="#333")
            flight_outline(ycut + 0.15, yl, x0A, x1A, lw="xs", color="#333")
        v.line(x0A, yl, x1B, yl, lw="s")
        # down walking line
        wl = x0B + M.ST["w"] / 2 + 0.12
        pts = [v.P(wl, yB[-1] + 0.05), v.P(wl, yl + 0.30)]
        if up is None:
            pts += [v.P(x0A + M.ST["w"] / 2 + 0.12, yl + 0.30), v.P(x0A + M.ST["w"] / 2 + 0.12, yA[0] + 0.08)]
        sh.circle(*pts[0], 0.6, lw="xs", fill="#000")
        arrow_line(sh, pts, lw="s")
        sh.text(*v.P(wl, yB[-1] - 0.16), "יורד", size=SZ, weight=700)
    # landing
    if up or dn:
        v.line(x0A, yl, x1B, yl, lw="s")
    # gap / glass spine between flights
    ys0 = max(hole, (up or dn)["yA0"])
    v.rect(x1A + 0.035, ys0, x0B - 0.035, yl, fill="#cfe5ee", lw="xs")
    # glass guards of this level from model RAILS
    for rl in M.RAILS:
        if rl["kind"] != "glass" or abs(rl["z0"] - M.LV[lvl]) > 1e-6:
            continue
        rx0, rx1 = sorted((rl["x0"], rl["x1"]))
        ry0, ry1 = sorted((rl["y0"], rl["y1"]))
        if rx1 < xa or rx0 > xb or ry1 < ya or ry0 > yb:
            continue
        if up and abs(ry0 - ry1) < 1e-6 and abs(ry0 - up["yA0"]) < 0.05 and rx0 < x1A and rx1 > x0A:
            msg = (f"RAILS guard at y={ry0:.2f}, x {rx0:.2f}–{rx1:.2f}, z0={rl['z0']:+.2f} blocks the first riser of "
                   f"the {lvl}-run flight A (y={up['yA0']:.2f}) – omitted on the stair sheet")
            if msg not in ISSUES:
                ISSUES.append(msg)
            continue
        if abs(ry0 - ry1) < 1e-6:
            v.rect(rx0, ry0 - 0.012, rx1, ry0 + 0.012, fill="#cfe5ee", lw="xs")
        else:
            v.rect(rx0 - 0.012, ry0, rx0 + 0.012, ry1, fill="#cfe5ee", lw="xs")
    # wall handrail along flight A (west wall)
    st_ = up or dn
    hx = x0A + 0.045
    v.line(hx, st_["yA0"] - 0.30, hx, yl, lw="m", color="#333")
    for yy in [st_["yA0"] + 0.25 + i * 0.9 for i in range(3)]:
        v.line(x0A - 0.06, yy, hx, yy, lw="s", color="#333")
    # slab hole of the floor above (overhead) dashed
    if hup:
        v.polyline([(hup[0], hup[1]), (hup[2], hup[1]), (hup[2], yn), (hup[0], yn)], closed=True,
                   lw="s", dash="3 1 0.6 1", color="#222")
    # floor edge at this level (cut) – heavy
    if hz:
        v.line(hz[2], hz[1], hz[2], M.LIFT["y0"], lw="l")
        v.line(x1A + M.ST["gap"] if up else hz[0], hz[1], hz[2], hz[1], lw="l" if not up else "m")
        if hz[0] < x0A - 0.01:
            v.line(hz[0], hz[1], x0A, hz[1], lw="m")
    # ---------------- walls
    for w in M.walls_on(lvl):
        if w.kind in ("parapet",):
            continue
        ext = w.kind in ("ext", "retain")
        x0, y0, x1, y1 = _wall_rect(w, ext)
        if x1 < xa or x0 > xb or y1 < ya or y0 > yb:
            continue
        # openings cut at 1.20 above floor
        spans = [(w.a0 - (w.t / 2 if ext else 0), w.a1 + (w.t / 2 if ext else 0))]
        ops = [o for o in w.openings if (o.sill < 1.2 < o.head) or o.kind in ("passage", "open")]
        for o in ops:
            new = []
            for s0, s1 in spans:
                if o.end <= s0 or o.pos >= s1:
                    new.append((s0, s1))
                    continue
                if o.pos > s0:
                    new.append((s0, o.pos))
                if o.end < s1:
                    new.append((o.end, s1))
            spans = new
        rc = w.core == "rc" or w.kind in ("rc", "shaft", "retain", "mamad")
        for s0, s1 in spans:
            if w.horiz:
                rr = (s0, w.c - w.t / 2, s1, w.c + w.t / 2)
            else:
                rr = (w.c - w.t / 2, s0, w.c + w.t / 2, s1)
            if ext and w.out:
                _ext_wall_plan(v, w, rr)
            else:
                v.rect(*rr, fill=fill_ref(v.sh, "pat:rc" if rc else "dx:blk" if w.t > 0.11 else "pat:partition"), lw="l")
        for o in ops:
            _opening_plan(v, w, o, lvl)
    # ---------------- lift
    L = M.LIFT
    v.rect(L["x0"] + 0.30, L["y0"] + 0.30, L["x1"] - 0.30, L["y1"] - 0.10, fill="none", lw="s")
    v.line(L["x0"] + 0.30, L["y0"] + 0.30, L["x1"] - 0.30, L["y1"] - 0.10, lw="xs")
    v.line(L["x0"] + 0.30, L["y1"] - 0.10, L["x1"] - 0.30, L["y0"] + 0.30, lw="xs")
    v.line(16.30, L["y0"] + 0.23, 16.90, L["y0"] + 0.23, lw="s")
    v.line(16.30, L["y0"] + 0.17, 16.90, L["y0"] + 0.17, lw="s")
    sh.end_group()
    # frame
    sh.rect(cx + 2, cy + 2, pw, ph, lw="xxs", color="#999")
    # ---------------- annotations
    P = v.P
    if lvl != "B" or True:
        lx, ly = P(16.60, 30.80)
        sh.rect(lx - 9, ly - 4.2, 18, 7.4, color="none", fill="#fff")
        sh.text(lx, ly - 1.4, "פיר מעלית", size=SZS, weight=500)
        sh.text(lx, ly + 1.8, "ביתית 140/180", size=SZS)
    # landing level
    st_l = up or dn
    if up:
        sh.text(*P(14.35, 31.25), f"משטח ביניים {ltr(fmt_lv(up['zl'], 3))}", size=SZS, weight=700)
    if dn and lvl != "B":
        sh.text(*P(14.35, 30.90), f"(משטח תחתון {ltr(fmt_lv(dn['zl'], 3))})" if up else f"משטח ביניים {ltr(fmt_lv(dn['zl'], 3))}",
                size=SZS, color="#444" if up else "#000", weight=400 if up else 700)
    # floor level (plan symbol)
    v.level_mark(16.0, 28.55, M.LV[lvl], size=SZ, plan=True)
    # riser / tread note
    st_n = up or dn
    nn = st_n["nA"] + st_n["nB"]
    rr = st_n["r"] * 100
    note = f"{nn} × {rr:.1f} / 28   ‏2R+T={2 * rr + 28:.1f}"
    sh.text(*P(14.35, 27.40), note, size=SZ, weight=700)
    sh.text(*P(14.35, 27.22) if lvl != "R" else P(14.35, 27.22), f"רוחב מהלך 110 · {'עולה ל' + {'B': 'ק. קרקע', 'G': 'קומה א׳', 'U': 'גג'}[lvl] if up else 'מגיע מקומה א׳'}",
            size=SZS, color="#333")
    # labels
    if lvl != "R":
        leader(sh, *P(hup[2], 29.30), *P(hup[2] + 0.35, 29.0), ["קו חור בתקרה מעל"], side="right", size=SZS, dot=True)
    if lvl == "B":
        sh.text(*P(14.95, 29.15), "חלל מתחת", size=SZS, color="#555")
        sh.text(*P(14.95, 28.95), "למדרגות", size=SZS, color="#555")
    # section marker A-A
    for yy, lab_side in ((ya + 0.25, 1), (yb - 0.30, -1)):
        px_, py_ = P(X_CUT, yy)
        sh.line(px_, py_ - 3.5, px_, py_ + 3.5, lw="l")
        sh.path(f"M{px_},{py_ - 1.4} L{px_ + 3.2},{py_} L{px_},{py_ + 1.4} Z", lw="xs", fill="#000")
        sh.text(px_ - 2.2, py_ + 1.0, "א", size=2.6, weight=700)
    # detail B reference at the east glass
    if lvl == "U":
        detail_ref(sh, *P(hz[2], 28.75), 4.0, "B", SN, ang=0)
    if lvl == "R":
        rx = [w for w in M.walls_on("R") if w.horiz and w.kind == "ext" and w.out == -1]
        if rx:
            yin = rx[0].c + rx[0].t / 2
            sh.text(*P(16.0, 27.75), f"משטח עליון {ltr(f'{(hole - yin) * 100:.0f}')} ס\"מ עד דלת היציאה לגג (D-31)", size=SZS)
            arrow_line(sh, [P(14.85, 27.60), P(14.85, ya + 0.02)], lw="s", head=1.5)
    # dims: x chain below
    ydm = cy + 2 + ph + 5.5
    xs = [P(xx, ya)[0] for xx in (13.20, 14.30, 14.40, 15.50, 15.70, 17.50)]
    dim_chain_h(sh, xs, ydm, texts=["110", "10", "110", "20", "180"], size=SZS)
    # y chain right
    xdm = cx + 2 + pw + 5
    stn = up or dn
    tt, r, yA, yB = run_data(stn)
    ys = [hole if lvl != "G" else yA[0], yl, yn, 32.0]
    nt = int(round((yl - ys[0]) / 0.28))
    dim_chain_v(sh, [P(xa, yy)[1] for yy in ys], xdm,
                texts=[f"{nt}×28={nt * 28}", "120", "30"], size=SZS, left=False)
    # title
    names = {"B": "תכנית מדרגות – קומת מרתף", "G": "תכנית מדרגות – קומת קרקע",
             "U": "תכנית מדרגות – קומה א'", "R": "תכנית מדרגות – יציאה לגג"}
    D.drawing_title(sh, cx + cw - 6, cy + ch - 8.5, names[lvl], 'קנ"מ 1:25', width=72, size=4.6)
    sh.text(cx + 8, cy + ch - 5.2, fmt_lv(M.LV[lvl]), size=3.4, weight=700, anchor="left")


def _ext_wall_plan(v, w, rr):
    """exterior wall in plan: 20 core + 10 skin (layers)."""
    x0, y0, x1, y1 = rr
    s = w.out
    core_fill = "pat:rc" if (w.core == "rc" or w.kind == "retain") else "dx:blk"
    if w.horiz:
        if s > 0:   # exterior on +y
            core = (x0, y0, x1, y1 - 0.10)
            sk = (x0, y1 - 0.10, x1, y1)
        else:
            core = (x0, y0 + 0.10, x1, y1)
            sk = (x0, y0, x1, y0 + 0.10)
    else:
        if s > 0:
            core = (x0, y0, x1 - 0.10, y1)
            sk = (x1 - 0.10, y0, x1, y1)
        else:
            core = (x0 + 0.10, y0, x1, y1)
            sk = (x0, y0, x0 + 0.10, y1)
    if w.kind == "retain":
        v.rect(x0, y0, x1, y1, fill="pat:rc", lw="l")
        return
    v.rect(*core, fill=fill_ref(v.sh, core_fill), lw="l")
    skf = {"stone": "dx:woolv", "plaster": "dx:eps"}.get(w.skin, "dx:eps")
    v.rect(*sk, fill=fill_ref(v.sh, skf), lw="s")
    # cladding line
    if w.horiz:
        yy = sk[3] - 0.03 if s > 0 else sk[1] + 0.03
        if w.skin == "stone":
            v.rect(sk[0], yy - 0.0, sk[2], sk[3] if s > 0 else sk[1], fill=fill_ref(v.sh, "dx:lime"), lw="xs")


def _opening_plan(v, w, o, lvl):
    sh = v.sh
    if not w.horiz and o.kind == "door":
        x0, x1 = w.c - w.t / 2, w.c + w.t / 2
        v.line(x0, o.pos, x0, o.end, lw="xs")
        v.line(x1, o.pos, x1, o.end, lw="xs")
        hy = o.pos if o.hinge == "a" else o.end
        L = o.end - o.pos
        xx = x1 if o.swing > 0 else x0
        oy_ = o.end if o.hinge == "a" else o.pos
        v.line(xx, hy, xx + o.swing * L, hy, lw="m")
        a_h = 0 if o.swing > 0 else 180
        a_o = 90 if o.hinge == "a" else 270
        a0, a1 = sorted((a_h, a_o if not (a_h == 0 and a_o == 270) else -90))
        v.arc(xx, hy, L, a0, a1, lw="xs")
        return
    if w.horiz:
        y0, y1 = w.c - w.t / 2, w.c + w.t / 2
        if o.kind in ("fixed", "window", "slide"):
            v.rect(o.pos, w.c - 0.04, o.end, w.c + 0.04, fill=fill_ref(sh, "dx:alu"), lw="s")
            v.line(o.pos, w.c, o.end, w.c, lw="s", color="#2b6c86")
            v.line(o.pos, y0, o.end, y0, lw="xs")
            v.line(o.pos, y1, o.end, y1, lw="xs")
        elif o.kind == "door":
            v.line(o.pos, y0, o.end, y0, lw="xs")
            v.line(o.pos, y1, o.end, y1, lw="xs")
            hx = o.pos if o.hinge == "a" else o.end
            L = o.end - o.pos
            sgn = o.swing
            yy = y1 if sgn > 0 else y0
            v.line(hx, yy, hx, yy + sgn * L, lw="m")
            a0 = 90 if sgn > 0 else 270
            if o.hinge == "a":
                v.arc(hx, yy, L, 0 if sgn > 0 else 270, 90 if sgn > 0 else 360, lw="xs")
            else:
                v.arc(hx, yy, L, 90 if sgn > 0 else 180, 180 if sgn > 0 else 270, lw="xs")


# --------------------------------------------------------------------------- #
#  stair details 1:5
# --------------------------------------------------------------------------- #
def _det_frame(sh, x, y, w, h, scale, xmin, xmax, zmin, zmax, bands=None, dx=0.0, dy=0.0):
    """Centre a model window [xmin,xmax]×[zmin,zmax] in the paper box (x,y,w,h) – returns Frame."""
    k = 1000.0 / scale
    if bands:
        hh = sum(b - a for a, b in bands) * k + 5.0 * (len(bands) - 1)
    else:
        hh = (zmax - zmin) * k
    ww = (xmax - xmin) * k
    ox = x + (w - ww) / 2 + dx
    top = y + (h - hh) / 2 + dy
    fr = Frame(sh, ox, 0, scale, x0=xmin, bands=bands or [(zmin, zmax)], clip=(xmin, xmax))
    # set oy so that the top of the last band maps to `top`
    zt = fr.bands[-1][1]
    fr.oy = top + (zt - fr.offs[-1]) * k
    return fr


def detail_A(sh, x, y, w, h):
    """A – tread nosing with LED strip (section along the walking line)."""
    r, t = M.STAIRS[1]["r"], 0.28
    th = h - 16
    fr = _det_frame(sh, x + 4, y + 2, w * 0.56, th, 5, -0.17, 0.33, -0.40, 0.10, dx=0)
    c = C_NOSE
    # geometry: lower tread top at z=-r (nosing at y=-t), riser k at y=0 (nosing), upper tread top z=0
    z_up, z_lo = 0.0, -r
    items = []
    # RC folded plate: lower tread slab + riser + upper tread slab
    top = [(-0.17, z_lo - T_OAK), (c, z_lo - T_OAK), (c, z_up - T_OAK), (0.33, z_up - T_OAK)]
    bot = [(0.33, z_up - T_OAK - T_PLATE), (c + T_PLATE, z_up - T_OAK - T_PLATE), (c + T_PLATE, z_lo - T_OAK - T_PLATE),
           (-0.17, z_lo - T_OAK - T_PLATE)]
    rc = PG(top + bot)
    items.append((rc, S_RC))
    # riser finish: fine plaster 1 cm
    items.append((R(c - 0.008, z_lo, c, z_up - T_OAK), S_PLAST))
    # oak treads (upper with nosing + groove for LED), lower tread
    oak_up = PG([(0.0, z_up), (0.33, z_up), (0.33, z_up - T_OAK), (0.022, z_up - T_OAK), (0.022, z_up - T_OAK + 0.012),
                 (0.008, z_up - T_OAK + 0.012), (0.008, z_up - T_OAK), (0.0, z_up - T_OAK)])
    # rounded nosing approximation (chamfer 3 mm)
    oak_up = oak_up.difference(PG([(0.0, z_up), (0.004, z_up), (0.0, z_up - 0.004)]))
    items.append((oak_up, S_OAK))
    items.append((R(-0.17, z_lo - T_OAK, c - 0.008, z_lo), S_OAK))
    # adhesive layers
    items.append((R(c, z_up - T_OAK - 0.004, 0.33, z_up - T_OAK), dict(fill="#555", lw="xxs")))
    items.append((R(-0.17, z_lo - T_OAK - 0.004, c - 0.008, z_lo - T_OAK), dict(fill="#555", lw="xxs")))
    # LED alu profile in groove under nosing
    items.append((R(0.009, z_up - T_OAK + 0.001, 0.021, z_up - T_OAK + 0.011), S_ALU))
    items.append((R(0.010, z_up - T_OAK + 0.0005, 0.020, z_up - T_OAK + 0.003), dict(fill="#fff6c8", lw="xxs")))
    fr.render(items)
    # light cone
    p0 = fr.P(0.015, z_up - T_OAK)
    p1 = fr.P(c - 0.006, z_lo + 0.02)
    p2 = fr.P(-0.06, z_lo)
    sh.polyline([p0, p1, p2], closed=True, lw="xxs", color="#e2b400", fill="#fff3b0", fop=0.6)
    # anti-slip grooves
    for gx in (0.025, 0.040):
        sh.line(*fr.P(gx, z_up), *fr.P(gx, z_up - 0.003), lw="xs")
    # break lines
    breakline(sh, fr.X(-0.17), fr.Y(z_lo + 0.03), fr.X(-0.17), fr.Y(z_lo - 0.27), amp=1.2)
    breakline(sh, fr.X(0.33), fr.Y(z_up + 0.03), fr.X(0.33), fr.Y(z_up - 0.27), amp=1.2)
    # dims
    dimv(sh, fr.Y(z_lo), fr.Y(z_up), fr.X(-0.12), f"{r * 100:.1f}", ext=fr.X(-0.02), size=SZS)
    dimv(sh, fr.Y(z_up - T_OAK), fr.Y(z_up), fr.X(0.30), "5", ext=fr.X(0.25), size=SZS, left=False)
    dimh(sh, fr.X(0.0), fr.X(c), fr.Y(z_up) - 4, "3", ext=fr.Y(z_up), size=SZS)
    dimh(sh, fr.X(c), fr.X(c + T_PLATE), fr.Y(z_lo - 0.30), "18", ext=fr.Y(z_lo - 0.24), size=SZS)
    dimv(sh, fr.Y(z_up - T_OAK - T_PLATE), fr.Y(z_up - T_OAK), fr.X(0.31) + 6, "18", ext=fr.X(0.29), size=SZS, left=False)
    # callouts
    tx = x + w * 0.56 + 6
    L = lambda px, pz, ty, lines: leader(sh, *fr.P(px, pz), tx, ty, lines, side="right", size=SZS)
    y_ = fr.Y(z_up) - 14
    L(0.20, z_up - 0.02, y_, ["מדרך עץ אלון מלא 5 ס\"מ", "שמן-לכה מט, חריצי החלקה"])
    L(0.10, z_up - T_OAK - 0.002, y_ + 7, ["הדבקה אלסטית פוליאוריטן"])
    L(0.015, z_up - T_OAK + 0.006, y_ + 12, ["פס לד 24V בפרופיל אלומיניום", "בחריץ מתחת לחוטם, 3000K"])
    L(-0.04, z_lo + 0.06, y_ + 21, ["תאורה עקיפה על הרום"])
    L(c - 0.004, z_lo + 0.10, y_ + 27, ["טיח פנים חלק + צבע"])
    L(0.15, z_up - T_OAK - 0.10, y_ + 33, ["מדרגה מקופלת ב\"מ 18 ס\"מ", "ב-30, ברזל לפי מהנדס"])
    detail_title(sh, x + w - 3, y + h - 8, "A", "חוטם מדרגה ופס לד", 'קנ"מ 1:5', size=4.0)


def detail_B(sh, x, y, w, h):
    """B – flight / landing edge with glass balustrade in side-mounted SS channel (cross-section)."""
    th = h - 16
    bands = [(-0.30, 0.10), (0.94, 1.10)]
    fr = _det_frame(sh, x + 2, y + 2, w * 0.52, th, 5, -0.25, 0.14, -0.30, 1.10, bands=bands, dx=4)
    items = []
    z0 = 0.0
    # RC landing/flight edge (floor at 0): oak 5 on RC 20
    items.append((R(-0.25, -0.25, 0.0, -0.05), S_RC))
    items.append((R(-0.25, -0.05, -0.005, 0.0), S_OAK))
    # side channel SS316 (U 80x140) fixed to slab face
    ch_x0 = 0.0
    chan = PG([(0.0, -0.215), (0.075, -0.215), (0.075, -0.055), (0.068, -0.055), (0.068, -0.208), (0.007, -0.208),
               (0.007, -0.055), (0.0, -0.055)])
    items.append((chan, S_SS))
    # glass 12+12 laminated
    gx0, gx1 = 0.025, 0.050
    items.append((R(gx0, -0.195, gx1, 1.05 - 0.015), S_GLASS))
    items.append((LN([(0.0375, -0.195), (0.0375, 1.035)]), dict(lw="xxs", color="#2b6c86")))
    # setting block + wedge gaskets
    items.append((R(gx0, -0.207, gx1, -0.195), dict(fill="#333", lw="xxs")))
    items.append((PG([(0.007, -0.06), (gx0, -0.06), (gx0, -0.15), (0.007, -0.14)]), dict(fill="dx:rubber", lw="xxs")))
    items.append((PG([(gx1, -0.06), (0.068, -0.06), (0.068, -0.14), (gx1, -0.15)]), dict(fill="dx:rubber", lw="xxs")))
    # cap rail: SS U-channel + tube Ø42.4
    items.append((PG([(gx0 - 0.004, 1.02), (gx1 + 0.004, 1.02), (gx1 + 0.004, 1.034), (gx0 - 0.004, 1.034)]), S_SS))
    tube = ring(0.0375, 1.05 + 0.0, 0.0212, 0.0025)
    items.append((tube, S_SS))
    items.append((R(gx0, 1.015, gx1, 1.03), dict(fill="dx:rubber", lw="xxs")))
    fr.render(items)
    fr.breaks(-0.25, 0.14, amp=1.2)
    # anchors (chemical M12)
    for zz in (-0.10, -0.17):
        a, b = fr.P(-0.12, zz), fr.P(0.07, zz)
        sh.line(*a, *b, lw="m")
        sh.line(a[0], a[1] - 0.6, a[0], a[1] + 0.6, lw="xs")
        hx, hy = fr.P(0.075, zz)
        sh.rect(hx, hy - 1.6, 1.4, 3.2, lw="xs", fill="#8e969e")
    breakline(sh, fr.X(-0.25), fr.Y(0.02), fr.X(-0.25), fr.Y(-0.29), amp=1.2)
    # dims
    xdim = fr.X(0.14) + 3
    sh.line(fr.X(0.09), fr.Y(0.0), xdim + 1, fr.Y(0.0), lw="xxs", color="#444")
    sh.line(fr.X(0.06), fr.Y(1.05 + 0.021), xdim + 1, fr.Y(1.05 + 0.021, 1), lw="xxs", color="#444")
    dimv(sh, fr.Y(0.0), fr.Y(0.0) - 0.0 + 0.0 - 1e-3 - 0.0 - (fr.Y(0.0) - fr.Y(0.10)), xdim, None, size=SZS, left=False)
    dimv(sh, fr.Y(0.94, 1), fr.Y(1.071, 1), xdim, None, size=SZS, left=False)
    sh.text(xdim + 3.4, (fr.Y(0.10) + fr.Y(0.94, 1)) / 2 + 1, "105", size=SZS, weight=700)
    sh.text(xdim + 3.4, (fr.Y(0.10) + fr.Y(0.94, 1)) / 2 + 3.6, "(90 לאורך מהלך)", size=SZS)
    dimh(sh, fr.X(gx0), fr.X(gx1), fr.Y(0.10) - 3, "2.5", ext=fr.Y(0.08), size=SZS)
    dimv(sh, fr.Y(-0.215), fr.Y(-0.055), fr.X(-0.25) - 3, "16", ext=fr.X(-0.01), size=SZS)
    level_tag(sh, fr.X(-0.18), fr.Y(0.0), "±0.00 מפלס", side="right", size=SZS, line=6)
    # callouts
    tx = x + w * 0.52 + 12
    L = lambda px, pz, ty, lines, b=None: leader(sh, *fr.P(px, pz, b), tx, ty, lines, side="right", size=SZS)
    yy = fr.Y(1.10, 1) - 1
    L(0.03, 1.07, yy, ["מאחז יד נירוסטה 316 Ø42.4", "על פרופיל כיסוי U"], 1)
    L(0.045, 0.98, yy + 9, ["זכוכית מחוסמת שכבתית", "12+12 PVB/SGP"], 1)
    L(0.06, -0.10, fr.Y(-0.02) + 2, ["פרופיל U נירוסטה 316", "מוצמד לצד (80×140)"])
    L(0.06, -0.12, fr.Y(-0.02) + 11, ["טריזי EPDM + שומר מרחק"])
    L(-0.10, -0.17, fr.Y(-0.02) + 17, ["עוגן כימי M12 @30"])
    L(-0.15, -0.20, fr.Y(-0.02) + 23, ["שפת משטח ב\"מ"])
    detail_title(sh, x + w - 3, y + h - 8, "B", "מעקה זכוכית בשפת משטח", 'קנ"מ 1:5', size=4.0)


def detail_C(sh, x, y, w, h):
    """C – start of a flight on the floor slab with floor finishes."""
    r = M.STAIRS[1]["r"]
    th = h - 16
    fr = _det_frame(sh, x + 4, y + 2, w * 0.56, th, 5, -0.26, 0.31, -0.32, 0.26, dx=0)
    c = C_NOSE
    items = []
    zs = -M.FIN
    # slab
    items.append((R(-0.26, -0.40, 0.31, zs), S_RC))
    # floor build-up: fill 7 + mortar/adhesive 1 + porcelain 2
    items.append((R(-0.26, zs, -0.004 + c - 0.012, -0.03), S_FILL))
    items.append((R(-0.26, -0.03, c - 0.012, -0.02), S_MORTAR))
    items.append((R(-0.26, -0.02, c - 0.012, 0.0), S_PORC))
    # perimeter joint
    items.append((R(c - 0.012, zs, c - 0.004, 0.0), dict(fill="#fff", lw="xxs")))
    # first step RC on slab (dowelled)
    top = [(c, zs), (c, r - T_OAK), (c + 0.28, r - T_OAK), (c + 0.28, 0.31)]
    step = PG([(c, zs), (c, r - T_OAK), (0.31, r - T_OAK), (0.31, zs)])
    items.append((step, S_RC))
    items.append((R(c - 0.008, 0.0, c, r - T_OAK), S_PLAST))
    # oak tread with nosing + LED
    items.append((R(0.0, r - T_OAK, 0.31, r), S_OAK))
    items.append((R(0.009, r - T_OAK + 0.001, 0.021, r - T_OAK + 0.011), S_ALU))
    # second riser (begins at 0.28)
    items.append((R(0.28 + c, r, 0.31, 0.26), S_RC))
    fr.render(items)
    # shadow gap skirting line + dowels
    for dx_ in (0.08, 0.20):
        a, b = fr.P(c + dx_, zs - 0.15), fr.P(c + dx_, r - T_OAK - 0.04)
        sh.line(*a, *b, lw="m", dash="1.2 0.5")
    # starter bar (bent)
    sh.polyline([fr.P(c + 0.03, zs - 0.05), fr.P(c + 0.03, r - T_OAK - 0.03), fr.P(0.25, r - T_OAK - 0.03)], lw="s")
    breakline(sh, fr.X(-0.26), fr.Y(0.04), fr.X(-0.26), fr.Y(-0.33), amp=1.2)
    breakline(sh, fr.X(0.31), fr.Y(0.27), fr.X(0.31), fr.Y(-0.33), amp=1.2)
    breakline(sh, fr.X(-0.27), fr.Y(-0.32), fr.X(0.32), fr.Y(-0.32), amp=1.2)
    # dims
    xd = fr.X(-0.20)
    dim_chain_v(sh, [fr.Y(zs), fr.Y(-0.03), fr.Y(0.0)], xd, texts=["7", "3"], ext=fr.X(-0.15), size=SZS)
    dimv(sh, fr.Y(0.0), fr.Y(r), fr.X(-0.05), f"{r * 100:.1f}", ext=fr.X(-0.01), size=SZS)
    dimh(sh, fr.X(0.0), fr.X(0.28), fr.Y(0.26) + 0.5, "28", ext=fr.Y(r), size=SZS)
    level_tag(sh, fr.X(-0.13), fr.Y(0.0), "±0.00", side="right", size=SZS, line=5)
    # callouts
    tx = x + w * 0.56 + 6
    L = lambda px, pz, ty, lines: leader(sh, *fr.P(px, pz), tx, ty, lines, side="right", size=SZS)
    y_ = fr.Y(0.26) - 1
    L(0.20, r - 0.02, y_, ["מדרך אלון 5 ס\"מ + לד"])
    L(c - 0.004, 0.08, y_ + 6, ["רום ראשון – טיח + צבע"])
    L(0.05, 0.0, y_ + 12, ["פרופיל הפרדה נירוסטה", "+ מישק אלסטי 8 מ\"מ"])
    L(-0.10, -0.01, y_ + 21, ["ריצוף פורצלן 120/120", "על דבק C2TE S1"])
    L(-0.18, -0.06, y_ + 30, ["מילוי בטון קל/חול 7 ס\"מ"])
    L(0.11, 0.0, y_ + 36, ["קוצים Ø10 @20 – מדרגה", "ראשונה יצוקה על התקרה"])
    L(0.0, -0.30, y_ + 45, ["תקרת ב\"מ 30 ס\"מ"])
    detail_title(sh, x + w - 3, y + h - 8, "C", "תחילת מהלך על תקרה", 'קנ"מ 1:5', size=4.0)


def detail_D(sh, x, y, w, h):
    """D – wall-mounted handrail bracket (section across the rail) + stair notes."""
    th = h - 4
    fr = _det_frame(sh, x + w - 108, y + 2, 60, th - 10, 5, -0.06, 0.13, -0.10, 0.08)
    items = []
    # wall: RC + plaster
    items.append((R(-0.06, -0.10, -0.012, 0.08), S_RC))
    items.append((R(-0.012, -0.10, 0.0, 0.08), S_PLAST))
    # rosette plate Ø70 (in section 8 mm)
    items.append((R(0.0, -0.035, 0.008, 0.035), S_SS))
    # arm Ø16 bent
    arm = LN([(0.008, 0.0), (0.040, 0.0), (0.065, 0.025), (0.0712, 0.032)]).buffer(0.008, cap_style=2)
    items.append((arm, S_SS))
    # saddle + tube Ø42.4×2
    cx, cz = 0.0712, 0.032 + 0.0212 + 0.004
    items.append((R(cx - 0.012, cz - 0.0212 - 0.006, cx + 0.012, cz - 0.0212 + 0.001), S_SS))
    items.append((ring(cx, cz, 0.0212, 0.0026), S_SS))
    fr.render(items)
    # anchor screw
    for zz in (-0.02, 0.02):
        sh.line(*fr.P(-0.05, zz), *fr.P(0.006, zz), lw="m")
    breakline(sh, fr.X(-0.06), fr.Y(0.08) - 1, fr.X(-0.06), fr.Y(-0.10) + 1, amp=1.0)
    dimh(sh, fr.X(0.0), fr.X(cx - 0.0212), fr.Y(cz + 0.0212) - 4, "5", ext=fr.Y(cz), size=SZS)
    dimh(sh, fr.X(cx - 0.0212), fr.X(cx + 0.0212), fr.Y(cz + 0.0212) - 4, "4.2", ext=fr.Y(cz), size=SZS)
    sh.text(fr.X(0.10), fr.Y(-0.06), "90 מעל קו", size=SZS, anchor="left")
    sh.text(fr.X(0.10), fr.Y(-0.06) + 2.8, "חוטמי המדרגות", size=SZS, anchor="left")
    tx = fr.X(-0.06) - 4
    L = lambda px, pz, ty, lines: leader(sh, *fr.P(px, pz), tx, ty, lines, side="left", size=SZS)
    L(cx - 0.015, cz + 0.012, fr.Y(0.08), ["מאחז יד נירוסטה 316", "צינור Ø42.4×2 מוברש"])
    L(0.05, 0.012, fr.Y(0.08) + 8, ["זרוע נירוסטה Ø16", "+ אוכף מרותך"])
    L(0.004, -0.025, fr.Y(0.08) + 16, ["רוזטה Ø70 + 2 ברגים", "ודיבלים כימיים"])
    L(-0.03, -0.07, fr.Y(0.08) + 24, ["קיר בטון/בלוק + טיח"])
    detail_title(sh, x + w - 4, y + h - 6, "D", "תושבת מאחז יד", 'קנ"מ 1:5', size=4.0)
    # notes (left part)
    notes = ["הערות:",
             "1. מידות בס\"מ, מפלסים במ' (±0.00 = +18.50).",
             "2. 2R+T בתחום 61–63 ס\"מ; רום ≤17.5, שלח 28.",
             "3. מעקה 105 במשטחים, 90 לאורך המהלך;",
             "    מרווח פתוח ≤10 ס\"מ.",
             "4. גובה חופשי מעל קו החוטמים ≥210.",
             "5. נירוסטה 316 ואלומיניום ימי (אוויר מלוח).",
             "6. מדרגות ב\"מ – לפי תכנון מהנדס קונסטרוקציה."]
    xn = x + 2
    hr = headroom_report()
    mins = min(min(a, b) for _, a, b in hr)
    notes.append(f"7. גובה חופשי מינ' מחושב: {mins * 100:.0f} ס\"מ.")
    for i, t in enumerate(notes):
        sh.text(x + 112, y + 6 + i * 3.0, t, size=SZS, anchor="right", weight=700 if i == 0 else 400)


# =========================================================================== #
#  SHEET 16 – WALL SECTION & DETAILS
# =========================================================================== #
def sheet_details(sh: D.Sheet, box):
    from details_wall import build_sheet16
    build_sheet16(sh, box)
