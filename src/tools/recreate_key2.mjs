// recreate_key2.mjs — 删除 → 新建 → 捕获明文 key（监听前端 API 响应）
import fs from 'node:fs';

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pend = new Map();
const apiBodies = [];

ws.onmessage = async (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.error ? { __err: m.error } : m.result);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Network.responseReceived') {
    const u = m.params?.response?.url || '';
    if (/\/api\/.*(key|project|credential)/i.test(u)) {
      apiBodies.push({ requestId: m.params.requestId, url: u });
    }
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

/** 真实点击某个按钮（按文字） */
async function realClickText(re, label) {
  const box = await ev(`(() => {
    const btn = [...document.querySelectorAll('button')]
      .filter((b) => !b.disabled)
      .find((b) => ${re}.test((b.innerText || '').trim()));
    if (!btn) return null;
    btn.scrollIntoView({ block: 'center' });
    const r = btn.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, t: (btn.innerText || '').trim() };
  })()`);
  if (!box) {
    console.log(`  [skip] 找不到按钮: ${label}`);
    return false;
  }
  console.log(`  [click] ${box.t}`);
  const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
  await sleep(2500);
  return true;
}

await send('Network.enable');

console.log('[1] 删除现有 key');
const deleted = await realClickText('/删除/', '删除');

// 可能有确认弹窗
await sleep(1500);
const confirmHit = await realClickText('/^(确认|确定|删除)$/', '确认删除');
if (!confirmHit) await realClickText('/^(确认|确定)$/', '确认');

await sleep(3000);
const afterDelete = await ev(`(() => {
  const t = document.body.innerText;
  return {
    buttons: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(Boolean),
    hasKeyMask: /[A-Za-z0-9]{10}•{4,}/.test(t),
    text: t.slice(0, 700),
  };
})()`);
console.log('删除后:', JSON.stringify(afterDelete, null, 2));

// 取所有已捕获的 API 响应体
console.log('\n[2] 抓取 API 响应体');
const seen = new Set();
for (const b of apiBodies) {
  if (seen.has(b.requestId)) continue;
  seen.add(b.requestId);
  try {
    const r = await send('Network.getResponseBody', { requestId: b.requestId });
    const body = r.body || '';
    if (body.length > 10) {
      console.log(`  ${b.url.slice(0, 100)}`);
      console.log(`    ${body.slice(0, 400)}`);
    }
  } catch (e) {
    /* 响应体可能已过期 */
  }
}

ws.close();
