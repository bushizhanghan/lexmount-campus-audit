(() => {
  const body = document.body.innerText;
  return {
    url: location.href,
    // Cloud Browser 试验场的关键控件
    buttons: [...document.querySelectorAll('button')].map((b) => b.innerText.trim()).filter(Boolean).slice(0, 20),
    hasCodeEditor: !!document.querySelector('.monaco-editor, textarea, [class*="cm-editor"]'),
    editors: document.querySelectorAll('.monaco-editor, textarea, [class*="cm-editor"], [contenteditable="true"]').length,
    output: (() => {
      const i = body.indexOf('执行结果');
      return i >= 0 ? body.slice(i, i + 400) : null;
    })(),
  };
})()
