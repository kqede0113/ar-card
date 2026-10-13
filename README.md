# DCC AR

GitHub Pages: https://kqede0113.github.io/ar-card/

The page lets visitors place the DCC avatar on a detected floor without a card or QR marker. It uses [model-viewer](https://modelviewer.dev/) with WebXR or Scene Viewer on compatible Android devices and AR Quick Look on compatible iPhones. Desktop browsers can rotate and zoom the 3D preview.

The site consists of index.html, styles.css, app.js, avatar-ar.glb, avatar-ar.usdz, and avatar-ar-preview.png. The older card-tracking files remain in the repository but are not used by the current page.

## Rebuild the AR assets

The existing compressed VRM uses EXT_meshopt_compression, which Blender 4.4's glTF importer cannot open. Use the owner's uncompressed source VRM and Blender 4.4 or newer:

1. Run Blender in background mode with export_ar_models.py and pass the uncompressed source VRM path after a double dash.
2. Run Blender in background mode with export_usdc.py.
3. Run Python with package_usdz.py.

The scripts bake a static relaxed standing pose into the GLB, then package the USD scene and textures as an uncompressed, 64-byte-aligned USDZ archive. The original VRM remains untouched.

## Rights

Avatar: kqede. The source VRM metadata requires credit and says redistribution and modification need the author's permission. The AR assets are for this DCC experience; contact the author before reusing them.
