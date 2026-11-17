/* 统一外观面板：深/浅/跟随系统、5 主题色、简/繁/EN。所有页面共用。 */
(function () {
  if (window.TF_APPEARANCE) return;

  var root = document.documentElement;
  var LS_THEME = 'tf-theme';
  var LS_ACCENT = 'tf-accent';
  var LS_LANG = 'tf-lang';
  var mql = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  var ACCENTS = [
    ['graphite', '薄荷'], ['indigo', '靛蓝'], ['teal', '青绿'],
    ['clay', '陶土'], ['plum', '梅紫']
  ];
  var LANGS = [['zh', '简体'], ['zh-Hant', '繁體'], ['en', 'EN']];

  var Q = new URLSearchParams(location.search);
  var urlMode = Q.get('theme');
  var urlAccent = Q.get('accent');
  function mode() { return urlMode || localStorage.getItem(LS_THEME) || 'dark'; }
  function accent() { return urlAccent || localStorage.getItem(LS_ACCENT) || 'graphite'; }
  function resolved() {
    var m = mode();
    if (m === 'system') return mql && mql.matches ? 'dark' : 'light';
    return m;
  }
  function applyTheme() {
    root.dataset.theme = resolved();
    root.dataset.themeMode = mode();
    sync();
  }
  function applyAccent() {
    root.dataset.accent = accent();
    sync();
  }
  function applyLang() {
    root.lang = localStorage.getItem(LS_LANG) || 'zh';
  }
  function setTheme(m) {
    urlMode = null;
    localStorage.setItem(LS_THEME, m);
    applyTheme();
  }
  function setAccent(a) {
    urlAccent = null;
    localStorage.setItem(LS_ACCENT, a);
    applyAccent();
  }
  function setLang(l) {
    localStorage.setItem(LS_LANG, l);
    applyLang();
    location.reload();
  }

  // boot 已在 CSS 前应用；这里只同步属性，等面板建好后再 sync()
  root.dataset.theme = resolved();
  root.dataset.themeMode = mode();
  root.dataset.accent = accent();
  root.lang = localStorage.getItem(LS_LANG) || 'zh';

  if (mql && mql.addEventListener) {
    mql.addEventListener('change', function () { if (mode() === 'system') applyTheme(); });
  }

  var panel = document.createElement('div');
  panel.id = 'tfAppearance';
  panel.className = 'tf-appearance';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', '外观设置');
  panel.innerHTML =
    '<div class="tf-ap-head"><div><div class="tf-ap-kicker">APPEARANCE</div><b>外观</b></div>' +
    '<button class="tf-ap-close" aria-label="关闭">×</button></div>' +
    '<div class="tf-ap-label">主题模式 <em id="tfApModeHint"></em></div>' +
    '<div class="tf-ap-seg" data-group="theme">' +
      '<button data-value="light">亮色</button><button data-value="dark">暗色</button><button data-value="system">跟随系统</button>' +
    '</div>' +
    '<div class="tf-ap-label">主题色</div>' +
    '<div class="tf-ap-swatches">' + ACCENTS.map(function (a) {
      return '<button class="tf-ap-swatch" data-accent="' + a[0] + '" title="' + a[1] + '">' +
        '<i></i><span>' + a[1] + '</span></button>';
    }).join('') + '</div>' +
    '<div class="tf-ap-label">语言 <em>切换后刷新</em></div>' +
    '<div class="tf-ap-seg" data-group="lang">' + LANGS.map(function (l) {
      return '<button data-value="' + l[0] + '">' + l[1] + '</button>';
    }).join('') + '</div>' +
    '<div class="tf-ap-foot">设置保存在本机，所有页面生效。</div>';
  document.body.appendChild(panel);

  function sync() {
    if (!panel) return;
    var m = mode();
    var r = resolved();
    panel.querySelectorAll('[data-group="theme"] button').forEach(function (b) {
      b.classList.toggle('on', b.dataset.value === m);
    });
    panel.querySelectorAll('.tf-ap-swatch').forEach(function (b) {
      b.classList.toggle('on', b.dataset.accent === root.dataset.accent);
    });
    panel.querySelectorAll('[data-group="lang"] button').forEach(function (b) {
      b.classList.toggle('on', b.dataset.value === (localStorage.getItem(LS_LANG) || 'zh'));
    });
    var hint = panel.querySelector('#tfApModeHint');
    if (hint) hint.textContent = m === 'system' ? (r === 'dark' ? '当前暗色' : '当前亮色') : '';
    document.querySelectorAll('#themeBtn,#themeBtn2').forEach(function (b) {
      b.innerHTML = '<svg class="icon sm"><use href="#' + (r === 'dark' ? 'i-moon' : 'i-sun') + '"/></svg>';
      b.setAttribute('aria-label', '外观设置');
      b.style.display = 'none';
    });
  }

  function openPanel() {
    sync();
    panel.classList.add('show');
    var b = document.getElementById('tfAppearanceBtn');
    if (b) b.setAttribute('aria-expanded', 'true');
  }
  function closePanel() {
    panel.classList.remove('show');
    var b = document.getElementById('tfAppearanceBtn');
    if (b) b.setAttribute('aria-expanded', 'false');
  }
  function togglePanel(e) {
    if (e) e.stopPropagation();
    panel.classList.contains('show') ? closePanel() : openPanel();
  }

  panel.querySelector('.tf-ap-close').addEventListener('click', closePanel);
  panel.querySelectorAll('[data-group="theme"] button').forEach(function (b) {
    b.addEventListener('click', function () { setTheme(b.dataset.value); });
  });
  panel.querySelectorAll('.tf-ap-swatch').forEach(function (b) {
    b.addEventListener('click', function () { setAccent(b.dataset.accent); });
  });
  panel.querySelectorAll('[data-group="lang"] button').forEach(function (b) {
    b.addEventListener('click', function () { setLang(b.dataset.value); });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('#tfAppearance') && !e.target.closest('#tfAppearanceBtn') &&
        !e.target.closest('#themeBtn') && !e.target.closest('#themeBtn2')) closePanel();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closePanel(); });

  var bar = document.querySelector('.topbar');
  var btn = document.createElement('button');
  btn.id = 'tfAppearanceBtn';
  btn.className = 'btn ghost sm tf-appearance-btn';
  btn.title = '外观 / Appearance';
  btn.setAttribute('aria-label', '外观设置');
  btn.setAttribute('aria-expanded', 'false');
  btn.innerHTML = '<svg class="icon sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">' +
    '<path d="M12 3a9 9 0 1 0 0 18h1.2a1.8 1.8 0 0 0 1.4-3l-.4-.5a1.4 1.4 0 0 1 1.1-2.3H17a4 4 0 0 0 4-4A8.8 8.8 0 0 0 12 3Z"/>' +
    '<circle cx="7.5" cy="10" r="1"/><circle cx="10" cy="6.8" r="1"/><circle cx="14" cy="6.8" r="1"/><circle cx="16.5" cy="10" r="1"/></svg>';
  btn.addEventListener('click', togglePanel);
  if (bar) bar.appendChild(btn); else document.body.appendChild(btn);

  ['themeBtn', 'themeBtn2'].forEach(function (id) {
    var b = document.getElementById(id);
    if (b) b.addEventListener('click', togglePanel);
  });
  sync();
  if (new URLSearchParams(location.search).get('panel') === '1') openPanel();
  window.TF_APPEARANCE = { open: openPanel, close: closePanel, setTheme: setTheme, setAccent: setAccent, setLang: setLang };
})();
