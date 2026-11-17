/* 在 CSS 之前同步应用主题/主题色/语言，避免闪白或“切了页面就丢”。 */
(function () {
  try {
    var q = new URLSearchParams(location.search);
    var mode = q.get('theme') || localStorage.getItem('tf-theme') || 'dark';
    var resolved = mode;
    if (mode === 'system') {
      resolved = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    var accent = q.get('accent') || localStorage.getItem('tf-accent') || 'graphite';
    var lang = q.get('lang') || localStorage.getItem('tf-lang') || 'zh';
    var root = document.documentElement;
    root.dataset.theme = resolved;
    root.dataset.themeMode = mode;
    root.dataset.accent = accent;
    root.lang = lang;
  } catch (e) {}
})();
