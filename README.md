# kqede AR card prototype
Files: index.html (MindAR image tracking + three-vrm, idle sway/breath/head turn + random blink), model.vrm, targets.mind (compiled from target.png = left pattern area of card.png), card.png (85.6x54mm @300dpi, QR box at top right), preview.png, preview.html+shot.js (headless render), compile.mjs (target compiler), makecard.py.
Local test: `python3 -m http.server 8080` then open from a phone over HTTPS (camera needs a secure context), e.g. via an HTTPS host or tunnel.
Print card.png. Point the camera at the patterned left side (target.png).
After adding the real QR, keep target.png unchanged, or recompile with `node compile.mjs`.
License: VRM 1.0 avatarPermission=onlyAuthor, personalNonProfit, redistribution NO, modification NO, credit required.
