// grab_key2.mjs — 阻止创建后的自动跳转，抓明文弹窗
import fs from 'node:fs';

const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
const page = list.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pend = new Map();
const bodies = new Map();

ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) {
    pend.get(m.id)(m.error ? { __err: m.error } : m.result);
    pend.delete(m.id);
    return;
  }
  if (m.method === 'Network.responseReceived') {
    const u = m.params.response.url;
    if (/\/api\//i.test(u) && m.params.response.status < 400) {
      // 立刻异步取 body，避免过期
      send('Network.getResponseBody', { requestId: m.params.requestId })
        .then((r) => {
          const b = r && r.body;
          if (b && b.length > 15) bodies.set(u, b);
        })
        .catch(() => {});
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
        return { x: r.left + r.width / 2, y: r.top + r.height / 2, t: (btn.innerText || '').trim() };
      }
    }
    return null;
  })()`);
  if (!box) return null;
  console.log(`  [click] "${box.t}"`);
  const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
  return box;
}

await send('Network.enable');
await send('Page.enable');

// 阻止跳到 /playground，保住对话框
await send('Page.navigate', { url: 'https://browser.lexmount.cn/settings/api-keys' });
await sleep(12000);
for (let i = 0; i < 30; i++) {
  if (await ev(`document.body.innerText.includes('创建 API 密钥')`).catch(() => false)) break;
  await sleep(1000);
}
console.log('[状态]', await ev(`(() => {
  const t = document.body.innerText;
  return { hasKey: /•{3,}/.test(t), canCreate: t.includes('创建 API 密钥') };
})()`));

// 先删除（若存在）
if (await ev(`/•{3,}/.test(document.body.innerText)`)) {
  console.log('[1] 删除旧 key');
  await clickIn('/^删除$/');
  await sleep(1500);
  await clickIn('/^删除$/');
  await sleep(3000);
}

// 关键：创建前先注入 history 拦截，防止跳走
await ev(`(() => {
  window.__origPush = history.pushState.bind(history);
  window.__origReplace = history.replaceState.bind(history);
  const block = (fn) => function(...args) {
    try {
      const u = String(args[2] || '');
      if (/\\/playground/.test(u)) { console.warn('blocked nav to ' + u); return; }
    } catch(e) {}
    return fn.apply(history, args);
  };
  history.pushState = block(window.__origPush);
  history.replaceState = block(window.__origReplace);
  return 'patched';
})()`);

console.log('[2] 创建新 key');
await clickIn('/创建 API 密钥/');
await sleep(3500);

// 读弹窗
const shown = await ev(`(() => {
  const dlg = document.querySelector('[role="dialog"],[role="alertdialog"]');
  const scope = dlg || document.body;
  const t = scope.innerText;
  return {
    dialogOpen: !!dlg,
    text: t.slice(0, 1000),
    candidates: (t.match(/[A-Za-z0-9_\\-]{24,64}/g) || []).slice(0, 8),
  };
})()`);
console.log('\n[3] 弹窗内容:');
console.log(shown.text.slice(0, 800));
console.log('\n候选串:', JSON.stringify(shown.candidates));

console.log('\n[4] 已捕获的 API 响应体:');
let foundKey = null;
for (const [u, b] of bodies) {
  if (!/key|credential/i.test(u)) continue;
  console.log(`  ${u.slice(0, 110)}`);
  console.log(`    ${b.slice(0, 500)}`);
  const m = b.match(/"(?:api_?key|apiKey|secret|plaintext|key)"\s*:\s*"([A-Za-z0-9_\-]{20,})"/i);
  if (m) foundKey = m[1];
}

if (foundKey) {
  fs.writeFileSync('E:/dsh/output/webfetch-playground/project/.apikey.tmp', foundKey, 'utf8');
  console.log(`\n✅ 捕获明文 key: ${foundKey.slice(0, 6)}...${foundKey.slice(-4)} (len=${foundKey.length})`);
} else {
  console.log('\n❌ 仍未捕获');
}

// 恢复 history
await ev(`(() => { if (window.__origPush) history.pushState = window.__origPush; if (window.__origReplace) history.replaceState = window.__origReplace; return 'restored'; })()`);
ws.close();
