# -*- coding: utf-8 -*-
"""build_v4_data.py — v4 数据汇总：整合审计意见后的最终数据。

相对 v3 的修正（依据 method-auditor 的 t4 审计）：
  - 撤掉「3,400 倍差距」（UI 口径伪影，API 基线是 13.5 倍）
  - 新增 JS 源码污染分析（浙大 70%）
  - 新增 CB「以链接换正文」的取舍分析（不写「全面更好」）
  - 强调人大+哈工大双站双驱动的 panic 对照
  - 记录「能证明/不能证明」的分界
"""
import json
import io
import sys
import pathlib
import statistics
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
D = json.loads((ROOT / "v3_data.json").read_text(encoding="utf-8"))

JS = json.loads((ROOT / "js_pollution.json").read_text(encoding="utf-8"))

api_rows = D["api_rows"]
ui_rows = D["ui_rows"]
cb = D["cb"]
stab = D["stability"]

ok_api = [r for r in api_rows if r["ok"]]
fail_api = [r for r in api_rows if not r["ok"]]

# ---------- 纯净正文（剔除 JS 后）----------
js_map = {r["slug"]: r for r in JS["sites"]}
for r in api_rows:
    j = js_map.get(r["slug"])
    r["clean_len"] = j["clean"] if j else (r["text_len"] if r["ok"] else 0)
    r["js_pct"] = j["js_pct"] if j else 0

ok_api = [r for r in api_rows if r["ok"]]
clean_lens = [r["clean_len"] for r in ok_api]

# ---------- CB 取舍分析 ----------
cb_map = {c["slug"]: c for c in cb}
cb_cmp = []
for r in ok_api:
    c = cb_map.get(r["slug"])
    if not c or not c.get("ok"):
        continue
    cb_cmp.append({
        "name": r["name"],
        "api_len": r["text_len"],
        "cb_len": c["textLen"],
        "len_diff": c["textLen"] - r["text_len"],
        "api_links": r["links"],
        "cb_links": c["linkCount"],
        "link_diff": c["linkCount"] - r["links"],
    })

cb_more_text = [x for x in cb_cmp if x["len_diff"] > 0]
cb_less_text = [x for x in cb_cmp if x["len_diff"] < 0]
cb_more_links = [x for x in cb_cmp if x["link_diff"] > 0]

# ---------- 跨批次不一致（回应审计「别说平台输出稳定」）----------
# 同站点在 UI / API 两次抓取差异
cross = []
for r in api_rows:
    u = ui_rows.get(r["slug"])
    if not u or not r["ok"]:
        continue
    d = r["text_len"] - u["text_len"]
    if abs(d) > 200:
        cross.append({"name": r["name"], "ui": u["text_len"], "api": r["text_len"], "diff": d})

# ---------- panic 双站双驱动 ----------
panic_slugs = {r["slug"] for r in fail_api}

summary = dict(D)  # 继承 v3
summary.update({
    "js_pollution": JS,
    "cb_tradeoff": {
        "compared": len(cb_cmp),
        "cb_more_text": len(cb_more_text),
        "cb_less_text": len(cb_less_text),
        "cb_more_links": len(cb_more_links),
        "api_median_len": statistics.median([x["api_len"] for x in cb_cmp]) if cb_cmp else 0,
        "cb_median_len": statistics.median([x["cb_len"] for x in cb_cmp]) if cb_cmp else 0,
        "api_median_links": statistics.median([x["api_links"] for x in cb_cmp]) if cb_cmp else 0,
        "cb_median_links": statistics.median([x["cb_links"] for x in cb_cmp]) if cb_cmp else 0,
        "detail": cb_cmp,
    },
    "cross_batch": cross,
    "clean_stats": {
        "median": statistics.median(clean_lens) if clean_lens else 0,
        "max": max(clean_lens) if clean_lens else 0,
        "min": min(clean_lens) if clean_lens else 0,
        "ratio": round(max(clean_lens) / max(min(clean_lens), 1), 1) if clean_lens else 0,
    },
    "panic_sites": sorted(panic_slugs),
    "cb_fixed_panic": [c["name"] for c in cb if c.get("ok") and c["slug"] in panic_slugs],
})

(ROOT / "v4_data.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

print("=" * 88)
print("v4 数据汇总")
print("=" * 88)
print(f"\n【API 基线】{len(ok_api)}/{len(api_rows)} 成功, 失败 {len(fail_api)}")
print(f"  正文中位 {statistics.median([r['text_len'] for r in ok_api]):.0f}")
print(f"  纯净正文中位 {summary['clean_stats']['median']:.0f}")
print(f"  纯净后最大/最小倍数: {summary['clean_stats']['ratio']}x")

print(f"\n【JS 污染】{JS['polluted_count']} 站受影响, 总体 {JS['total_js_pct']}%")
for r in JS["sites"]:
    if r["js_pct"] > 5:
        print(f"  {r['name']}: {r['total']:,} -> 纯净 {r['clean']:,} ({r['js_pct']}% 是 JS)")

print(f"\n【CB 取舍】对比 {len(cb_cmp)} 站")
print(f"  正文: API 中位 {summary['cb_tradeoff']['api_median_len']:.0f} vs CB 中位 {summary['cb_tradeoff']['cb_median_len']:.0f}")
print(f"  链接: API 中位 {summary['cb_tradeoff']['api_median_links']:.0f} vs CB 中位 {summary['cb_tradeoff']['cb_median_links']:.0f}")
print(f"  CB 正文更多: {len(cb_more_text)} 站 / 更少: {len(cb_less_text)} 站")
print(f"  CB 链接更多: {len(cb_more_links)} 站")

print(f"\n【跨批次不一致（>200 字）】{len(cross)} 站")
for c in sorted(cross, key=lambda x: -abs(x["diff"]))[:6]:
    print(f"  {c['name']}: UI {c['ui']:,} -> API {c['api']:,} ({c['diff']:+,})")

print(f"\n【panic 双站双驱动】{sorted(panic_slugs)}")
print(f"  在 Cloud Browser 下全部恢复: {summary['cb_fixed_panic']}")

print(f"\n已存: {ROOT / 'v4_data.json'}")
