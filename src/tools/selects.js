(() => {
  const sels = [...document.querySelectorAll('select')];
  return {
    url: location.href,
    selects: sels.map((s, i) => {
      // 找 label
      let label = null;
      const fs = s.closest('div')?.parentElement;
      if (fs) label = (fs.innerText || '').split('\n').slice(0, 2).join(' ').trim().slice(0, 50);
      return {
        i,
        name: s.name,
        label,
        options: [...s.options].map((o) => ({ v: o.value, t: o.textContent.trim().slice(0, 50) })),
      };
    }),
  };
})()
