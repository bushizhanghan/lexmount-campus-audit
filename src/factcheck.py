# -*- coding: utf-8 -*-
"""factcheck.py — 逐条核对报告里的每个数字是否与原始 JSON 一致。"""
import json, io, sys, pathlib, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")

sites = json.loads((ROOT / "sites.json").read_text(encoding="utf-8"))["sites"]
print(f"样本清单: {len(sites)} 条")

extract_files = sorted((ROOT / "runs" / "extract").glob("*.json"))
dump_files = sorted((ROOT / "runs" / "dump").glob("*.json"))
print(f"extract 原始响应: {len(extract_files)} 份")
print(f"dump    原始响应: {len(dump_files)} 份")

ok = failed = 0
total_text = 0
lens, mss = [], []
empty_names, fail_names = [], []

for f in extract_files:
    d = json.loads(f.read_text(encoding="utf-8"))
    name = d.get("_site", {}).get("name", f.stem)
    if "result" in d:
        ok += 1
        r = d["result"]
        L = len(r.get("main_text") or "")
        total_text += L
        lens.append(L)
        ms = d.get("metadata", {}).get("server_elapsed_ms")
        if ms:
            mss.append(ms)
        if L < 200:
            empty_names.append((name, L))
    else:
        failed += 1
        fail_names.append((name, (d.get("error") or {}).get("code")))

print()
print("=" * 66)
print("核对项                                 报告值        实测值     结果")
print("=" * 66)

def check(label, reported, actual):
    good = str(reported) == str(actual)
    print(f"{label:<36}{str(reported):<14}{str(actual):<11}{'✓' if good else '✗ 不一致'}")
    return good

allgood = True
allgood &= check("总样本数", 20, len(extract_files))
allgood &= check("HTTP 200 数", 18, ok)
allgood &= check("引擎异常数", 2, failed)
allgood &= check("正文为空数(<200字)", 2, len(empty_names))
allgood &= check("正文正常数(>=200字)", 16, ok - len(empty_names))

import statistics
med = statistics.median(lens)
print(f"{'正文字数中位数':<36}{'3398':<14}{med:<11.0f}{'✓' if abs(med-3398)<2 else '✗'}")
allgood &= abs(med - 3398) < 2

print(f"{'正文字数最大值':<36}{'13751':<14}{max(lens):<11}{'✓' if max(lens)==13751 else '✗'}")
print(f"{'正文字数最小值':<36}{'4':<14}{min(lens):<11}{'✓' if min(lens)==4 else '✗'}")
allgood &= (max(lens) == 13751 and min(lens) == 4)

msmed = statistics.median(mss)
print(f"{'服务端耗时中位数(ms)':<36}{'~1000':<14}{msmed:<11.0f}{'✓' if 900<msmed<1100 else '✗'}")
print(f"{'服务端耗时最大(ms)':<36}{'6234':<14}{max(mss):<11}{'✓' if max(mss)==6234 else '✗'}")
allgood &= (900 < msmed < 1100 and max(mss) == 6234)

# 13,751 / 4 = 3437.75 -> 报告写"3,400 倍"
ratio = max(lens) / min(lens)
print(f"{'最大/最小 倍数':<36}{'~3400':<14}{ratio:<11.0f}{'✓' if 3300<ratio<3500 else '✗'}")
allgood &= (3300 < ratio < 3500)

print()
print("空正文站点:", empty_names)
print("引擎异常站点:", fail_names)

# 校名核对
reported_empty = {"浙江大学": 4, "华南理工大学": 6}
actual_empty = dict(empty_names)
print("空正文校名是否一致:", "✓" if actual_empty == reported_empty else f"✗ {actual_empty}")

# panic 行号核对
panic_lines = set()
for f in extract_files:
    d = json.loads(f.read_text(encoding="utf-8"))
    msg = (d.get("error") or {}).get("message") or ""
    m = re.search(r"panicked at ([\w./-]+:\d+:\d+)", msg)
    if m:
        panic_lines.add(m.group(1))
print("panic 位置:", panic_lines)
allgood &= panic_lines == {"moli-renderer-v8/src/live_document_parser.rs:498:9"}

print()
print("=" * 66)
print("总体结论:", "所有数字均与原始数据一致 ✓" if allgood else "存在不一致，需修正 ✗")
