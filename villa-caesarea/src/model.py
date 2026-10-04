"""Parametric model of 'Beit Kurkar' – a boutique villa in Caesarea.

Single source of truth for every drawing, schedule and 3-D render.
Units: metres. Origin: south-west corner of the lot. X → east, Y → north.
Z: relative to ±0.00 (finished ground-floor level = +18.50 above sea level).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
#  Project data
# --------------------------------------------------------------------------- #
PROJECT = dict(
    name="בית כורכר",
    name_en="BEIT KURKAR",
    subtitle="וילת בוטיק בקיסריה",
    series="וילות בוטיק – קיסריה",
    location="קיסריה, רובע 13 (מגרש לימודי)",
    instructor="שירן שריקי",
    student="__________",
    student_id="__________",
    school="הנדסאים – אדריכלות ועיצוב פנים",
    date="10.2026",
    abs_zero=18.50,
)

LOT = dict(x0=0.0, y0=0.0, x1=30.0, y1=36.0)            # 1,080 m²
SETBACK = dict(front=5.0, side=4.0, rear=6.0)            # front = east (street)
ENVELOPE = (LOT["x0"] + SETBACK["rear"], LOT["y0"] + SETBACK["side"],
            LOT["x1"] - SETBACK["front"], LOT["y1"] - SETBACK["side"])

# Levels (finished floor) and slabs
LV = {"B": -3.50, "G": 0.00, "U": 3.60, "R": 7.00, "RX": 10.00}
FIN = 0.10           # floor finish build-up
SLAB = 0.30          # typical RC slab
RAFT = 0.50          # basement raft
GARDEN = -0.15       # finished garden level
STREET = -0.35       # sidewalk level

T_EXT = 0.30         # exterior wall: 20 block/RC + 10 insulation & cladding
T_CORE = 0.20
T_SKIN = 0.10
T_INT = 0.12
T_RC = 0.20


def slab_top(level):
    return LV[level] - FIN


def slab_bot(level):
    return LV[level] - FIN - SLAB


# --------------------------------------------------------------------------- #
#  Data classes
# --------------------------------------------------------------------------- #
@dataclass
class Opening:
    pos: float            # start along the wall axis (absolute x for horizontal walls, y for vertical)
    end: float            # end along wall axis
    sill: float           # above floor level of the wall's storey
    head: float
    kind: str             # slide | window | fixed | door | pivot | mamad_win | mamad_door | open | passage
    tag: str = ""
    hinge: str = "a"      # 'a' = hinge at start, 'b' = hinge at end
    swing: int = 1        # +1 opens to +normal side (north / east), -1 to the other side
    frosted: bool = False


@dataclass
class Wall:
    x0: float
    y0: float
    x1: float
    y1: float
    t: float
    z0: float
    z1: float
    kind: str = "int"     # ext | int | rc | mamad | shaft | retain | parapet | glass
    out: int = 0          # for ext: +1 exterior on +normal side, -1 on -normal side
    skin: str = ""        # exterior finish: stone | plaster | rc_fair
    skin_z: tuple = None  # (z0, z1) of continuous cladding skin
    openings: list = field(default_factory=list)
    level: str = "G"
    core: str = "block"   # block | rc

    @property
    def horiz(self):
        return abs(self.y1 - self.y0) < 1e-6

    @property
    def a0(self):
        return min(self.x0, self.x1) if self.horiz else min(self.y0, self.y1)

    @property
    def a1(self):
        return max(self.x0, self.x1) if self.horiz else max(self.y0, self.y1)

    @property
    def c(self):
        """centre line coordinate on the other axis"""
        return self.y0 if self.horiz else self.x0


@dataclass
class Room:
    name: str
    level: str
    rects: list               # list of (x0,y0,x1,y1)
    floor: str = "פורצלן 120/120"
    ceil: float = 3.00
    tag_at: tuple = None
    no: str = ""
    service: bool = False
    outdoor: bool = False


@dataclass
class Slab:
    rects: list
    top: float
    t: float
    kind: str = "slab"      # slab | raft | roof | terrace | canopy | deck
    holes: list = field(default_factory=list)
    finish: str = ""


@dataclass
class Column:
    x: float
    y: float
    w: float
    d: float
    z0: float
    z1: float


@dataclass
class Furn:
    kind: str
    level: str
    x: float
    y: float
    w: float
    d: float
    rot: int = 0            # 0/90/180/270 – orientation of the 'front'
    h: float = 0.0
    label: str = ""


# --------------------------------------------------------------------------- #
#  Builder helpers
# --------------------------------------------------------------------------- #
WALLS: list[Wall] = []
ROOMS: list[Room] = []
SLABS: list[Slab] = []
COLS: list[Column] = []
FURN: list[Furn] = []
STAIRS: list[dict] = []
RAILS: list[dict] = []          # glass/steel railings: dict(x0,y0,x1,y1,z0,h,kind)
FINS: list[dict] = []           # vertical louvre fields
PERGOLAS: list[dict] = []
SITE: dict = {}


def storey_z(level):
    """z0/z1 of walls (structural slab top to slab bottom above)."""
    nxt = {"B": "G", "G": "U", "U": "R"}[level]
    return slab_top(level), slab_bot(nxt)


def ext_outline(level, pts, skin, skin_z, core_z=None, rc_segments=()):
    """Exterior walls along a CCW outline (outer faces). Creates walls whose centre line
    is offset T_EXT/2 inward. Returns created walls in edge order."""
    z0, z1 = core_z or storey_z(level)
    made = []
    n = len(pts)

    def centre(i):
        (ax, ay), (bx, by) = pts[i % n], pts[(i + 1) % n]
        if abs(ay - by) < 1e-9:
            inward = 1 if bx > ax else -1
            return ay + inward * T_EXT / 2
        inward = -1 if by > ay else 1
        return ax + inward * T_EXT / 2

    for i in range(n):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
        # inward normal for CCW polygon = left of direction
        dx, dy = bx - ax, by - ay
        if abs(dy) < 1e-9:  # horizontal edge
            inward = 1 if dx > 0 else -1  # left of +x is +y
            c = ay + inward * T_EXT / 2
            e0, e1 = sorted((centre(i - 1), centre(i + 1)))
            w = Wall(e0, c, e1, c, T_EXT, z0, z1, kind="ext", out=-inward,
                     skin=skin, skin_z=skin_z, level=level)
        else:
            inward = -1 if dy > 0 else 1  # left of +y is -x
            c = ax + inward * T_EXT / 2
            e0, e1 = sorted((centre(i - 1), centre(i + 1)))
            w = Wall(c, e0, c, e1, T_EXT, z0, z1, kind="ext", out=-inward,
                     skin=skin, skin_z=skin_z, level=level)
        WALLS.append(w)
        made.append(w)
    return made


def wall(level, x0, y0, x1, y1, t=T_INT, kind="int", z=None, core="block"):
    z0, z1 = z or storey_z(level)
    w = Wall(x0, y0, x1, y1, t, z0, z1, kind=kind, level=level, core=core)
    WALLS.append(w)
    return w


def find_wall(level, horiz, c, a, kinds=None, tol=0.2):
    best = None
    for w in WALLS:
        if w.level != level or w.horiz != horiz:
            continue
        if kinds and w.kind not in kinds:
            continue
        if abs(w.c - c) <= max(tol, w.t / 2 + 0.01) and w.a0 - 0.01 <= a <= w.a1 + 0.01:
            d = abs(w.c - c)
            if best is None or d < best[0]:
                best = (d, w)
    if not best:
        raise ValueError(f"no wall at {level} {'H' if horiz else 'V'} c={c} a={a}")
    return best[1]


def op(level, horiz, c, a0, a1, sill, head, kind, tag="", **kw):
    w = find_wall(level, horiz, c, (a0 + a1) / 2)
    o = Opening(a0, a1, sill, head, kind, tag, **kw)
    w.openings.append(o)
    return o


def room(name, level, rects, **kw):
    r = Room(name, level, rects, **kw)
    ROOMS.append(r)
    return r


def furn(kind, level, x, y, w, d, rot=0, h=0.0, label=""):
    FURN.append(Furn(kind, level, x, y, w, d, rot, h, label))


# =========================================================================== #
#  BUILDING
# =========================================================================== #
# Key coordinates
X_W, X_M, X_C, X_E = 6.0, 13.0, 19.0, 25.0      # west face, west-bar east face, kitchen line, east face
Y_S_G, Y_N = 21.0, 32.0                           # GF south face, north face
Y_S_U = 16.0                                      # UF cantilever end
Y_NB = 25.0                                       # UF north-bar south face
LOGGIA = 17.6                                     # master bedroom glazing line

# Stair core (stacked U-stair) & lift
ST = dict(x0=13.10, x1=15.60, ys=27.70, yl=30.50, yn=31.70, w=1.20, gap=0.10)
LIFT = dict(x0=15.70, x1=17.50, y0=29.70, y1=31.70)

# ------------------------------------------------------------------ BASEMENT
zB = storey_z("B")
bw = ext_outline("B", [(X_W, Y_S_G), (X_E, Y_S_G), (X_E, Y_N), (X_W, Y_N)], skin="rc_fair",
                 skin_z=(slab_top("B") - RAFT, slab_bot("G")))
for w in bw:
    w.kind = "retain"
    w.core = "rc"

# interior walls – basement
wall("B", 12.85, 21.30, 12.85, 31.70, t=0.30, kind="rc", core="rc")   # cinema/gym | lounge (under GF RC wall)
wall("B", 6.30, 25.15, 12.70, 25.15, t=0.30, kind="rc", core="rc")    # cinema | gym (grid 3)
wall("B", 19.06, 21.30, 19.06, 31.70)                     # lounge | guest/spa
wall("B", 19.12, 25.06, 24.70, 25.06)                     # guest bedroom | bath/spa
wall("B", 21.56, 25.06, 21.56, 31.70)                     # spa | guest bath / storage | tech
wall("B", 19.12, 27.66, 24.70, 27.66)                     # spa/bath | storage/tech
wall("B", 17.56, 29.70, 17.56, 31.70)                     # wine
wall("B", 17.56, 29.64, 19.06, 29.64)
wall("B", 15.6, 27.64, 15.6, 29.70, t=0.10)               # lift lobby screen (short)

# ------------------------------------------------------------------ GROUND
ext_outline("G", [(X_W, Y_S_G), (X_E, Y_S_G), (X_E, Y_N), (X_W, Y_N)], skin="stone",
            skin_z=(GARDEN - 0.05, slab_top("U") + 0.05))
wall("G", 12.85, 25.15, 12.85, 31.70, t=0.30, kind="rc", core="rc")   # living | core – RC shear wall (fireplace back)
wall("G", 19.06, 25.15, 19.06, 27.76)                     # hall | WC
wall("G", 19.06, 25.15, 24.70, 25.15, t=0.20)             # kitchen | pantry & WC (on grid 3, carries UF wall)
wall("G", 20.96, 25.25, 20.96, 27.76)                     # WC | pantry
wall("G", 19.12, 27.76, 24.70, 27.76, t=0.12)             # WC/pantry | foyer
wall("G", 17.56, 29.70, 17.56, 31.70)                     # coats
# ------------------------------------------------------------------ UPPER
UF_OUT = [(X_W, Y_S_U), (X_M, Y_S_U), (X_M, Y_NB), (X_E, Y_NB), (X_E, Y_N), (X_W, Y_N)]
uf = ext_outline("U", UF_OUT, skin="plaster", skin_z=(slab_top("U") - SLAB - 0.05, LV["R"] + 0.50))


def split_wall(w, at, rc_side):
    """split wall w at axis coordinate `at` (a wall-junction centre line); rc_side 'lo'|'hi' gets an RC core."""
    import copy
    a = copy.deepcopy(w)
    b = copy.deepcopy(w)
    if w.horiz:
        a.x0, a.x1 = w.a0, at - T_EXT / 2
        b.x0, b.x1 = at + T_EXT / 2, w.a1
    else:
        a.y0, a.y1 = w.a0, at - T_EXT / 2
        b.y0, b.y1 = at + T_EXT / 2, w.a1
    (a if rc_side == "lo" else b).core = "rc"
    (a if rc_side == "lo" else b).kind = "ext"
    i = WALLS.index(w)
    WALLS[i:i + 1] = [a, b]
    return a, b


_west = next(w for w in uf if not w.horiz and w.out == -1)
split_wall(_west, 26.96, "hi")           # mamad west wall RC (y 26.96 → 32.0)
_north = next(w for w in WALLS if w.level == "U" and w.kind == "ext" and w.horiz and w.out == 1)
split_wall(_north, 11.20, "lo")          # mamad north wall RC (x 6.0 → 11.20)
# The loggia: south edge (6,16)-(13,16) becomes an open frame (opening added below).
# master suite
wall("U", 6.30, LOGGIA, 12.70, LOGGIA, t=0.20, kind="glass")      # bedroom glazing line
wall("U", 6.30, 21.66, 12.70, 21.66)                               # bedroom | bath & dressing
wall("U", 9.56, 21.72, 9.56, 25.24)                                # bath | dressing
wall("U", 6.30, 25.30, 12.70, 25.30)                               # suite | corridor
# north strip
wall("U", 11.20, 26.96, 13.12, 26.96)                              # corridor | bath3
wall("U", 11.05, 26.96, 11.05, 31.70, t=0.30, kind="mamad", core="rc")        # mamad east wall
wall("U", 6.30, 27.11, 10.90, 27.11, t=0.30, kind="mamad", core="rc")         # mamad south wall
wall("U", 6.35, 27.26, 6.35, 31.60, t=0.10, kind="mamad", core="rc")          # RC liner → W wall 30 RC
wall("U", 6.30, 31.65, 10.90, 31.65, t=0.10, kind="mamad", core="rc")         # RC liner → N wall 30 RC
wall("U", 13.04, 26.96, 13.04, 31.70)                              # bath3 | stair
wall("U", 17.56, 29.70, 17.56, 31.70)                              # laundry | lift
wall("U", 19.66, 25.30, 19.66, 31.70)                              # lounge | bedroom 2
wall("U", 17.56, 29.64, 19.66, 29.64)                              # laundry south
wall("U", 19.72, 29.46, 24.70, 29.46)                              # bedroom2 | bath2

# ------------------------------------------------------------------ ROOF EXIT
RX_OUT = [(12.90, 26.45), (17.80, 26.45), (17.80, Y_N), (12.90, Y_N)]
rxz = (slab_top("R"), LV["RX"] - 0.30)
ext_outline("R", RX_OUT, skin="plaster", skin_z=(slab_top("R"), LV["RX"] + 0.20), core_z=rxz)

# lift shaft walls (all storeys) – RC
for lvl in ("B", "G", "U"):
    z = storey_z(lvl)
    wall(lvl, LIFT["x0"] + 0.10, LIFT["y0"], LIFT["x0"] + 0.10, 31.70, t=0.20, kind="shaft", core="rc")
    wall(lvl, LIFT["x1"] - 0.10, LIFT["y0"], LIFT["x1"] - 0.10, 31.70, t=0.20, kind="shaft", core="rc")
    wall(lvl, LIFT["x0"], LIFT["y0"] + 0.10, 16.15, LIFT["y0"] + 0.10, t=0.20, kind="shaft", core="rc")
    wall(lvl, 17.05, LIFT["y0"] + 0.10, LIFT["x1"], LIFT["y0"] + 0.10, t=0.20, kind="shaft", core="rc")
wall("R", LIFT["x0"] + 0.10, LIFT["y0"], LIFT["x0"] + 0.10, 31.70, t=0.20, kind="shaft", core="rc", z=rxz)
wall("R", LIFT["x1"] - 0.10, LIFT["y0"], LIFT["x1"] - 0.10, 31.70, t=0.20, kind="shaft", core="rc", z=rxz)
wall("R", LIFT["x0"], LIFT["y0"] + 0.10, 16.15, LIFT["y0"] + 0.10, t=0.20, kind="shaft", core="rc", z=rxz)
wall("R", 17.05, LIFT["y0"] + 0.10, LIFT["x1"], LIFT["y0"] + 0.10, t=0.20, kind="shaft", core="rc", z=rxz)

COURT_N = (6.60, 32.00, 12.40, 33.40)        # English court (חצר אנגלית) for the basement gym
for (x0, y0, x1, y1) in [(COURT_N[0] - 0.15, Y_N - 0.1, COURT_N[0] - 0.15, COURT_N[3] + 0.30),
                         (COURT_N[2] + 0.15, Y_N - 0.1, COURT_N[2] + 0.15, COURT_N[3] + 0.30),
                         (COURT_N[0] - 0.30, COURT_N[3] + 0.15, COURT_N[2] + 0.30, COURT_N[3] + 0.15)]:
    WALLS.append(Wall(x0, y0, x1, y1, 0.30, LV["B"] - 0.40, GARDEN + 0.10, kind="retain", level="B", core="rc"))

# --------------------------------------------------------------------------- #
#  OPENINGS  (sill/head relative to storey floor level)
# --------------------------------------------------------------------------- #
H = True
V = False
# ---- Basement
op("B", H, 21.15, 13.40, 18.80, 0.0, 2.90, "slide", "AL-B1")               # lounge -> patio
op("B", H, 21.15, 19.40, 21.40, 0.0, 2.90, "slide", "AL-B2")               # guest -> patio
op("B", H, 31.85, 7.10, 11.90, 0.0, 2.70, "slide", "AL-B3")                # gym -> English court
op("B", V, 12.85, 23.60, 24.50, 0, 2.20, "door", "D-B1", hinge="b", swing=-1)       # cinema (acoustic)
op("B", V, 12.85, 26.40, 27.30, 0, 2.20, "door", "D-B2", hinge="a", swing=-1)       # gym
op("B", V, 19.06, 21.40, 22.30, 0, 2.20, "door", "D-B3", hinge="a", swing=1)        # guest
op("B", H, 25.06, 22.20, 23.00, 0, 2.20, "door", "D-B4", hinge="a", swing=1)        # guest bath
op("B", V, 19.06, 26.65, 27.45, 0, 2.20, "door", "D-B5", hinge="b", swing=1)        # spa
op("B", V, 19.06, 28.40, 29.30, 0, 2.20, "door", "D-B6", hinge="b", swing=1)        # storage
op("B", V, 21.56, 28.40, 29.30, 0, 2.20, "door", "D-B7", hinge="a", swing=1)        # tech (from storage)
op("B", H, 29.64, 17.90, 18.80, 0, 2.20, "door", "D-B8", hinge="a", swing=-1)       # wine (glass)
# ---- Ground floor
op("G", H, 21.15, 6.45, 12.55, 0, 3.00, "slide", "AL-01")                  # living south
op("G", H, 21.15, 13.30, 18.80, 0, 3.00, "slide", "AL-02")                 # dining south
op("G", H, 21.15, 19.40, 21.80, 0, 3.00, "slide", "AL-03")                 # kitchen -> BBQ terrace
op("G", H, 21.15, 22.30, 24.40, 1.05, 2.40, "window", "AL-04")             # kitchen window
op("G", V, 6.15, 21.45, 25.60, 0, 3.00, "slide", "AL-05")                  # living west
op("G", V, 6.15, 26.40, 29.60, 0.45, 3.00, "fixed", "AL-06")               # picture window
op("G", H, 31.85, 7.20, 7.80, 0.30, 3.00, "fixed", "AL-07")                # slots by fireplace
op("G", H, 31.85, 11.50, 12.10, 0.30, 3.00, "fixed", "AL-07")
op("G", H, 31.85, 13.40, 15.30, 0.00, 3.20, "fixed", "AL-08")              # stair glazing (continuous)
op("G", H, 31.85, 19.60, 24.40, 2.10, 3.00, "window", "AL-09")             # foyer clerestory
op("G", V, 24.85, 22.00, 25.00, 1.05, 2.40, "window", "AL-10")             # kitchen east
op("G", V, 24.85, 25.50, 26.40, 0, 2.30, "door", "D-02", hinge="a", swing=1)   # pantry service door
op("G", V, 24.85, 29.10, 30.50, 0, 2.90, "pivot", "D-01")                 # entrance pivot door
op("G", V, 24.85, 30.60, 31.50, 0, 2.90, "fixed", "AL-11")                 # side light
op("G", V, 19.06, 25.40, 26.20, 0, 2.20, "door", "D-03", hinge="a", swing=1)   # guest WC
op("G", H, 25.15, 21.20, 22.00, 0, 2.20, "door", "D-04", hinge="a", swing=1)   # pantry from kitchen
# ---- Upper floor
op("U", H, 16.15, 6.30, 12.70, 0, 2.80, "open", "")                        # loggia frame
op("U", H, LOGGIA, 6.40, 12.60, 0, 2.80, "slide", "AL-21")                 # master bedroom glazing
op("U", V, 6.15, 17.90, 21.40, 0, 2.80, "slide", "AL-22")                  # master west (behind fins)
op("U", V, 6.15, 22.20, 24.60, 1.00, 2.70, "window", "AL-23", frosted=True)  # master bath
op("U", V, 6.15, 25.50, 26.75, 0, 2.70, "fixed", "AL-24")                  # corridor end
op("U", V, 6.15, 28.60, 29.60, 1.00, 2.00, "mamad_win", "M-1")             # mamad
op("U", V, 12.85, 18.00, 21.30, 0.50, 2.80, "window", "AL-25")             # master east
op("U", V, 12.85, 22.10, 24.80, 1.70, 2.70, "window", "AL-26")             # dressing high window
op("U", H, 31.85, 11.70, 12.70, 1.50, 2.40, "window", "AL-27", frosted=True)   # bath 3
op("U", H, 31.85, 13.40, 15.30, -0.40, 3.20, "fixed", "AL-34")             # stair glazing (continuous with AL-08)
op("U", H, 31.85, 17.90, 19.20, 1.40, 2.40, "window", "AL-28")             # laundry
op("U", H, 31.85, 22.30, 24.20, 1.50, 2.40, "window", "AL-29", frosted=True)   # bath 2
op("U", V, 24.85, 25.70, 28.70, 0.50, 2.80, "window", "AL-30")             # bedroom 2 east (fins)
op("U", H, 25.15, 13.40, 15.50, 0.00, 2.80, "fixed", "AL-31")              # stair/gallery south
op("U", H, 25.15, 15.80, 19.40, 0.00, 2.80, "slide", "AL-32")              # lounge -> terrace
op("U", H, 25.15, 20.00, 24.40, 0.00, 2.80, "slide", "AL-33")              # bedroom 2 -> terrace
op("U", H, 25.30, 11.50, 12.40, 0, 2.20, "door", "D-21", hinge="a", swing=-1)    # master suite entry
op("U", V, 9.56, 24.20, 25.00, 0, 2.20, "door", "D-22", hinge="b", swing=-1)     # master bath
op("U", H, 21.66, 10.60, 12.40, 0, 2.40, "passage")                              # dressing -> bedroom
op("U", H, 27.11, 9.00, 9.80, 0, 2.00, "mamad_door", "M-D", hinge="b", swing=-1) # mamad blast door
op("U", H, 26.96, 11.40, 12.20, 0, 2.20, "door", "D-23", hinge="a", swing=1)     # bath 3
op("U", V, 19.66, 26.00, 26.90, 0, 2.20, "door", "D-24", hinge="a", swing=1)     # bedroom 2
op("U", H, 29.46, 20.50, 21.30, 0, 2.20, "door", "D-25", hinge="a", swing=1)     # bath 2
op("U", H, 29.64, 18.30, 19.10, 0, 2.20, "door", "D-26", hinge="a", swing=1)     # laundry
# ---- Roof exit
op("R", H, 26.60, 14.35, 15.35, 0, 2.20, "door", "D-31", hinge="a", swing=-1)    # roof door
op("R", H, 31.85, 13.40, 15.30, -0.20, 2.20, "fixed", "AL-35")                   # stair glazing top

# --------------------------------------------------------------------------- #
#  SLABS
# --------------------------------------------------------------------------- #
stair_hole = (ST["x0"], 27.98, 15.70, ST["yn"])
stair_hole_g = (13.00, 27.98, 15.70, ST["yn"])
lift_hole = (LIFT["x0"] + 0.2, LIFT["y0"] + 0.2, LIFT["x1"] - 0.2, 31.70)
SLABS += [
    Slab([(X_W - 0.35, Y_S_G - 0.35, X_E + 0.35, Y_N + 0.35)], slab_top("B"), RAFT, "raft", holes=[]),
    Slab([(X_W + 0.10, Y_S_G + 0.10, X_E - 0.10, Y_N - 0.10)], slab_top("G"), SLAB, "slab",
         holes=[stair_hole_g, lift_hole], finish="פורצלן 120/120 + מילוי"),
    # UF slab: building + cantilever + GF-roof terrace
    Slab([(X_W + 0.10, Y_S_U + 0.10, X_M - 0.10, Y_S_G + 0.10),
          (X_W + 0.10, Y_S_G + 0.10, X_E - 0.10, Y_N - 0.10)], slab_top("U"), SLAB, "slab",
         holes=[stair_hole, lift_hole], finish="פרקט עץ אלון / פורצלן"),
    Slab([(X_W + 0.10, Y_S_U + 0.10, X_M - 0.10, Y_NB + 0.10),
          (X_W + 0.10, Y_NB + 0.10, X_E - 0.10, Y_N - 0.10)], slab_top("R"), SLAB, "roof",
         holes=[stair_hole, lift_hole]),
    Slab([(12.90 + 0.10, 26.55, 17.80 - 0.10, Y_N - 0.10)], LV["RX"] - 0.10 + 0.0, 0.25, "roof"),
    # entrance canopy (concrete plate)
    Slab([(X_E - 0.1, 28.40, X_E + 2.00, 31.80)], 3.05, 0.20, "canopy"),
]
# Sunken patio floor
PATIO = (14.00, 17.00, 21.50, 21.00)
SLABS.append(Slab([(PATIO[0] - 0.30, PATIO[1] - 0.30, PATIO[2] + 0.30, Y_S_G)], LV["B"] - 0.02, 0.35, "deck"))
# deck bridge over patio edge (GF level)
SLABS.append(Slab([(13.00, 19.60, PATIO[2] + 0.30, Y_S_G)], -0.02, 0.25, "deck"))

# patio retaining walls (from basement raft up to garden + 0.10 coping)
for (x0, y0, x1, y1) in [(PATIO[0] - 0.15, PATIO[1] - 0.30, PATIO[0] - 0.15, Y_S_G),
                         (PATIO[2] + 0.15, PATIO[1] - 0.30, PATIO[2] + 0.15, Y_S_G),
                         (PATIO[0] - 0.30, PATIO[1] - 0.15, PATIO[2] + 0.30, PATIO[1] - 0.15)]:
    WALLS.append(Wall(x0, y0, x1, y1, 0.30, LV["B"] - 0.40, GARDEN + 0.10, kind="retain", level="B", core="rc"))

# --------------------------------------------------------------------------- #
#  COLUMNS (RC 30/30 unless noted) – GF supports for the UF wall-beams
# --------------------------------------------------------------------------- #
for x, y in [(6.15, 21.15), (12.85, 21.15), (19.06, 21.15), (24.85, 21.15), (12.85, 25.15), (19.06, 25.15)]:
    COLS.append(Column(x, y, 0.30, 0.30, slab_top("G"), slab_bot("U")))
    COLS.append(Column(x, y, 0.30, 0.30, slab_top("B"), slab_bot("G")))

# --------------------------------------------------------------------------- #
#  PARAPETS & RAILINGS
# --------------------------------------------------------------------------- #
# UF roof parapet (on the outline), roof exit parapet
for i in range(len(UF_OUT)):
    (ax, ay), (bx, by) = UF_OUT[i], UF_OUT[(i + 1) % len(UF_OUT)]
    if abs(ay - by) < 1e-9:
        inward = 1 if bx > ax else -1
        c = ay + inward * 0.10
        segs = [(min(ax, bx), max(ax, bx))]
        if abs(ay - Y_N) < 1e-6:   # north edge: interrupted by the roof-exit wall
            segs = [(min(ax, bx), RX_OUT[0][0]), (RX_OUT[1][0], max(ax, bx))]
        for (s0, s1) in segs:
            WALLS.append(Wall(s0, c, s1, c, 0.20, slab_top("R"), LV["R"] + 0.50,
                              kind="parapet", level="R", out=-inward, skin="plaster"))
    else:
        inward = -1 if by > ay else 1
        c = ax + inward * 0.10
        WALLS.append(Wall(c, min(ay, by), c, max(ay, by), 0.20, slab_top("R"), LV["R"] + 0.50,
                          kind="parapet", level="R", out=-inward, skin="plaster"))
# GF-roof terrace parapet (x 13→25, y 21) and east edge (x 25, y 21→25)
WALLS.append(Wall(X_M, Y_S_G + 0.10, X_E, Y_S_G + 0.10, 0.20, slab_top("U"), LV["U"] + 0.15, kind="parapet",
                  level="U", out=-1, skin="stone"))
WALLS.append(Wall(X_E - 0.10, Y_S_G, X_E - 0.10, Y_NB, 0.20, slab_top("U"), LV["U"] + 0.15, kind="parapet",
                  level="U", out=1, skin="stone"))
RAILS += [
    dict(x0=X_M + 0.1, y0=Y_S_G + 0.15, x1=X_E - 0.1, y1=Y_S_G + 0.15, z0=LV["U"] + 0.15, h=0.95, kind="glass"),
    dict(x0=X_E - 0.15, y0=Y_S_G + 0.1, x1=X_E - 0.15, y1=Y_NB, z0=LV["U"] + 0.15, h=0.95, kind="glass"),
    # loggia
    dict(x0=X_W + 0.3, y0=Y_S_U + 0.15, x1=X_M - 0.3, y1=Y_S_U + 0.15, z0=LV["U"], h=1.05, kind="glass"),
    # roof terrace (north-bar roof, east part)
    dict(x0=17.9, y0=Y_NB + 0.20, x1=X_E - 0.2, y1=Y_NB + 0.20, z0=LV["R"] + 0.50, h=0.60, kind="glass"),
    dict(x0=X_E - 0.20, y0=Y_NB + 0.2, x1=X_E - 0.20, y1=Y_N - 0.2, z0=LV["R"] + 0.50, h=0.60, kind="glass"),
    dict(x0=17.9, y0=Y_N - 0.20, x1=X_E - 0.2, y1=Y_N - 0.20, z0=LV["R"] + 0.50, h=0.60, kind="glass"),
    # patio edge (GF level, around the void)
    dict(x0=PATIO[0], y0=PATIO[1], x1=PATIO[0], y1=19.6, z0=GARDEN + 0.10, h=0.95, kind="glass"),
    dict(x0=PATIO[2], y0=PATIO[1], x1=PATIO[2], y1=19.6, z0=GARDEN + 0.10, h=0.95, kind="glass"),
    dict(x0=PATIO[0], y0=PATIO[1], x1=19.42, y1=PATIO[1], z0=GARDEN + 0.10, h=0.95, kind="glass"),
    dict(x0=20.42, y0=PATIO[1], x1=PATIO[2], y1=PATIO[1], z0=GARDEN + 0.10, h=0.95, kind="glass"),
    dict(x0=PATIO[0], y0=19.6, x1=PATIO[2], y1=19.6, z0=-0.02, h=1.05, kind="glass"),
    # stair-void guards (over flight A of the run below)
    dict(x0=13.20, y0=27.98, x1=14.35, y1=27.98, z0=LV["R"], h=1.05, kind="glass"),
    # stair-void side guards next to the lift lobby
    dict(x0=15.70, y0=27.98, x1=15.70, y1=29.70, z0=LV["G"], h=1.05, kind="glass"),
    dict(x0=15.70, y0=27.98, x1=15.70, y1=29.70, z0=LV["U"], h=1.05, kind="glass"),
    dict(x0=15.70, y0=27.98, x1=15.70, y1=29.70, z0=LV["R"], h=1.05, kind="glass"),
    dict(x0=15.60, y0=27.98, x1=15.70, y1=27.98, z0=LV["U"], h=1.05, kind="glass"),
    dict(x0=15.60, y0=27.98, x1=15.70, y1=27.98, z0=LV["R"], h=1.05, kind="glass"),
    # roof path from the roof door to the roof terrace
    dict(x0=12.95, y0=Y_NB + 0.20, x1=17.90, y1=Y_NB + 0.20, z0=LV["R"] + 0.50, h=0.60, kind="glass"),
    dict(x0=12.95, y0=Y_NB + 0.20, x1=12.95, y1=26.45, z0=LV["R"], h=1.10, kind="glass"),
    # French-balcony guards in front of low-sill UF glazing
    dict(x0=X_W - 0.04, y0=17.90, x1=X_W - 0.04, y1=21.40, z0=LV["U"], h=1.05, kind="glass"),
    dict(x0=X_M + 0.04, y0=18.00, x1=X_M + 0.04, y1=21.30, z0=LV["U"], h=1.05, kind="glass"),
    dict(x0=X_E + 0.04, y0=25.70, x1=X_E + 0.04, y1=28.70, z0=LV["U"], h=1.05, kind="glass"),
    # English court guard
    dict(x0=COURT_N[0], y0=COURT_N[3], x1=COURT_N[2], y1=COURT_N[3], z0=GARDEN + 0.10, h=0.95, kind="glass"),
    dict(x0=COURT_N[0], y0=Y_N, x1=COURT_N[0], y1=COURT_N[3], z0=GARDEN + 0.10, h=0.95, kind="glass"),
    dict(x0=COURT_N[2], y0=Y_N, x1=COURT_N[2], y1=COURT_N[3], z0=GARDEN + 0.10, h=0.95, kind="glass"),
]

# --------------------------------------------------------------------------- #
#  VERTICAL LOUVRES (aluminium, wood-look finish 50x200 @ 180)
# --------------------------------------------------------------------------- #
FINS += [
    # UF west face over master suite
    dict(axis="y", c=X_W - 0.32, a0=16.0, a1=25.2, z0=slab_bot("U"), z1=LV["R"] + 0.50, depth=0.20, w=0.05, step=0.18),
    # loggia south frame (fixed, on the sides only)
    # UF east face (street) bedroom 2
    dict(axis="y", c=X_E + 0.32, a0=25.0, a1=29.4, z0=slab_bot("U"), z1=LV["R"] + 0.50, depth=0.20, w=0.05, step=0.18),
    # carport screen is part of site
]

# --------------------------------------------------------------------------- #
#  PERGOLAS
# --------------------------------------------------------------------------- #
PERGOLAS += [
    # carport pergola (front setback) – aluminium louvres on steel frame
    dict(x0=24.60, y0=15.70, x1=30.0 - 0.20, y1=21.70, z=2.60 + STREET, beam="y", step=0.25, posts=[(24.75, 15.85), (24.75, 21.55), (29.65, 15.85), (29.65, 21.55)]),
    # BBQ terrace pergola
    dict(x0=21.80, y0=16.80, x1=24.45, y1=Y_S_G, z=2.90, beam="x", step=0.30, posts=[(21.95, 16.95), (24.30, 16.95)]),
    # roof terrace pergola
    dict(x0=18.20, y0=27.40, x1=X_E - 0.3, y1=Y_N - 0.3, z=LV["R"] + 2.70, beam="x", step=0.30,
         posts=[(18.35, 27.55), (24.55, 27.55), (18.35, 31.55), (24.55, 31.55)], base=LV["R"]),
]

# --------------------------------------------------------------------------- #
#  STAIRS
# --------------------------------------------------------------------------- #
def u_stair(z_from, z_to, risers, first_flight_risers, level):
    """Stacked U stair: flight A (west, going north) → landing → flight B (east, going south)."""
    r = (z_to - z_from) / risers
    t = 0.28
    nA = first_flight_risers                # risers in flight A (last riser lands on landing)
    nB = risers - nA
    zl = z_from + nA * r
    yA0 = ST["yl"] - (nA - 1) * t
    flights = []
    treadsA = [(ST["x0"], yA0 + i * t, ST["x0"] + ST["w"], yA0 + (i + 1) * t, z_from + (i + 1) * r) for i in range(nA - 1)]
    xb0 = ST["x0"] + ST["w"] + ST["gap"]
    treadsB = [(xb0, ST["yl"] - (i + 1) * t, xb0 + ST["w"], ST["yl"] - i * t, zl + (i + 1) * r) for i in range(nB - 1)]
    STAIRS.append(dict(level=level, z0=z_from, z1=z_to, r=r, t=t, nA=nA, nB=nB, zl=zl,
                       treadsA=treadsA, treadsB=treadsB, landing=(ST["x0"], ST["yl"], xb0 + ST["w"], ST["yn"], zl),
                       yA0=yA0, yB_end=ST["yl"] - (nB - 1) * t, flightA=(ST["x0"], yA0, ST["x0"] + ST["w"], ST["yl"]),
                       flightB=(xb0, ST["yl"] - (nB - 1) * t, xb0 + ST["w"], ST["yl"])))


u_stair(LV["B"], LV["G"], 20, 10, "B")
u_stair(LV["G"], LV["U"], 21, 11, "G")
u_stair(LV["U"], LV["R"], 20, 10, "U")

# --------------------------------------------------------------------------- #
#  ROOMS
# --------------------------------------------------------------------------- #
# Basement
room("קולנוע ביתי", "B", [(6.30, 21.30, 12.70, 25.00)], floor="שטיח אקוסטי", ceil=2.90, no="B1")
room("חדר כושר / יוגה", "B", [(6.30, 25.30, 12.70, 31.70)], floor="פרקט ספורט", ceil=2.90, no="B2")
room("טרקלין ובר", "B", [(13.00, 21.30, 19.00, 27.60)], floor="פורצלן 120/120", ceil=2.90, no="B3")
room("חדר אורחים", "B", [(19.12, 21.30, 24.70, 25.00)], floor="פרקט עץ", ceil=2.90, no="B4")
room("רחצה אורחים", "B", [(21.62, 25.12, 24.70, 27.60)], floor="פורצלן 60/120", ceil=2.60, no="B5")
room("ספא – סאונה ומקלחת", "B", [(19.12, 25.12, 21.50, 27.60)], floor="אבן טבעית", ceil=2.60, no="B6")
room("מחסן", "B", [(19.12, 27.72, 21.50, 31.70)], floor="פורצלן 60/60", ceil=2.60, no="B7", service=True)
room("חדר טכני", "B", [(21.62, 27.72, 24.70, 31.70)], floor="בטון מוחלק", ceil=2.90, no="B8", service=True)
room("מרתף יין", "B", [(17.62, 29.70, 19.00, 31.70)], floor="אבן טבעית", ceil=2.60, no="B9", service=True)
room("מבואה ומדרגות", "B", [(13.00, 27.60, 15.55, 31.70), (15.65, 27.60, 19.00, 29.58), (15.55, 29.70, 15.70, 31.70)], floor="פורצלן 120/120", ceil=2.90, no="B10")
room("פטיו שקוע", "B", [(PATIO[0], PATIO[1], PATIO[2], Y_S_G)], floor="אבן כורכר", no="B11", outdoor=True)
# Ground
room("סלון", "G", [(6.30, 21.30, 12.70, 31.70), (12.70, 21.30, 13.00, 25.00)], floor="פורצלן 120/120", ceil=3.10, no="G1", tag_at=(9.6, 25.3))
room("פינת אוכל", "G", [(13.00, 21.30, 19.00, 25.15)], floor="פורצלן 120/120", ceil=3.10, no="G2", tag_at=(16.1, 24.75))
room("מטבח", "G", [(19.12, 21.30, 24.70, 25.05)], floor="פורצלן 120/120", ceil=3.00, no="G3", tag_at=(21.3, 24.25))
room("מבואה ומדרגות", "G", [(13.00, 25.15, 19.00, 29.70), (13.00, 29.70, 15.70, 31.70), (17.62, 29.76, 19.00, 31.70)], floor="פורצלן 120/120", ceil=3.10, no="G4", tag_at=(17.0, 26.6))
room("שירותי אורחים", "G", [(19.12, 25.25, 20.90, 27.70)], floor="פורצלן 60/120", ceil=2.60, no="G5")
room("מזווה / מטבח אחורי", "G", [(21.02, 25.25, 24.70, 27.70)], floor="פורצלן 60/60", ceil=2.60, no="G6")
room("לובי כניסה", "G", [(19.12, 27.82, 24.70, 31.70)], floor="אבן טבעית", ceil=3.10, no="G7")
room("מרפסת מקורה", "G", [(X_W, Y_S_U, X_M, Y_S_G)], floor="דק עץ טיק", no="G8", outdoor=True)
# Upper
room("חדר שינה הורים", "U", [(6.30, LOGGIA + 0.10, 12.70, 21.60)], floor="פרקט אלון", ceil=2.80, no="U1")
room("לוג'יה", "U", [(6.30, 16.30, 12.70, LOGGIA - 0.10)], floor="דק עץ", no="U2", outdoor=True)
room("רחצת הורים", "U", [(6.30, 21.72, 9.50, 25.24)], floor="אבן טבעית 60/120", ceil=2.70, no="U3")
room("חדר הלבשה", "U", [(9.62, 21.72, 12.70, 25.24)], floor="פרקט אלון", ceil=2.70, no="U4")
room("פרוזדור", "U", [(6.30, 25.36, 13.00, 26.90)], floor="פרקט אלון", ceil=2.70, no="U5")
room('ממ"ד / חדר ילד', "U", [(6.40, 27.26, 10.90, 31.60)], floor="פרקט אלון", ceil=2.60, no="U6", service=True)
room("רחצה 3", "U", [(11.20, 27.02, 13.00, 31.70)], floor="פורצלן 60/120", ceil=2.60, no="U7")
room("גלריה משפחתית", "U", [(13.12, 25.30, 19.60, 29.58), (13.10, 29.58, 15.70, 31.70)], floor="פרקט אלון", ceil=2.80, no="U8", tag_at=(17.6, 27.4))
room("כביסה", "U", [(17.62, 29.70, 19.60, 31.70)], floor="פורצלן 60/60", ceil=2.60, no="U9", service=True)
room("חדר שינה 2", "U", [(19.72, 25.30, 24.70, 29.40)], floor="פרקט אלון", ceil=2.80, no="U10")
room("רחצה 2", "U", [(19.72, 29.52, 24.70, 31.70)], floor="פורצלן 60/120", ceil=2.60, no="U11")
room("מרפסת גג משפחתית", "U", [(X_M, Y_S_G, X_E, Y_NB)], floor="דק עץ / אבן", no="U12", outdoor=True)
# Roof
room("יציאה לגג", "R", [(13.20, 26.75, 15.70, 31.70), (15.70, 26.75, 17.50, 29.70)], floor="פורצלן", no="R1", service=True)
room("מרפסת גג", "R", [(17.80, Y_NB, X_E, Y_N)], floor="דק עץ", no="R2", outdoor=True)
room("שביל גג", "R", [(12.90, Y_NB + 0.20, 17.80, 26.45)], floor="אריחי דק", no="R3", outdoor=True)

# --------------------------------------------------------------------------- #
#  FURNITURE (plan symbols; simple ones also become 3-D blocks)
# --------------------------------------------------------------------------- #
# Ground – living (front direction: 0=E 90=N 180=W 270=S)
furn("rug", "G", 7.0, 26.7, 5.0, 3.9)
furn("sofa_l", "G", 7.2, 26.0, 4.2, 2.6, rot=90, h=0.42)
furn("coffee", "G", 8.7, 28.9, 1.6, 0.9, h=0.35)
furn("armchair", "G", 11.4, 28.6, 0.9, 0.9, rot=180)
furn("fireplace", "G", 8.45, 31.15, 2.40, 0.55, rot=270)
furn("armchair", "G", 7.2, 22.4, 0.9, 0.9, rot=270)
furn("armchair", "G", 8.5, 22.4, 0.9, 0.9, rot=270)
furn("coffee", "G", 7.75, 23.55, 0.8, 0.6, h=0.45)
furn("piano", "G", 10.6, 22.0, 1.5, 1.9, rot=270)
# dining
furn("table_rect", "G", 14.4, 22.65, 3.4, 1.2, rot=270, h=0.75, label="10")
# kitchen
furn("counter", "G", 24.08, 21.45, 0.62, 3.6, rot=180)
furn("fridge", "G", 22.1, 24.43, 0.9, 0.62, rot=270)
furn("closet", "G", 23.0, 24.43, 1.08, 0.62, rot=270, label="תנורים")
furn("counter", "G", 19.2, 24.43, 1.8, 0.62, rot=270)
furn("island", "G", 20.4, 22.3, 2.6, 1.1, rot=270, h=0.92)
# pantry
furn("counter", "G", 21.1, 27.05, 3.5, 0.6)
# WC
furn("wc", "G", 19.8, 27.10, 0.4, 0.6, rot=270)
furn("basin", "G", 20.45, 25.60, 0.45, 0.6, rot=180)
# foyer
furn("closet", "G", 19.3, 31.05, 3.6, 0.6, rot=180)
furn("bench", "G", 23.0, 31.15, 1.5, 0.45, rot=180)
furn("closet", "G", 17.62, 31.10, 1.38, 0.55, rot=270)
# covered terrace
furn("table_rect", "G", 8.0, 18.4, 3.0, 1.1, rot=270, h=0.75, label="8")
# Upper – master
furn("bed_k", "U", 8.50, 19.40, 2.0, 2.2, rot=270)
furn("nightstand", "U", 7.90, 21.05, 0.5, 0.5)
furn("nightstand", "U", 10.60, 21.05, 0.5, 0.5)
furn("armchair", "U", 11.40, 18.00, 0.9, 0.9, rot=180)
furn("tub", "U", 6.45, 22.00, 0.8, 1.8, rot=0)
furn("vanity2", "U", 8.95, 21.85, 0.55, 2.2, rot=180)
furn("shower", "U", 6.35, 24.05, 1.5, 1.15)
furn("wc", "U", 7.95, 24.64, 0.4, 0.6, rot=270)
furn("closet", "U", 9.65, 21.80, 0.6, 2.20, rot=0)
furn("closet", "U", 12.05, 21.80, 0.6, 2.45, rot=180)
# corridor / mamad
furn("bed_s", "U", 7.0, 29.4, 1.2, 2.0, rot=270)
furn("desk", "U", 9.0, 30.95, 1.6, 0.6, rot=270)
furn("closet", "U", 6.55, 27.4, 2.2, 0.6, rot=90)
# bath 3
furn("vanity", "U", 12.40, 29.0, 0.55, 1.2, rot=180)
furn("shower", "U", 11.3, 30.4, 1.6, 1.2)
furn("wc", "U", 12.40, 27.10, 0.4, 0.6, rot=90)
# gallery
furn("sofa", "U", 15.9, 26.45, 3.0, 0.95, rot=270, h=0.42)
furn("coffee", "U", 16.8, 25.55, 1.2, 0.6, h=0.35)
furn("armchair", "U", 18.40, 27.80, 0.9, 0.9, rot=180)
# laundry
furn("counter", "U", 17.7, 31.05, 1.8, 0.6, rot=270)
# bedroom 2
furn("bed_q", "U", 22.3, 27.4, 1.6, 2.0, rot=270)
furn("nightstand", "U", 21.75, 28.9, 0.5, 0.45)
furn("nightstand", "U", 23.95, 28.9, 0.5, 0.45)
furn("closet", "U", 19.75, 27.05, 0.6, 2.35, rot=0)
furn("desk", "U", 24.1, 25.6, 0.6, 1.3, rot=180)
# bath 2
furn("vanity", "U", 21.25, 31.12, 1.4, 0.55, rot=270)
furn("shower", "U", 23.1, 30.4, 1.55, 1.25)
furn("wc", "U", 19.75, 30.90, 0.6, 0.4, rot=0)
# terrace
furn("lounger", "U", 14.2, 21.6, 0.7, 2.0, rot=0)
furn("lounger", "U", 15.2, 21.6, 0.7, 2.0, rot=0)
furn("table_round", "U", 21.0, 22.8, 1.2, 1.2, h=0.75)
# Basement
furn("screen", "B", 6.35, 21.70, 0.15, 3.0, rot=0)
furn("recliner_row", "B", 8.90, 21.65, 0.95, 3.0, rot=180)
furn("recliner_row", "B", 10.60, 21.65, 0.95, 3.0, rot=180)
furn("bar", "B", 14.0, 26.6, 3.0, 0.7, rot=270)
furn("sofa_l", "B", 13.9, 21.7, 3.0, 2.4)
furn("pool_table", "B", 17.2, 23.0, 1.4, 2.5)
furn("bed_q", "B", 19.15, 22.80, 2.0, 1.6, rot=0)
furn("closet", "B", 24.05, 22.40, 0.6, 2.2, rot=180)
furn("sauna", "B", 19.85, 25.2, 1.6, 1.4)
furn("shower", "B", 20.25, 26.65, 1.2, 0.9)
furn("shower", "B", 23.4, 25.2, 1.25, 1.2)
furn("vanity", "B", 21.65, 25.95, 0.5, 1.2, rot=0)
furn("wc", "B", 22.45, 27.0, 0.4, 0.6, rot=270)
furn("gym", "B", 7.0, 25.6, 1.8, 0.8)
furn("gym", "B", 9.4, 25.6, 1.8, 0.8)
furn("mat", "B", 7.2, 28.2, 1.9, 0.8)
furn("mat", "B", 9.6, 28.2, 1.9, 0.8)
furn("rack", "B", 17.62, 31.1, 1.38, 0.55, rot=180)
furn("tech", "B", 21.7, 30.3, 2.9, 1.3)

# --------------------------------------------------------------------------- #
#  SITE
# --------------------------------------------------------------------------- #
POOL = dict(x0=8.00, y0=9.50, x1=22.00, y1=13.50, water=GARDEN - 0.03, depth=1.45,
            shelf=(19.6, 9.5, 22.0, 13.5))
SITE.update(
    street=dict(x0=30.0, x1=40.0, sidewalk=2.5),
    pool=POOL,
    lawn=[(0.6, 0.6, 29.4, 7.4), (0.6, 7.4, 6.5, 24.0)],
    deck=[(6.5, 7.6, 24.5, 9.5), (6.5, 13.5, 13.0, 16.0), (6.5, 9.5, 8.0, 13.5), (22.0, 9.5, 24.5, 13.5),
          (13.0, 13.5, 24.5, 17.0 - 0.3)],
    paving=[(21.80, 16.80, 25.0, 19.6), (X_E, 15.80, LOT["x1"], 21.80),          # BBQ terrace, carport
            (X_E, 28.80, LOT["x1"], 30.80),                                        # entrance path
            (X_E, 25.80, X_E + 1.20, 28.80), (X_E, 21.80, X_E + 1.20, 25.80)],     # service path
    planting=[(X_E + 1.20, 21.8, LOT["x1"] - 0.3, 25.8), (X_E + 1.2, 25.8, LOT["x1"] - 0.3, 28.8),
              (X_E, 30.8, LOT["x1"] - 0.3, 35.7), (0.3, 24.0, 6.0, 35.7), (6.0, 32.0, X_E, 35.7),
              (0.3, 7.4, 0.6, 24.0)],
    water_feature=(26.2, 31.4, 29.2, 33.6),
    firepit=(3.4, 4.0, 1.4),
    trees=[  # (x, y, r, kind)
        (3.0, 12.0, 2.6, "olive"), (3.2, 19.5, 2.4, "olive"), (17.6, 18.3, 1.6, "olive_s"),
        (27.6, 23.8, 1.7, "olive"), (2.0, 30.0, 2.2, "carob"), (10.0, 34.0, 1.5, "palm"),
        (16.0, 34.0, 1.5, "palm"), (22.0, 34.0, 1.5, "palm"), (27.5, 34.6, 1.4, "palm"),
        (26.0, 2.6, 2.6, "carob"), (12.0, 2.4, 1.6, "palm"), (18.0, 2.4, 1.6, "palm"),
    ],
    fence_h=1.50,
    gate=(LOT["x1"], 28.8, 30.8),
    meters=(LOT["x1"] - 0.6, 22.8, LOT["x1"], 24.8),
    loungers=[(9.0, 14.2), (10.2, 14.2), (11.4, 14.2), (12.6, 14.2)],
    outdoor_shower=(6.8, 8.0),
    bbq=(22.0, 19.9, 24.4, 20.55),
    patio_stair=(14.10, 17.00, 20.42, 18.00),   # 20R × 16.9/28, w 1.00, top landing x 19.42–20.42
)
RISERS = [(12.40, 31.40, 12.70, 31.70), (19.72, 31.40, 20.02, 31.70)]   # wet-room riser shafts U→G→B
CARS = [(25.00, 15.95, 30.00, 18.45), (25.00, 18.95, 30.00, 21.45)]
# escape stair from the sunken patio to the garden: 20 risers along the south retaining wall
PATIO_STAIR = dict(x0=14.10, y0=17.00, y1=18.00, n=20, t=0.28, z0=LV["B"] - 0.02, z1=GARDEN)


# --------------------------------------------------------------------------- #
#  Convenience
# --------------------------------------------------------------------------- #
OUTLINES = {
    "B": [(X_W, Y_S_G), (X_E, Y_S_G), (X_E, Y_N), (X_W, Y_N)],
    "G": [(X_W, Y_S_G), (X_E, Y_S_G), (X_E, Y_N), (X_W, Y_N)],
    "U": UF_OUT,
    "R": RX_OUT,
}
# structural grid (wall / column centre lines)
GRID_X = [("A", 6.15), ("B", 12.85), ("C", 19.06), ("D", 24.85)]
GRID_Y = [("1", 16.15), ("2", 21.15), ("3", 25.15), ("4", 31.85)]


def walls_on(level):
    return [w for w in WALLS if w.level == level]


def rooms_on(level):
    return [r for r in ROOMS if r.level == level]


def furn_on(level):
    return [f for f in FURN if f.level == level]


LEVEL_NAMES = {"B": "קומת מרתף", "G": "קומת קרקע", "U": "קומה א'", "R": "תכנית גג"}
