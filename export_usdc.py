import bpy
import json
import struct
from pathlib import Path

here = Path(__file__).resolve().parent
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=str(here / "avatar-ar.glb"))
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 361
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
    output.name = "MaterialOutput"
    shader = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    shader.name = "Surface"
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.name = "BaseColorTexture"
    texture.image = images[0]
    uv = material.node_tree.nodes.new("ShaderNodeUVMap")
    uv.name = "UVMap"
    uv.uv_map = "UVMap"
    material.node_tree.links.new(uv.outputs["UV"], texture.inputs["Vector"])
    shader.inputs["Roughness"].default_value = 0.9
    shader.inputs["Specular IOR Level"].default_value = 0.2
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    # A small baked ambient contribution preserves the authored face/clothing
    # colors in dim AR lighting, while most of the material stays physically lit.
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Emission Color"])
    shader.inputs["Emission Strength"].default_value = 0.15
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
    generate_preview_surface=True,
    generate_materialx_network=False,
    convert_orientation=True,
    export_global_forward_selection="NEGATIVE_Z",
    export_global_up_selection="Y",
    export_armatures=True,
    export_shapekeys=False,
    export_lights=False,
    export_cameras=False,
)
# Keep portable package-relative texture paths and validate the exact USD layer.
from pxr import Gf, Sdf, Usd, UsdShade, UsdUtils
stage = Usd.Stage.Open(str(here / "avatar-ar.usdc"))
# Blender exports a linked emission texture without its Strength multiplier.
# Give ambient its own texture reader so only emission is scaled, not albedo.
for prim in list(stage.Traverse()):
    emission = prim.GetAttribute("inputs:emissiveColor")
    if emission and emission.GetConnections():
        source_path = emission.GetConnections()[0].GetPrimPath()
        ambient_path = source_path.GetParentPath().AppendChild("AmbientTexture")
        Sdf.CopySpec(stage.GetRootLayer(), source_path, stage.GetRootLayer(), ambient_path)
        ambient = UsdShade.Shader(stage.GetPrimAtPath(ambient_path))
        ambient.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(0.15, 0.15, 0.15, 1.0))
        emission.SetConnections([ambient_path.AppendProperty("outputs:rgb")])
for prim in stage.Traverse():
    attr = prim.GetAttribute("inputs:file")
    if attr and attr.Get():
        path = attr.Get().path.removeprefix("./")
        assert (here / path).is_file(), path
        attr.Set(Sdf.AssetPath(path))
stage.GetRootLayer().Save()
checker = UsdUtils.ComplianceChecker(arkit=True)
checker.CheckCompliance(str(here / "avatar-ar.usdc"))
assert not checker.GetErrors(), checker.GetErrors()
assert not checker.GetFailedChecks(), checker.GetFailedChecks()
print("USDC", (here / "avatar-ar.usdc").stat().st_size)
