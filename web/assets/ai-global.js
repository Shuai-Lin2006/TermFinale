/* 全局 AI 助教：任何页面都能问当前课程；先检索资料页，回答带来源。 */
(function () {
  if (window.__TF_GLOBAL_AI) return;
  if (document.getElementById('askFab') || document.querySelector('.drawer')) return; // 阅读器已有
  window.__TF_GLOBAL_AI = true;

  var COURSES = [];
  var CID = null;
  var HISTORY = [];

  var fab = document.createElement('button');
  fab.className = 'tf-ai-fab';
  fab.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/></svg><span>问 AI</span>';
  document.body.appendChild(fab);

  var drawer = document.createElement('aside');
  drawer.className = 'tf-ai-drawer';
  drawer.innerHTML =
    '<header class="tf-ai-head"><div><div class="eyebrow">AI 助教</div><b>问这门课</b></div>' +
    '<button class="tf-ai-close" aria-label="关闭">×</button></header>' +
    '<div class="tf-ai-course"><span>课程</span><select id="tfAiCourse"></select></div>' +
    '<div class="tf-ai-messages" id="tfAiMessages"><div class="tf-ai-hint">问资料里的概念、步骤、例题；回答会标页码。资料里没有会直说。</div></div>' +
    '<div class="tf-ai-sources" id="tfAiSources"></div>' +
    '<form class="tf-ai-form"><textarea id="tfAiInput" rows="2" placeholder="例如：隐函数求导怎么求？"></textarea>' +
    '<button class="btn primary sm" type="submit">发送</button></form>';
  document.body.appendChild(drawer);

  var msgBox = drawer.querySelector('#tfAiMessages');
  var srcBox = drawer.querySelector('#tfAiSources');
  var input = drawer.querySelector('#tfAiInput');
  var sel = drawer.querySelector('#tfAiCourse');

  function open() { drawer.classList.add('open'); fab.classList.add('hide'); setTimeout(function(){ input.focus(); }, 120); }
  function close() { drawer.classList.remove('open'); fab.classList.remove('hide'); }
  fab.addEventListener('click', open);
  drawer.querySelector('.tf-ai-close').addEventListener('click', close);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); }
  function loadCourses() {
    var q = new URLSearchParams(location.search).get('course');
    var fromPage = window.TF_COURSE_ID || q || null;
    fetch('/api/courses').then(function (r) { return r.json(); }).then(function (list) {
      COURSES = list || [];
      sel.innerHTML = COURSES.map(function (c) { return '<option value="' + c.id + '">' + esc(c.name) + '</option>'; }).join('');
      if (!COURSES.length) { sel.innerHTML = '<option>还没有课程</option>'; return; }
      CID = fromPage || COURSES[0].id;
      sel.value = String(CID);
    }).catch(function () {
      sel.innerHTML = '<option>课程加载失败</option>';
    });
  }
  sel.addEventListener('change', function () { CID = Number(sel.value); });

  function addMsg(role, text) {
    var d = document.createElement('div');
    d.className = 'tf-ai-msg ' + role;
    d.innerHTML = role === 'user' ? esc(text).replace(/\n/g, '<br>') : esc(text).replace(/\n/g, '<br>');
    msgBox.appendChild(d);
    msgBox.scrollTop = msgBox.scrollHeight;
    if (window.renderMathInElement && role === 'assistant') {
      try { renderMathInElement(d, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false}); } catch (e) {}
    }
  }
  function loadKatex(cb) {
    if (window.renderMathInElement) return cb();
    var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = 'assets/katex/katex.inline.css';
    document.head.appendChild(l);
    var s = document.createElement('script'); s.src = 'assets/katex/katex.min.js';
    s.onload = function () {
      var a = document.createElement('script'); a.src = 'assets/katex/auto-render.min.js';
      a.onload = cb; a.onerror = cb; document.head.appendChild(a);
    };
    s.onerror = cb; document.head.appendChild(s);
  }

  function send() {
    var q = (input.value || '').trim();
    if (!q) return;
    if (!CID) { addMsg('assistant', '先建一门课，我才能结合资料回答。'); return; }
    addMsg('user', q);
    input.value = '';
    var selText = String(window.getSelection ? window.getSelection() : '').trim().slice(0, 2000);
    var loading = document.createElement('div');
    loading.className = 'tf-ai-msg assistant loading';
    loading.textContent = '检索资料页并回答…';
    msgBox.appendChild(loading); msgBox.scrollTop = msgBox.scrollHeight;
    srcBox.innerHTML = '';
    var course = (COURSES.filter(function (c) { return c.id === CID; })[0] || {}).name || '';
    fetch('/api/ask', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({course_id: CID, course: course, question: q, context: selText, mode: 'explain'})
    }).then(function (r) { return r.json(); }).then(function (d) {
      loading.remove();
      if (!d.answer) throw new Error('没有返回内容');
      loadKatex(function () { addMsg('assistant', d.answer); });
      (d.sources || []).slice(0, 4).forEach(function (s) {
        var chip = document.createElement('span'); chip.className = 'chip'; chip.textContent = 'P.' + s.page;
        srcBox.appendChild(chip);
      });
    }).catch(function (e) {
      loading.remove(); addMsg('assistant', '问答失败：' + (e.message || '请检查 Key/网络'));
    });
  }
  drawer.querySelector('.tf-ai-form').addEventListener('submit', function (e) { e.preventDefault(); send(); });
  input.addEventListener('keydown', function (e) { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') send(); });
  loadCourses();
  var _qp = new URLSearchParams(location.search);
  if(_qp.get('ai') === '1') setTimeout(open, 700);
  if(_qp.get('q')) setTimeout(function(){ input.value = _qp.get('q'); send(); }, 1500);
})();
