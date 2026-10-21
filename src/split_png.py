# -*- coding: utf-8 -*-
"""split_png.py — 把长报告截图裁成可读的分段。"""
from PIL import Image
import io, sys, pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = pathlib.Path(r"E:\dsh\output\webfetch-playground\report-top.png")
img = Image.open(SRC)
w, h = img.size
print(f"原图 {w}x{h}")

seg = 2600
out = []
for i, top in enumerate(range(0, h, seg), 1):
    bottom = min(top + seg, h)
    if bottom - top < 400:
        break
    part = img.crop((0, top, w, bottom))
    p = SRC.parent / f"seg-{i:02d}.png"
    part.save(p, optimize=True)
    out.append((p.name, part.size))
    print(f"  {p.name} {part.size[0]}x{part.size[1]}")

print(f"\n共 {len(out)} 段")
