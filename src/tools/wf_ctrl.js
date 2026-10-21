(() => {
  const inputs = [...document.querySelectorAll('input,textarea')];
  const btns = [...document.querySelectorAll('button')];
  return {
    inputs: inputs.map((e, i) => ({
      i, tag: e.tagName, type: e.type, id: e.id || null,
      ph: e.placeholder || null, val: e.value, cls: e.className.slice(0, 60),
    })),
    buttons: btns.map((e, i) => ({ i, txt: (e.innerText || '').trim().slice(0, 30), id: e.id || null })),
    endpointBtn: btns.findIndex((b) => (b.innerText || '').includes('/v1/')),
  };
})()
