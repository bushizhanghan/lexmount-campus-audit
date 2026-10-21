(() => {
  const out = { url: location.href, title: document.title };
  out.hasMonaco = typeof window.monaco !== 'undefined';
  try {
    const models = window.monaco?.editor?.getModels?.() || [];
    out.monacoModelCount = models.length;
    out.code = models[0]?.getValue?.()?.slice(0, 600) ?? null;
  } catch (e) {
    out.monacoErr = String(e);
  }
  out.textareas = [...document.querySelectorAll('textarea')].length;
  out.buttons = [...document.querySelectorAll('button')]
    .map((b) => (b.innerText || '').trim())
    .filter(Boolean)
    .slice(0, 30);
  out.apiCalls = performance
    .getEntriesByType('resource')
    .map((r) => r.name)
    .filter((n) => /\/api\//.test(n))
    .slice(-25);
  return out;
})()
