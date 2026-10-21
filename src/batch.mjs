#!/usr/bin/env node
/**
 * batch.mjs — 批量跑 Web Fetch，逐条落盘，支持断点续跑。
 *
 *   node batch.mjs <extract|dump> [maxRuns]
 *
 * 每条结果写入 runs/<mode>/<slug>.json，已存在的跳过（断点续跑）。
 * 每跑完一条立即写盘，不会因为中断丢失已花掉的额度。
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const MODE = (process.argv[2] || 'extract').toLowerCase();
const MAX = Number(process.argv[3] || 999);
const OUTDIR = path.join(HERE, 'runs', MODE);
fs.mkdirSync(OUTDIR, { recursive: true });

const config = JSON.parse(fs.readFileSync(path.join(HERE, 'sites.json'), 'utf8'));
const sites = config.sites;

function runOne(url) {
  return new Promise((resolve) => {
    const p = spawn(
      process.execPath,
      [path.join(HERE, '..', 'webfetch.mjs'), url, MODE],
      { stdio: ['ignore', 'pipe', 'pipe'] }
    );
    let out = '';
    let err = '';
    p.stdout.on('data', (d) => (out += d));
    p.stderr.on('data', (d) => (err += d));
    p.on('close', (code) => resolve({ code, out, err }));
  });
}

let done = 0, skipped = 0, failed = 0;

for (const s of sites) {
  const file = path.join(OUTDIR, `${s.slug}.json`);
  if (fs.existsSync(file)) {
    skipped++;
    console.log(`- skip ${s.slug} (已存在)`);
    continue;
  }
  if (done >= MAX) {
    console.log(`\n已达到本次上限 ${MAX} 条，停止。`);
    break;
  }

  process.stdout.write(`> ${s.name} ${s.url} ... `);
  const t0 = Date.now();
  const { code, out, err } = await runOne(s.url);
  const ms = Date.now() - t0;

  // 从 stdout 里截出 JSON（前面可能有杂讯）
  const start = out.indexOf('{');
  const jsonText = start >= 0 ? out.slice(start) : '';

  let ok = false;
  let status = null;
  try {
    const parsed = JSON.parse(jsonText);
    ok = true;
    status = parsed.status_code ?? parsed.result?.status_code ?? null;
  } catch {
    /* keep ok=false */
  }

  if (ok) {
    // 附加可追溯的元信息
    const parsed = JSON.parse(jsonText);
    parsed._site = { slug: s.slug, name: s.name, url: s.url };
    parsed._run = { mode: MODE, ran_at: new Date().toISOString(), wall_ms: ms };
    fs.writeFileSync(file, JSON.stringify(parsed, null, 2), 'utf8');
    done++;
    console.log(`ok  http=${status}  ${(ms / 1000).toFixed(1)}s`);
  } else {
    failed++;
    fs.writeFileSync(
      path.join(OUTDIR, `${s.slug}.error.txt`),
      `url: ${s.url}\nexit: ${code}\n---stdout---\n${out}\n---stderr---\n${err}\n`,
      'utf8'
    );
    console.log(`FAIL exit=${code} ${(ms / 1000).toFixed(1)}s`);
  }
}

console.log(`\n完成: 新增 ${done} / 跳过 ${skipped} / 失败 ${failed}`);
