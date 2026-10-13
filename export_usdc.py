import bpy
from pathlib import Path

here = Path(__file__).resolve().parent
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(here / "avatar-ar.glb"))

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
    material.node_tree.links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
bpy.ops.wm.usd_export(
    filepath=str(here / "avatar-ar.usdc"),
    export_animation=False,
    export_textures=True,
    export_textures_mode="NEW",
    export_materials=True,
    export_armatures=False,
    export_shapekeys=False,
    export_lights=False,
    export_cameras=False,
)
print("USDC", (here / "avatar-ar.usdc").stat().st_size)
