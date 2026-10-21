// cb_capture.mjs — 在 Cloud Browser 运行脚本，并把完整输出原样落盘
import fs from 'node:fs';
import path from 'node:path';

const codeFile = process.argv[2];
const outFile = process.argv[3];
const waitMs = Number(process.argv[4] || 180000);
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

// 停止上次会话
const stop = await evaluate(`(() => {
  const b = [...document.querySelectorAll('button')].find((x) => /停止/.test((x.innerText || '').trim()));
  if (!b) return null;
  b.scrollIntoView({ block: 'center' });
  const r = b.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
})()`);
if (stop) {
  const b = { x: stop.x, y: stop.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...b });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...b });
  console.log('[stop] 已停止上次会话');
  await sleep(4000);
}

// 注入代码
const injected = await evaluate(`(() => {
  const models = window.monaco?.editor?.getModels?.() || [];
  if (!models.length) return 'NO_MODEL';
  models[0].setValue(${JSON.stringify(code)});
  return models[0].getValue().length;
})()`);
if (injected === 'NO_MODEL') throw new Error('Monaco 不可用');
console.log('[inject]', injected, '字符');
await sleep(1500);

// 点击运行
const clicked = await evaluate(`(() => {
  const btns = [...document.querySelectorAll('button')].filter((b) => !b.disabled);
  const bad = /试验场|浏览器资源|切换|Cookie|示例|恢复|停止|白也|打开|写一份|两个标签页|高级/;
  const el = btns.find((b) => /用 Chrome 运行|^运行$|重新运行|重试/.test((b.innerText || '').trim()) && !bad.test((b.innerText || '').trim()));
  if (!el) return null;
  el.scrollIntoView({ block: 'center' });
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2, t: (el.innerText || '').trim() };
})()`);
if (!clicked) throw new Error('找不到运行按钮');
console.log('[click]', clicked.t);
const cb = { x: clicked.x, y: clicked.y, button: 'left', clickCount: 1, buttons: 1 };
await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: clicked.x, y: clicked.y });
await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...cb });
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...cb });

// 轮询，收集所有输出快照
const snapshots = [];
const t0 = Date.now();
let last = '';
let done = false;
while (Date.now() - t0 < waitMs) {
  await sleep(3000);
  const out = await evaluate(`(() => {
    const body = document.body.innerText;
    const i = body.indexOf('执行结果');
    let seg = i >= 0 ? body.slice(i) : '';
    const cut = seg.indexOf('常见问题');
    if (cut > 0) seg = seg.slice(0, cut);
    return seg.trim();
  })()`);
  if (out !== last) {
    last = out;
    snapshots.push({ t_ms: Date.now() - t0, text: out });
    const sec = Math.round((Date.now() - t0) / 1000);
    console.log(`[${sec}s] 输出更新 (${out.length} chars)`);
    if (/ALL DONE|退出码|Error|FAILED/.test(out) && out.length > 300) {
      done = true;
      break;
    }
  }
}

const finalText = last;
fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(
  outFile,
  JSON.stringify({
    script_file: codeFile,
    script_code: code,
    ran_at: new Date().toISOString(),
    page_url: await evaluate('location.href'),
    done,
    elapsed_ms: Date.now() - t0,
    final_output: finalText,
    snapshots,
  }, null, 2),
  'utf8'
);

console.log('\n===== 最终输出 =====');
console.log(finalText.slice(0, 3000));
console.log('\n已落盘:', outFile);
ws.close();
