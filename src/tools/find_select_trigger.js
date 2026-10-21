(() => {
  // Radix Select：触发器是 button[role=combobox] 或带 data-radix-select-trigger
  const trigs = [...document.querySelectorAll('[role="combobox"], button')].filter((b) => {
    const t = (b.innerText || '').trim();
    return /讲清这次实践|作者与联系信息|本次实践|作品|作者/.test(t);
  });
  return {
    url: location.href,
    triggers: trigs.map((b) => ({
      text: (b.innerText || '').trim().slice(0, 40),
      role: b.getAttribute('role'),
      state: b.getAttribute('data-state'),
      id: b.id,
    })),
    allComboboxes: [...document.querySelectorAll('[role="combobox"]')].map((b) => ({
      text: (b.innerText || '').trim().slice(0, 60),
      state: b.getAttribute('data-state'),
    })),
  };
})()
