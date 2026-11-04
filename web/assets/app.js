(function () {
  var doc = document.getElementById('doc');
  var toolbar = document.getElementById('toolbar');
  var drawer = document.getElementById('drawer');
  var quoteEl = document.getElementById('quote');
  var answerEl = document.getElementById('answer');
  var selectedText = '';
  var lastQuestion = '';

  /* 主题 */
  var saved = localStorage.getItem('tf-theme');
  if (saved) document.documentElement.dataset.theme = saved;
  function toggleTheme() {
    var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('tf-theme', next);
  }
  ['themeBtn', 'themeBtn2'].forEach(function (id) {
    var b = document.getElementById(id); if (b) b.addEventListener('click', toggleTheme);
  });

  /* Toast */
  var toastEl = document.getElementById('toast');
  function toast(msg) {
    toastEl.textContent = msg; toastEl.classList.add('show');
    clearTimeout(toastEl._t); toastEl._t = setTimeout(function () { toastEl.classList.remove('show'); }, 2400);
  }
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
        var r = sel.getRangeAt(0).getBoundingClientRect();
        toolbar.classList.add('show');
        var w = toolbar.offsetWidth || 260;
        var left = Math.max(8, Math.min(r.left + r.width / 2 - w / 2, innerWidth - w - 8));
        toolbar.style.left = left + 'px';
        toolbar.style.top = Math.max(8, r.top - 46) + 'px';
      }, 10);
    });
    document.addEventListener('mousedown', function (e) {
      if (!e.target.closest('.toolbar')) toolbar.classList.remove('show');
    });
    toolbar.querySelectorAll('button').forEach(function (b) {
      b.addEventListener('click', function () {
        toolbar.classList.remove('show');
        ask(selectedText, { explain: '解释这段内容', example: '给一个期末可能考的例子', quiz: '出一道小题并给答案' }[b.dataset.mode] || '解释这段内容');
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
    setTimeout(function () { mockAnswer(question); }, 650);
  }
  function closeDrawer() { if (drawer) drawer.classList.remove('open'); }
  document.getElementById('drawerClose')?.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeDrawer(); toolbar && toolbar.classList.remove('show'); }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault(); document.getElementById('searchBox')?.focus?.(); toast('搜索（演示）');
    }
  });

  function mockAnswer(question) {
    var body = question.indexOf('出题') >= 0
      ? '<h5>自测题</h5><p>某电池在 25 ℃ 时 E° = 1.10 V，转移电子数 n = 2，求平衡常数 K°。</p><p><b>答案</b>：由 ln K° = nFE°/RT ≈ 85.9，得 K° ≈ 2.1×10³⁷。</p><p><b>考点</b>：E° 与 K° 的换算，注意 n 和单位。</p>'
      : question.indexOf('例子') >= 0
      ? '<h5>一个期末常见的例子</h5><p>丹尼尔电池 Zn|Zn²⁺‖Cu²⁺|Cu，已知 E° = 1.10 V。若 Zn²⁺ 浓度降到 0.01 mol/L，电动势怎么变？</p><p>用能斯特方程：E = E° − (0.0592/2)·lg([Zn²⁺]/[Cu²⁺])，代入得 E ≈ 1.16 V。浓度降低，电动势反而升高——这是最容易记反的地方。</p>'
      : '<h5>先给结论</h5><p>这段在讲「可逆电池」的三个条件：电极反应可逆、能量转换可逆、电流无限小。考试里常拿“有电流通过”来挖坑。</p><h5>怎么理解</h5><p>把电池想成一座双向都能走的桥：正向走能放电，反向走能充电，而且来回都不损耗能量，才叫可逆。实际电池做不到，所以只能“近似可逆”。</p><h5>易错点</h5><p>ΔG = −nFE 的负号。E 为正说明反应自发，ΔG 必须为负；写成正号就全错。</p>';
    answerEl.innerHTML = body;
  }

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
