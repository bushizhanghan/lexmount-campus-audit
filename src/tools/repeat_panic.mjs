#!/usr/bin/env node
/**
 * repeat_panic.mjs — 重复测试 panic 站点，证明可复现性。
 *
 *   node repeat_panic.mjs <slug> <times>
 *
 * 每次独立调用 Web Fetch，记录 status / error / 耗时。
 * 结果写入 runs/repeat/<slug>.json
 */
import fs from 'node:fs';
import path from 'node:path';

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const SLUG = process.argv[2];
const TIMES = Number(process.argv[3] || 3);
const OUTDIR = path.join(HERE, '..', 'runs', 'repeat');
fs.mkdirSync(OUTDIR, { recursive: true });

const config = JSON.parse(
  fs.readFileSync(path.join(HERE, '..', 'sites.json'), 'utf8')
);
const site = config.sites.find((s) => s.slug === SLUG);
if (!site) throw new Error('unknown slug: ' + SLUG);

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
  if (v !== u) throw new Error('fill failed: ' + v);
  await sleep(500);
}

const readResponse = () => evaluate(`(() => {
  const p = [...document.querySelectorAll('pre')]
    .map((e) => e.innerText).filter((t) => t.trim().startsWith('{'));
  const c = p.filter((t) => t.includes('"request_id"') || t.includes('"html"') || t.includes('metadata'));
  return c.length ? c[c.length - 1] : '';
})()`);

// 确保在 webfetch 页面且就绪
const url = await evaluate('location.href');
if (!url.includes('/playground/webfetch')) {
  await send('Page.navigate', { url: 'https://browser.lexmount.cn/playground/webfetch' });
}
for (let i = 0; i < 120; i++) {
  const ok = await evaluate(
    `!!document.querySelector('#webfetch-url')`
  ).catch(() => false);
  if (ok) break;
  await sleep(500);
}

const results = [];
for (let n = 1; n <= TIMES; n++) {
  process.stdout.write(`第 ${n}/${TIMES} 次 ${site.name} ... `);
  const t0 = Date.now();
  try {
    await setUrl(site.url);
    const before = await readResponse();
    await clickByText('运行请求');

    let out = '';
    for (let i = 0; i < 120; i++) {
      await sleep(500);
      const cur = await readResponse();
      if (cur && cur !== before) { out = cur; break; }
    }
    const ms = Date.now() - t0;
    if (!out) throw new Error('timeout');

    const j = JSON.parse(out);
    const isErr = !!j.error;
    const rec = {
      n,
      ok: !isErr,
      status: j.status_code ?? j.result?.status_code ?? null,
      text_len: j.result ? (j.result.main_text || '').length : 0,
      error_code: isErr ? j.error.code : null,
      panic_at: isErr
        ? ((j.error.message || '').match(/panicked at ([\w./-]+:\d+:\d+)/) || [])[1] || null
        : null,
      wall_ms: ms,
      server_ms: j.metadata?.server_elapsed_ms ?? null,
      request_id: j.request_id ?? null,
    };
    results.push(rec);
    console.log(
      isErr
        ? `FAIL ${rec.error_code} @ ${rec.panic_at} (${ms}ms)`
        : `ok ${rec.status} len=${rec.text_len} (${ms}ms)`
    );
  } catch (e) {
    const ms = Date.now() - t0;
    results.push({ n, ok: false, error_code: 'runner_error', err: e.message, wall_ms: ms });
    console.log(`RUNNER_ERROR ${e.message} (${ms}ms)`);
    // 尝试恢复页面
    try {
      await send('Page.navigate', { url: 'https://browser.lexmount.cn/playground/webfetch' });
      await sleep(6000);
    } catch {}
  }
}

const summary = {
  slug: site.slug,
  name: site.name,
  url: site.url,
  times: TIMES,
  ran_at: new Date().toISOString(),
  results,
  fail_count: results.filter((r) => !r.ok).length,
  panic_locations: [...new Set(results.map((r) => r.panic_at).filter(Boolean))],
};
fs.writeFileSync(
  path.join(OUTDIR, `${site.slug}.json`),
  JSON.stringify(summary, null, 2),
  'utf8'
);

console.log(
  `\n汇总: ${summary.fail_count}/${TIMES} 次失败, panic 位置: ${summary.panic_locations.join(',') || '无'}`
);
ws.close();
