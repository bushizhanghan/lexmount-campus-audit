// recreate_key.mjs — 删除现有 API Key 并新建，捕获明文
import fs from 'node:fs';

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

const ev = async (x) => {
  const r = await send('Runtime.evaluate', {
    expression: x, returnByValue: true, awaitPromise: true, userGesture: true,
  });
  if (r.__err) throw new Error(JSON.stringify(r.__err));
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 监听新的 API 响应，抓明文 key
const captured = [];
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.method === 'Network.responseReceived') return;
});

await send('Network.enable');

// 收集所有网络响应体（含 key 的接口）
const bodies = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.error ? { __err: m.error } : m.result);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Network.responseReceived') {
    const url = m.params?.response?.url || '';
    if (/api|key|project/i.test(url)) {
      bodies.push({ requestId: m.params.requestId, url });
    }
  }
};

// 先读当前页面状态
const state = await ev(`(() => {
  const body = document.body.innerText;
  return {
    url: location.href,
    hasDelete: [...document.querySelectorAll('button')].some(b => /删除/.test(b.innerText||'')),
    hasCreate: [...document.querySelectorAll('button')].some(b => /新建|创建|生成/.test(b.innerText||'')),
    buttons: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(Boolean),
  };
})()`);
console.log('页面状态:', JSON.stringify(state, null, 2));
ws.close();
