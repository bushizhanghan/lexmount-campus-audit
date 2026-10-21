// fetch_key_via_cdp.mjs — 直接监听并重放 key 接口，捕获明文
// 策略：回到 api-keys 页 → 开 Network 监听 → 调内部接口拿 key 列表
import fs from 'node:fs';

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pend = new Map();
const hits = [];

ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.error ? { __err: m.error } : m.result);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Network.responseReceived') {
    hits.push({
      requestId: m.params.requestId,
      url: m.params.response.url,
      status: m.params.response.status,
    });
  }
};

const send = (method, params = {}) =>
  new Promise((res) => {
    const i = ++id;
    pend.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });

const ev = async (x) => {
  const r = await send('Runtime.evaluate', {
    expression: x, returnByValue: true, awaitPromise: true, userGesture: true,
  });
  if (r.__err) throw new Error(JSON.stringify(r.__err));
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

await send('Network.enable');
await send('Page.enable');

console.log('[1] 回到 API 密钥页');
await send('Page.navigate', { url: 'https://browser.lexmount.cn/settings/api-keys' });
await sleep(12000);

// 等页面就绪
for (let i = 0; i < 30; i++) {
  const ok = await ev(`document.body.innerText.includes('API 密钥')`).catch(() => false);
  if (ok) break;
  await sleep(1000);
}

const st = await ev(`(() => {
  const t = document.body.innerText;
  return {
    buttons: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(Boolean),
    hasMask: /[A-Za-z0-9]{10}•{3,}/.test(t),
    snippet: t.slice(t.indexOf('API 密钥'), t.indexOf('API 密钥') + 500),
  };
})()`);
console.log('页面:', JSON.stringify(st, null, 2));

// 用页面自身的 fetch 调内部接口，拿 key 列表
console.log('\n[2] 尝试内部接口');
const probes = [
  '/api/api-keys',
  '/api/apikeys',
  '/api/projects',
  '/api/keys',
  '/api/v1/api-keys',
];
for (const p of probes) {
  const r = await ev(`(async () => {
    try {
      const res = await fetch(${JSON.stringify(p)}, { credentials: 'include' });
      const txt = await res.text();
      return { path: ${JSON.stringify(p)}, status: res.status, body: txt.slice(0, 500) };
    } catch (e) { return { path: ${JSON.stringify(p)}, err: String(e) }; }
  })()`);
  if (r.status && r.status < 400) {
    console.log(`  ${p} -> ${r.status}`);
    console.log(`    ${r.body}`);
  } else {
    console.log(`  ${p} -> ${r.status || r.err}`);
  }
}

// 输出所有捕获到的 API 相关响应
console.log('\n[3] 捕获到的 API 响应:');
const seen = new Set();
for (const h of hits) {
  if (seen.has(h.requestId)) continue;
  if (!/\/api\//i.test(h.url)) continue;
  seen.add(h.requestId);
  try {
    const r = await send('Network.getResponseBody', { requestId: h.requestId });
    const body = r.body || '';
    const interesting = /key|secret|token/i.test(body) && body.length > 20;
    if (interesting) {
      console.log(`  >> ${h.url.slice(0, 110)}`);
      console.log(`     ${body.slice(0, 700)}`);
    }
  } catch {}
}
ws.close();
