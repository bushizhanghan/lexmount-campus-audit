# -*- coding: utf-8 -*-
"""report.py — 生成可对外发布的巡检报告（HTML）与脱敏摘要。"""
import json, io, sys, pathlib, re, statistics, html as H
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
RUNS = ROOT / "runs"


def load(mode):
    out = []
    d = RUNS / mode
    if not d.exists():
        return out
    for f in sorted(d.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        site = j.get("_site", {})
        run = j.get("_run", {})
        meta = j.get("metadata", {})
        rec = {
            "slug": site.get("slug", f.stem),
            "name": site.get("name", f.stem),
            "url": site.get("url", ""),
            "server_ms": meta.get("server_elapsed_ms"),
            "wall_ms": run.get("wall_ms"),
            "ran_at": run.get("ran_at"),
            "request_id": j.get("request_id"),
            "error": j.get("error"),
        }
        if "result" in j:
            r = j["result"]
            rec.update({
                "ok": True,
                "status": r.get("status_code"),
                "final_url": r.get("final_url"),
                "title": (r.get("title") or "").strip(),
                "main_text": r.get("main_text") or "",
                "links": r.get("links") or [],
                "language": r.get("language") or "",
                "engine": r.get("engine") or "",
            })
        elif "html" in j:
            # /v1/dom/dump 返回扁平结构，不套 result
            rec.update({
                "ok": True,
                "status": j.get("status_code"),
                "final_url": j.get("final_url"),
                "title": "",
                "main_text": "",
                "links": [],
                "language": "",
                "engine": j.get("engine") or "",
                "html": j.get("html") or "",
            })
        else:
            rec["ok"] = False
        out.append(rec)
    return out


def visible_text(h):
    h = re.sub(r"(?s)<script.*?</script>", " ", h)
    h = re.sub(r"(?s)<style.*?</style>", " ", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return " ".join(h.split())


extract = load("extract")
dump = {r["slug"]: r for r in load("dump")}

for r in extract:
    r["text_len"] = len(r.get("main_text", ""))
    r["link_count"] = len(r.get("links", []))

ok = [r for r in extract if r.get("ok")]
failed = [r for r in extract if not r.get("ok")]
empty = [r for r in ok if r["text_len"] < 200]
healthy = [r for r in ok if r["text_len"] >= 200]

lens = [r["text_len"] for r in ok]
med = statistics.median(lens) if lens else 0

# dump 对照
dump_rows = []
for slug, d in dump.items():
    html = d.get("html") or ""
    vt = visible_text(html)
    ext = next((x for x in extract if x["slug"] == slug), None)
    dump_rows.append({
        "slug": slug,
        "name": d["name"],
        "html_len": len(html),
        "visible_len": len(vt),
        "extract_len": ext["text_len"] if ext else None,
        "spa": 'id="root"' in html or 'id="app"' in html,
        "status": d.get("status"),
    })

panics = []
for r in failed:
    e = r.get("error") or {}
    msg = e.get("message") or ""
    m = re.search(r"panicked at ([\w./-]+:\d+:\d+)", msg)
    panics.append({
        "name": r["name"],
        "url": r["url"],
        "code": e.get("code"),
        "stage": e.get("stage"),
        "panic_at": m.group(1) if m else None,
        "assertion": (re.search(r"assertion `([^`]+)` failed", msg) or [None, None])[1]
        if "assertion" in msg else None,
        "message": msg.split("\n")[0][:200],
    })

stats = {
    "total": len(extract),
    "ok": len(ok),
    "failed": len(failed),
    "empty": len(empty),
    "healthy": len(healthy),
    "median_len": med,
    "dump_count": len(dump_rows),
    "ran_at": extract[0]["ran_at"] if extract else None,
}

(ROOT / "report_data.json").write_text(
    json.dumps({"stats": stats, "sites": extract, "dump": dump_rows, "panics": panics},
               ensure_ascii=False, indent=2), encoding="utf-8")

print(f"统计: {stats}")
print(f"panic 案例: {len(panics)}")
for p in panics:
    print(f"  - {p['name']}: {p['code']} @ {p['panic_at']}")
print(f"SPA 案例（dump 可见文字 <200）: ")
for d in dump_rows:
    if d["visible_len"] < 200:
        print(f"  - {d['name']}: html={d['html_len']} 但可见文字仅 {d['visible_len']}")
