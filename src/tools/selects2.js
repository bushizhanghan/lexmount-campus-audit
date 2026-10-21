(() => {
  const sels = [...document.querySelectorAll('select')];
  return {
    url: location.href,
    outerHTML0: sels[0] ? sels[0].outerHTML.slice(0, 1500) : null,
    outerHTML1: sels[1] ? sels[1].outerHTML.slice(0, 1500) : null,
    // 表单附近完整文本
    formText: (document.querySelector('form') || document.body).innerText.slice(0, 3000),
  };
})()
