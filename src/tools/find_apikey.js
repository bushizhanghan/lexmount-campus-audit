(() => {
  const links = [...document.querySelectorAll('a[href]')]
    .map((a) => ({ t: (a.innerText || '').trim().slice(0, 24), h: a.getAttribute('href') }))
    .filter((x) => x.h && !x.h.startsWith('http'));
  return {
    url: location.href,
    links: links.filter((x) => /api|key|密钥|方案|用量|console|控制台/i.test(x.h + x.t)),
    allLinks: links.slice(0, 40),
  };
})()
