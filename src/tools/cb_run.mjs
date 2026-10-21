// cb_run.mjs — 在 Cloud Browser 试验场注入脚本并运行，回收执行结果
import fs from 'node:fs';

const codeFile = process.argv[2];
const waitMs = Number(process.argv[3] || 90000);
const code = fs.readFileSync(codeFile, 'utf8');

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

const evaluate = async (expression) => {
  const r = await send('Runtime.evaluate', {
    expression, returnByValue: true, awaitPromise: true, userGesture: true,
  });
  if (r.__err) throw new Error(JSON.stringify(r.__err));
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 1.5 若上一次会话还在跑，先停掉
const stopInfo = await evaluate(`(() => {
  const btns = [...document.querySelectorAll('button')];
  const stop = btns.find((b) => /停止/.test((b.innerText || '').trim()));
  if (!stop) return { needed: false };
  stop.scrollIntoView({ block: 'center' });
  const r = stop.getBoundingClientRect();
  return { needed: true, x: r.left + r.width / 2, y: r.top + r.height / 2, label: (stop.innerText || '').trim() };
})()`);
if (stopInfo.needed) {
  console.log('[stop] 先停止上一次会话:', stopInfo.label);
  const sb = { x: stopInfo.x, y: stopInfo.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...sb });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...sb });
  await sleep(4000);
}

// 2. 注入代码到 Monaco
const injected = await evaluate(`(() => {
  const models = window.monaco?.editor?.getModels?.() || [];
  if (!models.length) return 'NO_MODEL';
  models[0].setValue(${JSON.stringify(code)});
  return models[0].getValue().length;
})()`);
console.log('[inject] 字符数 =', injected);
if (injected === 'NO_MODEL') throw new Error('Monaco 模型不可用');
await sleep(1500);

// 2. 点「运行」按钮（登录态下可能叫「用 Chrome 运行 / 重试 / 运行」）
const clicked = await evaluate(`(() => {
  const btns = [...document.querySelectorAll('button')].filter((b) => !b.disabled);
  const norm = (s) => (s || '').trim();
  // 优先精确匹配，其次包含匹配；排除侧边栏和无关按钮
  const exact = ['用 Chrome 运行', '运行', '重新运行', '重试', 'Run'];
  const bad = /试验场|浏览器资源|切换|Cookie|示例|恢复|停止|白也|打开|写一份|两个标签页|高级/;
  let el = btns.find((b) => exact.includes(norm(b.innerText)));
  if (!el) {
    el = btns.find((b) => /运行|Run|重试/.test(norm(b.innerText)) && !bad.test(norm(b.innerText)));
  }
  if (!el) {
    return { fail: true, candidates: btns.map((b) => norm(b.innerText)).filter(Boolean) };
  }
  el.scrollIntoView({ block: 'center' });
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2, label: norm(el.innerText) };
})()`);
if (clicked.fail) {
  console.log('[click] 候选按钮:', JSON.stringify(clicked.candidates, null, 2));
  throw new Error('找不到运行按钮');
}
console.log('[click]', clicked.label, '@', Math.round(clicked.x), Math.round(clicked.y));

const base = { x: clicked.x, y: clicked.y, button: 'left', clickCount: 1, buttons: 1 };
await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: clicked.x, y: clicked.y });
await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });

// 3. 轮询执行结果
const readOutput = () => evaluate(`(() => {
  const body = document.body.innerText;
  const i = body.indexOf('执行结果');
  const seg = i >= 0 ? body.slice(i) : '';
  // 去掉尾部的常见问题等噪声
  const cut = seg.indexOf('常见问题');
  return (cut > 0 ? seg.slice(0, cut) : seg).trim();
})()`);

let last = '';
const t0 = Date.now();
while (Date.now() - t0 < waitMs) {
  await sleep(2000);
  const out = await readOutput();
  if (out && out !== last) {
    last = out;
    console.log(`[${Math.round((Date.now() - t0) / 1000)}s] 输出变化:\n${out.slice(0, 1200)}\n---`);
  }
  if (/完成|失败|错误|Error|结束/.test(out) && out.length > 200) break;
}

console.log('\n===== 最终执行结果 =====');
console.log(last);
ws.close();
