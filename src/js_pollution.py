# -*- coding: utf-8 -*-
"""js_pollution2.py — 改进 JS 源码检测。

浙大的 JS 行很长（800-1200 字符），且内含大量中文标题文本，
所以「符号密度」不足以识别。改用更强的代码特征信号。
"""
import json
import io
import sys
import re
import pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")

# 强代码特征：出现在 JS 里的固定语法
STRONG = [
    r"\bvar\s+[\w$]+\s*=",
    r"\blet\s+[\w$]+\s*=",
    r"\bconst\s+[\w$]+\s*=",
    r"\bfunction\s*\(",
    r"\bmain\.\w+",
    r"\{\s*id\s*:",
    r"\bJSON\.(parse|stringify)\b",
    r"document\.(getElementById|querySelector|write)",
    r"window\.(location|open|addEventListener)",
    r"=>\s*\{",
    r"\.push\(",
    r"\$\{",
    r"\bnew\s+[A-Z][\w$]*\(",
]
STRONG_RE = re.compile("|".join(STRONG))


def js_score(ln: str) -> float:
    """返回该行"像 JS 源码"的强度 0~1。"""
    if len(ln) < 40:
        return 0.0
    hits = len(STRONG_RE.findall(ln))
    if hits == 0:
        return 0.0
    # 关键：JS 行通常有不成比例的中文标点混合与很多 = : { } [ ]
    syntax = ln.count("{") + ln.count("}") + ln.count("[") + ln.count("]") \
        + ln.count("=") + ln.count(";") + ln.count("'") + ln.count('"')
    base = min(1.0, hits / 3.0)
    density = min(1.0, syntax / max(len(ln), 1) * 8)
    return round(0.6 * base + 0.4 * density, 2)


def classify(text):
    lines = text.split("\n")
    js_lines, js_chars = [], 0
    clean_lines = []
    for ln in lines:
        s = js_score(ln)
        if s >= 0.5:
            js_lines.append((s, ln))
            js_chars += len(ln)
        else:
            clean_lines.append(ln)
    return js_lines, js_chars, clean_lines


rows = []
for f in sorted((ROOT / "runs" / "api" / "extract").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    if "result" not in d:
        continue
    r = d["result"]
    name = d["_site"]["name"]
    text = r.get("main_text") or ""
    if not text:
        continue
    js_lines, js_chars, clean = classify(text)
    rows.append({
        "name": name,
        "slug": d["_site"]["slug"],
        "total": len(text),
        "js_chars": js_chars,
        "js_line_count": len(js_lines),
        "js_pct": round(js_chars / len(text) * 100, 1) if text else 0,
        "clean": len(text) - js_chars,
    })

print("=" * 94)
print("main_text 中的 JS 源码污染（改进检测）")
print("=" * 94)
print(f"{'站点':<14}{'总字符':>10}{'JS字符':>10}{'JS行':>6}{'污染率':>9}{'纯净正文':>10}")
print("-" * 94)
for r in sorted(rows, key=lambda x: -x["js_pct"]):
    flag = "  <== 严重" if r["js_pct"] > 20 else ("  <== 有" if r["js_pct"] > 5 else "")
    print(f"{r['name']:<14}{r['total']:>10,}{r['js_chars']:>10,}{r['js_line_count']:>6}"
          f"{r['js_pct']:>8.1f}%{r['clean']:>10,}{flag}")

polluted = [r for r in rows if r["js_pct"] > 5]
tot = sum(r["total"] for r in rows)
tot_js = sum(r["js_chars"] for r in rows)
print()
print(f"污染 >5% : {len(polluted)}/{len(rows)}")
print(f"合计 {tot:,} 字符，JS 源码 {tot_js:,} ({tot_js/tot*100:.1f}%)")

# 浙大单独详查
zju = next((r for r in rows if r["slug"] == "zju"), None)
if zju:
    d = json.loads((ROOT / "runs" / "api" / "extract" / "zju.json").read_text(encoding="utf-8"))
    text = d["result"]["main_text"]
    js_lines, js_chars, clean = classify(text)
    print(f"\n浙大详情：{len(js_lines)} 行被判为 JS，共 {js_chars:,} 字符")
    for s, ln in js_lines[:5]:
        print(f"  [score={s}, {len(ln)}字符] {ln[:110]}...")
    print(f"  纯净正文: {len(chr(10).join(clean))} 字符")

out = {
    "sites": rows,
    "polluted_count": len(polluted),
    "total_chars": tot,
    "total_js_chars": tot_js,
    "total_js_pct": round(tot_js / tot * 100, 1) if tot else 0,
}
(ROOT / "js_pollution.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n已存: {ROOT / 'js_pollution.json'}")
