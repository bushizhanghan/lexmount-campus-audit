# -*- coding: utf-8 -*-
"""enrich.py — 汇总新增的三项深度分析，产出 enrich_data.json 供报告使用。

新增发现：
  A. links 返回不完整且不可预测（vs 本地基准）
  B. 云平台 vs 裸抓的增值量化（结构化解构 vs 内容量）
  C. 上交案例：平台丢失正文段落（选择性过滤）
  D. extra 字段 schema 不统一（同一字段三种形态）
"""
import json, io, sys, pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")

links = json.loads((ROOT / "links_groundtruth_final.json").read_text(encoding="utf-8"))
value = json.loads((ROOT / "value_added.json").read_text(encoding="utf-8"))

# --- A. links 完整性 ---
trunc = [r for r in links if r["missing_pct"] > 20]
full = [r for r in links if r["missing_pct"] <= 20]
pcts = [r["missing_pct"] for r in trunc]
import statistics
links_stat = {
    "compared": len(links),
    "truncated": len(trunc),
    "complete": len(full),
    "median_missing_pct": round(statistics.median(pcts), 1) if pcts else 0,
    "max_missing_pct": round(max(pcts), 1) if pcts else 0,
    "min_platform_returned": min(r["platform_uniq"] for r in links),
    "max_platform_returned": max(r["platform_uniq"] for r in links),
    "detail": links,
}

# --- B. 增值量化 ---
ratios = [r["ratio"] for r in value if r["ratio"] > 0]
value_stat = {
    "compared": len(value),
    "ratio_median": round(statistics.median(ratios), 2) if ratios else 0,
    "ratio_min": round(min(ratios), 2) if ratios else 0,
    "ratio_max": round(max(ratios), 2) if ratios else 0,
    "above_1": sum(1 for x in ratios if x > 1),
    "detail": value,
}

# --- D. extra schema 不统一 ---
schema_kinds = {}
for f in sorted((ROOT / "runs" / "extract").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    if "result" not in d:
        continue
    name = d["_site"]["name"]
    extra = d["result"].get("extra")
    if not extra:
        kind = "(无 extra)"
    elif set(extra.keys()) == {"metadata"}:
        kind = "仅 metadata"
    else:
        kind = "dom_summary 家族"
    schema_kinds.setdefault(kind, []).append(name)

# engine 分布与提取质量的交叉
rows = []
for f in sorted((ROOT / "runs" / "extract").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    if "result" not in d:
        continue
    r = d["result"]
    extra = r.get("extra") or {}
    ds = extra.get("dom_summary") or {}
    rows.append({
        "name": d["_site"]["name"],
        "engine": r.get("engine") or "",
        "text_len": len(r.get("main_text") or ""),
        "desc_len": len(((extra.get("metadata") or {}).get("meta_tags") or {}).get("description") or ""),
        "links": len(r.get("links") or []),
        "headings": len(ds.get("headings") or []),
        "paragraphs": len(ds.get("paragraphs") or []),
        "lists": len(ds.get("lists") or []),
        "tables": len(ds.get("tables") or []),
        "forms": len(ds.get("forms") or []),
        "images": len(extra.get("images_detail") or []),
    })

out = {
    "links": links_stat,
    "value": value_stat,
    "schema_kinds": {k: len(v) for k, v in schema_kinds.items()},
    "schema_detail": schema_kinds,
    "sites": rows,
    "meta_desc_ok": sum(1 for r in rows if r["desc_len"] >= 20),
    "meta_desc_total": len(rows),
    "total_links": sum(r["links"] for r in rows),
    "total_images": sum(r["images"] for r in rows),
    "total_headings": sum(r["headings"] for r in rows),
    "total_paragraphs": sum(r["paragraphs"] for r in rows),
    "total_lists": sum(r["lists"] for r in rows),
    "total_tables": sum(r["tables"] for r in rows),
    "total_forms": sum(r["forms"] for r in rows),
}
(ROOT / "enrich_data.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print("=" * 84)
print("新增分析汇总")
print("=" * 84)
print(f"\nA. links 完整性（对比 {links_stat['compared']} 个站点的本地 HTML 基准）")
print(f"   确认丢失(>20%): {links_stat['truncated']}/{links_stat['compared']}")
print(f"   丢失率中位: {links_stat['median_missing_pct']}%  最高: {links_stat['max_missing_pct']}%")
print(f"   平台返回数范围: {links_stat['min_platform_returned']} ~ {links_stat['max_platform_returned']}")

print(f"\nB. 云平台 vs 裸抓（{value_stat['compared']} 个站点）")
print(f"   正文长度比 中位={value_stat['ratio_median']}x  范围 {value_stat['ratio_min']}x~{value_stat['ratio_max']}x")
print(f"   >1 的站点: {value_stat['above_1']}/{value_stat['compared']}")

print(f"\nC. extra 字段 schema 分布")
for k, v in out["schema_kinds"].items():
    print(f"   {k}: {v} 个站点")
print(f"   无 extra: {'、'.join(schema_kinds.get('(无 extra)', []))}")
print(f"   仅 metadata: {'、'.join(schema_kinds.get('仅 metadata', []))}")

print(f"\nD. 平台返回的结构化数据总量")
print(f"   headings={out['total_headings']}  paragraphs={out['total_paragraphs']}  "
      f"lists={out['total_lists']}  tables={out['total_tables']}  forms={out['total_forms']}  "
      f"images={out['total_images']}")
print(f"   meta description 可用: {out['meta_desc_ok']}/{out['meta_desc_total']}")

print(f"\n已存: {ROOT / 'enrich_data.json'}")
