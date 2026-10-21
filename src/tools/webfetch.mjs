#!/usr/bin/env node
/**
 * webfetch.mjs — drive the Lexmount "Web Fetch" playground from the terminal.
 *
 *   node webfetch.mjs <url> [extract|dump]
 *
 *   extract (default) -> POST /v1/extract   (main text + title + links)
 *   dump              -> POST /v1/dom/dump  (rendered HTML)
 *
 * How it works: launches (or reuses) a headless Edge with the DevTools protocol
 * on port 9222, opens the playground, fills the target URL, clicks 运行请求,
 * then reads the response JSON straight out of the page.
 *
 * NOTE: the playground allows 20 guest requests per day.
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const PAGE = 'https://browser.lexmount.cn/playground/webfetch';
const PORT = process.env.CDP_PORT || '9222';
const EDGE =
  process.env.EDGE_PATH ||
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const url = process.argv[2];
const mode = (process.argv[3] || 'extract').toLowerCase();
if (!url) {
  console.error('usage: node webfetch.mjs <url> [extract|dump]');
  process.exit(2);
}
const endpointLabel =
  mode === 'dump' ? 'POST /v1/dom/dump' : 'POST /v1/extract';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function cdpUp() {
  try {
    const r = await fetch(`http://127.0.0.1:${PORT}/json/version`, {
      signal: AbortSignal.timeout(1500),
    });
    return r.ok;
  } catch {
    return false;
  }
}

async function ensureBrowser() {
  if (await cdpUp()) return;
  const profile = path.join(os.tmpdir(), 'lexmount-wf-profile');
  fs.mkdirSync(profile, { recursive: true });
  const child = spawn(
    EDGE,
    [
      '--headless=new',
      `--remote-debugging-port=${PORT}`,
      `--user-data-dir=${profile}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-gpu',
      'about:blank',
    ],
    { detached: true, stdio: 'ignore' }
  );
  child.unref();
  for (let i = 0; i < 40; i++) {
    await sleep(250);
    if (await cdpUp()) return;
  }
  throw new Error('could not start Edge with CDP on port ' + PORT);
}

async function connect() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const page = list.find((t) => t.type === 'page');
  if (!page) throw new Error('no page target');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.onopen = res;
    ws.onerror = () => rej(new Error('ws connect failed'));
  });
  let id = 0;
  const pending = new Map();
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
    }
  };
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const mid = ++id;
      pending.set(mid, { resolve, reject });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
  return { send, close: () => ws.close() };
}

async function main() {
  await ensureBrowser();
  const { send, close } = await connect();

  const evaluate = async (expression) => {
    const r = await send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
      userGesture: true,
    });
    if (r.exceptionDetails) {
      throw new Error(
        'JS: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text)
      );
    }
    return r.result.value;
  };

  const realClick = async (selector) => {
    const box = await evaluate(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)});
      if (!el) return null;
      el.scrollIntoView({ block: 'center' });
      const r = el.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    })()`);
    if (!box) throw new Error('element not found: ' + selector);
    const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
  };

  const clickByText = async (text) => {
    const box = await evaluate(`(() => {
      const want = ${JSON.stringify(text)};
      const cands = [...document.querySelectorAll('body *')].filter((e) => {
        const t = (e.innerText || '').trim();
        if (t !== want) return false;
        const r = e.getBoundingClientRect();
        if (r.width < 4 || r.height < 4) return false;
        const st = getComputedStyle(e);
        return st.visibility !== 'hidden' && st.display !== 'none';
      });
      const el = cands.sort(
        (a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length
      )[0];
      if (!el) return null;
      el.scrollIntoView({ block: 'center' });
      const r = el.getBoundingClientRect();
      return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    })()`);
    if (!box) throw new Error('option not found: ' + text);
    const base = { x: box.x, y: box.y, button: 'left', clickCount: 1, buttons: 1 };
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...base });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...base });
  };

  try {
    await send('Page.enable');
    await send('Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 1100,
      deviceScaleFactor: 1,
      mobile: false,
    });

    await send('Page.navigate', { url: PAGE });

    // Wait for the form to actually hydrate. Logged-in sessions render slower
    // than guests, and acting on the SSR skeleton silently misses the controls.
    let hydrated = false;
    for (let i = 0; i < 60; i++) {
      await sleep(500);
      const has = await evaluate(
        `!!document.querySelector('#webfetch-url') && !!document.querySelector('#webfetch-endpoint')`
      );
      if (has) { hydrated = true; break; }
    }
    if (!hydrated) throw new Error('page did not hydrate (no #webfetch-url / #webfetch-endpoint)');
    await sleep(800);

    // Dismiss the cookie sheet if present.
    await evaluate(`(() => {
      const b = [...document.querySelectorAll('button')]
        .find((x) => (x.innerText || '').trim() === '仅必要 Cookie');
      if (b) b.click();
      return !!b;
    })()`);
    await sleep(400);

    // Pick the endpoint.
    const current = await evaluate(
      `document.querySelector('#webfetch-endpoint')?.innerText.trim()`
    );
    if (current !== endpointLabel) {
      await realClick('#webfetch-endpoint');
      await sleep(700);
      await clickByText(endpointLabel);
      await sleep(700);
    }

    // Fill the target URL. React controls this input, so drive it through the
    // native value setter + input event. Retry: right after navigation React may
    // not have hydrated yet and the value gets reverted to the default.
    const fillOnce = () => evaluate(`(() => {
      const el = document.querySelector('#webfetch-url');
      if (!el) return 'NOT_FOUND';
      const setter = Object.getOwnPropertyDescriptor(
        HTMLInputElement.prototype, 'value'
      ).set;
      el.focus();
      setter.call(el, ${JSON.stringify(url)});
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return el.value;
    })()`);

    let filled = await fillOnce();
    for (let attempt = 0; attempt < 6 && filled !== url; attempt++) {
      await sleep(700);
      filled = await fillOnce();
    }
    if (filled !== url) throw new Error('could not fill URL, got: ' + filled);
    // Let the request-body preview re-render before we grab the "before" state.
    await sleep(600);

    const before = await evaluate(`(() => {
      const p = [...document.querySelectorAll('pre')]
        .map((e) => e.innerText).filter((t) => t.trim().startsWith('{'));
      const cand = p.filter((t) => t.includes('"request_id"'));
      return cand.length ? cand[cand.length - 1] : '';
    })()`);

    // Run it.
    await clickByText('运行请求');

    // Poll until a *different* response (new request_id) shows up.
    let out = '';
    for (let i = 0; i < 90; i++) {
      await sleep(500);
      const cand = await evaluate(`(() => {
        const p = [...document.querySelectorAll('pre')]
          .map((e) => e.innerText).filter((t) => t.trim().startsWith('{'));
        const c = p.filter((t) => t.includes('"request_id"'));
        return c.length ? c[c.length - 1] : '';
      })()`);
      if (cand && cand !== before) {
        out = cand;
        break;
      }
    }
    if (!out) throw new Error('no response captured (check quota / network)');
    process.stdout.write(out + '\n');
  } finally {
    close();
  }
}

main().catch((e) => {
  console.error('ERROR: ' + e.message);
  process.exit(1);
});
