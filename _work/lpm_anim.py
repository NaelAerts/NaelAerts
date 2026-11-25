"""
lpm_anim.py - object-rig + render helpers shared by the animated lpm scenes.

An "object rig": every limb is its own flat-shaded lpm object whose origin sits on its joint,
parented into a chain, then keyframed in rotation. No armature, no skinning.

Two rules learned the hard way and baked in here:
  * a child's angles ADD to its parent's, so poses are written as WORLD angles and converted;
  * a prop held in a hand cannot be oriented by adding Euler angles (a shoulder yaw breaks the
    arithmetic) - aim_dir / aim_at / aim_tip_z solve it against the evaluated parent matrix.
"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Euler, Matrix, Vector

import lpm

PALETTE = {"P": None}


def set_palette(p):
    PALETTE["P"] = p
    return p


# --------------------------------------------------------------------------- rig building

def empty(name, at=(0, 0, 0), parent=None, collection="COL_Rig"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.06
    lpm._col(collection).objects.link(e)
    e.location = at
    if parent is not None:
        set_parent(e, parent)
    return e


def set_parent(ob, parent):
    """Parent while keeping the current world transform (rest-pose bind)."""
    bpy.context.view_layer.update()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()


def group(name, parts, pivot=(0, 0, 0), parent=None, budget=None):
    """finish() the parts in place, move the origin onto `pivot`, parent it."""
    ob = lpm.finish(name, parts, PALETTE["P"], budget=budget, ground=False, center=False)
    ob.data.transform(Matrix.Translation(-Vector(pivot)))
    ob.location = Vector(pivot)
    ob.rotation_mode = "XYZ"
    if parent is not None:
        set_parent(ob, parent)
    return ob


def dup(ob, name):
    d = ob.copy()
    d.data = ob.data.copy()
    d.name = name
    d.data.name = name
    for c in ob.users_collection:
        c.objects.link(d)
    return d


# --------------------------------------------------------------------------- keyframes

def _fcurves(ob):
    """Blender 5.x slotted actions: fcurves live in a channelbag, not on the action."""
    ad = ob.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    fc = getattr(act, "fcurves", None)
    if fc is not None:
        return list(fc)
    out = []
    slot = getattr(ad, "action_slot", None)
    for layer in act.layers:
        for strip in layer.strips:
            try:
                cb = strip.channelbag(slot) if slot is not None else None
            except Exception:
                cb = None
            if cb is None:
                cb = next(iter(getattr(strip, "channelbags", [])), None)
            if cb is not None:
                out.extend(cb.fcurves)
    return out


def _interp(ob, path, f, interp):
    for fc in _fcurves(ob):
        if fc.data_path != path:
            continue
        for k in fc.keyframe_points:
            if abs(k.co.x - f) < 0.5:
                k.interpolation = interp


def kr(ob, f, rx=0.0, ry=0.0, rz=0.0, interp="BEZIER"):
    ob.rotation_euler = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ")
    ob.keyframe_insert("rotation_euler", frame=f)
    _interp(ob, "rotation_euler", f, interp)


def kl(ob, f, x=None, y=None, z=None, interp="BEZIER"):
    loc = list(ob.location)
    for i, v in enumerate((x, y, z)):
        if v is not None:
            loc[i] = v
    ob.location = loc
    ob.keyframe_insert("location", frame=f)
    _interp(ob, "location", f, interp)


def ks(ob, f, s, interp="BEZIER"):
    ob.scale = s if isinstance(s, (tuple, list)) else (s, s, s)
    ob.keyframe_insert("scale", frame=f)
    _interp(ob, "scale", f, interp)


def kvis(ob, f, visible):
    """Keyframe render + viewport visibility (used to swap a prop between hand and ground)."""
    ob.hide_render = not visible
    ob.hide_viewport = not visible
    ob.keyframe_insert("hide_render", frame=f)
    ob.keyframe_insert("hide_viewport", frame=f)
    for path in ("hide_render", "hide_viewport"):
        _interp(ob, path, f, "CONSTANT")


# --------------------------------------------------------------------------- exact prop aiming

def _bind_frame(ob, dg):
    par = ob.parent.evaluated_get(dg).matrix_world
    return par @ ob.matrix_parent_inverse


def aim_dir(ob, f, local_vec, world_dir):
    """Key ob's local rotation at frame f so `local_vec` points along `world_dir` in world space."""
    sc = bpy.context.scene
    sc.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    M3 = _bind_frame(ob, dg).to_3x3()
    v = Vector(local_vec)
    u = M3.inverted() @ Vector(world_dir)
    ob.rotation_euler = v.rotation_difference(u).to_euler("XYZ")
    ob.keyframe_insert("rotation_euler", frame=f)
    _interp(ob, "rotation_euler", f, "BEZIER")


def aim_at(ob, f, local_vec, target):
    sc = bpy.context.scene
    sc.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    origin = _bind_frame(ob, dg) @ Vector(ob.location)
    aim_dir(ob, f, local_vec, Vector(target) - origin)


def aim_tip_z(ob, f, local_vec, tip_z, toward):
    """Aim so the tip sits exactly at height `tip_z` while pointing toward the (x, y) of `toward`."""
    sc = bpy.context.scene
    sc.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    origin = _bind_frame(ob, dg) @ Vector(ob.location)
    L = Vector(local_vec).length
    cos = max(-1.0, min(1.0, (origin.z - tip_z) / L))
    sin = math.sqrt(max(0.0, 1.0 - cos * cos))
    h = Vector((toward[0] - origin.x, toward[1] - origin.y, 0))
    h = h.normalized() if h.length > 1e-6 else Vector((0, -1, 0))
    aim_dir(ob, f, local_vec, Vector((h.x * sin, h.y * sin, -cos)))


# --------------------------------------------------------------------------- camera / light / render

def camera(name, loc, look, lens=40.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    tgt = empty(f"{name}_TGT", look)
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return cam, tgt


def sky_and_sun(sun_energy=4.6, sky_strength=0.28, elevation=38, rotation=205,
                sun_euler=(52, 0, 38), fill=None, flat=None):
    w = bpy.data.worlds.new("W_Sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    for st in ("MULTIPLE_SCATTERING", "NISHITA", "HOSEK_WILKIE"):
        try:
            sky.sky_type = st
            break
        except TypeError:
            continue
    for attr, val in (("sun_elevation", math.radians(elevation)), ("sun_rotation", math.radians(rotation)),
                      ("sun_disc", False), ("air_density", 1.0), ("dust_density", 0.8)):
        try:
            setattr(sky, attr, val)
        except Exception:
            pass
    if flat is None:
        nt.links.new(sky.outputs[0], bg.inputs[0])
    else:
        # a flat sky keeps the stylised look and stops the horizon blowing out to white
        bg.inputs[0].default_value = (flat[0], flat[1], flat[2], 1.0)
    bg.inputs[1].default_value = sky_strength

    sd = bpy.data.lights.new("L_Sun", "SUN")
    sd.energy = sun_energy
    sd.angle = math.radians(12)
    sd.color = (1.0, 0.95, 0.86)
    sun = bpy.data.objects.new("L_Sun", sd)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = Euler([math.radians(a) for a in sun_euler], "XYZ")
    if fill:
        fd = bpy.data.lights.new("L_Fill", "AREA")
        fd.energy, fd.size, fd.color = fill.get("energy", 90), fill.get("size", 6.0), fill.get("color", (1.0, 0.97, 0.92))
        fo = bpy.data.objects.new("L_Fill", fd)
        bpy.context.scene.collection.objects.link(fo)
        fo.location = fill.get("loc", (-4.5, -6.0, 4.2))
        fo.rotation_euler = Euler([math.radians(a) for a in fill.get("rot", (52, 0, -38))], "XYZ")
    return sun


def setup_render(samples=16, res=960, threads=0):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 2
    sc.cycles.transparent_max_bounces = 2
    sc.cycles.volume_bounces = 0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    except Exception as e:
        print("[render] denoiser unavailable:", e)
        sc.cycles.use_denoising = False
    sc.render.resolution_x = res
    sc.render.resolution_y = int(round(res * 9 / 16))
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.compression = 20
    sc.view_settings.view_transform = "Standard"
    sc.render.filter_size = 1.4
    if threads:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = threads


def render_frames(frames, out_dir, skip_existing=True):
    import time
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    for f in frames:
        path = os.path.join(out_dir, f"f_{f:04d}.png")
        if skip_existing and os.path.exists(path) and os.path.getsize(path) > 2000:
            continue
        t0 = time.time()
        sc.frame_set(f)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"[render] frame {f} -> {os.path.basename(path)}  {time.time() - t0:.1f}s", flush=True)


def world_point(ob, local=(0, 0, 0), frame=None):
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(frame)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    return ob.evaluated_get(dg).matrix_world @ Vector(local)
