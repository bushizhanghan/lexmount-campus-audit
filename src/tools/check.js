(() => {
  const body = document.body.innerText;
  const i = body.indexOf('响应');
  const tail = i >= 0 ? body.slice(i, i + 1200) : body.slice(0, 1200);
  return {
    url: location.href,
    inputUrl: document.querySelector('#webfetch-url')?.value,
    response: tail,
    alerts: [...document.querySelectorAll('[role="alert"],[role="status"]')].map((e) => e.innerText.trim()).filter(Boolean),
  };
})()
