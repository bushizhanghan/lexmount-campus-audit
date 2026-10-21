// stop_cb.mjs — 停止 Cloud Browser 会话（若在运行）
const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pend = new Map();
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.result);
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
  return r.result.value;
};

const info = await ev(`(() => {
  const b = [...document.querySelectorAll('button')].find((x) => /停止/.test((x.innerText || '').trim()));
  if (!b) return null;
  b.scrollIntoView({ block: 'center' });
  const r = b.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
})()`);

if (info) {
  const bs = { x: info.x, y: info.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...bs });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...bs });
  console.log('stopped');
} else {
  console.log('no running session');
}
await new Promise((r) => setTimeout(r, 5000));
ws.close();
