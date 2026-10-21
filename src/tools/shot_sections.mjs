// shot_sections.mjs — 分段截图长页面，便于逐段核验
import fs from 'node:fs';

const url = process.argv[2];
const outPrefix = process.argv[3];
const width = Number(process.argv[4] || 1440);
const segH = Number(process.argv[5] || 2400);

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

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width, height: segH, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url });
await new Promise((r) => setTimeout(r, 3000));

const total = (await send('Runtime.evaluate', {
  expression: `document.documentElement.scrollHeight`, returnByValue: true,
})).result.value;

const segments = Math.ceil(total / segH);
console.log(`total=${total}px -> ${segments} 段`);

for (let i = 0; i < segments; i++) {
  await send('Runtime.evaluate', { expression: `window.scrollTo(0, ${i * segH})` });
  await new Promise((r) => setTimeout(r, 400));
  const s = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  fs.writeFileSync(`${outPrefix}-${String(i + 1).padStart(2, '0')}.png`, Buffer.from(s.data, 'base64'));
}
console.log(`saved ${segments} segments`);
ws.close();
