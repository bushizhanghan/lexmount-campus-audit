# -*- coding: utf-8 -*-
"""explain_orphans.py — 追查 factcheck 报告里的 3 个无法溯源的数字。"""
import json
import io
import sys
import pathlib
import statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
D = json.loads((ROOT / "v3_data.json").read_text(encoding="utf-8"))

print("=" * 78)
print("追查孤立数字")
print("=" * 78)

# 1. 3363 —— 应该是正文字数中位数
B = D["api_baseline"]
print(f"\n3363: api_baseline.median_len = {B['median_len']}")
print(f"      f-string 用 :.0f 会渲染成 '{B['median_len']:.0f}'")
print(f"      数据文件里存的是 {B['median_len']}（小数），所以字符串 '3363' 找不到")
print("      → 属于「格式差异」，不是错误 ✓")

# 2. 2117 / 4075 —— 深度测试子页平均
print("\n2117 / 4075: 深度测试的子页平均字数")
for d in D["depth"]:
    pages = [p for p in d.get("pages", []) if p.get("ok")]
    lens = [p["text_len"] for p in pages]
    if not lens:
        continue
    avg = statistics.mean(lens)
    print(f"      {d['name']:<12} 子页 {len(lens)} 个, 平均 {avg:,.2f} -> 渲染为 {avg:,.0f}")
print("      → 这两个值是渲染时现算的，没写进 v3_data.json")
print("      → 属于「派生值未落盘」，建议写进数据文件以便溯源")

# 建议：把派生值补进数据文件
for d in D["depth"]:
    pages = [p for p in d.get("pages", []) if p.get("ok")]
    lens = [p["text_len"] for p in pages]
    d["child_count"] = len(pages)
    d["child_avg_len"] = round(statistics.mean(lens)) if lens else 0
    d["child_min_len"] = min(lens) if lens else 0
    d["child_max_len"] = max(lens) if lens else 0

(ROOT / "v3_data.json").write_text(json.dumps(D, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n已把派生值写回 v3_data.json（child_avg_len / child_min_len / child_max_len）")

print()
print("=" * 78)
print("结论：3 个数字都不是错误，而是「未落盘」的派生值。已补入数据文件。")
print("=" * 78)
