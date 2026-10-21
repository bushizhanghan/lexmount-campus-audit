# -*- coding: utf-8 -*-
"""verify_extra.py — 核实 extra 字段的不稳定性。

问题：example.com 的响应有 extra.canonical_url / extra.site_name，
而 18 个高校站点全都没有。是真字段缺失，还是字段在两种接口/不同
站点上的返回策略不同？

做法：逐份 dump 原始 JSON 里的 extra 结构，不依赖中间加工。
"""
import json, io, sys, pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def dump_extra(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    r = d.get("result")
    if not r:
        return None
    return r.get("extra")

print("=" * 78)
print("extract 接口：extra 字段实际内容")
print("=" * 78)

rows = []
for f in sorted(pathlib.Path(r"E:\dsh\output\webfetch-playground\project\runs\extract").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    name = d.get("_site", {}).get("name", f.stem)
    r = d.get("result")
    if not r:
        print(f"{name:<14} (失败，无 result)")
        continue
    extra = r.get("extra")
    print(f"{name:<14} {json.dumps(extra, ensure_ascii=False) if extra else '(null)'}")
    rows.append((name, extra))

print()
print("=" * 78)
print("dump 接口：extra 字段实际内容（对照组）")
print("=" * 78)
for f in sorted(pathlib.Path(r"E:\dsh\output\webfetch-playground\project\runs\dump").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    name = d.get("_site", {}).get("name", f.stem)
    extra = d.get("extra")
    print(f"{name:<14} {json.dumps(extra, ensure_ascii=False) if extra else '(null)'}")

print()
print("=" * 78)
print("参照：第一次抓 example.com 时（早期会话）的响应")
print("=" * 78)
ref = r"E:\dsh\output\webfetch-playground\contest\resp-extract-example.com.json"
p = pathlib.Path(ref)
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    r = d.get("result", d)
    print(json.dumps(r.get("extra"), ensure_ascii=False, indent=2))
else:
    print("(参照文件已清理)")
