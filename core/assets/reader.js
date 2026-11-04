(function () {
  var cfg = window.TF_BRIDGE || null;
  var root = document.getElementById('main-container');
  if (!root) return;

  var chapters = Array.prototype.slice.call(root.querySelectorAll('h2.chapter-title'));
  var toolbar = null, drawer = null, toastEl = null, currentText = '', currentChapter = '';

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function showToast(msg) {
    if (!toastEl) { toastEl = el('div', 'tf-toast'); document.body.appendChild(toastEl); }
    toastEl.textContent = msg; toastEl.classList.add('show');
    clearTimeout(toastEl._t); toastEl._t = setTimeout(function () { toastEl.classList.remove('show'); }, 2600);
  }

  function chapterOf(node) {
    var found = '';
    chapters.forEach(function (h) { if (h.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING) found = h.textContent.trim(); });
    return found;
  }

  /* ---------- 左栏目录 ---------- */
  if (chapters.length > 1) {
    var toc = el('nav', 'tf-toc');
    toc.appendChild(el('h4', '', '目录'));
    chapters.forEach(function (h) {
      var a = el('a', '', h.textContent.replace(/^第\s*\d+\s*章[:：]?\s*/, ''));
      a.href = '#' + (h.id || '');
      toc.appendChild(a);
      a.addEventListener('click', function (e) {
        e.preventDefault(); h.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    document.body.appendChild(toc);
    var links = Array.prototype.slice.call(toc.querySelectorAll('a'));
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          var i = chapters.indexOf(en.target);
          links.forEach(function (l, j) { l.classList.toggle('active', i === j); });
          renderRail(en.target);
        });
      }, { rootMargin: '-15% 0px -75% 0px' });
      chapters.forEach(function (h) { io.observe(h); });
    }
  }

  /* ---------- 右栏速查 ---------- */
  var rail = el('aside', 'tf-rail');
  var railCard = el('div', 'tf-card');
  rail.appendChild(el('h4', '', '本章速查'));
  rail.appendChild(railCard);
  rail.appendChild(el('p', 'tf-hint', '选中正文任意文字，可直接向 AI 提问（应用需保持打开）。'));
  document.body.appendChild(rail);

  function renderRail(chapter) {
    railCard.innerHTML = '';
    var heads = [];
    var n = chapter.nextElementSibling;
    while (n && !(n.classList && n.classList.contains('chapter-title'))) {
      if (n.tagName === 'H3') heads.push(n.textContent.trim());
      n = n.nextElementSibling;
    }
    if (!heads.length) { railCard.appendChild(el('div', 'tf-hint', '本章暂无小节标题')); return; }
    var ol = el('ol');
    heads.slice(0, 12).forEach(function (t) { ol.appendChild(el('li', '', t)); });
    railCard.appendChild(ol);
  }
  if (chapters.length) renderRail(chapters[0]);

  /* ---------- 选中工具条 ---------- */
  if (cfg) {
    toolbar = el('div', 'tf-toolbar');
    [['explain', '解释一下'], ['example', '举个例子'], ['quiz', '出题考我']].forEach(function (p) {
      var b = el('button', '', p[1]);
      b.addEventListener('mousedown', function (e) { e.preventDefault(); });
      b.addEventListener('click', function () { ask(p[0], currentText); });
      toolbar.appendChild(b);
    });
    document.body.appendChild(toolbar);

    document.addEventListener('mouseup', function (e) {
      if (e.target.closest && (e.target.closest('.tf-drawer') || e.target.closest('.tf-toolbar'))) return;
      setTimeout(function () {
        var sel = window.getSelection();
        var text = sel ? sel.toString().trim() : '';
        if (!text || text.length < 2 || text.length > 400 || !sel.anchorNode || !root.contains(sel.anchorNode)) {
          toolbar.classList.remove('show'); return;
        }
        currentText = text;
        currentChapter = chapterOf(sel.anchorNode);
        var r = sel.getRangeAt(0).getBoundingClientRect();
        toolbar.classList.add('show');
        var tw = toolbar.offsetWidth || 240;
        var left = Math.min(Math.max(8, r.left + r.width / 2 - tw / 2), window.innerWidth - tw - 8);
        toolbar.style.left = left + 'px';
        toolbar.style.top = Math.max(8, r.top - 44) + 'px';
      }, 10);
    });
    document.addEventListener('mousedown', function (e) {
      if (toolbar && !e.target.closest('.tf-toolbar')) toolbar.classList.remove('show');
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hideDrawer(); });
  }

  /* ---------- 抽屉 ---------- */
  function buildDrawer() {
    drawer = el('aside', 'tf-drawer');
    var head = el('header');
    head.appendChild(el('span', '', 'AI 答疑'));
    var close = el('button', 'close', '×');
    close.addEventListener('click', hideDrawer);
    head.appendChild(close);
    drawer.appendChild(head);
    drawer.appendChild(el('div', 'tf-quote'));
    drawer.appendChild(el('div', 'tf-answer'));
    drawer.appendChild(el('footer', '', '回答仅供参考，请对照原始资料。'));
    document.body.appendChild(drawer);
  }
  function hideDrawer() { if (drawer) drawer.classList.remove('open'); }

  function ask(mode, text) {
    if (!cfg) { showToast('请从 TermFinale 中打开本页再使用问答'); return; }
    if (!drawer) buildDrawer();
    toolbar.classList.remove('show');
    drawer.querySelector('.tf-quote').textContent = text;
    var ans = drawer.querySelector('.tf-answer');
    ans.innerHTML = '<span class="loading">思考中…</span>';
    drawer.classList.add('open');

    fetch('http://127.0.0.1:' + cfg.port + '/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-TF-Token': cfg.token },
      body: JSON.stringify({
        context: text.slice(0, 1200) + '\n' + currentChapter,
        question: mode === 'explain' ? '解释这段内容' : mode === 'example' ? '给一个期末可能考的例子' : '出一道小题并给答案',
        mode: mode, course: (window.TF_COURSE || ''), chapter: currentChapter
      })
    }).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (x) {
        if (!x.ok) throw new Error(x.d.error || '请求失败');
        ans.textContent = x.d.answer || '（空）';
        if (window.renderMathInElement) {
          try { renderMathInElement(ans, { delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }], throwOnError: false }); } catch (e) {}
        }
      })
      .catch(function (err) {
        ans.innerHTML = '<span class="err">' + (err.message || '问答服务未启动，请从 TermFinale 打开本页') + '</span>';
      });
  }
})();
