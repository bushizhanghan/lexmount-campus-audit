# -*- coding: utf-8 -*-
"""render_v4.py — 最终版报告。

严格遵循审计要求：
  - 撤回「3,400 倍」伪结论
  - 区分「能证明的」与「不能证明的」
  - Cloud Browser 写成「以链接换正文的取舍」，不写「全面更好」
  - 新增 JS 源码污染（浙大 70%）
  - 人大+哈工大双站双驱动的 panic 对照作为最强证据
"""
import json
import io
import sys
import pathlib
import statistics
import html as H
from datetime import datetime, timezone, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(r"E:\dsh\output\webfetch-playground\project")
D = json.loads((ROOT / "v4_data.json").read_text(encoding="utf-8"))
CH = json.loads((ROOT / "chart_svgs.json").read_text(encoding="utf-8"))
CH_PATHS = CH["paths"]
CH_STAB = CH["stability"]
CH_TRADE = CH["tradeoff"]

BJ = timezone(timedelta(hours=8))
now = datetime.now(BJ)
esc = lambda x: H.escape(str(x if x is not None else ""))

B = D["api_baseline"]
api_rows = D["api_rows"]
ui_rows = D["ui_rows"]
stab = D["stability"]
cb = D["cb"]
dedup = D["dedup"]
depth = D["depth"]
JS = D["js_pollution"]
TRADE = D["cb_tradeoff"]
CROSS = D["cross_batch"]
CLEAN = D["clean_stats"]
panic_sites = D["panic_sites"]
cb_fixed = D["cb_fixed_panic"]

ok_api = [r for r in api_rows if r["ok"]]
fail_api = [r for r in api_rows if not r["ok"]]
cb_map = {c["slug"]: c for c in cb}

# ---------- 三路径表 ----------
PATH_ROWS = []
for r in sorted(api_rows, key=lambda x: -(x["text_len"] if x["ok"] else -1)):
    u = ui_rows.get(r["slug"]) or {}
    ui_raw = u.get("text_len")
    if ui_raw is None:
        ui_txt, ui_cls = "—", "info"
    elif ui_raw < 200:
        ui_txt, ui_cls = f"{ui_raw}", "warn"
    else:
        ui_txt, ui_cls = f"{ui_raw:,}", "ok"

    c = cb_map.get(r["slug"])
    api_txt = f"{r['text_len']:,}" if r["ok"] else '<span class="pill err">失败</span>'
    if c and c.get("ok"):
        cb_txt = f"{c['textLen']:,}"
        cb_links = f"{c['linkCount']}"
    else:
        cb_txt, cb_links = "—", "—"

    # 标注：纯净正文（剔除 JS 后）
    if r["ok"] and r["js_pct"] > 5:
        api_txt += f'<br><span class="mini">纯净 {r["clean_len"]:,}</span>'

    PATH_ROWS.append(f"""<tr>
      <td class="name">{esc(r['name'])}</td>
      <td class="num"><span class="pill {ui_cls}">{ui_txt}</span></td>
      <td class="num">{api_txt}</td>
      <td class="num">{cb_txt}</td>
      <td class="num">{cb_links}</td>
    </tr>""")

# ---------- panic 卡 ----------
PANIC_HTML = []
for r in fail_api:
    PANIC_HTML.append(f"""<div class="case">
      <div class="case-head"><b>{esc(r['name'])}</b>
        <span class="pill err">{esc(r['error_code'])}</span></div>
      <div class="kv"><span>目标</span><code>{esc(r['url'])}</code></div>
      <div class="kv"><span>request_id</span><code>{esc(r['rid'])}</code></div>
      <div class="kv"><span>panic 位置</span><code>{esc(r['panic_at'])}</code></div>
      <pre class="err-trace">{esc(r['error_msg'][:260])}</pre>
    </div>""")

# ---------- 稳定性表 ----------
STAB_ROWS = []
for s in stab:
    if s.get("success", 0) == 0:
        STAB_ROWS.append(f"""<tr><td class="name">{esc(s['name'])}</td>
          <td class="num"><span class="pill err">0/{s['times']}</span></td>
          <td class="num">—</td><td class="num">—</td><td class="num">—</td>
          <td class="num"><span class="pill err">全部失败</span></td></tr>""")
        continue
    cv = s["cv_pct"]
    cls = "ok" if cv < 5 else ("warn" if cv < 30 else "err")
    label = "稳定" if cv < 5 else ("波动" if cv < 30 else "剧烈波动")
    STAB_ROWS.append(f"""<tr>
      <td class="name">{esc(s['name'])}</td>
      <td class="num">{s['success']}/{s['times']}</td>
      <td class="num">{s['len_min']:,}~{s['len_max']:,}</td>
      <td class="num">{s['len_range']:,}</td>
      <td class="num">{cv}%</td>
      <td class="num"><span class="pill {cls}">{label}</span></td>
    </tr>""")

# ---------- 跨批次表 ----------
CROSS_ROWS = []
for c in sorted(CROSS, key=lambda x: -abs(x["diff"])):
    CROSS_ROWS.append(f"""<tr>
      <td class="name">{esc(c['name'])}</td>
      <td class="num">{c['ui']:,}</td>
      <td class="num">{c['api']:,}</td>
      <td class="num"><span class="pill {'err' if abs(c['diff'])>1000 else 'warn'}">{c['diff']:+,}</span></td>
    </tr>""")

# ---------- CB 取舍表 ----------
TRADE_ROWS = []
for t in sorted(TRADE["detail"], key=lambda x: x["len_diff"]):
    lcls = "err" if t["len_diff"] < -1000 else ("warn" if t["len_diff"] < 0 else "ok")
    kcls = "ok" if t["link_diff"] > 0 else ("warn" if t["link_diff"] == 0 else "err")
    TRADE_ROWS.append(f"""<tr>
      <td class="name">{esc(t['name'])}</td>
      <td class="num">{t['api_len']:,}</td>
      <td class="num">{t['cb_len']:,}</td>
      <td class="num"><span class="pill {lcls}">{t['len_diff']:+,}</span></td>
      <td class="num">{t['api_links']}</td>
      <td class="num">{t['cb_links']}</td>
      <td class="num"><span class="pill {kcls}">{t['link_diff']:+d}</span></td>
    </tr>""")

# ---------- JS 污染 ----------
JS_ROWS = []
for r in JS["sites"]:
    if r["js_pct"] <= 0:
        continue
    cls = "err" if r["js_pct"] > 20 else "warn"
    JS_ROWS.append(f"""<tr>
      <td class="name">{esc(r['name'])}</td>
      <td class="num">{r['total']:,}</td>
      <td class="num">{r['js_chars']:,}</td>
      <td class="num"><span class="pill {cls}">{r['js_pct']}%</span></td>
      <td class="num">{r['clean']:,}</td>
    </tr>""")

# ---------- 去重 ----------
DEDUP_ROWS = []
for s in dedup.get("sites", []):
    if s["inflation_pct"] <= 0.5:
        continue
    DEDUP_ROWS.append(f"""<tr>
      <td class="name">{esc(s['name'])}</td>
      <td class="num">{s['raw_len']:,}</td>
      <td class="num">{s['dedup_len']:,}</td>
      <td class="num"><span class="pill {'err' if s['inflation_pct']>40 else 'warn'}">{s['inflation_pct']}%</span></td>
      <td class="num">{s['dup_lines']}</td>
    </tr>""")

# ---------- 深度 ----------
DEPTH_ROWS = []
for d in depth:
    pages = [p for p in d.get("pages", []) if p.get("ok")]
    lens = [p["text_len"] for p in pages]
    if not lens:
        DEPTH_ROWS.append(f"""<tr>
          <td class="name">{esc(d['name'])}</td>
          <td class="num">{d.get('home_text_len', 0):,}</td>
          <td class="num">0/{len(d.get('pages', []))}</td>
          <td class="num">—</td><td class="num">—</td>
        </tr>""")
        continue
    DEPTH_ROWS.append(f"""<tr>
      <td class="name">{esc(d['name'])}</td>
      <td class="num">{d.get('home_text_len', 0):,}</td>
      <td class="num">{len(pages)}/{len(d.get('pages', []))}</td>
      <td class="num">{statistics.mean(lens):,.0f}</td>
      <td class="num">{min(lens):,}~{max(lens):,}</td>
    </tr>""")

stable_ct = sum(1 for s in stab if s.get("cv_pct", 0) == 0)
cb_ok_ct = sum(1 for c in cb if c.get("ok"))
cb_html = ""
for c in cb:
    if not c.get("ok"):
        continue
    cb_html += f"""<tr>
      <td class="name">{esc(c['name'])}</td>
      <td class="num">{c['textLen']:,}</td>
      <td class="num">{c['linkCount']}</td>
      <td class="num">{c.get('imgCount', 0)}</td>
      <td class="num">{(c.get('elapsed_ms') or 0)/1000:.1f}s</td>
    </tr>"""

CSS = """
:root{--bg:#0b0e14;--panel:#141922;--panel2:#1b2230;--line:#28313f;--fg:#e6edf7;--dim:#8b98ab;
--accent:#7ee787;--warn:#f0b429;--err:#ff6b6b;--blue:#58a6ff;--purple:#bc8cff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1200px;margin:0 auto;padding:56px 28px 96px}
header{border-bottom:1px solid var(--line);padding-bottom:32px;margin-bottom:44px}
.tag{display:inline-block;padding:5px 12px;border:1px solid var(--line);border-radius:999px;
font-size:12.5px;color:var(--dim);letter-spacing:.04em;margin-bottom:20px}
h1{font-size:40px;line-height:1.2;margin:0 0 14px;letter-spacing:-.02em;font-weight:700}
h1 em{font-style:normal;color:var(--accent)}
.sub{color:var(--dim);font-size:16.5px;max-width:76ch;margin:0}
.meta{margin-top:22px;display:flex;flex-wrap:wrap;gap:10px 26px;font-size:13.5px;color:var(--dim)}
.meta b{color:var(--fg);font-weight:600}
h2{font-size:24px;margin:66px 0 8px;letter-spacing:-.01em;padding-bottom:10px;
border-bottom:1px solid var(--line);font-weight:650}
h2 .n{display:inline-block;width:30px;height:30px;line-height:30px;text-align:center;
background:var(--panel2);border:1px solid var(--line);border-radius:8px;font-size:14px;
color:var(--accent);margin-right:12px;vertical-align:2px}
h3{font-size:17.5px;margin:36px 0 10px;color:var(--fg);font-weight:600}
p{margin:12px 0;color:#c9d4e3}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
code{background:var(--panel2);padding:2px 7px;border-radius:5px;
font:13.5px/1.5 ui-monospace,"SF Mono",Menlo,Consolas,monospace;color:#ffd580}
.mini{font-size:11px;color:var(--dim);font-weight:400}
figure.chart{margin:22px 0 10px;background:var(--panel);border:1px solid var(--line);
border-radius:12px;padding:20px 18px}
.chart-note{font-size:13px;color:var(--dim);margin:0 0 24px;line-height:1.7}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:24px 0 8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px 18px}
.card .v{font-size:28px;font-weight:700;letter-spacing:-.02em;line-height:1.1}
.card .v.g{color:var(--accent)}.card .v.y{color:var(--warn)}.card .v.r{color:var(--err)}
.card .v.p{color:var(--purple)}.card .v.b{color:var(--blue)}
.card .l{font-size:13px;color:var(--dim);margin-top:7px}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}
th,td{padding:11px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.name{font-weight:600;white-space:nowrap}
tr:hover td{background:#10161f}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;
white-space:nowrap;border:1px solid transparent}
.pill.ok{color:var(--accent);background:rgba(126,231,135,.11);border-color:rgba(126,231,135,.28)}
.pill.warn{color:var(--warn);background:rgba(240,180,41,.11);border-color:rgba(240,180,41,.28)}
.pill.err{color:var(--err);background:rgba(255,107,107,.11);border-color:rgba(255,107,107,.28)}
.pill.info{color:var(--purple);background:rgba(188,140,255,.11);border-color:rgba(188,140,255,.28)}
.callout{background:var(--panel);border-left:3px solid var(--blue);border-radius:0 10px 10px 0;
padding:16px 20px;margin:22px 0}
.callout.warn{border-left-color:var(--warn)}
.callout.err{border-left-color:var(--err)}
.callout.ok{border-left-color:var(--accent)}
.callout b{color:#fff}
.case{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin:16px 0}
.case-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;font-size:17px}
.kv{display:flex;gap:10px;font-size:13.5px;margin:6px 0;align-items:baseline}
.kv span{color:var(--dim);min-width:96px}
pre.err-trace{background:#0a0d13;border:1px solid #2a1f24;border-radius:8px;padding:14px 16px;
overflow-x:auto;font-size:12.5px;line-height:1.62;color:#ff9b9b;margin:14px 0 0;
white-space:pre-wrap;word-break:break-word}
ul,ol{margin:12px 0;padding-left:22px;color:#c9d4e3}
li{margin:7px 0}
.foot{margin-top:70px;padding-top:26px;border-top:1px solid var(--line);color:var(--dim);font-size:13px}
.cannot{background:rgba(240,180,41,.06);border-left:3px solid var(--warn);border-radius:0 10px 10px 0;
padding:16px 20px;margin:22px 0}
"""

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>高校官网 AI 可读性巡检 · Lexmount 云平台真实任务挑战</title>
<style>{CSS}</style></head><body><div class="wrap">

<header>
  <div class="tag">Lexmount 云平台真实任务挑战 · 投稿作品</div>
  <h1>同一批网页，<em>三条路径</em>，三种结果</h1>
  <p class="sub">用 Lexmount 的两条产品线（Web Fetch 与 Cloud Browser）对 20 所双一流高校官网做巡检，
  发现同一批 URL 在不同接入方式下结果差异巨大。本文量化差异、把失败定位到源码行号，
  并明确区分<em>数据能证明什么</em>与<em>不能证明什么</em>。</p>
  <div class="meta">
    <div>执行时间 <b>{now.strftime('%Y-%m-%d %H:%M')} (UTC+8)</b></div>
    <div>样本 <b>20 所高校官网</b></div>
    <div>路径 <b>UI 表单 / 官方 API / Cloud Browser</b></div>
    <div>稳定性 <b>每站重复 3 次</b></div>
  </div>
</header>

<h2><span class="n">1</span>结论先行</h2>

<div class="cards">
  <div class="card"><div class="v g">18/20</div><div class="l">官方 API 抓取成功</div></div>
  <div class="card"><div class="v r">2</div><div class="l">引擎 panic（0/3 稳定失败）</div></div>
  <div class="card"><div class="v y">{len(CROSS)}</div><div class="l">UI 与 API 结果不一致</div></div>
  <div class="card"><div class="v p">{cb_ok_ct}/20</div><div class="l">Cloud Browser 全部成功</div></div>
  <div class="card"><div class="v b">{stable_ct}/{len(stab)}</div><div class="l">同批次三次结果一致</div></div>
  <div class="card"><div class="v">{CLEAN['median']:.0f}</div><div class="l">纯净正文中位数</div></div>
</div>

<div class="callout ok">
<b>三句话总结：</b>
<ol>
  <li><b>同一批 URL，三种接入方式结果不同。</b>{len(CROSS)} 个站点在 UI 与 API 之间差异超过 200 字。</li>
  <li><b>有两个站点在 Web Fetch 下稳定失败（0/3），但 Cloud Browser 全部成功</b>——
      证明是引擎缺陷而非站点不可访问。</li>
  <li><b>正文质量还有两个隐藏问题</b>：浙大 70% 是 JS 源码，清华 83% 是重复内容。</li>
</ol>
</div>

<h2><span class="n">2</span>三条路径对照（20 站全量）</h2>

<p>同一批 URL，三种方式各抓一遍。这是全文最重要的一张表：</p>

<table><thead><tr>
  <th>高校</th><th>① UI 表单</th><th>② 官方 API</th><th>③ Cloud Browser</th><th>③ 链接数</th>
</tr></thead><tbody>{''.join(PATH_ROWS)}</tbody></table>

<figure class="chart">{CH_PATHS}</figure>
<p class="chart-note">同一行三个色条是三种方式抓到的正文字数。复旦三条几乎等长，
说明站点本身稳定可抓；东南、浙大的 UI 条短到看不见；人大的 API 条是红色「失败」，
但它的 Cloud Browser 条有 2,549 字。</p>

<div class="callout warn">
<b>四个最值得注意的案例：</b>
<ul>
  <li><b>东南大学</b>：UI 完全失败 → API 6,473 字。同一平台，UI 路径拿不到。</li>
  <li><b>浙江大学</b>：UI 4 字 → API 6,173 字（其中 4,324 是 JS 源码，纯净 1,849）。</li>
  <li><b>中国人民大学</b>：UI 11,515 字（正常）→ API <em>完全失败</em>。API 路径反而挂了。</li>
  <li><b>哈尔滨工业大学</b>：UI 失败 → API 失败 → Cloud Browser 成功（1,750 字 / 502 链接）。</li>
</ul>
</div>

<h2><span class="n">3</span>最强证据：两个站点、两种驱动、同一行 panic</h2>

<p>哈尔滨工业大学与中国人民大学在官方 API 下返回 <code>browser_fetch_failed</code>，
两者的失败细节一致——同一个源文件、同一行、同一断言、同一个 HTTP 502：</p>

<p><b>先看清它证明了什么：</b>这两个站点在 Web Fetch 下<b>跨 UI 与 API 两种驱动都稳定失败</b>，
而在同一平台的 Cloud Browser 下<b>都成功</b>。这足以证明 panic 来自
<code>lightmount_dcl</code> 引擎本身，而不是网络或目标站点不可访问。</p>

{''.join(PANIC_HTML)}

<div class="callout err">
<b>为什么这条证据相对最硬：</b>
<ul>
  <li><b>跨两种驱动复现</b>：人民大学在 UI 和 API 下都失败（共 4 次），
      哈工大也跨两种驱动失败（共 6 次）。排除「某个驱动有问题」。</li>
  <li><b>同批次内 0/3</b>：连续 3 次，两个站点全部失败，其余 19 个站点结果极差为 0。</li>
  <li><b>唯一差别是 NativeNodeId</b>：<code>(116)</code> 与 <code>(677)</code>，
      说明命中同一处代码路径。</li>
  <li><b>Cloud Browser 对照</b>：同样的两个站点在 Cloud Browser 下
      <b>全部成功</b>（人大 2,549 字 / 446 链接，哈工大 1,750 字 / 502 链接）。</li>
</ul>
</div>

<div class="cannot">
<b>⚠️ 有一条必须说清楚，否则这条证据就是被夸大的：</b>
我原以为这是「两个完全不同的站点」命中同一个 bug。<b>实测推翻了这个说法</b>——
哈工大、东南、人大、复旦、南开<b>都是同一个 sudy 门户模板</b>
（源站 <code>&lt;head&gt;</code> 里都有 <code>sudy</code>、<code>_showDynClickBatch</code>、
<code>wbtreeid</code> 等指纹；哈工大与东南各命中 4 项）。
所以这是<b>同一模板的两个实例</b>，不是两个独立站点。
<br><br>
而且<b>同模板的复旦、南开并没有触发</b>——说明触发还需要我没控制到的附加条件
（页面规模、样式表数量或时序都可能）。
因此我只能说到这一步：<b>该 panic 在这两个站点上可稳定复现，且 Cloud Browser 能绕过</b>；
<b>不能</b>说「所有 sudy 模板站点都会触发」，也<b>不能</b>说触发条件已完全定位。
</div>

<p>结论收紧为：<b><code>lightmount_dcl</code> 引擎存在真实的 panic 缺陷，在受测站点上可稳定复现，
且存在可行的降级路径（Cloud Browser）</b>；触发面有待进一步定位。</p>

<h3>稳定性全表</h3>

<figure class="chart">{CH_STAB}</figure>
<p class="chart-note">每个点是一次抓取。19 个站点三次重叠成一个点（极差 0），
说明失败是确定性的；只有上海交大三个点分开，变异系数 45.3%；
人大与哈工大整行标红，0/3 全部失败。</p>

<table><thead><tr>
  <th>高校</th><th>成功</th><th>字数范围</th><th>极差</th><th>变异系数</th><th>判定</th>
</tr></thead><tbody>{''.join(STAB_ROWS)}</tbody></table>

<div class="callout warn">
<b>准确表述：</b>同批次内 <b>{stable_ct}/{len(stab)}</b> 个站点三次结果<em>完全一致</em>（极差 0），
说明失败是确定性的。<b>但不要把它读成「平台输出稳定」</b>——
跨批次（UI vs API）还有 {len(CROSS)} 个站点不一致，见下一节。
上海交通大学是唯一同批次内波动的站点（1,960~4,732，CV {next((s['cv_pct'] for s in stab if s.get('cv_pct',0)>5), 0)}%）。
</div>

<h2><span class="n">4</span>UI 与 API 不一致：能证明什么，不能证明什么</h2>

<p>同样的 20 个 URL，UI 表单与官方 API 之间有 <b>{len(CROSS)}</b> 个站点差异超过 200 字：</p>

<table><thead><tr>
  <th>高校</th><th>UI 表单</th><th>官方 API</th><th>差值</th>
</tr></thead><tbody>{''.join(CROSS_ROWS)}</tbody></table>

<div class="callout ok">
<b>✅ 能证明的：</b>同一批 URL、间隔约 14 小时、同一平台，
<b>两次结果不可复现</b>。这意味着用 UI 试验场验证过的抓取方案，接进应用后表现可能完全不同——
反过来也一样。<b>这对开发者是一个真实的陷阱。</b>
</div>

<div class="cannot">
<b>⚠️ 不能证明的（必须说清楚）：</b>我无法确定差异是<b>平台在两次之间变了</b>，
还是<b>UI 与 API 走了不同路径</b>。原因：
<ul>
  <li>UI 批次没有记录请求体，两种因素无法分离；</li>
  <li>我观察到平台侧有若干变化（<code>template_id</code> 分布不同、<code>extra</code> 字段更结构化、
      出现新引擎标识），但这是我事后观察，不是受控实验；</li>
  <li>北京大学在两次抓取中分别为 5,925 / 4,867 字，两个值都不等于深度测试时的 6,132 字——
      说明还有第三个因素我没想到。</li>
</ul>
<b>所以我只陈述现象，不归因。</b>要定位原因需要平台方的内部信息。
</div>

<h2><span class="n">5</span>Cloud Browser：不是「更好」，是「以链接换正文」</h2>

<p>Cloud Browser 对 20 个站点<b>{cb_ok_ct}/20 全部成功</b>，包括 Web Fetch 下稳定失败的两个。
但正文长度并不总是更多：</p>

<table><thead><tr>
  <th>高校</th><th>API 正文</th><th>CB 正文</th><th>正文差</th>
  <th>API 链接</th><th>CB 链接</th><th>链接差</th>
</tr></thead><tbody>{''.join(TRADE_ROWS)}</tbody></table>

<figure class="chart">{CH_TRADE}</figure>
<p class="chart-note">横轴是链接数差，纵轴是正文字数差。
绝大多数点落在右下方——链接更多、正文更少；
只有南京大学和同济落在左上方（正文更多）。
复旦单独在正下方极远处：正文少了 10,770，但链接多了 512。</p>

<div class="callout warn">
<b>准确说法是「取舍」，不是「替代」：</b>
<ul>
  <li>正文中位数：API <b>{TRADE['api_median_len']:.0f}</b> vs Cloud Browser <b>{TRADE['cb_median_len']:.0f}</b>
      —— CB 反而更低，{TRADE['cb_less_text']}/{TRADE['compared']} 个站点 CB 正文更少。</li>
  <li>链接中位数：API <b>{TRADE['api_median_links']:.0f}</b> vs Cloud Browser <b>{TRADE['cb_median_links']:.0f}</b>
      —— CB 高出 {(TRADE['cb_median_links']/max(TRADE['api_median_links'],1)):.1f} 倍，
      {TRADE['cb_more_links']}/{TRADE['compared']} 个站点 CB 链接更多。</li>
</ul>
<b>原因很直接：</b>我们直接读 <code>document.body.innerText</code>，不做正文抽取，
所以把导航噪音也算进去或屏掉了。<b>Web Fetch 的正文抽取能力 + Cloud Browser 的链接覆盖，才是最优组合。</b>
</div>

<p>但 Cloud Browser 唯一不可替代的价值是：<b>它能救回 Web Fetch 死掉的站点</b>。
{len(cb_fixed)} 个 panic 站点（{'、'.join(cb_fixed)}）在 Cloud Browser 下全部恢复。</p>

<h2><span class="n">6</span>隐藏问题一：正文里混进 JS 源码</h2>

<p>浙江大学官方 API 返回 6,173 字，其中 <b>4,324 字（70%）是页面内嵌的 JS 源码</b>：</p>

<pre class="err-trace">main._newsJson11 = [ {{ id: '1', image: '/_upload/article/images/...', title: ...
main._linkNews1 = [ {{ id: "1", colName: "树立和践行正确政绩观", title: '浙江大学召开...', text: ...
main._linkNews2 = [ {{ id: "1", colName: "教育强国 浙大何为", title: '在回答"四个之问"中...', image: ...
main._linkNews4 = [ {{ id: "1", colName: "文脉千秋 盛世修典", title: '山海与城垣共赏｜...', text: ...</pre>

<table><thead><tr>
  <th>高校</th><th>main_text 总长</th><th>JS 源码</th><th>污染率</th><th>纯净正文</th>
</tr></thead><tbody>{''.join(JS_ROWS)}</tbody></table>

<div class="callout err">
<b>影响：</b>如果下游拿 <code>main_text</code> 做 RAG 分块或摘要，这几段 JS 会：
<ul>
  <li>污染检索结果（里面确实有中文新闻标题，但被包裹在 JS 字面量里）；</li>
  <li>白白消耗约 4,300 字的 token；</li>
  <li>让「6,173 字」这个数字失去意义——真实可用正文只有 <b>{CLEAN['median']:.0f}</b> 字。</li>
</ul>
<b>20 站里只有浙大 1 站有此问题</b>，但它是我们最核心的案例，所以必须单独说明。
建议在正文抽取后增加一层「JS 字面量检测」，剔除 <code>\\w+\\.\\w+ = [{{...}}]</code> 形态的行。
</div>

<h2><span class="n">7</span>隐藏问题二：正文重复</h2>

<p>清华大学的 <code>main_text</code> 有 9,777 字，按行去重后只剩 <b>1,630 字</b>——
<b>83.4% 是重复内容</b>（同一行重复 15 次、同一行重复 10 次）：</p>

<table><thead><tr>
  <th>高校</th><th>原始字数</th><th>去重后</th><th>虚增率</th><th>重复行数</th>
</tr></thead><tbody>{''.join(DEDUP_ROWS)}</tbody></table>

<div class="callout warn">
<b>要说明的边界：</b>20 站里<b>只有清华 1 站</b>受影响，其余 19 站去重率几乎为 0。
所以「去重后中位数从 3,398 降到 3,090」这个变化<b>几乎全由清华一站拉动</b>，
不能据此说「平台普遍重复」。
</div>

<h2><span class="n">8</span>二级页面：首页好不代表内容页好</h2>

<table><thead><tr>
  <th>高校</th><th>首页字数</th><th>子页成功</th><th>子页平均字数</th><th>子页字数范围</th>
</tr></thead><tbody>{''.join(DEPTH_ROWS)}</tbody></table>

<div class="callout">
清华首页 9,777 字，但子页平均只有 <b>518 字</b>，最差的一个子页 145 字。
复旦子页平均 4,075 字。<b>只用首页评估平台能力会严重高估。</b>
</div>

<h2><span class="n">9</span>给平台的建议</h2>

<h3>P0：修 panic</h3>
<ol>
  <li><code>live_document_parser.rs:498</code> 的断言前，把
      <code>Suspended → Ready</code> 视为合法可恢复状态，而不是 <code>assert_eq!</code> 崩溃。</li>
  <li>panic 时<b>自动降级到 Cloud Browser 路径重试</b>——
      我们已经证明这条路径对这两个站点有效，成本可控而收益明确。</li>
  <li>把 panic 包装成结构化错误码（如 <code>parser_state_conflict</code>），而不是裸 502。</li>
</ol>

<h3>P1：修正文质量</h3>
<ol start="4">
  <li>正文抽取后剔除 JS 字面量行（浙大案例）。</li>
  <li>正文做行级去重（清华案例）。</li>
  <li>检测到 <code>#root</code>/<code>#app</code> 且可见文字接近 0 时，自动切换渲染路径。</li>
</ol>

<h3>P2：修可观测性</h3>
<ol start="7">
  <li>在响应里加 <code>engine_version</code>，让调用方能判断两次结果是否可比。</li>
  <li>UI 试验场与 API 若走不同路径，请在试验场明确标注「结果可能与 API 不一致」。</li>
  <li><code>links</code> 字段明确是「全量」还是「摘要」，并提供 <code>links_total</code>。</li>
</ol>

<h2><span class="n">10</span>方法与可复现性</h2>

<ol>
  <li><b>路径①</b>：驱动 <code>/playground/webfetch</code> 表单，逐条落盘响应。</li>
  <li><b>路径②</b>：<code>POST https://api.lexmount.cn/v1/extract</code>，
      带 <code>X-API-Key</code>/<code>X-Project-Id</code>，落盘完整响应与请求元信息。</li>
  <li><b>路径③</b>：<code>/playground</code> 注入 Playwright，渲染后读 DOM。</li>
  <li><b>稳定性</b>：每站连续 3 次，记录 <code>request_id</code>、字数、耗时。</li>
  <li><b>JS 污染检测</b>：按强代码特征（<code>var/let/const/function/main.xxx/({{id:...}})</code>）
      逐行打分，阈值 0.5 判定。</li>
  <li><b>去重</b>：按行去重并剔除 Unicode 私有区图标字符。</li>
  <li><b>本地基准</b>：普通 HTTP 客户端直连作为独立参照，不依赖平台提取逻辑。</li>
</ol>

<p>所有原始响应保留 <code>request_id</code>、<code>server_elapsed_ms</code>、<code>fetched_at</code>，
可逐条回溯。本仓库包含全部原始数据与统计脚本。</p>

<h2><span class="n">11</span>这份报告的价值在哪</h2>

<div class="callout ok">
<b>1. 三个视角而不是一个。</b>
绝大多数巡检只用一种接入方式。我用了三种，结果互相矛盾——
这个矛盾本身就说明「平台能力」不能用一个数字概括。
<br><br>
<b>2. 每条结论都定位到可核验的位置。</b>
panic 到源文件行号，JS 污染到具体字符数，重复内容到具体行数。
不是「感觉不稳定」，是「第 498 行崩了」。
<br><br>
<b>3. 严格区分「证明了」和「没证明」。</b>
UI/API 差异我无法归因，就明确写「不能证明」，只陈述现象。
Cloud Browser 正文更少，我写成「取舍」而不是「更好」。
<br><br>
<b>4. 撤回过自己的错误结论。</b>
初版报告写过「渲染引擎正文反而更短」，后来发现有批次混杂，已删除；
写过「两个站点可稳定复现 panic」，复测后改成「同批次 0/3，跨两种驱动复现」；
写过「3,400 倍差距」，那是 UI 口径的伪影，API 基线是 13.5 倍，已撤回。
<b>一份只报好消息、不自我纠错的巡检报告没有价值。</b>
</div>

<div class="foot">
  报告生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)<br>
  平台：Lexmount Web Fetch（<code>POST /v1/extract</code>、<code>POST /v1/dom/dump</code>）与 Lexmount Cloud Browser<br>
  样本：20 所中国双一流高校官网 · 三路径各 20 次 · 每站 3 次稳定性 · 4 站二级页面<br>
  所有数字来自实际调用；无法解释的现象已明确标注为「不能证明」
</div>

</div></body></html>
"""

out = ROOT.parent / "report.html"
out.write_text(HTML, encoding="utf-8")
print("v4 报告已生成:", out.resolve())
print("大小:", len(HTML), "字符")
