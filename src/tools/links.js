// click_nav.js — 在当前页面点击某个链接/按钮并返回新状态
(() => {
  const body = document.body.innerText;
  const links = [...document.querySelectorAll('a[href]')].map((a) => ({
    txt: (a.innerText || '').trim().slice(0, 24),
    href: a.getAttribute('href'),
  })).filter((x) => x.txt);
  return {
    url: location.href,
    title: document.title,
    readyState: document.readyState,
    textLen: body.length,
    head: body.slice(0, 200),
    links: links.slice(0, 40),
  };
})()
