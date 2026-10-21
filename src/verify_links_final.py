# -*- coding: utf-8 -*-
"""verify_links_final.py — 统一口径后的最终结论。

本地抓的 HTML 与平台返回的口径差异：
  1. 平台把相对 URL 规范化成绝对 URL -> 直接字符串对比会误判
  2. 平台可能做去重

所以正确做法：把两边的 href 都规范化（相对 -> 绝对，去掉 fragment、
去掉 query 里的跟踪参数）后，再比较集合大小。
"""
import urllib.request, re, io, sys, gzip, json, pathlib
from urllib.parse import urljoin, urldefrag

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

TARGETS = [
    ("复旦大学", "https://www.fudan.edu.cn/", "fudan"),
    ("北京师范大学", "https://www.bnu.edu.cn/", "bnu"),
    ("武汉大学", "https://www.whu.edu.cn/", "whu"),
    ("同济大学", "https://www.tongji.edu.cn/", "tongji"),
    ("南京大学", "https://www.nju.edu.cn/", "nju"),
    ("北京大学", "https://www.pku.edu.cn/", "pku"),
    ("上海交通大学", "https://www.sjtu.edu.cn/", "sjtu"),
    ("中山大学", "https://www.sysu.edu.cn/", "sysu"),
    ("中国科学技术大学", "https://www.ustc.edu.cn/", "ustc"),
    ("清华大学", "https://www.tsinghua.edu.cn/", "tsinghua"),
    ("华中科技大学", "https://www.hust.edu.cn/", "hust"),
    ("中国人民大学", "https://www.ruc.edu.cn/", "ruc"),
]

def norm(u, base):
    u = (u or "").strip()
    if not u or u.lower().startswith(("javascript:", "mailto:", "tel:")):
        return None
    try:
        absu = urljoin(base, u)
    except Exception:
        return None
    absu, _ = urldefrag(absu)
    return absu or None

RUNS = pathlib.Path(r"E:\dsh\output\webfetch-playground\project\runs\extract")
rows = []

for name, url, slug in TARGETS:
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        h = raw.decode("utf-8", "replace")
    except Exception as e:
        print(f"{name}: 本地失败 {e}")
        continue

    local = set()
    for x in re.findall(r'<a\b[^>]*\bhref=["\']([^"\']*)["\']', h, re.I):
        n = norm(x, url)
        if n:
            local.add(n)

    p = RUNS / f"{slug}.json"
    if not p.exists():
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    plat_links = d["result"].get("links") or []
    plat = set()
    for l in plat_links:
        n = norm(l.get("href"), url)
        if n:
            plat.add(n)

    missing = local - plat
    rows.append({
        "name": name,
        "local_uniq": len(local),
        "platform_uniq": len(plat),
        "platform_raw": len(plat_links),
        "missing": len(missing),
        "missing_pct": round(len(missing) / len(local) * 100, 1) if local else 0,
    })

print("=" * 100)
print("规范化后对比（相对URL转绝对、去 fragment）")
print("=" * 100)
print(f"{'站点':<14}{'本地去重':>10}{'平台去重':>10}{'平台原始':>10}{'缺失':>8}{'缺失率':>10}")
print("-" * 100)
for r in rows:
    print(f"{r['name']:<14}{r['local_uniq']:>10}{r['platform_uniq']:>10}{r['platform_raw']:>10}"
          f"{r['missing']:>8}{r['missing_pct']:>9.1f}%")

print()
trunc = [r for r in rows if r["missing_pct"] > 20]
full = [r for r in rows if r["missing_pct"] <= 20]
print(f"缺失率 > 20%（确认被截断/漏抓）: {len(trunc)}/{len(rows)}")
for r in trunc:
    print(f"  {r['name']}: 本地 {r['local_uniq']} 个，平台 {r['platform_uniq']} 个，漏 {r['missing']} ({r['missing_pct']}%)")
print()
print(f"缺失率 <= 20%（基本完整）: {len(full)}/{len(rows)}")

out = pathlib.Path(r"E:\dsh\output\webfetch-playground\project\links_groundtruth_final.json")
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n明细: {out}")
