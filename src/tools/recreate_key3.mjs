// recreate_key3.mjs — 点弹窗确认删除 → 等待出现新建 → 新建 → 捕获明文
import fs from 'node:fs';

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pend = new Map();
const apiBodies = [];

ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.error ? { __err: m.error } : m.result);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Network.responseReceived') {
    const u = m.params?.response?.url || '';
    if (/\/api\//i.test(u)) {
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

/** 在指定容器（弹窗优先）里点击匹配文字的按钮 */
async function clickIn(reSource, scopeHint = '') {
  const box = await ev(`(() => {
    const re = ${reSource};
    // 优先在 dialog / alertdialog 里找
    let scopes = [
      ...document.querySelectorAll('[role="dialog"],[role="alertdialog"]'),
    ];
    if (!scopes.length) scopes = [document.body];
    for (const sc of scopes) {
      const btn = [...sc.querySelectorAll('button')]
        .filter((b) => !b.disabled)
        .find((b) => re.test((b.innerText || '').trim()));
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        const r = btn.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2, t: (btn.innerText || '').trim(), inDialog: sc !== document.body };
      }
    }
    return null;
  })()`);
  if (!box) return null;
  console.log(`  [click] "${box.t}" ${box.inDialog ? '(弹窗)' : '(页面)'}`);
  const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
  await sleep(2500);
  return box;
}

await send('Network.enable');

// 若弹窗已开，直接点弹窗里的删除
console.log('[1] 确认删除');
await clickIn('/^删除$/');

await sleep(3000);
let st = await ev(`(() => ({
  buttons: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(Boolean),
  hasMask: /[A-Za-z0-9]{10}•{3,}/.test(document.body.innerText),
  text: document.body.innerText.slice(-800),
}))()`);
console.log('删除后状态:', JSON.stringify(st, null, 2));

// 找新建/生成按钮
if (!st.hasMask) {
  console.log('\n[2] 尝试新建 key');
  const made = await clickIn('/新建|创建|生成|添加/');
  if (made) {
    await sleep(2500);
    // 可能还有确认
    await clickIn('/^(确认|确定|创建|生成)$/');
    await sleep(3000);
  }
}

// 读取页面当前状态，看是否出现明文
const final = await ev(`(() => ({
  text: document.body.innerText.slice(0, 1600),
  buttons: [...document.querySelectorAll('button')].map(b => (b.innerText||'').trim()).filter(Boolean),
  codes: [...document.querySelectorAll('code,pre')].map(e => (e.innerText||'').trim()).filter(x => x.length > 12),
}))()`);
console.log('\n[3] 当前页面:');
console.log(final.text.slice(0, 1200));
console.log('\ncodes:', JSON.stringify(final.codes.slice(0, 6), null, 2));

// 抓 API 响应体
console.log('\n[4] API 响应体:');
const seen = new Set();
for (const b of apiBodies) {
  if (seen.has(b.requestId) || seen.size > 25) continue;
  seen.add(b.requestId);
  try {
    const r = await send('Network.getResponseBody', { requestId: b.requestId });
    const body = r.body || '';
    if (/api.?key|apiKey|secret|token/i.test(body) && body.length > 20) {
      console.log(`  >> ${b.url.slice(0, 110)}`);
      console.log(`     ${body.slice(0, 600)}`);
    }
  } catch {}
}

fs.writeFileSync(
  'E:/dsh/output/webfetch-playground/project/apikey_state.json',
  JSON.stringify({ final, apiHits: apiBodies.map(b => b.url) }, null, 2),
  'utf8'
);
ws.close();
