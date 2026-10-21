(() => {
  const body = document.body.innerText;
  return {
    spinner: !!document.querySelector('[class*="spinner"],[class*="loading"],[role="progressbar"]'),
    text: body.slice(0, 300),
    errors: window.__errs || null,
    pm: performance.getEntriesByType('resource')
      .filter((r) => ['fetch', 'xmlhttprequest'].includes(r.initiatorType))
      .map((r) => ({ name: r.name.slice(0, 120), dur: Math.round(r.duration), size: r.transferSize }))
      .slice(-15),
  };
})()
