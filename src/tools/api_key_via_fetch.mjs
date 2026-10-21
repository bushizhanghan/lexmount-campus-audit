// api_key_via_fetch.mjs — 用页面自身的 session 调内部接口，列出 key（不依赖 UI 渲染）
import fs from 'node:fs';

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pend = new Map();
const seen = [];

ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.error ? { __err: m.error } : m.result);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Network.requestWillBeSent') {
    const u = m.params.request.url;
    if (/\/api\//i.test(u)) seen.push({ method: m.params.request.method, url: u, post: (m.params.request.postData || '').slice(0, 200) });
  }
};

const send = (method, params = {}) =>
  new Promise((res) => {
    const i = ++id;
    pend.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });

const ev = async (x, awaitPromise = true) => {
  const r = await send('Runtime.evaluate', {
    expression: x, returnByValue: true, awaitPromise, userGesture: true,
  });
  if (r.__err) throw new Error(JSON.stringify(r.__err));
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

await send('Network.enable');
await send('Page.enable');

// 强制刷新到密钥页，同时观察它调了哪些接口
await send('Page.navigate', { url: 'https://browser.lexmount.cn/settings/api-keys' });
await sleep(15000);

console.log('=== 页面实际调用的 /api/ 请求 ===');
for (const s of seen.slice(-20)) {
  console.log(`  ${s.method.padEnd(6)} ${s.url.slice(0, 110)}`);
  if (s.post) console.log(`         body: ${s.post}`);
}

// 直接用页面 fetch 调那些接口
const endpoints = [...new Set(seen.map((s) => s.url).filter((u) => /key|project|credential/i.test(u)))];
console.log('\n=== 重放这些接口 ===');
for (const u of endpoints.slice(0, 8)) {
  const r = await ev(`(async () => {
    try {
      const res = await fetch(${JSON.stringify(u)}, { credentials: 'include', headers: { 'Accept': 'application/json' } });
      const t = await res.text();
      return { s: res.status, b: t.slice(0, 800) };
    } catch (e) { return { err: String(e) }; }
  })()`);
  console.log(`  ${u.slice(0, 100)} -> ${r.s || r.err}`);
  if (r.b) console.log(`    ${r.b}`);
}
ws.close();
