import bpy
import json
import struct
from pathlib import Path

here = Path(__file__).resolve().parent
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=str(here / "avatar-ar.glb"))
glb = (here / "avatar-ar.glb").read_bytes()
json_length = struct.unpack_from("<I", glb, 12)[0]
document = json.loads(glb[20:20 + json_length])
alpha_modes = {material["name"]: material.get("alphaMode", "OPAQUE") for material in document["materials"]}
for obj in tuple(bpy.data.objects):
    if obj.type == "MESH" and len(obj.data.vertices) < 100:
        bpy.data.objects.remove(obj, do_unlink=True)

# The glTF importer represents unlit VRM textures through Emission nodes.
# USD Preview Surface needs a Principled material to preserve those textures.
for material in [m for m in bpy.data.materials if m.node_tree]:
    images = [
        node.image for node in material.node_tree.nodes
        if node.bl_idname == "ShaderNodeTexImage" and node.image
    ]
    if not images:
        continue
    material.node_tree.nodes.clear()
    output = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    shader = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = images[0]
    shader.inputs["Roughness"].default_value = 1
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    if alpha_modes.get(material.name) == "MASK":
        # Preserve glTF alpha clipping. A plain opacity connection would turn
        # hair/clothing into blended surfaces and cause depth sorting artifacts.
        clip = material.node_tree.nodes.new("ShaderNodeMath")
        clip.operation = "ROUND"
        material.node_tree.links.new(texture.outputs["Alpha"], clip.inputs[0])
        material.node_tree.links.new(clip.outputs[0], shader.inputs["Alpha"])
    elif alpha_modes.get(material.name) == "BLEND":
        material.node_tree.links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
bpy.ops.wm.usd_export(
    filepath=str(here / "avatar-ar.usdc"),
    export_animation=True,
    export_textures=True,
    export_textures_mode="NEW",
    export_materials=True,
    export_armatures=True,
    export_shapekeys=False,
    export_lights=False,
    export_cameras=False,
)
print("USDC", (here / "avatar-ar.usdc").stat().st_size)
