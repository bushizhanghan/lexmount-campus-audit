# -*- coding: utf-8 -*-
"""验证浙大等站点是否为 JS 渲染 SPA（不消耗 Web Fetch 额度）。"""
import urllib.request, re, io, sys, gzip

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

TARGETS = [
    ("浙江大学", "https://www.zju.edu.cn/"),
    ("中国科学技术大学", "https://www.ustc.edu.cn/"),
    ("复旦大学", "https://www.fudan.edu.cn/"),
]

SPA_MARKERS = ['id="app"', 'id="root"', "__NUXT__", "__NEXT_DATA__", "__VUE__", "createApp"]

for name, url in TARGETS:
    print("=" * 70)
    print(name, url)
    try:
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=30).read()
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
        h = raw.decode("utf-8", "replace")
    except Exception as e:
        print("  请求失败:", e)
        continue

    m = re.search(r"(?s)<body[^>]*>(.*?)</body>", h)
    body = m.group(1) if m else ""
    stripped = re.sub(r"(?s)<script.*?</script>", " ", body)
    stripped = re.sub(r"(?s)<style.*?</style>", " ", stripped)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    visible = " ".join(stripped.split())

    print(f"  HTML 总大小      : {len(raw):>8} 字节")
    print(f"  <body> 大小      : {len(body):>8} 字符")
    print(f"  去标签后可见文字 : {len(visible):>8} 字符")
    print(f"  <script> 数量    : {h.count('<script'):>8}")
    markers = [k for k in SPA_MARKERS if k in h]
    print(f"  SPA 特征         : {markers if markers else '无'}")

    mt = re.search(r'<title[^>]*>(.*?)</title>', h, re.S)
    print(f"  <title>          : {mt.group(1).strip() if mt else '(无)'}")

    desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', h, re.S | re.I)
    if desc:
        print(f"  meta description : {desc.group(1).strip()[:80]}...")

    print(f"  可见文字预览     : {visible[:150]!r}")
    print()
