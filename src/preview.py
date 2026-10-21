# preview.py — 把三张 SVG 拼成一个临时 HTML，便于浏览器截图核验
import io
import json
import pathlib
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
charts = json.loads((ROOT / "chart_svgs.json").read_text(encoding="utf-8"))

TITLES = {
    "paths": "图 1 · 三路径正文字数对比（20 站全量）",
    "stability": "图 2 · 稳定性：每站 3 次抓取的字数分布",
    "tradeoff": "图 3 · Cloud Browser 相对 API 的取舍",
}

html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SVG 预览</title>
<style>
body{margin:0;background:#0b0e14;color:#e6edf7;
font:15px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:40px 24px 80px}
h3{font-size:17px;margin:34px 0 12px;color:#fff;font-weight:600}
figure{margin:0;background:#141922;border:1px solid #28313f;border-radius:12px;padding:22px}
svg{display:block}
</style></head><body><div class="wrap">
"""

for k in ["paths", "stability", "tradeoff"]:
    html += f"<h3>{TITLES[k]}</h3><figure>{charts[k]}</figure>\n"

html += "</div></body></html>"

out = ROOT.parent / "chart-preview.html"
out.write_text(html, encoding="utf-8")
print("预览已生成:", out.resolve())
print("大小:", len(html), "字符")
