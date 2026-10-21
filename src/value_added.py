# -*- coding: utf-8 -*-
"""value_added.py — 量化云平台相比裸 HTTP 抓取的真实增值。

不消耗平台额度。对比三个维度：
  1. 内容完整性：裸抓可见文字 vs 平台 main_text
  2. 结构化程度：裸抓只有 HTML vs 平台给 headings/paragraphs/lists/tables/links
  3. 可用性：裸抓需自己写解析 vs 平台直接可用
"""
import urllib.request, re, io, sys, gzip, json, pathlib, statistics
from urllib.parse import urljoin, urldefrag

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

TARGETS = [
    ("复旦大学", "https://www.fudan.edu.cn/", "fudan"),
    ("武汉大学", "https://www.whu.edu.cn/", "whu"),
    ("南京大学", "https://www.nju.edu.cn/", "nju"),
    ("中国人民大学", "https://www.ruc.edu.cn/", "ruc"),
    ("中国科学技术大学", "https://www.ustc.edu.cn/", "ustc"),
    ("上海交通大学", "https://www.sjtu.edu.cn/", "sjtu"),
    ("中山大学", "https://www.sysu.edu.cn/", "sysu"),
    ("同济大学", "https://www.tongji.edu.cn/", "tongji"),
    ("华中科技大学", "https://www.hust.edu.cn/", "hust"),
    ("北京师范大学", "https://www.bnu.edu.cn/", "bnu"),
]

RUNS = pathlib.Path(r"E:\dsh\output\webfetch-playground\project\runs\extract")

print("=" * 108)
print("云平台 vs 裸 HTTP 抓取：同一站点，两种方式拿到的东西")
print("=" * 108)
print(f"{'站点':<14}{'裸抓可见文字':>12}{'平台main_text':>14}{'平台/裸抓':>10}"
      f"{'裸抓链接数':>10}{'平台链接':>10}{'平台额外结构':>14}")
print("-" * 108)

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
        print(f"{name:<14} 本地失败: {e}")
        continue

    # 裸抓：去掉 script/style 后的可见文字
    b = re.sub(r"(?s)<script.*?</script>", " ", h)
    b = re.sub(r"(?s)<style.*?</style>", " ", b)
    b = re.sub(r"<[^>]+>", " ", b)
    bare_text = " ".join(b.split())

    # 裸抓：需要自己正则提取的链接数
    bare_links = len(set(
        urljoin(url, x.strip()) for x in
        re.findall(r'<a\b[^>]*\bhref=["\']([^"\']*)["\']', h, re.I)
        if x.strip() and not x.strip().lower().startswith("javascript")
    ))

    p = RUNS / f"{slug}.json"
    if not p.exists():
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    r = d["result"]
    plat_text = r.get("main_text") or ""
    plat_links = len(r.get("links") or [])
    ds = (r.get("extra") or {}).get("dom_summary") or {}
    struct = []
    if ds.get("headings"):  struct.append(f"H{len(ds['headings'])}")
    if ds.get("paragraphs"): struct.append(f"P{len(ds['paragraphs'])}")
    if ds.get("lists"):     struct.append(f"L{len(ds['lists'])}")
    if ds.get("tables"):    struct.append(f"T{len(ds['tables'])}")
    if ds.get("forms"):     struct.append(f"F{len(ds['forms'])}")
    imgs = (r.get("extra") or {}).get("images_detail") or []
    if imgs:                struct.append(f"I{len(imgs)}")
    struct_str = "+".join(struct) if struct else "(无)"

    ratio = len(plat_text) / len(bare_text) if bare_text else 0
    print(f"{name:<14}{len(bare_text):>12}{len(plat_text):>14}{ratio:>9.2f}x"
          f"{bare_links:>10}{plat_links:>10}{struct_str:>14}")

    rows.append({
        "name": name, "bare_text": len(bare_text), "plat_text": len(plat_text),
        "ratio": round(ratio, 2), "bare_links": bare_links, "plat_links": plat_links,
        "struct": struct_str,
    })

print()
if rows:
    ratios = [r["ratio"] for r in rows if r["ratio"] > 0]
    print("=" * 108)
    print(f"平台正文 / 裸抓可见文字 的比值：")
    print(f"  min={min(ratios):.2f}x  中位={statistics.median(ratios):.2f}x  max={max(ratios):.2f}x")
    print(f"  >1（平台比裸抓更干净/更长）: {sum(1 for x in ratios if x > 1)}/{len(ratios)}")
    print()
    print("说明：比值 > 1 不代表平台抓到了更多内容，而代表平台做了清洗（去掉导航噪音、")
    print("合并空白），输出更接近'正文'。这正是裸抓 HTML 后最费人工的一步。")

out = pathlib.Path(r"E:\dsh\output\webfetch-playground\project\value_added.json")
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n明细: {out}")
