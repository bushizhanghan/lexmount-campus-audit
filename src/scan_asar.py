# -*- coding: utf-8 -*-
"""scan_asar.py — 在 app.asar 里定位 workbuddy / codebuddy 的 API 端点与渠道校验逻辑。"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ASAR = r"E:\dsh\resources\app.asar"

# 只读目标片段，避免全量加载 121MB
pats = [
    rb"codebuddy\.cn",
    rb"workbuddy\.ai",
    rb"unapproved channel",
    rb"11128",
    rb"x-channel",
    rb"channel-verification",
]

found = {p: [] for p in pats}
CHUNK = 8 * 1024 * 1024
OVERLAP = 200

with open(ASAR, "rb") as f:
    prev = b""
    offset = 0
    while True:
        buf = f.read(CHUNK)
        if not buf:
            break
        data = prev + buf
        for p in pats:
            start = 0
            while True:
                i = data.find(p, start)
                if i < 0:
                    break
                # 抓前后文
                lo = max(0, i - 220)
                hi = min(len(data), i + 260)
                snippet = data[lo:hi].decode("utf-8", "replace")
                found[p].append((offset - len(prev) + i, snippet))
                start = i + 1
                if len(found[p]) >= 6:
                    break
        prev = data[-OVERLAP:]
        offset += len(buf)

for p, hits in found.items():
    print("=" * 82)
    print(p.decode(), f"-> {len(hits)} 处")
    for off, sn in hits[:4]:
        sn = re.sub(r"\s+", " ", sn)
        print(f"  @{off}: {sn[:340]}")
    print()
