# 高校官网 AI 可读性巡检

用 **Lexmount Web Fetch** 批量检查 20 所中国双一流高校官网，量化「Agent 能否稳定读到一个网页」，并对失败案例做根因定位。

## 一句话结论

20 所高校里 18 所能抓到（90%），但真正能让 Agent 直接用的只有 16 所。
剩下 4 所是**两类完全不同的失败**：2 所是客户端渲染的 SPA（页面本身没内容），2 所是抓取引擎内部 panic（平台该修的 bug）。

进一步深挖还发现了**第三类更隐蔽的问题**：`links` 字段返回不完整且不可预测——12 个受测站点里 9 个链接不全，中位缺失 38.9%。并且与裸 HTTP 抓取对照后发现，对这些非 SPA 站点，**云平台并没有抓到更多内容**，它的价值在结构化输出和省掉的解析工作。

## 目录结构

```
.
├── report.html                    # 最终报告 v2（自包含单文件，双击即可打开）
├── report-final.png               # 报告长截图
├── SUBMISSION.md                  # 投稿表单各字段的填写内容
├── evidence-raw-json.zip          # 20 份 extract + 3 份 dump 原始响应
├── README.md                      # 本文件
└── project/
    ├── sites.json                 # 20 所高校样本清单
    ├── drive.mjs                  # 批量执行（复用已加载页面，逐条落盘）
    ├── batch.mjs                  # 批量执行（每站重新导航，慢但更隔离）
    ├── analyze.py                 # 统计：成功率 / 正文字数 / 耗时分布
    ├── deep_analyze.py            # 深挖 links/meta/engine 字段
    ├── value_added.py             # 云平台 vs 裸抓的增值量化
    ├── verify_links_final.py      # links 完整性（本地基准，修正相对URL口径）
    ├── verify_links_groundtruth.py# links 完整性（初版，含未修正口径）
    ├── explain_overcount.py       # 解释"平台返回>本地<a>数"的矛盾
    ├── investigate_sjtu.py        # 上交案例：正文被选择性丢弃
    ├── verify_spa.py              # 本地直连复核 SPA 假设（不消耗额度）
    ├── verify_extra.py            # extra 字段 schema 差异
    ├── compare.py                 # extract vs dump 对照实验
    ├── enrich.py                  # 汇总深度分析 → enrich_data.json
    ├── report.py                  # 汇总 → report_data.json
    ├── render_report.py           # 渲染 report.html（v1）
    ├── render_report_v2.py        # 渲染 report.html（v2，当前版本）
    ├── factcheck.py               # v1 数字核对
    ├── factcheck_v2.py            # v2 数字核对（45 项）
    ├── tools/                     # 浏览器驱动的底层小工具
    ├── reference/                 # 活动页与文档的抓取存档
    └── runs/
        ├── extract/               # 20 份原始响应 JSON
        └── dump/                  # 3 份 dom/dump 响应
```

## 复跑方式

### 0. 一键 CLI（推荐）

巡检逻辑已抽成独立命令行工具，只依赖 Python 标准库：

```bash
# 跑官方 API 路径（需要 Key）
python audit.py --sites sites.json --path api \
  --key $env:LEXMOUNT_API_KEY --project $env:LEXMOUNT_PROJECT_ID

# 断点续跑 / 每站重复 3 次测稳定性
python audit.py --sites sites.json --path api --repeat 3 --out runs/audit

# 从已落盘数据重放（不发请求，用于复盘或改报告）
python audit.py --replay runs/api --out report-out
```

输出：
- `runs/audit/api/<slug>.json` — 每站点完整响应（含 `request_id`）
- `runs/audit/summary.json` — 汇总统计 + 多路径对照 + 稳定性
- `runs/audit/report.html` — 人类可读报告

本仓库的 `cli-demo-report.html` 就是用 `--replay` 模式从 `runs/api` 生成的真实示例。

### 1. 单站点抓取

```bash
cd project/tools
node webfetch.mjs https://www.zju.edu.cn extract
node webfetch.mjs https://www.zju.edu.cn dump
```

需要本机有 Edge/Chrome，脚本会自动拉起带调试端口的浏览器并驱动
`https://browser.lexmount.cn/playground/webfetch` 页面。

### 2. 批量巡检

```bash
cd project
node drive.mjs extract 20      # 跑 20 个站点
node drive.mjs dump 3          # 对前 3 个做 dump 对照
```

`drive.mjs` 不会重新导航（登录态下页面水合很慢），而是复用已加载好的页面，
只改目标 URL + 点运行 + 读结果，逐条写盘。中断后可断点续跑（已存在的跳过）。

### 3. 出报告

```bash
python analyze.py            # 终端统计
python report.py             # -> report_data.json
python enrich.py             # -> enrich_data.json（深度分析汇总）
python render_report_v2.py   # -> report.html（当前版本）
python factcheck_v2.py       # 核对 45 项数字，全部通过
```

### 4. 本地交叉验证（不消耗额度）

```bash
python verify_spa.py                  # 直连目标站点，对比 HTML 大小与可见文字
python verify_links_final.py          # links 完整性，与本地基准逐条比对
python value_added.py                 # 云平台 vs 裸抓的增值量化
python investigate_sjtu.py            # 上交案例：正文被选择性丢弃
```

这一步很重要：它用普通 HTTP 客户端独立验证「页面到底有什么」，
不依赖平台自身的提取逻辑，**避免自己验证自己**。

> ⚠️ **方法论提醒**：`verify_links_groundtruth.py` 是初版，直接字符串比对 href，
> 会因平台把相对 URL 规范化成绝对 URL 而误判（北师大、中科大出现"平台返回 > 本地"的矛盾）。
> 正确做法见 `verify_links_final.py`——先把两边 URL 规范化再比对。

## 数据口径

| 项目 | 说明 |
|---|---|
| 样本 | 20 所双一流高校官网首页 |
| 接口 | `POST /v1/extract`，对照实验用 `POST /v1/dom/dump` |
| 判定「正文为空」 | `main_text` 少于 200 字 |
| 判定「引擎异常」 | 响应无 `result`，含 `error.code` |
| 抓取时间 | 2026-10-19（北京时间） |

每条原始响应都保留 `request_id`、`server_elapsed_ms` 与 `debug.attempts`，
可逐条回溯。

## 主要发现

### 1. 空正文：SPA 导致，不是提取算法问题

浙江大学 `main_text` 只有 4 个字。用 `dom/dump` 拿回 88,480 字符 HTML，
去掉标签后可见文字仍然只有 4 个字 —— 说明 HTML 里本来就没有内容。
本地直连复核：`<body>` 有 87,546 字符，去标签后可见文字 0，页面含 `id="root"`。

### 2. 引擎 panic：可复现的平台缺陷

东南大学、哈尔滨工业大学返回 `browser_fetch_failed`，两个不同站点命中同一行：

```
moli-renderer-v8/src/live_document_parser.rs:498:9
assertion `left == right` failed:
a suspended or terminal live parser cannot enter a pump session
```

失败耗时 3–4.5 秒，远低于超时阈值，说明是解析阶段主动 abort。

### 3. 质量分布极不均匀

正文字数从 4 到 13,751，相差 3,400 倍。同样的调用方式，产出质量完全不可预期。
另外 `language` 字段在 20 站里出现 4 种取值（空 9 次、`zh-cn` 6 次、`en` 2 次、`zh-hans` 1 次），
中文站点有近一半没返回正确的中文标记，下游做多语言分流时不可靠。

### 4. links 返回不完整且不可预测（新发现）

用本地 HTTP 直连做基准（规范化 URL 后逐条比对，12 个站点）：

- **9/12 个站点链接不全**，中位缺失 38.9%，最高 78.4%
- 复旦：页面 310 个链接，平台只给 71 个
- 清华：页面 160 个，平台给 57 个；南大：页面 161 个，平台给 61 个
- 平台返回数在 57~94 之间浮动，**既不全，也没有可预测的上限或规则**

影响：任何依赖 `links` 做站点地图、入口发现、批量巡检的任务，都会静默漏掉
三到八成链接，而且调用方无法知道自己漏了多少。

### 5. 正文被选择性丢弃（新发现）

上海交大平台返回 1,865 字，本地裸抓可见文字 2,840 字，少 34%。
句子级比对：裸抓独有 19 条，平台独有仅 3 条。被丢掉的是徐汇校区『中院』、
闵行校区『李政道图书馆』的整段建筑介绍和校园新闻正文。

判断：平台把页面里的**长段落正文**当成了导航噪音过滤掉，只保留标题和列表。
对一个想读「学校介绍」的 Agent 来说，恰好丢掉了最有价值的部分。
这不是截断，是选择性丢失。

### 6. 一个诚实的负结果：云平台比裸抓强在哪（新发现）

10 个站点同站点对照，平台正文长度 / 裸抓可见文字的比值中位只有 **0.98x**
（范围 0.66x~1.30x），只有 1/10 个站点平台更长。

**对这些非 SPA 站点，云平台并没有抓到更多内容。** 裸抓 HTML 再自己清洗，
拿到的文字量和平台几乎一样。

增值在省掉的解析工作：18 个成功站点里平台额外返回了 201 个 headings、
194 个 paragraphs、130 个 lists、4 个 tables、9 个 forms、868 个 images。

结论：**平台的卖点是「结构化」而不是「抓得更多」**。
如实记录这一点，比包装成「抓取能力强 N 倍」更有用。

### 7. extra 字段 schema 不统一（新发现）

同一个 `extra` 字段在 18 个成功响应里有三种互不兼容的形态：
`dom_summary` 家族（15 个）、仅 `metadata`（2 个，恰好都是空正文站点）、
完全缺失（1 个，清华）。下游按固定 schema 解析会直接崩溃或静默跳过。

另外 `site_links` 与顶层 `links` 在所有站点内容完全相同（缺失率 0%），属于冗余字段。

还有一个反直觉现象：走 `lightmount_dcl`（渲染引擎）的 7 个站点，平均正文
反而比走 `lightmount_lite`（快速路径）的 11 个站点**更短**（约 3,100 vs 约 5,800 字）。

## 局限

- 只覆盖首页，未深入二级页面
- 样本 20 所，够看分布，不够做统计推断
- SPA 判定用启发式标记（`id="root"` 等），未逐个做运行时渲染验证
- 未测并发和重复调用的成功率波动
- 观察到 `language` 字段不稳定，但未深挖原因
- links 完整性只覆盖 12 个站点（受本地抓取耗时限制）
- 云平台 vs 裸抓的增值结论只覆盖 10 个站点，且都是非 SPA 站点
- 引擎路径与提取质量只做了相关性观察，没有做因果验证
- 上交案例是单站点深挖，未验证该现象在多少站点上出现

## 数据可信度

报告中每一个数字都由 `factcheck_v2.py` 与原始响应 JSON 逐条核对，
共 45 项，全部一致。原始响应含 `request_id`，可回溯。
