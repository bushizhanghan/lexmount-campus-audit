# -*- coding: utf-8 -*-
"""compare_ui_vs_api.py — 对比 UI 抓取与官方 API 抓取的差异。

这是本次最重要的诚实性检查：如果两种方式结果不同，
说明之前的结论受影响于驱动方式，必须以 API 为准。
"""
import json
import io
import sys
import pathlib
import statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")


def load_dir(d):
    out = {}
    p = ROOT / d
    if not p.exists():
        return out
    for f in p.glob("*.json"):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        site = j.get("_site") or {}
        slug = site.get("slug") or f.stem
        res = j.get("result") or {}
        out[slug] = {
            "name": site.get("name", f.stem),
            "ok": j.get("_ok", "result" in j),
            "status": res.get("status_code") or j.get("status_code"),
            "text_len": len(res.get("main_text") or ""),
            "links": len(res.get("links") or []),
            "server_ms": (j.get("metadata") or {}).get("server_elapsed_ms"),
            "rid": j.get("request_id"),
            "error": (j.get("error") or {}).get("code"),
        }
    return out


ui = load_dir("runs/extract")
api = load_dir("runs/api/extract")

print("=" * 100)
print("UI 抓取 vs 官方 API 抓取：同站点对比")
print("=" * 100)
print(f"{'站点':<14}{'UI正文':>9}{'API正文':>9}{'差异':>10}{'UI链接':>8}{'API链接':>8}  判定")
print("-" * 100)

big_change = []
for slug, a in sorted(api.items(), key=lambda x: -(x[1]["text_len"] or 0)):
    u = ui.get(slug)
    if not u:
        print(f"{a['name']:<14}{'-':>9}{a['text_len']:>9}{'':>10}{'-':>8}{a['links']:>8}  (UI无数据)")
        continue
    diff = a["text_len"] - u["text_len"]
    flag = ""
    if abs(diff) > 500:
        flag = "  <== 显著变化"
        big_change.append((a["name"], u["text_len"], a["text_len"], diff))
    print(f"{a['name']:<14}{u['text_len']:>9}{a['text_len']:>9}{diff:>+10}"
          f"{u['links']:>8}{a['links']:>8}{flag}")

print()
ui_ok = [v for v in ui.values() if v["ok"]]
api_ok = [v for v in api.values() if v["ok"]]
print("=" * 100)
print(f"UI  成功率: {len(ui_ok)}/{len(ui)}   正文字数中位: {statistics.median([v['text_len'] for v in ui_ok]):.0f}")
print(f"API 成功率: {len(api_ok)}/{len(api)}   正文字数中位: {statistics.median([v['text_len'] for v in api_ok]):.0f}")

print()
print("空正文站点（<200 字）：")
print(f"  UI : {[v['name'] for v in ui_ok if v['text_len'] < 200]}")
print(f"  API: {[v['name'] for v in api_ok if v['text_len'] < 200]}")

print()
print("失败站点：")
print(f"  UI : {[v['name'] for v in ui.values() if not v['ok']]}")
print(f"  API: {[(v['name'], v['error'], v['status']) for v in api.values() if not v['ok']]}")

print()
print("=" * 100)
print("显著变化的站点（差异 > 500 字）")
print("=" * 100)
for name, ul, al, d in big_change:
    print(f"  {name:<14} {ul:>7} -> {al:>7}  ({d:+d})")
