#!/usr/bin/env node
/**
 * depth_test.mjs — 二级页面深度测试：首页链接进去，看提取质量是否下降。
 *
 *   node depth_test.mjs [maxSites] [pagesPerSite]
 *
 * 步骤：读首页 extract 结果 → 挑正文类链接 → 逐个 extract → 统计成功率
 * 结果写 runs/depth/<slug>.json
 */
import fs from 'node:fs';
import path from 'node:path';

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const MAX_SITES = Number(process.argv[2] || 5);
const PER_SITE = Number(process.argv[3] || 3);
const OUTDIR = path.join(HERE, '..', 'runs', 'depth');
fs.mkdirSync(OUTDIR, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pend = new Map();
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.error ? { __err: m.error } : m.result);
    pend.delete(m.id);
  }
};
const send = (method, params = {}) =>
  new Promise((res) => {
    const i = ++id;
    pend.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });

async function evaluate(expression) {
  const r = await send('Runtime.evaluate', {
    expression, returnByValue: true, awaitPromise: true, userGesture: true,
  });
  if (r.__err) throw new Error(JSON.stringify(r.__err));
  if (r.exceptionDetails) {
    throw new Error('JS: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
  }
  return r.result.value;
}

async function clickByText(text) {
  const box = await evaluate(`(() => {
    const want = ${JSON.stringify(text)};
    const cands = [...document.querySelectorAll('body *')].filter((e) => {
      const t = (e.innerText || '').trim();
      if (t !== want) return false;
      const r = e.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) return false;
      const st = getComputedStyle(e);
      return st.visibility !== 'hidden' && st.display !== 'none';
    });
    const el = cands.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length)[0];
    if (!el) return null;
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  if (!box) throw new Error('not found: ' + text);
  const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
}

async function setUrl(u) {
  const fill = () => evaluate(`(() => {
    const el = document.querySelector('#webfetch-url');
    if (!el) return 'NOT_FOUND';
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    el.focus();
    setter.call(el, ${JSON.stringify(u)});
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return el.value;
  })()`);
  let v = await fill();
  for (let i = 0; i < 10 && v !== u; i++) {
    await sleep(400);
    v = await fill();
  }
  if (v !== u) throw new Error('fill failed');
  await sleep(400);
}

const readResponse = () => evaluate(`(() => {
  const p = [...document.querySelectorAll('pre')]
    .map((e) => e.innerText).filter((t) => t.trim().startsWith('{'));
  const c = p.filter((t) => t.includes('"request_id"') || t.includes('metadata'));
  return c.length ? c[c.length - 1] : '';
})()`);

/** 一次完整的 extract 调用 */
async function fetchOne(u) {
  await setUrl(u);
  const before = await readResponse();
  await clickByText('运行请求');
  let out = '';
  for (let i = 0; i < 120; i++) {
    await sleep(500);
    const cur = await readResponse();
    if (cur && cur !== before) { out = cur; break; }
  }
  if (!out) throw new Error('timeout');
  return JSON.parse(out);
}

// 等页面就绪
const cur = await evaluate('location.href');
if (!cur.includes('/playground/webfetch')) {
  await send('Page.navigate', { url: 'https://browser.lexmount.cn/playground/webfetch' });
}
for (let i = 0; i < 120; i++) {
  if (await evaluate(`!!document.querySelector('#webfetch-url')`).catch(() => false)) break;
  await sleep(500);
}

const sites = JSON.parse(
  fs.readFileSync(path.join(HERE, '..', 'sites.json'), 'utf8')
).sites.slice(0, MAX_SITES);

/** 从首页 links 里挑出像"内容页"的链接 */
function pickContentLinks(links, baseUrl) {
  const host = new URL(baseUrl).host.replace(/^www\./, '');
  const scored = [];
  for (const l of links) {
    const href = l.href || '';
    const text = (l.text || '').trim();
    if (!href.startsWith('http')) continue;
    let u;
    try { u = new URL(href); } catch { continue; }
    if (u.host.replace(/^www\./, '') !== host) continue;  // 同站
    if (/\.(pdf|jpg|png|zip|doc|docx|xls|xlsx|ppt|pptx|rar|mp4|mp3)$/i.test(u.pathname)) continue;
    if (/#/.test(href)) continue;
    if (!text || text.length < 4) continue;
    // 内容页特征：info/ news/ article/ content/ detail/ .htm/.html 且路径较深
    let score = 0;
    if (/\/info\/|\/news\/|\/article\/|\/content\/|\/detail\/|\/tzgg\//.test(u.pathname)) score += 3;
    if (/\.(htm|html|shtml|jsp|php)$/i.test(u.pathname)) score += 1;
    if (u.pathname.split('/').filter(Boolean).length >= 2) score += 1;
    if (text.length >= 8) score += 1;
    scored.push({ score, url: href, text });
  }
  scored.sort((a, b) => b.score - a.score);
  // 去重同路径前缀
  const seen = new Set();
  const out = [];
  for (const s of scored) {
    const key = s.url.replace(/[?#].*$/, '');
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(s);
    if (out.length >= PER_SITE) break;
  }
  return out;
}

const all = [];

for (const site of sites) {
  console.log(`\n=== ${site.name} ===`);
  const rec = { slug: site.slug, name: site.name, home: site.url, pages: [] };

  let home;
  try {
    home = await fetchOne(site.url);
  } catch (e) {
    console.log(`  首页失败: ${e.message}`);
    rec.home_error = e.message;
    all.push(rec);
    continue;
  }

  const homeRes = home.result || {};
  rec.home_text_len = (homeRes.main_text || '').length;
  rec.home_links = (homeRes.links || []).length;
  console.log(`  首页: ${rec.home_text_len} 字, ${rec.home_links} 链接`);

  const picks = pickContentLinks(homeRes.links || [], site.url);
  console.log(`  挑选 ${picks.length} 个内容页`);

  for (const p of picks) {
    process.stdout.write(`    ${p.text.slice(0, 24).padEnd(26)} `);
    try {
      const r = await fetchOne(p.url);
      const rr = r.result || {};
      const len = (rr.main_text || '').length;
      rec.pages.push({
        url: p.url,
        text: p.text,
        ok: true,
        status: rr.status_code,
        text_len: len,
        link_count: (rr.links || []).length,
        title: (rr.title || '').slice(0, 60),
        server_ms: r.metadata?.server_elapsed_ms ?? null,
      });
      console.log(`ok ${rr.status_code} ${len} 字`);
    } catch (e) {
      rec.pages.push({ url: p.url, text: p.text, ok: false, err: e.message });
      console.log(`FAIL ${e.message}`);
    }
  }

  all.push(rec);
  fs.writeFileSync(
    path.join(OUTDIR, `${site.slug}.json`),
    JSON.stringify(rec, null, 2),
    'utf8'
  );
}

console.log('\n===== 汇总 =====');
for (const r of all) {
  const ok = r.pages.filter((p) => p.ok).length;
  const lens = r.pages.filter((p) => p.ok).map((p) => p.text_len);
  const avg = lens.length ? Math.round(lens.reduce((a, b) => a + b, 0) / lens.length) : 0;
  console.log(
    `${r.name.padEnd(12)} 首页 ${String(r.home_text_len ?? '-').padStart(6)} 字 | ` +
    `子页 ${ok}/${r.pages.length} 成功, 平均 ${avg} 字`
  );
}

fs.writeFileSync(
  path.join(OUTDIR, '_summary.json'),
  JSON.stringify(all, null, 2),
  'utf8'
);
ws.close();
