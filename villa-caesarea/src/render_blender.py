#!/usr/bin/env python3
"""render_blender.py - photoreal Cycles renders of 'Beit Kurkar' built from geom.all_boxes().

The building is NOT modelled here: every architectural element comes from geom.all_boxes() (the same boxes that
drive the elevations / sections), so renders always match the drawings.  This script only adds materials,
lighting, sky, vegetation, furniture detail (at model.FURN positions), neighbouring context and cameras.

usage (run with plain python3, bpy module):
    python3 render_blender.py ext_01                       # final render of one camera
    python3 render_blender.py ext_01 int_02 --samples 64   # several cameras, custom samples
    python3 render_blender.py all                          # every camera
    python3 render_blender.py ext_03 --preview             # fast low-res preview (to /tmp/beit_kurkar_previews)
    python3 render_blender.py --export                     # out/model/beit_kurkar.glb + .blend (no render)
    python3 render_blender.py --list                       # list cameras
options: --width W  --samples N  --out DIR  --threads N  --noveg  --blend  --export
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Euler, Matrix, Vector, noise as mnoise  # noqa: E402

import model as M  # noqa: E402
import geom as G  # noqa: E402

OUT_RENDERS = os.path.join(ROOT, "out", "renders")
OUT_MODEL = os.path.join(ROOT, "out", "model")
PREVIEW_DIR = "/tmp/beit_kurkar_previews"

WARM = (1.0, 0.66, 0.38)       # ~2700 K
WARM2 = (1.0, 0.68, 0.40)      # ~2900 K
POOLC = (0.30, 0.82, 1.0)

# =========================================================================== #
#  Cameras
# =========================================================================== #
# loc / tgt in model metres. level=True -> two-point perspective (vertical lines stay vertical, shift_y frames).
CAMS = {
    "ext_01": dict(mode="dusk", loc=(6.5, 3.6, 1.2), tgt=(12.8, 18.5, 4.0), lens=21, level=True, exposure=0.6,
                   desc="hero - south-west, eye level, dusk: cantilever over the pool"),
    "ext_02": dict(mode="day", loc=(9.6, 1.35, 1.6), tgt=(9.6, 17.0, 4.6), lens=24, level=True, exposure=0.0,
                   desc="garden / pool axis looking north at the cantilevered master loggia"),
    "ext_03": dict(mode="dusk", loc=(40.4, 26.8, 1.40), tgt=(25.0, 24.2, 4.6), lens=22, level=True, exposure=0.9,
                   desc="street (east) facade: pivot door, canopy, carport"),
    "ext_04": dict(mode="day", loc=(-16.0, -13.0, 25.0), tgt=(15.5, 20.0, 1.5), lens=30, level=False, exposure=0.0,
                   desc="aerial south-west 3/4 view: roof terrace, whole lot"),
    "ext_05": dict(mode="dusk", loc=(21.1, 19.0, -1.9), tgt=(15.0, 19.6, -1.2), lens=19, level=True, exposure=0.8,
                   desc="sunken patio + covered terrace under the cantilever"),
    "int_01": dict(mode="int_day", loc=(12.0, 30.95, 1.30), tgt=(8.2, 22.0, 1.10), lens=18, level=True, exposure=1.2,
                   desc="living room toward the garden"),
    "int_02": dict(mode="int_day", loc=(13.55, 24.95, 1.40), tgt=(22.0, 22.9, 1.10), lens=18, level=True, exposure=1.6,
                   desc="kitchen, island and dining"),
    "int_03": dict(mode="int_dusk", loc=(12.35, 21.3, 4.95), tgt=(8.0, 17.4, 4.80), lens=18, level=True,
                   exposure=0.9, desc="master bedroom toward the loggia"),
}

# per mode: sun / sky / light-group multipliers
MODES = {
    "day": dict(sun_el=46.0, sun_az=218.0, sun_E=5.5, sun_col=(1.0, 0.95, 0.88), sky=0.22, dust=0.6, look="AgX - Punchy",
                lights=dict(interior=0.0, downlight=0.0, pendant=0.0, garden=0.0, pool=0.0, soffit=0.0,
                            neighbour=0.0, fire=0.0, lamp=0.0, portal=0.0)),
    "dusk": dict(sun_el=float(os.environ.get("BK_EL", -1.0)), sun_az=256.0, sun_E=float(os.environ.get("BK_SUNE", 0.0)),
                 sun_col=(1.0, 0.50, 0.24), sky=float(os.environ.get("BK_SKY", 0.35)), dust=2.5,
                 lights=dict(interior=1.0, downlight=1.0, pendant=1.0, garden=1.0, pool=1.0, soffit=1.0,
                             neighbour=1.0, fire=1.0, lamp=1.0, portal=0.0)),
    "int_day": dict(sun_el=38.0, sun_az=232.0, sun_E=4.5, sun_col=(1.0, 0.95, 0.88), sky=0.25, dust=0.6,
                    lights=dict(interior=0.12, downlight=0.0, pendant=0.35, garden=0.0, pool=0.0, soffit=0.0,
                                neighbour=0.0, fire=0.6, lamp=0.0, portal=1.0)),
    "int_dusk": dict(sun_el=1.5, sun_az=258.0, sun_E=1.2, sun_col=(1.0, 0.48, 0.22), sky=0.55, dust=2.5,
                     lights=dict(interior=0.55, downlight=0.8, pendant=1.0, garden=1.0, pool=1.0, soffit=1.0,
                                 neighbour=1.0, fire=1.0, lamp=1.0, portal=0.0)),
}


# =========================================================================== #
#  Helpers
# =========================================================================== #
def srgb(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple([x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [a])


def _find(socks, key):
    for s in socks:
        if s.name == key and s.enabled:
            return s
    k2 = key.replace("_", " ")
    for s in socks:
        if s.name == k2 and s.enabled:
            return s
    for s in socks:
        if s.identifier == key:
            return s
    for s in socks:
        if s.name in (key, k2):
            return s
    raise KeyError(key)


class NT:
    """tiny node-tree builder"""

    def __init__(self, nt):
        self.nt = nt
        nt.nodes.clear()
        self._tc = None

    def n(self, typ, props=None, **inputs):
        nd = self.nt.nodes.new(typ)
        for k, v in (props or {}).items():
            setattr(nd, k, v)
        for k, v in inputs.items():
            self.set(nd, k, v)
        return nd

    def set(self, nd, key, v):
        s = _find(nd.inputs, key)
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, s)
        else:
            if isinstance(v, (tuple, list)) and len(v) == 3:
                try:
                    if len(s.default_value) == 4:
                        v = (*v, 1.0)
                except TypeError:
                    pass
            s.default_value = v

    @staticmethod
    def o(nd, key=0):
        if isinstance(key, int):
            return nd.outputs[key]
        return _find(nd.outputs, key)

    def tc(self, key="UV"):
        if self._tc is None:
            self._tc = self.n("ShaderNodeTexCoord")
        return self._tc.outputs[key]

    def mix(self, fac, a, b, blend="MIX"):
        nd = self.n("ShaderNodeMix", props=dict(data_type="RGBA", blend_type=blend))
        self.set(nd, "Factor_Float", fac)
        self.set(nd, "A_Color", a)
        self.set(nd, "B_Color", b)
        return self.o(nd, "Result_Color")

    def math(self, op, a, b=0.0):
        nd = self.n("ShaderNodeMath", props=dict(operation=op))
        ins = [s for s in nd.inputs]
        for s, v in zip(ins, (a, b)):
            if isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, s)
            else:
                s.default_value = v
        return nd.outputs[0]

    def ramp(self, fac, stops):
        nd = self.n("ShaderNodeValToRGB")
        self.set(nd, "Fac", fac)
        cr = nd.color_ramp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for el, (p, c) in zip(cr.elements, stops):
            el.position = p
            el.color = c if len(c) == 4 else (*c, 1.0)
        return nd.outputs[0]

    def noise(self, vec, scale, detail=4.0, rough=0.5, dist=0.0, out="Fac"):
        nd = self.n("ShaderNodeTexNoise", Vector=vec, Scale=scale, Detail=detail, Roughness=rough, Distortion=dist)
        return self.o(nd, out)

    def bump(self, height, strength=0.2, dist=0.02, normal=None):
        nd = self.n("ShaderNodeBump", Height=height, Strength=strength, Distance=dist)
        if normal is not None:
            self.set(nd, "Normal", normal)
        return nd.outputs[0]

    def output(self, shader):
        out = self.n("ShaderNodeOutputMaterial")
        self.nt.links.new(shader, out.inputs["Surface"])
        return out


MATS = {}
SIMPLE = {}            # name -> (rgba, roughness, metallic, alpha) for glTF export
EMIT = {}              # light group -> [(emission socket, base strength)]


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, NT(m.node_tree)


def principled(T, color, rough=0.5, metal=0.0, normal=None, **kw):
    p = T.n("ShaderNodeBsdfPrincipled", Base_Color=color, Roughness=rough, Metallic=metal)
    for k, v in kw.items():
        T.set(p, k, v)
    if normal is not None:
        T.set(p, "Normal", normal)
    return p


def shadow_transparent(T, shader, tint=(1, 1, 1, 1)):
    """let shadow rays pass (no caustics needed) - sun light reaches interiors / pool floor"""
    lp = T.n("ShaderNodeLightPath")
    tr = T.n("ShaderNodeBsdfTransparent", Color=tint)
    mx = T.n("ShaderNodeMixShader", Fac=T.o(lp, "Is Shadow Ray"))
    T.nt.links.new(shader, mx.inputs[1])
    T.nt.links.new(tr.outputs[0], mx.inputs[2])
    return mx.outputs[0]


# --------------------------------------------------------------------------- materials
def m_stone(name="stone"):
    """warm kurkar-tone natural limestone, 60x120 panels (running bond), porous texture"""
    m, T = new_mat(name)
    uv = T.tc("UV")
    ob = T.tc("Object")
    br = T.n("ShaderNodeTexBrick", Vector=uv, Color1=srgb("#D8C29F"), Color2=srgb("#CDB48D"),
             Mortar=srgb("#A8957A"), Scale=1.0, Mortar_Size=0.0045, Mortar_Smooth=0.2, Bias=0.0,
             Brick_Width=1.20, Row_Height=0.60, props=dict(offset=0.5, offset_frequency=2))
    big = T.noise(ob, 0.6, 3, 0.5)
    tone = T.mix(T.math("MULTIPLY", big, 0.35), T.o(br, "Color"), srgb("#E0CCA8"), "OVERLAY")
    fine = T.noise(ob, 9.0, 8, 0.65)
    vor = T.n("ShaderNodeTexVoronoi", Vector=ob, Scale=55.0)
    pores = T.math("LESS_THAN", T.o(vor, "Distance"), 0.10)
    dark = T.ramp(fine, [(0.35, (0.80, 0.76, 0.70)), (0.7, (1.0, 1.0, 1.0))])
    col = T.mix(1.0, tone, dark, "MULTIPLY")
    col = T.mix(T.math("MULTIPLY", pores, 0.45), col, srgb("#7E6A52"))
    h = T.math("ADD", T.math("MULTIPLY", fine, 0.25), T.math("MULTIPLY", T.o(br, "Fac"), -0.6))
    h = T.math("ADD", h, T.math("MULTIPLY", pores, -0.3))
    p = principled(T, col, 0.82, normal=T.bump(h, 0.35, 0.01))
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb("#C8AB84"), 0.85, 0.0, 1.0)
    return m


def m_plaster(name, hexc="#EEEAE2", rough=0.9, bump=0.06):
    m, T = new_mat(name)
    ob = T.tc("Object")
    big = T.noise(ob, 0.35, 3)
    col = T.mix(T.math("MULTIPLY", big, 0.10), srgb(hexc), srgb("#D9D2C6"))
    fine = T.noise(ob, 35.0, 6, 0.6)
    p = principled(T, col, rough, normal=T.bump(fine, bump, 0.01))
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb(hexc), rough, 0.0, 1.0)
    return m


def m_rc_fair(name="rc_fair"):
    m, T = new_mat(name)
    uv = T.tc("UV")
    ob = T.tc("Object")
    br = T.n("ShaderNodeTexBrick", Vector=uv, Color1=srgb("#B2AEA6"), Color2=srgb("#A9A59D"),
             Mortar=srgb("#8C8881"), Scale=1.0, Mortar_Size=0.003, Bias=0.0, Brick_Width=2.5, Row_Height=1.25,
             props=dict(offset=0.0, offset_frequency=1))
    mot = T.noise(ob, 2.2, 6, 0.55)
    col = T.mix(T.math("MULTIPLY", mot, 0.5), T.o(br, "Color"), srgb("#8F8B84"), "MULTIPLY")
    col = T.mix(0.35, col, srgb("#C2BEB6"), "OVERLAY")
    # tie holes at 62.5/62.5 cm
    tie = T.n("ShaderNodeTexBrick", Vector=uv, Scale=1.0, Mortar_Size=0.0, Brick_Width=0.625, Row_Height=0.625,
              Color1=(0, 0, 0, 1), Color2=(0, 0, 0, 1), props=dict(offset=0.0, offset_frequency=1))
    p = principled(T, col, 0.72, normal=T.bump(T.math("ADD", T.math("MULTIPLY", mot, 0.2),
                                                      T.math("MULTIPLY", T.o(br, "Fac"), -0.5)), 0.25, 0.01))
    del tie
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb("#ADA9A1"), 0.75, 0.0, 1.0)
    return m


def m_tiles(name, c1, c2, grout, size, rough, joint=0.002, offset=0.0, var=0.25, w=None):
    m, T = new_mat(name)
    uv = T.tc("UV")
    ob = T.tc("Object")
    br = T.n("ShaderNodeTexBrick", Vector=uv, Color1=srgb(c1), Color2=srgb(c2), Mortar=srgb(grout), Scale=1.0,
             Mortar_Size=joint, Bias=0.0, Brick_Width=w or size, Row_Height=size,
             props=dict(offset=offset, offset_frequency=2 if offset else 1))
    n = T.noise(ob, 3.0, 5)
    col = T.mix(var * 0.3, T.o(br, "Color"), T.ramp(n, [(0.3, srgb(c2)), (0.7, srgb(c1))]))
    p = principled(T, col, rough, normal=T.bump(T.math("MULTIPLY", T.o(br, "Fac"), -1.0), 0.3, 0.003))
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb(c1), rough, 0.0, 1.0)
    return m


def m_wood(name, c_light, c_dark, rough=0.45, scale=6.0, planks=None, metal=0.0, coat=0.0, distort=7.0, grain="u"):
    """grain='u': grain lines run along U (decks, floors); 'v': along V (= vertical on walls / fins)"""
    m, T = new_mat(name)
    uv = T.tc("UV")
    ob = T.tc("Object")
    mp = T.n("ShaderNodeMapping", Vector=uv, Scale=(1.0, 8.0, 1.0) if grain == "u" else (8.0, 1.0, 1.0))
    wv = T.n("ShaderNodeTexWave", Vector=mp.outputs[0], Scale=scale, Distortion=distort, Detail=3.0, Detail_Scale=1.5,
             props=dict(wave_type="BANDS", bands_direction="Y" if grain == "u" else "X"))
    n = T.noise(uv, 40.0, 3)
    g = T.math("MULTIPLY", T.o(wv, "Fac"), 0.75)
    g = T.math("ADD", g, T.math("MULTIPLY", n, 0.25))
    col = T.ramp(g, [(0.15, srgb(c_dark)), (0.85, srgb(c_light))])
    h = g
    if planks:
        pw, pl, mortar = planks
        br = T.n("ShaderNodeTexBrick", Vector=uv, Color1=(1, 1, 1, 1), Color2=(0.78, 0.78, 0.78, 1),
                 Mortar=(0.08, 0.06, 0.05, 1), Scale=1.0, Mortar_Size=mortar, Bias=0.0, Brick_Width=pl,
                 Row_Height=pw, props=dict(offset=0.37, offset_frequency=1))
        col = T.mix(1.0, col, T.o(br, "Color"), "MULTIPLY")
        h = T.math("ADD", T.math("MULTIPLY", g, 0.3), T.math("MULTIPLY", T.o(br, "Fac"), -1.0))
    p = principled(T, col, rough, metal, normal=T.bump(h, 0.15, 0.004), Coat_Weight=coat)
    del ob
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb(c_light), rough, metal, 1.0)
    return m


def m_simple(name, color, rough=0.5, metal=0.0, **kw):
    m, T = new_mat(name)
    c = srgb(color) if isinstance(color, str) else color
    p = principled(T, c, rough, metal, **kw)
    T.output(p.outputs[0])
    SIMPLE[name] = (c, rough, metal, 1.0)
    return m


def m_fabric(name, hexc, rough=0.95, scale=220.0, sheen=0.6):
    m, T = new_mat(name)
    uv = T.tc("UV")
    ob = T.tc("Object")
    wv = T.n("ShaderNodeTexWave", Vector=uv, Scale=scale, props=dict(wave_type="BANDS", bands_direction="DIAGONAL"))
    n = T.noise(ob, 4.0, 3)
    col = T.mix(T.math("MULTIPLY", n, 0.3), srgb(hexc), srgb("#000000"), "MULTIPLY")
    col = T.mix(0.35, srgb(hexc), col)
    p = principled(T, col, rough, normal=T.bump(T.o(wv, "Fac"), 0.08, 0.002), Sheen_Weight=sheen)
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb(hexc), rough, 0.0, 1.0)
    return m


def m_glass(name, tint=(0.90, 0.95, 0.94, 1.0), refl=1.0, rough=0.0):
    m, T = new_mat(name)
    tr = T.n("ShaderNodeBsdfTransparent", Color=tint)
    gl = T.n("ShaderNodeBsdfGlossy", Color=(refl, refl, refl, 1), Roughness=rough)
    fr = T.n("ShaderNodeFresnel", IOR=1.52)
    geo = T.n("ShaderNodeNewGeometry")
    # back faces: no reflection (avoids total-internal-reflection arcs on thin panes)
    fac = T.math("MULTIPLY", T.o(fr, "Fac"), T.math("SUBTRACT", 1.0, T.o(geo, "Backfacing")))
    mx = T.n("ShaderNodeMixShader", Fac=fac)
    T.nt.links.new(tr.outputs[0], mx.inputs[1])
    T.nt.links.new(gl.outputs[0], mx.inputs[2])
    T.output(shadow_transparent(T, mx.outputs[0], tint))
    SIMPLE[name] = ((0.72, 0.82, 0.84, 1.0), 0.05, 0.0, 0.28)
    return m


def m_frosted(name="glass_frosted"):
    m, T = new_mat(name)
    tl = T.n("ShaderNodeBsdfTranslucent", Color=(0.85, 0.88, 0.88, 1))
    gl = T.n("ShaderNodeBsdfGlossy", Roughness=0.15)
    mx = T.n("ShaderNodeMixShader", Fac=0.12)
    T.nt.links.new(tl.outputs[0], mx.inputs[1])
    T.nt.links.new(gl.outputs[0], mx.inputs[2])
    T.output(mx.outputs[0])
    SIMPLE[name] = ((0.85, 0.88, 0.88, 1), 0.3, 0.0, 0.7)
    return m


def m_water(name="water"):
    m, T = new_mat(name)
    ob = T.tc("Object")
    n1 = T.noise(ob, 1.4, 4, 0.5, dist=0.6)
    n2 = T.noise(ob, 7.0, 3)
    h = T.math("ADD", n1, T.math("MULTIPLY", n2, 0.25))
    p = T.n("ShaderNodeBsdfPrincipled", Base_Color=(0.80, 0.97, 0.96, 1), Roughness=0.0,
            Transmission_Weight=1.0, IOR=1.333)
    T.set(p, "Normal", T.bump(h, 0.22, 0.03))
    T.output(shadow_transparent(T, p.outputs[0], (0.85, 0.97, 0.97, 1)))
    SIMPLE[name] = ((0.25, 0.65, 0.70, 1), 0.05, 0.0, 0.6)
    return m


def m_grass(name, c1="#6C8A3A", c2="#93A552", stripes=0.0, dry=0.15):
    m, T = new_mat(name)
    ob = T.tc("Object")
    n1 = T.noise(ob, 0.18, 4)
    n2 = T.noise(ob, 2.5, 6)
    col = T.ramp(n1, [(0.35, srgb(c1)), (0.65, srgb(c2))])
    col = T.mix(T.math("MULTIPLY", n2, dry), col, srgb("#A39A5E"))
    if stripes:
        sep = T.n("ShaderNodeSeparateXYZ", Vector=ob)
        wv = T.n("ShaderNodeMath", props=dict(operation="SINE"))
        T.nt.links.new(T.math("MULTIPLY", sep.outputs[1], 0.45), wv.inputs[0])
        st = T.math("GREATER_THAN", wv.outputs[0], 0.0)
        col = T.mix(T.math("MULTIPLY", st, stripes), col, srgb("#B4C46A"), "OVERLAY")
    fine = T.noise(ob, 180.0, 2)
    p = principled(T, col, 0.95, normal=T.bump(fine, 0.5, 0.01), Specular_IOR_Level=0.3)
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb(c1), 0.95, 0.0, 1.0)
    return m


def m_leaves(name, c1, c2, transl=0.25, rough=0.65, scale=9.0):
    m, T = new_mat(name)
    ob = T.tc("Object")
    vor = T.n("ShaderNodeTexVoronoi", Vector=ob, Scale=scale * 3)
    n = T.noise(ob, scale * 0.25, 3)
    col = T.ramp(T.math("ADD", T.math("MULTIPLY", n, 0.7), T.math("MULTIPLY", T.o(vor, "Distance"), 0.5)),
                 [(0.25, srgb(c2)), (0.75, srgb(c1))])
    p = principled(T, col, rough, normal=T.bump(T.o(vor, "Distance"), 0.6, 0.03), Specular_IOR_Level=0.35)
    tl = T.n("ShaderNodeBsdfTranslucent", Color=col)
    mx = T.n("ShaderNodeMixShader", Fac=transl)
    T.nt.links.new(p.outputs[0], mx.inputs[1])
    T.nt.links.new(tl.outputs[0], mx.inputs[2])
    T.output(mx.outputs[0])
    SIMPLE[name] = (srgb(c1), 0.8, 0.0, 1.0)
    return m


def m_emit(name, color, strength, group, base_shader=None):
    m, T = new_mat(name)
    em = T.n("ShaderNodeEmission", Color=color, Strength=strength)
    EMIT.setdefault(group, []).append((em.inputs["Strength"], strength))
    if base_shader:
        bs = principled(T, srgb(base_shader), 0.4)
        ad = T.n("ShaderNodeAddShader")
        T.nt.links.new(bs.outputs[0], ad.inputs[0])
        T.nt.links.new(em.outputs[0], ad.inputs[1])
        T.output(ad.outputs[0])
    else:
        T.output(em.outputs[0])
    SIMPLE[name] = ((*color[:3], 1.0), 0.5, 0.0, 1.0)
    return m


def m_marble(name="marble"):
    m, T = new_mat(name)
    ob = T.tc("Object")
    n = T.noise(ob, 1.6, 8, 0.6, dist=3.0)
    wv = T.n("ShaderNodeTexWave", Vector=ob, Scale=1.2, Distortion=12.0, Detail=6.0,
             props=dict(wave_type="BANDS", bands_direction="DIAGONAL"))
    v = T.math("POWER", T.o(wv, "Fac"), 10.0)
    col = T.mix(T.math("MULTIPLY", v, 0.55), srgb("#EEEBE6"), srgb("#8F8A84"))
    col = T.mix(T.math("MULTIPLY", n, 0.15), col, srgb("#D8D2C8"))
    p = principled(T, col, 0.18, Coat_Weight=0.2)
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb("#EAE6E0"), 0.2, 0.0, 1.0)
    return m


def m_pv(name="pv"):
    m, T = new_mat(name)
    uv = T.tc("UV")
    br = T.n("ShaderNodeTexBrick", Vector=uv, Color1=srgb("#151C2C"), Color2=srgb("#18203A"),
             Mortar=srgb("#A0A4AA"), Scale=1.0, Mortar_Size=0.004, Brick_Width=0.166, Row_Height=0.166,
             props=dict(offset=0.0, offset_frequency=1))
    p = principled(T, T.o(br, "Color"), 0.15, 0.3, Coat_Weight=1.0)
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb("#161D30"), 0.2, 0.3, 1.0)
    return m


def m_palm_trunk(name="palm_trunk"):
    m, T = new_mat(name)
    ob = T.tc("Object")
    wv = T.n("ShaderNodeTexWave", Vector=ob, Scale=9.0, Distortion=2.0,
             props=dict(wave_type="RINGS", rings_direction="Z"))
    sep = T.n("ShaderNodeSeparateXYZ", Vector=ob)
    rings = T.n("ShaderNodeMath", props=dict(operation="SINE"))
    T.nt.links.new(T.math("MULTIPLY", sep.outputs[2], 28.0), rings.inputs[0])
    n = T.noise(ob, 6.0, 5)
    col = T.ramp(T.math("ADD", T.math("MULTIPLY", rings.outputs[0], 0.25), n),
                 [(0.3, srgb("#5E4D3C")), (0.75, srgb("#9C8A70"))])
    p = principled(T, col, 0.9, normal=T.bump(T.math("ADD", rings.outputs[0], T.math("MULTIPLY", n, 0.6)), 0.6, 0.03))
    del wv
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb("#86745E"), 0.9, 0.0, 1.0)
    return m


def m_bark(name="bark", c1="#7A6A58", c2="#463A2F"):
    m, T = new_mat(name)
    ob = T.tc("Object")
    n = T.noise(ob, 5.0, 8, 0.7, dist=1.5)
    col = T.ramp(n, [(0.3, srgb(c2)), (0.7, srgb(c1))])
    p = principled(T, col, 0.9, normal=T.bump(n, 0.8, 0.04))
    T.output(p.outputs[0])
    SIMPLE[name] = (srgb(c1), 0.9, 0.0, 1.0)
    return m


def build_materials():
    mk = {}
    mk["stone"] = m_stone()
    mk["plaster"] = m_plaster("plaster", "#EFEBE3", 0.88, 0.05)
    mk["white"] = m_plaster("white", "#F1EEE8", 0.85, 0.02)
    mk["block"] = mk["plaster"]
    mk["rc"] = m_plaster("rc", "#E9E5DD", 0.9, 0.02)
    mk["rc_fair"] = m_rc_fair()
    mk["floor"] = m_tiles("floor", "#DCD6CC", "#D2CBBF", "#B9B1A5", 1.2, 0.22, joint=0.0016)
    mk["roofing"] = m_tiles("roofing", "#C9C5BC", "#BDB8AE", "#A9A49A", 0.6, 0.85, joint=0.006)
    mk["paving"] = m_tiles("paving", "#DBD1BE", "#CFC3AD", "#B3A790", 0.45, 0.72, joint=0.006, offset=0.5, w=0.9)
    mk["stone_white"] = m_tiles("stone_white", "#ECE6DB", "#E2DACC", "#C9C0B0", 0.5, 0.55, joint=0.003, w=1.0)
    mk["glass"] = m_glass("glass")
    mk["glass_frosted"] = m_frosted()
    mk["car_glass"] = m_glass("car_glass", tint=(0.08, 0.09, 0.10, 1), refl=1.0)
    mk["n_glass"] = m_glass("n_glass", tint=(0.18, 0.20, 0.21, 1))
    mk["frame"] = m_simple("frame", "#2E2924", 0.38, 0.75)
    mk["steel"] = m_simple("steel", "#B9B9B6", 0.22, 1.0)
    mk["alu_wood"] = m_wood("alu_wood", "#9E7A58", "#694C35", rough=0.48, scale=4.0, grain="v")
    mk["wood"] = m_wood("wood", "#C3A27A", "#93714E", rough=0.42, scale=5.0)
    mk["wood_dark"] = m_wood("wood_dark", "#5C4433", "#2F2219", rough=0.35, scale=5.0, coat=0.3, grain="v")
    mk["deck"] = m_wood("deck", "#94704C", "#6B4D33", rough=0.62, scale=7.0, planks=(0.145, 2.4, 0.012))
    mk["water"] = m_water()
    mk["pool_plaster"] = m_plaster("pool_plaster", "#DCEDF0", 0.55, 0.02)
    mk["grass"] = m_grass("grass", "#5F7F33", "#86A048")
    mk["grass_n"] = m_grass("grass_n", "#5A7A33", "#7E9846")
    mk["golf"] = m_grass("golf", "#5E8A33", "#7FA544", stripes=0.35, dry=0.08)
    mk["planting"] = m_tiles("planting", "#4E3D2E", "#5A4836", "#3A2D22", 0.11, 1.0, joint=0.02, offset=0.5, var=1.0)
    mk["soil"] = m_simple("soil", "#5A4836", 1.0)
    mk["gravel"] = m_tiles("gravel", "#BEB6A6", "#A9A090", "#8E8676", 0.04, 1.0, joint=0.05, offset=0.5, var=1.0)
    mk["asphalt"] = m_tiles("asphalt", "#3B3B3C", "#363637", "#3A3A3B", 7.5, 0.85, joint=0.0)
    mk["furn"] = m_simple("furn", "#A79D90", 0.45)
    mk["furn_dark"] = m_wood("furn_dark", "#3D3029", "#231B16", rough=0.4, scale=5.0)
    mk["fabric"] = m_fabric("fabric", "#D6CEC1")
    mk["fabric_dark"] = m_fabric("fabric_dark", "#77695A", scale=90.0)
    mk["fabric_accent"] = m_fabric("fabric_accent", "#A8673F")
    mk["fabric_olive"] = m_fabric("fabric_olive", "#7E7B57")
    mk["bedding"] = m_fabric("bedding", "#F3F0EA", sheen=0.3)
    mk["outdoor_fab"] = m_fabric("outdoor_fab", "#E7E1D6")
    mk["marble"] = m_marble()
    mk["black_gloss"] = m_simple("black_gloss", "#0B0B0C", 0.08, 0.0, Coat_Weight=1.0)
    mk["mirror"] = m_simple("mirror", "#E8E8E8", 0.02, 1.0)
    mk["car"] = m_simple("car", "#3A3D42", 0.32, 0.6, Coat_Weight=1.0)
    mk["car_white"] = m_simple("car_white", "#D9D9D6", 0.3, 0.1, Coat_Weight=1.0)
    mk["tire"] = m_simple("tire", "#141414", 0.8)
    mk["tail"] = m_simple("tail", "#7A0F0F", 0.2, Coat_Weight=1.0)
    mk["n_beige"] = m_plaster("n_beige", "#E4DCCD", 0.88, 0.05)
    mk["felt"] = m_fabric("felt", "#2F5B45")
    mk["sauna"] = m_wood("sauna", "#C8A275", "#9E7A50", rough=0.6)
    mk["pv"] = m_pv()
    mk["bark"] = m_bark()
    mk["palm_trunk"] = m_palm_trunk()
    mk["olive_leaf"] = m_leaves("olive_leaf", "#97A088", "#56634A", transl=0.2, rough=0.55, scale=14)
    mk["carob_leaf"] = m_leaves("carob_leaf", "#47622F", "#22331A", transl=0.15, scale=14)
    mk["palm_leaf"] = m_leaves("palm_leaf", "#7C8A48", "#4C5A2C", transl=0.3, scale=20)
    mk["hedge_leaf"] = m_leaves("hedge_leaf", "#4D6B31", "#2C421D", transl=0.15, scale=14)
    mk["pine_leaf"] = m_leaves("pine_leaf", "#41562C", "#26341A", transl=0.1)
    mk["shrub_leaf"] = m_leaves("shrub_leaf", "#62773E", "#3A4D25", transl=0.2, scale=16)
    mk["lavender"] = m_leaves("lavender", "#8C7BB5", "#5D4F8A", transl=0.25, scale=30)
    mk["lav_leaf"] = m_leaves("lav_leaf", "#9AA488", "#6B7558", transl=0.2, scale=30)
    mk["grass_orn"] = m_leaves("grass_orn", "#B8AE78", "#7F7E4A", transl=0.35, scale=30)
    mk["rug"] = m_fabric("rug", "#B5AA99", scale=70.0)
    mk["parquet"] = m_wood("parquet", "#C8A47B", "#9A7550", rough=0.38, scale=5.0, planks=(0.19, 1.9, 0.0015), distort=4.0)
    mk["carpet"] = m_fabric("carpet", "#5E5852", scale=300.0)
    mk["stone_floor"] = m_tiles("stone_floor", "#DED3C0", "#D2C5AE", "#BDB09A", 0.6, 0.32, joint=0.0015, w=1.2)
    mk["default"] = m_simple("default", "#B5ADA2", 0.6)
    # emissive
    mk["em_down"] = m_emit("em_down", WARM2, 25.0, "downlight")
    mk["em_pend"] = m_emit("em_pend", WARM, 4.0, "pendant")
    mk["em_lamp"] = m_emit("em_lamp", WARM, 6.0, "lamp")
    mk["em_fire"] = m_emit("em_fire", (1.0, 0.42, 0.12), 14.0, "fire")
    mk["em_pool"] = m_emit("em_pool", POOLC, 8.0, "pool")
    mk["em_garden"] = m_emit("em_garden", WARM2, 25.0, "garden")
    mk["em_soffit"] = m_emit("em_soffit", WARM2, 25.0, "soffit")
    mk["n_glow"] = m_emit("n_glow", (1.0, 0.70, 0.42), 1.6, "neighbour", base_shader="#202224")
    mk["em_screen"] = m_emit("em_screen", (0.55, 0.65, 0.8), 0.0, "lamp")
    MATS.update(mk)


ALIAS = {"furn_dark": "furn_dark", "screen": "white"}


def mat(name):
    if name in MATS:
        return MATS[name]
    return MATS["default"]


# =========================================================================== #
#  Mesh building
# =========================================================================== #
_BOXF = [((0, 3, 2, 1), 2), ((4, 5, 6, 7), 2), ((0, 1, 5, 4), 1), ((2, 3, 7, 6), 1), ((3, 0, 4, 7), 0),
         ((1, 2, 6, 5), 0)]


def _uv(v, ax):
    return (v[1], v[2]) if ax == 0 else (v[0], v[2]) if ax == 1 else (v[0], v[1])


def elem_geo(e):
    """element -> (verts, faces[(idx..)], face_axes, smooth_flags)"""
    t = e.get("t", "box")
    if t == "box":
        x0, y0, z0, x1, y1, z1 = e["x0"], e["y0"], e["z0"], e["x1"], e["y1"], e["z1"]
        if min(x1 - x0, y1 - y0, z1 - z0) < 1e-5:
            return None
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1),
             (x0, y1, z1)]
        return v, [f for f, _ in _BOXF], [a for _, a in _BOXF], [e.get("soft", 0) == 2] * 6
    if t == "obox":
        sx, sy, sz = e["size"]
        mtx = Matrix.Translation(e["c"]) @ Euler(e.get("rot", (0, 0, 0)), "ZYX").to_matrix().to_4x4()
        loc = [(-sx / 2, -sy / 2, -sz / 2), (sx / 2, -sy / 2, -sz / 2), (sx / 2, sy / 2, -sz / 2),
               (-sx / 2, sy / 2, -sz / 2), (-sx / 2, -sy / 2, sz / 2), (sx / 2, -sy / 2, sz / 2),
               (sx / 2, sy / 2, sz / 2), (-sx / 2, sy / 2, sz / 2)]
        v = [tuple(mtx @ Vector(p)) for p in loc]
        axes = []
        for f, a in _BOXF:
            nrm = (Vector(v[f[1]]) - Vector(v[f[0]])).cross(Vector(v[f[2]]) - Vector(v[f[1]]))
            axes.append(max(range(3), key=lambda i: abs(nrm[i])))
        return v, [f for f, _ in _BOXF], axes, [e.get("soft", 0) == 2] * 6
    if t == "cyl":
        n = e.get("seg", 20)
        x, y, z0, z1, r = e["x"], e["y"], e["z0"], e["z1"], e["r"]
        r1 = e.get("r1", r)
        v = [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
        v += [(x + r1 * math.cos(2 * math.pi * i / n), y + r1 * math.sin(2 * math.pi * i / n), z1) for i in range(n)]
        if e.get("axis") == "y":   # x,y = centre in x/z plane, z0..z1 = extent along y
            v = [(px, e["zc"] + pz, py) for (px, py, pz) in v]
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        axes = [2, 2] + [0 if abs(math.cos(2 * math.pi * (i + .5) / n)) > .7 else 1 for i in range(n)]
        return v, faces, axes, [False, False] + [True] * n
    if t == "prism":
        pts = e["pts"]
        n = len(pts)
        z0, z1 = e["z0"], e["z1"]
        area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
        if area < 0:   # make CCW
            pts = pts[::-1]
        v = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
        if e.get("axis") == "y":   # pts are (x, z) profile, extruded over y = z0..z1
            v = [(px, pz, py) for (px, py, pz) in v]
        faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        axes = [2, 2]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
            dx, dy = v[j][0] - v[i][0], v[j][1] - v[i][1]
            axes.append(1 if abs(dx) > abs(dy) else 0)
        return v, faces, axes, [False] * len(faces)
    raise ValueError(t)


def mesh_from_elems(name, elems):
    verts, faces, uvs, smooth = [], [], [], []
    for e in elems:
        g = elem_geo(e)
        if not g:
            continue
        v, f, ax, sm = g
        base = len(verts)
        verts += v
        for ff, a, s in zip(f, ax, sm):
            faces.append(tuple(base + i for i in ff))
            for i in ff:
                uvs.extend(_uv(v[i], a))
            smooth.append(s)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if any(e.get("t") in ("prism", "cyl") and e.get("axis") for e in elems):
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", uvs)
    me.polygons.foreach_set("use_smooth", smooth)
    me.validate(clean_customdata=False)
    return me


COLL = {}


def coll(name):
    if name not in COLL:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLL[name] = c
    return COLL[name]


BEVEL = {0: (float(os.environ.get("BK_BEVEL", "0.006")), 1), 1: (0.008, 2), 2: (0.035, 3), 3: (0.0, 0)}
NOBEVEL = {"glass", "glass_frosted", "water", "car_glass", "n_glass", "grass", "golf", "grass_n", "asphalt",
           "planting", "em_down", "em_pool", "em_garden", "em_soffit", "roofing", "floor", "deck", "paving", "frame",
           "alu_wood", "steel", "mirror"}


PRIO = dict(glass=9, frame=8, fin=8, skin=7, rail=7, door=7, pergola=6, furn=6, fence=6, car=6, site=5, pool=5,
            wall=4, column=3, stair=3, slab=2)


def fix_coplanar(elems, eps=0.0015):
    """Coincident same-facing faces of overlapping boxes make Cycles shadow rays hit the twin face (black
    patches).  Move the lower-priority face inward by eps (only that face, so no slits open elsewhere)."""
    boxes = [e for e in elems if e.get("t", "box") == "box"]
    cell = 2.0
    grid = {}
    for i, b in enumerate(boxes):
        for gx in range(int(math.floor(b["x0"] / cell)), int(math.floor(b["x1"] / cell)) + 1):
            for gy in range(int(math.floor(b["y0"] / cell)), int(math.floor(b["y1"] / cell)) + 1):
                grid.setdefault((gx, gy), []).append(i)
        if len(grid) > 400000:
            break
    seen = set()
    moves = {}
    T = 1e-6
    for ids in grid.values():
        if len(ids) > 400:
            continue
        for ai in range(len(ids)):
            for bj in range(ai + 1, len(ids)):
                i, j = ids[ai], ids[bj]
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                a, b = boxes[i], boxes[j]
                if (a["x0"] >= b["x1"] - T or b["x0"] >= a["x1"] - T or a["y0"] >= b["y1"] - T or b["y0"] >= a["y1"] - T
                        or a["z0"] >= b["z1"] - T or b["z0"] >= a["z1"] - T):
                    continue
                for k in "xyz":
                    for side in ("0", "1"):
                        key = k + side
                        if abs(a[key] - b[key]) < T:
                            pa = PRIO.get(a.get("cls"), 6) + (0.5 if a.get("soft", 0) == 2 else 0)
                            pb = PRIO.get(b.get("cls"), 6) + (0.5 if b.get("soft", 0) == 2 else 0)
                            lo = j if pb <= pa else i
                            moves.setdefault(lo, set()).add(key)
    for i, keys in moves.items():
        b = boxes[i]
        for key in keys:
            k = key[0]
            th = b[k + "1"] - b[k + "0"]
            d = min(eps, th * 0.2)
            if key[1] == "0":
                b[key] += d
            else:
                b[key] -= d
    return len(moves)


def add_elems(elems, collection="building", prefix=""):
    n = fix_coplanar(elems)
    if n:
        print(f"  {collection}: nudged {n} coplanar faces")
    groups = {}
    for e in elems:
        groups.setdefault((e["mat"], e.get("soft", 0)), []).append(e)
    objs = []
    for (mname, soft), els in sorted(groups.items()):
        nm = f"{prefix}{mname}" + (f"_s{soft}" if soft else "")
        me = mesh_from_elems(nm, els)
        me.materials.append(mat(mname))
        ob = bpy.data.objects.new(nm, me)
        coll(collection).objects.link(ob)
        w, segs = BEVEL[soft]
        if w > 0 and mname not in NOBEVEL:
            bv = ob.modifiers.new("bevel", "BEVEL")
            bv.width = w
            bv.segments = segs
            bv.limit_method = "ANGLE"
            bv.use_clamp_overlap = True
        objs.append(ob)
    return objs


def bm_object(name, bm, material, collection, loc=(0, 0, 0), smooth=True, mats=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    for mm in (mats or [material]):
        me.materials.append(mat(mm))
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    coll(collection).objects.link(ob)
    return ob


def B(x0, y0, z0, x1, y1, z1, m, soft=0, **kw):
    d = G.B(x0, y0, z0, x1, y1, z1, m, kw.pop("cls", "x"))
    d["soft"] = soft
    d.update(kw)
    return d


# =========================================================================== #
#  Architecture from geom (+ render-side ground handling)
# =========================================================================== #
ISSUES = []


def building_elems():
    bx = G.all_boxes(include_site=True, include_furn=False)
    P = M.SITE["pool"]
    out = []
    shell_in_model = False
    for b in bx:
        mname = b["mat"]
        if b["cls"] == "site" and mname == "grass":
            continue  # replaced by terrain with holes (see terrain_elems)
        if b["cls"] == "car":
            continue  # replaced by simple car models in the same footprint
        if b["cls"] == "furn" and mname == "white" and abs((b["y1"] - b["y0"]) - 1.9) < 1e-6:
            continue  # pool loungers -> detailed loungers at the same spots
        if b["cls"] == "pool" and mname == "water":
            continue  # water surface built in build_scene
        if b["cls"] == "pool" and mname == "rc":
            mname = "pool_plaster"   # model's RC pool shell -> white pool plaster finish
            shell_in_model = True
        if mname in ("asphalt",) or (b["cls"] == "site" and mname == "paving" and b["x0"] >= M.LOT["x1"] - 1e-6):
            b = dict(b)
            b["y0"], b["y1"] = -420.0, 460.0  # continue street / sidewalk to the horizon
        e = dict(b)
        e["mat"] = mname
        e["soft"] = 0
        out.append(e)
    # pool shell (white plaster) around the water volume of the model
    wz, d = P["water"], P["depth"]
    zb = wz - d
    t = 0.25
    top = M.GARDEN - 0.05
    if shell_in_model:
        shell = []
    else:
        shell = [B(P["x0"] - t, P["y0"] - t, zb - t, P["x1"] + t, P["y1"] + t, zb, "pool_plaster"),
            B(P["x0"] - t, P["y0"] - t, zb, P["x1"] + t, P["y0"], top, "pool_plaster"),
            B(P["x0"] - t, P["y1"], zb, P["x1"] + t, P["y1"] + t, top, "pool_plaster"),
            B(P["x0"] - t, P["y0"], zb, P["x0"], P["y1"], top, "pool_plaster"),
            B(P["x1"], P["y0"], zb, P["x1"] + t, P["y1"], top, "pool_plaster")]
    out += shell
    if P.get("shelf"):
        sx0, sy0, sx1, sy1 = P["shelf"]
        out.append(B(sx0, sy0, zb, sx1, sy1, wz - 0.32, "pool_plaster"))
        out.append(B(sx0 - 0.02, sy0, wz - 0.40, sx0, sy1, wz - 0.32, "pool_plaster"))
    return out


def terrain_elems():
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union
    L = M.LOT
    g = M.GARDEN
    top = g - 0.05
    P = M.SITE["pool"]
    raft = [s for s in M.SLABS if s.kind == "raft"][0].rects[0]
    holes = [raft, (P["x0"] - 0.25, P["y0"] - 0.25, P["x1"] + 0.25, P["y1"] + 0.25)]
    # sunken patio: model deck slab at basement level + its retaining walls
    for s in M.SLABS:
        if s.kind == "deck" and s.top < -1.0:
            for r in s.rects:
                holes.append(r)
    lot = sbox(L["x0"], L["y0"], L["x1"], L["y1"]).difference(unary_union([sbox(*h) for h in holes]))
    out = [B(*r[:2], top - 0.8, *r[2:], top, "grass") for r in G.decompose(lot)]
    # context ground
    R = 900.0
    out += [B(-R, -R, top - 1.0, L["x0"], R, top - 0.004, "golf"),                       # golf course (west)
            B(L["x0"], L["y1"], top - 1.0, L["x1"], R, top - 0.004, "grass_n"),          # north neighbours
            B(L["x0"], -R, top - 1.0, L["x1"], L["y0"], top - 0.004, "grass_n")]         # south neighbours
    st = M.SITE["street"]
    xs = L["x1"] + st["sidewalk"] + 7.5
    out += [B(xs, -420, M.STREET - 0.1, xs + 2.5, 460, M.STREET, "paving"),            # far sidewalk
            B(xs + 2.5, -R, M.STREET - 1.0, R, R, M.STREET + 0.05, "grass_n")]
    # kerb line + road centre dashes
    for y in range(-200, 260, 6):
        out.append(B(L["x1"] + st["sidewalk"] + 3.68, y, M.STREET - 0.15, L["x1"] + st["sidewalk"] + 3.82, y + 3,
                     M.STREET - 0.148, "plaster"))
    return out


def room_floor_elems():
    """3 mm finish overlay per room from model.ROOMS[].floor (parquet / carpet / natural stone; porcelain = base)"""
    out = []
    for r in M.ROOMS:
        if r.outdoor or r.level not in ("B", "G", "U"):
            continue
        m = "parquet" if "פרקט" in r.floor else "carpet" if "שטיח" in r.floor else \
            "stone_floor" if "אבן" in r.floor else None
        if not m:
            continue
        z = M.LV[r.level]
        for (x0, y0, x1, y1) in r.rects:
            out.append(B(x0, y0, z, x1, y1, z + 0.003, m, 0, cls="site"))
    return out


def derived_site_elems():
    """Things the model describes semantically but geom does not box (documented in report)."""
    out = []
    g = M.GARDEN
    covered = []
    for b in [*M.SITE["deck"], *M.SITE["paving"]]:
        covered.append(b)
    # outdoor ground-floor rooms with a deck finish but no deck/paving box -> teak deck at garden level
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union
    cov = unary_union([sbox(*r) for r in covered])
    for r in M.ROOMS:
        if r.outdoor and r.level == "G" and "דק" in r.floor:
            for rc in r.rects:
                rem = sbox(*rc).difference(cov)
                if rem.area > 1.0:
                    for q in G.decompose(rem):
                        out.append(B(q[0], q[1], g - 0.05, q[2], q[3], g + 0.0, "deck"))
                    ISSUES.append(f"room '{r.no}' (covered terrace {rc}) has floor '{r.floor}' but no deck/paving box "
                                  f"in geom.site_boxes(); renderer adds a deck there ({rem.area:.1f} m2).")
    return out


# =========================================================================== #
#  Furniture (positions/footprints from model.FURN, detail added here)
# =========================================================================== #
ROTV = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}     # model.Furn.rot = direction the FRONT faces
UAX = {270: (1, 0), 90: (-1, 0), 0: (0, 1), 180: (0, -1)}      # +u direction (furniture2d.Local)


def vec2rot(v):
    for k, vv in ROTV.items():
        if vv == (round(v[0]), round(v[1])):
            return k
    raise ValueError(v)


class Frame:
    """local furniture frame identical to furniture2d.Local: u along the front edge (0..W), v from the front
    (0) to the back (D); rot = direction the front faces (0=E, 90=N, 180=W, 270=S)"""

    def __init__(self, x0, y0, x1, y1, rot, z=0.0):
        self.box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        x0, y0, x1, y1 = self.box
        self.r = int(rot) % 360
        if self.r in (90, 270):
            self.W, self.D = x1 - x0, y1 - y0
        else:
            self.W, self.D = y1 - y0, x1 - x0
        self.z = z

    def pt(self, u, v):
        x0, y0, x1, y1 = self.box
        r = self.r
        if r == 270:
            return x0 + u, y0 + v
        if r == 90:
            return x1 - u, y1 - v
        if r == 0:
            return x1 - v, y0 + u
        return x0 + v, y1 - u

    def rect(self, u0, v0, u1, v1):
        a, b = self.pt(u0, v0), self.pt(u1, v1)
        return min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])

    def b(self, u0, v0, u1, v1, z0, z1, m, soft=1):
        x0, y0, x1, y1 = self.rect(u0, v0, u1, v1)
        return B(x0, y0, self.z + z0, x1, y1, self.z + z1, m, soft, cls="furn")

    def cyl(self, u, v, z0, z1, r, m, soft=1, seg=20, r1=None):
        x, y = self.pt(u, v)
        return dict(t="cyl", x=x, y=y, z0=self.z + z0, z1=self.z + z1, r=r, r1=r1 or r, mat=m, soft=soft, seg=seg)

    def dirv(self, local):
        f = ROTV[self.r]
        ua = UAX[self.r]
        return {"front": f, "back": (-f[0], -f[1]), "+u": ua, "-u": (-ua[0], -ua[1])}[local]

    def sub(self, u0, v0, u1, v1, local_front):
        x0, y0, x1, y1 = self.rect(u0, v0, u1, v1)
        return Frame(x0, y0, x1, y1, vec2rot(self.dirv(local_front)), self.z)

    def chair_at(self, u, v, facing, m_seat="fabric", m_leg="wood", w=0.48, d=0.52):
        """chair centred at local (u,v) whose front faces local direction `facing`"""
        x, y = self.pt(u, v)
        rot = vec2rot(self.dirv(facing))
        if rot in (90, 270):
            return f_chair(Frame(x - w / 2, y - d / 2, x + w / 2, y + d / 2, rot, self.z), m_seat, m_leg)
        return f_chair(Frame(x - d / 2, y - w / 2, x + d / 2, y + w / 2, rot, self.z), m_seat, m_leg)


def f_sofa(F, arms=(1, 1), back=True, pillows=True, H=0.42):
    W, D = F.W, F.D
    bd = 0.22
    aw = 0.18
    o = [F.b(0.06, 0.06, W - 0.06, D - 0.06, 0, 0.07, "furn_dark"), F.b(0, 0, W, D, 0.07, H - 0.12, "fabric", 1)]
    if back:
        o.append(F.b(0, D - bd, W, D, H - 0.12, 0.74, "fabric", 2))
    ua0 = aw if arms[0] else 0.0
    ua1 = W - aw if arms[1] else W
    if arms[0]:
        o.append(F.b(0, 0, aw, D, H - 0.12, 0.62, "fabric", 2))
    if arms[1]:
        o.append(F.b(W - aw, 0, W, D, H - 0.12, 0.62, "fabric", 2))
    inner = ua1 - ua0
    n = max(1, round(inner / 0.95))
    cw = inner / n
    for i in range(n):
        a = ua0 + i * cw
        o.append(F.b(a + 0.008, 0.015, a + cw - 0.008, D - (bd if back else 0.02), H - 0.12, H + 0.04, "fabric", 2))
        if back:
            o.append(F.b(a + 0.02, D - bd - 0.20, a + cw - 0.02, D - bd + 0.02, H + 0.02, 0.86, "fabric", 2))
    if pillows and back and inner > 1.2:
        o.append(F.b(ua0 + 0.06, D - bd - 0.36, ua0 + 0.52, D - bd - 0.18, H + 0.04, H + 0.46, "fabric_accent", 2))
        o.append(F.b(ua1 - 0.52, D - bd - 0.36, ua1 - 0.06, D - bd - 0.18, H + 0.04, H + 0.46, "fabric_olive", 2))
    return o


def f_sofa_l(F):
    main = F.sub(0, F.D - 1.0, F.W, F.D, "front")
    ret = F.sub(0, 0, 1.0, F.D - 1.0, "+u")
    o = f_sofa(main, arms=(0, 1))
    o += f_sofa(ret, arms=(0, 0) if ret.dirv("+u") != F.dirv("front") else (1, 0), pillows=False)
    # chaise end arm
    return o


def f_chair(F, m_seat="fabric", m_leg="wood"):
    W, D = F.W, F.D
    o = [F.b(0.03, 0.03, 0.06, 0.06, 0, 0.44, m_leg), F.b(W - 0.06, 0.03, W - 0.03, 0.06, 0, 0.44, m_leg),
         F.b(0.03, D - 0.06, 0.06, D - 0.03, 0, 0.44, m_leg), F.b(W - 0.06, D - 0.06, W - 0.03, D - 0.03, 0, 0.44, m_leg),
         F.b(0.0, 0.0, W, D, 0.42, 0.49, m_seat, 2), F.b(0.02, D - 0.07, W - 0.02, D, 0.49, 0.86, m_seat, 2)]
    return o


def f_table(F, seats=0, top="wood", outdoor=False):
    W, D = F.W, F.D
    o = [F.b(0, 0, W, D, 0.715, 0.75, top), F.b(0.35, 0.18, 0.43, D - 0.18, 0, 0.715, top),
         F.b(W - 0.43, 0.18, W - 0.35, D - 0.18, 0, 0.715, top),
         F.b(0.35, D / 2 - 0.03, W - 0.35, D / 2 + 0.03, 0.62, 0.715, top)]
    ms, ml = ("outdoor_fab", "frame") if outdoor else ("fabric", "wood")
    if seats:
        n = max(1, int(round((W - 0.2) / 0.68)))
        step = (W - 0.2) / n
        for i in range(n):
            cu = 0.1 + step * (i + 0.5)
            o += F.chair_at(cu, -0.30, "back", ms, ml)
            o += F.chair_at(cu, D + 0.30, "front", ms, ml)
        if seats > 2 * n:
            o += F.chair_at(-0.30, D / 2, "+u", ms, ml)
            o += F.chair_at(W + 0.30, D / 2, "-u", ms, ml)
    return o


def f_cabinets(F, h=0.88, top="marble", body="furn", door=0.6, plinth=0.10, splash=0.0, top_t=0.04):
    W, D = F.W, F.D
    o = [F.b(0.0, 0.07, W, D, 0, plinth, "furn_dark", 0), F.b(0, 0.02, W, D, plinth, h, body, 0)]
    n = max(1, round(W / door))
    dw = W / n
    for i in range(n):
        o.append(F.b(i * dw + 0.002, 0.0, (i + 1) * dw - 0.002, 0.021, plinth + 0.003, h - 0.003, body, 0))
    if top:
        o.append(F.b(-0.0, -0.02, W, D, h, h + top_t, top, 1))
        if splash:
            o.append(F.b(0, D - 0.02, W, D, h + top_t, h + top_t + splash, top, 0))
    return o


def f_tall(F, H, body="wood", door=0.55):
    W, D = F.W, F.D
    o = [F.b(0, 0.02, W, D, 0, H, body, 0)]
    n = max(1, round(W / door))
    dw = W / n
    for i in range(n):
        o.append(F.b(i * dw + 0.002, 0.0, (i + 1) * dw - 0.002, 0.021, 0.003, H - 0.003, body, 0))
    return o


def f_bed(F):
    W, D = F.W, F.D
    np_ = 2 if W < 1.7 else 3
    o = [F.b(0.12, 0.12, W - 0.12, D - 0.12, 0, 0.12, "furn_dark", 1),
         F.b(0, 0, W, D - 0.06, 0.12, 0.32, "fabric", 1),
         F.b(0.03, 0.03, W - 0.03, D - 0.1, 0.32, 0.53, "bedding", 2),
         F.b(-0.02, -0.02, W + 0.02, D - 0.62, 0.48, 0.60, "bedding", 2),
         F.b(-0.03, 0.12, W + 0.03, 0.62, 0.58, 0.635, "fabric_olive", 2),
         F.b(-0.06, D - 0.09, W + 0.06, D, 0.0, 1.18, "fabric", 2)]
    pw = (W - 0.16) / np_
    for i in range(np_):
        u0 = 0.08 + i * pw
        o.append(F.b(u0 + 0.02, D - 0.62, u0 + pw - 0.02, D - 0.22, 0.52, 0.72, "bedding", 2))
    o.append(F.b(W / 2 - 0.35, D - 0.80, W / 2 + 0.35, D - 0.62, 0.55, 0.78, "fabric_accent", 2))
    return o


def f_nightstand(F, lamp=True):
    o = [F.b(0, 0, F.W, F.D, 0.12, 0.5, "furn_dark", 1)]
    if lamp:
        o.append(F.cyl(F.W / 2, F.D / 2, 0.5, 0.82, 0.04, "marble"))
    return o


def f_coffee(F):
    W, D = F.W, F.D
    return [F.b(0.12, 0.12, W - 0.12, D - 0.12, 0, 0.30, "furn_dark", 1), F.b(0, 0, W, D, 0.30, 0.35, "marble", 1),
            F.b(0.15, 0.2, 0.55, 0.48, 0.35, 0.38, "fabric_accent", 1), F.b(0.17, 0.22, 0.50, 0.45, 0.38, 0.40, "white", 1),
            F.cyl(W - 0.35, D / 2, 0.35, 0.47, 0.11, "black_gloss", 1, r1=0.14)]


def f_island(F, stools_side="front", n_st=4):
    W, D = F.W, F.D
    o = [F.b(0, 0, 0.04, D, 0, 0.88, "marble", 0), F.b(W - 0.04, 0, W, D, 0, 0.88, "marble", 0),
         F.b(0, 0, W, D, 0.88, 0.92, "marble", 1), F.b(0.04, 0.30, W - 0.04, D - 0.03, 0.0, 0.88, "furn", 0),
         F.b(W * 0.5 - 0.4, D - 0.5, W * 0.5 + 0.4, D - 0.12, 0.905, 0.925, "steel", 0)]
    # stools on the overhang side
    for i in range(n_st):
        uc = W * (i + 0.5) / n_st
        o.append(F.cyl(uc, -0.30, 0.0, 0.02, 0.18, "steel", 1))
        o.append(F.cyl(uc, -0.30, 0.02, 0.62, 0.022, "steel", 1))
        o.append(F.cyl(uc, -0.30, 0.62, 0.68, 0.18, "fabric_dark", 1))
        o.append(F.b(uc - 0.15, -0.50, uc + 0.15, -0.46, 0.68, 0.88, "fabric_dark", 2))
    return o


def f_lounger(F, cushion="outdoor_fab", frame="white"):
    """sun lounger: head at the back of the frame"""
    W, D = F.W, F.D
    o = [F.b(0.03, 0.05, W - 0.03, D - 0.05, 0.0, 0.25, frame, 1), F.b(0.05, 0.05, W - 0.05, D - 0.65, 0.25, 0.33, cushion, 2)]
    # inclined backrest (oriented box)
    cx, cy = F.pt(W / 2, D - 0.36)
    bv = F.dirv("back")
    ang = math.radians(38)
    yaw = math.atan2(bv[1], bv[0]) - math.pi / 2
    c = Vector((cx, cy, F.z + 0.33 + 0.30 * math.sin(ang) / 1.0))
    o.append(dict(t="obox", c=tuple(c), size=(W - 0.10, 0.72, 0.08), rot=(-ang, 0, yaw), mat=cushion, soft=2))
    return o


def f_tub(F):
    W, D = F.W, F.D
    return [F.b(0, 0, W, D, 0, 0.58, "white", 2), F.b(0.08, 0.08, W - 0.08, D - 0.08, 0.40, 0.585, "water", 0)]


def f_vanity(F, double=False):
    W, D = F.W, F.D
    o = [F.b(0, 0, W, D, 0.35, 0.80, "wood", 1), F.b(-0.01, -0.01, W, D, 0.80, 0.83, "marble", 1),
         F.b(0.05, D - 0.015, W - 0.05, D, 1.0, 2.0, "mirror", 0)]
    for k in ([0.27, 0.73] if double else [0.5]):
        o.append(F.cyl(W * k, D * 0.45, 0.83, 0.96, 0.19, "white", 1, seg=24))
    return o


def f_tv(F):
    W, D = F.W, F.D
    return [F.b(0, 0, W, D, 0.15, 0.48, "furn_dark", 1),
            F.b(W / 2 - 0.85, D - 0.05, W / 2 + 0.85, D - 0.01, 1.05, 2.02, "black_gloss", 0)]


def f_fireplace(F):
    W, D = F.W, F.D
    return [F.b(0, 0.12, W, D, 0, 1.0, "rc_fair", 0), F.b(0, 0.12, 0.25, D, 0, 1.0, "rc_fair", 0),
            F.b(-0.05, 0, W + 0.05, D, 0, 0.12, "rc_fair", 1),
            F.b(0.35, 0.08, W - 0.35, D - 0.08, 0.30, 0.75, "black_gloss", 0),
            F.b(0.45, 0.07, W - 0.45, 0.12, 0.33, 0.48, "em_fire", 0),
            F.b(0.0, D - 0.08, W, D, 1.0, 3.2, "rc_fair", 0)]


def f_piano(F):
    """grand piano after the plan symbol: straight keyboard side at the back (v=D), curved tail toward v=0"""
    W, D = F.W, F.D
    poly = [(0, D), (W, D), (W, D * 0.45), (W * 0.75, D * 0.1), (W * 0.35, 0), (0, D * 0.35)]
    # smooth the tail with a few interpolated points
    pts = [F.pt(u, v) for (u, v) in poly]
    o = [dict(t="prism", pts=pts, z0=F.z + 0.68, z1=F.z + 0.98, mat="black_gloss", soft=1),
         dict(t="prism", pts=[F.pt(u, v) for (u, v) in [(0.04, D - 0.04), (W - 0.04, D - 0.04), (W - 0.04, D * 0.47),
                                                         (W * 0.74, D * 0.13), (W * 0.36, 0.04), (0.04, D * 0.36)]],
              z0=F.z + 0.98, z1=F.z + 1.0, mat="black_gloss", soft=0),
         F.b(0.06, D - 0.02, W - 0.06, D + 0.02, 0.70, 0.80, "black_gloss", 0),
         F.b(0.08, D - 0.18, W - 0.08, D - 0.02, 0.76, 0.80, "white", 0),
         F.b(0.08, D - 0.08, W - 0.08, D - 0.02, 0.80, 0.81, "black_gloss", 0),
         F.cyl(0.18, D - 0.18, 0, 0.68, 0.045, "black_gloss"), F.cyl(W - 0.18, D - 0.18, 0, 0.68, 0.045, "black_gloss"),
         F.cyl(W * 0.4, D * 0.25, 0, 0.68, 0.045, "black_gloss"),
         F.b(0.35, D + 0.30, W - 0.35, D + 0.65, 0.0, 0.48, "black_gloss", 1)]
    return o


def f_desk(F):
    W, D = F.W, F.D
    return [F.b(0, 0, W, D, 0.72, 0.75, "wood", 1), F.b(0.03, 0.03, 0.07, D - 0.03, 0, 0.72, "frame"),
            F.b(W - 0.07, 0.03, W - 0.03, D - 0.03, 0, 0.72, "frame")] + F.chair_at(W / 2, -0.35, "back")


def f_round_table(F, seats=4, outdoor=True):
    W, D = F.W, F.D
    cx, cy = W / 2, D / 2
    r = min(W, D) / 2
    o = [F.cyl(cx, cy, 0.71, 0.75, r, "white", 1, seg=36), F.cyl(cx, cy, 0.0, 0.71, 0.05, "frame", 1),
         F.cyl(cx, cy, 0.0, 0.03, 0.3, "frame", 1)]
    for (du, dv, fr) in [(-1, -1, "back"), (1, 1, "front"), (-1, 1, "+u"), (1, -1, "-u")][:seats]:
        k = (r + 0.3) / math.sqrt(2)
        o += F.chair_at(cx + du * k, cy + dv * k, fr, "outdoor_fab", "frame")
    return o


ROOM_SKIP = ("wc", "basin", "shower", "mat", "gym")


def room_of(level, x, y):
    for r in M.ROOMS:
        if r.level != level:
            continue
        for (a, b, c, d) in r.rects:
            if a <= x <= c and b <= y <= d:
                return r, (a, b, c, d)
    return None, None


def furniture_elems():
    out = []
    P = M.SITE["pool"]
    for f in M.FURN:
        if f.kind in ROOM_SKIP:
            continue
        z = M.LV.get(f.level, 0.0)
        cx, cy = f.x + f.w / 2, f.y + f.d / 2
        if f.level == "G" and P["x0"] < cx < P["x1"] and P["y0"] < cy < P["y1"]:
            ISSUES.append(f"model.FURN {f.kind} at ({f.x},{f.y}) level {f.level} lies inside the pool "
                          f"({P['x0']}-{P['x1']} x {P['y0']}-{P['y1']}); not rendered.")
            continue
        F = Frame(f.x, f.y, f.x + f.w, f.y + f.d, f.rot, z)
        rm = room_of(f.level, cx, cy)[0]
        outdoor = bool(rm and rm.outdoor)
        k = f.kind
        if k == "sofa":
            out += f_sofa(F)
        elif k == "sofa_l":
            out += f_sofa_l(F)
        elif k == "armchair":
            out += f_sofa(F, pillows=False)
        elif k == "coffee":
            out += f_coffee(F)
        elif k == "rug":
            out.append(F.b(0, 0, F.W, F.D, 0.0, 0.012, "rug", 0))
        elif k == "table_rect":
            seats = int(f.label) if f.label.isdigit() else 6
            out += f_table(F, seats, outdoor=outdoor)
        elif k == "table_round":
            out += f_round_table(F)
        elif k in ("bed_k", "bed_q", "bed_s"):
            out += f_bed(F)
        elif k == "nightstand":
            out += f_nightstand(F)
        elif k == "island":
            out += f_island(F)
        elif k == "island_s":
            out += f_cabinets(F, 0.9, "marble", "wood", 0.45)
        elif k == "counter":
            out += f_cabinets(F, splash=0.55 if f.level == "G" and rm is not None and rm.no == "G3" else 0.0)
        elif k == "counter_l":
            a_ = F.sub(0, F.D - 0.62, F.W, F.D, "front")
            b_ = F.sub(F.W - 0.62, 0, F.W, F.D - 0.62, "-u")
            out += f_cabinets(a_) + f_cabinets(b_)
        elif k == "fridge":
            out += f_tall(F, 2.4, "furn", 0.45)
        elif k == "closet":
            body = "furn" if (rm is not None and rm.no == "G3") else "wood"
            out += f_tall(F, 2.4 if body == "furn" else FURN_H("closet"), body)
        elif k == "lounger":
            out += f_lounger(F)
        elif k == "tub":
            out += f_tub(F)
        elif k in ("vanity", "vanity2"):
            out += f_vanity(F, k == "vanity2")
        elif k == "tvunit":
            out += f_tv(F)
        elif k == "fireplace":
            out += f_fireplace(F)
        elif k == "piano":
            out += f_piano(F)
        elif k == "desk":
            out += f_desk(F)
        elif k == "pool_table":
            out += [F.b(0.1, 0.1, F.W - 0.1, F.D - 0.1, 0, 0.68, "furn_dark", 1), F.b(0, 0, F.W, F.D, 0.68, 0.8, "furn_dark", 1),
                    F.b(0.1, 0.1, F.W - 0.1, F.D - 0.1, 0.8, 0.805, "felt", 0)]
        elif k == "recliner_row":
            n = max(2, int(F.W / 0.9))
            for i in range(n):
                out += f_sofa(F.sub(i * F.W / n, 0, (i + 1) * F.W / n, F.D, "front"), pillows=False)
        elif k == "sauna":
            out.append(F.b(0, 0, F.W, F.D, 0, 2.1, "sauna", 1))
        elif k == "bar":
            out += f_cabinets(F, 1.02, "marble", "furn_dark", 0.6)
        elif k == "bench":
            out.append(F.b(0, 0, F.W, F.D, 0.0, 0.45, "wood", 1))
        else:
            h = G.FURN_H.get(k, 0.5)
            out.append(F.b(0, 0, F.W, F.D, 0, h, G.FURN_MAT.get(k, "furn"), 1))
    # pool loungers (model.SITE) - head away from the pool (front faces the pool)
    for (x, y) in M.SITE["loungers"]:
        rot = 270 if y > P["y1"] else 90
        out += f_lounger(Frame(x, y, x + 0.7, y + 1.9, rot, M.GARDEN))
    return out


def FURN_H(k):
    return G.FURN_H.get(k, 0.5)


def car_elems():
    """simple but car-like models inside model.CARS footprints (nose toward the house / west)"""
    out = []
    prof = [(0.0, 0.32), (0.0, 0.78), (0.22, 0.96), (1.05, 1.02), (1.45, 1.44), (2.95, 1.46), (3.55, 1.04),
            (4.40, 0.92), (4.62, 0.72), (4.60, 0.32)]
    win = [(1.12, 1.03), (1.50, 1.40), (2.92, 1.42), (3.45, 1.05)]
    for i, (x0, y0, x1, y1) in enumerate(M.CARS):
        z = M.STREET
        Lc, Wc = 4.62, 1.86
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        xr = cx + Lc / 2          # rear at east (street side), nose west
        paint = "car" if i == 0 else "car_white"
        P = [(xr - a, z + b) for (a, b) in prof]
        out.append(dict(t="prism", pts=P, z0=cy - Wc / 2, z1=cy + Wc / 2, axis="y", mat=paint, soft=1))
        Wn = [(xr - a, z + b) for (a, b) in win]
        out.append(dict(t="prism", pts=Wn, z0=cy - Wc / 2 - 0.01, z1=cy + Wc / 2 + 0.01, axis="y", mat="car_glass", soft=0))
        out.append(dict(t="prism", pts=[(xr - 3.50, z + 1.05), (xr - 2.98, z + 1.43), (xr - 1.50, z + 1.43), (xr - 1.08, z + 1.05)],
                        z0=cy - Wc / 2 + 0.12, z1=cy + Wc / 2 - 0.12, axis="y", mat="car_glass", soft=0))
        for (wx, wy) in [(xr - 0.95, cy - Wc / 2 + 0.12), (xr - 3.75, cy - Wc / 2 + 0.12),
                         (xr - 0.95, cy + Wc / 2 - 0.12), (xr - 3.75, cy + Wc / 2 - 0.12)]:
            out.append(dict(t="cyl", axis="y", x=wx, y=z + 0.34, zc=wy, z0=-0.13, z1=0.13, r=0.34, seg=24, mat="tire", soft=1))
            out.append(dict(t="cyl", axis="y", x=wx, y=z + 0.34, zc=wy, z0=-0.135, z1=0.135, r=0.21, seg=20, mat="steel", soft=0))
        # lights
        out.append(B(xr - 4.62, cy - 0.85, z + 0.68, xr - 4.58, cy - 0.55, z + 0.76, "white", 0, cls="car"))
        out.append(B(xr - 4.62, cy + 0.55, z + 0.68, xr - 4.58, cy + 0.85, z + 0.76, "white", 0, cls="car"))
        out.append(B(xr - 0.02, cy - 0.9, z + 0.74, xr + 0.005, cy + 0.9, z + 0.80, "tail", 0, cls="car"))
    return out


# =========================================================================== #
#  Vegetation
# =========================================================================== #
def _blob(bm, center, r, rng, sub=2, sq=1.0, amp=0.18):
    res = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    off = Vector((rng.random() * 100, rng.random() * 100, rng.random() * 100))
    for v in res["verts"]:
        d = v.co.normalized()
        n = mnoise.fractal(d * 2.6 + off, 0.6, 2.0, 3)
        v.co = Vector((d.x * r, d.y * r, d.z * r * sq)) * (1 + amp * n) + Vector(center)
    return res["verts"]


def _tube(bm, pts, radii, sides=8):
    rings = []
    prev_a = None
    for i, p in enumerate(pts):
        p = Vector(p)
        d = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        if prev_a is None:
            a = d.orthogonal().normalized()
        else:
            a = (prev_a - d * prev_a.dot(d)).normalized()
        prev_a = a
        b = d.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / sides) + b * math.sin(2 * math.pi * k / sides)) * radii[i])
                      for k in range(sides)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
    bm.faces.new(rings[-1])


def tree_olive(x, y, r, rng, name, z0):
    bm = bmesh.new()
    h0 = 1.0 + rng.random() * 0.3
    lean = Vector((rng.uniform(-.25, .25), rng.uniform(-.25, .25), 0))
    trunk = [(0, 0, -0.1), (lean.x * .3, lean.y * .3, 0.4), (lean.x * .6 + .05, lean.y * .6, 0.8), (lean.x, lean.y, h0)]
    _tube(bm, trunk, [0.22 * r / 2.4 + .06, 0.18, 0.16, 0.14], 9)
    nb = 3
    for i in range(nb):
        a = 2 * math.pi * i / nb + rng.random()
        rr = r * 0.45
        pts = [(lean.x, lean.y, h0 - 0.1), (lean.x + math.cos(a) * rr * .4, lean.y + math.sin(a) * rr * .4, h0 + 0.5),
               (lean.x + math.cos(a) * rr * .8, lean.y + math.sin(a) * rr * .8, h0 + 1.1 + rng.random() * .3)]
        _tube(bm, pts, [0.10, 0.075, 0.05], 7)
    trunk_bm = bm
    leaves = bmesh.new()
    zc = h0 + 1.15 + r * 0.25
    # several sub-crowns (olive canopies are clumpy and airy), each made of many small leaf clusters
    subs = []
    for k in range(5 + int(r)):
        a = rng.random() * 2 * math.pi
        rad = r * 0.55 * rng.random() ** 0.5
        subs.append((math.cos(a) * rad + lean.x, math.sin(a) * rad + lean.y, zc + rng.uniform(-0.25, 0.45) * r * 0.5,
                     r * rng.uniform(0.38, 0.55)))
    for (sx, sy, sz, sr) in subs:
        for i in range(int(22 + sr * 22)):
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 0.6))).normalized() * sr * rng.random() ** 0.3
            _blob(leaves, (sx + d.x, sy + d.y, sz + d.z), r * rng.uniform(0.06, 0.10), rng, 2, 0.8, 0.4)
    o1 = bm_object(name + "_trunk", trunk_bm, "bark", "veg", (x, y, z0), True)
    o2 = bm_object(name + "_leaves", leaves, "olive_leaf", "veg", (x, y, z0), True)
    return [o1, o2]


def tree_carob(x, y, r, rng, name, z0):
    bm = bmesh.new()
    _tube(bm, [(0, 0, -0.1), (0.05, 0.02, 0.8), (0.1, -0.05, 1.5)], [0.28, 0.24, 0.2], 10)
    for i in range(4):
        a = 2 * math.pi * i / 4 + rng.random()
        _tube(bm, [(0.1, -0.05, 1.4), (math.cos(a) * r * .35, math.sin(a) * r * .35, 2.2)], [0.13, 0.08], 7)
    leaves = bmesh.new()
    zc = 2.3 + r * 0.45
    n = int(50 + r * 26)
    for i in range(n):
        a = rng.random() * 2 * math.pi
        rad = r * 0.85 * rng.random() ** 0.4
        dz = (1 - min(1, rad / r) ** 2) ** .5 * r * 0.5
        c = (math.cos(a) * rad, math.sin(a) * rad, zc + rng.uniform(-0.5, 1.0) * dz)
        _blob(leaves, c, r * rng.uniform(0.17, 0.26), rng, 2, 0.85, 0.3)
    return [bm_object(name + "_trunk", bm, "bark", "veg", (x, y, z0)),
            bm_object(name + "_leaves", leaves, "carob_leaf", "veg", (x, y, z0))]


def tree_palm(x, y, r, rng, name, z0):
    bm = bmesh.new()
    H = 5.6 + r * 1.6 + rng.uniform(-0.6, 0.8)
    bend = Vector((rng.uniform(-.4, .4), rng.uniform(-.4, .4), 0))
    pts = [(bend.x * (t / 10) ** 2, bend.y * (t / 10) ** 2, -0.1 + H * t / 10) for t in range(11)]
    _tube(bm, pts, [0.30 - 0.06 * t / 10 for t in range(11)], 12)
    top = Vector(pts[-1])
    # crown base (old frond bases)
    _blob(bm, top + Vector((0, 0, 0.15)), 0.42, rng, 2, 1.0, 0.25)
    fr = bmesh.new()
    nf = 22
    for k in range(nf):
        az = k * 2.39996 + rng.uniform(-.1, .1)
        layer = k / nf
        el = math.radians(62 - 100 * layer + rng.uniform(-8, 8))
        Lf = r * 1.75 + rng.uniform(-0.2, 0.3)
        droop = 0.25 + 0.55 * layer
        hd = Vector((math.cos(az), math.sin(az), 0))
        side = Vector((-math.sin(az), math.cos(az), 0))
        spine = []
        ns = 22
        for i in range(ns + 1):
            t = i / ns
            p = top + Vector((0, 0, 0.35)) + hd * (Lf * t * math.cos(el)) + Vector((0, 0, Lf * t * math.sin(el) - droop * Lf * t * t))
            spine.append(p)
        for i in range(2, ns):
            t = i / ns
            p = spine[i]
            tang = (spine[i + 1] - spine[i - 1]).normalized()
            up = tang.cross(side).normalized()
            if up.z < 0:
                up = -up
            ll = 0.62 * Lf / 3.0 * math.sin(math.pi * min(1, t * 1.15)) ** 0.6 + 0.05
            for s in (-1, 1):
                d = (side * s * 0.85 + up * 0.38 + tang * 0.45).normalized()
                w = 0.035
                a1 = p - tang * w
                a2 = p + tang * w
                tip = p + d * ll
                v = [fr.verts.new(a1), fr.verts.new(a2), fr.verts.new(tip + tang * 0.01), fr.verts.new(tip - tang * 0.01)]
                fr.faces.new(v)
        # rachis ribbon
        prev = None
        for i in range(ns + 1):
            wv = side * (0.03 * (1 - i / ns) + 0.006)
            pr = (fr.verts.new(spine[i] - wv), fr.verts.new(spine[i] + wv))
            if prev:
                fr.faces.new((prev[0], prev[1], pr[1], pr[0]))
            prev = pr
    return [bm_object(name + "_trunk", bm, "palm_trunk", "veg", (x, y, z0)),
            bm_object(name + "_fronds", fr, "palm_leaf", "veg", (x, y, z0), smooth=False)]


def tree_pine(x, y, r, rng, name, z0, h=None):
    """umbrella stone-pine / generic context tree (golf course, neighbours)"""
    bm = bmesh.new()
    H = h or (4.5 + rng.random() * 3)
    _tube(bm, [(0, 0, -0.1), (rng.uniform(-.3, .3), rng.uniform(-.3, .3), H)], [0.22, 0.14], 7)
    leaves = bmesh.new()
    n = int(8 + r * 3)
    for i in range(n):
        a = rng.random() * 2 * math.pi
        rad = r * 0.7 * math.sqrt(rng.random())
        _blob(leaves, (math.cos(a) * rad, math.sin(a) * rad, H + rng.uniform(-.2, .7)), r * rng.uniform(.35, .5), rng, 2, 0.55, 0.25)
    return [bm_object(name + "_trunk", bm, "bark", "context", (x, y, z0)),
            bm_object(name + "_leaves", leaves, "pine_leaf", "context", (x, y, z0))]


def hedge(x0, y0, x1, y1, h, rng, name, z0):
    bm = bmesh.new()
    L = max(x1 - x0, y1 - y0)
    horiz = (x1 - x0) >= (y1 - y0)
    n = max(1, int(L / 1.6))
    seg = L / n
    t = min(x1 - x0, y1 - y0)
    for i in range(n):
        c0 = (x0 if horiz else y0) + i * seg - 0.15
        c1 = c0 + seg + 0.3
        if horiz:
            bx = (c0, y0, c1, y1)
        else:
            bx = (x0, c0, x1, c1)
        res = bmesh.ops.create_cube(bm, size=1.0)
        vs = res["verts"]
        sx, sy = bx[2] - bx[0], bx[3] - bx[1]
        hh = h * rng.uniform(0.94, 1.05)
        for v in vs:
            v.co = Vector(((v.co.x + .5) * sx + bx[0], (v.co.y + .5) * sy + bx[1], (v.co.z + .5) * hh + z0))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=5, use_grid_fill=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)
    for v in bm.verts:
        n_ = mnoise.fractal(v.co * 1.6, 0.6, 2.0, 3)
        v.co += Vector((n_ * 0.07, mnoise.noise(v.co * 1.3 + Vector((5, 5, 5))) * 0.07, n_ * 0.05))
    del t
    return bm_object(name, bm, "hedge_leaf", "veg", (0, 0, 0))


def plant_meshes():
    """base meshes for instanced bed planting (lavender, ornamental grass, low shrub)"""
    rng = random.Random(7)
    meshes = {}
    # lavender
    bm = bmesh.new()
    _blob(bm, (0, 0, 0.12), 0.24, rng, 2, 0.75, 0.25)
    nb = len(bm.faces)
    for i in range(34):
        a = rng.random() * 2 * math.pi
        rad = 0.22 * math.sqrt(rng.random())
        hz = 0.30 + rng.random() * 0.16
        res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.028)
        for v in res["verts"]:
            v.co = Vector((v.co.x + math.cos(a) * rad, v.co.y + math.sin(a) * rad, v.co.z * 3.2 + hz))
    me = bpy.data.meshes.new("pl_lavender")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat("lav_leaf"))
    me.materials.append(mat("lavender"))
    for i, p in enumerate(me.polygons):
        p.material_index = 0 if i < nb else 1
        p.use_smooth = True
    meshes["lavender"] = me
    # ornamental grass (Pennisetum)
    bm = bmesh.new()
    for i in range(46):
        a = rng.random() * 2 * math.pi
        hgt = rng.uniform(0.45, 0.75)
        out = rng.uniform(0.15, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        s = Vector((-d.y, d.x, 0))
        prev = None
        for k in range(5):
            t = k / 4
            p = d * (0.03 + out * t * t) + Vector((0, 0, hgt * math.sin(t * 1.35)))
            w = 0.012 * (1 - t) + 0.002
            pr = (bm.verts.new(p - s * w), bm.verts.new(p + s * w))
            if prev:
                bm.faces.new((prev[0], prev[1], pr[1], pr[0]))
            prev = pr
    me = bpy.data.meshes.new("pl_grass")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat("grass_orn"))
    meshes["grass"] = me
    # low shrub (rosemary / pittosporum ball)
    bm = bmesh.new()
    _blob(bm, (0, 0, 0.22), 0.34, rng, 3, 0.75, 0.3)
    me = bpy.data.meshes.new("pl_shrub")
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.materials.append(mat("shrub_leaf"))
    meshes["shrub"] = me
    return meshes


def tree_base(x, y):
    """garden level, or the sunken patio floor when a model tree stands inside the patio void"""
    P = M.PATIO
    if P[0] < x < P[2] and P[1] < y < P[3]:
        msg = (f"tree at ({x},{y}) lies inside the sunken patio void {P}; rendered planted on the patio floor "
               f"(z={M.LV['B']:+.2f}).")
        if msg not in ISSUES:
            ISSUES.append(msg)
        return M.LV["B"] - 0.02
    return M.GARDEN


def build_vegetation(dense=True):
    g = M.GARDEN
    trees = G.trees()
    for i, (x, y, r, kind) in enumerate(trees):
        rng = random.Random(i * 31 + 5)
        nm = f"tree{i:02d}_{kind}"
        zt = tree_base(x, y)
        if kind.startswith("olive"):
            tree_olive(x, y, r, rng, nm, zt)
        elif kind == "carob":
            tree_carob(x, y, r, rng, nm, zt)
        elif kind == "palm":
            tree_palm(x, y, r, rng, nm, zt)
        else:
            tree_olive(x, y, r, rng, nm, zt)
    # hedges inside the north and south boundary walls (screen the neighbours)
    L = M.LOT
    rng = random.Random(3)
    hedge(L["x0"] + 0.6, L["y1"] - 0.95, L["x1"] - 0.3, L["y1"] - 0.25, 1.9, rng, "hedge_north", g)
    hedge(L["x0"] + 0.6, L["y0"] + 0.25, L["x1"] - 0.3, L["y0"] + 0.95, 1.9, rng, "hedge_south", g)
    hedge(L["x1"] - 0.95, L["y1"] - 5.0, L["x1"] - 0.3, L["y1"] - 0.95, 1.6, rng, "hedge_ne", g)
    if not dense:
        return
    # instanced bed planting in drifts
    meshes = plant_meshes()
    c = coll("veg_instances")
    rng = random.Random(11)
    tr = [(x, y, r) for (x, y, r, _) in trees]
    raft = [s for s in M.SLABS if s.kind == "raft"][0].rects[0]
    wf = M.SITE.get("water_feature")
    k = 0
    for (x0, y0, x1, y1) in M.SITE["planting"]:
        step = 0.55
        nx, ny = max(1, int((x1 - x0) / step)), max(1, int((y1 - y0) / step))
        for i in range(nx):
            for j in range(ny):
                x = x0 + (i + 0.5) * (x1 - x0) / nx + rng.uniform(-.16, .16)
                y = y0 + (j + 0.5) * (y1 - y0) / ny + rng.uniform(-.16, .16)
                if any((x - tx) ** 2 + (y - ty) ** 2 < 0.55 ** 2 for tx, ty, _ in tr):
                    continue
                if raft[0] - 0.2 < x < raft[2] + 0.2 and raft[1] - 0.2 < y < raft[3] + 0.2:
                    continue
                if wf and wf[0] < x < wf[2] and wf[1] < y < wf[3]:
                    continue
                if y > L["y1"] - 1.0 or y < 1.0:   # hedge zone
                    if y > L["y1"] - 1.0:
                        continue
                n = mnoise.noise(Vector((x * 0.28, y * 0.28, 1.7)))
                kind = "lavender" if n > 0.12 else ("grass" if n > -0.2 else "shrub")
                if (x1 - x0) < 0.5 or (y1 - y0) < 0.5:
                    kind = "grass"
                ob = bpy.data.objects.new(f"pl_{k}", meshes[kind])
                s = rng.uniform(0.8, 1.2)
                ob.scale = (s, s, s * rng.uniform(0.85, 1.15))
                ob.rotation_euler = (0, 0, rng.random() * 6.28)
                ob.location = (x, y, g - 0.13)
                c.objects.link(ob)
                k += 1
    print(f"  planting instances: {k}")


# =========================================================================== #
#  Neighbourhood context
# =========================================================================== #
def villa(x0, y0, x1, y1, rng, glow_side):
    """simple low white neighbouring villa: base + offset upper volume + glazing bands"""
    z = M.GARDEN
    o = []
    h1, h2 = 3.5, 3.3
    pm = rng.choice(["plaster", "plaster", "n_beige"])
    o.append(B(x0, y0, z, x1, y1, z + h1, pm, 0))
    ux0 = x0 + rng.uniform(0, 3)
    uy0 = y0 + rng.uniform(0, 3)
    ux1 = x1 - rng.uniform(0, 4)
    uy1 = y1 - rng.uniform(0, 4)
    o.append(B(ux0, uy0, z + h1, ux1, uy1, z + h1 + h2, "plaster", 0))
    o.append(B(x0, y0, z + h1, x1, y1, z + h1 + 0.4, pm, 0))  # parapet band
    for (a0, a1, c, horiz, zz, hh) in [(x0, x1, y0, True, z, h1), (x0, x1, y1, True, z, h1), (y0, y1, x0, False, z, h1),
                                       (y0, y1, x1, False, z, h1), (ux0, ux1, uy0, True, z + h1, h2),
                                       (ux0, ux1, uy1, True, z + h1, h2), (uy0, uy1, ux0, False, z + h1, h2),
                                       (uy0, uy1, ux1, False, z + h1, h2)]:
        L = a1 - a0
        n = max(1, int(L / 5))
        for i in range(n):
            if rng.random() < 0.35:
                continue
            w = rng.uniform(1.6, min(4.0, L / n - 0.6))
            a = a0 + (i + 0.5) * L / n - w / 2
            m = "n_glow" if (rng.random() < 0.45 and glow_side) else "n_glass"
            s0, s1 = zz + (0.0 if zz < 1 else 0.3), zz + hh - 0.5
            if horiz:
                o.append(B(a, c - 0.03, s0, a + w, c + 0.03, s1, m, 0))
            else:
                o.append(B(c - 0.03, a, s0, c + 0.03, a + w, s1, m, 0))
    return o


def build_context():
    rng = random.Random(42)
    el = []
    L = M.LOT
    # neighbouring lots: north, south, across the street (east), and their diagonals
    lots = [(0, 36, 30, 72), (0, -36, 30, 0), (0, 72, 30, 108), (0, -72, 30, -36),
            (42.5, 0, 72.5, 36), (42.5, 36, 72.5, 72), (42.5, -36, 72.5, 0), (42.5, 72, 72.5, 108), (42.5, -72, 72.5, -36)]
    for (a, b, c, d) in lots:
        east = a > 40
        bx0 = a + (6 if not east else 5) + rng.uniform(0, 2)
        bx1 = c - (5 if not east else 6) - rng.uniform(0, 2)
        by0 = b + 6 + rng.uniform(0, 3)
        by1 = d - 6 - rng.uniform(0, 4)
        el += villa(bx0, by0, bx1, by1, rng, True)
        # their boundary walls on the street side
        if east:
            el.append(B(a, b + 0.5, M.STREET + 0.05, a + 0.2, d - 0.5, M.STREET + 1.5, "plaster", 0))
        for _ in range(9):
            tx, ty = rng.uniform(a + 2, c - 2), rng.uniform(b + 2, d - 2)
            if bx0 - 1.5 < tx < bx1 + 1.5 and by0 - 1.5 < ty < by1 + 1.5:
                continue
            kind = rng.choice(["pine", "olive", "palm", "carob"])
            nm = f"ntree_{len(el)}_{_}"
            if kind == "olive":
                tree_olive(tx, ty, rng.uniform(1.6, 2.4), rng, nm, M.GARDEN)
            elif kind == "palm":
                tree_palm(tx, ty, rng.uniform(1.3, 1.6), rng, nm, M.GARDEN)
            elif kind == "carob":
                tree_carob(tx, ty, rng.uniform(1.8, 2.6), rng, nm, M.GARDEN)
            else:
                tree_pine(tx, ty, rng.uniform(1.8, 2.8), rng, nm, M.GARDEN, h=rng.uniform(3.5, 6.0))
        if abs(b) < 1 or abs(d) < 1 or east:   # hedge screening the lots next to ours / along the street
            if east:
                hedge(a + 0.4, b + 1.0, a + 1.1, d - 1.0, 1.8, rng, f"nhedge_{len(el)}", M.GARDEN)
            elif d > 36 - 1e-6 and b > 1:
                hedge(a + 0.6, b + 0.4, c - 0.6, b + 1.1, 1.8, rng, f"nhedge_{len(el)}", M.GARDEN)
            elif abs(d) < 1:
                hedge(a + 0.6, d - 1.1, c - 0.6, d - 0.4, 1.8, rng, f"nhedge_{len(el)}", M.GARDEN)
        # fences between lots (simple white walls)
        if not east:
            el.append(B(a, d - 0.1 if d > 36 else b, M.GARDEN - 0.05, c, (d if d > 36 else b + 0.1), M.GARDEN + 1.5, "plaster", 0)) \
                if abs(d - 36) > 1 and abs(b) > 1 else None
    el = [e for e in el if e]
    add_elems(el, "context", "ctx_")
    # golf course trees (west)
    for i in range(26):
        x = -rng.uniform(8, 140)
        y = rng.uniform(-90, 130)
        tree_pine(x, y, rng.uniform(2.0, 3.6), rng, f"golf_tree{i}", M.GARDEN - 0.05, h=rng.uniform(4, 8))
    # distant tree line / horizon silhouettes
    for i in range(70):
        a = rng.uniform(math.radians(100), math.radians(330))
        d = rng.uniform(220, 420)
        x, y = L["x1"] / 2 + d * math.cos(a), L["y1"] / 2 + d * math.sin(a)
        tree_pine(x, y, rng.uniform(4, 8), rng, f"far_tree{i}", M.GARDEN - 0.05, h=rng.uniform(5, 10))
    # far low villas silhouettes north / south / east
    far = []
    for i in range(40):
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(130, 320)
        x, y = L["x1"] / 2 + d * math.cos(a), L["y1"] / 2 + d * math.sin(a)
        if x < -10:
            continue
        w, dd = rng.uniform(12, 20), rng.uniform(10, 16)
        far += villa(x, y, x + w, y + dd, rng, True)
    add_elems(far, "context", "far_")


# =========================================================================== #
#  Lights
# =========================================================================== #
LIGHTS = []   # (object, group, base energy)


def add_light(kind, loc, energy, color, group, size=0.1, size_y=None, rot=(0, 0, 0), spot=None, shape="RECTANGLE",
              direction=None, name="L", portal=False):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color[:3]
    if kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    if kind == "AREA":
        ld.shape = shape
        ld.size = size
        if size_y is not None:
            ld.size_y = size_y
        if portal:
            ld.cycles.is_portal = True
    if kind == "SPOT" and spot:
        ld.spot_size = math.radians(spot[0])
        ld.spot_blend = spot[1]
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    if direction is not None:
        ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    else:
        ob.rotation_euler = rot
    ob.visible_camera = False
    coll("lights").objects.link(ob)
    LIGHTS.append((ob, group, energy))
    return ob


def next_level(lv):
    return {"B": "G", "G": "U", "U": "R"}.get(lv)


def build_lights():
    em = []
    # ---------------- interior rooms: area fill + downlight grid
    for r in M.ROOMS:
        if r.outdoor or r.level not in ("B", "G", "U"):
            continue
        nl = next_level(r.level)
        zc = M.slab_bot(nl) - 0.005
        for (x0, y0, x1, y1) in r.rects:
            w, d = x1 - x0, y1 - y0
            if w < 0.8 or d < 0.8:
                continue
            area = w * d
            add_light("AREA", ((x0 + x1) / 2, (y0 + y1) / 2, zc - 0.02), 3.5 * area, WARM2, "interior",
                      size=max(0.3, w - 0.8), size_y=max(0.3, d - 0.8), name=f"fill_{r.no}")
            # downlights
            sp = 1.9
            nx, ny = max(1, round((w - 0.6) / sp)), max(1, round((d - 0.6) / sp))
            for i in range(nx):
                for j in range(ny):
                    x = x0 + 0.3 + (i + 0.5) * (w - 0.6) / nx
                    y = y0 + 0.3 + (j + 0.5) * (d - 0.6) / ny
                    add_light("SPOT", (x, y, zc - 0.03), 14.0, WARM2, "downlight", size=0.03, spot=(110, 0.9),
                              name=f"dl_{r.no}")
                    em.append(dict(t="cyl", x=x, y=y, z0=zc - 0.012, z1=zc + 0.001, r=0.045, mat="em_down", soft=3, seg=14))
                    em.append(dict(t="cyl", x=x, y=y, z0=zc - 0.006, z1=zc + 0.0005, r=0.06, mat="frame", soft=3, seg=14))
    # ---------------- exterior soffit downlights: covered terrace (cantilever), loggia, canopy, BBQ pergola
    zsoff = M.slab_bot("U") - 0.005
    for x in (7.3, 9.5, 11.7):
        for y in (17.0, 18.9, 20.4):
            add_light("SPOT", (x, y, zsoff - 0.03), 45.0, WARM2, "soffit", size=0.03, spot=(80, 0.7), name="soffit")
            em.append(dict(t="cyl", x=x, y=y, z0=zsoff - 0.012, z1=zsoff + 0.001, r=0.045, mat="em_soffit", soft=3, seg=14))
    zl = M.slab_bot("R") - 0.005
    for x in (7.6, 9.5, 11.4):
        add_light("SPOT", (x, 16.9, zl - 0.03), 35.0, WARM2, "soffit", size=0.03, spot=(85, 0.7), name="loggia")
        em.append(dict(t="cyl", x=x, y=16.9, z0=zl - 0.012, z1=zl + 0.001, r=0.045, mat="em_soffit", soft=3, seg=14))
    can = [s for s in M.SLABS if s.kind == "canopy"]
    for s in can:
        for (x0, y0, x1, y1) in s.rects:
            zc = s.top - s.t - 0.005
            for y in (y0 + 0.8, (y0 + y1) / 2, y1 - 0.8):
                xx = (x0 + x1) / 2 + 0.3
                add_light("SPOT", (xx, y, zc - 0.03), 40.0, WARM2, "soffit", size=0.03, spot=(75, 0.7), name="canopy")
                em.append(dict(t="cyl", x=xx, y=y, z0=zc - 0.012, z1=zc + 0.001, r=0.045, mat="em_soffit", soft=3, seg=14))
    for p in M.PERGOLAS:
        zz = p["z"] - 0.02
        add_light("AREA", ((p["x0"] + p["x1"]) / 2, (p["y0"] + p["y1"]) / 2, zz), 22.0, WARM2, "soffit",
                  size=(p["x1"] - p["x0"]) * 0.6, size_y=(p["y1"] - p["y0"]) * 0.6, name="pergola")
    # ---------------- pool: underwater lights + cove strip
    P = M.SITE["pool"]
    wz = P["water"]
    for x in [P["x0"] + 1.2 + i * (P["x1"] - P["x0"] - 2.4) / 4 for i in range(5)]:
        for (y, dy) in ((P["y0"] + 0.12, 1), (P["y1"] - 0.12, -1)):
            add_light("SPOT", (x, y, wz - 0.45), 55.0, POOLC, "pool", size=0.06, spot=(130, 1.0),
                      direction=(0, dy, -0.25), name="pool")
            em.append(B(x - 0.09, y - 0.115 * dy - 0.01, wz - 0.53, x + 0.09, y - 0.115 * dy + 0.01, wz - 0.37, "em_pool", 3)
                      if False else B(x - 0.09, min(y - 0.125 * dy, y - 0.105 * dy), wz - 0.53, x + 0.09,
                                      max(y - 0.125 * dy, y - 0.105 * dy), wz - 0.37, "em_pool", 3))
    # linear cove under the coping (long sides)
    for (y0, y1) in ((P["y0"], P["y0"] + 0.02), (P["y1"] - 0.02, P["y1"])):
        em.append(B(P["x0"] + 0.1, y0, wz - 0.16, P["x1"] - 0.1, y1, wz - 0.12, "em_pool", 3))
    # ---------------- garden uplights at trees
    for (x, y, r, kind) in G.trees():
        n = 2 if r > 2 else 1
        for k in range(n):
            a = k * math.pi + 0.6
            px, py = x + math.cos(a) * 0.6, y + math.sin(a) * 0.6
            zb = tree_base(x, y)
            add_light("SPOT", (px, py, zb + 0.05), 180.0 if kind != "palm" else 260.0, WARM2, "garden",
                      size=0.04, spot=(45 if kind == "palm" else 70, 0.6),
                      direction=(x - px, y - py, 6.0), name="uplight")
            em.append(dict(t="cyl", x=px, y=py, z0=zb - 0.01, z1=zb + 0.03, r=0.06, mat="frame", soft=3))
            em.append(dict(t="cyl", x=px, y=py, z0=zb + 0.03, z1=zb + 0.035, r=0.045, mat="em_garden", soft=3))
    # ---------------- step / marker lights: patio retaining walls, deck edge, entrance path
    PAT = M.PATIO
    for x in [PAT[0] + 1.0 + i * (PAT[2] - PAT[0] - 2.0) / 3 for i in range(4)]:
        y = PAT[1] + 0.005
        em.append(B(x - 0.12, y - 0.01, M.LV["B"] + 0.35, x + 0.12, y + 0.004, M.LV["B"] + 0.42, "em_garden", 3))
        add_light("AREA", (x, y + 0.05, M.LV["B"] + 0.38), 6.0, WARM2, "garden", size=0.3, size_y=0.08,
                  direction=(0, 1, -0.6), name="step")
    for y in (29.0, 30.6):
        for x in (26.0, 27.5, 29.0):
            em.append(dict(t="cyl", x=x, y=y, z0=M.GARDEN, z1=M.GARDEN + 0.45, r=0.05, mat="frame", soft=3))
            em.append(dict(t="cyl", x=x, y=y, z0=M.GARDEN + 0.38, z1=M.GARDEN + 0.43, r=0.052, mat="em_garden", soft=3))
            add_light("POINT", (x, y, M.GARDEN + 0.40), 8.0, WARM2, "garden", size=0.03, name="bollard")
    # deck-edge step lights along the pool deck north edge
    for x in (14.0, 16.5, 19.0, 21.5, 23.8):
        em.append(B(x - 0.15, 16.69, M.GARDEN - 0.05, x + 0.15, 16.70, M.GARDEN - 0.01, "em_garden", 3))
    # entrance: wall washers on the stone east facade next to the door
    add_light("SPOT", (26.0, 28.6, M.GARDEN + 0.05), 120.0, WARM2, "garden", size=0.03, spot=(40, 0.5),
              direction=(-0.6, 0, 6), name="wallwash")
    add_light("SPOT", (26.0, 31.9, M.GARDEN + 0.05), 120.0, WARM2, "garden", size=0.03, spot=(40, 0.5),
              direction=(-0.6, 0, 6), name="wallwash")
    # grazers along the south stone facade (dining/kitchen part) and west facade
    for x in (13.6, 16.0, 18.6, 21.0, 23.6):
        add_light("SPOT", (x, M.Y_S_G - 0.25, M.GARDEN + 0.03), 70.0, WARM2, "garden", size=0.03, spot=(35, 0.5),
                  direction=(0, 0.15, 6), name="graze")
    # ---------------- pendants (dining, island), lamps, fire
    pend = []
    for f in M.FURN:
        z = M.LV.get(f.level, 0.0)
        cx, cy = f.x + f.w / 2, f.y + f.d / 2
        zc = M.slab_bot(next_level(f.level)) if next_level(f.level) else z + 3
        if f.kind == "table_rect" and f.level == "G" and not room_of("G", cx, cy)[0].outdoor:
            long_x = f.w >= f.d
            for k in (-1, 0, 1):
                px = cx + (k * f.w * 0.3 if long_x else 0)
                py = cy + (0 if long_x else k * f.d * 0.3)
                pend.append((px, py, z + 1.55, zc, 0.17))
        if f.kind == "island":
            for k in (-1, 1):
                pend.append((cx, cy + k * f.d * 0.25, z + 1.65, zc, 0.13))
        if f.kind == "nightstand":
            add_light("POINT", (cx, cy, z + 0.95), 14.0, WARM, "lamp", size=0.1, name="lamp")
        if f.kind == "fireplace":
            add_light("POINT", (cx, f.y + 0.12, z + 0.45), 40.0, (1.0, 0.45, 0.15), "fire", size=0.25, name="fire")
    for (px, py, pz, zc, r) in pend:
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=r)
        ob = bm_object("pendant", bm, "em_pend", "lights_geo", (px, py, pz))
        ob.scale = (1, 1, 0.85)
        em.append(B(px - 0.004, py - 0.004, pz + r * 0.8, px + 0.004, py + 0.004, zc, "frame", 3))
        em.append(dict(t="cyl", x=px, y=py, z0=zc - 0.015, z1=zc, r=0.06, mat="frame", soft=3))
        add_light("POINT", (px, py, pz), 28.0, WARM, "pendant", size=r * 0.9, name="pendant")
    # lamp shades on nightstands
    for f in M.FURN:
        if f.kind == "nightstand":
            z = M.LV[f.level]
            cx, cy = f.x + f.w / 2, f.y + f.d / 2
            em.append(dict(t="cyl", x=cx, y=cy, z0=z + 0.80, z1=z + 1.02, r=0.17, r1=0.14, mat="em_lamp", soft=3, seg=28))
    add_elems(em, "lights_geo", "fx_")
    # ---------------- daylight portals on all glazed openings of ext walls (used for interior views)
    for w in M.WALLS:
        if w.kind != "ext" or not w.out:
            continue
        lv = M.LV.get(w.level, 0.0)
        for o in w.openings:
            if o.kind not in ("slide", "fixed", "window"):
                continue
            L_ = o.end - o.pos
            h = o.head - max(o.sill, 0)
            c = (o.pos + o.end) / 2
            zc = lv + (max(o.sill, 0) + o.head) / 2
            off = w.out * (w.t / 2 + 0.03)
            if w.horiz:
                loc = (c, w.c + off, zc)
                d = (0, -w.out, 0)
                add_light("AREA", loc, 1.0, (1, 1, 1), "portal", size=L_, size_y=h, direction=d, portal=True,
                          name="portal")
            else:
                loc = (w.c + off, c, zc)
                d = (-w.out, 0, 0)
                add_light("AREA", loc, 1.0, (1, 1, 1), "portal", size=h, size_y=L_, direction=d, portal=True,
                          name="portal")


# =========================================================================== #
#  World / sun / render settings
# =========================================================================== #
SUN = None
SKY = None
BG = None


def build_world():
    global SUN, SKY, BG
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    T = NT(w.node_tree)
    SKY = T.n("ShaderNodeTexSky", props=dict(sky_type="NISHITA", sun_disc=False, altitude=20.0))
    BG = T.n("ShaderNodeBackground", Color=SKY.outputs[0], Strength=0.3)
    out = T.n("ShaderNodeOutputWorld")
    T.nt.links.new(BG.outputs[0], out.inputs[0])
    ld = bpy.data.lights.new("sun", "SUN")
    ld.angle = math.radians(0.8)
    SUN = bpy.data.objects.new("sun", ld)
    coll("lights").objects.link(SUN)


def set_mode(mode_name, cam_cfg):
    md = MODES[mode_name]
    el, az = math.radians(md["sun_el"]), math.radians(md["sun_az"])
    SKY.sun_elevation = el
    SKY.sun_rotation = az
    SKY.dust_density = md["dust"]
    SKY.air_density = 1.0
    BG.inputs["Strength"].default_value = md["sky"]
    to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    SUN.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    SUN.data.energy = md["sun_E"]
    SUN.hide_render = md["sun_E"] <= 0
    SUN.data.color = md["sun_col"]
    mult = dict(md["lights"])
    mult.update(cam_cfg.get("lights", {}))
    for ob, grp, e0 in LIGHTS:
        f = mult.get(grp, 0.0)
        ob.data.energy = e0 * f
        ob.hide_render = f <= 0
    for grp, lst in EMIT.items():
        f = mult.get(grp, 0.0)
        for sock, s0 in lst:
            sock.default_value = s0 * f
    sc = bpy.context.scene
    sc.view_settings.exposure = cam_cfg.get("exposure", 0.0)
    sc.view_settings.look = cam_cfg.get("look", md.get("look", "AgX - Medium High Contrast"))


def setup_render(samples, width, threads):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.adaptive_min_samples = 16
    try:
        import _cycles
        has_oidn = bool(getattr(_cycles, "with_openimagedenoise", False))
    except Exception:
        has_oidn = False
    cy.use_denoising = True
    if has_oidn:
        cy.denoiser = "OPENIMAGEDENOISE"
        try:
            cy.denoising_input_passes = "RGB_ALBEDO_NORMAL"
            cy.denoising_prefilter = "ACCURATE"
        except Exception:
            pass
    else:
        cy.use_denoising = False
        print("  OpenImageDenoise not available - rendering without denoiser")
    cy.max_bounces = 8
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 3
    cy.transmission_bounces = 8
    cy.transparent_max_bounces = 24
    cy.volume_bounces = 0
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    cy.sample_clamp_indirect = 8.0
    cy.light_sampling_threshold = 0.01
    try:
        cy.use_light_tree = True
    except Exception:
        pass
    sc.render.threads_mode = "FIXED"
    sc.render.threads = threads
    sc.render.resolution_x = width
    sc.render.resolution_y = int(round(width * 10 / 16))
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 90
    sc.render.image_settings.color_mode = "RGB"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.display_settings.display_device = "sRGB"
    try:
        sc.cycles.tile_size = 1024
    except Exception:
        pass


def make_camera(name, cfg):
    cam = bpy.data.cameras.new(name)
    cam.lens = cfg["lens"]
    cam.sensor_width = 36.0
    cam.sensor_fit = "HORIZONTAL"
    cam.clip_start = 0.05
    cam.clip_end = 3000.0
    ob = bpy.data.objects.new(name, cam)
    coll("cameras").objects.link(ob)
    loc = Vector(cfg["loc"])
    tgt = Vector(cfg["tgt"])
    d = tgt - loc
    ob.location = loc
    if cfg.get("level", True):
        dh = math.hypot(d.x, d.y)
        ob.rotation_euler = (math.pi / 2, 0, math.atan2(d.y, d.x) - math.pi / 2)
        cam.shift_y = (cfg["lens"] * d.z / dh) / 36.0
    else:
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.shift_x = cfg.get("shift_x", 0.0)
    if "shift_y" in cfg:
        cam.shift_y = cfg["shift_y"]
    return ob


# =========================================================================== #
#  Scene assembly
# =========================================================================== #
def build_scene(veg=True, dense=True):
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    build_materials()
    arch = building_elems() + derived_site_elems() + room_floor_elems()
    add_elems(arch, "building")
    add_elems(terrain_elems(), "terrain", "ground_")
    add_elems(furniture_elems(), "furniture", "furn_")
    add_elems(car_elems(), "cars", "car_")
    # water surface (single plane - underwater lights reach the shell directly)
    P = M.SITE["pool"]
    me = bpy.data.meshes.new("pool_water")
    me.from_pydata([(P["x0"], P["y0"], P["water"]), (P["x1"], P["y0"], P["water"]), (P["x1"], P["y1"], P["water"]),
                    (P["x0"], P["y1"], P["water"])], [], [(0, 1, 2, 3)])
    me.materials.append(mat("water"))
    ob = bpy.data.objects.new("pool_water", me)
    coll("building").objects.link(ob)
    if veg:
        build_vegetation(dense)
    build_context()
    build_lights()
    build_world()
    cams = {n: make_camera(n, c) for n, c in CAMS.items()}
    unknown = sorted({b["mat"] for b in G.all_boxes()} - set(MATS))
    if unknown:
        print("  unknown materials mapped to default:", unknown)
    print(f"  scene built in {time.time() - t0:.1f}s  ({len(bpy.data.objects)} objects, {len(LIGHTS)} lights)")
    return cams


# =========================================================================== #
#  Export (glTF binary + .blend)
# =========================================================================== #
def export_model():
    os.makedirs(OUT_MODEL, exist_ok=True)
    blend = os.path.join(OUT_MODEL, "beit_kurkar.blend")
    sc = bpy.context.scene
    sc.camera = bpy.data.objects.get("ext_01")
    set_mode(CAMS["ext_01"]["mode"], CAMS["ext_01"])
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print("  saved", blend, f"{os.path.getsize(blend) / 1e6:.1f} MB")
    # lean copy for the web viewer: simple PBR materials, no bed planting instances / lights / far context
    for ob in list(bpy.data.objects):
        if ob.type != "MESH" or ob.users_collection[0].name in ("veg_instances", "lights_geo") \
                or ob.name.startswith(("far_", "far_tree", "golf_tree", "ntree_")):
            bpy.data.objects.remove(ob, do_unlink=True)
            continue
        for md in list(ob.modifiers):
            ob.modifiers.remove(md)
    # crop the huge ground plates to a 160 m square around the lot for the viewer
    for ob in bpy.data.objects:
        if ob.type == "MESH" and (ob.name.startswith("ground_") or ob.name in ("asphalt", "paving")):
            for v in ob.data.vertices:
                v.co.x = max(-60.0, min(90.0, v.co.x))
                v.co.y = max(-60.0, min(96.0, v.co.y))
                v.co.z = max(v.co.z, -2.0) if ob.name.startswith("ground_") else v.co.z
    simple = {}
    for name, (c, r, mtl, a) in SIMPLE.items():
        m = bpy.data.materials.new("gltf_" + name)
        m.use_nodes = True
        p = m.node_tree.nodes.get("Principled BSDF")
        p.inputs["Base Color"].default_value = c
        p.inputs["Roughness"].default_value = r
        p.inputs["Metallic"].default_value = mtl
        if a < 1.0:
            p.inputs["Alpha"].default_value = a
            m.blend_method = "BLEND"
            try:
                m.surface_render_method = "BLENDED"
            except Exception:
                pass
        m.name = name + "_pbr"
        simple[name] = m
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for slot in ob.material_slots:
            if slot.material:
                base = slot.material.name.split(".")[0]
                if base in simple:
                    slot.material = simple[base]
    bpy.ops.preferences.addon_enable(module="io_scene_gltf2")
    glb = os.path.join(OUT_MODEL, "beit_kurkar.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=False, export_apply=False,
                              export_lights=False, export_cameras=False, export_yup=True, export_texcoords=False,
                              export_normals=True, export_extras=False)
    print("  saved", glb, f"{os.path.getsize(glb) / 1e6:.1f} MB")


# =========================================================================== #
#  CLI
# =========================================================================== #
def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cams", nargs="*", help="camera names or 'all'")
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--preview", action="store_true", help="fast low-res preview")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--noveg", action="store_true", help="skip vegetation (fast tests)")
    ap.add_argument("--export", action="store_true", help="write out/model/beit_kurkar.glb and .blend")
    ap.add_argument("--blend", action="store_true", help="also save the .blend of the render scene")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--loc", help="override camera location x,y,z (iteration aid)")
    ap.add_argument("--tgt", help="override camera target x,y,z")
    ap.add_argument("--lens", type=float, help="override focal length")
    ap.add_argument("--mode", help="override light mode (day, dusk, int_day, int_dusk)")
    ap.add_argument("--exposure", type=float, help="override exposure")
    ap.add_argument("--suffix", default="", help="output file name suffix")
    a = ap.parse_args(argv)
    for n in (a.cams or []):
        if n in CAMS:
            c = CAMS[n]
            if a.loc:
                c["loc"] = tuple(float(v) for v in a.loc.split(","))
            if a.tgt:
                c["tgt"] = tuple(float(v) for v in a.tgt.split(","))
            if a.lens:
                c["lens"] = a.lens
            if a.mode:
                c["mode"] = a.mode
            if a.exposure is not None:
                c["exposure"] = a.exposure
    if a.list:
        for n, c in CAMS.items():
            print(f"{n:8s} {c['mode']:9s} {c['desc']}")
        return
    names = list(CAMS) if (not a.cams or "all" in a.cams) else a.cams
    if a.export and not a.cams:
        names = []
    for n in names:
        if n not in CAMS:
            sys.exit(f"unknown camera {n}; choose from {', '.join(CAMS)}")
    samples = a.samples or (20 if a.preview else 128)
    width = a.width or (640 if a.preview else 1800)
    out_dir = a.out or (PREVIEW_DIR if a.preview else OUT_RENDERS)
    os.makedirs(out_dir, exist_ok=True)
    cams = build_scene(veg=not a.noveg, dense=not a.noveg)
    for i in ISSUES:
        print("  NOTE:", i)
    setup_render(samples, width, a.threads)
    times = {}
    for n in names:
        cfg = CAMS[n]
        sc = bpy.context.scene
        sc.camera = cams[n]
        set_mode(cfg["mode"], cfg)
        sc.render.filepath = os.path.join(out_dir, f"{n}{a.suffix}.jpg")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        times[n] = time.time() - t0
        print(f"  rendered {n} -> {sc.render.filepath}  {width}px  {samples} spp  {times[n]:.0f}s", flush=True)
    if a.blend and not a.export:
        os.makedirs(OUT_MODEL, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_MODEL, "beit_kurkar.blend"), compress=True)
    if a.export:
        export_model()
    if times:
        print("render times:", ", ".join(f"{k} {v:.0f}s" for k, v in times.items()))


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    main(argv)
