// shot_url.mjs — 打开本地文件/URL 并截图，用于核验渲染效果
import fs from 'node:fs';

const url = process.argv[2];
const out = process.argv[3];
const width = Number(process.argv[4] || 1440);
const height = Number(process.argv[5] || 1200);

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
if (!page) throw new Error('no page target — 先启动带 CDP 的浏览器');
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

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', {
  width, height, deviceScaleFactor: 1, mobile: false,
});
await send('Page.navigate', { url });
await new Promise((r) => setTimeout(r, 3000));

const s = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
fs.writeFileSync(out, Buffer.from(s.data, 'base64'));
const dims = await send('Runtime.evaluate', {
  expression: `({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight})`,
  returnByValue: true,
});
console.log('saved', out, JSON.stringify(dims.result.value));
ws.close();
