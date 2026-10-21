// git_sync.mjs — 把项目全部源码、数据、文档增量推送到 GitHub 仓库
import fs from 'node:fs';
import path from 'node:path';

const OWNER = 'bushizhanghan';
const REPO = 'lexmount-campus-audit';
const API = 'https://api.github.com';
const SITE = 'E:\\dsh\\output\\gh-pages-site';
const PROJECT = 'E:\\dsh\\output\\webfetch-playground';

const TOKEN_FILE = 'E:\\dsh\\output\\gh-pages-site\\.gh_token.tmp';
let TOKEN = '';
try {
  TOKEN = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
} catch {}

if (!TOKEN) {
  console.error('需要 GitHub token（凭据管理器里的 ghp_...）');
  process.exit(1);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function req(method, p, body) {
  const url = p.startsWith('http') ? p : API + p;
  const r = await fetch(url, {
    method,
    headers: {
      Authorization: 'Bearer ' + TOKEN,
      Accept: 'application/vnd.github+json',
      'User-Agent': 'dsh-agent',
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const txt = await r.text();
  return { status: r.status, body: txt };
}

// 1. 身份
const me = await (await fetch(API + '/user', {
  headers: { Authorization: 'Bearer ' + TOKEN, 'User-Agent': 'dsh-agent' },
})).json();
console.log('身份:', me.login);

// 2. 取远端文件树（拿 sha）
const tree = await (await fetch(`${API}/repos/${OWNER}/${REPO}/git/trees/main?recursive=1`, {
  headers: { Authorization: 'Bearer ' + TOKEN, 'User-Agent': 'dsh-agent' },
})).json();
const remote = new Map();
for (const it of tree.tree || []) {
  if (it.type === 'blob') remote.set(it.path, it.sha);
}
console.log('远端已有文件:', remote.size);

// 3. 收集本地待传文件
const SKIP = new Set([
  'push-to-github-pages.ps1', 'push_update.py', 'get_gh_token.py',
  'read_cred.py', 'read-cred.ps1', 'create_and_push.py', '.gh_token.tmp',
  'report-v3.png', 'report-v4.png', 'report-top.png', 'report-final.png',
  'report-shot.png', 'report-full.png', 'shot-loggedin.png',
  '01-extract-example.png', '02-endpoints.png', '03-extract-qq.png',
  'chart-preview.png', 'seg-01.png', 'seg-02.png', 'seg-03.png', 'seg-04.png',
  'v3-seg-01.png', 'v3-seg-02.png', 'v3-seg-03.png', 'v3-seg-04.png', 'v3-seg-05.png',
  'v4-seg-01.png', 'v4-seg-02.png', 'v4-seg-03.png', 'v4-seg-04.png',
  'v5-seg-01.png', 'v5-seg-02.png', 'v5-seg-03.png', 'v5-seg-04.png',
]);

const files = [];
function walk(dir, rel) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === '.git' || e.name === 'node_modules') continue;
    const full = path.join(dir, e.name);
    const r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) {
      walk(full, r);
    } else if (e.isFile()) {
      if (SKIP.has(r) || r.endsWith('.tmp')) continue;
      files.push({ full, rel: r });
    }
  }
}

walk(SITE, '');
// project 源码树
for (const sub of ['sites.json', 'README.md', 'SUBMISSION.md', 'report.html',
                   'audit.py', 'sites.json']) {
  const p = path.join(SITE, sub);
  if (fs.existsSync(p)) continue;
}
const PROJ_FILES = [
  'svg_charts.py', 'build_v4_data.py', 'render_v4.py', 'factcheck_v4.py',
  'dedup_analyze.py', 'js_pollution.py', 'enrich.py', 'analyze.py',
  'report.py', 'compare.py', 'verify_links_final.py', 'verify_spa.py',
  'value_added.py', 'investigate_sjtu.py', 'verify_extra.py',
  'compare_ui_vs_api.py', 'explain_orphans.py', 'probe_api.py',
  'probe_upstream.py', 'probe_chat.py', 'probe_chat_stream.py',
  'probe_cn_tools.py', 'probe_labels.py', 'probe_consts.py',
  'probe_provider.py', 'find_fmt.py', 'scan_upstream_fmt.py',
  'scan_asar.py', 'check_catalogs.py', 'check_template.py',
  'depth_test.mjs', 'drive.mjs', 'batch.mjs', 'preview.py',
  'split_png.py', 'verify.py', 'factcheck.py', 'factcheck_v3.py',
];
for (const f of PROJ_FILES) {
  const p = path.join(PROJECT, 'project', f);
  if (fs.existsSync(p)) files.push({ full: p, rel: 'src/' + f });
}
// tools
const toolsDir = path.join(PROJECT, 'project', 'tools');
if (fs.existsSync(toolsDir)) {
  walk(toolsDir, 'src/tools');
}

console.log('本地待传文件:', files.length);

// 4. 逐个上传（同 sha 跳过）
let ok = 0, skip = 0, fail = 0;
for (const f of files) {
  const content = fs.readFileSync(f.full);
  const b64 = content.toString('base64');

  const sha = remote.get(f.rel);
  if (sha) {
    // 比对内容：GET 现有 blob 太重，用 Contents API 取 size
    const g = await req('GET', `/repos/${OWNER}/${REPO}/contents/${encodeURI(f.rel)}`);
    if (g.status === 200) {
      try {
        const cur = JSON.parse(g.body);
        if (cur.size === content.length) { skip++; continue; }
      } catch {}
    }
  }

  const body = { message: `sync ${f.rel}`, content: b64, branch: 'main' };
  if (sha) body.sha = sha;

  const r = await req('PUT', `/repos/${OWNER}/${REPO}/contents/${encodeURI(f.rel)}`, body);
  if (r.status === 200 || r.status === 201) {
    ok++;
    console.log(`  ✓ ${f.rel} (${content.length.toLocaleString()} B)`);
  } else {
    fail++;
    console.log(`  ✗ ${f.rel}: ${r.status} ${r.body.slice(0, 120)}`);
  }
  await sleep(120);
}

console.log(`\n完成：新增 ${ok} / 跳过 ${skip} / 失败 ${fail}`);
console.log(`仓库：https://github.com/${OWNER}/${REPO}`);
