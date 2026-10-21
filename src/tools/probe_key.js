(() => {
  // 查找页面里是否缓存了完整 key（Next.js 的 __NEXT_DATA__ / React props / fetch 缓存）
  const out = { sources: [] };

  const html = document.documentElement.outerHTML;
  const k = html.match(/ZAwJEKQRTI[A-Za-z0-9_\-]{6,}/g);
  out.inHtml = k ? k.slice(0, 5) : null;

  // Next.js 飞行数据
  const scripts = [...document.querySelectorAll('script')].map((s) => s.textContent || '').join('\n');
  const k2 = scripts.match(/ZAwJEKQRTI[A-Za-z0-9_\-]{6,}/g);
  out.inScripts = k2 ? k2.slice(0, 5) : null;

  // 全量搜索形如 20-40 位且含大写小写数字的 key
  const all = html.match(/[A-Za-z0-9_\-]{28,48}/g) || [];
  const cand = all.filter((x) => /[A-Z]/.test(x) && /[a-z]/.test(x) && /\d/.test(x));
  out.candidates = [...new Set(cand)].slice(0, 15);

  return out;
})()
