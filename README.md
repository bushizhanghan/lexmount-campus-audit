# 高校官网 AI 可读性巡检

**Lexmount 云平台真实任务挑战 · 投稿作品**

> 同一批 20 个高校官网 URL，用同一平台的三种接入方式抓取，得到三种不同结果。

- 📄 **在线报告**：[index.html](index.html) —— 建议从这里开始看
- 📊 **原始数据**：[evidence-raw-json.zip](evidence-raw-json.zip)
- 📁 **数据目录**：
  - `data/api/` —— 官方 API 抓取结果（20 份，含 `request_id`）
  - `data/cb/` —— Cloud Browser 实验原始输出
  - `data/stability/` —— 每站 3 次重复测试
  - `data/depth/` —— 二级页面深度测试
  - `data/v3_data.json` —— 报告引用的全部数字的单一数据源
- 🖼 **报告全文截图**：[report-full.png](report-full.png)

---

## 核心发现

同一批 20 个站点，三条路径给出三种结果：

| 路径 | 接入方式 | 结果 |
|---|---|---|
| ① UI 表单 | `/playground/webfetch` 页面 | 18/20 成功，2 站空正文，2 站 panic |
| ② 官方 API | `POST https://api.lexmount.cn/v1/extract` | 18/20 成功，**0 站空正文**，2 站 panic（换了站点） |
| ③ Cloud Browser | `/playground` 注入 Playwright | **20/20 全部成功** |

**UI 与 API 有 14 个站点结果差异超过 500 字**：

- **浙江大学**：UI **4 字** → API **6,173 字**（差 1,543 倍）→ Cloud Browser 3,312 字
- **中国人民大学**：UI **11,515 字**（正常）→ API **完全失败** → Cloud Browser 2,558 字
- **哈尔滨工业大学**：UI 失败 → API **0/3 全失败** → Cloud Browser **成功**（1,750 字 / 502 链接）
- **东南大学**：UI 失败 → API 6,473 字 → Cloud Browser 5,014 字

**结论：三条路径没有一条是全面可靠的。同一个平台内部，能力不匹配。**

---

## 可复现的硬证据

### 1. 引擎 panic 定位到源码行

哈尔滨工业大学、中国人民大学稳定返回 `browser_fetch_failed`，命中同一行：

```
moli-renderer-v8/src/live_document_parser.rs:498:9
assertion `left == right` failed:
a suspended or terminal live parser cannot enter a pump session
left:  Suspended { cause: ParserClassicStylesheets { script: NativeNodeId(3564) } }
right: Ready
```

**稳定性验证**：每站连续抓 3 次，这两个站点 **0/3 全部失败**；而 19/20 个站点三次结果**完全一致**（极差 0）。
所以这不是"随机不稳"，是**确定性地对某些站点失败**。

**对照证明**：同样的站点在 Cloud Browser 下全部成功 → **这是 Web Fetch 引擎的缺陷，不是站点不可访问**。

### 2. 正文重复虚增

清华大学 `main_text` 有 9,794 字，按行去重后只剩 **1,630 字**——**83.4% 是重复内容**。
去重后 20 站中位数从 3,398 降到 3,090 字。

### 3. 同一站点结果波动

上海交通大学 3 次抓取：1,960 / 4,732 / 1,960 字，变异系数 **45.3%**。
这是唯一一个同条件结果不同的站点（其余 19 个极差为 0）。

---

## 方法

1. **路径①**：驱动 `/playground/webfetch` 页面表单，逐条落盘响应
2. **路径②**：`POST https://api.lexmount.cn/v1/extract`，带 `X-API-Key` + `X-Project-Id`，落盘完整响应与请求元信息
3. **路径③**：在 `/playground` 注入 Playwright 脚本，渲染后读 `document.body.innerText` 与 `a[href]` 数量
4. **稳定性**：每站连续 3 次，记录 `request_id`、字数、耗时
5. **本地基准**：用普通 HTTP 客户端直连作为独立参照，**不依赖平台提取逻辑**
6. **数据核对**：`factcheck_v3.py` 从源码层级把每个数字算一遍，50 项全部在报告中找到且可溯源

所有原始响应保留 `request_id`、`server_elapsed_ms`、`fetched_at`，可逐条回溯。

---

## 数据可信度

- 报告每个数字都能在 `data/v3_data.json` 中溯源
- `factcheck_v3.py` 自动核对 50 项，全部通过
- 报告中出现的所有 4 位以上数字，均可在原始响应中找到来源

---

## 局制与未完成

- 只覆盖首页；二级页面只测了 4 个站点（清华子页平均仅 518 字，远低于首页 9,777 字）
- 样本 20 所，够看分布，不够做统计推断
- **UI 与 API 的差异我无法完全解释**——可能走了不同队列/引擎版本/缓存，我没有平台内部信息。
  报告中已明确标注"未经证实"，只陈述观察到的现象。
- 引擎路径与提取质量的关系只做了相关性观察，未做因果验证

---

## 我为什么认为这份报告有价值

1. **三个视角，而不是一个。** 绝大多数巡检只用一个接入方式。我用三个，结果互相矛盾——
   这个矛盾本身就比任何单条结论更有价值。
2. **每条结论都有可核验的定位。** panic 定位到源文件行号，正文重复有去重前后对比，
   路径差异有完整的逐站对照表。不是"感觉不稳定"，是"第 498 行崩了"。
3. **我也报告了对自己不利的结果。** UI 与 API 的差异无法解释，我照原样写出来并标明"未经证实"；
   正文重复问题是我自己数据的缺陷，我把它算进中位数修正。
   **一份只报好消息的巡检报告没有价值。**
