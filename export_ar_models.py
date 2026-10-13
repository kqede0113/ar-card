"""Build a relaxed-pose, animated AR GLB from an uncompressed VRM.

Run from this directory, passing the owner's uncompressed source VRM after --.
"""

import bpy
import sys
import math
from pathlib import Path
from mathutils import Vector


HERE = Path(__file__).resolve().parent
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
if not args:
    raise SystemExit("Pass an uncompressed VRM source path after --")
source = Path(args[0])
if not source.exists():
    raise SystemExit("VRM source not found: " + str(source))
bpy.ops.import_scene.gltf(filepath=str(source))

# Keep the exported scene focused on the avatar. The helper end nodes and
# spring-bone metadata are not needed for a stationary AR preview.
for obj in tuple(bpy.data.objects):
    if obj.type not in {"MESH", "ARMATURE"} or (obj.type == "MESH" and len(obj.data.vertices) < 100):
        bpy.data.objects.remove(obj, do_unlink=True)

armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
for name, angle in (("J_Bip_L_UpperArm", -1.13), ("J_Bip_R_UpperArm", 1.13)):
    bone = armature.pose.bones[name]
    bone.rotation_mode = "XYZ"
    bone.rotation_euler.z = angle

# Scene Viewer does not support morph targets. Encode the author's blink shape
# as translations of six head-relative joints instead. Each affected vertex
# uses its three signed-axis weights plus the head weight (four influences).
face = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.data.shape_keys)
blink_shape = face.data.shape_keys.key_blocks["Fcl_EYE_Close"]
head = armature.data.bones["J_Bip_C_Head"]
head_matrix = head.matrix_local.copy()
to_head = head_matrix.inverted().to_3x3() @ armature.matrix_world.inverted().to_3x3() @ face.matrix_world.to_3x3()
deltas = {v.index: to_head @ (blink_shape.data[v.index].co - v.co) for v in face.data.vertices}
deltas = {i: d for i, d in deltas.items() if d.length > 1e-7}
amplitude = max(sum(abs(x) for x in d) for d in deltas.values()) * 1.2
bpy.context.view_layer.objects.active = armature
armature.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
blink_bones = []
for axis in range(3):
    for sign in (-1, 1):
        name = "AR_Blink_%s_%s" % ("XYZ"[axis], "N" if sign < 0 else "P")
        bone = armature.data.edit_bones.new(name)
        bone.matrix = head_matrix
        bone.length = 0.01
        bone.parent = armature.data.edit_bones["J_Bip_C_Head"]
        blink_bones.append((name, axis, sign))
bpy.ops.object.mode_set(mode="OBJECT")
groups = {name: face.vertex_groups.new(name=name) for name, _, _ in blink_bones}
head_group = face.vertex_groups.get("J_Bip_C_Head") or face.vertex_groups.new(name="J_Bip_C_Head")
for index, delta in deltas.items():
    for group in face.vertex_groups:
        group.remove([index])
    total = 0.0
    for name, axis, sign in blink_bones:
        weight = max(0, delta[axis] * sign) / amplitude
        if weight > 0:
            groups[name].add([index], weight, "REPLACE")
            total += weight
    head_group.add([index], 1.0 - total, "REPLACE")
for obj in bpy.data.objects:
    if obj.type == "MESH" and obj.data.shape_keys:
        obj.shape_key_clear()

scene = bpy.context.scene
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 361

def smoothstep(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)

def blink_at(t):
    amount = 0.0
    for start in (1.7, 5.25, 5.62, 9.3):
        elapsed = t - start
        if 0 <= elapsed < 0.08:
            amount = max(amount, smoothstep(elapsed / 0.08))
        elif 0.08 <= elapsed < 0.11:
            amount = 1.0
        elif 0.11 <= elapsed < 0.24:
            amount = max(amount, 1 - smoothstep((elapsed - 0.11) / 0.13))
    return amount

for frame in range(1, scene.frame_end + 1):
    t = (frame - 1) / scene.render.fps
    breath = 0.5 - 0.5 * math.cos(2 * math.pi * t / 4)
    sway = math.sin(2 * math.pi * t / 12)
    chest = armature.pose.bones["J_Bip_C_Chest"]
    chest.scale = (1 + 0.008 * breath, 1 + 0.003 * breath, 1 + 0.007 * breath)
    chest.keyframe_insert("scale", frame=frame)
    for name, angle in (("J_Bip_L_UpperArm", -1.13 - 0.002 * breath), ("J_Bip_R_UpperArm", 1.13 + 0.002 * breath)):
        bone = armature.pose.bones[name]
        bone.rotation_euler.z = angle
        bone.keyframe_insert("rotation_euler", frame=frame)
    head_pose = armature.pose.bones["J_Bip_C_Head"]
    head_pose.rotation_mode = "XYZ"
    head_pose.rotation_euler = (0.003 * breath, 0.005 * sway, 0.008 * sway)
    head_pose.keyframe_insert("rotation_euler", frame=frame)
    blink = blink_at(t)
    for name, axis, sign in blink_bones:
        bone = armature.pose.bones[name]
        location = Vector((0, 0, 0))
        location[axis] = sign * amplitude * blink
        bone.location = location
        bone.keyframe_insert("location", frame=frame)
armature.animation_data.action.name = "Idle_Breathe_Blink"
scene.frame_set(1)
bpy.context.view_layer.update()
for obj in bpy.data.objects:
    if obj.type == "MESH":
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
print("BLINK_JOINTS", len(blink_bones), "VERTICES", len(deltas), "AMPLITUDE", amplitude)
(HERE / ".blender-temp").mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / ".blender-temp" / "avatar-animated.blend"))

print("IMPORTED", [(obj.name, obj.type) for obj in bpy.data.objects])

bpy.ops.export_scene.gltf(
    filepath=str(HERE / "avatar-ar.glb"),
    export_format="GLB",
    export_apply=False,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_frame_range=True,
    export_force_sampling=True,
    export_skins=True,
    export_morph=False,
    export_image_format="AUTO",
)
print("GLB", (HERE / "avatar-ar.glb").stat().st_size)

# The USDZ build is performed separately after the GLB is visually checked.
