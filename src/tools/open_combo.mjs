// open_combo.mjs — 点开第 i 个 Radix combobox，读出全部选项
import fs from 'node:fs';

const idx = Number(process.argv[2] || 0);

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

const evaluate = async (expression) => {
  const r = await send('Runtime.evaluate', {
    expression, returnByValue: true, awaitPromise: true, userGesture: true,
  });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
};

const pos = await evaluate(fs.readFileSync('E:/dsh/output/webfetch-playground/project/tools/combo_pos.js', 'utf8'));
const p = pos[idx];
if (!p) throw new Error('no combobox at ' + idx);
console.log(`点击 combobox #${idx}: "${p.text}" @ ${Math.round(p.x)},${Math.round(p.y)}`);

const base = { x: p.x, y: p.y, button: 'left', clickCount: 1, buttons: 1 };
await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: p.x, y: p.y });
await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
await new Promise((r) => setTimeout(r, 900));

const opts = await evaluate(`(() => {
  const els = [...document.querySelectorAll('[role="option"], [data-radix-collection-item]')];
  return els.map((e) => (e.innerText || '').trim()).filter(Boolean);
})()`);
console.log('选项:', JSON.stringify(opts, null, 2));

// 关掉
await send('Input.dispatchMouseEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
ws.close();
