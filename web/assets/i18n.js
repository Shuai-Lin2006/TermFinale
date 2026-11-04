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
    "期末冲刺工作台":"Final-exam workspace","本周学习":"This week","小时":"hours",
    "比上周多 1.2 小时":"1.2h more than last week","新建冲刺":"New sprint",
    "连续学习 4 天":"4-day streak","进行中的课":"In progress","最近生成":"Recently generated",
    "这次考试，分都在哪":"Where the marks are","按你上传的 3 份资料统计":"Based on your materials",
    "今天做什么":"Today","按考试紧迫度排序":"By exam urgency",
    "今天做什么":"What to do today","本周学习":"This week",
    "AI 答疑":"AI Q&A","Key 文件":"Key file","Key":"Key",
    "PDF / 扫描件 / PPTX / Word / 教材照片 / 音频，都可以直接丢进来":"PDF / scans / PPTX / Word / textbook photos / audio",
    "上传第一份课件，5 分钟后就能开始冲刺。":"Upload your first file and start in 5 minutes.",
    "先为这门课生成一份讲义，再回来阅读。":"Generate a guide for this course first.",
    "还没有可读的内容":"Nothing to read yet","只重写当前这一章，其他章节不动。":"Only this chapter is rewritten.",
    "选中正文任意一段 → 解释 / 举例 / 出题；回答会保留在这里。":"Select any passage → explain / example / quiz. Answers stay here.",
    "回答仅供参考":"For reference only","加入错题":"Add to mistakes","出题考我":"Quiz me",
    "举个例子":"Give an example","解释一下":"Explain","继续追问…":"Ask a follow-up…",
    "选中一段正文，我会结合上下文解释。":"Select a passage and I will explain it in context.",
    "你可以先选中一句话，或者直接在右侧输入问题。":"Select a sentence, or ask on the right.",
    "你会选择哪种讲解？":"Which style?",
    "全量 · 讲透原理":"Full · explain principles","精简 · 只讲拿分":"Compact · score-focused",
    "讲义":"Guide","考点提取":"Key points","训练试卷":"Mock paper","逻辑分析":"Logic analysis",
    "讲解深度":"Depth","出题方式":"Question style","套数":"Sets","难度":"Difficulty",
    "包含答案与解析":"Include answers","原题":"Original","原题改数":"Numbers changed",
    "原题变式":"Variants","模拟练习":"Mock","预测仿真":"Prediction",
    "考点":"Key points","名词":"Terms","提取类型":"Extract type",
    "文本生成":"Text","图片理解":"Vision","扫描 OCR":"Scan OCR","音频转写":"Audio ASR","并发":"Concurrency",
    "可在 .env 覆盖":"Override in .env","旧文件，需重新生成":"Old file, regenerate",
    "可在阅读器打开":"Open in reader","可判分":"Gradable","可阅读":"Readable","需重生成":"Regenerate",
    "已连接":"Connected","已生成":"Generated","已完成":"Done","失败":"Failed",
    "材料就绪":"Materials ready","资料越多，讲义越全；只有一份也能生成，缺的部分会标【延伸】。":"More materials, fuller guide. Missing parts are marked [Extended].",
    "会作为偏好发给模型；与资料冲突时仍以资料为准。":"Sent as preference; source material wins on conflicts.",
    "生成过程会实时显示阶段和进度；中途可以取消，已完成的章节不会浪费。":"Live progress; cancel anytime. Finished chapters are kept.",
    "预计耗时 2~6 分钟，取决于资料页数和配图数量。":"About 2–6 min depending on pages and figures.",
    "准备好了就开始":"Ready when you are","开始":"Start","打开结果":"Open result","再生成一份":"Generate again",
    "取消任务":"Cancel task","正在加载…":"Loading…","加载中…":"Loading…",
    "去练习":"Practice","去阅读":"Read","复习":"Review","首页":"Home","阅读":"Read",
    "阅读进度":"Reading progress","本章速查":"Chapter notes","重新生成本章":"Regenerate chapter",
    "问 AI":"Ask AI","TermFinale · 开发者 Lan":"TermFinale · Lan",
    "本地优先：资料只在本机解析，Key 只保存在本机 .env。":"Local-first: files never leave this machine; keys stay in local .env.",
    "清理调试缓存":"Clear debug cache","数据与缓存":"Data & cache","生成文件":"Outputs",
    "解析图片":"Figures","调试产物":"Debug","日志":"Logs","模型":"Models","外观":"Appearance",
    "关于":"About","版本":"Version","构建":"Build","开发者":"Developer",
    "已配置 · 尾号":"Configured · ends","只存本机":"Local only","测试连接":"Test",
    "阿里云百炼":"DashScope","适配":"Adapt",
    "继续阅读":"Continue reading","问一下":"Ask AI","预计提分":"Projected",
    "生成中…":"Generating…","重写中":"Rewriting","课程":"Course","大二 · 环境工程":"Sophomore · Env. Engineering",
    "思考中…":"Thinking…","完成":"Done","讲义生成好了":"Guide ready","提取完成":"Extraction done",
    "试卷生成好了":"Paper ready","分析完成":"Analysis done","准备中…":"Preparing…",
    "下午好":"Good afternoon","上午好":"Good morning","晚上好":"Good evening"
  };
  var RULES = [
    [/^共 (\d+) 门课$/, "$1 courses"],
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
    [/^共 (\d+) 题 · 今天该复习 (\d+) 题$/, "$1 questions · $2 due today"],
    [/^共 (\d+) 门课[·，,]\s*最近考试在 (\d+) 天后$/, "$1 courses · next exam in $2 days"],
    [/^已配置 · 尾号 (\w+)$/, "Configured · ends $1"],
    [/^距 (.+?) 考试 · (\d+) 天$/, "$1 exam in $2 days"],
    [/^还有 (\d+) 天，目标 (\d+) 分$/, "$1 days left · Target $2"],
    [/^还有 (\d+) 天，Target (\d+)$/, "$1 days left · Target $2"],
    [/^已有 (\d+) 份资料、(\d+) 份生成材料。先把重点章节过一遍，再做题。$/, "$1 files · $2 generated. Skim key chapters, then practice."]
  ];
  var PRE = [
    [/ 份资料/g, " files"], [/ 份已生成/g, " generated"], [/目标 (\d+) 分/g, "Target $1"],
    [/ 天后考试/g, " days to exam"], [/ 个考点/g, " key points"], [/ 页讲义/g, " pages"],
    [/ 个错题/g, " mistakes"], [/ 分钟/g, " min"]
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
    var pre = key;
    PRE.forEach(function (r) { pre = pre.replace(r[0], r[1]); });
    if (pre !== key) return raw.replace(key, pre);
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
    var bar = document.querySelector('.topbar');
    if (bar) {
      btn.style.cssText = 'font-size:12px;padding:6px 10px;margin-left:8px';
    } else {
      btn.style.cssText = 'position:fixed;right:18px;top:14px;z-index:9999;font-size:11px;padding:6px 10px';
    }
    btn.textContent = lang === 'en' ? '中文' : 'EN';
    btn.title = 'Switch UI language';
    btn.addEventListener('click', function () {
      localStorage.setItem('tf-lang', lang === 'en' ? 'zh' : 'en');
      location.reload();
    });
    if (bar) bar.appendChild(btn); else document.body.appendChild(btn);
  }

  function message(text) {
    if (lang !== 'en' || !text) return text;
    var rules = [
      [/^正在解析文件：(.+)$/, "Parsing $1"],
      [/^正在解析 (.+?)（(\d+)\/(\d+)）$/, "Parsing $1 ($2/$3)"],
      [/^正在规划课程大纲/, "Planning outline"],
      [/^已规划 (\d+) 章，开始逐章生成/, "$1 chapters planned, generating"],
      [/^已生成 (\d+)\/(\d+) 个章节块/, "Wrote $1/$2 sections"],
      [/^正在识别配图：(.+?)（(\d+)\/(\d+)）/, "Figures: $1 ($2/$3)"],
      [/^正在 OCR 扫描页：(.+?)（(\d+)\/(\d+)）/, "OCR: $1 ($2/$3)"],
      [/^正在排版/, "Typesetting"],
      [/^正在重写：(.+)$/, "Rewriting: $1"],
      [/^正在提取区块 (\d+)\/(\d+).*$/, "Extracting chunk $1/$2"],
      [/^正在生成…$/, "Generating…"],
      [/^完成（自检有问题）$/, "Done (with warnings)"],
      [/^完成$/, "Done"]
    ];
    for (var i = 0; i < rules.length; i++) {
      if (rules[i][0].test(text)) return text.replace(rules[i][0], rules[i][1]);
    }
    return text;
  }

  window.TF_LANG = { get: function () { return lang; }, apply: apply, msg: message };
  document.addEventListener('DOMContentLoaded', function () {
    apply(); toggleButton();
    if (lang === 'en') {
      new MutationObserver(function (muts) {
        muts.forEach(function (m) {
          if (m.type === 'characterData') {
            var out = translateString(m.target.nodeValue);
            if (out !== null) m.target.nodeValue = out;
          }
          m.addedNodes.forEach(function (n) {
            if (n.nodeType === 1) walk(n);
            else if (n.nodeType === 3) {
              var out = translateString(n.nodeValue);
              if (out !== null) n.nodeValue = out;
            }
          });
        });
      }).observe(document.body, { childList: true, subtree: true, characterData: true });
    }
  });
})();
