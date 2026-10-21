(() => {
  const body = document.body.innerText;
  return {
    url: location.href,
    text: body.slice(0, 2200),
    buttons: [...document.querySelectorAll('button')].map((b) => (b.innerText || '').trim()).filter(Boolean).slice(0, 25),
    inputs: [...document.querySelectorAll('input,textarea')].map((e) => ({ type: e.type, ph: e.placeholder, val: (e.value || '').slice(0, 40) })),
    codes: [...document.querySelectorAll('code,pre,[class*="mono"]')].map((e) => (e.innerText || '').trim()).filter((x) => x.length > 8).slice(0, 10),
  };
})()
