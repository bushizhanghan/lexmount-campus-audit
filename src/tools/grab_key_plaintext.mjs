// grab_key_plaintext.mjs — 删除 → 创建，全程捕获 API 响应体里的明文 key
import fs from 'node:fs';

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pend = new Map();
const respUrls = new Map(); // requestId -> url

ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.error ? { __err: m.error } : m.result);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Network.responseReceived') {
    respUrls.set(m.params.requestId, m.params.response.url);
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

async function clickIn(reSource) {
  const box = await ev(`(() => {
    const re = ${reSource};
    let scopes = [...document.querySelectorAll('[role="dialog"],[role="alertdialog"]')];
    if (!scopes.length) scopes = [document.body];
    for (const sc of scopes) {
      const btn = [...sc.querySelectorAll('button')]
        .filter((b) => !b.disabled)
        .find((b) => re.test((b.innerText || '').trim()));
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        const r = btn.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2, t: (btn.innerText || '').trim(), dlg: sc !== document.body };
      }
    }
    return null;
  })()`);
  if (!box) return null;
  console.log(`  [click] "${box.t}" ${box.dlg ? '(弹窗)' : ''}`);
  const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
  await sleep(2500);
  return box;
}

await send('Network.enable');
await send('Page.enable');

// 记录开启监听前的 requestId 集合
const before = new Set(respUrls.keys());

console.log('[1] 删除现有 key');
await clickIn('/^删除$/');
await sleep(1500);
await clickIn('/^删除$/'); // 弹窗确认
await sleep(3000);

const st1 = await ev(`({ has: /•{3,}/.test(document.body.innerText), t: document.body.innerText.slice(-300) })`);
console.log('  删除后:', st1.has ? '仍有 key' : '已清空');

console.log('[2] 创建新 key');
const made = await clickIn('/创建 API 密钥|新建|生成/');
if (!made) { console.log('  找不到创建按钮'); }
await sleep(2000);
// 可能弹窗要求确认
await clickIn('/^(确认|确定|创建|生成)$/');
await sleep(4000);

// 立即读页面（明文可能显示在弹窗里）
const shown = await ev(`(() => {
  const dlg = document.querySelector('[role="dialog"],[role="alertdialog"]');
  const scope = dlg || document.body;
  return {
    dialogOpen: !!dlg,
    text: scope.innerText.slice(0, 1200),
    codes: [...scope.querySelectorAll('code,pre,input')].map(e => e.value || e.innerText || '').filter(x => x && x.length > 15).slice(0, 8),
  };
})()`);
console.log('\n[3] 创建后页面:');
console.log(shown.text.slice(0, 900));

// 立刻抓所有新响应体
console.log('\n[4] 新响应体:');
const newIds = [...respUrls.keys()].filter((k) => !before.has(k));
let found = null;
for (const rid of newIds) {
  const url = respUrls.get(rid) || '';
  if (!/\/api\//i.test(url)) continue;
  try {
    const r = await send('Network.getResponseBody', { requestId: rid });
    const body = r.body || '';
    if (body.length < 20) continue;
    const looksKey = /"?(api_?key|apiKey|secret|plaintext|raw_?key)"?\s*:/i.test(body);
    console.log(`  ${url.slice(0, 100)}${looksKey ? '  <== 可能含 key' : ''}`);
    if (looksKey) {
      console.log('    ' + body.slice(0, 900));
      // 尝试抽出一个像 key 的字符串
      try {
        const j = JSON.parse(body);
        const stack = [j];
        while (stack.length) {
          const cur = stack.pop();
          if (!cur || typeof cur !== 'object') continue;
          for (const [k, v] of Object.entries(cur)) {
            if (typeof v === 'string' && v.length >= 20 && /key|secret|token/i.test(k)) {
              found = found || { field: k, value: v };
            } else if (v && typeof v === 'object') stack.push(v);
          }
        }
      } catch {}
    }
  } catch (e) {}
}

if (found) {
  console.log('\n=== 捕获到明文 key ===');
  console.log(`字段: ${found.field}`);
  console.log(`值:   ${found.value.slice(0, 6)}...${found.value.slice(-4)} (len=${found.value.length})`);
  fs.writeFileSync('E:/dsh/output/webfetch-playground/project/.apikey.tmp', found.value, 'utf8');
  console.log('已写入 .apikey.tmp');
} else {
  console.log('\n未从响应体捕获到明文 key');
}

const finalBtn = await ev(`[...document.querySelectorAll('button')].map(b=>(b.innerText||'').trim()).filter(Boolean)`);
console.log('\n当前按钮:', JSON.stringify(finalBtn));
ws.close();
