# -*- coding: utf-8 -*-
"""factcheck_v4.py — v4 报告与投稿材料的全量核对。

改进点（相对 v3）：
  - 覆盖 v4 新增的 JS 污染、CB 取舍、跨批次不一致
  - 显式检查「已撤回的错误结论」不再出现
"""
import json
import io
import sys
import pathlib
import re
import statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
D = json.loads((ROOT / "v4_data.json").read_text(encoding="utf-8"))
HTML = (ROOT.parent / "report.html").read_text(encoding="utf-8")
SUB = (ROOT.parent / "SUBMISSION.md").read_text(encoding="utf-8")

B = D["api_baseline"]
api_rows = D["api_rows"]
ui_rows = D["ui_rows"]
stab = D["stability"]
cb = D["cb"]
JS = D["js_pollution"]
TRADE = D["cb_tradeoff"]
CROSS = D["cross_batch"]
CLEAN = D["clean_stats"]
dedup = D["dedup"]

checks = []


def ck(label, value, target="html"):
    s = value if isinstance(value, str) else f"{value}"
    src = {"html": HTML, "sub": SUB, "both": HTML + SUB}[target] if target != "both" else HTML + SUB
    present = s in src
    checks.append((label, s, present))
    return present


# ---- 基线 ----
ck("API 成功数", B["ok"])
ck("API 失败数", B["fail"])
ck("正文中位", f"{B['median_len']:.0f}")
ck("正文最大", f"{B['max_len']:,}")
ck("正文最小", f"{B['min_len']:,}")
ck("纯净正文中位", f"{CLEAN['median']:.0f}", "both")

# ---- 稳定性 ----
stable_ct = sum(1 for s in stab if s.get("cv_pct", 0) == 0)
ck("稳定站点数", stable_ct)
ck("稳定性总数", len(stab))
for s in stab:
    if s.get("cv_pct", 0) > 5 and s.get("len_min") is not None:
        ck(f"波动-{s['name']}-范围", f"{s['len_min']:,}~{s['len_max']:,}")

# ---- CB ----
cb_ok = sum(1 for c in cb if c.get("ok"))
ck("CB 成功数", cb_ok)
ck("CB 取舍-正文中位", f"{TRADE['cb_median_len']:.0f}", "both")
ck("CB 取舍-API正文中位", f"{TRADE['api_median_len']:.0f}", "both")
ck("CB 取舍-链接中位", f"{TRADE['cb_median_links']:.0f}", "both")
ck("CB 取舍-API链接中位", f"{TRADE['api_median_links']:.0f}", "both")
ck("CB 正文更少站数", TRADE["cb_less_text"], "both")

# ---- JS 污染 ----
for r in JS["sites"]:
    if r["js_pct"] > 5:
        ck(f"JS-{r['name']}-总长", f"{r['total']:,}", "both")
        ck(f"JS-{r['name']}-JS字符", f"{r['js_chars']:,}", "both")
        ck(f"JS-{r['name']}-纯净", f"{r['clean']:,}", "both")
        ck(f"JS-{r['name']}-比例", f"{r['js_pct']:.0f}%")

# ---- 跨批次 ----
ck("跨批次站数", len(CROSS), "both")
top = sorted(CROSS, key=lambda x: -abs(x["diff"]))[:6]
for c in top:
    ck(f"跨批次-{c['name']}-UI", f"{c['ui']:,}" if c["ui"] >= 1000 else str(c["ui"]), "both")
    ck(f"跨批次-{c['name']}-API", f"{c['api']:,}", "both")

# ---- 去重 ----
for s in dedup.get("sites", []):
    if s["inflation_pct"] > 40:
        ck(f"去重-{s['name']}-原始", f"{s['raw_len']:,}", "both")
        ck(f"去重-{s['name']}-去后", f"{s['dedup_len']:,}", "both")
        ck(f"去重-{s['name']}-比例", f"{s['inflation_pct']}")

# ---- panic ----
panic_lines = set(r["panic_at"] for r in api_rows if not r["ok"] and r["panic_at"])
ck("panic 位置", list(panic_lines)[0] if len(panic_lines) == 1 else "MULTI", "both")

# ---- 已撤回的错误结论必须不存在 ----
# 注意：第 11 章有"我撤回过什么"的自我记录，会合法提到这些字符串。
# 所以检测时要排除该段落，只检查正文其它部分。
withdraw_sec = ""
marker = "撤回过自己的错误结论"
if marker in HTML:
    i = HTML.index(marker)
    withdraw_sec = HTML[i:i + 1200]
HTML_BODY = HTML.replace(withdraw_sec, "") if withdraw_sec else HTML

WITHDRAWN = [
    ("3,400 倍差距", "3,400 倍"),
    ("dcl 引擎正文更短", "渲染引擎正文反而更短"),
    ("两个站点可稳定复现", "两个站点可稳定复现 panic"),
]
print("=" * 94)
print("已撤回结论检查（排除第 11 章的自我记录段落）")
print("=" * 94)
withdraw_ok = True
for label, s in WITHDRAWN:
    in_body = s in HTML_BODY
    in_sub = s in SUB
    if in_body or in_sub:
        withdraw_ok = False
    print(f"  {label:<24} 正文:{'仍存在 ✗' if in_body else '已删除 ✓':<12} "
          f"投稿:{'仍存在 ✗' if in_sub else '已删除 ✓'}")

# ---- 输出 ----
print()
print("=" * 94)
print(f"{'核对项':<38}{'值':>18}   状态")
print("=" * 94)
bad = 0
for label, val, present in checks:
    if not present:
        bad += 1
    print(f"{label:<38}{val:>18}   {'✓' if present else '✗ 缺失'}")

print()
print("=" * 94)
print(f"共核对 {len(checks)} 项，{len(checks)-bad} 项通过，{bad} 项缺失")
print("结论:", "全部一致 ✓" if bad == 0 else f"{bad} 项需检查 ✗")
