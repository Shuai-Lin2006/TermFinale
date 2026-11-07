(function () {
  if (navigator.userAgent.indexOf('Electron') >= 0) document.documentElement.classList.add('tf-electron');
  var doc = document.getElementById('doc');
  var toolbar = document.getElementById('toolbar');
  var drawer = document.getElementById('drawer');
  var quoteEl = document.getElementById('quote');
  var answerEl = document.getElementById('answer');
  function chapterOf(node) {
    var found = '';
    var heads = document.querySelectorAll('#content h2, .chapter-title');
    Array.prototype.forEach.call(heads, function (h) {
      if (h.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING) found = h.textContent.trim();
    });
    return found;
  }

  var selectedText = '';
  var currentChapter = '';
  var lastQuestion = '';

  /* 主题与强调色 */
  var html = document.documentElement;
  html.dataset.theme = localStorage.getItem('tf-theme') || 'light';
  html.dataset.accent = localStorage.getItem('tf-accent') || 'graphite';

  var params = new URLSearchParams(location.search);
  if (params.get('theme')) html.dataset.theme = params.get('theme');
  if (params.get('accent')) html.dataset.accent = params.get('accent');

  var panel = document.createElement('div');
  panel.className = 'theme-panel';
  panel.innerHTML =
    '<div class="tp-label">模式</div>' +
    '<div class="tp-seg"><button data-t="light">亮色</button><button data-t="dark">暗色</button></div>' +
    '<div class="tp-label">强调色</div>' +
    '<div class="swatches">' +
    ['graphite', 'indigo', 'teal', 'clay', 'plum'].map(function (a) {
      return '<button data-accent="' + a + '" title="' + a + '"></button>';
    }).join('') + '</div>';
  document.body.appendChild(panel);

  function syncPanel() {
    panel.querySelectorAll('.tp-seg button').forEach(function (b) {
      b.classList.toggle('on', b.dataset.t === html.dataset.theme);
    });
    panel.querySelectorAll('.swatches button').forEach(function (b) {
      b.classList.toggle('on', b.dataset.accent === html.dataset.accent);
    });
  }
  syncPanel();
  if (params.get('panel') === '1') panel.classList.add('show');
  panel.querySelectorAll('.tp-seg button').forEach(function (b) {
    b.addEventListener('click', function () {
      html.dataset.theme = b.dataset.t;
      localStorage.setItem('tf-theme', b.dataset.t);
      syncPanel();
    });
  });
  panel.querySelectorAll('.swatches button').forEach(function (b) {
    b.addEventListener('click', function () {
      html.dataset.accent = b.dataset.accent;
      localStorage.setItem('tf-accent', b.dataset.accent);
      syncPanel();
    });
  });
  ['themeBtn', 'themeBtn2'].forEach(function (id) {
    var b = document.getElementById(id);
    if (b) b.addEventListener('click', function (e) {
      e.stopPropagation();
      panel.classList.toggle('show');
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.theme-panel') && !e.target.closest('#themeBtn') && !e.target.closest('#themeBtn2')) {
      panel.classList.remove('show');
    }
  });

  /* Toast */
  var toastEl = document.getElementById('toast');
  function toast(msg) {
    toastEl.textContent = msg; toastEl.classList.add('show');
    clearTimeout(toastEl._t); toastEl._t = setTimeout(function () { toastEl.classList.remove('show'); }, 2400);
  }
  window.__toast = toast;
  document.querySelectorAll('[data-toast]').forEach(function (el) {
    el.addEventListener('click', function (e) { e.preventDefault(); toast(el.dataset.toast); });
  });

  /* 选中工具条 */
  if (doc && toolbar) {
    document.addEventListener('mouseup', function (e) {
      if (e.target.closest('.drawer') || e.target.closest('.toolbar')) return;
      setTimeout(function () {
        var sel = window.getSelection();
        var text = sel ? sel.toString().trim() : '';
        if (!text || text.length < 2 || text.length > 400 || !sel.anchorNode || !doc.contains(sel.anchorNode)) {
          toolbar.classList.remove('show'); return;
        }
        selectedText = text;
        currentChapter = chapterOf(sel.anchorNode) || '';
        var r = sel.getRangeAt(0).getBoundingClientRect();
        toolbar.classList.add('show');
      }, 10);
    });
    document.addEventListener('mousedown', function (e) {
      if (!e.target.closest('.toolbar')) toolbar.classList.remove('show');
    });
    toolbar.querySelectorAll('button').forEach(function (b) {
      b.addEventListener('click', function () {
        toolbar.classList.remove('show');
        if (b.dataset.mode === 'mistake') {
          if (!window.TF_COURSE_ID) { if (window.__toast) window.__toast('请从课程进入阅读器'); return; }
          fetch('/api/mistakes', { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course_id: window.TF_COURSE_ID, question: selectedText }) })
            .then(function () { if (window.__toast) window.__toast('已加入错题本，明天开始复习'); })
            .catch(function () { if (window.__toast) window.__toast('加入失败'); });
          return;
        }
        openDrawer(selectedText, { explain: '解释这段内容', example: '给一个期末可能考的例子', quiz: '出一道小题并给答案' }[b.dataset.mode] || '解释这段内容');
      });
    });
  }

  window.TF_SELECT_TEXT = function (text) {
    if (!text) return;
    selectedText = text;
    toolbar.classList.add('show');
  };

  /* 抽屉 */
  var talkHistory = [];
  function openDrawer(context, question, quoteText) {
    if (!drawer) return;
    if (window.TF_LAST_RAW_CONTEXT && window.TF_LAST_RAW_CONTEXT !== context) talkHistory = [];
    window.TF_LAST_RAW_CONTEXT = context;
    var historyText = talkHistory.slice(-6).map(function(x){ return 'Q: '+x.q+'\nA: '+x.a.slice(0,300); }).join('\n');
    context = (context || '') + (historyText ? ('\n【对话历史】\n' + historyText) : '');
    window.TF_LAST_CONTEXT = context || '';
    var _q = quoteText || (context && context.length > 260 ? '整篇讲义' : context);
    quoteEl.textContent = _q || '（未选中内容）';
    drawer.classList.add('open');
    answerEl.innerHTML = '<span class="loading">思考中…</span>';
    lastQuestion = question;
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 90000);
    fetch('/api/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({ context: (context || '') + '\n' + (currentChapter || ''),
                             question: question, mode: 'explain',
                             course: window.TF_COURSE || '', chapter: currentChapter || '' })
    }).then(function (r) { clearTimeout(timer); return r.json(); })
      .then(function (d) {
        if (!d.answer) throw new Error('没有返回内容');
        var safe = d.answer.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        talkHistory.push({q: question, a: d.answer});
        if (talkHistory.length > 8) talkHistory.shift();
        answerEl.innerHTML = safe.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
        if (window.renderMathInElement) { try { renderMathInElement(answerEl, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false},{left:'\\(',right:'\\)',display:false}],throwOnError:false}); } catch(e){} }
        if (window.renderMathInElement) {
          try { renderMathInElement(answerEl, { delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }], throwOnError: false }); } catch (e) {}
        }
      })
      .catch(function (err) {
        clearTimeout(timer);
        answerEl.innerHTML = '<span class="err">' + (err.name === 'AbortError' ? '回答超时，请重试' : (err.message || '问答服务不可用')) + '</span>';
      });
  }
  window.TF_ASK = openDrawer;
  function closeDrawer() { if (drawer) drawer.classList.remove('open'); }
  document.getElementById('drawerClose')?.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeDrawer(); toolbar && toolbar.classList.remove('show'); }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault(); document.getElementById('searchBox')?.focus?.(); toast('搜索（演示）');
    }
  });


  /* 右侧提问 */
  var railAsk = document.getElementById('railAsk');
  var railSend = document.getElementById('railSend');
  if (railSend) {
    railSend.addEventListener('click', function () {
      var q = (railAsk.value || '').trim();
      if (!q) { toast('先写一个问题'); return; }
      var _sel = window.TF_SELECTED || '';
      var _ctx = _sel
        ? _sel + '\n\n【当前页参考】\n' + (window.TF_PAGE_TEXT || '')
        : (window.TF_DOC_TEXT || window.TF_PAGE_TEXT || '');
      openDrawer(_ctx, q, _sel ? _sel.slice(0, 500) : '整篇讲义');
      railAsk.value = '';
    });
  }
  document.getElementById('mAsk')?.addEventListener('click', function (e) {
    e.preventDefault(); openDrawer('', '解释这一节');
  });

  /* 复制 */
  document.getElementById('copyBtn')?.addEventListener('click', function () {
    var text = answerEl.innerText;
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(function () { toast('已复制'); });
    else toast('复制失败');
  });


  /* 图片点击放大 */
  var lightbox = null;
  document.addEventListener('click', function (e) {
    var img = e.target.closest && e.target.closest('.doc figure img');
    if (img) {
      if (!lightbox) {
        lightbox = document.createElement('div');
        lightbox.className = 'tf-lightbox';
        lightbox.innerHTML = '<img alt=""><div class="hint">点击任意处关闭 · Esc</div>';
        document.body.appendChild(lightbox);
        lightbox.addEventListener('click', function () { lightbox.classList.remove('show'); });
      }
      lightbox.querySelector('img').src = img.src;
      lightbox.classList.add('show');
      return;
    }
    if (lightbox && e.target === lightbox) lightbox.classList.remove('show');
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && lightbox) lightbox.classList.remove('show');
  });


  /* 名词点击解释 */
  var kwPop = null;
  document.addEventListener('click', function (e) {
    var kw = e.target.closest && e.target.closest('.kw');
    if (kw && kw.title) {
      if (!kwPop) { kwPop = document.createElement('div'); kwPop.className = 'kw-pop'; document.body.appendChild(kwPop); }
      kwPop.textContent = kw.title;
      var r = kw.getBoundingClientRect();
      kwPop.style.left = Math.min(Math.max(8, r.left), innerWidth - 330) + 'px';
      kwPop.style.top = (r.bottom + 8) + 'px';
      kwPop.style.display = 'block';
      e.stopPropagation();
      return;
    }
    if (kwPop) kwPop.style.display = 'none';
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && kwPop) kwPop.style.display = 'none'; });


  /* 统一返回按钮：固定层级，不依赖历史 */
  (function () {
    var path = location.pathname.split('/').pop() || '';
    if (path === 'dashboard.html' || path === 'welcome.html' || path === '' || path === '/') return;
    var cid = new URLSearchParams(location.search).get('course');
    var parent = 'dashboard.html';
    if (path === 'reader.html') parent = cid ? ('course_detail.html?course=' + cid) : 'courses.html';
    else if (path === 'course_detail.html') parent = 'courses.html';
    else if (path === 'generate.html' || path === 'upload.html') parent = cid ? ('course_detail.html?course=' + cid) : 'courses.html';
    else if (path === 'materials_stats.html') parent = cid ? ('course_detail.html?course=' + cid) : 'dashboard.html';
    else if (path === 'courses.html') parent = 'dashboard.html';
    var existing = document.querySelector('.topbar a');
    if (existing && /返回|Back/.test(existing.textContent)) return;
    var btn = document.createElement('button');
    btn.className = 'btn ghost sm nav-back';
    btn.innerHTML = '← <span data-back-label>返回</span>';
    btn.addEventListener('click', function () { location.href = parent; });
    var bar = document.querySelector('.topbar');
    if (bar) bar.insertBefore(btn, bar.firstChild);
    else {
      var host = document.getElementById('doc') || document.body;
      host.insertBefore(btn, host.firstChild);
      btn.classList.add('nav-back-inline');
    }
  })();

  /* 拦截 WKWebView 横向滑动返回：输入框拖选时会误触 */
  try {
    history.pushState({ tf: 1 }, '', location.href);
    window.addEventListener('popstate', function () {
      history.pushState({ tf: 1 }, '', location.href);
    });
  } catch (e) {}


  /* 内部页面改为 replace 跳转：不产生历史记录，滑动返回无页可回 */
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (!/\.html(?:\?|$)/.test(href)) return;
    if (a.target === '_blank' || e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    location.replace(a.href);
  }, true);

  /* 统一侧栏：所有页面共用同一份导航，避免缺项/缺图标 */
  var TF_NAV = [
    ["dashboard.html", "今日冲刺", '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>'],
    ["courses.html", "我的课程", '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v18H6.5A2.5 2.5 0 0 1 4 18.5z"/><path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20"/>'],
    ["practice.html", "练习与错题", '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/>'],
    ["review_plan.html", "复习计划", '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'],
    ["materials_stats.html", "资料统计", '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>'],
    ["notes.html", "笔记", '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v18H6.5A2.5 2.5 0 0 1 4 18.5z"/><path d="M8 8h8M8 12h6"/>'],
    ["settings.html", "设置", '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1Z"/>']
  ];
  function renderNav() {
    var nav = document.querySelector('.rail .nav');
    if (!nav) return;
    var current = location.pathname.split('/').pop() || 'dashboard.html';
    nav.innerHTML = TF_NAV.map(function (it) {
      var active = (current === it[0]) ? ' active' : '';
      return '<a class="nav-item' + active + '" href="' + it[0] + '">'
        + '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + it[2] + '</svg>'
        + it[1] + '</a>';
    }).join('');
  }
  function renderFoot(p) {
    var rail = document.querySelector('.rail');
    if (!rail) return;
    var foot = rail.querySelector('.rail-foot');
    if (!foot) { foot = document.createElement('div'); foot.className = 'rail-foot'; rail.appendChild(foot); }
    var _l = localStorage.getItem('tf-lang');
    var name = p && p.name ? p.name : (_l === 'en' ? 'Student' : (_l === 'zh-Hant' ? '同學' : '同学'));
    var major = p && p.major ? p.major : (_l === 'en' ? 'Major not set' : (_l === 'zh-Hant' ? '未填寫專業' : '未填写专业'));
    var avatar = p && p.avatar ? '<img src="' + p.avatar + '" style="width:100%;height:100%;object-fit:cover;border-radius:50%">' : name.slice(0, 1);
    foot.innerHTML = '<div class="user"><div class="avatar">' + avatar + '</div><div><b>' + name + '</b><div class="tiny muted">' + major + '</div></div></div>';
    document.body.classList.add('profile-ready');
  }
  renderNav();
  renderFoot(null);

  /* 真实档案：先用缓存立即渲染，再拉接口更新 */
  function applyProfile(p) {
    if (!p || !p.name) return;
    window.TF_PROFILE = p;
    try { localStorage.setItem('tf-profile', JSON.stringify(p)); } catch (e) {}
    renderFoot(p);
  }
  try { applyProfile(JSON.parse(localStorage.getItem('tf-profile') || 'null')); } catch (e) {}
  fetch('/api/profile').then(function (r) { return r.json(); }).then(applyProfile).catch(function () { renderFoot(null); });

  /* 导航高亮 */
  document.querySelectorAll('.nav-item').forEach(function (item) {
    item.addEventListener('click', function () {
      document.querySelectorAll('.nav-item').forEach(function (i) { i.classList.remove('active'); });
      item.classList.add('active');
    });
  });

  /* 目录高亮 */
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  var heads = tocLinks.map(function (a) { return document.querySelector(a.getAttribute('href')); }).filter(Boolean);
  if ('IntersectionObserver' in window && heads.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var i = heads.indexOf(en.target);
        tocLinks.forEach(function (l, j) { l.classList.toggle('active', i === j); });
      });
    }, { rootMargin: '-10% 0px -80% 0px' });
    heads.forEach(function (h) { io.observe(h); });
  }
})();
