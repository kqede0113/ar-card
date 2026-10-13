"""Build a static, relaxed-pose GLB from an uncompressed VRM with Blender.

Run from this directory, passing the owner's uncompressed source VRM after --.
"""

import bpy
import sys
from pathlib import Path


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
    if obj.type not in {"MESH", "ARMATURE"} or obj.name == "Icosphere":
        bpy.data.objects.remove(obj, do_unlink=True)

armature = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
for name, angle in (("J_Bip_L_UpperArm", -1.13), ("J_Bip_R_UpperArm", 1.13)):
    bone = armature.pose.bones[name]
    bone.rotation_mode = "XYZ"
    bone.rotation_euler.z = angle
bpy.context.view_layer.update()

# Bake the relaxed pose into geometry. AR Quick Look and Scene Viewer then show
# the same pose without depending on VRM rigging or animation support.
depsgraph = bpy.context.evaluated_depsgraph_get()
for obj in tuple(bpy.data.objects):
    if obj.type != "MESH":
        continue
    matrix = obj.matrix_world.copy()
    baked_mesh = bpy.data.meshes.new_from_object(
        obj.evaluated_get(depsgraph),
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    obj.data = baked_mesh
    obj.modifiers.clear()
    obj.parent = None
    obj.matrix_world = matrix
bpy.data.objects.remove(armature, do_unlink=True)

print("IMPORTED", [(obj.name, obj.type) for obj in bpy.data.objects])

bpy.ops.export_scene.gltf(
    filepath=str(HERE / "avatar-ar.glb"),
    export_format="GLB",
    export_apply=True,
    export_animations=False,
    export_skins=False,
    export_morph=False,
    export_image_format="AUTO",
)
print("GLB", (HERE / "avatar-ar.glb").stat().st_size)

# The USDZ build is performed separately after the GLB is visually checked.
