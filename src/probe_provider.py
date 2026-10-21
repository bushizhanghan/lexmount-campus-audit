# -*- coding: utf-8 -*-
"""probe_provider.py — 定位 provider 注册与区域选择逻辑。"""
import io
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LIB = pathlib.Path(r"C:\Users\1\.dsh\profiles\desktop\node_modules\dsh-workbuddy\lib")
p = LIB / "index.js"
src = p.read_text(encoding="utf-8", errors="replace")
lines = src.split("\n")

# 找 provider 注册结构
print("=" * 88)
print("provider 相关注册")
print("=" * 88)
for i, ln in enumerate(lines, 1):
    if re.search(r'registerProvider|providerName|provider:\s*\{|name:\s*"(WorkBuddy|workbuddy)', ln, re.I):
        t = ln.strip()
        print(f"L{i}: {t[:190]}")

print()
print("=" * 88)
print("region 判定逻辑")
print("=" * 88)
for i, ln in enumerate(lines, 1):
    if re.search(r'regionOf|region\s*===|"cn"|"global"', ln):
        t = ln.strip()
        if len(t) > 170:
            t = t[:170]
        print(f"L{i}: {t}")
        if i > 4000:
            break
