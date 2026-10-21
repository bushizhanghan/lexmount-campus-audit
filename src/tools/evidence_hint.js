(() => {
  const body = document.body.innerText;
  // 找 evidenceLink 附近的说明文字
  const el = document.querySelector('#evidenceLink');
  let near = '';
  if (el) {
    const g = el.closest('div')?.parentElement?.parentElement;
    if (g) near = (g.innerText || '').slice(0, 800);
  }
  return {
    url: location.href,
    evidenceLinkNear: near,
    // 页面里关于"链接""公开""材料"的说明
    hints: (body.match(/[^\n]*(材料|链接|公开|演示)[^\n]*/g) || []).slice(0, 20),
    fullText: body.slice(0, 3500),
  };
})()
