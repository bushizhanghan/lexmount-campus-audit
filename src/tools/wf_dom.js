(() => {
  const els = [...document.querySelectorAll('input,textarea,select,button,a')];
  const ided = [...document.querySelectorAll('[id]')].map((e) => e.id).filter(Boolean);
  return {
    url: location.href,
    title: document.title,
    readyState: document.readyState,
    totalInputs: document.querySelectorAll('input').length,
    hasWebfetchUrl: !!document.querySelector('#webfetch-url'),
    webdebugIds: ided.filter((x) => /webfetch|endpoint|url/i.test(x)),
    controls: els.slice(0, 30).map((e, i) => ({
      i, tag: e.tagName, type: e.type || null, id: e.id || null,
      txt: (e.innerText || '').trim().slice(0, 30), val: (e.value || '').slice(0, 40),
    })),
    bodyHead: document.body.innerText.slice(0, 600),
  };
})()
