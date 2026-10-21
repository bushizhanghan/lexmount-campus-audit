# -*- coding: utf-8 -*-
"""svg_charts.py — 从 v4_data.json 生成内联 SVG 图表，供报告直接嵌入。

设计原则：
  - 纯内联 SVG，无外部依赖
  - 走查阻力最小：每张图只讲一件事
  - 深色主题与报告一致
"""
import json
import io
import sys
import pathlib
import math

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
D = json.loads((ROOT / "v4_data.json").read_text(encoding="utf-8"))

C = {
    "bg": "#0b0e14", "panel": "#141922", "line": "#28313f",
    "fg": "#e6edf7", "dim": "#8b98ab",
    "green": "#7ee787", "warn": "#f0b429", "err": "#ff6b6b",
    "blue": "#58a6ff", "purple": "#bc8cff",
}

api_rows = D["api_rows"]
ui_rows = D["ui_rows"]
cb = D["cb"]
cb_map = {c["slug"]: c for c in cb}
stab = D["stability"]
stab_map = {s["slug"]: s for s in stab}
TRADE = D["cb_tradeoff"]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_open(w, h, title=""):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px;display:block;margin:0 auto" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(title)}">')


# ============================================================
# 图 1：三路径分组条形图
# ============================================================
def chart_paths():
    rows = sorted(api_rows, key=lambda r: -(r["text_len"] if r["ok"] else -1))
    n = len(rows)
    LEFT, RIGHT, TOP = 96, 130, 46
    ROW = 30
    W = 1040
    H = TOP + n * ROW + 58
    max_v = max(max((r["text_len"] for r in rows if r["ok"]), default=1),
                max((c["textLen"] for c in cb if c.get("ok")), default=1))
    plot_w = W - LEFT - RIGHT
    scale = plot_w / max_v

    out = [svg_open(W, H, "三路径正文字数对比")]
    # 网格
    for i in range(5):
        v = max_v / 4 * i
        x = LEFT + v * scale
        out.append(f'<line x1="{x:.1f}" y1="{TOP-8}" x2="{x:.1f}" y2="{TOP+n*ROW}" '
                   f'stroke="{C["line"]}" stroke-width="1" stroke-dasharray="3 4" opacity=".55"/>')
        out.append(f'<text x="{x:.1f}" y="{TOP-16}" fill="{C["dim"]}" font-size="10.5" '
                   f'text-anchor="middle">{int(v):,}</text>')

    for idx, r in enumerate(rows):
        y0 = TOP + idx * ROW
        out.append(f'<text x="{LEFT-10}" y="{y0+ROW*0.62:.1f}" fill="{C["fg"]}" font-size="12" '
                   f'text-anchor="end" font-weight="600">{esc(r["name"])}</text>')
        bars = []
        u = ui_rows.get(r["slug"]) or {}
        if u.get("text_len") is not None:
            bars.append((u["text_len"], C["blue"], "UI", u["ok"]))
        else:
            bars.append((0, C["line"], "UI", False))
        if r["ok"]:
            bars.append((r["text_len"], C["green"], "API", True))
        else:
            bars.append((0, C["err"], "API", False))
        c = cb_map.get(r["slug"])
        bars.append(((c["textLen"] if c and c.get("ok") else 0),
                     C["purple"] if c and c.get("ok") else C["line"], "CB",
                     bool(c and c.get("ok"))))

        bh = 6.4
        for bi, (val, color, tag, ok) in enumerate(bars):
            by = y0 + 4 + bi * (bh + 1.6)
            if not ok:
                # 失败：细红条 + 标签，窄一点避免压住相邻条
                out.append(f'<rect x="{LEFT}" y="{by:.1f}" width="18" height="{bh}" '
                           f'fill="{C["err"]}" opacity=".9" rx="1.5"/>')
                out.append(f'<text x="{LEFT+23}" y="{by+bh-1:.1f}" fill="{C["err"]}" '
                           f'font-size="9" font-weight="700">失败</text>')
            else:
                w = max(val * scale, 1.6)
                out.append(f'<rect x="{LEFT}" y="{by:.1f}" width="{w:.1f}" height="{bh}" '
                           f'fill="{color}" rx="1.5"/>')
                # 条够长时数值放条内右侧（深色字），否则放条外
                if w > 48:
                    out.append(f'<text x="{LEFT+w-5:.1f}" y="{by+bh-1:.1f}" fill="{C["bg"]}" '
                               f'font-size="9" font-weight="700" text-anchor="end">{val:,}</text>')
                else:
                    out.append(f'<text x="{LEFT+w+5:.1f}" y="{by+bh-1:.1f}" fill="{C["dim"]}" '
                               f'font-size="9">{val:,}</text>')

    # 图例
    ly = H - 30
    lx = LEFT
    for label, color in [("① UI 表单", C["blue"]), ("② 官方 API", C["green"]),
                         ("③ Cloud Browser", C["purple"]), ("失败", C["err"])]:
        out.append(f'<rect x="{lx}" y="{ly}" width="11" height="11" fill="{color}" rx="2"/>')
        out.append(f'<text x="{lx+16}" y="{ly+9.5}" fill="{C["dim"]}" font-size="11">{label}</text>')
        lx += 150
    out.append("</svg>")
    return "\n".join(out)


# ============================================================
# 图 2：稳定性条带图
# ============================================================
def chart_stability():
    rows = [s for s in stab]
    n = len(rows)
    LEFT, RIGHT, TOP = 96, 150, 44
    ROW = 26
    W = 1040
    H = TOP + n * ROW + 46
    max_v = max((s.get("len_max") or 0) for s in rows) or 1
    plot_w = W - LEFT - RIGHT
    scale = plot_w / max_v

    out = [svg_open(W, H, "稳定性：每站 3 次抓取的字数分布")]
    for i in range(5):
        v = max_v / 4 * i
        x = LEFT + v * scale
        out.append(f'<line x1="{x:.1f}" y1="{TOP-8}" x2="{x:.1f}" y2="{TOP+n*ROW}" '
                   f'stroke="{C["line"]}" stroke-dasharray="3 4" opacity=".55"/>')
        out.append(f'<text x="{x:.1f}" y="{TOP-16}" fill="{C["dim"]}" font-size="10.5" '
                   f'text-anchor="middle">{int(v):,}</text>')

    for idx, s in enumerate(rows):
        y = TOP + idx * ROW + ROW / 2
        out.append(f'<text x="{LEFT-10}" y="{y+4:.1f}" fill="{C["fg"]}" font-size="12" '
                   f'text-anchor="end" font-weight="600">{esc(s["name"])}</text>')

        if s.get("success", 0) == 0:
            out.append(f'<rect x="{LEFT}" y="{y-5}" width="30" height="10" fill="{C["err"]}" '
                       f'opacity=".85" rx="2"/>')
            out.append(f'<text x="{LEFT+36}" y="{y+4:.1f}" fill="{C["err"]}" font-size="10" '
                       f'font-weight="700">0/3 全部失败</text>')
            continue

        lens = sorted(set(r["text_len"] for r in s["runs"] if r.get("ok")))
        if len(lens) == 1:
            x = LEFT + lens[0] * scale
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{C["green"]}"/>')
            out.append(f'<text x="{x+9:.1f}" y="{y+3.6:.1f}" fill="{C["dim"]}" font-size="9.5">'
                       f'{lens[0]:,} ×3</text>')
        else:
            xs = [LEFT + v * scale for v in lens]
            out.append(f'<line x1="{min(xs):.1f}" y1="{y:.1f}" x2="{max(xs):.1f}" y2="{y:.1f}" '
                       f'stroke="{C["warn"]}" stroke-width="2" opacity=".55"/>')
            for v, x in zip(lens, xs):
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{C["warn"]}"/>')
            # 数值标在点的下方，CV 标在最右侧点旁（避免压住网格刻度）
            for v, x in zip(lens, xs):
                out.append(f'<text x="{x:.1f}" y="{y-9:.1f}" fill="{C["warn"]}" font-size="9" '
                           f'text-anchor="middle">{v:,}</text>')
            cvx = min(max(xs) + 10, W - RIGHT + 22)
            out.append(f'<text x="{cvx:.1f}" y="{y+3.6:.1f}" fill="{C["warn"]}" font-size="9.5" '
                       f'font-weight="700">CV {s["cv_pct"]}%</text>')

    ly = H - 26
    for i, (label, color) in enumerate([("三次结果完全一致", C["green"]),
                                        ("同批次内有波动", C["warn"]),
                                        ("三次全部失败", C["err"])]):
        lx = LEFT + i * 210
        out.append(f'<circle cx="{lx+5}" cy="{ly}" r="4.5" fill="{color}"/>')
        out.append(f'<text x="{lx+16}" y="{ly+4}" fill="{C["dim"]}" font-size="11">{label}</text>')
    out.append("</svg>")
    return "\n".join(out)


# ============================================================
# 图 3：CB 取舍双轴散点
# ============================================================
def chart_tradeoff():
    detail = TRADE["detail"]
    W, H = 1040, 460
    LEFT, RIGHT, TOP, BOT = 110, 40, 40, 70
    pw, ph = W - LEFT - RIGHT, H - TOP - BOT
    xs = [d["link_diff"] for d in detail]
    ys = [d["len_diff"] for d in detail]
    xmax = max(max(xs), 10) * 1.12
    xmin = min(min(xs), -10) * 1.12
    ymax = max(max(ys), 10) * 1.12
    ymin = min(min(ys), -10) * 1.12

    def px(v):
        return LEFT + (v - xmin) / (xmax - xmin) * pw

    def py(v):
        return TOP + ph - (v - ymin) / (ymax - ymin) * ph

    out = [svg_open(W, H, "Cloud Browser 相对 API 的取舍")]
    # 象限底色
    out.append(f'<rect x="{px(0):.1f}" y="{py(0):.1f}" width="{px(xmax)-px(0):.1f}" '
               f'height="{max(py(ymin)-py(0),0):.1f}" fill="{C["purple"]}" opacity=".07"/>')
    out.append(f'<rect x="{px(xmin):.1f}" y="{py(0):.1f}" width="{max(px(0)-px(xmin),0):.1f}" '
               f'height="{max(py(ymin)-py(0),0):.1f}" fill="{C["green"]}" opacity=".07"/>')

    # 轴
    out.append(f'<line x1="{LEFT}" y1="{py(0):.1f}" x2="{LEFT+pw}" y2="{py(0):.1f}" '
               f'stroke="{C["line"]}" stroke-width="1.4"/>')
    out.append(f'<line x1="{px(0):.1f}" y1="{TOP}" x2="{px(0):.1f}" y2="{TOP+ph}" '
               f'stroke="{C["line"]}" stroke-width="1.4"/>')
    out.append(f'<text x="{LEFT+pw/2:.0f}" y="{H-26}" fill="{C["dim"]}" font-size="12" '
               f'text-anchor="middle">链接数差（Cloud Browser − API）</text>')
    out.append(f'<text x="26" y="{TOP+ph/2:.0f}" fill="{C["dim"]}" font-size="12" '
               f'text-anchor="middle" transform="rotate(-90 26 {TOP+ph/2:.0f})">'
               f'正文字数差（Cloud Browser − API）</text>')

    # 刻度（两侧对称，都覆盖）
    xticks = sorted({0, round(xmax * 0.5), round(xmax),
                     round(xmin * 0.5), round(xmin)})
    for v in xticks:
        out.append(f'<text x="{px(v):.1f}" y="{TOP+ph+18}" fill="{C["dim"]}" font-size="10" '
                   f'text-anchor="middle">{v:+d}</text>')
    yticks = sorted({0, round(ymax * 0.5), round(ymax),
                     round(ymin * 0.5), round(ymin)})
    for v in yticks:
        out.append(f'<text x="{LEFT-8}" y="{py(v)+3.5:.1f}" fill="{C["dim"]}" font-size="10" '
                   f'text-anchor="end">{v:+d}</text>')

    # 点（文字避让：先按 y 排序，近邻上下错开）
    pts = sorted(detail, key=lambda d: d["len_diff"])
    placed = []
    for d in pts:
        x, y = px(d["link_diff"]), py(d["len_diff"])
        # 与已放置的点太近则上下偏移标签
        ty = y + 3.6
        for (_, py_) in placed:
            if abs(x - _) < 60 and abs(ty - py_) < 11:
                ty = py_ + 11 if ty < py_ else py_ - 11
        placed.append((x, ty))
        color = C["green"] if d["len_diff"] >= 0 else C["warn"]
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6" fill="{color}" opacity=".9"/>')
        anchor = "end" if x > LEFT + pw * 0.72 else "start"
        dx = -9 if anchor == "end" else 9
        out.append(f'<text x="{x+dx:.1f}" y="{ty:.1f}" fill="{C["fg"]}" font-size="9.5" '
                   f'text-anchor="{anchor}">{esc(d["name"])}</text>')

    # 象限说明
    out.append(f'<text x="{px(xmax)-10:.1f}" y="{py(ymin)+18:.1f}" fill="{C["purple"]}" '
               f'font-size="11" text-anchor="end" opacity=".9">链接更多 · 正文更少</text>')
    out.append(f'<text x="{px(xmax)-10:.1f}" y="{TOP+16}" fill="{C["green"]}" '
               f'font-size="11" text-anchor="end" opacity=".9">链接更多 · 正文更多</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    charts = {
        "paths": chart_paths(),
        "stability": chart_stability(),
        "tradeoff": chart_tradeoff(),
    }
    outdir = ROOT / "charts"
    outdir.mkdir(exist_ok=True)
    for k, v in charts.items():
        (outdir / f"{k}.svg").write_text(v, encoding="utf-8")
        print(f"{k}.svg  {len(v):,} 字符")
    (ROOT / "chart_svgs.json").write_text(
        json.dumps(charts, ensure_ascii=False), encoding="utf-8")
    print("已存 chart_svgs.json")
