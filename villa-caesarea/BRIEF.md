# בית כורכר – Beit Kurkar · Boutique villa in Caesarea (final project, Practical Engineers – Architecture & Interior Design)

Supervisor (מנחה): **שירן שריקי**. Student name is a placeholder in `model.PROJECT`.

## Concept
* Site: Caesarea, **Neighborhood 13 (Golf)** – highest point of Caesarea, lots 1,000–1,200 m², golf-community landscape.
  Study lot 30 × 36 m = 1,080 m²; street on the **east**; **west** boundary faces the golf course (open view, sea breeze W–NW).
* Idea: **"Ridge & Horizon"** – a heavy ground floor "base" clad in warm kurkar-tone natural limestone (the coastal kurkar ridge;
  Herod built Caesarea of kurkar coated in white stucco) and a light **white-plaster upper volume** laid across it,
  cantilevering 5 m south toward pool & garden and framing the horizon with a recessed master loggia. Aqueduct rhythm →
  vertical aluminium wood-look louvres (50×200 @180) on the west (sunset) faces.
* Programme: basement (cinema, gym, lounge+bar opening to a **sunken patio**, guest suite, spa, wine, technical),
  ground floor (living, dining, kitchen+island, pantry, foyer with pivot door, guest WC, covered terrace under cantilever),
  upper floor (master suite with loggia/dressing/bath, ממ"ד used as child room, bedroom 2 en-suite, family gallery,
  laundry, family roof terrace on GF roof), roof (roof exit, roof terrace with pergola, PV), 14×4 m pool, stacked U-stair + home lift.

## Planning base case (Neighborhood 13 – verify against takanon 303-0207092)
Main area 35% (378 m²) over 2 floors; service 16% (173 m²); coverage 40%; 2 floors above entrance + 1 basement (outline of floor above);
setbacks assumed front(E) 5 / side 4 / rear(W) 6 m; parking 2 in lot; pool water ≤60 m², depth ≤1.8; roof PV mandatory.
Regulations used: stairs 2R+T = 61–63 cm, riser ≤17.5, tread ≥26 (we use 28); railings 1.05 m (0.90 along stair slope), gaps ≤10 cm;
ממ"ד ≥9 m² net, RC walls 25–30 cm, blast door 80/200, window ≤100/100 with steel shutter; habitable rooms clear height ≥2.50.
Climate: summer noon sun altitude ≈81°, equinox ≈57.5°, winter ≈34°; summer W–NW sea breeze; salt air → marine-grade alu, SS316.

## Code conventions (villa-caesarea/src)
* `model.py` – single source of truth (metres; origin lot SW corner; X east, Y north; Z relative to ±0.00 = +18.50).
  Levels `LV = {B:-3.50, G:0.00, U:+3.60, R:+7.00, RX:+9.80}`; slab 30 cm + 10 cm finishes; ext. wall 30 = 20 block/RC + 10 insulation & cladding.
* `geom.py` – converts model to axis-aligned boxes (`all_boxes()`), each `dict(x0,y0,z0,x1,y1,z1,mat,cls,level)`.
* `draw.py` – `Sheet` (paper mm, y down, SVG) and `View(sheet, ox, oy, scale)` (model metres → paper, optional DXF mirror).
  Text: `sh.text(x, y, t, size, anchor='left'|'middle'|'right', weight)`; Hebrew handled (RTL). Hatches: `fill="pat:concrete"` etc.
  Line weights: `lw='xs'|'s'|'m'|'l'|'xl'|'xxl'`. Helpers: `drawing_title`, `north_arrow`, `scale_bar`, `View.dim_chain`, `View.level_mark`.
* `sheets.py` – A1 landscape (841×594 mm) sheets; builder signature `fn(sh: Sheet, box)` where `box=(x,y,w,h)` free area left of title block.
* `build.py [nums] --png --nopdf` renders sheets to `out/sheets/*.html|pdf` and previews `out/png/sheet_NN.png`.
* Dimensions on drawings in **cm** (Israeli convention), levels in m (+3.60). All text in Hebrew.
