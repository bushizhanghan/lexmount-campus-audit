(() => {
  const els = [...document.querySelectorAll('input,textarea,select')];
  const btnByText = {};
  return {
    url: location.href,
    fields: els.map((e) => {
      let label = null;
      if (e.id) {
        const l = document.querySelector(`label[for="${e.id}"]`);
        if (l) label = l.innerText.trim();
      }
      if (!label && e.closest('div')) {
        const g = e.closest('div')?.parentElement;
        if (g) label = (g.innerText || '').split('\n')[0].trim().slice(0, 40);
      }
      return {
        tag: e.tagName,
        type: e.type,
        id: e.id || null,
        name: e.name || null,
        ph: e.placeholder || null,
        label,
        value: (e.value || '').slice(0, 60),
        required: e.required,
      };
    }),
    textareas: [...document.querySelectorAll('textarea')].map((t) => ({
      id: t.id, name: t.name, ph: t.placeholder, rows: t.rows,
    })),
    bodyText: document.body.innerText.slice(0, 2200),
  };
})()
