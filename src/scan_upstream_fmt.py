# -*- coding: utf-8 -*-
"""scan_upstream_fmt.py — 在 DSH 运行时里找 "upstream client" 错误格式的来源。"""
import io
import re
import pathlib
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOTS = [
    pathlib.Path(r"E:\dsh\resources\app.asar.unpacked\dsh\node_modules\@deepseek-ai"),
]

PAT = re.compile(rb"upstream\s*(client|server)?\s*\(http")

hits = 0
for root in ROOTS:
    if not root.exists():
        print("(目录不存在)", root)
        continue
    for p in root.rglob("*.js"):
        try:
            if p.stat().st_size > 8 * 1024 * 1024:
                continue
            data = p.read_bytes()
        except Exception:
            continue
        for m in PAT.finditer(data):
            lo = max(0, m.start() - 260)
            hi = min(len(data), m.end() + 260)
            sn = data[lo:hi].decode("utf-8", "replace")
            sn = re.sub(r"\s+", " ", sn)
            print("=" * 80)
            print(p.relative_to(root))
            print("  ", sn[:480])
            hits += 1
            if hits >= 6:
                break
        if hits >= 6:
            break
    if hits >= 6:
        break

if not hits:
    print("未在 unpacked 中找到；可能打包在 app.asar 内。")
