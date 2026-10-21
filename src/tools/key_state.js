(() => {
  const t = document.body.innerText;
  const i = t.indexOf('API 密钥');
  return {
    url: location.href,
    ready: t.includes('API 密钥'),
    section: i >= 0 ? t.slice(i, i + 700) : t.slice(0, 400),
    masks: (t.match(/[A-Za-z0-9]{6,12}•{3,}[A-Za-z0-9]{4,8}/g) || []),
    buttons: [...document.querySelectorAll('button')].map((b) => (b.innerText || '').trim()).filter(Boolean),
  };
})()
