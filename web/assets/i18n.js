(function () {
  var DICT = {
    "今日冲刺":"Today","我的课程":"Courses","练习与错题":"Practice","资料库":"Library",
    "笔记":"Notes","设置":"Settings","上传资料":"Upload","生成工作台":"Generate",
    "新建课程":"New course","新建第一门课":"Create first course","编辑课程":"Edit course",
    "资料":"Files","生成":"Generate","打开":"Open","保存":"Save","取消":"Cancel",
    "删除":"Delete","去生成":"Go generate","开始生成":"Start","打印":"Print","编辑":"Edit",
    "主题":"Theme","搜索":"Search","导出 PDF":"Export PDF","发送":"Send","存为笔记":"Save note",
    "复制":"Copy","关闭":"Close","全部课程":"All courses","全部":"All","重试":"Retry",
    "本次目标":"Target","剩余天数":"Days left","讲解人设":"Persona","资料":"Files",
    "生成":"Generated","待复习":"Due","训练试卷":"Mock exams","错题":"Mistakes",
    "判分练习":"Grade me","提交判分":"Submit","继续追问…":"Ask a follow-up…",
    "本章速查":"Chapter notes","问 AI":"Ask AI","重新生成本章":"Regenerate chapter",
    "阅读进度":"Reading progress","章节目录":"Contents","正在加载…":"Loading…",
    "准备好了就开始":"Ready when you are","要生成什么":"What to create",
    "讲解深度":"Depth","讲义语言":"Language","讲解人设":"Persona","补充要求（选填）":"Extra instructions (optional)",
    "用哪些资料":"Materials","全选":"Select all","已有的资料":"Files","说明":"Notes",
    "拖文件到这里，或点击选择":"Drop files here, or click to choose",
    "支持多选；单个文件不超过 500MB":"Multiple files · max 500MB each",
    "已有资料":"Files","去生成 →":"Generate →","保存并退出":"Save & exit",
    "外观":"Appearance","模式":"Mode","亮色":"Light","暗色":"Dark","强调色":"Accent",
    "关于":"About","版本":"Version","构建":"Build","开发者":"Developer",
    "数据与缓存":"Data & cache","清理调试缓存":"Clear debug cache",
    "API Key":"API Key","模型":"Models","只存本机":"Local only",
    "本次目标":"Target","全部课程":"All courses",
    "还没有课程":"No courses yet","没有课程":"No courses",
    "还没有笔记":"No notes yet","还没有错题":"No mistakes yet",
    "先做套卷，再把错的题收进来，按遗忘曲线复习":"Take a paper, collect mistakes, review on a schedule",
    "生成一套试卷":"Generate a paper","先生成一套试卷":"Generate a paper first",
    "错题本":"Mistakes","训练试卷":"Mock exams","笔记":"Notes",
    "记住了":"Got it","忘了":"Forgot","删除":"Delete","待复习":"Due",
    "判分练习":"Grade me","提交判分":"Submit","题目":"Questions",
    "难度":"Difficulty","满分":"Full score","考试范围":"Scope",
    "课程名":"Course name","学校层次":"School tier","专业":"Major","学分":"Credits",
    "剩余天数":"Days left","目标分数":"Target score","基础难度":"Baseline",
    "这是专业课":"Major course","保存":"Save","取消":"Cancel",
    "临近考试":"Exam soon","进行中":"In progress","资料就绪":"Files ready","资料缺失":"Missing files",
    "已掌握":"Mastered","今天该复习":"Due today","下次":"Next","第":"Round",
    "测试连接":"Test connection","已配置":"Configured","未配置":"Not configured",
    "只存本机":"Local only","用 Key 文件":"Key file","数据目录":"Data folder","输出目录":"Output folder",
    "本地优先":"Local-first","清理调试缓存":"Clear debug cache","关于":"About",
    "版本":"Version","构建":"Build","开发者":"Developer","模式":"Mode","强调色":"Accent",
    "外观":"Appearance","模型":"Models","API Key":"API Key","讲义语言":"Language",
    "补充要求（选填）":"Extra instructions (optional)","用哪些资料":"Materials","全选":"Select all",
    "已有资料":"Files","说明":"Notes","拖文件到这里，或点击选择":"Drop files here, or click to choose",
    "支持多选；单个文件不超过 500MB":"Multiple files · max 500MB each",
    "准备好了就开始":"Ready when you are","要生成什么":"What to create","讲解深度":"Depth",
    "判分":"Grade","得分":"Score","全对":"All correct","未作答":"blank","正确答案":"Correct answer",
    "你选了":"You chose","我的课程":"Courses","练习与错题":"Practice","笔记":"Notes",
    "下午好":"Good afternoon","上午好":"Good morning","晚上好":"Good evening"
  };
  var RULES = [
    [/^共 (\d+) 门课.*$/, "$1 courses"],
    [/^(\d+) 天后考试$/, "Exam in $1 days"],
    [/^(\d+) 天后$/, "$1 days"],
    [/^(\d+) 份资料 · (\d+) 份已生成 · 目标 (\d+) 分$/, "$1 files · $2 generated · Target $3"],
    [/^(\d+) 份资料 · 目标 (\d+) 分$/, "$1 files · Target $2"],
    [/^第 (\d+) 章$/, "Chapter $1"],
    [/^目标 (\d+) 分$/, "Target $1"],
    [/^剩余 (\d+) 天$/, "$1 days left"],
    [/^共 (\d+) 条笔记$/, "$1 notes"],
    [/^共 (\d+) 题.*$/, "$1 questions"],
    [/^(\d+) 题已加入错题本$/, "$1 added to mistakes"],
    [/^(\d+) 天后考试 · /, "Exam in $1 days · "],
    [/ 份资料 · /, " files · "], [/ 份已生成 · 目标 /, " generated · Target "],
    [/ 天后考试$/, " days to exam"],
    [/^第 (\d+) 轮$/, "Round $1"],
    [/^得分：(\d+) \/ (\d+)/, "Score: $1 / $2"],
    [/^共 (\d+) 题 · 今天该复习 (\d+) 题$/, "$1 questions · $2 due today"]
  ];
  var lang = localStorage.getItem('tf-lang') || 'zh';
  var translating = false;

  function translateString(raw) {
    var key = (raw || '').trim();
    if (!key) return null;
    if (DICT[key] !== undefined) return raw.replace(key, DICT[key]);
    for (var i = 0; i < RULES.length; i++) {
      if (RULES[i][0].test(key)) return raw.replace(key, key.replace(RULES[i][0], RULES[i][1]));
    }
    if (key.indexOf('下午好，') === 0) return raw.replace(key, 'Good afternoon, ' + key.slice(4));
    if (key.indexOf('上午好，') === 0) return raw.replace(key, 'Good morning, ' + key.slice(4));
    if (key.indexOf('晚上好，') === 0) return raw.replace(key, 'Good evening, ' + key.slice(4));
    return null;
  }

  function walk(root) {
    if (lang !== 'en' || translating) return;
    translating = true;
    try {
      var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      var nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(function (n) {
        var out = translateString(n.nodeValue);
        if (out !== null) n.nodeValue = out;
      });
      (root.querySelectorAll ? root : document).querySelectorAll('[placeholder]').forEach(function (el) {
        var out = translateString(el.getAttribute('placeholder'));
        if (out !== null) el.setAttribute('placeholder', out);
      });
    } finally { translating = false; }
  }

  function apply() {
    if (lang !== 'en') return;
    document.documentElement.lang = 'en';
    walk(document.body);
  }

  function toggleButton() {
    var btn = document.createElement('button');
    btn.className = 'btn ghost sm';
    btn.style.cssText = 'position:fixed;left:14px;bottom:14px;z-index:9999;font-size:11px;padding:4px 8px;opacity:.75';
    btn.textContent = lang === 'en' ? '中文' : 'EN';
    btn.title = 'Switch UI language';
    btn.addEventListener('click', function () {
      localStorage.setItem('tf-lang', lang === 'en' ? 'zh' : 'en');
      location.reload();
    });
    document.body.appendChild(btn);
  }

  window.TF_LANG = { get: function () { return lang; }, apply: apply };
  document.addEventListener('DOMContentLoaded', function () {
    apply(); toggleButton();
    if (lang === 'en') {
      new MutationObserver(function (muts) {
        muts.forEach(function (m) {
          m.addedNodes.forEach(function (n) { if (n.nodeType === 1) walk(n); });
        });
      }).observe(document.body, { childList: true, subtree: true });
    }
  });
})();
