# -*- coding: utf-8 -*-
"""find_fmt.py — 在插件里找 (http 与 upstream 的拼装点。"""
import io
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LIB = pathlib.Path(r"C:\Users\1\.dsh\profiles\desktop\node_modules\dsh-workbuddy\lib")

pats = [
    r"\(http\s",
    r"upstream\s+client",
    r"upstream\s+\$\{",
    r"\$\{kind\}",
    r"`[^`]{0,60}upstream[^`]{0,60}`",
]

for f in ["index.js", "host-heartbeat-BLiKF_E0.js", "client.js"]:
    p = LIB / f
    if not p.exists():
        continue
    lines = p.read_text(encoding="utf-8", errors="replace").split("\n")
    print("=" * 80)
    print(f)
    n = 0
    for i, ln in enumerate(lines, 1):
        if any(re.search(pt, ln) for pt in pats):
            t = ln.strip()
            print(f"  L{i}: {t[:210]}")
            n += 1
            if n >= 12:
                break
    if n == 0:
        print("  (无匹配)")
    print()
