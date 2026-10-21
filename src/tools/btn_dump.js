(() => {
  return {
    url: location.href,
    buttons: [...document.querySelectorAll('button')].map((b) => ({
      t: (b.innerText || '').trim().slice(0, 24),
      dis: b.disabled,
      aria: b.getAttribute('aria-label'),
    })).filter((x) => x.t || x.aria),
    tailText: document.body.innerText.slice(-600),
  };
})()
