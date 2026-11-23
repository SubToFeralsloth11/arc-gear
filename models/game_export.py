"""Game-ready exports: the animated raider and every gear model as GLBs with baked textures.

The Blender models use procedural Cycles materials, which glTF cannot carry. This script lays out a
shared UV atlas per model, bakes base colour and roughness into images, applies the modifiers, joins
each model into one mesh with one material and writes out/game/<name>.glb.

Run after models/raider_anim.py (and the gear scripts):
    blender -b -P models/game_export.py                 (raider + all gear)
    blender -b -P models/game_export.py -- ar pickaxe   (only the named models; `raider` for the raider)
    add `quick` for 512 px textures.
Raider: out/game/raider.glb, skinned, every animation clip as its own action, plus the weapon_r
socket bone. Gear: out/game/<item>.glb in the item's own frame (forward +X, up +Z in Blender, which
glTF stores as +X forward, +Y up).
"""
import math
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
GAME = os.path.join(OUT, "game")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "quick" in ARGS
GEAR = ["ar", "smg", "rifle", "pickaxe", "impact_grenade", "smoke_grenade", "shield_recharger", "bandage"]
os.makedirs(GAME, exist_ok=True)


def setup_cycles():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception as e:
        print("GPU setup failed, using CPU:", e)
    scene.cycles.samples = 4
    scene.render.bake.margin = 4


def only_select(objs, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def bake_and_join(objs, name, size):
    """Bake colour + roughness of objs into one atlas, apply modifiers (except ARMATURE), join them."""
    setup_cycles()
    for o in objs:
        o.hide_render = o.hide_viewport = False
        o.hide_set(False)
        uv = o.data.uv_layers.get("bake") or o.data.uv_layers.new(name="bake")
        o.data.uv_layers.active = uv
    only_select(objs)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    images = {}
    for kind in ("color", "rough"):
        img = bpy.data.images.new(f"{name}_{kind}", size, size, alpha=False)
        if kind == "rough":
            img.colorspace_settings.name = "Non-Color"
        images[kind] = img
    mats = {m for o in objs for m in o.data.materials if m}
    for m in mats:
        nt = m.node_tree
        n = nt.nodes.new("ShaderNodeTexImage")
        n.name = "__bake__"
        nt.nodes.active = n
    for kind, btype in (("color", "DIFFUSE"), ("rough", "ROUGHNESS")):
        for m in mats:
            m.node_tree.nodes["__bake__"].image = images[kind]
        kw = dict(type=btype, use_clear=True, margin=4)
        if btype == "DIFFUSE":
            kw["pass_filter"] = {"COLOR"}
        only_select(objs)
        bpy.ops.object.bake(**kw)
        images[kind].pack()
        print(f"[export] {name}: baked {kind}")
    # one material with the baked maps
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexImage")
    tc.image = images["color"]
    tr = nt.nodes.new("ShaderNodeTexImage")
    tr.image = images["rough"]
    nt.links.new(tc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 0.0
    for o in objs:
        for mod in list(o.modifiers):
            if mod.type == "ARMATURE":
                continue
            if not mod.show_render:
                o.modifiers.remove(mod)
                continue
            only_select([o])
            bpy.ops.object.modifier_apply(modifier=mod.name)
        o.data.materials.clear()
        o.data.materials.append(mat)
        for uv in list(o.data.uv_layers):
            if uv.name != "bake":
                o.data.uv_layers.remove(uv)
    only_select(objs, objs[0])
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = joined.data.name = name
    me = joined.data
    me.calc_loop_triangles()
    print(f"[export] {name}: {len(me.loop_triangles):,} tris")
    return joined


def export(path, objs, anim=False):
    only_select(objs)
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_apply=False,
              export_skins=anim, export_image_format="JPEG", export_jpeg_quality=88)
    if anim:
        kw.update(export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True,
                  export_frame_range=False, export_def_bones=False)
    else:
        kw.update(export_animations=False)
    bpy.ops.export_scene.gltf(**kw)
    print("EXPORTED", path)


targets = [a for a in ARGS if a in GEAR + ["raider"]] or ["raider"] + GEAR

if "raider" in targets:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "raider_anim.blend"))
    rig = bpy.data.objects["Raider_Skeleton"]
    rig.animation_data.action = None
    rig.data.pose_position = "REST"
    for o in [o for o in bpy.data.objects if o.parent is rig and o.parent_type == "BONE"]:
        bpy.data.objects.remove(o)              # the preview rifle on weapon_r
    parts = [o for o in rig.children if o.type == "MESH" and not o.hide_render]
    body = bake_and_join(parts, "Raider", 1024 if QUICK else 4096)
    rig.data.pose_position = "POSE"
    export(os.path.join(GAME, "raider.glb"), [rig, body], anim=True)

for item in [t for t in targets if t in GEAR]:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, f"{item}.blend"))
    objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name != "Floor"]
    for o in objs:                              # world-space parts, no parenting surprises on join
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    m = bake_and_join(objs, item, 512 if QUICK else 2048)
    export(os.path.join(GAME, f"{item}.glb"), [m])
