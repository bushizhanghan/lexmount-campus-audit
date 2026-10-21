(() => {
  const txt = document.body.innerText;
  return {
    title: document.title,
    h1: document.querySelector('h1')?.innerText.trim(),
    h2Count: document.querySelectorAll('h2').length,
    tableCount: document.querySelectorAll('table').length,
    textLen: txt.length,
    keyNumbers: ['18/20', '38.9%', '0.98x', '498:9', '0.98'].filter((k) => txt.includes(k)),
    cssLoaded: getComputedStyle(document.body).backgroundColor,
  };
})()
