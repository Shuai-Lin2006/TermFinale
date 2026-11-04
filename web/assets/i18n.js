(function () {
  var DICT = {
    "今日冲刺": "Today", "我的课程": "Courses", "练习与错题": "Practice",
    "资料库": "Library", "笔记": "Notes", "设置": "Settings",
    "我的课程": "My Courses", "练习与错题": "Practice & Mistakes",
    "上传资料": "Upload", "生成工作台": "Generate", "笔记": "Notes",
    "新建课程": "New course", "新建第一门课": "Create first course",
    "资料": "Files", "生成": "Generate", "打开": "Open", "保存": "Save",
    "取消": "Cancel", "删除": "Delete", "去生成": "Go generate",
    "开始生成": "Start", "打印": "Print", "编辑": "Edit", "主题": "Theme",
    "搜索": "Search", "导出 PDF": "Export PDF", "发送": "Send",
    "存为笔记": "Save note", "复制": "Copy", "继续追问…": "Ask a follow-up…",
    "本次目标": "Target", "剩余天数": "Days left", "讲解人设": "Persona",
    "生成": "Generated", "待复习": "Due", "训练试卷": "Mock exams",
    "错题": "Mistakes", "判分练习": "Grade me", "提交判分": "Submit",
    "关闭": "Close", "全部课程": "All courses", "全部": "All",
    "我的课程": "My Courses", "还没有课程": "No courses yet",
    "资料就绪": "Files ready", "资料缺失": "Missing files",
    "进行中": "In progress", "临近考试": "Exam soon",
    "生成一套试卷": "Generate a paper", "先生成一套试卷": "Generate a paper first",
    "中": "EN"
  };
  var lang = localStorage.getItem('tf-lang') || 'zh';

  function walkText(replace) {
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (n) {
      var key = (n.nodeValue || '').trim();
      if (key && replace[key] !== undefined) {
        n.nodeValue = n.nodeValue.replace(key, replace[key]);
      }
    });
  }

  function apply() {
    if (lang !== 'en') return;
    document.documentElement.lang = 'en';
    walkText(DICT);
    document.querySelectorAll('[placeholder]').forEach(function (el) {
      var key = el.getAttribute('placeholder').trim();
      if (DICT[key]) el.setAttribute('placeholder', DICT[key]);
    });
  }

  function toggleButton() {
    var btn = document.createElement('button');
    btn.className = 'btn ghost sm';
    btn.style.cssText = 'position:fixed;left:14px;bottom:14px;z-index:9999;font-size:11px;padding:4px 8px;opacity:.75';
    btn.textContent = lang === 'en' ? '中文' : 'EN';
    btn.title = 'Switch UI language (Beta)';
    btn.addEventListener('click', function () {
      localStorage.setItem('tf-lang', lang === 'en' ? 'zh' : 'en');
      location.reload();
    });
    document.body.appendChild(btn);
  }

  window.TF_LANG = { get: function () { return lang; }, apply: apply };
  document.addEventListener('DOMContentLoaded', function () { apply(); toggleButton(); });
})();
