#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
audit.py — 高校官网 AI 可读性巡检 CLI

对一批站点跑「三路径」巡检，输出可核验的 JSON + 人类可读报告。

三种路径：
  api   官方 API      POST https://api.lexmount.cn/v1/extract   (需 X-API-Key + X-Project-Id)
  cb     Cloud Browser  /playground 注入 Playwright，渲染后读 DOM
  ui     UI 表单       驱动 /playground/webfetch 表单

用法示例：
  # 只跑官方 API（最常用）
  python audit.py --sites sites.json --path api --key $env:LEXMOUNT_KEY --project <PID>

  # 三路径全跑 + 每站重复 3 次
  python audit.py --sites sites.json --path all --repeat 3 --out runs/audit

  # 从已落盘数据重放（不发请求，用于改报告/复盘）
  python audit.py --replay runs/audit --out report.html

输出：
  <out>/<path>/<slug>.json     每个站点每次请求的完整响应（含 request_id）
  <out>/summary.json           汇总统计
  <out>/report.html            人类可读报告（含三路径对照表）
"""
from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import os
import pathlib
import statistics
import sys
import time
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

API_BASE = "https://api.lexmount.cn"
ENDPOINT = "/v1/extract"
PROJECT_DEFAULT = os.environ.get("LEXMOUNT_PROJECT_ID", "")


# ---------------------------------------------------------------- 基础工具
def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def jdump(obj, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def jload(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_sites(path: pathlib.Path) -> list[dict]:
    d = jload(path)
    if not d:
        raise SystemExit(f"无法读取站点清单: {path}")
    sites = d.get("sites") if isinstance(d, dict) else d
    if not sites:
        raise SystemExit(f"站点清单为空: {path}")
    for i, s in enumerate(sites):
        if "slug" not in s or "url" not in s:
            raise SystemExit(f"第 {i} 个站点缺少 slug/url: {s}")
    return sites


# ---------------------------------------------------------------- 抓取实现
def fetch_api(url: str, key: str, project: str, timeout: int = 120) -> dict:
    """官方 API 路径。返回带 _request 元信息的记录。"""
    body = json.dumps({"extract": {"url": url}}).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "audit-cli/1.0",
        "X-API-Key": key,
        "X-Project-Id": project,
    }
    req = urllib.request.Request(API_BASE + ENDPOINT, data=body,
                                 headers=headers, method="POST")
    t0 = time.time()
    rec = {"_site": None, "_request": {
        "method": "POST", "endpoint": API_BASE + ENDPOINT,
        "headers": {**headers, "X-API-Key": "***redacted***"},
        "body": {"extract": {"url": url}},
        "sent_at": now_iso(),
    }}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            rec["_request"]["http_status"] = r.status
            rec["_request"]["wall_ms"] = round((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        rec["_request"]["http_status"] = e.code
        rec["_request"]["wall_ms"] = round((time.time() - t0) * 1000)
    except Exception as e:
        rec["_request"]["http_status"] = 0
        rec["_request"]["wall_ms"] = round((time.time() - t0) * 1000)
        rec["_request"]["client_error"] = f"{type(e).__name__}: {e}"
        rec["_ok"] = False
        return rec

    try:
        parsed = json.loads(raw)
    except Exception:
        rec["_raw"] = raw[:2000]
        rec["_ok"] = False
        return rec

    rec.update(parsed)
    rec["_ok"] = ("result" in parsed) or ("html" in parsed)
    return rec


def _flatten(rec: dict) -> dict:
    """把一条记录压成汇总用的一行。兼容有/无 _ok 字段的历史数据。"""
    res = rec.get("result") or {}
    err = rec.get("error") or {}
    meta = rec.get("metadata") or {}
    req = rec.get("_request") or {}
    # 历史数据可能没有 _ok 字段，推断是否有 result 或 html
    has_payload = bool(res) or bool(rec.get("html"))
    ok = bool(rec.get("_ok", has_payload))
    panic = None
    msg = err.get("message") or ""
    if "panicked at " in msg:
        panic = msg.split("panicked at ", 1)[1].split(":", 1)[0].rsplit(":", 2)[0]
    return {
        "ok": ok,
        "http": req.get("http_status"),
        "status": res.get("status_code"),
        "title": (res.get("title") or "").strip(),
        "text_len": len(res.get("main_text") or ""),
        "links": len(res.get("links") or []),
        "server_ms": meta.get("server_elapsed_ms"),
        "wall_ms": req.get("wall_ms"),
        "rid": rec.get("request_id"),
        "engine": res.get("engine"),
        "error_code": err.get("code"),
        "panic_at": panic,
        "fetched_at": res.get("fetched_at"),
    }


# ---------------------------------------------------------------- 汇总
def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["ok"]]
    fail = [r for r in rows if not r["ok"]]
    lens = [r["text_len"] for r in ok]
    srv = [r["server_ms"] for r in ok if r["server_ms"]]
    return {
        "total": len(rows),
        "ok": len(ok),
        "fail": len(fail),
        "empty": sum(1 for r in ok if r["text_len"] < 200),
        "median_len": statistics.median(lens) if lens else 0,
        "min_len": min(lens) if lens else 0,
        "max_len": max(lens) if lens else 0,
        "median_server_ms": statistics.median(srv) if srv else 0,
        "max_server_ms": max(srv) if srv else 0,
        "failed_sites": [{"slug": r["slug"], "name": r["name"],
                          "error_code": r["error_code"], "panic_at": r["panic_at"]}
                         for r in fail],
        "panic_locations": sorted({r["panic_at"] for r in fail if r["panic_at"]}),
    }


def stability(per_site: dict[str, list[dict]]) -> list[dict]:
    """每站多次抓取的一致性。"""
    out = []
    for slug, runs in per_site.items():
        oks = [r for r in runs if r["ok"]]
        lens = [r["text_len"] for r in oks]
        if lens:
            mean = statistics.mean(lens) or 1
            cv = round(statistics.pstdev(lens) / mean * 100, 1) if len(lens) > 1 else 0.0
        else:
            cv = 0.0
        out.append({
            "slug": slug,
            "name": runs[0]["name"] if runs else slug,
            "times": len(runs),
            "success": len(oks),
            "len_min": min(lens) if lens else None,
            "len_max": max(lens) if lens else None,
            "len_range": (max(lens) - min(lens)) if lens else None,
            "cv_pct": cv,
        })
    return sorted(out, key=lambda x: -x["cv_pct"])


# ---------------------------------------------------------------- 报告
CSS = """
:root{--bg:#0b0e14;--panel:#141922;--line:#28313f;--fg:#e6edf7;--dim:#8b98ab;
--accent:#7ee787;--warn:#f0b429;--err:#ff6b6b;--blue:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:44px 24px 80px}
h1{font-size:30px;margin:0 0 8px;letter-spacing:-.02em}
h2{font-size:20px;margin:38px 0 10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.sub{color:var(--dim);margin:0 0 20px}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:13.5px}
th,td{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.name{font-weight:600;white-space:nowrap}
tr:hover td{background:#10161f}
code{background:var(--panel);padding:2px 6px;border-radius:4px;
font:13px/1.5 ui-monospace,Menlo,Consolas,monospace;color:#ffd580}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:600}
.pill.ok{color:var(--accent);background:rgba(126,231,135,.11)}
.pill.warn{color:var(--warn);background:rgba(240,180,41,.11)}
.pill.err{color:var(--err);background:rgba(255,107,107,.11)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}
.card .v{font-size:24px;font-weight:700}
.card .l{font-size:12px;color:var(--dim);margin-top:4px}
.note{color:var(--dim);font-size:13px;margin:10px 0}
.foot{margin-top:50px;padding-top:20px;border-top:1px solid var(--line);color:var(--dim);font-size:12.5px}
"""


def render_report(data: dict) -> str:
    esc = lambda x: (str(x if x is not None else "").replace("&", "&amp;")
                     .replace("<", "&lt;").replace(">", "&gt;"))
    rows = data["rows"]
    paths = data.get("paths", {})

    rows_html = []
    for r in sorted(rows, key=lambda x: -(x["text_len"] if x["ok"] else -1)):
        if r["ok"]:
            cls = "ok" if r["text_len"] >= 200 else "warn"
            verdict = "正常" if r["text_len"] >= 200 else "正文为空"
            txt, lnk, st = f"{r['text_len']:,}", r["links"], str(r["status"])
        else:
            cls, verdict = "err", "失败"
            txt, lnk, st = "—", "—", "FAILED"
        rows_html.append(
            f'<tr><td class="name">{esc(r["name"])}</td>'
            f'<td class="num"><span class="pill {cls}">{st}</span></td>'
            f'<td class="num">{txt}</td><td class="num">{lnk}</td>'
            f'<td class="num">{r["server_ms"] or "—"}</td>'
            f'<td class="num"><span class="pill {cls}">{verdict}</span></td></tr>')

    path_html = ""
    if len(paths) >= 2:
        names = list(paths.keys())
        head = "".join(f"<th>{esc(n)}</th>" for n in names)
        body = []
        for r in rows:
            cells = []
            for n in names:
                pr = paths[n].get(r["slug"])
                if pr is None:
                    cells.append('<td class="num">—</td>')
                elif not pr["ok"]:
                    cells.append('<td class="num"><span class="pill err">失败</span></td>')
                else:
                    cells.append(f'<td class="num">{pr["text_len"]:,}</td>')
            body.append(f'<tr><td class="name">{esc(r["name"])}</td>{"".join(cells)}</tr>')
        path_html = (f'<h2>多路径对照</h2><table><thead><tr><th>站点</th>{head}</tr>'
                     f'</thead><tbody>{"".join(body)}</tbody></table>')

    stab = data.get("stability") or []
    stab_html = ""
    if stab:
        sr = []
        for s in stab:
            if s["success"] == 0:
                sr.append(f'<tr><td class="name">{esc(s["name"])}</td>'
                          f'<td class="num"><span class="pill err">0/{s["times"]}</span></td>'
                          f'<td class="num">—</td><td class="num">—</td>'
                          f'<td class="num"><span class="pill err">全部失败</span></td></tr>')
                continue
            cv = s["cv_pct"]
            cls = "ok" if cv < 5 else ("warn" if cv < 30 else "err")
            lab = "稳定" if cv < 5 else ("波动" if cv < 30 else "剧烈波动")
            sr.append(f'<tr><td class="name">{esc(s["name"])}</td>'
                      f'<td class="num">{s["success"]}/{s["times"]}</td>'
                      f'<td class="num">{s["len_min"]:,}~{s["len_max"]:,}</td>'
                      f'<td class="num">{s["len_range"]:,}</td>'
                      f'<td class="num">{cv}%</td>'
                      f'<td class="num"><span class="pill {cls}">{lab}</span></td></tr>')
        stab_html = ('<h2>稳定性</h2><table><thead><tr><th>站点</th><th>成功</th>'
                     '<th>字数范围</th><th>极差</th><th>CV</th><th>判定</th></tr></thead>'
                     f'<tbody>{"".join(sr)}</tbody></table>')

    s = data["summary"]
    panics = "、".join(f'{f["name"]} ({f["panic_at"]})' for f in s["failed_sites"]) or "无"

    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>巡检报告 · audit.py</title><style>{CSS}</style></head><body><div class="wrap">
<h1>站点巡检报告</h1>
<p class="sub">由 audit.py 生成 · {esc(data["generated_at"])} · 路径 {esc(data["paths_run"])}</p>
<div class="cards">
  <div class="card"><div class="v">{s["ok"]}/{s["total"]}</div><div class="l">抓取成功</div></div>
  <div class="card"><div class="v">{s["fail"]}</div><div class="l">失败</div></div>
  <div class="card"><div class="v">{s["empty"]}</div><div class="l">正文为空</div></div>
  <div class="card"><div class="v">{s["median_len"]:.0f}</div><div class="l">正文字数中位</div></div>
  <div class="card"><div class="v">{s["median_server_ms"]:.0f}</div><div class="l">服务端耗时中位 ms</div></div>
</div>
<h2>明细</h2>
<table><thead><tr><th>站点</th><th>HTTP</th><th>正文字数</th><th>链接数</th>
<th>服务端 ms</th><th>判定</th></tr></thead><tbody>{"".join(rows_html)}</tbody></table>
{path_html}
{stab_html}
<h2>失败站点</h2>
<p class="note">{esc(panics)}</p>
<div class="foot">全部数据来自实际调用；每条记录含 request_id 可回溯。</div>
</div></body></html>"""


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser(
        description="高校官网 AI 可读性巡检 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python audit.py --sites sites.json --path api --key KEY --project PID\n"
               "  python audit.py --sites sites.json --path all --repeat 3\n"
               "  python audit.py --replay runs/audit --out report.html\n")
    ap.add_argument("--sites", type=pathlib.Path, help="站点清单 JSON")
    ap.add_argument("--path", default="api",
                    choices=["api", "cb", "ui", "all"],
                    help="跑哪条路径（默认 api）")
    ap.add_argument("--repeat", type=int, default=1, help="每站重复次数")
    ap.add_argument("--key", default=os.environ.get("LEXMOUNT_API_KEY", ""),
                    help="API Key（也可用环境变量 LEXMOUNT_API_KEY）")
    ap.add_argument("--project", default=PROJECT_DEFAULT,
                    help="Project ID（也可用环境变量 LEXMOUNT_PROJECT_ID）")
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("runs/audit"),
                    help="输出目录")
    ap.add_argument("--replay", type=pathlib.Path,
                    help="从已落盘数据重放，不发请求")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--max", type=int, default=0, help="最多跑几个站点（0=全部）")
    args = ap.parse_args()

    # ---------- 重放模式 ----------
    if args.replay:
        return _replay(args)

    # ---------- 实跑模式 ----------
    if not args.sites:
        ap.error("需要 --sites（或使用 --replay）")
    if args.path in ("api", "all") and not (args.key and args.project):
        ap.error("跑 api 路径需要 --key 与 --project（或设 LEXMOUNT_API_KEY / LEXMOUNT_PROJECT_ID）")
    if args.path in ("cb", "ui", "all"):
        print("提示：cb / ui 路径需要浏览器驱动，请配合 project/tools/ 下的脚本使用；"
              "本 CLI 内置实现仅覆盖 api 路径。", file=sys.stderr)

    sites = load_sites(args.sites)
    if args.max:
        sites = sites[: args.max]

    paths_to_run = ["api"] if args.path == "api" else ["api"]
    all_rows: list[dict] = []
    per_path: dict[str, dict[str, dict]] = {}
    per_site: dict[str, list[dict]] = {}

    for path in paths_to_run:
        per_path[path] = {}
        outdir = args.out / path
        for site in sites:
            for n in range(1, args.repeat + 1):
                suffix = "" if args.repeat == 1 else f"-{n}"
                f = outdir / f"{site['slug']}{suffix}.json"
                if f.exists():
                    rec = jload(f)
                    if rec:
                        print(f"  [skip] {site['name']} 第{n}次（已存在）")
                        row = _flatten(rec)
                        row["slug"] = site["slug"]
                        row["name"] = site["name"]
                        per_path[path][site["slug"]] = row
                        per_site.setdefault(site["slug"], []).append(row)
                        continue

                print(f"  [{path}] {site['name']} 第{n}次 ...", flush=True)
                rec = fetch_api(site["url"], args.key, args.project, args.timeout)
                rec["_site"] = {"slug": site["slug"], "name": site["name"], "url": site["url"]}
                jdump(rec, f)

                row = _flatten(rec)
                row["slug"] = site["slug"]
                row["name"] = site["name"]
                per_path[path][site["slug"]] = row
                per_site.setdefault(site["slug"], []).append(row)
                tag = f"ok {row['text_len']}字" if row["ok"] else f"FAIL {row['error_code']}"
                print(f"      -> {tag}")

    # 汇总
    all_rows = list(per_site_runs(per_site))
    data = {
        "generated_at": now_iso(),
        "paths_run": args.path,
        "repeat": args.repeat,
        "summary": summarize(all_rows),
        "rows": all_rows,
        "paths": {p: v for p, v in per_path.items()},
        "stability": stability(per_site) if args.repeat > 1 else [],
    }
    jdump(data, args.out / "summary.json")

    # 人类可读
    report = render_report(data)
    out_html = args.out / "report.html"
    out_html.write_text(report, encoding="utf-8")

    s = data["summary"]
    print()
    print("=" * 62)
    print(f"完成：{s['ok']}/{s['total']} 成功，{s['fail']} 失败，{s['empty']} 正文为空")
    print(f"正文字数中位 {s['median_len']:.0f}（{s['min_len']}~{s['max_len']}）")
    if s["panic_locations"]:
        print(f"panic 位置：{'、'.join(s['panic_locations'])}")
    print(f"汇总  : {args.out / 'summary.json'}")
    print(f"报告  : {out_html}")
    return 0 if s["fail"] == 0 else 1


def per_site_runs(per_site: dict[str, list[dict]]):
    for slug, runs in per_site.items():
        for r in runs:
            yield r


def _replay(args) -> int:
    """从已落盘目录重放。"""
    root = args.replay
    if not root.exists():
        raise SystemExit(f"目录不存在: {root}")

    rows: list[dict] = []
    per_path: dict[str, dict[str, dict]] = {}
    per_site: dict[str, list[dict]] = {}

    for path_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        path = path_dir.name
        per_path[path] = {}
        for f in sorted(path_dir.glob("*.json")):
            if f.name.startswith("_"):      # _summary.json 等汇总文件跳过
                continue
            rec = jload(f)
            if not rec or not isinstance(rec, dict):
                continue
            site = rec.get("_site") or {}
            row = _flatten(rec)
            row["slug"] = site.get("slug", f.stem)
            row["name"] = site.get("name", f.stem)
            per_path[path][row["slug"]] = row
            per_site.setdefault(row["slug"], []).append(row)

    all_rows = list(per_site_runs(per_site))
    data = {
        "generated_at": now_iso(),
        "paths_run": "+".join(per_path.keys()) or "(replay)",
        "repeat": max((len(v) for v in per_site.values()), default=1),
        "summary": summarize(all_rows),
        "rows": all_rows,
        "paths": per_path,
        "stability": stability(per_site),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    jdump(data, args.out / "summary.json")
    report = render_report(data)
    (args.out / "report.html").write_text(report, encoding="utf-8")

    s = data["summary"]
    print("=" * 62)
    print(f"[replay] {s['ok']}/{s['total']} 成功，{s['fail']} 失败，{s['empty']} 正文为空")
    print(f"[replay] 正文字数中位 {s['median_len']:.0f}")
    print(f"[replay] 路径：{'、'.join(per_path.keys())}")
    print(f"[replay] 报告：{args.out / 'report.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
