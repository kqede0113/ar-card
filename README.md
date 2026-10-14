# DCC AR

GitHub Pages: https://kqede0113.github.io/ar-card/

The page lets visitors place the DCC avatar on a detected floor without a card or QR marker. It uses [model-viewer](https://modelviewer.dev/) with WebXR or Scene Viewer on compatible Android devices and AR Quick Look on compatible iPhones. Desktop browsers can rotate and zoom the 3D preview.

The site consists of index.html, styles.css, app.js, avatar-ar.glb, avatar-ar.usdz, and avatar-ar-preview.png. The older card-tracking files remain in the repository but are not used by the current page.

## Rebuild the AR assets

The existing compressed VRM uses EXT_meshopt_compression, which Blender 4.4's glTF importer cannot open. Use the owner's uncompressed source VRM and Blender 4.4 or newer:

1. Run Blender in background mode with export_ar_models.py and pass the uncompressed source VRM path after a double dash.
2. Run Blender in background mode with export_usdc.py.
3. Run Python with package_usdz.py.

The scripts keep the relaxed standing pose and export a single 12-second idle loop: subtle chest breathing, small shoulder/head movement, and four blinks with varied spacing (including one double blink). Feet remain fixed. The author's eye-close shape is converted to six head-relative joints, keeping at most four skin influences per vertex and avoiding morph targets that Android Scene Viewer does not support. Both GLB and USDZ contain skeletal animation. The web preview autoplays the same loop.

The arms also swing gently on independent six-second cycles, with delayed forearm and wrist movement and a slower twelve-second drift. The elbows stay slightly bent to soften the straight-down pose. The neck and head share a slow glance, gentle tilt, and smaller nod to keep the gaze relaxed.

The USD scene and textures are packaged as an uncompressed, 64-byte-aligned USDZ archive. The iPhone export uses Y-up, ASCII shader names, explicit UV coordinates, portable texture paths, and the full 12-second animation range; OpenUSD's ARKit compliance checker validates the exported layer. The original VRM remains untouched. Actual native AR playback still needs verification on iPhone Safari and Android Chrome.

## Rights

Avatar: kqede. The source VRM metadata requires credit and says redistribution and modification need the author's permission. The AR assets are for this DCC experience; contact the author before reusing them.
