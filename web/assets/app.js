(function () {
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

  /* 抽屉 */
  function openDrawer(context, question) {
    if (!drawer) return;
    quoteEl.textContent = context || '（未选中内容）';
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
        answerEl.innerHTML = safe.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
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
      openDrawer('提问：' + q, q);
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


  /* 统一返回按钮 */
  (function () {
    if (location.pathname.endsWith('dashboard.html') || location.pathname.endsWith('/')) return;
    var btn = document.createElement('button');
    btn.className = 'btn ghost sm nav-back';
    btn.innerHTML = '← <span data-back-label>返回</span>';
    btn.addEventListener('click', function () {
      if (document.referrer && document.referrer.indexOf(location.origin) === 0 && history.length > 1) history.back();
      else location.href = 'courses.html';
    });
    var bar = document.querySelector('.topbar');
    if (bar) bar.insertBefore(btn, bar.firstChild);
    else document.body.appendChild(btn);
  })();

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
