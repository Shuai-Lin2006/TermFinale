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
    "返回":"Back","继续阅读":"Continue reading","问一下":"Ask AI","预计提分":"Projected",
    "生成中…":"Generating…","重写中":"Rewriting","课程":"Course","大二 · 环境工程":"Sophomore · Env. Engineering",
    "思考中…":"Thinking…","完成":"Done","讲义生成好了":"Guide ready","提取完成":"Extraction done",
    "试卷生成好了":"Paper ready","分析完成":"Analysis done","准备中…":"Preparing…",
    "普通一本":"Ordinary","二本":"Second tier","专科":"College","211":"Project 211","985":"Project 985",
    "1 · 很好":"1 · Great","2 · 还行":"2 · Okay","3 · 一般":"3 · Average","4 · 较弱":"4 · Weak","5 · 很弱":"5 · Very weak",
    "这些信息会影响讲义的讲法和紧迫度":"These affect how the guide is written.",
    "选好资料和模式，剩下的交给流水线":"Pick materials and a mode; the pipeline does the rest.",
    "页数上限（分册）":"Page limit (volumes)","全部页":"All pages","30 页 / 册":"30 pages / vol","60 页 / 册":"60 pages / vol","100 页 / 册":"100 pages / vol",
    "严格模式：覆盖率低于 80% 不交付":"Strict: no delivery below 80% coverage",
    "温柔小姐姐":"Gentle","老师":"Teacher","学术AI":"Academic AI","阳光小哥哥":"Sunny","暴力极客":"Hacker",
    "危险操作":"Danger zone","清除全部数据":"Clear all data",
    "阅读时选中提问，点「存为笔记」就会出现在这里":"Select text and save a note; it appears here.",
    "在阅读器里选中一段话，问 AI，然后把回答存下来":"Ask AI in the reader and save answers here.",
    "去阅读 →":"Read →","还没有试卷，去生成一套。":"No papers yet. Generate one.",
    "选择题自动判分，做错的题自动进错题本":"Auto-grade multiple choice; wrong answers go to mistakes.",
    "2 星 · 基础":"2★ Basic","3 星 · 常规期末":"3★ Standard","4 星 · 拔高":"4★ Advanced","5 星 · 地狱":"5★ Hard",
    "自定义题型 / 数量 / 分值（合计必须 100 分）":"Custom types / counts / points (total 100)",
    "单项选择题":"Multiple choice","多项选择题":"Multi-select","判断题":"True / False","填空题":"Fill blanks",
    "名词解释":"Definitions","简答题":"Short answer","计算题":"Calculations","推断题":"Inference","综合题":"Comprehensive",
    "证明题":"Proof","翻译题":"Translation","写作题":"Writing","阅读理解":"Reading","完形填空":"Cloze",
    "编程题":"Programming","案例分析题":"Case analysis","论述题":"Essay",
    "模拟练习":"Mock","原题改数":"Numbers changed","原题变式":"Variants","预测仿真":"Prediction",
    "在阅读器里选中一段话，问 AI，然后把回答存下来。":"Ask AI in the reader and save answers here.",
    "还没有课程":"No courses yet","还没有课程，先新建一门":"No courses yet. Create one.",
    "先新建一门课，上传资料，5 分钟后就能开始。":"Create your first course and upload materials to start.",
    "进行中的课":"In progress","新建课程":"New course",
    "今天没有到期错题，休息一下。":"No mistakes due today. Take a break.",
    "还没有资料":"No materials yet","复习计划":"Review plan","资料统计":"Materials","今天该复习":"Due today","最近考试":"Upcoming exams",
    "去复习":"Review","管理资料 →":"Manage →","共 ":"Total "," 门课":" courses","还没有资料":"No materials yet",
    "Final Exam Studio · 期末冲刺工作台":"Final Exam Studio","欢迎来到":"Welcome to","开发者 Lan":"Developer Lan",
    "先花两分钟，":"Take two minutes","把工作台调成你的样子。":"Make this workspace yours.",
    "开始设置":"Get started","从资料，到分数。":"From materials to marks.",
    "上传资料，填写你的个人情况":"Upload materials and fill in your profile",
    "PDF、PPTX、Word、扫描件、教材照片、音频都可以。":"PDF, PPTX, Word, scans, textbook photos, audio.",
    "生成讲义与题目，随时编辑、保留、导出、打印":"Generate guides and papers; edit, keep, export, print",
    "按你的资料写，标注来源页，图片只引用原图。":"Written from your materials, with source pages and original figures.",
    "可练习，可随时提问 AI":"Practice and ask AI anytime",
    "选中正文提问，存笔记、收错题，选择题自动判分。":"Ask about any passage, save notes, collect mistakes, auto-grade.",
    "继续":"Continue","返回":"Back","怎么称呼你？":"What should we call you?",
    "只用来在首页打招呼和预填课程专业，保存在本机，之后可以随时修改。":"Used for the homepage greeting and course major. Stored locally.",
    "名字 / ID":"Name / ID","专业":"Major","完成，进入工作台":"Finish and enter",
    "一本":"Tier 1","二本":"Tier 2","PH:搜索课程…":"Search courses…",
    "题 ×":"questions ×","分":"pts","+ 加题型":"+ Add type","按科目推荐":"Suggest by subject",
    "准备好就开始":"Ready when you are","个人资料":"Profile","首页与侧栏显示":"Shown on home and sidebar",
    "建议 200KB 以内的正方形图片":"Square image under 200KB recommended",
    "保存资料":"Save profile",
    "删除全部课程、资料、生成物、笔记、错题，并回到欢迎页。API Key 会保留。":"Delete all courses, files, outputs, notes and mistakes, then return to welcome. API keys are kept.",
    "PH:已配置，留空表示不修改":"Configured; leave blank to keep",
    "阅读时选中题目，点「加入错题」；之后按 1/2/4/7 天提醒复习。":"Select a question and choose Add to mistakes; review on a 1/2/4/7-day schedule.",
    "← 返回":"← Back","去课程里上传第一份资料。":"Upload your first file from a course.",
    "PH:例如：老师强调第 3 章 / 多给计算题 / 我基础差，讲慢一点 / 不要英文缩写":"e.g. focus on chapter 3 / more calculations / explain slowly",
    "搜索课程…":"Search courses…",
    "中文":"Chinese","繁體中文":"Traditional Chinese",
    "参考历年真题":"Reference past papers",
    "例如：老师强调第 3 章 / 多给计算题 / 我基础差，讲慢一点 / 不要英文缩写":"e.g. focus on chapter 3 / more calculations / explain slowly",
    "已配置，留空表示不修改":"Configured; leave blank to keep",
    "资料类型判断":"Material type","生成模式":"Study mode","期末冲刺":"Exam sprint","课堂理解":"Lecture mode",
    "更像课堂讲义":"Looks like lecture notes","更像考试资料":"Looks like exam material","不确定":"Uncertain",
    "考试相关词":"exam keywords","课堂/活动词":"lecture keywords","习题词":"exercise keywords","个":"",
    "自设难度（这门课）":"Self difficulty","你的基础（这门课）":"Your foundation",
    "1 · 很容易":"1 · Very easy","2 · 比较简单":"2 · Easy","3 · 常规期末":"3 · Standard",
    "4 · 比较难":"4 · Hard","5 · 很难":"5 · Very hard",
    "1 · 基础很好":"1 · Strong","2 · 基础还行":"2 · Okay","3 · 基础一般":"3 · Average",
    "4 · 基础较弱":"4 · Weak","5 · 基础很弱":"5 · Very weak",
    "打开课程":"Open course","课程详情":"Course","资料":"Materials","生成物":"Generated",
    "上传资料":"Upload material","再生成":"Generate again","剩余天数":"Days left",
    "目标分":"Target","自设难度":"Self difficulty","自身基础":"Foundation","讲解人设":"Persona",
    "可用":"Available","缺失":"Missing","权重":"Weight","去生成":"Generate",
    "还没有资料":"No materials yet","还没有生成物":"Nothing generated yet",
    "旧生成物，未记录语言/人设参数":"Legacy output, no language/persona metadata",
    "选择一份打开":"Choose one to open","进行中":"In progress","临近考试":"Exam soon",
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
    [/^旧生成物，未记录语言\/人设参数 · 资料 (\d+) 份 · (\d+) KB$/, "Legacy output · $1 files · $2 KB"],
    [/^资料 (\d+) 份 · (\d+) KB$/, "$1 files · $2 KB"],
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
    [/^(\d+) 份$/, "$1 files"],
    [/^(\d+) 个 · ([\d.]+[A-Za-z]+)$/, "$1 items · $2"],
    [/^(\d+) 页 \/ 册$/, "$1 pages / vol"],
    [/^共 (\d+) 道到期错题 · (\d+) 门课$/, "$1 due · $2 courses"],
    [/^共 (\d+) 份资料 · (\d+) MB · (\d+) 门课$/, "$1 files · $2 MB · $3 courses"],
    [/^(\d+) 题$/, "$1 questions"],
    [/^合计 (\d+) 分$/, "Total $1 pts"],
    [/^共 (\d+) files · (\d+) MB · (\d+) 门课$/, "$1 files · $2 MB · $3 courses"],
    [/^共 (\d+) files · (\d+) MB$/, "$1 files · $2 MB"],
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
        var ph = el.getAttribute('placeholder') || '';
        var out = translateString(ph);
        if (out === null && ph.indexOf('已配置') === 0) out = 'Configured; leave blank to keep';
        if (out !== null) el.setAttribute('placeholder', out);
      });
    } finally { translating = false; }
  }

  var HANT = null;
  var HANT_PHRASES = [["软件","軟體"],["网络","網路"],["信息","資訊"],["视频","影片"],["打印","列印"],
    ["设置","設定"],["默认","預設"],["支持","支援"],["保存","儲存"],["质量","品質"],["数据","資料"],
    ["用户","使用者"],["文件","檔案"],["项目","專案"],["课程","課程"],["复习","複習"]];
  function hantStr(s) {
    if (!HANT || !s) return s;
    HANT_PHRASES.forEach(function (p) { s = s.split(p[0]).join(p[1]); });
    return s.split('').map(function (c) { return HANT[c] || c; }).join('');
  }
  function applyHant(root) {
    if (!HANT) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (n) {
      var tag = n.parentNode && n.parentNode.nodeName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'CODE') return;
      var _h = hantStr(n.nodeValue); if (_h !== n.nodeValue) n.nodeValue = _h;
    });
    (root.querySelectorAll ? root : document).querySelectorAll('[placeholder]').forEach(function (el) {
      el.setAttribute('placeholder', hantStr(el.getAttribute('placeholder')));
    });
  }
  function apply() {
    if (lang === 'en') {
      document.documentElement.lang = 'en';
      walk(document.body);
    } else if (lang === 'zh-Hant') {
      document.documentElement.lang = 'zh-Hant';
      if (HANT) applyHant(document.body);
      else fetch('assets/hant.json?v=1').then(function (r) { return r.json(); }).then(function (m) {
        HANT = m; applyHant(document.body);
      }).catch(function () {});
    }
  }

  function langSelect() {
    var sel = document.createElement('select');
    sel.className = 'lang-select';
    var labels = lang === 'en' ? ['Simplified Chinese','Traditional Chinese','English']
      : (lang === 'zh-Hant' ? ['簡體中文','繁體中文','English'] : ['简体中文','繁體中文','English']);
    sel.innerHTML = '<option value="zh">'+labels[0]+'</option><option value="zh-Hant">'+labels[1]+'</option><option value="en">'+labels[2]+'</option>';
    sel.value = lang;
    sel.addEventListener('change', function () {
      localStorage.setItem('tf-lang', sel.value);
      location.reload();
    });
    var bar = document.querySelector('.topbar');
    if (bar) bar.appendChild(sel); else document.body.appendChild(sel);
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
      [/^模型生成中…（已用 (\d+) 秒）$/, "Model is writing… ($1s)"],
      [/^共 (\d+) 道到期错题 · (\d+) 门课$/, "$1 due · $2 courses"],
    [/^共 (\d+) 份资料 · (\d+) MB · (\d+) 门课$/, "$1 files · $2 MB · $3 courses"],
    [/^完成$/, "Done"]
    ];
    for (var i = 0; i < rules.length; i++) {
      if (rules[i][0].test(text)) return text.replace(rules[i][0], rules[i][1]);
    }
    return text;
  }

  window.TF_LANG = { get: function () { return lang; }, apply: apply, msg: message };
  document.addEventListener('DOMContentLoaded', function () {
    apply(); langSelect();
    if (lang === 'en' || lang === 'zh-Hant') {
      new MutationObserver(function (muts) {
        muts.forEach(function (m) {
          if (lang === 'zh-Hant') {
            if (m.type === 'characterData') { var _h2 = hantStr(m.target.nodeValue); if (_h2 !== m.target.nodeValue) m.target.nodeValue = _h2; }
            m.addedNodes.forEach(function (n) { if (n.nodeType === 1) applyHant(n); });
            return;
          }
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
