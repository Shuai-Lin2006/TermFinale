"""讲义阅读器工具条：搜索 / 编辑 / 导出 / AI 助教。

纯前端；AI 需要宿主页设置 window.TF_AI_ENDPOINT（v2 API 接入后）。
"""
from __future__ import annotations

READER_CSS = """
[hidden]{display:none!important}
.tf-reader-tools{position:fixed;right:20px;top:16px;z-index:60;display:flex;gap:6px;
  font-family:-apple-system,"PingFang SC",sans-serif}
.tf-reader-tools button{border:1px solid #cfd6df;background:#fff;color:#1f2328;border-radius:8px;
  padding:6px 10px;font-size:12px;cursor:pointer;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.tf-reader-tools button:hover{background:#f4f6f8}
.tf-lib-link{align-self:center;font-size:12px;color:#245c73;text-decoration:none;padding:0 4px}
.tf-search-bar{position:fixed;right:20px;top:56px;z-index:61;display:flex;gap:6px;align-items:center;
  background:#fff;border:1px solid #cfd6df;border-radius:10px;padding:8px;box-shadow:0 4px 18px rgba(0,0,0,.12);
  font-family:-apple-system,"PingFang SC",sans-serif;font-size:12px}
.tf-search-bar input{width:220px;border:1px solid #d8dde3;border-radius:6px;padding:5px 8px;font:inherit}
.tf-search-bar button{border:1px solid #d8dde3;background:#fff;border-radius:6px;padding:4px 7px;cursor:pointer}
.tf-search-count{color:#5b6470;min-width:48px;text-align:center}
mark.tf-hit{background:#ffe08a;color:inherit;padding:0 1px}
mark.tf-hit.tf-current{background:#f59e0b;color:#111}
.tf-editing{outline:2px dashed #245c73;outline-offset:6px}
.tf-practice{position:fixed;right:20px;top:56px;bottom:20px;width:400px;z-index:64;display:flex;flex-direction:column;background:#fff;border:1px solid #cfd6df;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.16);font-family:-apple-system,"PingFang SC",sans-serif}
.tf-practice-head{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid #e6e9ee;font-size:13px;font-weight:600}
.tf-practice-head button{border:0;background:transparent;font-size:18px;cursor:pointer;color:#5b6470}
.tf-practice-body{flex:1;overflow:auto;padding:14px;font-size:13px;line-height:1.8}
.tf-practice-q{background:#f6f7f9;border-radius:8px;padding:10px;margin-bottom:10px}
.tf-practice-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.tf-practice-actions button{border:1px solid #245c73;background:#fff;color:#245c73;border-radius:6px;padding:5px 9px;cursor:pointer;font-size:12px}
.tf-practice-actions button.primary{background:#245c73;color:#fff}
.tf-practice-answer{margin-top:8px;padding:8px;border-left:3px solid #245c73;background:#f8fbfc;white-space:pre-wrap}
.tf-ai-panel{position:fixed;right:20px;top:56px;bottom:20px;width:360px;z-index:62;display:flex;
  flex-direction:column;background:#fff;border:1px solid #cfd6df;border-radius:12px;
  box-shadow:0 8px 30px rgba(0,0,0,.16);font-family:-apple-system,"PingFang SC",sans-serif}
.tf-ai-head{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;
  border-bottom:1px solid #e6e9ee;font-size:13px;font-weight:600}
.tf-ai-head button{border:0;background:transparent;font-size:18px;cursor:pointer;color:#5b6470}
.tf-ai-msgs{flex:1;overflow:auto;padding:12px 14px;font-size:13px;line-height:1.7}
.tf-ai-msg{margin:0 0 10px;padding:8px 10px;border-radius:8px;white-space:pre-wrap}
.tf-ai-msg.user{background:#eef6fa;margin-left:28px}
.tf-ai-msg.assistant{background:#f6f7f9;margin-right:12px}
.tf-ai-msg.thinking{color:#7a828c}
.tf-ai-msg.thinking::after{content:"…";display:inline-block;animation:tf-dots 1.2s steps(4,end) infinite;width:1.4em}
@keyframes tf-dots{0%{opacity:.25}50%{opacity:1}100%{opacity:.25}}
.tf-new-chat{border:1px solid #d8dde3!important;background:#fff!important;color:#245c73!important;border-radius:6px!important;font-size:11px!important;padding:3px 7px!important;margin-right:4px}
.tf-src{margin-top:6px;padding-top:4px;border-top:1px dashed #d8dde3;font-size:11px;line-height:1.6}
.tf-src a{color:#245c73;margin-right:8px;white-space:nowrap}
.tf-rewrite{margin-top:6px;padding:7px;border:1px dashed #245c73;border-radius:6px;font-size:12px;background:#f8fbfc}
.tf-rewrite button{margin-top:5px;margin-right:5px;border:1px solid #245c73;background:#fff;color:#245c73;border-radius:5px;padding:3px 7px;cursor:pointer;font-size:11px}
.tf-ai-form{display:flex;gap:6px;padding:10px 12px;border-top:1px solid #e6e9ee}
.tf-ai-form textarea{flex:1;resize:vertical;min-height:54px;border:1px solid #d8dde3;border-radius:8px;
  padding:7px 9px;font:inherit;font-size:12.5px}
.tf-ai-form button{border:1px solid #245c73;background:#245c73;color:#fff;border-radius:8px;padding:6px 10px;cursor:pointer}
.tf-export-menu{position:fixed;right:20px;top:60px;z-index:80;background:#fff;border:1px solid #cfd6df;
  border-radius:10px;padding:6px;box-shadow:0 8px 24px rgba(0,0,0,.14);display:flex;flex-direction:column;
  font-family:-apple-system,"PingFang SC",sans-serif;font-size:12px}
.tf-export-menu button{border:0;background:transparent;text-align:left;padding:7px 10px;border-radius:6px;cursor:pointer}
.tf-export-menu button:hover{background:#f4f6f8}
.tf-selection-tools{position:fixed;z-index:70;display:flex;gap:4px;background:#fff;border:1px solid #cfd6df;border-radius:8px;padding:4px;box-shadow:0 6px 20px rgba(0,0,0,.16)}
.tf-selection-tools button{border:0;background:#245c73;color:#fff;border-radius:5px;padding:4px 7px;font-size:12px;cursor:pointer}
@media print{.tf-reader-tools,.tf-search-bar,.tf-ai-panel,.tf-export-menu,.tf-practice{display:none!important}}
@media (max-width:720px){.tf-reader-tools{right:10px}.tf-ai-panel{right:10px;left:10px;width:auto}}
"""

READER_HTML = """
<div class="tf-reader-tools" id="tfReaderTools">
  <button type="button" id="tfSearchBtn">搜索</button>
  <button type="button" id="tfEditBtn">编辑</button>
  <button type="button" id="tfExportBtn">导出</button>
  <button type="button" id="tfPracticeBtn">练习</button>
  <button type="button" id="tfAiBtn">AI 助教</button>
  <a class="tf-lib-link" id="tfLibLink" href="/#/library" target="_top" hidden>讲义库</a>
  <button type="button" id="tfLangBtn">EN</button>
</div>
<div class="tf-search-bar" id="tfSearchBar" hidden>
  <input id="tfSearchInput" placeholder="搜索正文，回车跳转" autocomplete="off">
  <span class="tf-search-count" id="tfSearchCount">0 处</span>
  <button type="button" id="tfSearchPrev">↑</button>
  <button type="button" id="tfSearchNext">↓</button>
  <button type="button" id="tfSearchClose">关闭</button>
</div>
<div class="tf-export-menu" id="tfExportMenu" hidden>
  <button type="button" id="tfPdfBtn">导出 PDF（真实分页）</button>
  <button type="button" id="tfPrintBtn">打印</button>
  <button type="button" id="tfWordBtn">导出 Word</button>
  <button type="button" id="tfHtmlBtn">导出 HTML</button>
</div>
<div class="tf-selection-tools" id="tfSelectionTools" hidden>
  <button type="button" id="tfSelAsk">问 AI</button>
  <button type="button" id="tfSelSimplify">简化</button>
  <button type="button" id="tfSelQuiz">出题</button>
  <button type="button" id="tfSelRewrite">改稿</button>
  <button type="button" id="tfSelNote">存笔记</button>
</div>
<aside class="tf-practice" id="tfPractice" hidden>
  <div class="tf-practice-head"><span id="tfPracticeTitle">练习 · 当前讲义</span><button type="button" id="tfPracticeClose">×</button></div>
  <div class="tf-practice-body" id="tfPracticeBody"></div>
</aside>
<aside class="tf-ai-panel" id="tfAiPanel" hidden>
  <div class="tf-ai-head"><span id="tfAiTitle">AI 助教 · 当前讲义</span><div><button type="button" class="tf-new-chat" id="tfPlan">学习计划</button><button type="button" class="tf-new-chat" id="tfRewriteSection">重写本节</button><button type="button" class="tf-new-chat" id="tfUndo" hidden>撤销改写</button><button type="button" class="tf-new-chat" id="tfNewChat">新对话</button><button type="button" id="tfAiClose">×</button></div></div>
  <div class="tf-ai-msgs" id="tfAiMsgs"><div class="tf-ai-msg assistant">可以问我这一节的任何概念、步骤或例题；我会尽量只依据这份讲义回答。若页面是静态预览，AI 需要连接本地服务。</div></div>
  <form class="tf-ai-form" id="tfAiForm">
    <textarea id="tfAiInput" rows="2" placeholder="例如：椅式和船式为什么稳定性不同？"></textarea>
    <button type="submit">发送</button>
  </form>
</aside>
"""

READER_JS = r"""
(function () {
  if (window.__TF_READER_TOOLS__) return;
  window.__TF_READER_TOOLS__ = true;
  var root = document.querySelector('.lecture');
  if (!root) return;
  var $ = function (id) { return document.getElementById(id); };
  var uiLang = localStorage.getItem('tf-ui-lang') || 'zh';
  var libLink = $('tfLibLink');
  if (libLink && location.protocol.indexOf('http') === 0) libLink.hidden = false;
  // When this HTML is embedded in the product reader, the parent already has
  // search / edit / export. Hide the duplicate inner buttons instead of
  // showing two toolbars with two search systems.
  var embedded = false;
  try { embedded = new URLSearchParams(location.search).get('embed') === '1'; } catch (e) {}
  if (embedded) {
    ['tfSearchBtn', 'tfEditBtn', 'tfExportBtn'].forEach(function (id) {
      var el = $(id); if (el) el.hidden = true;
    });
    if (libLink) libLink.hidden = true;
  }

  // ---------- 搜索 ----------
  var searchBar = $('tfSearchBar'), searchInput = $('tfSearchInput'), searchCount = $('tfSearchCount');
  var hits = [], hitIndex = -1, lastQuery = '';
  function updateCount() {
    if (!searchCount) return;
    searchCount.textContent = hits.length ? ((hitIndex + 1) + ' / ' + hits.length) : (uiLang === 'en' ? '0 hits' : (uiLang === 'hant' ? '0 處' : '0 处'));
  }
  function clearHits() {
    root.querySelectorAll('mark.tf-hit').forEach(function (m) {
      var t = document.createTextNode(m.textContent);
      m.parentNode.replaceChild(t, m);
    });
    root.normalize();
    hits = []; hitIndex = -1; updateCount();
  }
  function focusHit(step) {
    if (!hits.length) { updateCount(); return; }
    if (hitIndex >= 0) hits[hitIndex].classList.remove('tf-current');
    hitIndex = (hitIndex + step + hits.length) % hits.length;
    hits[hitIndex].classList.add('tf-current');
    hits[hitIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
    updateCount();
  }
  function doSearch(q, step) {
    if (q !== lastQuery) {
      clearHits(); lastQuery = q;
      if (!q) return;
      var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      var nodes = [], n;
      while ((n = walker.nextNode())) {
        if (!n.nodeValue || n.nodeValue.indexOf(q) < 0) continue;
        var p = n.parentElement;
        if (p && p.closest('script,style,.tf-reader-tools,.tf-search,.tf-ai-panel,.tf-export-menu')) continue;
        nodes.push(n);
      }
      nodes.forEach(function (node) {
        var parts = node.nodeValue.split(q);
        if (parts.length < 2) return;
        var frag = document.createDocumentFragment();
        parts.forEach(function (part, i) {
          frag.appendChild(document.createTextNode(part));
          if (i < parts.length - 1) {
            var m = document.createElement('mark');
            m.className = 'tf-hit'; m.textContent = q; frag.appendChild(m); hits.push(m);
          }
        });
        node.parentNode.replaceChild(frag, node);
      });
    }
    if (hits.length) focusHit(step); else updateCount();
  }
  if ($('tfSearchBtn')) $('tfSearchBtn').onclick = function () {
    searchBar.hidden = !searchBar.hidden;
    if (!searchBar.hidden) { searchInput.focus(); searchInput.select(); }
  };
  if ($('tfSearchClose')) $('tfSearchClose').onclick = function () { searchBar.hidden = true; clearHits(); lastQuery = ''; };
  if (searchInput) searchInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); doSearch(searchInput.value.trim(), e.shiftKey ? -1 : 1); }
  });
  if ($('tfSearchNext')) $('tfSearchNext').onclick = function () { doSearch(searchInput.value.trim(), 1); };
  if ($('tfSearchPrev')) $('tfSearchPrev').onclick = function () { doSearch(searchInput.value.trim(), -1); };
  // Parent reader toolbar uses this small bridge. The iframe search UI stays
  // hidden, so focus and count never get lost inside the frame.
  window.tfReaderSearch = {
    show: function () { searchBar.hidden = false; searchInput.focus(); searchInput.select(); },
    search: function (q) { q = String(q || '').trim(); searchInput.value = q; if (!q) { clearHits(); lastQuery = ''; return state(); } doSearch(q, 1); return state(); },
    next: function () { doSearch(searchInput.value.trim(), 1); return state(); },
    prev: function () { doSearch(searchInput.value.trim(), -1); return state(); },
    close: function () { searchBar.hidden = true; clearHits(); lastQuery = ''; },
    state: function () { return { count: hits.length, index: hitIndex }; }
  };

  // ---------- 编辑 ----------
  var editing = false;
  if ($('tfEditBtn')) $('tfEditBtn').onclick = function () {
    editing = !editing;
    root.contentEditable = editing ? 'true' : 'false';
    root.classList.toggle('tf-editing', editing);
    this.textContent = editing ? '退出编辑' : '编辑';
    if (!editing) window.alert('已退出编辑。改动只保存在当前页面，请用“导出 HTML”保存副本。');
  };

  // ---------- 导出 ----------
  var exportMenu = $('tfExportMenu');
  if ($('tfExportBtn')) $('tfExportBtn').onclick = function () {
    exportMenu.hidden = !exportMenu.hidden;
  };
  document.addEventListener('mousedown', function (e) {
    if (exportMenu && !exportMenu.hidden && !exportMenu.contains(e.target) && e.target.id !== 'tfExportBtn') exportMenu.hidden = true;
  });
  function download(name, content, mime) {
    var blob = new Blob(['\ufeff', content], { type: mime });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); }, 3000);
  }
  if ($('tfPdfBtn')) $('tfPdfBtn').onclick = function () {
    exportMenu.hidden = true;
    var a = document.createElement('a');
    a.href = 'lecture.pdf';
    a.download = (document.title || 'lecture') + '.pdf';
    document.body.appendChild(a); a.click(); a.remove();
  };
  if ($('tfPrintBtn')) $('tfPrintBtn').onclick = function () { exportMenu.hidden = true; window.print(); };
  async function wordHtml() {
    // Word 导出：去掉 KaTeX 的排版 span，只保留 MathML；图片转 data URL，
    // 否则导出的 .doc 换目录后图片全丢、公式变成一堆内联样式。
    var clone = root.cloneNode(true);
    clone.querySelectorAll('.katex-html').forEach(function (el) { el.remove(); });
    var imgs = Array.prototype.slice.call(clone.querySelectorAll('img'));
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i], src = img.getAttribute('src');
      if (!src || src.indexOf('data:') === 0) continue;
      try {
        var resp = await fetch(src);
        if (!resp.ok) continue;
        var blob = await resp.blob();
        var data = await new Promise(function (resolve, reject) {
          var fr = new FileReader();
          fr.onload = function () { resolve(fr.result); };
          fr.onerror = reject;
          fr.readAsDataURL(blob);
        });
        img.setAttribute('src', data);
      } catch (e) {}
    }
    return '<html><head><meta charset="utf-8"><style>'
      + 'body{font-family:"Songti SC",serif;line-height:1.9;font-size:14px;color:#111}'
      + 'h1{font-size:26px}h2{font-size:22px}h3{font-size:17px}p{text-indent:2em}.kicker,.course,.subtitle,.meta{text-indent:0}'
      + 'figure{text-align:center}figcaption{font-size:12px;color:#666}'
      + 'table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px}'
      + 'math{font-family:"Cambria Math",serif}'
      + '</style></head><body>' + clone.innerHTML + '</body></html>';
  }
  if ($('tfWordBtn')) $('tfWordBtn').onclick = async function () {
    exportMenu.hidden = true;
    try {
      var html = await wordHtml();
      download((document.title || '讲义') + '.doc', html, 'application/msword');
    } catch (e) {
      window.alert('导出 Word 失败：' + e);
    }
  };
  if ($('tfHtmlBtn')) $('tfHtmlBtn').onclick = function () {
    exportMenu.hidden = true;
    var styles = Array.prototype.map.call(document.querySelectorAll('style'), function (x) { return x.textContent || ''; }).join('\n');
    var paper = root.cloneNode(true);
    var bar = '<div class="tf-export-back"><a href="#" onclick="if(history.length>1){history.back();return false;}">← 返回 TermFinale</a></div>';
    var extra = ".tf-reader-tools,.tf-search-bar,.tf-ai-panel,.tf-export-menu,.tf-practice,.tf-selection-tools,.tf-export-back{display:none!important}"
      + "body{background:#f3f4f6;margin:0}.lecture{max-width:1080px;margin:0 auto;background:#fff;padding:56px 64px}"
      + ".tf-export-back{display:block!important;position:fixed;left:18px;top:14px;z-index:99999}"
      + ".tf-export-back a{display:inline-block;padding:7px 11px;border:1px solid #cfd6df;border-radius:4px;background:#fff;color:#245c73;text-decoration:none;font:12px -apple-system,sans-serif}";
    download((document.title || '讲义') + '.html',
      '<!doctype html><html><head><meta charset="utf-8"><title>' + (document.title || '讲义') + '</title><style>' + styles + extra + '</style></head><body>' + bar + paper.outerHTML + '</body></html>',
      'text/html');
  };

  // ---------- AI ----------
  var aiPanel = $('tfAiPanel'), aiMsgs = $('tfAiMsgs'), aiInput = $('tfAiInput');
  var artifactId = (location.pathname.match(/\/(?:docs\/evidence|artifact)\/([^/]+)\//) || [])[1] || '';
  var historyKey = 'tf-chat-' + (artifactId || 'static');
  var history = [];
  try { history = JSON.parse(localStorage.getItem(historyKey) || '[]') || []; } catch (e) { history = []; }
  var sessionId = localStorage.getItem('tf-session-' + (artifactId || 'static')) || 'default';
  var undoStack = [];
  var lastSelectionRange = null;
  var lastRewriteSection = null;
  if ($('tfAiBtn')) $('tfAiBtn').onclick = function () {
    aiPanel.hidden = false; exportMenu.hidden = true; aiInput.focus(); if (practicePanel) practicePanel.hidden = true;
  };
  if ($('tfAiClose')) $('tfAiClose').onclick = function () { aiPanel.hidden = true; };
  function fmt(text) {
    var s = String(text == null ? '' : text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    s = s.replace(/^###\s+(.+)$/gm, '<b>$1</b>')
      .replace(/^##\s+(.+)$/gm, '<b>$1</b>')
      .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
      .replace(/^\s*[-*]\s+/gm, '• ');
    // 公式内部的换行不能变成 <br>，否则 KaTeX 会整段放弃渲染。
    s = s.replace(/\$\$([\s\S]*?)\$\$/g, function (_, body) { return '$$' + body.replace(/\n/g, ' ') + '$$'; });
    s = s.replace(/\$([^$\n]+)\$/g, function (_, body) { return '$' + body.replace(/\n/g, ' ') + '$'; });
    return s.replace(/\n/g, '<br>');
  }
  function addMsg(role, text, sources) {
    var d = document.createElement('div');
    d.className = 'tf-ai-msg ' + role;
    d.innerHTML = fmt(text);
    if (sources && sources.length) {
      var sd = document.createElement('div'); sd.className = 'tf-src'; sd.appendChild(document.createTextNode('来源：'));
      sources.forEach(function (s, i) {
        if (i) sd.appendChild(document.createTextNode(' · '));
        var a = document.createElement('a');
        a.textContent = s.section + (s.pages && s.pages.length ? '（第' + s.pages.join(',') + '页）' : '');
        a.href = '#' + s.anchor;
        a.onclick = function (e) { e.preventDefault(); var el = document.getElementById(s.anchor); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
        sd.appendChild(a);
      });
      d.appendChild(sd);
    }
    aiMsgs.appendChild(d); aiMsgs.scrollTop = aiMsgs.scrollHeight;
    if (role === 'assistant' && window.renderMathInElement) {
      try {
        renderMathInElement(d, { delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\[', right: '\\]', display: true },
          { left: '\\(', right: '\\)', display: false }
        ], throwOnError: false });
      } catch (e) {}
    }
    return d;
  }
  function saveHistory() {
    try { localStorage.setItem(historyKey, JSON.stringify(history.slice(-200))); } catch (e) {}
  }
  function ask(q, selected, opts) {
    opts = opts || {};
    addMsg('user', q);
    var endpoint = window.TF_AI_ENDPOINT || (location.protocol.indexOf('http') === 0 ? '/api/ask' : '');
    if (!endpoint) {
      addMsg('assistant', '当前是静态讲义预览，AI 助教需要连接 TermFinale 本地服务。接入后这里会基于当前讲义回答并标出处。');
      return;
    }
    var prior = history.slice(-200);
    history.push({ role: 'user', content: q });
    var holder = addMsg('assistant', '正在思考…');
    holder.classList.add('thinking');
    var finished = false, started = false, answer = '', sources = [];
    function finish(text, srcs) {
      if (finished) return;
      finished = true;
      if (holder.parentNode) holder.remove();
      alertDone(text || '模型没有返回内容', srcs || sources);
    }
    function fail(e) {
      if (finished) return;
      finished = true;
      holder.classList.remove('thinking');
      holder.textContent = '问答失败：' + (e && e.message ? e.message : '请检查本地服务');
    }
    function alertDone(text, srcs) {
      // 情绪安慰/闲聊不挂检索来源；只有回答实际引用讲义时才显示来源。
      var cite = /第\s*\d+\s*页|《|讲义|资料/.test(text || '');
      addMsg('assistant', text, (opts.mode || 'chat') === 'chat' && !cite ? [] : (srcs || []));
      history.push({ role: 'assistant', content: text });
      saveHistory();
      if (opts.rewriteSection) showSectionRewrite(text, lastRewriteSection);
      else if (opts.rewrite) showRewrite(text, selected);
    }
    var payload = JSON.stringify({
      question: q, artifact_id: artifactId, session_id: sessionId, lang: uiLang, selection: selected || '',
      history: prior, context: root.innerText.slice(0, 6000), mode: opts.mode || 'chat'
    });
    function processBlock(block) {
      var line = '';
      block.split('\n').forEach(function (x) { if (x.indexOf('data:') === 0) line = x.slice(5).trim(); });
      if (!line) return;
      var evt = JSON.parse(line);
      if (evt.type === 'sources') sources = evt.sources || [];
      else if (evt.type === 'delta') {
        started = true;
        answer += evt.text || '';
        holder.classList.remove('thinking');
        holder.textContent = answer;
        aiMsgs.scrollTop = aiMsgs.scrollHeight;
      } else if (evt.type === 'done') {
        if (evt.answer) answer = evt.answer;
      } else if (evt.type === 'error') {
        throw new Error(evt.error || '模型调用失败');
      }
    }
    function readStream(resp) {
      var reader = resp.body.getReader(), decoder = new TextDecoder(), buffer = '';
      function pump() {
        return reader.read().then(function (res) {
          if (res.done) {
            if (buffer.trim()) processBlock(buffer);
            return;
          }
          buffer += decoder.decode(res.value, { stream: true });
          var cut;
          while ((cut = buffer.indexOf('\n\n')) >= 0) {
            var block = buffer.slice(0, cut); buffer = buffer.slice(cut + 2);
            processBlock(block);
          }
          return pump();
        });
      }
      return pump();
    }
    var streamUrl = endpoint.replace(/\/$/, '') + '/stream';
    fetch(streamUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload })
      .then(function (r) {
        if (!r.ok || !r.body || (r.headers.get('content-type') || '').indexOf('text/event-stream') < 0) {
          throw new Error('stream unavailable');
        }
        return readStream(r);
      }).then(function () {
        finish(answer, sources);
      }).catch(function (e) {
        if (started) { fail(e); return; }
        // 老服务没有流式接口时退回普通请求，不丢消息。
        fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (!d || !d.answer) throw new Error('没有返回内容');
            finish(d.answer, d.sources || []);
          }).catch(fail);
      });
  }
  if ($('tfNewChat')) $('tfNewChat').onclick = function () {
    history = []; saveHistory(); aiMsgs.innerHTML = '';
    if (artifactId && location.protocol.indexOf('http') === 0) {
      fetch('/api/chat/' + encodeURIComponent(artifactId) + '?session_id=' + encodeURIComponent(sessionId), { method: 'DELETE' }).catch(function () {});
    }
    addMsg('assistant', '新对话开始。你可以继续问这一节的任何内容。');
  };
  if (artifactId && location.protocol.indexOf('http') === 0) {
    fetch('/api/chat/' + encodeURIComponent(artifactId) + '?session_id=' + encodeURIComponent(sessionId))
      .then(function (r) { return r.json(); }).then(function (d) {
        var msgs = (d && d.messages) || [];
        if (!msgs.length) return;
        history = msgs.map(function (m) { return { role: m.role, content: m.content }; });
        aiMsgs.innerHTML = '';
        history.slice(-20).forEach(function (m) { addMsg(m.role, m.content); });
        saveHistory();
      }).catch(function () {});
  } else if (history.length) {
    aiMsgs.innerHTML = '';
    history.slice(-20).forEach(function (m) { addMsg(m.role, m.content); });
  }
  if (new URLSearchParams(location.search).get('ai') === '1') aiPanel.hidden = false;


  // ---------- 练习模式 ----------
  var practicePanel = $('tfPractice'), practiceBody = $('tfPracticeBody');
  var practiceState = { questions: [], idx: 0, score: 0, wrong: [] };
  var studyKey = 'tf-study-' + (artifactId || 'static');
  function loadStudy() {
    try { var x = JSON.parse(localStorage.getItem(studyKey) || '{}'); return { items: x.items || {}, stats: x.stats || {} }; }
    catch (e) { return { items: {}, stats: {} }; }
  }
  function saveStudy(x) { try { localStorage.setItem(studyKey, JSON.stringify(x)); } catch (e) {} }
  function keyOf(q) { return String(q.question || '').slice(0, 80); }
  function gradeItem(q, ok) {
    var st = loadStudy(), key = keyOf(q);
    var it = st.items[key] || { question: q.question, answer: q.answer, explanation: q.explanation, page: q.page,
      section: currentSection(), interval: 1, streak: 0, due: 0, last: '' };
    it.section = it.section || currentSection() || '未分节';
    if (ok) {
      it.streak = (it.streak || 0) + 1;
      it.interval = it.streak === 1 ? 3 : Math.min(30, (it.interval || 1) * 2);
      it.due = Date.now() + it.interval * 86400000; it.last = 'right';
    } else {
      it.streak = 0; it.interval = 1; it.due = Date.now() + 86400000; it.last = 'wrong';
    }
    st.items[key] = it;
    var sec = it.section || '未分节';
    st.stats[sec] = st.stats[sec] || { right: 0, wrong: 0 };
    st.stats[sec][ok ? 'right' : 'wrong']++;
    saveStudy(st);
  }
  function dueItems() {
    var st = loadStudy(), now = Date.now(), out = [];
    Object.keys(st.items).forEach(function (k) { var it = st.items[k]; if ((it.due || 0) <= now) out.push(it); });
    return out;
  }
  function wrongItems() {
    var st = loadStudy(), out = [];
    Object.keys(st.items).forEach(function (k) { var it = st.items[k]; if (it.last === 'wrong' || (it.streak || 0) === 0) out.push(it); });
    return out;
  }
  function masteryHtml() {
    var st = loadStudy(), rows = [];
    Object.keys(st.stats).forEach(function (sec) {
      var x = st.stats[sec], total = x.right + x.wrong;
      if (total) rows.push({ sec: sec, pct: Math.round(x.right * 100 / total), total: total });
    });
    rows.sort(function (a, b) { return b.total - a.total; });
    if (!rows.length) return '<div style="color:#8a929c">还没有练习记录。</div>';
    return rows.slice(0, 4).map(function (r) {
      return '<div>· ' + fmt(r.sec) + '：' + r.pct + '%（' + r.total + ' 题）</div>';
    }).join('');
  }
  function currentSection() {
    var cur = '';
    document.querySelectorAll('section.chapter').forEach(function (sec) {
      if (sec.getBoundingClientRect().top <= 140) {
        var h = sec.querySelector('h2,h3'); cur = h ? h.textContent.trim() : (sec.id || '');
      }
    });
    if (!cur) {
      var first = document.querySelector('section.chapter h2,section.chapter h3');
      if (first) cur = first.textContent.trim();
    }
    return cur;
  }
  function closePractice() { if (practicePanel) practicePanel.hidden = true; }
  function openPractice() {
    if (!practicePanel) return;
    aiPanel.hidden = true; practicePanel.hidden = false;
    var due = dueItems().length, wrong = wrongItems().length;
    practiceBody.innerHTML = '<div class="tf-practice-q"><b>练习 · 当前讲义</b><br>到期复习：' + due + ' 题 ｜ 错题本：' + wrong + ' 题</div>' +
      '<div style="margin:8px 0"><b>掌握度</b></div>' + masteryHtml();
    var actions = document.createElement('div'); actions.className = 'tf-practice-actions';
    var fresh = document.createElement('button'); fresh.textContent = '生成 3 道新题'; fresh.className = 'primary'; fresh.onclick = startNewPractice;
    var review = document.createElement('button'); review.textContent = '今日复习（' + due + '）'; review.disabled = due === 0; review.onclick = startReview;
    var wrongBtn = document.createElement('button'); wrongBtn.textContent = '练错题（' + wrong + '）'; wrongBtn.disabled = wrong === 0; wrongBtn.onclick = startWrongPractice;
    actions.appendChild(fresh); actions.appendChild(review); actions.appendChild(wrongBtn);
    practiceBody.appendChild(actions);
  }
  function startNewPractice() {
    practiceBody.innerHTML = '正在出题…';
    var endpoint = window.TF_AI_ENDPOINT || (location.protocol.indexOf('http') === 0 ? '/api/practice' : '');
    if (!endpoint) { practiceBody.textContent = '静态预览没有练习服务，请通过本地讲义库打开。'; return; }
    fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ artifact_id: artifactId, section: currentSection(), count: 3 })
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d || !d.questions || !d.questions.length) throw new Error('没有题目');
      practiceState = { questions: d.questions, idx: 0, score: 0, wrong: [] };
      renderPractice();
    }).catch(function (e) { practiceBody.textContent = '出题失败：' + (e.message || '请检查本地服务'); });
  }
  function startReview() {
    var list = dueItems();
    if (!list.length) { practiceBody.textContent = '今天没有到期复习。'; return; }
    practiceState = { questions: list.slice(0, 10), idx: 0, score: 0, wrong: [] }; renderPractice();
  }
  function startWrongPractice() {
    var list = wrongItems();
    if (!list.length) { practiceBody.textContent = '错题本是空的。'; return; }
    practiceState = { questions: list.slice(0, 10), idx: 0, score: 0, wrong: [] }; renderPractice();
  }
  function renderPractice() {
    var st = practiceState;
    if (st.idx >= st.questions.length) {
      var due = dueItems().length, wrongCount = wrongItems().length;
      practiceBody.innerHTML = '<div class="tf-practice-q"><b>本轮完成</b><br>得分：' + st.score + ' / ' + st.questions.length + '<br>到期复习：' + due + ' ｜ 错题本：' + wrongCount + '</div>';
      var actions = document.createElement('div'); actions.className = 'tf-practice-actions';
      var again = document.createElement('button'); again.textContent = '再练一次'; again.className = 'primary'; again.onclick = openPractice;
      actions.appendChild(again);
      if (due) { var r = document.createElement('button'); r.textContent = '继续复习'; r.onclick = startReview; actions.appendChild(r); }
      practiceBody.appendChild(actions);
      return;
    }
    var q = st.questions[st.idx];
    practiceBody.innerHTML = '<div class="tf-practice-q"><div><b>第 ' + (st.idx + 1) + ' / ' + st.questions.length + ' 题</b></div><div>' + fmt(q.question || '') + '</div></div>';
    var actions = document.createElement('div'); actions.className = 'tf-practice-actions';
    var show = document.createElement('button'); show.textContent = '显示答案'; show.className = 'primary';
    var right = document.createElement('button'); right.textContent = '答对了'; right.hidden = true;
    var wrong = document.createElement('button'); wrong.textContent = '答错了'; wrong.hidden = true;
    var ans = document.createElement('div'); ans.className = 'tf-practice-answer'; ans.hidden = true;
    ans.innerHTML = '<b>答案：</b>' + fmt(q.answer || '') + '<br><b>解析：</b>' + fmt(q.explanation || '') + (q.page ? '<br><span style="color:#8a929c">出处：第' + q.page + '页</span>' : '');
    show.onclick = function () { ans.hidden = false; right.hidden = false; wrong.hidden = false; show.hidden = true; if (window.renderMathInElement) try { renderMathInElement(ans, {delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]}); } catch (e) {} };
    right.onclick = function () { gradeItem(q, true); st.score++; st.idx++; renderPractice(); };
    wrong.onclick = function () { gradeItem(q, false); st.wrong.push(q); st.idx++; renderPractice(); };
    actions.appendChild(show); actions.appendChild(right); actions.appendChild(wrong); actions.appendChild(ans);
    practiceBody.appendChild(actions);
  }
  if ($('tfPracticeBtn')) $('tfPracticeBtn').onclick = openPractice;
  if ($('tfPracticeClose')) $('tfPracticeClose').onclick = closePractice;

  // ---------- 选中文本 -> 问 AI / 简化 ----------
  var selTools = $('tfSelectionTools'), selText = '';
  function hideSel() { if (selTools) selTools.hidden = true; }
  function captureSelection(e) {
    setTimeout(function () {
      var sel = window.getSelection();
      var txt = sel ? String(sel).trim() : '';
      if (!txt || !root.contains(sel.anchorNode)) { hideSel(); return; }
      var range = sel.getRangeAt(0);
      var rect = range.getBoundingClientRect();
      selText = txt.slice(0, 1200);
      lastSelectionRange = range.cloneRange();
      selTools.hidden = false;
      selTools.style.left = Math.min(window.innerWidth - 170, Math.max(8, rect.left)) + 'px';
      selTools.style.top = Math.min(window.innerHeight - 52, Math.max(8, rect.top - 38)) + 'px';
    }, 10);
  }
  document.addEventListener('mouseup', captureSelection);
  document.addEventListener('mousedown', function (e) { if (selTools && !selTools.contains(e.target)) hideSel(); });
  if ($('tfSelAsk')) $('tfSelAsk').onclick = function () {
    hideSel(); aiPanel.hidden = false; ask('请解释这段内容：' + selText, selText);
  };
  if ($('tfSelSimplify')) $('tfSelSimplify').onclick = function () {
    hideSel(); aiPanel.hidden = false; ask('请把这段讲得更简单，保留关键步骤：' + selText, selText, { mode: 'simplify' });
  };
  if ($('tfSelQuiz')) $('tfSelQuiz').onclick = function () {
    hideSel(); aiPanel.hidden = false; ask('请基于这段内容出一道小题，先题干，再答案：' + selText, selText, { mode: 'quiz' });
  };
  if ($('tfSelNote')) $('tfSelNote').onclick = function () {
    hideSel();
    var section = '';
    try {
      var node = lastSelectionRange ? lastSelectionRange.startContainer : null;
      var el = node && (node.nodeType === 1 ? node : node.parentElement);
      var h = el ? el.closest('h2,h3') : null;
      if (h) section = h.textContent.trim();
    } catch (e) {}
    fetch('/api/notes', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({artifact_id: artifactId, text: selText, section: section})})
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function () { alert('已存为笔记。可在学习台「笔记」页查看。'); })
      .catch(function (e) { alert('存笔记失败：' + e.message); });
  };
  if ($('tfSelRewrite')) $('tfSelRewrite').onclick = function () {
    hideSel(); aiPanel.hidden = false; ask('请改写这段，使基础较弱的学生更容易懂；只输出改写后的段落：' + selText, selText, { mode: 'rewrite', rewrite: true });
  };
  function showSectionRewrite(text, section) {
    if (!section) return;
    var box = document.createElement('div'); box.className = 'tf-rewrite';
    box.appendChild(document.createTextNode('本节改写预览：'));
    var pre = document.createElement('div'); pre.style.marginTop='4px'; pre.textContent = text; box.appendChild(pre);
    var apply = document.createElement('button'); apply.textContent = '替换本节';
    var cancel = document.createElement('button'); cancel.textContent = '取消';
    apply.onclick = function () {
      undoStack.push(root.innerHTML);
      var heading = section.querySelector('h2,h3');
      var h = heading ? heading.outerHTML : '';
      var paras = String(text).split(/\n{2,}/).map(function (x) { return x.trim(); }).filter(Boolean)
        .map(function (x) { var p = document.createElement('p'); p.textContent = x; return p.outerHTML; }).join('');
      section.innerHTML = h + paras;
      box.remove(); if ($('tfUndo')) $('tfUndo').hidden = false;
    };
    cancel.onclick = function () { box.remove(); };
    box.appendChild(apply); box.appendChild(cancel);
    aiMsgs.appendChild(box); aiMsgs.scrollTop = aiMsgs.scrollHeight;
  }
  function currentSectionEl() {
    var cur = null;
    document.querySelectorAll('section.chapter').forEach(function (sec) {
      if (sec.getBoundingClientRect().top <= 140) cur = sec;
    });
    return cur || document.querySelector('section.chapter');
  }
  function showRewrite(text, original) {
    if (!lastSelectionRange) return;
    var box = document.createElement('div'); box.className = 'tf-rewrite';
    box.appendChild(document.createTextNode('改写预览：'));
    var pre = document.createElement('div'); pre.style.marginTop='4px'; pre.textContent = text; box.appendChild(pre);
    var apply = document.createElement('button'); apply.textContent = '替换选中';
    var cancel = document.createElement('button'); cancel.textContent = '取消';
    apply.onclick = function () {
      if (!lastSelectionRange) return;
      undoStack.push(root.innerHTML);
      var r = lastSelectionRange;
      r.deleteContents(); r.insertNode(document.createTextNode(text));
      box.remove(); if ($('tfUndo')) $('tfUndo').hidden = false;
    };
    cancel.onclick = function () { box.remove(); };
    box.appendChild(apply); box.appendChild(cancel);
    aiMsgs.appendChild(box); aiMsgs.scrollTop = aiMsgs.scrollHeight;
  }
  if ($('tfRewriteSection')) $('tfRewriteSection').onclick = function () {
    var sec = currentSectionEl();
    if (!sec) return;
    lastRewriteSection = sec;
    aiPanel.hidden = false;
    var body = sec.innerText.slice(0, 5000);
    ask('请重写这一节，保留全部知识点、公式与因果关系，只输出正文段落，不要标题/解释：\n' + body, body, { mode: 'rewrite', rewriteSection: true });
  };
  if ($('tfPlan')) $('tfPlan').onclick = function () {
    aiPanel.hidden = false; ask('请基于当前讲义给我一份 7 天复习计划，按天列出重点和练习。', '', { mode: 'plan' });
  };
  if ($('tfUndo')) $('tfUndo').onclick = function () {
    if (!undoStack.length) return;
    root.innerHTML = undoStack.pop(); this.hidden = true;
  };

  if ($('tfAiForm')) $('tfAiForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var q = (aiInput.value || '').trim(); if (!q) return;
    aiInput.value = ''; ask(q);
  });

  // ---------- 界面语言（只切 UI，不翻译正文） ----------
  var UI = {
    zh: { search:'搜索', edit:'编辑', export:'导出', practice:'练习', ai:'AI 助教', lib:'讲义库',
      searchPh:'搜索正文，回车跳转', close:'关闭', pdf:'导出 PDF（真实分页）', print:'打印',
      word:'导出 Word', html:'导出 HTML', aiTitle:'AI 助教 · 当前讲义', practiceTitle:'练习 · 当前讲义',
      newChat:'新对话', plan:'学习计划', rewriteSection:'重写本节', undo:'撤销改写', ask:'问 AI', simplify:'简化', quiz:'出题', rewrite:'改稿', note:'存笔记',
      send:'发送', aiPh:'例如：椅式和船式为什么稳定性不同？' },
    hant: { search:'搜尋', edit:'編輯', export:'匯出', practice:'練習', ai:'AI 助教', lib:'講義庫',
      searchPh:'搜尋正文，回車跳轉', close:'關閉', pdf:'匯出 PDF（真實分頁）', print:'列印',
      word:'匯出 Word', html:'匯出 HTML', aiTitle:'AI 助教 · 當前講義', practiceTitle:'練習 · 當前講義',
      newChat:'新對話', plan:'學習計劃', rewriteSection:'重寫本節', undo:'撤銷改寫', ask:'問 AI', simplify:'簡化', quiz:'出題', rewrite:'改稿', note:'存筆記',
      send:'傳送', aiPh:'例如：椅式和船式為什麼穩定性不同？' },
    en: { search:'Search', edit:'Edit', export:'Export', practice:'Practice', ai:'AI Tutor', lib:'Library',
      searchPh:'Search text, Enter to jump', close:'Close', pdf:'Export PDF (paged)', print:'Print',
      word:'Export Word', html:'Export HTML', aiTitle:'AI Tutor · Current lecture', practiceTitle:'Practice · Current lecture',
      newChat:'New chat', plan:'Study plan', rewriteSection:'Rewrite section', undo:'Undo rewrite', ask:'Ask AI', simplify:'Simplify', quiz:'Quiz', rewrite:'Rewrite', note:'Save note',
      send:'Send', aiPh:'e.g. Why is the chair more stable than the boat?' }
  };
  function setText(id, text) { var el = $(id); if (el) el.textContent = text; }
  function applyLang(lang) {
    uiLang = lang === 'en' ? 'en' : (lang === 'hant' ? 'hant' : 'zh');
    var t = UI[uiLang];
    setText('tfSearchBtn', t.search); setText('tfEditBtn', t.edit); setText('tfExportBtn', t.export);
    setText('tfPracticeBtn', t.practice); setText('tfAiBtn', t.ai); setText('tfLibLink', t.lib);
    setText('tfPdfBtn', t.pdf); setText('tfPrintBtn', t.print); setText('tfWordBtn', t.word); setText('tfHtmlBtn', t.html);
    setText('tfAiTitle', t.aiTitle); setText('tfPracticeTitle', t.practiceTitle);
    setText('tfNewChat', t.newChat); setText('tfPlan', t.plan); setText('tfRewriteSection', t.rewriteSection); setText('tfUndo', t.undo);
    setText('tfSelAsk', t.ask); setText('tfSelSimplify', t.simplify); setText('tfSelQuiz', t.quiz); setText('tfSelRewrite', t.rewrite); setText('tfSelNote', t.note);
    setText('tfSearchClose', t.close);
    var send = document.querySelector('#tfAiForm button[type=submit]'); if (send) send.textContent = t.send;
    if ($('tfSearchInput')) $('tfSearchInput').placeholder = t.searchPh;
    if ($('tfAiInput')) $('tfAiInput').placeholder = t.aiPh;
    setText('tfLangBtn', uiLang === 'zh' ? '繁' : (uiLang === 'hant' ? 'EN' : '简'));
    document.documentElement.lang = uiLang === 'en' ? 'en' : (uiLang === 'hant' ? 'zh-Hant' : 'zh-CN');
    try { localStorage.setItem('tf-ui-lang', uiLang); } catch (e) {}
  }
  if ($('tfLangBtn')) $('tfLangBtn').onclick = function () { var order = ['zh','hant','en']; applyLang(order[(order.indexOf(uiLang) + 1) % 3]); };
  applyLang(uiLang);
  // 从 AI 来源链接精确定位到页：?page=36
  try {
    var qp = new URLSearchParams(location.search).get('page');
    if (qp) {
      var el = Array.prototype.find.call(document.querySelectorAll('[data-pages]'), function (n) {
        return (n.getAttribute('data-pages') || '').split(',').indexOf(String(qp)) >= 0;
      });
      if (el) setTimeout(function () { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 80);
    }
  } catch (e) {}

})();
"""


def reader_tools_html() -> str:
    return READER_HTML
