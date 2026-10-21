(() => {
  const body = document.body.innerText;
  const i = body.indexOf('响应');
  return {
    url: location.href,
    loggedIn: !body.includes('你今天的免登录'),
    inputUrl: document.querySelector('#webfetch-url')?.value,
    quotaHint: (body.match(/[^\n]*次数[^\n]*/g) || []).slice(0, 4),
    responseArea: i >= 0 ? body.slice(i, i + 400) : null,
  };
})()
