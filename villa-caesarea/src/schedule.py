"""Sheet 17 – openings schedule (רשימת אלומיניום ונגרות).

Everything on this sheet is derived from the model at build time:
  * aluminium items  – openings of kind slide / window / fixed / mamad_win, grouped by tag
  * doors            – openings of kind door / pivot / mamad_door, grouped by door type
                       (category + size) for the elevation cells, plus a per-tag door list
Width / height / sill are taken from Opening(pos, end, sill, head) in cm; rooms, floor,
facade orientation and shading (louvre fields) are found from the model geometry.

Builder: sheet_schedule(sh, box) with box = (x, y, w, h) in paper mm.
`audit()` returns a list of model inconsistencies (also printed by `python3 schedule.py`).
"""
from __future__ import annotations

import math
import os
from collections import Counter, OrderedDict

import model as M
from draw import drawing_title

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(HERE), "fonts")

ALU_KINDS = ("slide", "window", "fixed", "mamad_win")
DOOR_KINDS = ("door", "pivot", "mamad_door")
SKIP_KINDS = ("open", "passage")
LEVEL_ORDER = ["B", "G", "U", "R"]
LEVEL_HE = {"B": "מרתף", "G": "קרקע", "U": "א'", "R": "גג"}

# colours
BRONZE = "#4b4037"
GLASS = "#e2edf1"
FROST = "#d3d9dc"
OAK = "#c9a273"
STEEL = "#a7acb1"
LEAF = "#f7f4ee"
SPANDREL = "#bdb6aa"
HDR = "#efe7da"
LBL = "#f7f3ec"
INK = "#2b2b2b"

LRI, PDI = "⁦", "⁩"
ZW = {"⁦", "⁧", "⁨", "⁩", "‎", "‏"}


def ltr(s):
    """Isolate a left-to-right chunk (signed numbers, codes) inside Hebrew text."""
    return f"{LRI}{s}{PDI}"


# --------------------------------------------------------------------------- #
#  Font metrics (Heebo) for wrapping / fitting
# --------------------------------------------------------------------------- #
_FM: dict = {}


def _font(weight):
    w = 400 if weight < 450 else (500 if weight < 650 else 700)
    if w not in _FM:
        try:
            from fontTools.ttLib import TTFont
            f = TTFont(os.path.join(FONT_DIR, f"Heebo-{w}.ttf"))
            _FM[w] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
        except Exception:  # pragma: no cover - fallback estimate
            _FM[w] = None
    return _FM[w]


def tw(t, size, weight=400):
    fm = _font(weight)
    t = str(t)
    if fm is None:
        return sum(0 if c in ZW else 0.56 for c in t) * size
    cmap, hm, upm = fm
    tot = 0.0
    for ch in t:
        if ch in ZW:
            continue
        g = cmap.get(ord(ch))
        tot += hm[g][0] if g in hm else upm * 0.56
    return tot / upm * size


def wrap(text, size, width, weight=400):
    lines = []
    for para in str(text).split("\n"):
        words = para.split(" ")
        cur = ""
        for wd in words:
            cand = wd if not cur else cur + " " + wd
            if tw(cand, size, weight) <= width or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = wd
        lines.append(cur)
    return lines


def longest_token(text, size, weight=400):
    return max((tw(t, size, weight) for t in str(text).replace("\n", " ").split(" ")), default=0)


class NullSheet:
    """Measuring pass: swallows every drawing call."""

    def __getattr__(self, name):
        return lambda *a, **k: None


# --------------------------------------------------------------------------- #
#  Model extraction
# --------------------------------------------------------------------------- #
CIRC = ("פרוזדור", "מבואה", "לובי", "גלריה", "טרקלין")


def _room_at(level, x, y):
    for r in M.ROOMS:
        if r.level != level:
            continue
        for (x0, y0, x1, y1) in r.rects:
            if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
                return r
    return None


class _Pseudo:
    def __init__(self, name, ceil=3.0):
        self.name, self.outdoor, self.ceil, self.pseudo = name, False, ceil, True


def _stair_at(level, x, y):
    st = M.ST
    if level in ("B", "G", "U") and st["x0"] - 0.1 <= x <= st["x1"] + 0.1 and st["ys"] - 0.4 <= y <= st["yn"] + 0.1:
        return _Pseudo("חדר מדרגות", ceil=99)
    return None


def _sides(w, o):
    """Rooms on the + and - normal side of the wall at the opening's midpoint."""
    a = (o.pos + o.end) / 2
    res = {}
    for s in (1, -1):
        found = None
        for d in (w.t / 2 + 0.25, w.t / 2 + 0.6, w.t / 2 + 1.0):
            p = (a, w.c + s * d) if w.horiz else (w.c + s * d, a)
            found = _room_at(w.level, *p) or _stair_at(w.level, *p)
            if found:
                break
        res[s] = found
    return res


def _facing(w, s):
    if w.horiz:
        return "צפון" if s > 0 else "דרום"
    return "מזרח" if s > 0 else "מערב"


def _behind_fins(w, o):
    if w.horiz:
        return False
    z0 = M.LV[w.level] + o.sill
    z1 = M.LV[w.level] + o.head
    for f in M.FINS:
        if f.get("axis") != "y" or abs(f["c"] - w.c) > 0.8:
            continue
        if min(o.end, f["a1"]) - max(o.pos, f["a0"]) > 0.2 and min(z1, f["z1"]) - max(z0, f["z0"]) > 0.3:
            return True
    return False


class Inst:
    """One opening instance with everything derived from the model."""

    def __init__(self, w, o):
        self.w, self.o = w, o
        self.level = w.level
        self.kind = o.kind
        self.tag = o.tag
        self.wm = round(o.end - o.pos, 3)
        self.hm = round(o.head - o.sill, 3)
        self.sm = round(o.sill, 3)
        self.wc = int(round(self.wm * 100))
        self.hc = int(round(self.hm * 100))
        self.sc = int(round(self.sm * 100))
        self.frosted = o.frosted
        sides = _sides(w, o)
        self.sides = sides

        def outside(r):
            return r is None or r.outdoor

        ext_side = 0
        if w.kind in ("ext", "retain") and w.out:
            ext_side = w.out
        elif w.kind in ("ext", "retain", "glass", "parapet"):
            # glazing line without 'out': exterior = side of an outdoor room / no room
            if outside(sides[1]) and not outside(sides[-1]):
                ext_side = 1
            elif outside(sides[-1]) and not outside(sides[1]):
                ext_side = -1
        self.ext_side = ext_side
        self.exterior = ext_side != 0
        self.facing = _facing(w, ext_side) if ext_side else ""
        if ext_side:
            r_in = sides[-ext_side]
            self.room = r_in.name if r_in else (sides[ext_side].name if sides[ext_side] else "")
            self.other = sides[ext_side].name if sides[ext_side] else "חוץ"
        else:
            # interior door: served room = swing side unless circulation
            sw = sides[o.swing] if o.swing in sides else None
            ot = sides[-o.swing] if o.swing in sides else None
            if sw is None or any(c in sw.name for c in CIRC):
                if ot is not None and not any(c in ot.name for c in CIRC):
                    sw, ot = ot, sw
            if sw is None:
                sw, ot = ot, sw
            self.room = sw.name if sw else ""
            self.other = ot.name if ot else ""
        self.room_obj = sides[-ext_side] if ext_side else None
        self.fins = _behind_fins(w, o)
        # door hand: 'ימין' = hinges on the right of a viewer standing on the swing side
        if w.horiz:
            right = "a" if o.swing > 0 else "b"
        else:
            right = "b" if o.swing > 0 else "a"
        self.hinge_right = (o.hinge == right)
        self.hand = "ימין" if self.hinge_right else "שמאל"
        self.abs_head = M.LV[w.level] + o.head


def _tag_key(tag):
    import re
    m = re.match(r"([A-Za-z]+)-([A-Za-z]*)(\d+)", tag or "")
    if not m:
        return (9, tag)
    pre, sub, num = m.group(1), m.group(2), int(m.group(3))
    sub_rank = {"B": 0, "": 1}.get(sub, 2)
    return (0 if pre in ("AL", "D") else 1, sub_rank, num, tag)


def collect():
    alu, doors, skipped = [], [], []
    for w in M.WALLS:
        for o in w.openings:
            if o.kind in SKIP_KINDS:
                skipped.append(Inst(w, o))
            elif o.kind in ALU_KINDS:
                alu.append(Inst(w, o))
            elif o.kind in DOOR_KINDS:
                doors.append(Inst(w, o))
            else:
                skipped.append(Inst(w, o))
    # group aluminium by tag (untagged get a placeholder tag so they still show up)
    groups = OrderedDict()
    for i in alu:
        key = i.tag or f"?{i.level}-{i.kind}-{i.wc}x{i.hc}"
        groups.setdefault(key, []).append(i)
    order = sorted(groups, key=lambda t: (min(LEVEL_ORDER.index(x.level) for x in groups[t]), _tag_key(t)))
    alu_items = [AluItem(t, groups[t]) for t in order]
    doors.sort(key=lambda d: (LEVEL_ORDER.index(d.level), _tag_key(d.tag)))
    dgroups = OrderedDict()
    for d in doors:
        cat = door_category(d)
        dgroups.setdefault((cat, d.wc, d.hc), []).append(d)
    cat_rank = {c: i for i, c in enumerate(DOOR_CATS)}
    dkeys = sorted(dgroups, key=lambda k: (cat_rank.get(k[0], 99), -len(dgroups[k]), -k[1]))
    door_items = [DoorItem(k, dgroups[k]) for k in dkeys]
    return dict(alu=alu, doors=doors, skipped=skipped, alu_items=alu_items, door_items=door_items)


# --------------------------------------------------------------------------- #
#  Aluminium items – sashes and specification
# --------------------------------------------------------------------------- #
def _fmt_sill(c):
    if c == 0:
        return "±0"
    return ltr(f"{c:+d}")


def _join_unique(xs, sep=", "):
    out = []
    for x in xs:
        if x and x not in out:
            out.append(x)
    return sep.join(out)


def _floors(insts):
    lv = sorted({i.level for i in insts}, key=LEVEL_ORDER.index)
    return " + ".join(LEVEL_HE[l] for l in lv)


class AluItem:
    def __init__(self, tag, insts):
        self.tag = tag
        self.insts = insts
        cnt = Counter((i.wc, i.hc, i.sc) for i in insts)
        top = cnt.most_common(1)[0][0]
        self.rep = next(i for i in insts if (i.wc, i.hc, i.sc) == top)
        self.variants = list(OrderedDict.fromkeys((i.level, i.wc, i.hc, i.sc) for i in insts))
        self.sizes = list(OrderedDict.fromkeys((i.wc, i.hc) for i in insts))
        self.sills = list(OrderedDict.fromkeys(i.sc for i in insts))
        self.qty = len(insts)
        r = self.rep
        self.wc, self.hc, self.sc = r.wc, r.hc, r.sc
        self.kind = r.kind
        self.w, self.h, self.sill = r.wm, r.hm, r.sm
        self.frosted = any(i.frosted for i in insts)
        self.fins = any(i.fins for i in insts)
        self.panels, self.n_open, self.n_fixed, self.subtype = alu_panels(r.kind, r.wm, r.hm, r.sm)
        self.spec = self._spec()

    # ---------------------------------------------------------------- spec text
    def _spec(self):
        k, r = self.kind, self.rep
        n = sum(1 for p in self.panels if p["t"] not in ("spandrel",))
        rooms = _join_unique(i.room for i in self.insts)
        facing = _join_unique(i.facing for i in self.insts)
        room_names = " ".join(i.room for i in self.insts)
        bedroom = ("שינה" in room_names) or ("ממ" in room_names) or ("אורחים" in room_names and "חדר" in room_names)
        big = max((p["u1"] - p["u0"]) * (p["v1"] - p["v0"]) for p in self.panels)
        floor_level = self.sill <= 0.5
        notes = []
        # type & system
        if k == "slide":
            typ = f"דלת הרמה-הזזה תרמית, {n} כנפיים ({self.n_fixed} קבועה)" if self.n_fixed else \
                f"דלת הרמה-הזזה תרמית, {n} כנפיים"
            sysm = 'פרופיל הרמה-הזזה תרמי דוגמת סדרה כבדה "160", מסילה שקועה'
            notes.append("סף נגיש שקוע ברצפה, מנעול רב-נקודתי")
        elif k == "window":
            if self.subtype == "tilt":
                typ = f"חלון נטוי (קיפ) חשמלי, {n} כנפיים" if n > 1 else "חלון נטוי (קיפ) חשמלי"
                notes.append("מנוע פתיחה + חיישן גשם, אוורור לילה")
            else:
                no = self.n_open
                typ = f"חלון ציר-נטוי, {no} כנפיים" if no > 1 else "חלון ציר-נטוי, כנף אחת"
                if self.n_fixed:
                    typ += f" + {self.n_fixed} קבוע"
            sysm = 'פרופיל ציר-נטוי תרמי דוגמת סדרה "70", 3 אטמים'
        elif k == "fixed":
            spand = any(p["t"] == "spandrel" for p in self.panels)
            if spand or self.h >= 3.0:
                typ = "ויטרינה קבועה רציפה (קיר מסך)"
            else:
                typ = "חלון קבוע (ויטרינה)" if self.w > 0.8 else "חריץ זיגוג קבוע"
            sysm = 'פרופיל ויטרינה / מסך תרמי דוגמת סדרה "50", גליף נסתר'
            if spand:
                notes.append("ספנדרל אטום מבודד מול התקרה, רציף בין הקומות")
        else:  # mamad_win
            typ = 'חלון ממ"ד: הזזה + חלון הדף פלדה'
            sysm = 'פרופיל הזזה תרמי דוגמת סדרה "70" + חלון הדף פלדה מאושר'
        sysm += " · ברונזה כהה, מפרט ימי"
        # glazing
        if k == "mamad_win":
            glass = 'בידודי 6+12A+6 Low-E (חלון האלומיניום); מיגון: חלון הדף פלדה'
        else:
            if big > 3.5 and (k == "slide" or floor_level):
                g = "8+16A+55.2"
            else:
                g = "6+16A+44.2"
            outer = "מחוסם" if (k == "slide" or floor_level or big > 2.0) else "שקוף"
            glass = f"בידודי {g} Low-E · חוץ {outer}, פנים שכבתי"
            if self.frosted:
                glass += " חלבי (סאטן)"
        # shading
        roomtxt = rooms
        if k == "mamad_win":
            shade = 'תריס פלדה נגלל/הזזה (פקע"ר)'
        elif self.fins:
            shade = "רפפות אנכיות קבועות דמוי עץ 50/200 @180"
            if bedroom or k == "slide":
                shade += " + תריס חשמלי נסתר"
        elif self.frosted:
            shade = "— (זכוכית חלבית)"
        elif k == "fixed":
            if self.w * self.h > 2.5 and facing in ("מערב", "דרום"):
                shade = "וילון סקרין פנימי חשמלי"
            else:
                shade = "—"
        elif self.subtype == "tilt" and facing == "צפון":
            shade = "— (חזית צפון)"
        else:
            shade = "תריס גלילה חשמלי נסתר, שלבי אלומיניום מוקצף"
        # remarks
        if k == "mamad_win":
            notes.insert(0, 'חלון הדף + תריס פלדה נגלל/הזזה לפי הנחיות פקע"ר')
            notes.append('מידה מרבית 100/100, בקיר בטון מזוין')
        if self.frosted:
            notes.append("זכוכית חלבית לפרטיות")
        if any(p["t"] == "fixed" and p.get("guard") for p in self.panels):
            notes.append('מקטע תחתון קבוע שכבתי עד 105 ס"מ (מניעת נפילה)')
        if self.fins:
            notes.append("מאחורי מסך רפפות אנכיות")
        if k == "fixed" and self.sill <= 0.05 and not any(p["t"] == "spandrel" for p in self.panels):
            notes.append("זיגוג בטיחותי עד רצפה")
        if k == "fixed" and self.w <= 0.7 and self.qty > 1:
            notes.append(f"{self.qty} חריצים זהים")
        # neighbour of a pivot door → side light
        for i in self.insts:
            for o2 in i.w.openings:
                if o2.kind == "pivot" and (abs(o2.end - i.o.pos) < 0.25 or abs(i.o.end - o2.pos) < 0.25):
                    notes.append(f"חלון צד לדלת הכניסה {o2.tag}")
        if len(self.sizes) > 1 or len(self.sills) > 1:
            vv = []
            for (lv, wc, hc, sc) in self.variants:
                vv.append(f"{LEVEL_HE[lv]} {wc}/{hc}")
            notes.append("מידות לפי קומה: " + ", ".join(vv))
        size = ", ".join(f"{a}/{b}" for a, b in self.sizes)
        sill = ", ".join(_fmt_sill(s) for s in self.sills)
        return OrderedDict(
            type=typ,
            system=sysm,
            glass=glass,
            shade=shade,
            size=f"{size} · אדן {sill}",
            qty=f"{self.qty} יח' · {_floors(self.insts)}",
            loc=f"{roomtxt} · {facing}" if facing else roomtxt,
            note=" · ".join(dict.fromkeys(notes)) if notes else "—",
        )


def alu_panels(kind, w, h, sill):
    """Divide a unit into panels (unit-local metres, u from left seen from outside, v from sill up).
    Returns (panels, n_operable, n_fixed, subtype)."""
    P = []
    sub = kind
    if kind == "slide":
        n = max(2, math.ceil(w / 2.4 - 0.05))
        pw = w / n
        for i in range(n):
            if i == 0:
                P.append(dict(u0=0, u1=pw, v0=0, v1=h, t="fixed"))
            else:
                P.append(dict(u0=i * pw, u1=(i + 1) * pw, v0=0, v1=h, t="slide", dir=-1, lift=True))
    elif kind == "window":
        tilt_only = sill >= 1.6
        sub = "tilt" if tilt_only else "tt"
        v0 = 0.0
        if sill < 0.9 and h > 1.5:
            band = round(1.05 - sill, 3)
            P.append(dict(u0=0, u1=w, v0=0, v1=band, t="fixed", guard=True))
            v0 = band
        n = max(1, int(round(w / 1.1)))
        pw = w / n
        for i in range(n):
            d = dict(u0=i * pw, u1=(i + 1) * pw, v0=v0, v1=h)
            if tilt_only:
                d["t"] = "tilt"
            elif n >= 3 and 0 < i < n - 1:
                d["t"] = "fixed"
            else:
                d["t"] = "tt"
                d["hinge"] = "l" if (i < n / 2 or n == 1) else "r"
            P.append(d)
    elif kind == "fixed":
        v0 = 0.0
        if sill < -0.01:
            v0 = -sill
            P.append(dict(u0=0, u1=w, v0=0, v1=v0, t="spandrel"))
        n = max(1, math.ceil(w / 2.6 - 0.05))
        pw = w / n
        hh = h - v0
        m = 2 if hh > 3.4 else 1
        for i in range(n):
            for j in range(m):
                P.append(dict(u0=i * pw, u1=(i + 1) * pw, v0=v0 + j * hh / m, v1=v0 + (j + 1) * hh / m, t="fixed"))
    elif kind == "mamad_win":
        P.append(dict(u0=0, u1=w / 2, v0=0, v1=h, t="slide", dir=1, lift=False))
        P.append(dict(u0=w / 2, u1=w, v0=0, v1=h, t="slide", dir=-1, lift=False))
    n_open = sum(1 for p in P if p["t"] in ("slide", "tt", "tilt"))
    n_fixed = sum(1 for p in P if p["t"] == "fixed" and not p.get("guard"))
    return P, n_open, n_fixed, sub


# --------------------------------------------------------------------------- #
#  Doors
# --------------------------------------------------------------------------- #
DOOR_CATS = ["pivot", "mamad", "service", "roof", "interior", "acoustic", "fire", "spa", "wine"]

DOOR_SPEC = {
    "pivot": dict(
        name="דלת כניסה – ציר מרכזי",
        type="דלת ציר מרכזי (Pivot)",
        leaf='כנף מבודדת 100 מ"מ, חיפוי לוחות אלון מלא אנכיים, לכה ימית UV',
        frame='משקוף אלומיניום סמוי, ציר רצפתי הידראולי',
        hw='מנעול חכם (טביעת אצבע + אפליקציה), נעילה רב-נקודתית, ידית משיכה נירוסטה 316 L=180',
        note="סף נגיש, אטימה היקפית, מתחת לגגון בטון"),
    "mamad": dict(
        name='דלת ממ"ד',
        type='דלת הדף ואטימה לממ"ד',
        leaf='פלדה, מאושרת ע"י פיקוד העורף',
        frame='משקוף פלדה יצוק בקיר בטון מזוין',
        hw='ידיות נעילה (בריחים), אטם גומי היקפי',
        note='פתיחה החוצה מהממ"ד · לפי הנחיות פקע"ר העדכניות'),
    "service": dict(
        name="דלת שירות חיצונית",
        type="דלת אלומיניום חיצונית",
        leaf="פנל אלומיניום תרמי מבודד, ברונזה כהה, מפרט ימי",
        frame="משקוף אלומיניום תרמי, סף אטימה",
        hw="מנעול רב-בריחי, צילינדר מאסטר, מחזיר",
        note="כניסת שירות למזווה"),
    "roof": dict(
        name="דלת יציאה לגג",
        type="דלת אלומיניום חיצונית מזוגגת",
        leaf="אלומיניום תרמי + זיגוג בידודי מחוסם, ברונזה כהה",
        frame='סף מוגבה 5 ס"מ + אטימה למים',
        hw="מנעול רב-נקודתי, מחזיר הידראולי",
        note="יציאה למרפסת הגג"),
    "interior": dict(
        name="דלת פנים",
        type="דלת פנים לבודה",
        leaf='כנף לבודה 45 מ"מ, לכה לבנה מט / פורניר אלון',
        frame="משקוף עץ סמוי (Flush) בגובה הכנף",
        hw="ידית נירוסטה מוברשת, מנעול מגנטי שקט",
        note=""),
    "acoustic": dict(
        name="דלת אקוסטית",
        type="דלת אקוסטית",
        leaf='כנף מלאה 60 מ"מ, Rw≥40dB, חיפוי בד אקוסטי',
        frame="משקוף פלדה, אטמים כפולים + סף נשמט",
        hw="ידית נירוסטה, מחזיר שקט",
        note="קולנוע ביתי"),
    "fire": dict(
        name="דלת חדר טכני",
        type="דלת פלדה עמידת אש",
        leaf="פלדה מבודדת, עמידות אש 30 דק'",
        frame="משקוף פלדה, אטם עשן",
        hw="מחזיר הידראולי, ידית + צילינדר",
        note="חדר טכני"),
    "spa": dict(
        name="דלת ספא",
        type="דלת זכוכית",
        leaf='זכוכית מחוסמת 10 מ"מ חלבית',
        frame="צירי נירוסטה 316, אטם לחות",
        hw="ידית משיכה נירוסטה",
        note="ספא – אזור רטוב"),
    "wine": dict(
        name="דלת מרתף יין",
        type="דלת זכוכית מבודדת",
        leaf="מסגרת פלדה שחורה + זיגוג בידודי",
        frame="אטם תרמי היקפי",
        hw="ידית משיכה, מנעול",
        note="מרתף יין מבוקר טמפרטורה"),
}


def door_category(d):
    if d.kind == "pivot":
        return "pivot"
    if d.kind == "mamad_door":
        return "mamad"
    if d.exterior:
        return "roof" if d.level == "R" else "service"
    n = d.room
    if "קולנוע" in n:
        return "acoustic"
    if "טכני" in n:
        return "fire"
    if "ספא" in n:
        return "spa"
    if "יין" in n:
        return "wine"
    return "interior"


def _wet(name):
    return any(s in name for s in ("רחצ", "שירותי"))


class DoorItem:
    def __init__(self, key, insts):
        self.cat, self.wc, self.hc = key
        self.insts = insts
        self.rep = insts[0]
        self.w, self.h = self.rep.wm, self.rep.hm
        self.qty = len(insts)
        s = DOOR_SPEC[self.cat]
        tags = ", ".join(i.tag or "?" for i in insts)
        notes = [s["note"]] if s["note"] else []
        if self.cat == "interior":
            wet = sum(1 for i in insts if _wet(i.room))
            if wet:
                notes.append("חדרי רחצה: נעילת פנוי/תפוס + מרווח אוורור תחתון")
            if not notes:
                notes.append("—")
        self.title = f'{s["name"]} {self.wc}/{self.hc}'
        self.spec = OrderedDict(
            tags=tags,
            type=s["type"],
            leaf=s["leaf"],
            frame=s["frame"],
            hw=s["hw"],
            size=f"{self.wc}/{self.hc}",
            qty=f"{self.qty} יח' · {_floors(insts)}",
            note=" · ".join(notes),
        )


# --------------------------------------------------------------------------- #
#  Audit
# --------------------------------------------------------------------------- #
def audit(data=None):
    import re
    data = data or collect()
    issues = []
    alls = data["alu"] + data["doors"]
    for it in data["alu_items"]:
        if it.tag.startswith("?"):
            issues.append(f"פתח אלומיניום ללא סימון: {it.tag[1:]} ({len(it.insts)} יח')")
        kinds = {i.kind for i in it.insts}
        if len(kinds) > 1:
            issues.append(f"{it.tag}: סוגים שונים לאותו סימון {sorted(kinds)}")
        if len(it.sizes) > 1 or len(it.sills) > 1:
            issues.append(f"{it.tag}: מידות שונות לאותו סימון: "
                          + ", ".join(f"{LEVEL_HE[l]} {w}/{h} אדן {s}" for (l, w, h, s) in it.variants))
        if len({i.frosted for i in it.insts}) > 1:
            issues.append(f"{it.tag}: זיגוג חלבי לא אחיד")
    for d in data["doors"]:
        if not d.tag:
            issues.append(f"דלת ללא סימון ({LEVEL_HE[d.level]}, {d.room} {d.wc}/{d.hc})")
    tags_d = Counter(d.tag for d in data["doors"] if d.tag)
    for t, c in tags_d.items():
        if c > 1:
            issues.append(f"{t}: סימון דלת כפול ({c} יח')")
    for i in alls:
        if i.tag and i.kind in DOOR_KINDS and not (i.tag.startswith("D-") or i.tag.startswith("M-")):
            issues.append(f"{i.tag}: דלת עם קידומת לא תקנית")
        if i.tag and i.kind in ALU_KINDS and not (i.tag.startswith("AL-") or i.tag.startswith("M-")):
            issues.append(f"{i.tag}: אלומיניום עם קידומת לא תקנית")
        if not i.room:
            issues.append(f"{i.tag or i.kind}: לא נמצא חדר צמוד ({LEVEL_HE[i.level]})")
        if i.wm <= 0 or i.hm <= 0:
            issues.append(f"{i.tag}: מידה לא חוקית {i.wc}/{i.hc}")
        # wall extents / storey height
        w = i.w
        if i.o.pos < w.a0 - 0.01 or i.o.end > w.a1 + 0.01:
            issues.append(f"{i.tag}: חורג מאורך הקיר")
        top = w.z1 - M.LV[w.level]
        if i.o.head > top + 0.01:
            issues.append(f"{i.tag}: משקוף {i.o.head:.2f} מעל תקרת הקונסטרוקציה ({top:.2f})")
        if i.room_obj is not None and not i.room_obj.outdoor and i.o.head > i.room_obj.ceil + 0.01:
            issues.append(f"{i.tag}: משקוף {i.o.head:.2f} גבוה מתקרת החדר {i.room_obj.name} ({i.room_obj.ceil:.2f})")
    for d in data["doors"]:
        if not d.exterior and (d.sides[1] is None or d.sides[-1] is None):
            issues.append(f"{d.tag}: בצד אחד של הדלת אין חדר מוגדר במודל ({LEVEL_HE[d.level]}, {d.room})")
        if not d.exterior and _wet(d.other) and not _wet(d.room):
            issues.append(f"{d.tag}: הגישה ל{d.room} היא דרך {d.other} (חדר רטוב) – לבדוק תכנון")
    for i in alls:
        for s_ in (1, -1):
            r = i.sides.get(s_)
            if r is not None and getattr(r, "pseudo", False):
                issues.append(f"{i.tag}: {r.name} בקומה {LEVEL_HE[i.level]} אינו מוגדר כחדר במודל")
    # same tag stacked vertically (continuous glazing split per floor) – overlaps / gaps
    by_tag = {}
    for i in data["alu"]:
        if i.tag:
            by_tag.setdefault(i.tag, []).append(i)
    for t, lst in by_tag.items():
        col = sorted(lst, key=lambda i: M.LV[i.level] + i.o.sill)
        for a, b in zip(col, col[1:]):
            if a.w.horiz == b.w.horiz and abs(a.w.c - b.w.c) < 0.3 and abs(a.o.pos - b.o.pos) < 0.05:
                za, zb = M.LV[a.level] + a.o.head, M.LV[b.level] + b.o.sill
                if za > zb + 0.01:
                    issues.append(f"{t}: חלקי הזיגוג הרציף חופפים {(za - zb) * 100:.0f} ס\"מ בין קומה "
                                  f"{LEVEL_HE[a.level]} ל{LEVEL_HE[b.level]} (משקוף {za:+.2f} / אדן {zb:+.2f})")
                elif zb > za + 0.01:
                    issues.append(f"{t}: פער {(zb - za) * 100:.0f} ס\"מ בזיגוג הרציף בין {LEVEL_HE[a.level]} ל{LEVEL_HE[b.level]}")
    # overlaps on the same wall
    for w in M.WALLS:
        ops = sorted([o for o in w.openings], key=lambda o: o.pos)
        for a, b in zip(ops, ops[1:]):
            if b.pos < a.end - 0.01 and min(a.head, b.head) > max(a.sill, b.sill):
                issues.append(f"חפיפה בין פתחים {a.tag or a.kind} / {b.tag or b.kind}")
    # numbering gaps inside a decade
    fam = {}
    for i in alls:
        m = re.match(r"([A-Z]+-[A-Z]*)(\d+)$", i.tag or "")
        if m:
            n = int(m.group(2))
            fam.setdefault((m.group(1), n // 10), set()).add(n)
    for (pre, dec), nums in sorted(fam.items()):
        lo = max(min(nums), dec * 10 + (1 if dec == 0 or pre.endswith("B") else 0))
        miss = [n for n in range(lo, max(nums) + 1) if n not in nums]
        if miss:
            issues.append(f"מספור חסר: " + ", ".join(f"{pre}{n:02d}" if not pre.endswith('B') else f"{pre}{n}"
                                                       for n in miss))
    # regulation checks
    for i in data["alu"]:
        if i.kind == "mamad_win" and (i.wc > 100 or i.hc > 100):
            issues.append(f'{i.tag}: חלון ממ"ד {i.wc}/{i.hc} חורג מ-100/100')
    for d in data["doors"]:
        if d.kind == "mamad_door" and (d.wc, d.hc) != (80, 200):
            issues.append(f'{d.tag}: דלת ממ"ד {d.wc}/{d.hc} (נדרש 80/200)')
        if d.kind == "pivot" and (d.wc, d.hc) != (140, 290):
            issues.append(f"{d.tag}: דלת ציר מרכזי {d.wc}/{d.hc} (מתוכנן 140/290)")
    # hidden shutter boxes need ~25 cm above the head
    for it in data["alu_items"]:
        if "תריס" in it.spec["shade"] and "פלדה" not in it.spec["shade"]:
            for i in it.insts:
                room_left = i.w.z1 - (M.LV[i.level] + i.o.head)
                if room_left < 0.25:
                    issues.append(f"{i.tag}: אין מקום לארגז תריס נסתר מעל המשקוף "
                                  f"({room_left * 100:.0f} ס\"מ עד תחתית התקרה) – נדרש שקע בתקרה/קורה")
                    break
    for s in data["skipped"]:
        if s.tag:
            issues.append(f"{s.tag}: פתח מסוג '{s.kind}' עם סימון – לא נכלל ברשימה")
    return list(dict.fromkeys(issues))


# --------------------------------------------------------------------------- #
#  Drawing helpers (paper mm)
# --------------------------------------------------------------------------- #
def dim_h(sh, xs, y, labels=None, size=2.0, ext_y=None):
    xs = list(xs)
    sh.line(xs[0] - 1.0, y, xs[-1] + 1.0, y, lw="xs", color=INK)
    for x in xs:
        sh.line(x - 0.6, y + 0.6, x + 0.6, y - 0.6, lw="s", color=INK)
        if ext_y is not None:
            d = 1 if ext_y > y else -1
            sh.line(x, ext_y - d * 0.7, x, y - d * 1.0, lw="xxs", color="#555")
    for k, (a, b) in enumerate(zip(xs, xs[1:])):
        s = labels[k] if labels else ""
        sh.text((a + b) / 2, y - 0.6, s, size=size, color=INK)


def dim_v(sh, ys, x, labels, size=2.0, ext_x=None):
    """ys: paper y list (any order) with matching labels for consecutive segments (top→bottom)."""
    ys = list(ys)
    sh.line(x, min(ys) - 1.0, x, max(ys) + 1.0, lw="xs", color=INK)
    for y in ys:
        sh.line(x - 0.6, y + 0.6, x + 0.6, y - 0.6, lw="s", color=INK)
        if ext_x is not None:
            d = 1 if ext_x > x else -1
            sh.line(ext_x - d * 0.7, y, x - d * 1.0, y, lw="xxs", color="#555")
    for k, (a, b) in enumerate(zip(ys, ys[1:])):
        s = labels[k]
        ym = (a + b) / 2
        if abs(b - a) < tw(s, size) + 0.6:
            # too short – write beside the dim line
            sh.text(x - 0.6, ym + size * 0.35, s, size=size * 0.9, anchor="right", color=INK)
        else:
            sh.text(x - 0.6, ym, s, size=size, rot=-90, color=INK)


def arrow(sh, x0, y, x1, lift=False, color=INK):
    d = 1 if x1 > x0 else -1
    L = abs(x1 - x0)
    hl = min(1.8, L * 0.3)
    sh.line(x0, y, x1 - d * hl * 0.6, y, lw="s", color=color)
    sh.path(f"M{x1:.3f},{y:.3f} L{x1 - d * hl:.3f},{y - hl * 0.42:.3f} L{x1 - d * hl:.3f},{y + hl * 0.42:.3f} Z",
            color="none", fill=color)
    if lift:
        sh.line(x0, y, x0, y - 2.2, lw="s", color=color)
        sh.path(f"M{x0:.3f},{y - 3.0:.3f} L{x0 - 0.6:.3f},{y - 1.9:.3f} L{x0 + 0.6:.3f},{y - 1.9:.3f} Z",
                color="none", fill=color)


def tri_side(sh, x0, y0, x1, y1, hinge, dashed=True, color=INK):
    """Side-hung symbol: apex on the hinge side, lines to the opposite corners."""
    ym = (y0 + y1) / 2
    if hinge == "l":
        pts = [(x1, y0), (x0, ym), (x1, y1)]
    else:
        pts = [(x0, y0), (x1, ym), (x0, y1)]
    sh.polyline(pts, lw="xs", color=color, dash="1.2 0.7" if dashed else None)


def tri_tilt(sh, x0, y0, x1, y1, dashed=True, color=INK):
    """Bottom-hung (tilt) symbol: apex at the bottom centre."""
    sh.polyline([(x0, y0), ((x0 + x1) / 2, y1), (x1, y0)], lw="xs", color=color, dash="1.2 0.7" if dashed else None)


def draw_alu(sh, x0, yfloor, k, item, size=2.0):
    """Elevation of an aluminium unit seen from outside. x0 = left edge, yfloor = paper y of floor."""
    w, h, sill = item.w, item.h, item.sill
    W, Hh = w * k, h * k
    top = yfloor - (sill + h) * k
    bot = yfloor - sill * k
    F = (0.07 if item.kind == "slide" else 0.05) * k
    Mu = 0.035 * k
    S = 0.06 * k
    sh.rect(x0, top, W, Hh, lw="m", color="#000", fill=BRONZE)
    glass_fill = FROST if item.frosted else GLASS

    def X(u):
        return x0 + u * k

    def Y(v):
        return bot - v * k

    for p in item.panels:
        a0 = X(p["u0"]) + (F if p["u0"] <= 1e-6 else Mu / 2)
        a1 = X(p["u1"]) - (F if p["u1"] >= w - 1e-6 else Mu / 2)
        b1 = Y(p["v0"]) - (F if p["v0"] <= 1e-6 else Mu / 2)    # bottom (paper)
        b0 = Y(p["v1"]) + (F if p["v1"] >= h - 1e-6 else Mu / 2)  # top (paper)
        t = p["t"]
        if t == "spandrel":
            sh.rect(a0, b0, a1 - a0, b1 - b0, lw="xs", color="#000", fill=SPANDREL)
            if (b1 - b0) > size * 1.3 and tw("ספנדרל", 2.0) < (a1 - a0) - 1:
                sh.text((a0 + a1) / 2, (b0 + b1) / 2 + 0.7, "ספנדרל", size=2.0, color="#333")
            continue
        if t in ("slide", "tt", "tilt"):
            sh.rect(a0, b0, a1 - a0, b1 - b0, lw="xs", color="#000", fill=BRONZE)
            g0, g1, h0, h1 = a0 + S, a1 - S, b0 + S, b1 - S
        else:
            g0, g1, h0, h1 = a0, a1, b0, b1
        sh.rect(g0, h0, g1 - g0, h1 - h0, lw="xs", color="#000", fill=glass_fill)
        gw, gh = g1 - g0, h1 - h0
        if t == "fixed":
            fs = max(2.0, size)
            if gw > tw("קבוע", fs) + 1.0 and gh > fs * 1.2:
                sh.text((g0 + g1) / 2, (h0 + h1) / 2 + fs * 0.35, "קבוע", size=fs, color="#333")
            elif gh > tw("קבוע", fs) + 1.0:
                sh.text((g0 + g1) / 2 + fs * 0.35, (h0 + h1) / 2, "קבוע", size=fs, color="#333", rot=-90)
        elif t == "slide":
            ya = h1 - min(gh * 0.45, 1.1 * k)
            L = gw * 0.55
            cx = (g0 + g1) / 2
            if p["dir"] < 0:
                arrow(sh, cx + L / 2, ya, cx - L / 2, lift=p.get("lift"))
            else:
                arrow(sh, cx - L / 2, ya, cx + L / 2, lift=p.get("lift"))
        elif t == "tt":
            tri_side(sh, g0, h0, g1, h1, p["hinge"], dashed=True)
            tri_tilt(sh, g0, h0, g1, h1, dashed=True)
        elif t == "tilt":
            tri_tilt(sh, g0, h0, g1, h1, dashed=True)
    sh.rect(x0, top, W, Hh, lw="m", color="#000")
    if item.kind == "mamad_win":
        # steel shutter / blast window outline (outside the aluminium)
        sh.rect(x0 - 1.2, top - 1.2, W + 2.4, Hh + 2.4, lw="xs", color="#000", dash="2 0.8 0.4 0.8")
    return top, bot


def draw_door(sh, x0, yfloor, k, item, size=2.0):
    w, h = item.w, item.h
    W, Hh = w * k, h * k
    top = yfloor - Hh
    cat = item.cat
    hr = item.rep.hinge_right
    hinge = "r" if hr else "l"
    if cat == "pivot":
        F = 0.04 * k
        sh.rect(x0, top, W, Hh, lw="m", color="#000", fill=BRONZE)
        l0, l1, t0 = x0 + F, x0 + W - F, top + F
        sh.rect(l0, t0, l1 - l0, yfloor - t0, lw="xs", color="#000", fill=OAK)
        n = max(4, int((l1 - l0) / (0.14 * k)))
        for i in range(1, n):
            xx = l0 + (l1 - l0) * i / n
            sh.line(xx, t0, xx, yfloor, lw="xxs", color="#8a6a44")
        ax = (l1 - (l1 - l0) * 0.2) if hr else (l0 + (l1 - l0) * 0.2)   # pivot axis
        sh.line(ax, top - 1.5, ax, yfloor + 1.5, lw="xs", color="#000", dash="3 0.8 0.5 0.8")
        ym = (t0 + yfloor) / 2
        far = l0 if hr else l1
        near = l1 if hr else l0
        sh.polyline([(far, t0), (ax, ym), (far, yfloor)], lw="xs", color=INK)
        sh.polyline([(near, t0), (ax, ym), (near, yfloor)], lw="xs", color=INK, dash="1.2 0.7")
        hx = far + (1.6 if not hr else 1.6) * (1 if far == l0 else -1)
        sh.rect(hx - 0.35, yfloor - 2.1 * k, 0.7, 1.8 * k, lw="xs", color="#000", fill="#d9d9d9")
        return top
    if cat == "mamad":
        F = 0.08 * k
        sh.rect(x0, top, W, Hh, lw="m", color="#000", fill="#6d7378")
        l0, l1, t0 = x0 + F, x0 + W - F, top + F
        sh.rect(l0, t0, l1 - l0, yfloor - t0, lw="xs", color="#000", fill=STEEL)
        tri_side(sh, l0, t0, l1, yfloor, hinge, dashed=False)
        hx = (l0 + 1.2) if hinge == "r" else (l1 - 1.2 - 2.4)
        for f in (0.33, 0.66):
            yy = t0 + (yfloor - t0) * f
            sh.rect(hx, yy - 0.35, 2.4, 0.7, lw="xs", color="#000", fill="#333")
        return top
    # generic doors
    F = 0.05 * k
    frame_fill = {"service": BRONZE, "roof": BRONZE, "fire": "#6d7378", "acoustic": "#6d6259"}.get(cat, "#e7e1d6")
    leaf_fill = {"service": "#6b5d51", "roof": GLASS, "fire": STEEL, "acoustic": "#d9cfc0",
                 "spa": FROST, "wine": GLASS}.get(cat, LEAF)
    sh.rect(x0, top, W, Hh, lw="m", color="#000", fill=frame_fill)
    l0, l1, t0 = x0 + F, x0 + W - F, top + F
    sh.rect(l0, t0, l1 - l0, yfloor - t0, lw="xs", color="#000", fill=leaf_fill)
    if cat == "roof":
        g = 0.09 * k
        sh.rect(l0 + g, t0 + g, l1 - l0 - 2 * g, (yfloor - t0) * 0.62, lw="xs", color="#000", fill=GLASS)
    if cat == "wine":
        g = 0.06 * k
        sh.rect(l0 + g, t0 + g, l1 - l0 - 2 * g, yfloor - t0 - 2 * g, lw="xs", color="#000", fill=GLASS)
        sh.rect(l0, t0, l1 - l0, yfloor - t0, lw="s", color="#111")
    tri_side(sh, l0, t0, l1, yfloor, hinge, dashed=False)
    # handle on the lock side
    hy = yfloor - 1.05 * k
    hx = (l0 + 0.8) if hinge == "r" else (l1 - 0.8)
    d = 1 if hinge == "r" else -1
    sh.line(hx, hy, hx + d * 2.2, hy, lw="m", color="#000")
    return top


# --------------------------------------------------------------------------- #
#  Band layout
# --------------------------------------------------------------------------- #
class Cfg:
    def __init__(self, scale, ts, minw):
        self.scale = scale
        self.k = 1000.0 / scale
        self.ts = ts              # body text size
        self.minw = minw          # minimum column width
        self.pad = 1.3
        self.pitch = ts * 1.32
        self.label_w = 21.0
        self.hdr_h = 6.8


ALU_ROWS = [("type", "סוג"), ("system", "מערכת / גמר"), ("glass", "זיגוג"), ("shade", "הצללה"),
            ("size", "מידות ר/ג · אדן"), ("qty", "כמות · קומה"), ("loc", "מיקום · חזית"), ("note", "הערות")]
DOOR_ROWS = [("tags", "סימונים"), ("type", "סוג"), ("leaf", "כנף וגמר"), ("frame", "משקוף"), ("hw", "פרזול"),
             ("size", "מידות ר/ג"), ("qty", "כמות · קומה"), ("note", "הערות")]
BOLD_ROWS = {"qty", "tags", "size"}


def _col(item, cfg, door=False):
    k = cfg.k
    multi = (not door) and len({(p["u0"], p["u1"]) for p in item.panels if p["t"] != "spandrel"}) > 1
    elev_w = item.w * k + 7.5
    nat = max(cfg.minw, elev_w + 6)
    # longest unbreakable token must fit
    tok = max(longest_token(v, cfg.ts, 600 if r in BOLD_ROWS else 400) for r, v in item.spec.items())
    nat = max(nat, tok + 2 * cfg.pad + 1)
    return dict(item=item, nat=nat, w=nat, door=door, multi=multi)


def pack(cols, avail):
    bands, cur, cw = [], [], 0.0
    for c in cols:
        if cur and cw + c["nat"] > avail + 1e-6:
            bands.append(cur)
            cur, cw = [], 0.0
        cur.append(c)
        cw += c["nat"]
    if cur:
        bands.append(cur)
    return bands


def stretch(band, avail, last=False):
    tot = sum(c["nat"] for c in band)
    extra = avail - tot
    if last:
        extra = min(extra, sum(c["nat"] for c in band) * 0.25)
    for c in band:
        c["w"] = c["nat"] + extra * c["nat"] / tot
    return sum(c["w"] for c in band)


def elev_zone(band, cfg, door=False):
    k = cfg.k
    if door:
        heads = [c["item"].h for c in band]
        base = 0.0
    else:
        heads = [c["item"].sill + c["item"].h for c in band]
        base = min(0.0, min(c["item"].sill for c in band))
    dims_above = max((9.0 if c["multi"] else 4.8) for c in band)
    zh = 3.0 + dims_above + (max(heads) - base) * k + 3.0 + (2.5 if base < 0 else 0)
    return zh, base


def band_rows_h(band, rows, cfg):
    hs = []
    for key, _lbl in rows:
        n = 1
        for c in band:
            wgt = 600 if key in BOLD_ROWS else 400
            n = max(n, len(wrap(c["item"].spec[key], cfg.ts, c["w"] - 2 * cfg.pad, wgt)))
        lab_n = len(wrap(_lbl, cfg.ts, cfg.label_w - 2 * cfg.pad, 700))
        n = max(n, lab_n)
        hs.append(n * cfg.pitch + 2 * cfg.pad - (cfg.pitch - cfg.ts) + 0.4)
    return hs


def render_band(sh, xr, y, band, rows, cfg, door=False, elev_label=""):
    """Draw one band whose right edge is xr; columns flow right → left. Returns height."""
    k = cfg.k
    total_w = cfg.label_w + sum(c["w"] for c in band)
    x0 = xr - total_w
    zh, base = elev_zone(band, cfg, door)
    rh = band_rows_h(band, rows, cfg)
    H = cfg.hdr_h + zh + sum(rh)
    ts = cfg.ts
    # backgrounds
    sh.rect(xr - cfg.label_w, y, cfg.label_w, H, lw="xs", color="none", fill=LBL)
    sh.rect(x0, y, total_w - cfg.label_w, cfg.hdr_h, lw="xs", color="none", fill=HDR)
    # label column texts
    lx = xr - cfg.pad
    sh.text(lx, y + cfg.hdr_h / 2 + ts * 0.4, "סימון", size=ts + 0.2, anchor="right", weight=700)
    yy = y + cfg.hdr_h
    for i, ln in enumerate(wrap(elev_label, ts, cfg.label_w - 2 * cfg.pad, 700)):
        sh.text(lx, yy + 4 + ts + i * cfg.pitch, ln, size=ts, anchor="right", weight=700)
    # floor-line legend in label column
    yfl = yy + zh - 3.0 - (2.5 if base < 0 else 0) + base * k
    sh.line(xr - cfg.label_w + 1.5, yfl, xr - 1.5, yfl, lw="xs", color="#777", dash="3 1 0.6 1")
    sh.text(lx, yfl - 1.0, 'ר.ג. קומה', size=max(2.0, ts * 0.95), anchor="right", color="#555")
    yy += zh
    for (key, lbl), hh in zip(rows, rh):
        for i, ln in enumerate(wrap(lbl, ts, cfg.label_w - 2 * cfg.pad, 700)):
            sh.text(lx, yy + cfg.pad + ts * 0.85 + i * cfg.pitch, ln, size=ts, anchor="right", weight=700)
        yy += hh
    # columns
    cx_r = xr - cfg.label_w
    for c in band:
        it = c["item"]
        cw = c["w"]
        cx0 = cx_r - cw
        # header
        title = it.tag if not door else it.title
        hs = 3.4 if not door else ts + 0.3
        while tw(title, hs, 700) > cw - 2 and hs > ts:
            hs -= 0.2
        sh.text(cx0 + cw / 2, y + cfg.hdr_h / 2 + hs * 0.36, title, size=hs, weight=700)
        # elevation
        zy0 = y + cfg.hdr_h
        yfloor = zy0 + zh - 3.0 - (2.5 if base < 0 else 0) + base * k
        sh.line(cx0 + 1.5, yfloor, cx0 + cw - 1.5, yfloor, lw="xs", color="#777", dash="3 1 0.6 1")
        uw = it.w * k
        bx0 = cx0 + (cw - (uw + 7.5)) / 2 + 7.5   # unit left edge (dims on the left)
        if door:
            top = draw_door(sh, bx0, yfloor, k, it, size=ts)
            dim_v(sh, [top, yfloor], bx0 - 4.0, [f"{it.hc}"], size=ts, ext_x=bx0)
            dim_h(sh, [bx0, bx0 + uw], top - 3.8, [f"{it.wc}"], size=ts, ext_y=top)
        else:
            top, bot = draw_alu(sh, bx0, yfloor, k, it, size=ts)
            # vertical chain: floor → sill → transoms → head
            vs = sorted({0.0, it.sill, it.sill + it.h} |
                        {round(it.sill + p["v1"], 3) for p in it.panels
                         if p.get("guard") or p["t"] == "spandrel"})
            ys = [yfloor - v * k for v in reversed(vs)]
            labs = [f"{(b - a) * 100:.0f}" for a, b in zip(reversed(vs[:-1]), reversed(vs[1:]))]
            labs = [f"{(vs[i + 1] - vs[i]) * 100:.0f}" for i in reversed(range(len(vs) - 1))]
            dim_v(sh, ys, bx0 - 4.0, labs, size=ts, ext_x=bx0)
            # widths: panel chain + overall
            if c["multi"]:
                us = sorted({round(p["u0"], 4) for p in it.panels} | {round(p["u1"], 4) for p in it.panels})
                xs = [bx0 + u * k for u in us]
                labs = [f"{(b - a) * 100:.0f}" for a, b in zip(us, us[1:])]
                dim_h(sh, xs, top - 3.6, labs, size=ts * 0.92, ext_y=top)
                dim_h(sh, [bx0, bx0 + uw], top - 8.2, [f"{it.wc}"], size=ts, ext_y=top - 3.6)
            else:
                dim_h(sh, [bx0, bx0 + uw], top - 3.8, [f"{it.wc}"], size=ts, ext_y=top)
        # spec texts
        yy = zy0 + zh
        for (key, _l), hh in zip(rows, rh):
            wgt = 600 if key in BOLD_ROWS else 400
            for i, ln in enumerate(wrap(it.spec[key], ts, cw - 2 * cfg.pad, wgt)):
                sh.text(cx0 + cw - cfg.pad, yy + cfg.pad + ts * 0.85 + i * cfg.pitch, ln, size=ts,
                        anchor="right", weight=wgt)
            yy += hh
        sh.line(cx0, y, cx0, y + H, lw="xs", color="#000")
        cx_r = cx0
    # grid
    sh.line(x0, y + cfg.hdr_h, xr, y + cfg.hdr_h, lw="s", color="#000")
    yy = y + cfg.hdr_h + zh
    sh.line(x0, yy, xr, yy, lw="s", color="#000")
    for hh in rh[:-1]:
        yy += hh
        sh.line(x0, yy, xr, yy, lw="xxs", color="#666")
    sh.line(xr - cfg.label_w, y, xr - cfg.label_w, y + H, lw="s", color="#000")
    sh.rect(x0, y, total_w, H, lw="m", color="#000")
    return H


# --------------------------------------------------------------------------- #
#  Door list table, legend, notes
# --------------------------------------------------------------------------- #
DOOR_TABLE_COLS = [("tag", "מס'", 12), ("room", "חדר", 27), ("from", "גישה מ-", 24), ("lvl", "קומה", 10),
                   ("size", "ר/ג", 14), ("hand", "כיוון", 10), ("cat", "סוג", 27)]


def door_table(sh, xr, y, doors, cfg):
    ts = cfg.ts
    rh = ts * 1.75
    W = sum(c[2] for c in DOOR_TABLE_COLS)
    x0 = xr - W
    sh.text(xr, y + ts + 1.6, "טבלת דלתות", size=ts + 1.4, anchor="right", weight=700)
    y0 = y + ts + 4.0
    H = rh * (len(doors) + 1)
    sh.rect(x0, y0, W, rh, lw="xs", color="none", fill=HDR)
    x = xr
    for key, lbl, cw in DOOR_TABLE_COLS:
        sh.text(x - cw / 2, y0 + rh / 2 + ts * 0.36, lbl, size=ts, weight=700)
        x -= cw
    for r, d in enumerate(doors):
        yy = y0 + rh * (r + 1)
        if r % 2:
            sh.rect(x0, yy, W, rh, color="none", fill="#faf8f4")
        vals = dict(tag=d.tag or "?", room=d.room or "—", frm=d.other or "—", lvl=LEVEL_HE[d.level], size=f"{d.wc}/{d.hc}",
                    hand=("—" if d.kind == "pivot" else d.hand), cat=DOOR_SPEC[door_category(d)]["name"])
        vals["from"] = vals.pop("frm")
        x = xr
        for key, lbl, cw in DOOR_TABLE_COLS:
            s = vals[key]
            fs = ts
            while tw(s, fs, 600 if key == "tag" else 400) > cw - 1.6 and fs > 2.0:
                fs -= 0.1
            if tw(s, fs) > cw - 1.6:
                while s and tw(s + "…", fs) > cw - 1.6:
                    s = s[:-1]
                s += "…"
            sh.text(x - cw / 2, yy + rh / 2 + fs * 0.36, s, size=fs, weight=600 if key == "tag" else 400)
            x -= cw
    # grid
    for r in range(len(doors) + 2):
        sh.line(x0, y0 + rh * r, xr, y0 + rh * r, lw="xxs" if 0 < r <= len(doors) else "s", color="#000")
    x = xr
    for key, lbl, cw in DOOR_TABLE_COLS:
        sh.line(x, y0, x, y0 + H, lw="xxs", color="#000")
        x -= cw
    sh.rect(x0, y0, W, H, lw="m", color="#000")
    note = "כיוון: ימין/שמאל = צד הצירים במבט מצד הפתיחה"
    sh.text(xr, y0 + H + ts + 1.2, note, size=ts, anchor="right", color="#444")
    return W, (y0 - y) + H + ts + 2.0


LEGEND = [
    ("lift", "הרמה-הזזה – חץ בכיוון הפתיחה"),
    ("slide", "הזזה"),
    ("tt", "ציר-נטוי – קודקוד המשולש בצד הצירים"),
    ("tilt", "נטוי (קיפ) – צירים בתחתית הכנף"),
    ("dash", "קו מקווקו – נפתח פנימה (הרחק מהצופה)"),
    ("solid", "קו רציף – נפתח לכיוון הצופה"),
    ("fixed", "קבוע – זיגוג ללא כנף"),
    ("pivot", "ציר מרכזי – קו ציר נקודה-קו"),
    ("spand", "ספנדרל – פנל אטום מול תקרה"),
    ("floor", "קו רצפה גמורה של הקומה (ר.ג.)"),
]

NOTES = [
    'כל המידות בס"מ. מידות הפתחים לפי המודל; מידות ייצור – לפי מדידה באתר ואישור דוגמאות.',
    "אלומיניום: פרופילים תרמיים עם גשר תרמי (Thermal Break), צבע אבקה אלקטרוסטטי בגוון ברונזה כהה,"
    " מפרט ימי (Seaside) – טיפול מקדים מוגבר לסביבה ימית. הסדרות המצוינות הן 'דוגמת' בלבד.",
    "פרזול, ברגים ועוגנים – נירוסטה 316; אטמי EPDM; משקוף עיוור ואיטום היקפי בכל הפתחים החיצוניים.",
    "זיגוג: Low-E בצד הפנימי של הזכוכית החיצונית, מרווח ארגון; זכוכית בטיחותית (מחוסמת/שכבתית)"
    " בכל זיגוג עד רצפה, בדלתות ובמקטעים נמוכים – לפי התקנים הישראליים.",
    "תריסי גלילה חשמליים נסתרים – ארגז בשקע בתקרה/בקורה מעל המשקוף; רפפות אנכיות מאלומיניום דמוי עץ"
    " 50/200 @180 בחזיתות מערב ומזרח של קומה א'.",
    'חלון ודלת ממ"ד – לפי הנחיות פיקוד העורף העדכניות; האלומיניום אינו חלק ממערך המיגון.',
    "הרשימה מופקת אוטומטית מהמודל הפרמטרי – סימונים, כמויות ומידות לפי מצב המודל.",
]


def legend_symbol(sh, kind, x, y, w, h):
    """Small symbol inside box (x,y,w,h)."""
    g = (x, y, w, h)
    if kind == "floor":
        sh.line(x, y + h * 0.6, x + w, y + h * 0.6, lw="xs", color="#777", dash="3 1 0.6 1")
        return
    if kind == "dash":
        sh.line(x + 1, y + h / 2, x + w - 1, y + h / 2, lw="xs", color=INK, dash="1.2 0.7")
        return
    if kind == "solid":
        sh.line(x + 1, y + h / 2, x + w - 1, y + h / 2, lw="xs", color=INK)
        return
    fill = SPANDREL if kind == "spand" else (OAK if kind == "pivot" else GLASS)
    sh.rect(x, y, w, h, lw="xs", color="#000", fill=fill)
    if kind == "lift":
        arrow(sh, x + w * 0.8, y + h * 0.65, x + w * 0.2, lift=True)
    elif kind == "slide":
        arrow(sh, x + w * 0.2, y + h * 0.55, x + w * 0.8)
    elif kind == "tt":
        tri_side(sh, x, y, x + w, y + h, "l")
        tri_tilt(sh, x, y, x + w, y + h)
    elif kind == "tilt":
        tri_tilt(sh, x, y, x + w, y + h)
    elif kind == "fixed":
        sh.text(x + w / 2, y + h / 2 + 0.7, "קבוע", size=2.0, color="#333")
    elif kind == "pivot":
        ax = x + w * 0.3
        sh.line(ax, y - 0.8, ax, y + h + 0.8, lw="xs", color="#000", dash="3 0.8 0.5 0.8")
        sh.polyline([(x + w, y), (ax, y + h / 2), (x + w, y + h)], lw="xs", color=INK)
        sh.polyline([(x, y), (ax, y + h / 2), (x, y + h)], lw="xs", color=INK, dash="1.2 0.7")


def legend_notes(sh, x, y, w, h_avail, cfg):
    """Legend + general notes in the area (x, y, w); returns height."""
    ts = cfg.ts
    xr = x + w
    sh.text(xr, y + ts + 1.6, "מקרא סימנים", size=ts + 1.4, anchor="right", weight=700)
    yy = y + ts + 4.5
    ncol = 2 if w > 150 else 1
    colw = w / ncol
    rowh = 6.2
    nrows = math.ceil(len(LEGEND) / ncol)
    for i, (kind, txt) in enumerate(LEGEND):
        c, r = divmod(i, nrows)
        cxr = xr - c * colw
        sy = yy + r * rowh
        legend_symbol(sh, kind, cxr - 10.5, sy, 9.0, 4.8)
        sh.text(cxr - 12.5, sy + 3.3, txt, size=ts, anchor="right")
    yy += nrows * rowh + 3.0
    sh.text(xr, yy + ts + 1.6, "הערות כלליות", size=ts + 1.4, anchor="right", weight=700)
    yy += ts + 4.5
    for i, n in enumerate(NOTES):
        lines = wrap(n, ts, w - 6)
        sh.text(xr, yy + ts * 0.9, f"{i + 1}.", size=ts, anchor="right", weight=700)
        for ln in lines:
            sh.text(xr - 4.0, yy + ts * 0.9, ln, size=ts, anchor="right")
            yy += cfg.pitch
        yy += 0.8
    return yy - y


# --------------------------------------------------------------------------- #
#  Sheet composition
# --------------------------------------------------------------------------- #
CONFIGS = [(50, 2.1, 46), (50, 2.0, 42), (50, 2.0, 38), (60, 2.0, 38), (75, 2.0, 36), (100, 2.0, 34)]


def _title(sh, xr, y, title, sub, size=6.2, width=150):
    drawing_title(sh, xr, y + size, title, "", width=width, size=size)
    sh.text(xr - tw(title, size, 700) - 4, y + size, sub, size=3.0, anchor="right", weight=500, color="#333")
    return size + 5.0


def compose(sh, box, data, cfg, spare=0.0):
    x, y, w, h = box
    xr = x + w
    gap = 3.5
    # spare height distributed into the gaps between blocks
    n_gaps_guess = 6
    g_extra = min(6.0, spare / n_gaps_guess) if spare > 0 else 0.0
    alu_items, door_items, doors = data["alu_items"], data["door_items"], data["doors"]
    n_alu = sum(i.qty for i in alu_items)
    yy = y
    th = _title(sh, xr, yy, "רשימת אלומיניום",
                f'חזיתות מבט מבחוץ · קנ"מ 1:{cfg.scale} · {len(alu_items)} פריטים · {n_alu} יח\'')
    yy += th + 1.5 + g_extra * 0.5
    cols = [_col(it, cfg) for it in alu_items]
    avail = w - cfg.label_w
    bands = pack(cols, avail)
    for bi, band in enumerate(bands):
        stretch(band, avail, last=(bi == len(bands) - 1 and len(bands) > 1))
        hh = render_band(sh, xr, yy, band, ALU_ROWS, cfg, door=False, elev_label=f"חזית מבחוץ 1:{cfg.scale}")
        yy += hh + gap + g_extra
    # doors section
    yy += 1.0
    th = _title(sh, xr, yy, "רשימת דלתות ונגרות",
                f'מבט מצד הפתיחה · קנ"מ 1:{cfg.scale} · {len(door_items)} סוגים · {len(doors)} דלתות')
    yy += th + 1.5 + g_extra * 0.5
    dcols = [_col(it, cfg, door=True) for it in door_items]
    tbl_w = sum(c[2] for c in DOOR_TABLE_COLS)
    leg_min = 118.0
    d_avail = w - tbl_w - leg_min - 2 * 6.0 - cfg.label_w
    d_avail = max(d_avail, max(c["nat"] for c in dcols) if dcols else 0)
    dbands = pack(dcols, d_avail)
    widest = max(sum(c["nat"] for c in b) for b in dbands) if dbands else 0
    dy = yy
    for band in dbands:
        stretch(band, widest)
        hh = render_band(sh, xr, dy, band, DOOR_ROWS, cfg, door=True, elev_label=f"מבט 1:{cfg.scale}")
        dy += hh + gap
    dband_w = widest + cfg.label_w
    t_xr = xr - dband_w - 6.0
    tw_, th_ = door_table(sh, t_xr, yy, doors, cfg)
    l_xr = t_xr - tw_ - 6.0
    lh = legend_notes(sh, x, yy, l_xr - x, h, cfg)
    end = max(dy - gap, yy + th_, yy + lh)
    return end - y


def sheet_schedule(sh, box):
    data = collect()
    x, y, w, h = box
    chosen = None
    for sc, ts, mw in CONFIGS:
        cfg = Cfg(sc, ts, mw)
        need = compose(NullSheet(), box, data, cfg)
        if need <= h:
            chosen = (cfg, need)
            break
    if chosen is None:
        cfg = Cfg(*CONFIGS[-1])
        need = compose(NullSheet(), box, data, cfg)
        chosen = (cfg, need)
    cfg, need = chosen
    compose(sh, box, data, cfg, spare=max(0.0, h - need))


if __name__ == "__main__":
    d = collect()
    for it in d["alu_items"]:
        print(it.tag, it.qty, it.sizes, it.sills, it.kind, it.subtype, [i.room for i in it.insts],
              _join_unique(i.facing for i in it.insts), "fins" if it.fins else "")
    for it in d["door_items"]:
        print(it.cat, it.wc, it.hc, [(i.tag, i.room, i.other, i.hand) for i in it.insts])
    print("\nISSUES:")
    for s in audit(d):
        print(" -", s)
    for sc, ts, mw in CONFIGS:
        cfg = Cfg(sc, ts, mw)
        print(sc, ts, mw, round(compose(NullSheet(), (12, 12, 737, 570), d, cfg), 1))
