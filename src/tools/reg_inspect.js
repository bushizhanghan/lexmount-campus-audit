(() => {
  const body = document.body.innerText;
  const fields = [...document.querySelectorAll('input,select,textarea,button')].map((e, i) => ({
    i,
    tag: e.tagName,
    type: e.type || null,
    id: e.id || null,
    name: e.name || null,
    ph: e.placeholder || null,
    label: e.labels && e.labels[0] ? e.labels[0].innerText.trim() : null,
    txt: (e.innerText || '').trim().slice(0, 30),
    val: (e.value || '').slice(0, 40),
    required: e.required || e.getAttribute('aria-required') === 'true',
  }));
  return { url: location.href, title: document.title, fields, text: body.slice(0, 1500) };
})()
