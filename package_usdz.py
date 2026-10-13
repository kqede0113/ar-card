"""Package Blender's USD and texture files as a 64-byte-aligned USDZ archive."""

from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo
import struct


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "avatar-ar.usdc"
OUTPUT = HERE / "avatar-ar.usdz"
FILES = [SOURCE, *sorted((HERE / "textures").iterdir())]

with ZipFile(OUTPUT, "w", compression=ZIP_STORED, allowZip64=False) as archive:
    for path in FILES:
        name = path.name if path == SOURCE else "textures/" + path.name
        info = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
        info.compress_type = ZIP_STORED
        offset = archive.fp.tell()
        padding = (-offset - 30 - len(name.encode("utf-8"))) % 64
        if 0 < padding < 4:
            padding += 64
        if padding:
            info.extra = struct.pack("<HH", 0x1986, padding - 4) + bytes(padding - 4)
        archive.writestr(info, path.read_bytes())

with ZipFile(OUTPUT) as archive:
    assert archive.testzip() is None
    assert all((entry.header_offset + 30 + len(entry.filename.encode("utf-8")) + len(entry.extra)) % 64 == 0 for entry in archive.infolist())
    assert archive.namelist()[0] == "avatar-ar.usdc"

print(f"USDZ: {OUTPUT.stat().st_size:,} bytes; {len(FILES)} files")
