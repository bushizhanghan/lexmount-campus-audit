// nav.mjs — 导航到指定 URL，等待就绪后执行一个 JS 文件
import fs from 'node:fs';

const targetUrl = process.argv[2];
const jsFile = process.argv[3];

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
  width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false,
});
await send('Page.navigate', { url: targetUrl });

// 等表单控件出现
for (let i = 0; i < 90; i++) {
  await new Promise((r) => setTimeout(r, 500));
  const probe = await send('Runtime.evaluate', {
    expression: `document.querySelectorAll('input,textarea,select').length`,
    returnByValue: true,
  });
  if ((probe.result?.value || 0) >= 3) break;
}

const r = await send('Runtime.evaluate', {
  expression: fs.readFileSync(jsFile, 'utf8'),
  returnByValue: true,
  awaitPromise: true,
});
if (r.exceptionDetails) {
  console.log('JS ERROR:', r.exceptionDetails.exception?.description || r.exceptionDetails.text);
} else {
  console.log(JSON.stringify(r.result.value, null, 2));
}
ws.close();
