#!/usr/bin/env node
/**
 * drive.mjs — 复用同一个已加载好的 playground 页面批量跑。
 *
 *   node drive.mjs <extract|dump> [max]
 *
 * 与 batch.mjs 的区别：不重新导航（登录态水合很慢），
 * 复用当前标签页，只改目标 URL + 点运行 + 读结果。
 * 逐条落盘，已存在则跳过，可断点续跑。
 */
import fs from 'node:fs';
import path from 'node:path';

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const MODE = (process.argv[2] || 'extract').toLowerCase();
const MAX = Number(process.argv[3] || 999);
const OUTDIR = path.join(HERE, 'runs', MODE);
fs.mkdirSync(OUTDIR, { recursive: true });

const config = JSON.parse(fs.readFileSync(path.join(HERE, 'sites.json'), 'utf8'));
const ENDPOINT = MODE === 'dump' ? 'POST /v1/dom/dump' : 'POST /v1/extract';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
if (!page) throw new Error('no page target');
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

async function realClick(selector) {
  const box = await evaluate(`(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) return null;
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`);
  if (!box) throw new Error('not found: ' + selector);
  const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
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
    const el = cands.sort((a,b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length)[0];
    if (!el) return null;
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    return { x: r.left + r.width/2, y: r.top + r.height/2 };
  })()`);
  if (!box) throw new Error('option not found: ' + text);
  const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
}

// ---- ensure the page is loaded and interactive ----
async function ensureReady() {
  const url = await evaluate('location.href');
  if (!url.includes('/playground/webfetch')) {
    await send('Page.navigate', { url: 'https://browser.lexmount.cn/playground/webfetch' });
  }
  for (let i = 0; i < 120; i++) {
    const ok = await evaluate(
      `!!document.querySelector('#webfetch-url') && !!document.querySelector('#webfetch-endpoint')`
    ).catch(() => false);
    if (ok) return true;
    await sleep(500);
  }
  throw new Error('webfetch page never became ready');
}

async function setEndpoint() {
  const cur = await evaluate(`document.querySelector('#webfetch-endpoint')?.innerText.trim()`);
  if (cur === ENDPOINT) return;
  await realClick('#webfetch-endpoint');
  await sleep(800);
  await clickByText(ENDPOINT);
  await sleep(800);
}

async function setUrl(u) {
  const fillOnce = () => evaluate(`(() => {
    const el = document.querySelector('#webfetch-url');
    if (!el) return 'NOT_FOUND';
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    el.focus();
    setter.call(el, ${JSON.stringify(u)});
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return el.value;
  })()`);
  let v = await fillOnce();
  for (let i = 0; i < 10 && v !== u; i++) {
    await sleep(400);
    v = await fillOnce();
  }
  if (v !== u) throw new Error('fill failed: ' + v);
  await sleep(500);
}

const readResponse = () => evaluate(`(() => {
  const p = [...document.querySelectorAll('pre')]
    .map((e) => e.innerText).filter((t) => t.trim().startsWith('{'));
  const c = p.filter((t) => t.includes('"request_id"') || t.includes('"html"') || t.includes('metadata'));
  return c.length ? c[c.length - 1] : '';
})()`);

await ensureReady();
await setEndpoint();
console.log('页面就绪，接口 =', ENDPOINT);

let done = 0, skipped = 0, failed = 0;
const t0 = Date.now();

for (const s of config.sites) {
  const file = path.join(OUTDIR, `${s.slug}.json`);
  if (fs.existsSync(file)) { skipped++; continue; }
  if (done >= MAX) { console.log(`\n达到本次上限 ${MAX}`); break; }

  process.stdout.write(`> ${s.name.padEnd(12)} `);
  const start = Date.now();
  try {
    await setUrl(s.url);
    const before = await readResponse();
    await clickByText('运行请求');

    let out = '';
    for (let i = 0; i < 120; i++) {
      await sleep(500);
      const cur = await readResponse();
      if (cur && cur !== before) { out = cur; break; }
      // 额度/错误提示
      const alertTxt = await evaluate(`(() => {
        const a = [...document.querySelectorAll('[role="alert"],[role="status"]')]
          .map(e => e.innerText.trim()).filter(Boolean);
        return a.join(' | ');
      })()`).catch(() => '');
      if (alertTxt && /失败|次数|用完|错误/.test(alertTxt)) {
        throw new Error('页面报错: ' + alertTxt);
      }
    }
    if (!out) throw new Error('等待响应超时');

    const parsed = JSON.parse(out);
    parsed._site = { slug: s.slug, name: s.name, url: s.url };
    parsed._run = {
      mode: MODE,
      ran_at: new Date().toISOString(),
      wall_ms: Date.now() - start,
    };
    fs.writeFileSync(file, JSON.stringify(parsed, null, 2), 'utf8');
    done++;
    const status = parsed.status_code ?? parsed.result?.status_code;
    console.log(`ok http=${status} ${(Date.now() - start) / 1000}s`);
  } catch (e) {
    failed++;
    fs.writeFileSync(path.join(OUTDIR, `${s.slug}.error.txt`),
      `url: ${s.url}\nerror: ${e.message}\n`, 'utf8');
    console.log(`FAIL ${(Date.now() - start) / 1000}s — ${e.message.slice(0, 80)}`);
    // 页面可能已经崩了，重新就绪
    try { await ensureReady(); await setEndpoint(); } catch {}
  }
}

console.log(`\n完成: 新增 ${done} / 跳过 ${skipped} / 失败 ${failed}  (共 ${((Date.now()-t0)/1000).toFixed(0)}s)`);
ws.close();
