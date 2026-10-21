# -*- coding: utf-8 -*-
"""dedup_analyze.py — 重算 main_text 去重后的真实指标（修正 F4）。

问题：清华 main_text 9,794 字里有 84.6% 是重复内容。
方法：按行切分、去重后再统计字数。
"""
import json, io, sys, pathlib, re, statistics
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project\runs\extract")


def dedup_text(t):
    """按行/句去重，去掉私有区图标字符与重复行。"""
    if not t:
        return "", 0
    # 去掉 Unicode 私有区字符（图标字体）
    cleaned = re.sub(r"[\ue000-\uf8ff]", "", t)
    lines = [l.strip() for l in cleaned.split("\n")]
    seen = set()
    kept = []
    dup_lines = 0
    for l in lines:
        if not l:
            continue
        key = " ".join(l.split())
        if key in seen:
            dup_lines += 1
            continue
        seen.add(key)
        kept.append(l)
    return " ".join(kept), dup_lines


rows = []
for f in sorted(ROOT.glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    if "result" not in d:
        continue
    r = d["result"]
    raw = r.get("main_text") or ""
    dedup, dup_lines = dedup_text(raw)
    rows.append({
        "slug": d["_site"]["slug"],
        "name": d["_site"]["name"],
        "raw_len": len(raw),
        "dedup_len": len(dedup),
        "dup_lines": dup_lines,
        "inflation_pct": round((1 - len(dedup) / len(raw)) * 100, 1) if raw else 0,
        "text": dedup,
    })

print("=" * 88)
print("main_text 去重分析（按行去重 + 剔除私有区图标字符）")
print("=" * 88)
print(f"{'站点':<14}{'原始字数':>10}{'去重后':>10}{'虚增率':>10}{'重复行数':>10}")
print("-" * 88)
for r in sorted(rows, key=lambda x: -x["inflation_pct"]):
    flag = "  <== 严重" if r["inflation_pct"] > 40 else ""
    print(f"{r['name']:<14}{r['raw_len']:>10}{r['dedup_len']:>10}{r['inflation_pct']:>9.1f}%{r['dup_lines']:>10}{flag}")

rawlens = [r["raw_len"] for r in rows]
dedlens = [r["dedup_len"] for r in rows]
print()
print(f"原始 main_text 中位数 : {statistics.median(rawlens):.0f}")
print(f"去重后中位数          : {statistics.median(dedlens):.0f}")
print(f"中位数变化            : {statistics.median(rawlens) - statistics.median(dedlens):.0f} 字")

heavy = [r for r in rows if r["inflation_pct"] > 40]
print(f"\n虚增 >40% 的站点: {len(heavy)} 个")
for r in heavy:
    print(f"  {r['name']}: {r['raw_len']} -> {r['dedup_len']} ({r['inflation_pct']}%)")

# 去重后「正文为空」的判定是否变化（阈值 200 字）
raw_empty = [r["name"] for r in rows if r["raw_len"] < 200]
ded_empty = [r["name"] for r in rows if r["dedup_len"] < 200]
print(f"\n按 200 字判定正文为空：")
print(f"  原始口径: {raw_empty}")
print(f"  去重口径: {ded_empty}")

out = {
    "method": "按行去重 + 剔除 Unicode 私有区图标字符",
    "sites": [{k: v for k, v in r.items() if k != "text"} for r in rows],
    "median_raw": statistics.median(rawlens),
    "median_dedup": statistics.median(dedlens),
    "heavy_inflation": [{"name": r["name"], "raw": r["raw_len"], "dedup": r["dedup_len"], "pct": r["inflation_pct"]} for r in heavy],
}
(ROOT.parent / "dedup_data.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n已存: {ROOT.parent / 'dedup_data.json'}")
