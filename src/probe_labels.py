# -*- coding: utf-8 -*-
"""probe_labels.py — 找 provider 注册名与错误标签模板。"""
import io
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LIB = pathlib.Path(r"C:\Users\1\.dsh\profiles\desktop\node_modules\dsh-workbuddy\lib")

pats = [
    r'"?workbuddy-cn"?',
    r'"?workbuddy-ai"?',
    r'upstream[^"\']{0,40}',
    r'providerId\s*[:=][^,\n]{0,40}',
    r'id:\s*"workbuddy[^"]*"',
]

for f in ["index.js", "host-heartbeat-BLiKF_E0.js", "client.js"]:
    p = LIB / f
    if not p.exists():
        continue
    print("=" * 84)
    print(f)
    lines = p.read_text(encoding="utf-8", errors="replace").split("\n")
    hits = 0
    for i, ln in enumerate(lines, 1):
        for pat in pats:
            if re.search(pat, ln):
                t = ln.strip()
                if len(t) > 200:
                    t = t[:200]
                print(f"  L{i}: {t}")
                hits += 1
                break
        if hits >= 14:
            break
    print()
