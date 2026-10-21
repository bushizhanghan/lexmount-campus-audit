# -*- coding: utf-8 -*-
"""probe_consts.py — 提取 provider 常量。"""
import io
import pathlib
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LIB = pathlib.Path(r"C:\Users\1\.dsh\profiles\desktop\node_modules\dsh-workbuddy\lib")
NAMES = [
    "WORKBUDDY_PROVIDER", "WORKBUDDY_CN_PROVIDER",
    "WORKBUDDY_DISPLAY_NAME", "WORKBUDDY_CN_DISPLAY_NAME",
    "WORKBUDDY_SETTINGS_NS",
]

for f in ["index.js", "host-heartbeat-BLiKF_E0.js"]:
    p = LIB / f
    if not p.exists():
        continue
    src = p.read_text(encoding="utf-8", errors="replace")
    print("=" * 76)
    print(f)
    for name in NAMES:
        # 只匹配赋值语句，值抓到 ; 或换行为止
        pat = re.compile(r"\b" + name + r"\s*=\s*(.+?)(?:;|\n)")
        m = pat.search(src)
        if m:
            v = m.group(1).strip()
            print(f"  {name:<26} = {v[:120]}")
    # 也找 import/export 里的
    for name in NAMES:
        if re.search(r"\b" + name + r"\b", src) and not re.search(
                r"\b" + name + r"\s*=", src):
            print(f"  {name:<26} (仅引用)")
    print()
