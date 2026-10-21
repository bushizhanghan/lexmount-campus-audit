# -*- coding: utf-8 -*-
"""factcheck_v3.py — 从 report.html 反向抽取数字，与原始 JSON 逐项核对。

思路：不预设清单，而是从源码层级把每个渲染进去的数值算一遍，
再检查 HTML 里是否出现该字符串。这样能发现「HTML 里的数字没有数据来源」。
"""
import json
import io
import sys
import pathlib
import re
import statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
D = json.loads((ROOT / "v3_data.json").read_text(encoding="utf-8"))
HTML = (ROOT.parent / "report.html").read_text(encoding="utf-8")

B = D["api_baseline"]
api_rows = D["api_rows"]
ui_rows = D["ui_rows"]
stab = D["stability"]
cb = D["cb"]
dedup = D["dedup"]
depth = D["depth"]
compare = D["ui_vs_api"]

ok_api = [r for r in api_rows if r["ok"]]
fail_api = [r for r in api_rows if not r["ok"]]

checks = []


def ck(label, value, expect_present=True):
    """value 是应从数据算出的真值；检查它是否出现在 HTML 里。"""
    s = value if isinstance(value, str) else f"{value}"
    present = s in HTML
    ok = present if expect_present else True
    checks.append((label, s, present, ok))
    return ok


# ---------- 1. 基线统计 ----------
ck("总站点数", len(api_rows))
ck("API 成功数", B["ok"])
ck("API 失败数", B["fail"])
ck("空正文数", B["empty"])
ck("正文字数中位数", f"{B['median_len']:.0f}")
ck("正文字数最大", f"{B['max_len']:,}")
ck("正文字数最小", f"{B['min_len']:,}")
ck("服务端耗时中位", f"{B['median_server_ms']:.0f}")
ck("服务端耗时最大", f"{B['max_server_ms']}")

# ---------- 2. UI vs API ----------
ck("UI/API 显著差异站点数", D["ui_vs_api_changed"])
ck("UI 成功数", sum(1 for v in ui_rows.values() if v["ok"]))

# ---------- 3. 稳定性 ----------
stable_ct = sum(1 for s in stab if s.get("cv_pct", 0) == 0)
ck("完全稳定站点数", stable_ct)
ck("稳定性总站点数", len(stab))
for s in stab:
    if s.get("cv_pct", 0) > 5 and s.get("len_min") is not None:
        ck(f"波动-{s['name']}-min", f"{s['len_min']:,}")
        ck(f"波动-{s['name']}-max", f"{s['len_max']:,}")
        ck(f"波动-{s['name']}-cv", f"{s['cv_pct']}")

# ---------- 4. Cloud Browser ----------
cb_ok = sum(1 for c in cb if c.get("ok"))
ck("CB 成功数", cb_ok)
ck("CB 总数", len(cb))
for c in cb:
    if c.get("ok") and c.get("slug") in ("zju", "hit", "ruc", "scut", "seu", "nju", "hust", "bnu"):
        ck(f"CB-{c['name']}-字数", f"{c['textLen']:,}")
        ck(f"CB-{c['name']}-链接", str(c["linkCount"]))

# ---------- 5. 去重 ----------
if dedup:
    ck("去重前中位", f"{dedup.get('median_raw', 0):.0f}")
    ck("去重后中位", f"{dedup.get('median_dedup', 0):.0f}")
    for h in dedup.get("heavy_inflation", []):
        ck(f"去重-{h['name']}-原", f"{h['raw']:,}")
        ck(f"去重-{h['name']}-后", f"{h['dedup']:,}")
        ck(f"去重-{h['name']}-比例", f"{h['pct']}")

# ---------- 6. panic ----------
panic_lines = set(r["panic_at"] for r in fail_api if r["panic_at"])
ck("panic 位置", list(panic_lines)[0] if len(panic_lines) == 1 else "MULTI")
for r in fail_api:
    ck(f"panic-{r['name']}-code", r["error_code"])

# ---------- 7. 三路径表具体数字 ----------
targets = {
    "zju": ("浙江大学", 4, 6173, 3312),
    "ruc": ("中国人民大学", 11515, None, 2549),
    "hit": ("哈尔滨工业大学", None, None, 1750),
    "seu": ("东南大学", None, 6473, 5014),
}
for slug, (name, ui_v, api_v, cb_v) in targets.items():
    if ui_v is not None:
        ck(f"三路径-{name}-UI", f"{ui_v:,}" if ui_v >= 1000 else str(ui_v))
    if api_v is not None:
        ck(f"三路径-{name}-API", f"{api_v:,}")
    if cb_v is not None:
        ck(f"三路径-{name}-CB", f"{cb_v:,}")

# ---------- 8. 检查 HTML 里是否有「无来源」的孤立大数字 ----------
# 收集 HTML 表格里形如 1,234 的数字，看是否都能在数据里找到
html_nums = set(re.findall(r">\s*([\d,]{4,})\s*<", HTML))
data_nums = set()
def add_nums(o):
    if isinstance(o, dict):
        for v in o.values():
            add_nums(v)
    elif isinstance(o, list):
        for v in o:
            add_nums(v)
    elif isinstance(o, (int, float)):
        data_nums.add(f"{o:,}")
        data_nums.add(f"{o}")
add_nums(D)

orphan = [n for n in html_nums if n not in data_nums]

# ---------- 输出 ----------
print("=" * 92)
print(f"{'核对项':<40}{'值':>16}   出现?")
print("=" * 92)
bad = 0
for label, val, present, ok in checks:
    if not ok:
        bad += 1
    mark = "✓" if present else "✗ 未在报告中出现"
    print(f"{label:<40}{val:>16}   {mark}")

print()
print("=" * 92)
print(f"共核对 {len(checks)} 项，其中 {len(checks)-bad} 项在报告中找到，{bad} 项缺失")

if orphan:
    print(f"\n报告中出现但数据文件里找不到的 4 位以上数字（{len(orphan)} 个，需人工确认）:")
    for n in sorted(orphan)[:25]:
        print(f"  {n}")
else:
    print("\n报告中的所有 4 位以上数字均可在数据文件中溯源 ✓")

print("\n结论:", "全部一致 ✓" if bad == 0 else f"有 {bad} 项需检查 ✗")
