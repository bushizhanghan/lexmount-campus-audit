#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""analyze.py — 把 runs/extract/*.json 分析成巡检指标表。"""

import json, io, sys, pathlib, re, statistics
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
RUNS = ROOT / "runs" / "extract"

rows = []
for f in sorted(RUNS.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[skip] {f.name}: {e}")
        continue
    site = d.get("_site", {})
    run = d.get("_run", {})
    res = d.get("result", d)
    meta = d.get("metadata", {})

    text = res.get("main_text") or ""
    links = res.get("links") or []

    rows.append({
        "slug": site.get("slug", f.stem),
        "name": site.get("name", f.stem),
        "url": site.get("url", ""),
        "final_url": res.get("final_url", ""),
        "status": res.get("status_code"),
        "title": (res.get("title") or "").strip(),
        "lang": res.get("language") or "",
        "text_len": len(text),
        "link_count": len(links),
        "engine": res.get("engine", ""),
        "server_ms": meta.get("server_elapsed_ms"),
        "wall_ms": run.get("wall_ms"),
        "has_extra_canonical": bool((res.get("extra") or {}).get("canonical_url")),
        "site_name": (res.get("extra") or {}).get("site_name", ""),
        "text_sample": " ".join(text.split())[:120],
    })

if not rows:
    print("没有找到数据")
    sys.exit(1)

def pct(a, b):
    return f"{(a / b * 100):.0f}%" if b else "-"

n = len(rows)
ok = [r for r in rows if r["status"] == 200]
empty = [r for r in ok if r["text_len"] < 200]
no_links = [r for r in ok if r["link_count"] == 0]
no_title = [r for r in ok if not r["title"]]

print("=" * 78)
print(f"高校官网 AI 可读性巡检  —  样本 {n} 个站点，全部经 Lexmount Web Fetch 实际抓取")
print("=" * 78)

print(f"\n【抓取成功率】 200 状态: {len(ok)}/{n} ({pct(len(ok), n)})")
for r in rows:
    if r["status"] != 200:
        print(f"  ✗ {r['name']:<12} status={r['status']}")

print(f"\n【正文提取质量】")
print(f"  提取到正文 (<200 字视为空): {len(ok)-len(empty)}/{len(ok)} ({pct(len(ok)-len(empty), len(ok))})")
if empty:
    print("  ⚠ 正文几乎为空（抓到了 HTML 但提取不出内容）:")
    for r in sorted(empty, key=lambda x: x["text_len"]):
        print(f"     {r['name']:<12} {r['text_len']:>6} 字   final_url={r['final_url']}")
if no_links:
    print(f"  链接解析为空: {len(no_links)} 个 -> " + "、".join(r["name"] for r in no_links))
if no_title:
    print(f"  标题缺失: {len(no_title)} 个 -> " + "、".join(r["name"] for r in no_title))

lens = [r["text_len"] for r in ok]
if lens:
    print(f"\n【正文字数分布】 min={min(lens)}  中位={statistics.median(lens):.0f}  max={max(lens)}")
    print(f"  字数最多: " + "、".join(f"{r['name']}({r['text_len']})" for r in sorted(ok, key=lambda x:-x['text_len'])[:3]))
    print(f"  字数最少: " + "、".join(f"{r['name']}({r['text_len']})" for r in sorted(ok, key=lambda x:x['text_len'])[:3]))

lc = [r["link_count"] for r in ok]
if lc:
    print(f"\n【链接数分布】 min={min(lc)}  中位={statistics.median(lc):.0f}  max={max(lc)}")

print(f"\n【语言标记】 " + ", ".join(f"{k or '(空)'}={v}" for k, v in Counter(r['lang'] for r in ok).most_common()))

print(f"\n【服务端耗时】")
ss = [r["server_ms"] for r in ok if r["server_ms"]]
if ss:
    print(f"  min={min(ss)}ms  中位={statistics.median(ss):.0f}ms  max={max(ss)}ms")
    slow = sorted([r for r in ok if r["server_ms"]], key=lambda x: -x["server_ms"])[:3]
    print("  最慢: " + "、".join(f"{r['name']}({r['server_ms']}ms)" for r in slow))
ww = [r["wall_ms"] for r in ok if r["wall_ms"]]
if ww:
    print(f"  端到端(含浏览器交互) 中位={statistics.median(ww)/1000:.1f}s")

print("\n" + "=" * 78)
print("明细表")
print("=" * 78)
hdr = f"{'站点':<14}{'状态':>5}{'字数':>7}{'链接':>6}{'服务端ms':>10}  标题"
print(hdr)
print("-" * 78)
for r in sorted(rows, key=lambda x: -x["text_len"]):
    print(f"{r['name']:<14}{str(r['status']):>5}{r['text_len']:>7}{r['link_count']:>6}{str(r['server_ms']):>10}  {r['title'][:34]}")

(ROOT / "analysis.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n明细已存: {ROOT / 'analysis.json'}")
