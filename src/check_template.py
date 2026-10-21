# -*- coding: utf-8 -*-
"""check_template.py — 核实 panic 两站是否同一门户模板（影响头条发现的强度）。"""
import io
import re
import sys
import urllib.request
import gzip

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

SITES = [
    ("哈尔滨工业大学", "https://www.hit.edu.cn/"),
    ("东南大学",       "https://www.seu.edu.cn/"),
    ("复旦大学",       "https://www.fudan.edu.cn/"),
    ("南开大学",       "https://www.nankai.edu.cn/"),
]

# 博达/sudy 门户的典型指纹
SUDY_MARKS = [
    "sudy", "www.sudytech.com", "index_files/", "wp_", "column-news",
    "_showDynClickBatch", "wbnewsid", "urltype=tree", "wbtreeid",
    "jquery.sudy", "sudyNav", "sudyFocus",
]


def fetch(url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
    try:
        raw = gzip.decompress(raw)
    except Exception:
        pass
    return raw.decode("utf-8", "replace")


print("=" * 84)
print("门户模板指纹检测（判断 panic 两站是否同模板）")
print("=" * 84)
print(f"{'站点':<14}{'sudy 指纹数':>12}{'命中项':>8}   判定")
print("-" * 84)

rows = {}
for name, url in SITES:
    try:
        h = fetch(url)
    except Exception as e:
        print(f"{name:<14} 抓取失败 {e}")
        continue
    hits = [m for m in SUDY_MARKS if m.lower() in h.lower()]
    verdict = "sudy 门户" if len(hits) >= 3 else ("疑似" if len(hits) >= 1 else "非 sudy")
    rows[name] = (len(hits), verdict)
    print(f"{name:<14}{len(hits):>12}{len(hits):>8}   {verdict}")

print()
hit_n = rows.get("哈尔滨工业大学", (0,))[0]
seu_n = rows.get("东南大学", (0,))[0]
print(f"panic 两站指纹数：哈工大 {hit_n}、东南 {seu_n}")
if hit_n >= 3 and seu_n >= 3:
    print("→ 两站都是 sudy 门户模板，「两个完全不同的站点」这个说法不成立")
else:
    print("→ 两站模板不同，「两个完全不同的站点」成立")

fudan_n = rows.get("复旦大学", (0,))[0]
nankai_n = rows.get("南开大学", (0,))[0]
print(f"\n未触发的同模板站：复旦 {fudan_n}、南开 {nankai_n}")
if fudan_n >= 3 or nankai_n >= 3:
    print("→ 同模板存在未触发站点，说明触发还有附加条件，「任何这种页面都可能触发」不成立")
