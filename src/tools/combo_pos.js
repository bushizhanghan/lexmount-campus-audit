(() => {
  const combos = [...document.querySelectorAll('[role="combobox"]')];
  const out = [];
  for (let i = 0; i < combos.length; i++) {
    const b = combos[i];
    b.scrollIntoView({ block: 'center' });
    const r = b.getBoundingClientRect();
    out.push({ i, text: b.innerText.trim(), x: r.left + r.width / 2, y: r.top + r.height / 2 });
  }
  return out;
})()
