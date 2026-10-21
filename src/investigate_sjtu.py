# -*- coding: utf-8 -*-
"""investigate_sjtu.py — 上海交大：平台 1865 字 vs 裸抓 2840 字，平台短 34%。

假设：平台把部分内容判定为"导航/页脚"过滤掉了。
验证：对比平台 main_text 与裸抓可见文字，找出被丢弃的内容。
"""
import urllib.request, re, io, sys, gzip, json, pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

url = "https://www.sjtu.edu.cn/"
raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
try:
    raw = gzip.decompress(raw)
except Exception:
    pass
h = raw.decode("utf-8", "replace")

b = re.sub(r"(?s)<script.*?</script>", " ", h)
b = re.sub(r"(?s)<style.*?</style>", " ", b)
b = re.sub(r"<[^>]+>", " ", b)
bare = " ".join(b.split())

d = json.loads(pathlib.Path(r"E:\dsh\output\webfetch-playground\project\runs\extract\sjtu.json").read_text(encoding="utf-8"))
plat = d["result"].get("main_text") or ""

print("=" * 80)
print("上海交通大学：平台 main_text 短 34%，内容去哪了？")
print("=" * 80)
print(f"裸抓可见文字: {len(bare)} 字")
print(f"平台 main_text: {len(plat)} 字")
print(f"差值: {len(bare) - len(plat)} 字\n")

# 用句子级对比，找出裸抓有但平台没有的句子
def sentences(t):
    return set(s.strip() for s in re.split(r"[。；;！!？?\n]", t) if len(s.strip()) >= 8)

bs, ps = sentences(bare), sentences(plat)
only_bare = bs - ps
only_plat = ps - bs

print(f"裸抓独有句子: {len(only_bare)} 条")
print(f"平台独有句子: {len(only_plat)} 条\n")

print("--- 平台丢弃的内容（裸抓有、平台没有）前 15 条 ---")
for s in list(only_bare)[:15]:
    print(f"  - {s[:76]}")

print()
print("--- 平台额外产出的内容（平台有、裸抓没有）前 8 条 ---")
for s in list(only_plat)[:8]:
    print(f"  + {s[:76]}")

print()
print("=" * 80)
print("平台 main_text 结尾 400 字（看是否被截断）：")
print("=" * 80)
print(plat[-400:])
