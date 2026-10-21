# -*- coding: utf-8 -*-
"""对比 extract vs dump 在浙大（SPA）上的差异，验证根因。"""
import json, io, sys, re, pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project\runs")

def load(mode, slug):
    p = ROOT / mode / f"{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

def visible_text(h):
    h = re.sub(r"(?s)<script.*?</script>", " ", h)
    h = re.sub(r"(?s)<style.*?</style>", " ", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return " ".join(h.split())

print("=" * 76)
print("对照组实验：同一站点，extract 与 dump 两条路径的差异")
print("=" * 76)

for slug, name in [("zju", "浙江大学（SPA）"), ("tsinghua", "清华大学（对照）"), ("pku", "北京大学（对照）")]:
    e = load("extract", slug)
    d = load("dump", slug)
    print(f"\n### {name}  ({slug})")

    if e and "result" in e:
        r = e["result"]
        print(f"  [extract] main_text={len(r.get('main_text') or '')} 字, "
              f"links={len(r.get('links') or [])}, title={(r.get('title') or '')[:30]!r}")
    else:
        print("  [extract] 无数据")

    if d:
        html = d.get("html") or ""
        vt = visible_text(html)
        print(f"  [dump]    html={len(html)} 字符, 去标签后可见文字={len(vt)} 字符")
        print(f"            status={d.get('status_code')}, engine={d.get('engine')}")
        if vt:
            print(f"            可见文字预览: {vt[:160]!r}")
        if html:
            has_root = 'id="root"' in html
            scripts = html.count("<script")
            print(f"            SPA标记 id=root: {has_root}, <script> 数: {scripts}")
    else:
        print("  [dump]   无数据")
