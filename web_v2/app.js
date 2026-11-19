/* TermFinale 学习台 v3 · 单页前端（无外部依赖） */
(() => {
  "use strict";

  const view = document.getElementById("view");
  const crumb = document.getElementById("crumb");
  const toastEl = document.getElementById("toast");
  let onboardingStep = 0;
  let onboardingAvatar = "";
  let onboardingName = "";
  let onboardingSchool = "";
  let onboardingSchoolTier = "";
  let onboardingSchoolLogo = "";
  let onboardingMajor = "";
  let schoolCatalog = null;
  let schoolCatalogPromise = null;

  const state = {
    settings: null,
    courseEditing: false,
    courseEditingKey: "",
    courseTab: "lectures",
    libraryEditing: false,
    artifacts: [],
    artifact: null,
    practice: null,
    review: null,
    workbench: null,
    ai: { open: false, artifactId: "", messages: [], busy: false, web: false, deep: false },
    lang: "zh",
    seq: 0,
    lastRoute: "",
    routeStack: [],
    skipPush: false,
  };

  function currentCourseKey() {
    try { return localStorage.getItem("tf-current-course") || ""; } catch (e) { return ""; }
  }
  function setCurrentCourseKey(key, name = "") {
    try {
      if (key) localStorage.setItem("tf-current-course", key);
      if (name) localStorage.setItem("tf-current-course-name", name);
    } catch (e) {}
    updateCourseChip();
  }
  function updateCourseChip() {
    const chip = document.getElementById("currentCourseChip");
    if (!chip) return;
    const key = currentCourseKey();
    const name = (() => { try { return localStorage.getItem("tf-current-course-name") || ""; } catch (e) { return ""; } })();
    if (!key || !name) { chip.hidden = true; return; }
    chip.hidden = false;
    chip.href = `#/course/${encodeURIComponent(key)}`;
    chip.innerHTML = `<span>${esc(name)}</span>`;
  }

  updateCourseChip();
  // ---------------- i18n ----------------
  // Only UI chrome lives here. Course names, artifact/section titles, task
  // content and reader iframe content are source data and are never translated.
  const plural = (n, one, many) => `${n} ${Number(n) === 1 ? one : many}`;

  const I18N = {
    zh: {
      "app.title": "TermFinale 学习台",
      "brand.sub": "学习台",
      "foot.local": "本地优先 · 数据不离开本机",
      "foot.version": "v3.0 · 学习台",
      "nav.home": "主控台",
      "nav.guide": "说明",
      "guide.title": "说明",
      "guide.pendingTitle": "说明正在整理",
      "guide.pendingBody": "写好后会放在这里。在此之前，每个页面上都有一两句提示，照着做就能用起来。",
      "guide.firstUse": "首次使用，必读",
      "guide.mustRead": "查看说明",
      "guide.later": "稍后",
      "guide.bannerHint": "先看完使用说明，再开始课程。",
      "settings.avatarHint": "点击更换头像（可选）",
      "onboard.brandKicker": "TERMFINALE · 学习工作台",
      "onboard.brandTitle": "真·一站式<br>大学生<br>期末复习系统",
      "onboard.brandBody": "课程、讲义、训练、复习、试卷，收在一条线上。",
      "onboard.brandFoot": "本地优先　·　无需注册　·　开发者 Lan",
      "onboard.step1": "开始",
      "onboard.step2": "使用说明",
      "onboard.step3": "建立档案",
      "onboard.stepLabel": "第 {n} 步",
      "onboard.welcomeKicker": "WELCOME",
      "onboard.welcomeTitle": "欢迎来到<br>TermFinale",
      "onboard.welcomeLead": "不用注册账号。先看一遍课程、训练、试卷怎么连起来，再给自己起一个称呼。",
      "onboard.start": "开始设置",
      "onboard.time": "约 2 分钟",
      "onboard.welcomeNote": "本地优先 · 无需注册 · 约 2 分钟",
      "onboard.welcomeC1Title": "课程与讲义",
      "onboard.welcomeC1Body": "资料按权重变成课程与可读讲义。",
      "onboard.welcomeC2Title": "训练与复习",
      "onboard.welcomeC2Body": "从讲义小节出题，错题自动进入复习队列。",
      "onboard.welcomeC3Title": "出卷与自测",
      "onboard.welcomeC3Body": "按真题结构生成试卷，选择题自动判分。",
      "onboard.introKicker": "HOW IT WORKS",
      "onboard.introTitle": "一门课，一条完整闭环。",
      "onboard.row1": "资料变成课程与讲义",
      "onboard.row1Body": "讲义按课程归档，引用来源页，保留原图；课程、讲义和学习路径一一对应。",
      "onboard.row2": "训练形成闭环",
      "onboard.row2Body": "新题、题库和错题复习共用同一套答题记录；每次作答都会更新掌握度和复习排期。",
      "onboard.row3": "试卷与 AI 都能溯源",
      "onboard.row3Body": "正式试卷可以自测并自动判选择题；AI 能查讲义、联网引用，错题直接进入复习。",
      "onboard.profileKicker": "PROFILE",
      "onboard.profileTitle": "怎么称呼你？",
      "onboard.profileLead": "头像可以先不填。名字会出现在首页问候语里，之后可在设置中修改。",
      "onboard.avatarHint": "上传头像（可选）",
      "onboard.nameLabel": "名字 / ID",
      "onboard.namePlaceholder": "",
      "onboard.profileNote": "头像和名字之后都可以在设置里修改。",
      "onboard.nameRequired": "请先填写名字。",
      "onboard.finish": "完成，进入总控台",
      "onboard.back": "返回",
      "onboard.continue": "继续",
      "onboard.saveFailed": "保存失败，请重试",
      "onboard.avatarTooBig": "头像请小于 350KB",
      "onboard.schoolLabel": "学校",
      "onboard.schoolPlaceholder": "输入几个字，自动匹配学校",
      "onboard.tierLabel": "学校层级",
      "onboard.tierPlaceholder": "请选择",
      "onboard.schoolRequired": "学校、学校层级和专业都必须填写",
      "onboard.majorLabel": "专业",
      "settings.schoolLabel": "学校",
      "settings.schoolPlaceholder": "输入几个字，自动匹配学校",
      "settings.schoolTierLabel": "学校层级",
      "settings.schoolTierPlaceholder": "请选择",
      "settings.schoolRequired": "保存前请填写学校、学校层级和专业",
      "settings.majorLabel": "专业",
      "onboard.title": "先走一遍这三层",
      "onboard.body": "课程是容器，讲义是内容；练习和复习进入训练，出卷是正式试卷。先打开课程，不要从这里直接做题。",
      "onboard.dismiss": "知道了",
      "cc.continue": "继续上次",
      "cc.start": "从这里开始",
      "cc.startAction": "打开课程",
      "cc.review": "到期复习",
      "cc.dueCount": "{n} 道待复习",
      "cc.noneDue": "暂无到期",
      "nav.search": "打开课程与资料库",
      "search.title": "搜索课程与资料",
      "search.placeholder": "搜索课程、讲义标题或正文…",
      "search.hint": "输入关键词开始搜索；⌘K 打开，Esc 关闭",
      "search.empty": "没有找到相关内容",
      "search.loading": "搜索中…",
      "search.results": "找到 {n} 条结果",
      "search.course": "课程",
      "search.artifact": "讲义",
      "search.content": "正文",
      "nav.groupLearn": "学习",
      "nav.groupTrain": "训练",
      "nav.groupExam": "测评",
      "nav.groupData": "资料",
      "nav.groupSystem": "系统",
      "foot.localShort": "本地",
      "foot.localId": "本地 ID",
      "focus.line1": "先讀一頁，再練一題，",
      "focus.line2": "最後複習到期。",
      "focus.line1": "先读一页，再练一题，",
      "focus.line2": "最后复习到到期。",
      "foot.localId": "本地 ID",
      "nav.library": "课程库",
      "nav.workbench": "内容工具",
      "nav.practice": "练习",
      "nav.review": "错题本",
      "nav.notes": "笔记",
      "nav.settings": "设置",
      "nav.back": "返回",
      "nav.exam": "出卷",
      "exam.eyebrow": "试卷",
      "exam.title": "出卷",
      "exam.lede": "按真题格式或自定义蓝图出卷。",
      "exam.artifact": "知识范围（讲义）",
      "exam.subject": "科目",
      "exam.subjectAuto": "科目：{subject}（按课程资料）",
      "exam.limit": "单卷最多 50 题；超过请拆成两份",
      "exam.longConfirm": "这份试卷题量较大，生成可能需要数分钟，且审计会分批进行。继续？",
      "exam.difficulty": "难度（1–5）",
      "exam.mode": "模式",
      "exam.types": "题型（逗号分隔）",
      "exam.typesHint": "留空按科目默认",
      "exam.blueprint": "自定义蓝图（可空）",
      "exam.blueprintHint": "如：选择题 10 题 30 分；计算题 4 题 40 分；简答题 2 题 30 分",
      "exam.references": "历届真题（可选，最多 3 份）",
      "exam.referencesHint": "原题改数/变式需先上传真题。",
      "exam.chooseRefs": "选择真题文件",
      "exam.noRefs": "未选择真题",
      "exam.refRequired": "原题改数/原题变式需要先上传至少一份真题；否则请用模拟/预测模式。",
      "exam.custom": "补充要求",
      "exam.customHint": "如：多考换路定则，计算步骤要完整",
      "exam.start": "生成试卷",
      "exam.generating": "出卷 + 答案审计中，通常 1–3 分钟…",
      "exam.failed": "出卷失败",
      "exam.total": "总分",
      "exam.paper": "试卷",
      "exam.showAnswers": "显示答案",
      "exam.hideAnswers": "隐藏答案",
      "exam.print": "打印",
      "exam.export": "导出 HTML",
      "exam.word": "导出 Word",
      "exam.saveWord": "保存 Word 到桌面",
      "exam.savePdf": "保存 PDF 到桌面",
      "exam.selfTest": "开始自测",
      "exam.selfTestHint": "只自动判选择题；非选择题需人工核对。",
      "exam.backPreview": "返回试卷预览",
      "exam.autoOnly": "可自动判分的选择题：{n} 道",
      "exam.noChoice": "这份试卷没有可自动判分的单选题。",
      "exam.submit": "交卷",
      "exam.submitted": "已交卷",
      "exam.score": "得分",
      "exam.autoResult": "答对 {correct} / {auto} 道自动判分题，已答 {answered} 道。",
      "exam.autoScore": "自动判分",
      "exam.manualNote": "计算题/简答题没有自动判分，需按参考答案人工核对。",
      "exam.goScheduled": "错题已进入复习",
      "exam.retry": "再考一次",
      "exam.viewPaper": "查看完整试卷",

      "exam.pdf": "打印 / 另存为 PDF",
      "exam.edit": "编辑",
      "exam.editOn": "已进入编辑模式：可直接改纸上文字；再次点编辑退出",
      "exam.editOff": "已退出编辑模式",
      "exam.figure": "配图说明",
      "exam.answer": "答案",
      "exam.analysis": "解析",
      "exam.noDoc": "还没有试卷。选好资料和模式生成第一份。",
      "exam.noArtifactTitle": "还没有可出卷的讲义",
      "exam.noArtifactText": "先建立一份讲义，再选范围和模式出卷。",
      "exam.afterGenerateHint": "生成后打开试卷；历史试卷在课程页「出卷」。",
      "exam.modeChange": "原题改数",
      "exam.modeVariant": "原题变式",
      "exam.modeMock": "模拟",
      "exam.modePredict": "预测",
      "exam.subjectMath": "高等数学",
      "exam.subjectPhysics": "物理",
      "exam.subjectCircuit": "电路",
      "exam.subjectChem": "化学",
      "exam.subjectCS": "计算机",
      "exam.subjectBio": "生物",
      "exam.subjectMedical": "医学",
      "exam.subjectLiberal": "文科",
      "exam.subjectOther": "其他",
      "exam.points": "分",
      "exam.source": "出处",
      "exam.paperMeta": "满分 100 分 · 考试时间 120 分钟 · 姓名 ______ 学号 ______ 得分 ______",
      "exam.footnote": "本试卷由 TermFinale 智能体生成，仅供复习训练；具体请以实际资料为准，本资料不承担由此产生的法律责任。",
      "exam.issueTitle": "生成不完整 · {n} 个问题：",
      "exam.type.choice": "选择题",
      "exam.type.calculation": "计算题",
      "exam.type.short_answer": "简答题",
      "exam.type.fill_blank": "填空题",
      "exam.type.proof": "证明题",
      "exam.type.experiment": "实验题",
      "exam.type.design": "设计题",
      "exam.type.term": "名词解释",
      "exam.type.case": "病例分析",
      "exam.type.essay": "论述题",
      "crumb.library": "讲义库",
      "crumb.new": "新建课程",
      "crumb.course": "课程",
      "crumb.artifact": "质量报告",
      "crumb.read": "阅读",
      "aria.menu": "菜单",
      "aria.theme": "切换主题",
      "aria.langToEn": "切换到英文",
      "aria.langToZh": "切换到中文",
      "lang.zh": "简体中文",
      "lang.hant": "繁體中文",
      "gen.lang": "生成语言",
      "gen.zh": "简体中文",
      "gen.hant": "繁體中文",
      "gen.en": "English",
      "gen.illustrations": "AI decorative background (~$0.025/image, not precise)",
      "gen.illustrations": "AI 装饰背景（约 $0.025/张，非精确图）",
      "lang.en": "English",
      "lang.label": "界面语言",
      "lang.meta": "导航、按钮、标签与状态",
      "ai.title": "AI 助教",
      "ai.general": "通用学习助手",
      "ai.context": "上下文",
      "ai.allLibrary": "全部课程资料",
      "ai.allPlaceholder": "问任何问题；也可以说资料名，如：环境工程原理讲义里…",
      "ai.allHint": "可以说资料名，我会检索全部课程；也能直接聊天或点联网。",
      "ai.placeholder": "问 AI，或者直接聊天；也可以说资料名…",
      "ai.send": "发送",
      "ai.thinking": "思考中…",
      "ai.empty": "随时问：这段为什么这样？帮我出题、提炼重点，或聊任何学习问题。",
      "ai.capTitle": "我可以帮你",
      "ai.capExplain": "解释 / 总结",
      "ai.capExplainBody": "按小节和页码解释概念，也可以整段改写。",
      "ai.capQuiz": "出题 / 变式",
      "ai.capQuizBody": "基于当前讲义出单选、计算或简答，附答案与解析。",
      "ai.capPlan": "复习计划",
      "ai.capPlanBody": "按到期错题和弱项排 7 天计划，不编资料外章节。",
      "ai.capAgent": "多步任务",
      "ai.capAgentBody": "规划工具步骤，查资料、出卷、生成讲义；生成前会确认。",
      "ai.capNote": "首页会检索全部课程资料；你也可以直接说资料名。",
      "ai.advanced": "历史运行 / 工作流 / 目标",
      "ai.useful": "有用",
      "ai.useless": "没用",
      "ai.recorded": "已记录",
      "ai.unsourced": "未引用讲义，请核对",
      "ai.agentGoalEmpty": "先输入一个目标，再点 Agent",
      "ai.wholePrompt": "先输入整份改写的指令",

      "ai.failed": "AI 调用失败",
      "ai.note": "AI 可能出错；资料内答案以讲义出处为准。",
      "ai.quickExplain": "解释这一节",
      "ai.quickQuiz": "出 2 道题",
      "ai.quickPlan": "7 天计划",
      "ai.quickPoints": "提炼重点",
      "ai.agent": "执行任务",
      "ai.agentPlan": "计划",
      "ai.agentSources": "出处页",
      "ai.agentRun": "执行计划",
      "ai.agentCancel": "取消任务",
      "ai.agentNeedConfirm": "需要确认",
      "ai.agentRuns": "最近任务",
      "ai.agentNoRuns": "还没有 Agent 任务",
      "ai.agentPlanner": "规划来源",
      "ai.agentEdit": "编辑计划",
      "ai.agentApply": "应用修改",
      "ai.agentSave": "保存工作流",
      "ai.agentWorkflows": "已存工作流",
      "ai.agentResume": "继续",
      "ai.agentReplan": "重规划",
      "ai.agentForm": "表单编辑",
      "ai.agentAddStep": "加一步",
      "ai.agentRemove": "删",
      "ai.agentGoals": "长期目标",
      "ai.agentGoalPlan": "生成今日计划",
      "ai.agentRunDue": "运行到期目标",
      "ai.agentSavePrompt": "给这份工作流起个名字",
      "ai.whole": "整份改写",
      "ai.wholeRunning": "正在整份改写并重新检查、重出 PDF…",
      "ai.wholeDone": "整份改写草稿已生成",
      "ai.openDraft": "打开草稿",
      "lang.note": "只切换界面文案；课程名、讲义标题、小节标题和生成内容保持原语言。阅读器内的 EN 开关独立生效。",
      "error.request": "请求失败（{status}）",
      "error.network": "无法连接网络或本地服务，请检查网络后重试。",
      "error.actionFailed": "操作失败，请重试",
      "error.title": "出错了",
      "error.load": "加载失败",
      "error.retry": "重试",
      "loading.default": "正在加载…",
      "notFound.title": "页面不存在",
      "notFound.text": "回到讲义库继续。",
      "notFound.cta": "去讲义库",
      "status.delivered": "可读",
      "status.review": "已生成",
      "status.rejected": "需重做",
      "status.draft": "草稿",
      "status.due": "到期",
      "status.passed": "通过",
      "status.passedShort": "通过",
      "status.notPassed": "需重做",
      "status.notPassedShort": "重做",
      "status.machinePassed": "机器检查通过",
      "status.partialCoverage": "部分覆盖",
      "status.partialDelivery": "部分交付",
      "status.configured": "已配置",
      "status.notConfigured": "未配置",
      "status.migrated": "已迁入",
      "status.pendingReview": "已生成",
      "status.migratedManual": "已迁入 · 待人工",
      "status.readReport": "读报告，不自动生成",
      "status.notDone": "未做",
      "unit.lecturePages": "{n} 页讲义",
      "unit.sourcePages": "{n} 页资料",
      "unit.lectures": "{n} 份讲义",
      "unit.sections": "{n} 节",
      "unit.figures": "{n} 图",
      "unit.blocks": "{n} 块",
      "unit.paragraphs": "{n} 段",
      "unit.pages": "{n} 页",
      "unit.notes": "{n} 条笔记",
      "unit.sources": "{n} 份资料",
      "unit.pageN": "第 {n} 页",
      "sep.list": "、",
      "meta.pages": "页",
      "meta.sections": "节",
      "meta.figures": "图",
      "meta.items": "张",
      "meta.all": "全",
      "quality.noAudit": "未做内容检查",
      "quality.noAuditFile": "还没有内容检查记录",
      "quality.structureGate": "结构完整",
      "quality.content": "文字检查",
      "quality.pdf": "版面检查",
      "quality.language": "语言一致",
      "quality.semantic": "内容检查",
      "quality.contentMetrics": "内容质量",
      "quality.citationSupport": "说法有依据",
      "quality.termRecall": "重点词覆盖",
      "quality.dupSentence": "重复句",
      "quality.boilerplate": "模板句密度",
      "quality.waterTitle": "重复与套话",
      "quality.dupShort": "重复 {n}%",
      "quality.boilerShort": "套话 {n}/千字",
      "quality.imageMode": "影像版",
      "quality.imageModeDetail": "保留原页影像 {images} 张，资料共 {pages} 页",
      "quality.metricsHint": "这些都在你本机算：每段说法能否在资料页找到依据、重点词有没有讲到、有没有重复或套话。",
      "quality.fallbackNotice": "有 {n} 节模型没写出来，已改用资料原文排：{labels}。这几节照样能读、有出处。",
      "quality.coverage": "讲义覆盖",
      "quality.coverageMet": "讲到 {actual}% 的页，目标 {target}% 以上",
      "quality.coverageNoTier": "讲到 {actual}% 的页",
      "quality.figures": "图源",
      "quality.pass": "通过",
      "quality.fail": "需重做",
      "quality.zeroIssues": "0 条硬伤",
      "quality.hasIssues": "有硬伤",
      "quality.figureOk": "{n} 张 ok",
      "quality.figureBad": " · {n} 张异常",
      "quality.figureFallback": "图",
      "quality.issue": "异常",
      "quality.ok": "ok",
      "artifact.notFoundTitle": "讲义不存在",
      "artifact.notFoundText": "可能已被移动或删除。",
      "artifact.backLibrary": "回讲义库",
      "artifact.eyebrow": "质量报告",
      "artifact.meta": "{pages} 页资料 · {pdf} 页讲义 · {sections} 节 · {figures} 图",
      "artifact.read": "开始阅读",
      "artifact.practice": "练习",
      "artifact.backCourse": "← 回课程",
      "artifact.sections": "小节",
      "artifact.sectionsHint": "练哪一节，就从哪一节出题",
      "artifact.pageCol": "页码",
      "artifact.noSections": "没有 sections.json",
      "artifact.practiceSection": "练这一节",
      "artifact.figures": "图",
      "artifact.figuresCount": "{n} 张",
      "artifact.noFigures": "没有图源报告。",
      "artifact.figureSource": "来源：第 {pages} 页 · {origin} · {status}",
      "artifact.bannerRejectedTitle": "这份讲义生成得不完整。",
      "artifact.bannerRejectedBody": "建议重新生成，或换几页资料再试。",
      "artifact.bannerReviewTitle": "已生成，可以开始阅读。",
      "artifact.bannerReviewBody": "{audit}。个别页面可能讲得简略，建议对照原页看重点。",
      "artifact.bannerGoodTitle": "可以读了：基础检查和内容检查都通过。",
      "artifact.bannerGoodBody": "{audit}；还是建议你抽看几道关键例题。",
      "artifact.rewrite": "整份 AI 改写（草稿）",
      "artifact.rewriteHint": "不会改原稿：先出新草稿并重新检查、重出 PDF，你对比后决定保留还是丢弃。",
      "artifact.rewriteInstruction": "改写要求",
      "artifact.rewritePlaceholder": "例如：讲得更通俗，多举生活例子；保留所有公式、页码和例题",
      "artifact.rewriteStart": "生成改写草稿",
      "artifact.rewriteRunning": "正在逐节改写并重新检查、重出 PDF…",
      "artifact.rewriteDraft": "草稿已生成",
      "artifact.rewriteKeep": "打开草稿",
      "artifact.rewriteDiscard": "丢弃草稿",
      "artifact.rewriteDiff": "改写对比",
      "artifact.acceptDraft": "一键替换原稿",
      "artifact.acceptHint": "会先自动备份原稿，再用草稿替换并重新检查、重出 PDF；失败会自动还原。",
      "artifact.acceptConfirm": "用这份草稿替换原稿？原稿会先备份。",
      "artifact.restore": "恢复上一版",
      "artifact.restoreConfirm": "恢复上一版备份？当前版本也会先备份。",
      "artifact.review": "人工复核",
      "artifact.reviewHint": "机器检查不等于老师签字；复核人/日期只存在本机。",
      "artifact.nextStep": "建议顺序：先通读一遍，再用「练习」检查掌握度；要整卷复习就去「出卷」。",
      "artifact.runAudit": "补充检查",
      "artifact.auditRunning": "正在逐页检查，页多会久一点…",
      "artifact.auditDone": "检查完成",
      "artifact.auditGaps": "检查完成：有 {n} 页可以补讲",
      "artifact.auditUnverified": "检查完成：有 {n} 页没跑完，可再试一次",
      "artifact.reviewer": "复核人",
      "artifact.reviewNotes": "复核意见（可空）",
      "artifact.saveReview": "保存复核",
      "artifact.reviewed": "已人工复核",
      "artifact.constraints": "生成约束",
      "artifact.keyPoints": "重点/权重",
      "artifact.excluded": "明确不考",
      "artifact.customPrompt": "自定义提示词",
      "artifact.missingPages": "还没讲到的页",
      "card.read": "阅读",
      "card.quality": "质量报告",
      "card.practice": "练习",
      "card.practiceThis": "练这一份",
      "card.noCoverage": "未记录页覆盖",
      "home.eyebrow": "今天先做一件事",
      "home.continue": "继续阅读",
      "home.viewQuality": "看质量报告",
      "home.dueLabel": "道错题到期",
      "home.readableStat": "份可读讲义",
      "home.heroNote": "“可读”表示机器检查已通过；具体质量请在发布声明里说明。",
      "home.emptyEyebrow": "开始",
      "home.emptyTitle": "还没有可读讲义",
      "home.emptyText": "先把资料生成成讲义，或从课程打开已有产物；没有质量报告的不会标“可读”。",
      "home.emptyCta": "去工作台",
      "home.emptyNote": "这里只展示已经生成好的讲义。",
      "home.doNow": "现在做",
      "home.practiceEyebrow": "练习",
      "home.practiceTitle": "练一组",
      "home.practiceBody": "从当前讲义的一节出 3 道单选题；服务端判分，答错自动进错题本。",
      "home.practiceCta": "开始练习 →",
      "home.reviewTitleDue": "{n} 道到期错题",
      "home.reviewTitleNone": "复习队列为空",
      "home.reviewBodyDue": "先清到期项，再开新题；错题按 1/2/4/7 天回来。",
      "home.reviewBodyNone": "没有到期项不是 100% 掌握；可以做新题或看掌握度。",
      "home.reviewCta": "去复习 →",
      "home.workbenchEyebrow": "工作台",
      "home.workbenchTitle": "提取 / 试卷 / 分析",
      "home.workbenchBody": "考点、名词、原题、试卷、逻辑分析都能单独生成；过了机器检查才标“机器通过”。",
      "home.workbenchCta": "打开工作台 →",
      "home.courses": "课程",
      "home.allCourses": "全部 {n} 门",
      "home.noCourseTitle": "还没有课程",
      "home.noCourseText": "去工作台新建一份讲义。",
      "library.eyebrow": "课程",
      "library.title": "课程",
      "library.lede": "按课程看讲义、质量报告和练习；生成物不再堆在首页。",
      "library.backHome": "回今日",
      "library.emptyTitle": "还没有课程",
      "library.emptyText": "先新建一门课程，填入资料和课程信息，再生成首份讲义。",
      "library.cta": "新建课程",
      "course.badgeLecture": "课程 · 有讲义",
      "course.badgeSource": "课程 · 仅资料",
      "course.readableBadge": "{n} 份可读",
      "course.meta": "{n} 份讲义 · {pages} 页 · {figures} 图",
      "course.foot": "{delivered} 可读 · {review} 已生成",
      "course.open": "打开课程 →",
      "course.backAll": "← 全部课程",
      "course.new": "生成讲义",
      "course.newCourse": "新建课程",
      "course.edit": "编辑课程",
      "course.editDone": "完成编辑",
      "course.finishEdit": "完成编辑",
      "course.editLecture": "编辑",
      "course.editCourse": "编辑课程资料",
      "course.generateLecture": "生成讲义 / 编辑资料",
      "course.deleteLecture": "删除",
      "course.deleteLectureConfirm": "永久删除这份资料/讲义？文件、课程记录、练习和错题都会一起删掉。",
      "course.deleteLectureDone": "已永久删除",
      "course.deleteLectureFailed": "删除讲义失败",
      "course.editTitle": "编辑课程",
      "course.editSectionSources": "课程资料",
      "course.editSectionSourcesHint": "保留、添加或移除这门课的原始资料。",
      "course.editSectionInfo": "课程信息",
      "course.editSectionInfoHint": "课程级别信息；讲义参数在讲义模块里设置。",
      "course.editSectionGenerate": "生成设置",
      "course.editSectionGenerateHint": "只影响生成语气和语言",
      "course.editLede": "修改课程信息、AI 总偏好与原始资料；生成讲义在课程内的讲义模块进行。",
      "course.editBack": "返回课程",
      "course.editSourceLecture": "编辑哪份讲义",
      "course.editAddSources": "添加新资料",
      "course.editNoSource": "没有可复用资料",
      "course.editNoSourceBody": "请在下方添加新资料后再重新生成。",
      "course.editWeights": "资料权重（逐份，1–5）",
      "course.editExistingSources": "原有资料",
      "course.editExcludedSources": "已排除资料（{n}）",
      "course.editExcludedHint": "勾选可恢复到本次资料选择；文件本身没有被删除。",
      "course.editKeepHint": "勾选保留；取消勾选只表示从下次生成中排除，不会删除原文件。下方可添加新资料。",
      "course.editChooseFiles": "选择新资料",
      "course.editNoFiles": "未选择文件",
      "course.editGenerate": "生成讲义",
      "course.editSaveOnly": "只保存资料与参数",
      "course.editSaveOnlyDone": "资料与参数已保存；现有讲义未重建",
      "course.editParamsDone": "参数已保存",
      "course.editSaveOnlyFailed": "保存资料失败",
      "course.pendingRebuild": "资料已更新 · 待重建",
      "course.editGenerating": "重新生成中",
      "course.editDone": "新版本已生成，正在回到课程",
      "course.editFailed": "重新生成失败",
      "course.archive": "删除课程",
      "course.archiveNote": "删除会永久移除这门课的用户资料、讲义、试卷、题库、错题和聊天记录；内置/交付资料不会动。",
      "course.archiveConfirm": "永久删除这门课程？用户资料、讲义、试卷、题库、错题和聊天记录都会删除；内置/交付资料保留。",
      "course.deleted": "课程已删除：{n} 份用户资料已移除",
      "course.deleteFailed": "删除课程失败",
      "course.overview": "课程概览",
      "course.settings": "设置",
      "doc.delete": "删除",
      "doc.rename": "重命名",
      "doc.back": "返回内容工具",
      "doc.unknownSource": "未知讲义",
      "doc.hits": "找到 {n} 处",
      "doc.renamePrompt": "输入新的试卷标题",
      "doc.renamed": "已重命名",
      "doc.renameFailed": "重命名失败",
      "doc.deleteConfirm": "删除这份产物？此操作不可撤销。",
      "doc.deleted": "已删除",
      "doc.deleteFailed": "删除失败",
      "course.training": "练习",
      "course.trainingNote": "只统计这门课的练习与到期错题。",
      "course.newPractice": "新题练习",
      "course.newPracticeNote": "选讲义，再选小节。",
      "course.practice": "练习",
      "course.noLectures": "这门课还没有讲义。",
      "course.review": "错题复习",
      "course.reviewNote": "到期与已排期都按这门课过滤。",
      "course.openReview": "打开本课复习",
      "course.papers": "出卷",
      "course.papersNote": "只收正式试卷。",
      "course.newPaper": "新建试卷",
      "course.cleanPapers": "清理重复试卷 · {n}",
      "course.cleanPapersConfirm": "删除同名旧试卷，只保留最新一份？此操作不可撤销。",
      "course.cleanPapersDone": "已清理 {n} 份重复试卷",
      "course.paperAll": "全部 · {n}",
      "course.paperValidated": "通过 · {n}",
      "course.paperReview": "需重做 · {n}",
      "course.selfTested": "已自测 {score}/{total}",
      "course.paper": "试卷",
      "course.noPapers": "还没有试卷",
      "course.noPapersNote": "从讲义生成一份试卷。",
      "course.tools": "提取",
      "course.bankPractice": "题库练习",
      "bank.title": "题库",
      "bank.eyebrow": "BANK",
      "bank.lede": "这里只放已加入题库的原题；删除后会同时移除相关答题记录和错题。",
      "bank.practice": "开始题库练习",
      "bank.manage": "管理题库",
      "bank.count": "{n} 道题",
      "bank.answer": "答案 {x}",
      "bank.emptyTitle": "题库为空",
      "bank.emptyText": "先到内容工具提取原题，再加入题库。",
      "bank.deleteConfirm": "从题库删除这道题？相关答题记录和错题也会移除。",
      "course.bankNote": "从原题提取产物加入题库，再从本课讲义做题。",
      "course.bankEmpty": "还没有题库题。到内容工具运行“提取原题”，再把产物加入题库。",
      "course.bankCount": "{n} 道",
      "course.targetProgress": "目標 {target} 分 · 已練章節均分 {current}",
      "course.targetNoData": "還沒有練習記錄",
      "course.targetUnset": "還沒有設定目標分。",
      "course.targetProgress": "目标 {target} 分 · 已练章节均分 {current}",
      "course.targetNoData": "还没有练习记录",
      "course.targetUnset": "还没有设置目标分。",
      "course.toolsNote": "从讲义生成考点、术语、原题、导图或逻辑分析。",
      "course.openTools": "打开内容工具",
      "course.noTools": "还没有提取结果",
      "course.noToolsNote": "选讲义，运行一次提取。",

      "course.scopeTools": "本课内容工具",
      "course.lecturesTab": "讲义",
      "fuse.title": "多资料拼接",
      "wb.sourceSection": "按讲文章节",
      "wb.sourcePages": "按资料页（扫描/公式页保留原页）",
      "wb.sourceLabel": "取材方式",
      "wb.pagesLabel": "资料页",
      "wb.pagesHint": "例如 1-20 或 3,5,8；公式/图片页会显式跳过，不硬转文字",
      "wb.pagesUseSaved": "用已选页",
      "wb.pagesEmpty": "先填资料页，例如 1-10",
      "wb.unitRunning": "正在按资料页提取",
      "wb.unitSkipped": "公式/图片页已跳过：{pages}",
      "fuse.lede": "勾选至少两份资料：拼接会按主题重排成一份讲义（统一章节、章级过渡、同名内容只讲一次）；不拼接则每份资料各出一份讲义。",
      "fuse.needOne": "先勾选至少一份资料",
      "fuse.needTwo": "拼接至少要两份资料；只做一份请用上面的「选择资料页」",
      "fuse.mergeOn": "拼接：自然融合成一份",
      "fuse.mergeOff": "不拼接：N 份资料 → N 份讲义",
      "fuse.author": "用模型成文（更自然，耗时更长；失败会写明原因）",
      "fuse.digestNote": "不勾选时按原文页组织：公式和扫描页保留原页影像，不改写正文。",
      "fuse.titlePlaceholder": "讲义标题（可留空，默认用课程名）",
      "fuse.start": "开始拼接",
      "fuse.running": "正在拼接资料",
      "fuse.failed": "拼接失败",
      "fuse.done": "拼接完成：{n} 份讲义",
      "fuse.oneDone": "融合完成",
      "fuse.empty": "还没有可选的原始资料：先在「编辑课程」里上传。",
      "fuse.pages": "{n} 页",
      "practice.skippedPages": "这些页是公式/图片页，已跳过不出题：第 {pages} 页",
      "exam.unitTitle": "按资料页出卷",
      "exam.unitLede": "直接用原始资料页出选择题卷：公式/图片页会跳过并说明，分值由系统算平。",
      "exam.unitPages": "资料页，例如 1-16",
      "exam.unitStart": "按页出卷",
      "exam.unitRunning": "正在按资料页出卷",
      "exam.unitNeedPages": "先填资料页，例如 1-16",
      "exam.unitSkipped": "这些页是公式/图片页，已跳过：第 {pages} 页",
      "fuse.tiersLoading": "正在核对拼接档位…",
      "fuse.tiersOk": "拼接可用档位：{tiers}",
      "fuse.tiersNone": "这些资料的可用档位没有交集，不能拼接：请分开生成，或减少资料",
      "fuse.tiersNeedTwo": "再勾选一份资料，就能看到拼接后可用档位",
      "fuse.tiersError": "档位核对失败：{msg}",
      "course.structure": "这门课的结构",
      "course.structureNote": "课程名由讲义聚合。讲义列表放在第二个页签，不混在课程概览里。",
      "course.viewLectures": "查看讲义列表",
      "course.lecturesCount": "讲义",
      "course.pages": "页",
      "course.figures": "图",
      "course.target": "目标分",
      "course.days": "天",
      "course.today": "今天",
      "course.ended": "已结束",
      "course.noDate": "未设置考试",
      "course.setGoal": "点击设置目标",
      "course.saveGoal": "保存课程设置",
      "course.examDate": "考试日期",
      "course.targetScore": "目标分数",
      "course.name": "课程名称",
      "course.nameHint": "留空则自动取讲义名",
      "course.metaDetail": "{n} 份讲义 · {pages} 页 · {sections} 节 · {figures} 图",
      "course.academicMeta": "{credits} 学分 · {type} · 难度 {difficulty}/5",
      "course.readableStat": "份可读",
      "course.reviewStat": "份已生成",
      "course.generateHere": "生成试卷",
      "course.lectures": "讲义",
      "course.materials": "资料",
      "course.materialsEmpty": "还没有生成内容",
      "course.materialsEmptyText": "从讲义开始生成。",
      "course.sourceSaved": "资料已保存",
      "course.sourceCount": "{n} 份资料",
      "course.readSource": "阅读资料",
      "course.sourceListHint": "资料已保存；先生成讲义，或直接去内容工具提取考点。",
      "course.noLectureTitle": "还没有生成讲义",
      "course.noLectureText": "已保存 {n} 份资料。生成讲义后即可阅读、练习。",
      "course.sourceOnlyHint": "还没有生成讲义。可先保存资料，之后生成讲义；内容工具可直接提取考点。",
      "course.sourceSavedHint": "已保存的课程资料",
      "course.qualityHint": "质量报告在每张卡里",
      "course.emptyTitle": "这门课还没有讲义",
      "course.emptyText": "先到「资料」上传 PDF 或 PPT，选几页点「生成讲义」；页数多的话再挑一个档位。",
      "course.notFoundTitle": "课程不存在",
      "course.notFoundText": "回课程列表。",
      "course.notFoundCta": "回课程",
      "practice.eyebrow": "练习",
      "practice.title": "练习",
      "practice.listLede": "选讲义，再选小节。",
      "practice.pickHint": "选择课程下的讲义，进入后选小节和题数。",
      "practice.courseScope": "当前课程：{name}",
      "practice.noLectureTitle": "这门课还没有讲义",
      "practice.noLectureText": "「{name}」只有资料；先生成讲义。",
      "practice.ungrouped": "未归入课程",
      "practice.bankTitle": "题库练习",
      "practice.bankLede": "从已加入题库的原题练习；判分、错题回流和普通练习一致。",
      "practice.bankSource": "题库 · 提取原题",
      "practice.bankHint": "题库题直接抽取，不再调用模型出题。",
      "practice.bankStart": "开始题库练习",
      "practice.emptyTitle": "还没有讲义",
      "practice.emptyText": "讲义库为空。",
      "practice.lede": "只从这一节的讲义段落出题；答案在服务端判，错了自动进错题本。",
      "practice.viewQuality": "看质量报告",
      "practice.section": "小节",
      "practice.sectionPages": "（第 {range} 页）",
      "practice.count": "题量",
      "practice.count3": "3 题",
      "practice.count5": "5 题",
      "practice.source": "出处",
      "practice.sourceValue": "服务端校验，答题前不下发答案",
      "practice.start": "开始出题",
      "practice.startHint": "约 10–30 秒；失败直接报错。",
      "practice.generating": "正在按这一节出题（只依据讲义段落）…",
      "practice.noQuestions": "模型没有返回合法题目",
      "practice.generateFailed": "出题失败",
      "practice.retry": "重试",
      "practice.cancel": "取消出题",
      "practice.resumed": "已恢复上次练习：第 {i} / {n} 题",
      "practice.restart": "重新开始",
      "practice.progress": "第 {i} / {n} 题",
      "practice.sourcePage": "出处第 {n} 页",
      "practice.submit": "提交判分",
      "practice.submitHint": "判分在服务端；错了自动进错题本。",
      "practice.correct": "答对了",
      "practice.wrong": "答错了，已加入错题本",
      "practice.answerText": "正确答案：{letter}。{explanation}",
      "practice.sourceLine": "出处：第 {n} 页",
      "practice.next": "下一题",
      "practice.finish": "看结果",
      "practice.gradeFailed": "判分失败",
      "practice.doneTitle": "这一组做完了",
      "practice.doneText": "{correct} / {total} 正确（{acc}%）。",
      "practice.goReview": "去复习错题",
      "practice.wrongScheduled": "{n} 道错题已进入错题本，明天开始到期复习。",
      "practice.noWrong": "这一组没有错题。",
      "practice.goScheduled": "查看已排期",
      "practice.again": "再练一组",
      "review.eyebrow": "复习",
      "review.title": "复习",
      "review.lede": "今天只看到期错题；已排期单独列出。掌握度按真实答题记录算，0 次就是 —，不是 100%。",
      "review.doNew": "做新题",
      "review.dueToday": "今日到期",
      "review.forecast": "接下来几天：{list}",
      "review.totalWrong": "错题总数",
      "review.tabDue": "今天",
      "review.tabScheduled": "已排期",
      "review.scheduledCount": "已排期",
      "review.courseFilter": "课程筛选",
      "review.allCourses": "全部课程",
      "review.scheduledTitle": "已排期错题",
      "review.scheduledEmptyTitle": "没有已排期错题",
      "review.scheduledEmptyText": "练习中的错题会按间隔排期，到期后才进入今天。",
      "review.nextDate": "下次 {date}",
      "review.trackedSections": "有记录的章节",
      "review.dueTitle": "今日错题",
      "review.emptyTitle": "没有到期错题",
      "review.emptyText": "当前没有到期项。可以主动练一组，或查看掌握度。",
      "review.emptyCta": "做一组新题",
      "review.mastery": "掌握度",
      "review.noRecords": "还没有练习记录。做完一组题，这里才会有真实数据。",
      "review.wrongTimes": "错 {n} 次",
      "review.showAnswer": "显示答案",
      "review.remembered": "记住了",
      "review.forgot": "还没记住",
      "review.correctAnswer": "正确答案：",
      "review.sourceLine": "出处：第 {n} 页",
      "review.advance": "已推进到下一档复习",
      "review.reset": "已重置到 1 天后",
      "review.failed": "操作失败",
      "review.tableSection": "章节",
      "review.tableAttempts": "答题",
      "review.tableCorrect": "正确",
      "review.tableAccuracy": "正确率",
      "review.tableScore": "掌握分",
      "settings.eyebrow": "设置",
      "settings.title": "设置",
      "settings.lede": "本地优先：资料和练习记录都在本机；Key 只存在本机 .env。",
      "settings.appearance": "外观",
      "settings.themeMeta": "全站主题",
      "settings.light": "亮色",
      "settings.dark": "暗色",
      "settings.model": "模型",
      "settings.readonly": "只读",
      "settings.keyLocal": "本机配置",
      "settings.keyPlaceholder": "粘贴新 Key",
      "settings.keyPlaceholderSet": "已配置；留空不修改",
      "settings.saveKeys": "保存 Key",
      "settings.testKeys": "测试连接",
      "settings.keyTesting": "测试中…",
      "settings.keySaved": "Key 已保存，立即生效",
      "settings.keyNoInput": "没有填写新 Key；留空不会修改",
      "settings.keySaveFailed": "Key 保存失败",
      "settings.keyTestOk": "连接正常",
      "settings.keyNotSet": "未配置",
      "settings.keyTestFail": "连接失败",
      "settings.textGeneration": "文本生成：",
      "settings.deepseekKey": "DeepSeek Key：",
      "settings.keyNote": "Key 只写入本机用户目录的 .env；页面不回显明文。留空保存不会修改。",
      "settings.profile": "个人资料",
      "settings.profileHint": "只保存在本机，显示在左下角。",
      "settings.profileName": "你的称呼",
      "settings.saveProfile": "保存称呼",
      "settings.profileSaved": "称呼已保存",
      "user.default": "学习者",
      "settings.language": "界面语言",
      "settings.languageMeta": "导航、按钮、标签与状态",
      "settings.data": "学习数据",
      "settings.dataNote": "练习记录、错题、笔记、聊天都在这里；不会上传云端。",
      "settings.backup": "备份",
      "settings.backupMeta": "ZIP · 本机文件",
      "settings.backupNote": "下载包含数据库、聊天记录、讲义文件与原始上传件的 ZIP。恢复前先解压检查，不要覆盖正在使用的数据库。",
      "settings.backupNow": "立即备份",
      "settings.migration": "迁移状态",
      "settings.migrationMeta": "v3 只承接可信的部分",
      "settings.migratedLine": "讲义 / 阅读 / 练习 / 复习 / 笔记：",
      "settings.experimentalLine": "实验讲义生成（PDF/PPTX/DOCX + 大纲/页图）：",
      "settings.tasksLine": "提取 / 试卷 / 逻辑分析：",
      "settings.tasksLineTail": "（机器检查通过，不是人工验收）",
      "settings.auditLine": "内容检查：",
      "settings.wordLine": "讲义原生 .docx：",
      "settings.packLine": "任务 Word 导出 / 打包 / 公证：",
      "settings.wordPartial": "已接入，未在 Word 验收",
      "settings.release": "发布口径",
      "settings.releaseBody": "v3 把「机器检查全部通过」的讲义标成可读。Word 版式、资料缺口等细节以发布声明为准。",
      "task.extractPoints": "提取考点",
      "task.disclaimer": "本结果由 TermFinale 智能体生成，仅供复习参考；具体请以实际资料为准。",
      "task.print": "打印",
      "task.export": "导出 HTML",
      "task.word": "导出 Word",
      "task.pdf": "导出 PDF",
      "task.edit": "编辑",
      "task.extractPointsHint": "考点 + 页码 + 解释；每条必须有出处。",
      "task.extractNouns": "提取名词",
      "task.extractNounsHint": "术语 + 定义 + 易混词 + 页码。",
      "task.extractQuestions": "提取原题",
      "task.extractQuestionsHint": "原题逐字；支持选择题/计算题/简答题，答案/解析/页码。",
      "task.mindmap": "思维导图",
      "task.mindmapHint": "节点 8–40 个，带 parent 与页码；未覆盖全部页码会标部分覆盖。",
      "task.paper": "生成试卷",
      "task.paperHint": "原题/变式/模拟；选项唯一、答案在选项内、独立答案审计。",
      "task.analysis": "逻辑分析",
      "task.analysisHint": "主线 + 概念层级 + 因果链 + 考点映射 + 易混 + 顺序 + 出处。",
      "wb.eyebrow": "工作台",
      "wb.title": "内容工具",
      "wb.lede": "一次只做一件事：选资料、选小节、选任务，运行；结果存本机生成物。",
      "wb.new": "新建讲义（实验）",
      "wb.mode": "模式",
      "wb.modeOriginal": "原题（逐字）",
      "wb.modeVariant": "变式",
      "wb.modeMock": "模拟",
      "wb.count": "题量",
      "wb.course": "课程",
      "wb.material": "资料 / 讲义",
      "wb.chooseCourse": "请先选择课程",
      "wb.chooseMaterial": "请选择该课程的资料",
      "wb.basis": "生成依据",
      "wb.basisSection": "按讲义",
      "wb.basisPages": "按资料页",
      "wb.pagesInline": "按资料页取材，不需要先有讲义",
      "wb.modeLabel": "提取方式",
      "wb.modeOriginal2": "原题逐字（必须是资料原句）",
      "wb.modeVariant2": "变式改写（可改写，仍标出处）",
      "artifact.chipBase": "基础检查",
      "artifact.chipContent": "内容检查",
      "artifact.chipFigures": "配图",
      "artifact.chipCoverage": "讲义覆盖",
      "artifact.chipQuality": "内容质量",
      "artifact.detailPass": "通过",
      "artifact.detailRedo": "需重做",
      "artifact.detailGap": "有缺口",
      "artifact.detailUnchecked": "未检查",
      "wb.lecture": "讲义",
      "wb.section": "小节",
      "wb.noSections": "没有小节",
      "wb.run": "运行",
      "wb.addBank": "加入题库",
      "wb.addBankHint": "只加入可判分的单选题；可到课程训练里练习。",
      "wb.bankAdded": "已加入题库：{n} 道题",
      "wb.bankFailed": "加入题库失败",
      "wb.bankNoChoice": "这份提取产物没有可自动判分的单选题，不能加入题库。",
      "wb.running": "运行中…",
      "wb.runningHint": "正在生成并检查，通常 10–40 秒。",
      "wb.runHint": "生成后建议自己再核对一眼。",
      "wb.generating": "正在生成并检查…",
      "wb.outputs": "生成物",
      "wb.recent": "最近 {n} 份",
      "wb.historyHint": "历史生成物在「本课内容工具」；生成完成后会打开阅读器。",
      "wb.noOutputs": "还没有生成物。运行一次任务，这里会出现结果。",
      "wb.noDocTitle": "还没有结果",
      "wb.noDocText": "选资料和小节，点“运行”。结果会自动存到本机生成物。",
      "wb.selectFirst": "先选讲义和小节",
      "wb.taskFailed": "任务失败",
      "wb.readFailed": "读取失败",
      "wb.passToast": "机器检查通过",
      "wb.partialToast": "部分覆盖，未到 98%",
      "wb.failToast": "没通过检查，结果已保留",
      "wb.resultOf": "结果 · {task}",
      "wb.allSections": "全部资料（不遗漏）",
      "wb.pageCoverage": "页覆盖 {cited}/{total} · {pct}%",
      "wb.partialBanner": "部分覆盖，未到 98%",
      "wb.gateIssues": "检查问题",
      "wb.machinePassedNote": "不是人工验收；错答案/教学价值仍需抽检。",
      "wb.thPoint": "考点",
      "wb.thExplanation": "解释",
      "wb.thPage": "页",
      "wb.thTerm": "术语",
      "wb.thDefinition": "定义",
      "wb.thConfused": "易混",
      "wb.sourcePage": "第 {n} 页",
      "wb.sourceNo": "原题 {n}",
      "wb.answer": "答案：",
      "wb.referenceAnswer": "参考答案：",
      "wb.choice": "选择题",
      "wb.calculation": "计算题",
      "wb.shortAnswer": "简答题",
      "wb.manualTitle": "含计算/简答题",
      "wb.manualBody": "选择题已做独立答案审计；计算/简答的参考答案需人工核对，不冒充自动判对。",
      "wb.oneLine": "一句话主线",
      "wb.concepts": "概念层级",
      "wb.causal": "因果链",
      "wb.examMap": "考点映射",
      "wb.confusions": "易混",
      "wb.order": "学习顺序",
      "new.eyebrow": "新建课程",
      "new.title": "新建课程",
      "new.courseLede": "填写课程信息并上传资料，保存后进入课程。讲义、提取、练习、出卷都在课程内单独设置。",
      "new.back": "← 返回",
      "new.warningTitle": "先说清楚",
      "new.warningBody": "生成时会优先按资料大纲分段，缺页会补“补充”段，并自动识别图注；你填的重点/不考会进生成约束。试卷/答题纸会被拒绝。",
      "new.file": "资料（可多选，最多 20 份；PDF / PPT / PPTX / DOC / DOCX / 图片）",
      "new.fileHint": "支持 PDF / PPT / PPTX / DOC / DOCX / 图片，可多选。",
      "new.maxFiles": "一次最多 20 份资料。",
      "new.fileSelectTitle": "已上传 {n} 份资料",
      "new.selectAll": "全选",
      "new.fileOrderHint": "已按章节号预排，可用 ↑↓ 调整；生成严格按此顺序",
      "new.fileSelectHint": "生成时只使用勾选的资料；权重与勾选顺序一致。",
      "new.selectedCount": "已勾选 {n} 份",
      "new.noFiles": "至少勾选一份资料。",
      "new.moveUp": "上移",
      "new.moveDown": "下移",
      "new.lectureTitle": "首份讲义标题",
      "new.titlePlaceholder": "留空用文件名",
      "new.course": "课程名称",
      "new.coursePlaceholder": "例如：电路 / 有机化学",
      "new.credits": "学分",
      "new.mastery": "掌握度",
      "new.masteryHint": "你现在对这门课大概掌握到什么程度",
      "new.mastery1": "1 · 基本没学过",
      "new.mastery2": "2 · 听过但不熟",
      "new.mastery3": "3 · 一般，能跟上",
      "new.mastery4": "4 · 比较熟，想拔高",
      "new.mastery5": "5 · 很熟，只查漏",
      "new.examDate": "考试时间",
      "new.examDateHint": "可留空；填了会在讲义和计划里显示剩余天数",
      "new.courseType": "课程性质",
      "new.schoolLevel": "学校层次",
      "new.difficulty": "自设难度",
      "new.ctMajor": "专业课",
      "new.ctBasic": "专业基础课",
      "new.ctPublic": "公共基础课",
      "new.ctElective": "选修课",
      "new.slFirst": "一本",
      "new.slSecond": "二本",
      "new.slCollege": "专科高职",
      "new.slOther": "其他",
      "new.diffEasy": "容易",
      "new.diffNormal": "中等",
      "new.diffHard": "较难",
      "course.saveSettings": "保存课程设置",
      "course.settingsHint": "学分、课程性质、自设难度会保存到本机课程；学校层级使用档案层级参与权重；自设难度会进入讲义生成要求。",
      "new.target": "目标分",
      "new.days": "剩余天数",
      "new.foundation": "基础",
      "new.foundationWeak": "基础较弱",
      "new.foundationNormal": "一般",
      "new.foundationStrong": "基础较好",
      "new.multiTitle": "多资料合并（按权重）",
      "new.multiLede": "一次上传多份资料，权重 1–5；高权重资料切得更细、篇幅更长，合并成一份讲义。",
      "new.multiFiles": "资料（可多选，最多 20 份）",
      "new.weights": "每份权重（逗号分隔）",
      "new.weightsHint": "例如 5,3,1；顺序与勾选顺序一致，默认 1",
      "new.startMulti": "生成合并讲义",
      "new.keyPoints": "重点（可多行）",
      "new.keyPointsHint": "每行一个，可写权重 1–5：三要素法=5、换路定则=3；权重≥4 必须展开至少两处 + 例题/易错，只提一次会失败",
      "new.customPrompt": "补充要求 / 自定义提示词",
      "new.customPromptHint": "例：多举生活类比、公式推导慢一点、每节先给一张结构图；不违背资料事实",
      "new.excluded": "明确不考（可多行）",
      "new.excludedHint": "例：微分电路、积分电路；明确不考就不要写",
      "new.persona": "人设（只改语气）",
      "new.personaTeacher": "老师",
      "new.personaGentle": "温柔小姐姐",
      "new.personaAcademic": "学术AI",
      "new.personaSunny": "阳光小哥哥",
      "new.personaHacker": "暴力极客",
      "new.start": "创建课程并生成首讲",
      "new.startHint": "优先资料大纲，每段最多 8 页；单份 ≤159 页补齐全文；多份按顺序与权重合并。生成需要几分钟，失败会显示原因。",
      "new.saveSources": "保存课程",
      "new.saveSourcesHint": "保存课程与资料；生成在课程内进行。",
      "new.savingSources": "正在保存资料…",
      "new.saveSourcesTimeout": "保存资料超时，请重试；大文件可先压缩或拆分",
      "new.savedSources": "已保存 {n} 份资料，课程已建立",
      "new.saveSourcesFailed": "资料保存失败",
      "new.saveJobDonePages": "资料已保存，共 {pages} 页",
      "new.saveLimitsHint": "最多 20 份、单份 200MB、合计 500MB；保存会在后台继续，可以离开这一页。",
      "new.fastSave": "快速保存（扫描件先跳过识别）",
      "new.fastSaveHint": "扫描件的文字识别会推迟到第一次生成时进行；文字版 PDF 不受影响。",
      "new.saveJobResume": "上次的资料还在后台保存，继续跟进中",
      "new.jobEyebrow": "生成中",
      "new.queued": "排队",
      "new.elapsedOnly": "已用 {elapsed} · 正在估算剩余时间…",
      "new.eta": "预计还要 {eta}",
      "onboard.introLead": "先看一遍课程、训练、试卷怎么连起来，再开始设置。",
      "new.elapsedEta": "已用 {elapsed} · 预计还要 {eta}",
      "new.cancel": "取消",
      "new.uploading": "上传资料…",
      "new.uploadFailed": "上传失败（{status}）",
      "new.genFailed": "生成失败",
      "new.jobDone": "生成完成：已进讲义库",
      "new.complete": "完成",
      "new.jobDoneNote": "可以打开阅读了。",
      "new.unknownError": "未知错误",
      "new.cancelled": "已取消",
      "new.jobReadFailed": "任务状态读取失败",
      "ring.generating": "生成中",
      "ring.estimating": "处理中，请稍候",
      "ring.eta": "还剩 {eta}",
      "gen.locked": "生成中",
      "gen.navLocked": "生成进行中，请完成或取消后再切换页面",
      "new.cancelRequested": "已请求取消",
      "new.cancelFailed": "取消失败",
      "jobstep.ledger": "读取资料 / 建立页账本",
      "jobstep.segment": "生成第 {i}/{n} 段：{label}",
      "jobstep.assemble": "排版讲义 / 机器检查 / 生成 PDF",
      "jobstep.done": "完成：机器检查通过",
      "jobstep.doneShort": "完成",
      "jobstep.cancelled": "已取消",
      "jobstep.failed": "失败",
      "job.failedHint": "已有内容不会丢。",
      "job.resume": "接着生成",
      "job.resumeMissing": "没有找到可继续的进度，请重新生成。",
      "job.resumeStarted": "已从上次中断处接着做，稍等。",
      "job.failedNext": "可以稍后重试；页多的话先少选几页。",
      "notes.eyebrow": "笔记",
      "notes.title": "笔记",
      "notes.lede": "阅读器里选中一段话，点「存笔记」；这里按资料汇总。",
      "notes.goRead": "去阅读",
      "notes.count": "条笔记",
      "notes.artifacts": "份资料",
      "notes.emptyTitle": "还没有笔记",
      "notes.emptyText": "打开讲义，选中一段正文，点「存笔记」。",
      "notes.goLibrary": "去讲义库",
      "notes.viewLecture": "看讲义",
      "notes.delete": "删除",
      "notes.page": "第 {n} 页",
      "notes.deleted": "已删除",
      "notes.deleteFailed": "删除失败",
      "reader.back": "← 返回",
      "reader.pdf": "PDF 查看",
      "reader.search": "搜索",
      "reader.searchPh": "搜索讲义正文…",
      "reader.edit": "编辑",
      "reader.export": "导出",
      "reader.exportPdf": "导出 PDF",
      "reader.savePdf": "保存 PDF 到桌面",
      "reader.saveWord": "保存 Word 到桌面",
      "reader.exportWord": "导出 Word",
      "reader.exportHtml": "导出 HTML",
      "reader.print": "打印",
      "reader.editOn": "编辑模式已开启：改动只在当前页面，导出 HTML 保存副本",
      "reader.editOff": "已退出编辑",
      "reader.actionUnavailable": "阅读器尚未加载完成，请稍后再试",
      "export.saving": "正在生成并保存到桌面…",
      "export.savedTo": "已保存到：{path}",
      "export.failed": "保存失败",
      "reader.practice": "练习",
      "reader.notFound": "讲义不存在",
      "reader.notFoundText": "回讲义库。",
      "reader.backLibrary": "回讲义库",
    },
    hant: {
      "app.title": "TermFinale 學習臺",
      "brand.sub": "學習臺",
      "foot.local": "本地優先 · 資料不離開本機",
      "foot.version": "v3.0 · 學習臺",
      "nav.home": "主控台",
      "nav.guide": "說明",
      "guide.title": "說明",
      "guide.pendingTitle": "說明正在整理",
      "guide.pendingBody": "寫好後會放在這裡。在此之前，每個頁面上都有一兩句提示，照著做就能用起來。",
      "guide.firstUse": "首次使用，必讀",
      "guide.mustRead": "查看說明",
      "guide.later": "稍後",
      "guide.bannerHint": "先看完使用說明，再開始課程。",
      "settings.avatarHint": "點擊更換頭像（可選）",
      "onboard.brandKicker": "TERMFINALE · 學習工作臺",
      "onboard.brandTitle": "真·一站式<br>大學生<br>期末複習系統",
      "onboard.brandBody": "課程、講義、訓練、複習、試卷，收在一條線上。",
      "onboard.brandFoot": "本機優先　·　無需註冊　·　開發者 Lan",
      "onboard.step1": "開始",
      "onboard.step2": "使用說明",
      "onboard.step3": "建立檔案",
      "onboard.stepLabel": "第 {n} 步",
      "onboard.welcomeKicker": "WELCOME",
      "onboard.welcomeTitle": "歡迎來到<br>TermFinale",
      "onboard.welcomeLead": "不用註冊帳號。先看一遍課程、訓練、試卷怎麼連起來，再給自己起一個稱呼。",
      "onboard.start": "開始設定",
      "onboard.time": "約 2 分鐘",
      "onboard.welcomeNote": "本機優先 · 無需註冊 · 約 2 分鐘",
      "onboard.welcomeC1Title": "課程與講義",
      "onboard.welcomeC1Body": "資料按權重變成課程與可讀講義。",
      "onboard.welcomeC2Title": "訓練與複習",
      "onboard.welcomeC2Body": "從講義小節出題，錯題自動進入複習隊列。",
      "onboard.welcomeC3Title": "出卷與自測",
      "onboard.welcomeC3Body": "按真題結構生成試卷，選擇題自動判分。",
      "onboard.introKicker": "HOW IT WORKS",
      "onboard.introTitle": "一門課，一條完整閉環。",
      "onboard.row1": "資料變成課程與講義",
      "onboard.row1Body": "講義按課程歸檔，引用來源頁，保留原圖；課程、講義和學習路徑一一對應。",
      "onboard.row2": "訓練形成閉環",
      "onboard.row2Body": "新題、題庫和錯題複習共用同一套答題記錄；每次作答都會更新掌握度和複習排期。",
      "onboard.row3": "試卷與 AI 都能溯源",
      "onboard.row3Body": "正式試卷可以自測並自動判選擇題；AI 能查講義、聯網引用，錯題直接進入複習。",
      "onboard.profileKicker": "PROFILE",
      "onboard.profileTitle": "怎麼稱呼你？",
      "onboard.profileLead": "頭像可以先不填。名字會出現在首頁問候語裡，之後可在設定中修改。",
      "onboard.avatarHint": "上傳頭像（可選）",
      "onboard.nameLabel": "名字 / ID",
      "onboard.namePlaceholder": "",
      "onboard.profileNote": "頭像和名字之後都可以在設定裡修改。",
      "onboard.nameRequired": "請先填寫名字。",
      "onboard.finish": "完成，進入總控臺",
      "onboard.back": "返回",
      "onboard.continue": "繼續",
      "onboard.saveFailed": "保存失敗，請重試",
      "onboard.avatarTooBig": "頭像請小於 350KB",
      "onboard.schoolLabel": "學校",
      "onboard.schoolPlaceholder": "輸入幾個字，自動匹配學校",
      "onboard.tierLabel": "學校層級",
      "onboard.tierPlaceholder": "請選擇",
      "onboard.schoolRequired": "學校、學校層級和專業都必須填寫",
      "onboard.majorLabel": "專業",
      "settings.schoolLabel": "學校",
      "settings.schoolPlaceholder": "輸入幾個字，自動匹配學校",
      "settings.schoolTierLabel": "學校層級",
      "settings.schoolTierPlaceholder": "請選擇",
      "settings.schoolRequired": "儲存前請填寫學校、學校層級和專業",
      "settings.majorLabel": "專業",
      "onboard.title": "先走一遍這三層",
      "onboard.body": "課程是容器，講義是內容；練習和複習進入訓練，出卷是正式試卷。先打開課程，不要從這裡直接做題。",
      "onboard.dismiss": "知道了",
      "cc.continue": "繼續上次",
      "cc.start": "從這裡開始",
      "cc.startAction": "打開課程",
      "cc.review": "到期複習",
      "cc.dueCount": "{n} 道待複習",
      "cc.noneDue": "暫無到期",
      "nav.search": "打開課程與資料庫",
      "search.title": "搜尋課程與資料",
      "search.placeholder": "搜尋課程、講義標題或正文…",
      "search.hint": "輸入關鍵字開始搜尋；⌘K 開啟，Esc 關閉",
      "search.empty": "沒有找到相關內容",
      "search.loading": "搜尋中…",
      "search.results": "找到 {n} 條結果",
      "search.course": "課程",
      "search.artifact": "講義",
      "search.content": "正文",
      "nav.groupLearn": "學習",
      "nav.groupTrain": "訓練",
      "nav.groupExam": "測評",
      "nav.groupData": "資料",
      "nav.groupSystem": "系統",
      "foot.localShort": "本地",
      "nav.library": "課程",
      "nav.workbench": "內容工具",
      "nav.practice": "練習",
      "nav.review": "複習",
      "nav.notes": "筆記",
      "nav.settings": "設定",
      "nav.back": "返回",
      "nav.exam": "出卷",
      "exam.eyebrow": "試卷",
      "exam.title": "出卷",
      "exam.lede": "按真題格式或自定義藍圖出卷。",
      "exam.artifact": "知識範圍（講義）",
      "exam.subject": "科目",
      "exam.subjectAuto": "科目：{subject}（按課程資料）",
      "exam.limit": "單卷最多 50 題；超過請拆成兩份",
      "exam.longConfirm": "這份試卷題量較大，生成可能需要數分鐘，且審計會分批進行。繼續？",
      "exam.difficulty": "難度（1–5）",
      "exam.mode": "模式",
      "exam.types": "題型（逗號分隔）",
      "exam.typesHint": "留空按科目預設",
      "exam.blueprint": "自定義藍圖（可空）",
      "exam.blueprintHint": "如：選擇題 10 題 30 分；計算題 4 題 40 分；簡答題 2 題 30 分",
      "exam.references": "歷屆真題（可選，最多 3 份）",
      "exam.referencesHint": "原題改數/變式需先上傳真題。",
      "exam.chooseRefs": "選擇真題檔案",
      "exam.noRefs": "未選擇真題",
      "exam.refRequired": "原題改數/原題變式需要先上傳至少一份真題；否則請用模擬/預測模式。",
      "exam.custom": "補充要求",
      "exam.customHint": "如：多考換路定則，計算步驟要完整",
      "exam.start": "生成試卷",
      "exam.generating": "出卷 + 答案審計中，通常 1–3 分鐘…",
      "exam.failed": "出卷失敗",
      "exam.total": "總分",
      "exam.paper": "試卷",
      "exam.showAnswers": "顯示答案",
      "exam.hideAnswers": "隱藏答案",
      "exam.print": "列印",
      "exam.export": "匯出 HTML",
      "exam.word": "匯出 Word",
      "exam.saveWord": "儲存 Word 到桌面",
      "exam.savePdf": "儲存 PDF 到桌面",
      "exam.selfTest": "開始自測",
      "exam.selfTestHint": "只自動判選擇題；非選擇題需人工核對。",
      "exam.backPreview": "返回試卷預覽",
      "exam.autoOnly": "可自動判分的選擇題：{n} 道",
      "exam.noChoice": "這份試卷沒有可自動判分的單選題。",
      "exam.submit": "交卷",
      "exam.submitted": "已交卷",
      "exam.score": "得分",
      "exam.autoResult": "答對 {correct} / {auto} 道自動判分題，已答 {answered} 道。",
      "exam.autoScore": "自動判分",
      "exam.manualNote": "計算題/簡答題沒有自動判分，需按參考答案人工核對。",
      "exam.goScheduled": "錯題已進入複習",
      "exam.retry": "再考一次",
      "exam.viewPaper": "查看完整試卷",

      "exam.pdf": "列印 / 另存為 PDF",
      "exam.edit": "編輯",
      "exam.editOn": "已進入編輯模式：可直接改紙上文字；再次點編輯退出",
      "exam.editOff": "已退出編輯模式",
      "exam.figure": "配圖說明",
      "exam.answer": "答案",
      "exam.analysis": "解析",
      "exam.noDoc": "還沒有試卷。選好資料和模式生成第一份。",
      "exam.noArtifactTitle": "還沒有可出卷的講義",
      "exam.noArtifactText": "先建立一份講義，再選範圍和模式出卷。",
      "exam.afterGenerateHint": "生成完成後會在獨立閱讀器中打開；歷史試卷在課程頁的「試卷」裡。",
      "exam.modeChange": "原題改數",
      "exam.modeVariant": "原題變式",
      "exam.modeMock": "模擬",
      "exam.modePredict": "預測",
      "exam.subjectMath": "高等數學",
      "exam.subjectPhysics": "物理",
      "exam.subjectCircuit": "電路",
      "exam.subjectChem": "化學",
      "exam.subjectCS": "計算機",
      "exam.subjectBio": "生物",
      "exam.subjectMedical": "醫學",
      "exam.subjectLiberal": "文科",
      "exam.subjectOther": "其他",
      "exam.points": "分",
      "exam.source": "出處",
      "exam.paperMeta": "滿分 100 分 · 考試時間 120 分鐘 · 姓名 ______ 學號 ______ 得分 ______",
      "exam.footnote": "本試卷由 TermFinale 智慧體生成，僅供複習訓練；具體請以實際資料為準，本資料不承擔由此產生的法律責任。",
      "exam.type.choice": "選擇題",
      "exam.type.calculation": "計算題",
      "exam.type.short_answer": "簡答題",
      "exam.type.fill_blank": "填空題",
      "exam.type.proof": "證明題",
      "exam.type.experiment": "實驗題",
      "exam.type.design": "設計題",
      "exam.type.term": "名詞解釋",
      "exam.type.case": "病例分析",
      "exam.type.essay": "論述題",
      "crumb.library": "講義庫",
      "crumb.new": "新建課程",
      "crumb.course": "課程",
      "crumb.artifact": "質量報告",
      "crumb.read": "閱讀",
      "aria.menu": "選單",
      "aria.theme": "切換主題",
      "aria.langToEn": "切換到英文",
      "aria.langToZh": "切換到中文",
      "lang.zh": "簡體中文",
      "lang.hant": "繁體中文",
      "gen.lang": "生成語言",
      "gen.zh": "簡體中文",
      "gen.hant": "繁體中文",
      "gen.en": "English",
      "gen.illustrations": "AI decorative background (~$0.025/image, not precise)",
      "gen.illustrations": "AI 裝飾背景（約 $0.025/張，非精確圖）",
      "lang.en": "English",
      "lang.label": "介面語言",
      "lang.meta": "導航、按鈕、標籤與狀態",
      "ai.title": "AI 助教",
      "ai.general": "通用學習助手",
      "ai.context": "上下文",
      "ai.allLibrary": "全部課程資料",
      "ai.allPlaceholder": "問任何問題；也可以說資料名，如：環境工程原理講義裡…",
      "ai.allHint": "可以說資料名，我會檢索全部課程；也能直接聊天或點聯網。",
      "ai.placeholder": "問 AI，或直接聊天；也可以說資料名…",
      "ai.send": "傳送",
      "ai.thinking": "思考中…",
      "ai.empty": "隨時問：這段為什麼這樣？幫我出題、提煉重點，或聊任何學習問題。",
      "ai.capTitle": "我可以幫你",
      "ai.capExplain": "解釋 / 總結",
      "ai.capExplainBody": "按小節和頁碼解釋概念，也可以整段改寫。",
      "ai.capQuiz": "出題 / 變式",
      "ai.capQuizBody": "基於當前講義出單選、計算或簡答，附答案與解析。",
      "ai.capPlan": "複習計劃",
      "ai.capPlanBody": "按到期錯題和弱項排 7 天計劃，不編資料外章節。",
      "ai.capAgent": "多步任務",
      "ai.capAgentBody": "規劃工具步驟，查資料、出卷、生成講義；生成前會確認。",
      "ai.capNote": "首頁會檢索全部課程資料；你也可以直接說資料名。",
      "ai.advanced": "歷史運行 / 工作流 / 目標",
      "ai.useful": "有用",
      "ai.useless": "沒用",
      "ai.recorded": "已記錄",
      "ai.unsourced": "未引用講義，請核對",
      "ai.agentGoalEmpty": "先輸入一個目標，再點 Agent",
      "ai.wholePrompt": "先輸入整份改寫的指令",
      "ai.failed": "AI 呼叫失敗",
      "ai.note": "AI 可能出錯；資料內答案以講義出處為準。",
      "ai.quickExplain": "解釋這一節",
      "ai.quickQuiz": "出 2 道題",
      "ai.quickPlan": "7 天計劃",
      "ai.quickPoints": "提煉重點",
      "ai.agent": "執行任務",
      "ai.agentPlan": "計劃",
      "ai.agentSources": "出處頁",
      "ai.agentRun": "執行計劃",
      "ai.agentCancel": "取消任務",
      "ai.agentNeedConfirm": "需要確認",
      "ai.agentRuns": "最近任務",
      "ai.agentNoRuns": "還沒有 Agent 任務",
      "ai.agentPlanner": "規劃來源",
      "ai.agentEdit": "編輯計劃",
      "ai.agentApply": "應用修改",
      "ai.agentSave": "儲存工作流",
      "ai.agentWorkflows": "已存工作流",
      "ai.agentResume": "繼續",
      "ai.agentReplan": "重規劃",
      "ai.agentForm": "表單編輯",
      "ai.agentAddStep": "加一步",
      "ai.agentRemove": "刪",
      "ai.agentGoals": "長期目標",
      "ai.agentGoalPlan": "生成今日計劃",
      "ai.agentRunDue": "執行到期目標",
      "ai.agentSavePrompt": "給這份工作流起個名字",
      "ai.whole": "整份改寫",
      "ai.wholeRunning": "正在整份改寫並重新過 Gate/PDF…",
      "ai.wholeDone": "整份改寫草稿已生成",
      "ai.openDraft": "開啟草稿",
      "lang.note": "只切換介面文案；課程名、講義標題、小節標題和生成內容保持原語言。閱讀器內的 EN 開關獨立生效。",
      "error.request": "請求失敗（{status}）",
      "error.network": "無法連線網路或本機服務，請檢查網路後重試。",
      "error.actionFailed": "操作失敗，請重試",
      "error.title": "出錯了",
      "error.load": "載入失敗",
      "error.retry": "重試",
      "loading.default": "正在載入…",
      "notFound.title": "頁面不存在",
      "notFound.text": "回到講義庫繼續。",
      "notFound.cta": "去講義庫",
      "status.delivered": "可讀",
      "status.review": "已生成",
      "status.rejected": "需重做",
      "status.draft": "草稿",
      "status.due": "到期",
      "status.passed": "透過",
      "status.passedShort": "透過",
      "status.notPassed": "需重做",
      "status.notPassedShort": "重做",
      "status.machinePassed": "機器門禁透過",
      "status.partialCoverage": "部分覆蓋",
      "status.partialDelivery": "部分交付",
      "status.configured": "已配置",
      "status.notConfigured": "未配置",
      "status.migrated": "已遷入",
      "status.pendingReview": "已生成",
      "status.migratedManual": "已遷入 · 待人工",
      "status.readReport": "讀報告，不自動生成",
      "status.notDone": "未做",
      "unit.lecturePages": "{n} 頁講義",
      "unit.sourcePages": "{n} 頁資料",
      "unit.lectures": "{n} 份講義",
      "unit.sections": "{n} 節",
      "unit.figures": "{n} 圖",
      "unit.blocks": "{n} 塊",
      "unit.paragraphs": "{n} 段",
      "unit.pages": "{n} 頁",
      "unit.notes": "{n} 條筆記",
      "unit.sources": "{n} 份資料",
      "unit.pageN": "第 {n} 頁",
      "sep.list": "、",
      "meta.pages": "頁",
      "meta.sections": "節",
      "meta.figures": "圖",
      "meta.items": "張",
      "meta.all": "全",
      "quality.noAudit": "未做語義審計",
      "quality.noAuditFile": "沒有 coverage_audit.json，不能算內容透過",
      "quality.structureGate": "結構完整",
      "quality.content": "文字檢查",
      "quality.pdf": "版面檢查",
      "quality.language": "語言檢查",
      "quality.semantic": "語義覆蓋",
      "quality.contentMetrics": "內容品質",
      "quality.citationSupport": "說法有依據",
      "quality.termRecall": "重點詞覆蓋",
      "quality.dupSentence": "重複句",
      "quality.boilerplate": "模板句密度",
      "quality.waterTitle": "重複與套話",
      "quality.dupShort": "重複 {n}%",
      "quality.boilerShort": "模板 {n}/千字",
      "quality.imageMode": "影像版",
      "quality.imageModeDetail": "原頁影像 {images} 張 / 資料 {pages} 頁",
      "quality.metricsHint": "這些都在你本機算：每段說法能否在資料頁找到依據、重點詞有沒有講到、有沒有重複或套話。",
      "quality.fallbackNotice": "有 {n} 節模型沒寫出來，已改用資料原文排：{labels}。這幾節照樣能讀、有出處。",
      "quality.coverage": "講義覆蓋",
      "quality.coverageMet": "講到 {actual}% 的頁，目標 {target}% 以上",
      "quality.coverageNoTier": "已覆蓋 {actual}%（沒選檔位）",
      "quality.figures": "圖源",
      "quality.pass": "透過",
      "quality.fail": "未透過",
      "quality.zeroIssues": "0 條硬傷",
      "quality.hasIssues": "有硬傷",
      "quality.figureOk": "{n} 張 ok",
      "quality.figureBad": " · {n} 張異常",
      "quality.figureFallback": "圖",
      "quality.issue": "異常",
      "quality.ok": "ok",
      "artifact.notFoundTitle": "講義不存在",
      "artifact.notFoundText": "可能已被移動或刪除。",
      "artifact.backLibrary": "回講義庫",
      "artifact.eyebrow": "質量報告",
      "artifact.meta": "{pages} 頁資料 · {pdf} 頁講義 · {sections} 節 · {figures} 圖",
      "artifact.read": "開始閱讀",
      "artifact.practice": "練習",
      "artifact.backCourse": "← 回課程",
      "artifact.sections": "小節",
      "artifact.sectionsHint": "練哪一節，就從哪一節出題",
      "artifact.pageCol": "頁碼",
      "artifact.noSections": "沒有 sections.json",
      "artifact.practiceSection": "練這一節",
      "artifact.figures": "圖",
      "artifact.figuresCount": "{n} 張",
      "artifact.noFigures": "沒有圖源報告。",
      "artifact.figureSource": "來源：第 {pages} 頁 · {origin} · {status}",
      "artifact.bannerRejectedTitle": "未透過硬門禁，不能當交付物。",
      "artifact.bannerRejectedBody": "結構/內容/PDF/語言至少一項失敗；先看下面的質量報告，再決定是否重生成。",
      "artifact.bannerReviewTitle": "已生成，可以開始閱讀。",
      "artifact.bannerReviewBody": "{audit}。個別頁面可能講得簡略，建議對照原頁看重點。",
      "artifact.bannerGoodTitle": "可讀：硬門禁 + 語義審計都透過。",
      "artifact.bannerGoodBody": "{audit}；仍建議人工抽檢關鍵例題。",
      "artifact.rewrite": "整份 AI 改寫（草稿）",
      "artifact.rewriteHint": "不改原稿；生成新草稿並重新過 Gate/PDF。可對比後保留或丟棄。",
      "artifact.rewriteInstruction": "改寫要求",
      "artifact.rewritePlaceholder": "例如：講得更通俗，多舉生活例子；保留所有公式、頁碼和例題",
      "artifact.rewriteStart": "生成改寫草稿",
      "artifact.rewriteRunning": "正在逐節改寫並重新過 Gate/PDF…",
      "artifact.rewriteDraft": "草稿已生成",
      "artifact.rewriteKeep": "開啟草稿",
      "artifact.rewriteDiscard": "丟棄草稿",
      "artifact.rewriteDiff": "改寫對比",
      "artifact.acceptDraft": "一鍵替換原稿",
      "artifact.acceptHint": "會先自動備份原稿，再用草稿替換並重新過 Gate/PDF；失敗自動還原。",
      "artifact.acceptConfirm": "用這份草稿替換原稿？原稿會先備份。",
      "artifact.restore": "恢復上一版",
      "artifact.restoreConfirm": "恢復上一版備份？當前版本也會先備份。",
      "artifact.review": "人工複核",
      "artifact.reviewHint": "機器檢查不等於老師簽字；複核人/日期只存在本機。",
      "artifact.nextStep": "建議順序：先通讀一遍，再用「練習」檢查掌握度；要整卷複習就去「出卷」。",
      "artifact.runAudit": "補充檢查",
      "artifact.auditRunning": "正在逐頁複核，頁多會久一點…",
      "artifact.auditDone": "複核完成：內容通過",
      "artifact.auditGaps": "複核完成：有 {n} 頁需要補",
      "artifact.auditUnverified": "複核完成：有 {n} 頁沒跑完，可再試一次",
      "artifact.reviewer": "複核人",
      "artifact.reviewNotes": "複核意見（可空）",
      "artifact.saveReview": "儲存複核",
      "artifact.reviewed": "已人工複核",
      "artifact.constraints": "生成約束",
      "artifact.keyPoints": "重點/權重",
      "artifact.excluded": "明確不考",
      "artifact.customPrompt": "自定義提示詞",
      "artifact.missingPages": "缺失頁",
      "card.read": "閱讀",
      "card.quality": "質量報告",
      "card.practice": "練習",
      "card.practiceThis": "練這一份",
      "card.noCoverage": "未記錄頁覆蓋",
      "home.eyebrow": "今天先做一件事",
      "home.continue": "繼續閱讀",
      "home.viewQuality": "看質量報告",
      "home.dueLabel": "道錯題到期",
      "home.readableStat": "份可讀講義",
      "home.heroNote": "“可讀”表示機器檢查已通過；具體質量請在發布聲明裡說明。",
      "home.emptyEyebrow": "開始",
      "home.emptyTitle": "還沒有可讀講義",
      "home.emptyText": "先把資料生成成講義，或從課程開啟已有產物；沒有質量報告的不會標“可讀”。",
      "home.emptyCta": "去工作臺",
      "home.emptyNote": "這裡只展示已經生成好的講義。",
      "home.doNow": "現在做",
      "home.practiceEyebrow": "練習",
      "home.practiceTitle": "練一組",
      "home.practiceBody": "從當前講義的一節出 3 道單選題；服務端判分，答錯自動進錯題本。",
      "home.practiceCta": "開始練習 →",
      "home.reviewTitleDue": "{n} 道到期錯題",
      "home.reviewTitleNone": "複習隊列為空",
      "home.reviewBodyDue": "先清到期項，再開新題；錯題按 1/2/4/7 天回來。",
      "home.reviewBodyNone": "沒有到期項不是 100% 掌握；可以做新題或看掌握度。",
      "home.reviewCta": "去複習 →",
      "home.workbenchEyebrow": "工作臺",
      "home.workbenchTitle": "提取 / 試卷 / 分析",
      "home.workbenchBody": "考點、名詞、原題、試卷、邏輯分析；每類獨立 schema，過門禁才標“機器透過”。",
      "home.workbenchCta": "開啟工作臺 →",
      "home.courses": "課程",
      "home.allCourses": "全部 {n} 門",
      "home.noCourseTitle": "還沒有課程",
      "home.noCourseText": "去工作臺新建一份講義。",
      "library.eyebrow": "課程",
      "library.title": "課程",
      "library.lede": "按課程看講義、質量報告和練習；生成物不再堆在首頁。",
      "library.backHome": "回今日",
      "library.emptyTitle": "還沒有課程",
      "library.emptyText": "先新建一門課程，填入資料和課程資訊，再生成首份講義。",
      "library.cta": "新建課程",
      "course.readableBadge": "{n} 份可讀",
      "course.meta": "{n} 份講義 · {pages} 頁 · {figures} 圖",
      "course.foot": "{delivered} 可讀 · {review} 已生成",
      "course.open": "開啟課程 →",
      "course.backAll": "← 全部課程",
      "course.new": "生成講義",
      "course.newCourse": "新建課程",
      "course.edit": "編輯課程",
      "course.editDone": "完成編輯",
      "course.finishEdit": "完成編輯",
      "course.editLecture": "編輯",
      "course.editCourse": "編輯課程資料",
      "course.generateLecture": "生成講義 / 編輯資料",
      "course.deleteLecture": "刪除",
      "course.deleteLectureConfirm": "永久刪除這份資料/講義？檔案、課程記錄、練習和錯題都會一起刪掉。",
      "course.deleteLectureDone": "已永久刪除",
      "course.deleteLectureFailed": "刪除講義失敗",
      "course.editTitle": "編輯課程",
      "course.editSectionSources": "課程資料",
      "course.editSectionSourcesHint": "保留或新增生成講義的資料，並設定權重",
      "course.editSectionInfo": "課程資訊",
      "course.editSectionInfoHint": "標題、目標、基礎、難度與重點/不考約束",
      "course.editSectionGenerate": "生成設定",
      "course.editSectionGenerateHint": "只影響生成語氣和語言",
      "course.editLede": "修改課程資訊、AI 總偏好與原始資料；生成講義在課程內的講義模組進行。",
      "course.editBack": "返回課程",
      "course.editSourceLecture": "編輯哪份講義",
      "course.editAddSources": "加入新資料",
      "course.editNoSource": "沒有可重用資料",
      "course.editNoSourceBody": "請在下方加入新資料後再重新生成。",
      "course.editWeights": "資料權重（逐份，1–5）",
      "course.editExistingSources": "原有資料",
      "course.editExcludedSources": "已排除資料（{n}）",
      "course.editExcludedHint": "勾選可恢復到本次資料選擇；檔案本身沒有被刪除。",
      "course.editKeepHint": "勾選保留；取消勾選只表示從下次生成中排除，不會刪除原檔案。下方可加入新資料。",
      "course.editChooseFiles": "選擇新資料",
      "course.editNoFiles": "未選擇檔案",
      "course.editGenerate": "生成講義",
      "course.editSaveOnly": "只儲存資料與參數",
      "course.editSaveOnlyDone": "資料與參數已儲存；現有講義未重建",
      "course.editParamsDone": "參數已儲存",
      "course.editSaveOnlyFailed": "儲存資料失敗",
      "course.pendingRebuild": "資料已更新 · 待重建",
      "course.editGenerating": "重新生成中",
      "course.editDone": "新版本已生成，正在回到課程",
      "course.editFailed": "重新生成失敗",
      "course.archive": "刪除課程",
      "course.archiveNote": "刪除會永久移除這門課的使用者資料、講義、試卷、題庫、錯題和聊天記錄；內置/交付資料不會動。",
      "course.archiveConfirm": "永久刪除這門課程？使用者資料、講義、試卷、題庫、錯題和聊天記錄都會刪除；內置/交付資料保留。",
      "course.deleted": "課程已刪除：{n} 份使用者資料已移除",
      "course.deleteFailed": "刪除課程失敗",
      "course.overview": "課程概覽",
      "course.settings": "設定",
      "doc.delete": "刪除",
      "doc.rename": "重新命名",
      "doc.back": "返回內容工具",
      "doc.unknownSource": "未知講義",
      "doc.hits": "找到 {n} 處",
      "doc.renamePrompt": "輸入新的試卷標題",
      "doc.renamed": "已重新命名",
      "doc.renameFailed": "重新命名失敗",
      "doc.deleteConfirm": "刪除這份產物？此操作不可撤銷。",
      "doc.deleted": "已刪除",
      "doc.deleteFailed": "刪除失敗",
      "course.training": "練習",
      "course.trainingNote": "只統計這門課的練習與到期錯題。",
      "course.newPractice": "新題練習",
      "course.newPracticeNote": "選擇一份講義，進入後選小節和題數。",
      "course.practice": "練習",
      "course.noLectures": "這門課還沒有講義。",
      "course.review": "錯題複習",
      "course.reviewNote": "到期與已排期都按這門課過濾。",
      "course.openReview": "打開本課複習",
      "course.papers": "出卷",
      "course.papersNote": "只收正式試卷。",
      "course.newPaper": "新建試卷",
      "course.cleanPapers": "清理重複試卷 · {n}",
      "course.cleanPapersConfirm": "刪除同名舊試卷，只保留最新一份？此操作不可撤銷。",
      "course.cleanPapersDone": "已清理 {n} 份重複試卷",
      "course.paperAll": "全部 · {n}",
      "course.paperValidated": "通過 · {n}",
      "course.paperReview": "未通過 · {n}",
      "course.selfTested": "已自測 {score}/{total}",
      "course.paper": "試卷",
      "course.noPapers": "還沒有試卷",
      "course.noPapersNote": "從講義生成一份試卷。",
      "course.tools": "提取",
      "course.bankPractice": "題庫練習",
      "bank.title": "題庫",
      "bank.eyebrow": "BANK",
      "bank.lede": "這裡只放已加入題庫的原題；刪除後會同時移除相關答題記錄和錯題。",
      "bank.practice": "開始題庫練習",
      "bank.manage": "管理題庫",
      "bank.count": "{n} 道題",
      "bank.answer": "答案 {x}",
      "bank.emptyTitle": "題庫為空",
      "bank.emptyText": "先到內容工具提取原題，再加入題庫。",
      "bank.deleteConfirm": "從題庫刪除這道題？相關答題記錄和錯題也會移除。",
      "course.bankNote": "從原題提取產物加入題庫，再從本課講義做題。",
      "course.bankEmpty": "還沒有題庫題。到內容工具執行「提取原題」，再把產物加入題庫。",
      "course.bankCount": "{n} 道",
      "course.toolsNote": "從講義生成考點、術語、原題、導圖或邏輯分析。",
      "course.openTools": "打開內容工具",
      "course.noTools": "還沒有提取結果",
      "course.noToolsNote": "選講義，執行一次提取。",

      "course.scopeTools": "本課內容工具",
      "course.lecturesTab": "講義",
      "course.structure": "這門課的結構",
      "course.structureNote": "課程名由講義聚合。講義列表放在第二個頁籤，不混在課程概覽裡。",
      "course.viewLectures": "查看講義列表",
      "course.lecturesCount": "講義",
      "course.pages": "頁",
      "course.figures": "圖",
      "course.ended": "已結束",
      "course.target": "目標分",
      "course.days": "天",
      "course.today": "今天",
      "course.noDate": "未設定考試",
      "course.setGoal": "點擊設定目標",
      "course.saveGoal": "保存課程設定",
      "course.examDate": "考試日期",
      "course.targetScore": "目標分數",
      "course.name": "課程名稱",
      "course.nameHint": "留空則自動取講義名",
      "course.metaDetail": "{n} 份講義 · {pages} 頁 · {sections} 節 · {figures} 圖",
      "course.academicMeta": "{credits} 學分 · {type} · 難度 {difficulty}/5",
      "course.saveSettings": "保存課程設定",
      "course.settingsHint": "學分、課程性質、自設難度會儲存到本機課程；學校層級使用檔案層級參與權重；自設難度會進入講義生成要求。",
      "course.readableStat": "份可讀",
      "course.reviewStat": "份已生成",
      "course.generateHere": "生成試卷",
      "course.lectures": "講義",
      "course.materials": "資料",
      "course.materialsEmpty": "還沒有生成內容",
      "course.materialsEmptyText": "從講義開始生成。",
      "course.sourceSaved": "資料已儲存",
      "course.sourceCount": "{n} 份資料",
      "course.readSource": "閱讀資料",
      "course.sourceListHint": "資料已儲存；先生成講義，或直接去內容工具提取考點。",
      "course.noLectureTitle": "還沒有生成講義",
      "course.noLectureText": "已儲存 {n} 份資料。生成講義後即可閱讀、練習。",
      "course.sourceOnlyHint": "還沒有生成講義。可先儲存資料，之後生成講義；內容工具可直接提取考點。",
      "course.sourceSavedHint": "已儲存的課程資料",
      "course.qualityHint": "質量報告在每張卡里",
      "course.emptyTitle": "這門課還沒有講義",
      "course.emptyText": "先到「資料」上傳 PDF 或 PPT，選幾頁點「生成講義」；頁數多的話再挑一個檔位。",
      "course.notFoundTitle": "課程不存在",
      "course.notFoundText": "回課程列表。",
      "course.notFoundCta": "回課程",
      "practice.eyebrow": "練習",
      "practice.title": "練習",
      "practice.listLede": "先選一份講義，再選小節。",
      "practice.pickHint": "選擇課程下的講義，進入後選小節和題數。",
      "practice.courseScope": "目前課程：{name}",
      "practice.noLectureTitle": "這門課還沒有講義",
      "practice.noLectureText": "「{name}」只有資料；先生成講義。",
      "practice.ungrouped": "未歸入課程",
      "practice.bankTitle": "題庫練習",
      "practice.bankLede": "從已加入題庫的原題練習；判分、錯題回流和普通練習一致。",
      "practice.bankSource": "題庫 · 提取原題",
      "practice.bankHint": "題庫題直接抽取，不再呼叫模型出題。",
      "practice.bankStart": "開始題庫練習",
      "practice.emptyTitle": "還沒有講義",
      "practice.emptyText": "講義庫為空。",
      "practice.lede": "只從這一節的講義段落出題；答案在服務端判，錯了自動進錯題本。",
      "practice.viewQuality": "看質量報告",
      "practice.section": "小節",
      "practice.sectionPages": "（第 {range} 頁）",
      "practice.count": "題量",
      "practice.count3": "3 題",
      "practice.count5": "5 題",
      "practice.source": "出處",
      "practice.sourceValue": "服務端校驗，答題前不下發答案",
      "practice.start": "開始出題",
      "practice.startHint": "約 10–30 秒；失敗直接報錯。",
      "practice.generating": "正在按這一節出題（只依據講義段落）…",
      "practice.noQuestions": "模型沒有返回合法題目",
      "practice.generateFailed": "出題失敗",
      "practice.retry": "重試",
      "practice.cancel": "取消出題",
      "practice.resumed": "已恢復上次練習：第 {i} / {n} 題",
      "practice.restart": "重新開始",
      "practice.progress": "第 {i} / {n} 題",
      "practice.sourcePage": "出處第 {n} 頁",
      "practice.submit": "提交判分",
      "practice.submitHint": "判分在服務端；錯了自動進錯題本。",
      "practice.correct": "答對了",
      "practice.wrong": "答錯了，已加入錯題本",
      "practice.answerText": "正確答案：{letter}。{explanation}",
      "practice.sourceLine": "出處：第 {n} 頁",
      "practice.next": "下一題",
      "practice.finish": "看結果",
      "practice.gradeFailed": "判分失敗",
      "practice.doneTitle": "這一組做完了",
      "practice.doneText": "{correct} / {total} 正確（{acc}%）。錯題已進錯題本，按 1/2/4/7 天覆習。",
      "practice.goReview": "去複習錯題",
      "practice.wrongScheduled": "{n} 道錯題已進入錯題本，明天開始到期複習。",
      "practice.noWrong": "這一組沒有錯題。",
      "practice.goScheduled": "查看已排期",
      "practice.again": "再練一組",
      "review.eyebrow": "複習",
      "review.title": "複習",
      "review.lede": "今天只看到期錯題；已排期單獨列出。掌握度按真實答題記錄算，0 次就是 —，不是 100%。",
      "review.doNew": "做新題",
      "review.dueToday": "今日到期",
      "review.forecast": "接下來幾天：{list}",
      "review.totalWrong": "錯題總數",
      "review.tabDue": "今天",
      "review.tabScheduled": "已排期",
      "review.scheduledCount": "已排期",
      "review.courseFilter": "課程篩選",
      "review.allCourses": "全部課程",
      "review.scheduledTitle": "已排期錯題",
      "review.scheduledEmptyTitle": "沒有已排期錯題",
      "review.scheduledEmptyText": "練習中的錯題會按間隔排期，到期後才進入今天。",
      "review.nextDate": "下次 {date}",
      "review.trackedSections": "有記錄的章節",
      "review.dueTitle": "今日錯題",
      "review.emptyTitle": "沒有到期錯題",
      "review.emptyText": "目前沒有到期項。可以主動練一組，或查看掌握度。",
      "review.emptyCta": "做一組新題",
      "review.mastery": "掌握度",
      "review.noRecords": "還沒有練習記錄。做完一組題，這裡才會有真實資料。",
      "review.wrongTimes": "錯 {n} 次",
      "review.showAnswer": "顯示答案",
      "review.remembered": "記住了",
      "review.forgot": "還沒記住",
      "review.correctAnswer": "正確答案：",
      "review.sourceLine": "出處：第 {n} 頁",
      "review.advance": "已推進到下一檔複習",
      "review.reset": "已重置到 1 天后",
      "review.failed": "操作失敗",
      "review.tableSection": "章節",
      "review.tableAttempts": "答題",
      "review.tableCorrect": "正確",
      "review.tableAccuracy": "正確率",
      "review.tableScore": "掌握分",
      "settings.eyebrow": "設定",
      "settings.title": "設定",
      "settings.lede": "本地優先：資料和練習記錄都在本機；Key 只存在本機 .env。",
      "settings.appearance": "外觀",
      "settings.themeMeta": "全站主題",
      "settings.light": "亮色",
      "settings.dark": "暗色",
      "settings.model": "模型",
      "settings.readonly": "只讀",
      "settings.keyLocal": "本機設定",
      "settings.keyPlaceholder": "貼上新 Key",
      "settings.keyPlaceholderSet": "已設定；留空不修改",
      "settings.saveKeys": "儲存 Key",
      "settings.testKeys": "測試連線",
      "settings.keyTesting": "測試中…",
      "settings.keySaved": "Key 已儲存，立即生效",
      "settings.keyNoInput": "沒有填寫新 Key；留空不會修改",
      "settings.keySaveFailed": "Key 儲存失敗",
      "settings.keyTestOk": "連線正常",
      "settings.keyNotSet": "未設定",
      "settings.keyTestFail": "連線失敗",
      "settings.textGeneration": "文字生成：",
      "settings.deepseekKey": "DeepSeek Key：",
      "settings.keyNote": "Key 只寫入本機使用者目錄的 .env；頁面不回顯明文。留空儲存不會修改。",
      "settings.profile": "個人資料",
      "settings.profileHint": "只儲存在本機，顯示在左下角。",
      "settings.profileName": "你的稱呼",
      "settings.saveProfile": "儲存稱呼",
      "settings.profileSaved": "稱呼已儲存",
      "user.default": "學習者",
      "settings.language": "介面語言",
      "settings.languageMeta": "導航、按鈕、標籤與狀態",
      "settings.data": "學習資料",
      "settings.dataNote": "練習記錄、錯題、筆記、聊天都在這裡；不會上傳雲端。",
      "settings.backup": "備份",
      "settings.backupMeta": "ZIP · 本機檔案",
      "settings.backupNote": "下載包含資料庫、聊天記錄、講義檔案與原始上傳件的 ZIP。還原前先解壓檢查，不要覆蓋正在使用的資料庫。",
      "settings.backupNow": "立即備份",
      "settings.migration": "遷移狀態",
      "settings.migrationMeta": "v3 只承接可信的部分",
      "settings.migratedLine": "講義 / 閱讀 / 練習 / 複習 / 筆記：",
      "settings.experimentalLine": "實驗講義生成（PDF/PPTX/DOCX + 大綱/頁圖）：",
      "settings.tasksLine": "提取 / 試卷 / 邏輯分析：",
      "settings.tasksLineTail": "（機器門禁透過，不是人工驗收）",
      "settings.auditLine": "語義審計：",
      "settings.wordLine": "講義原生 .docx：",
      "settings.packLine": "任務 Word 匯出 / 打包 / 公證：",
      "settings.wordPartial": "已接入，未在 Word 驗收",
      "settings.release": "釋出口徑",
      "settings.releaseBody": "v3 只把“Gate + 內容/PDF/語言 + 語義審計 0 partial / 0 missing”的講義標成可讀。Word 版式、人工複核、3.5 資料缺口仍未完成；不能因為頁面變好就宣佈釋出。",
      "task.extractPoints": "提取考點",
      "task.disclaimer": "本結果由 TermFinale 智慧體生成，僅供複習參考；具體請以實際資料為準。",
      "task.print": "列印",
      "task.export": "匯出 HTML",
      "task.word": "匯出 Word",
      "task.pdf": "匯出 PDF",
      "task.edit": "編輯",
      "task.extractPointsHint": "考點 + 頁碼 + 解釋；每條必須有出處。",
      "task.extractNouns": "提取名詞",
      "task.extractNounsHint": "術語 + 定義 + 易混詞 + 頁碼。",
      "task.extractQuestions": "提取原題",
      "task.extractQuestionsHint": "原題逐字；支援選擇題/計算題/簡答題，答案/解析/頁碼。",
      "task.mindmap": "思維導圖",
      "task.mindmapHint": "節點 8–40 個，帶 parent 與頁碼；未覆蓋全部頁碼會標部分覆蓋。",
      "task.paper": "生成試卷",
      "task.paperHint": "原題/變式/模擬；選項唯一、答案在選項內、獨立答案審計。",
      "task.analysis": "邏輯分析",
      "task.analysisHint": "主線 + 概念層級 + 因果鏈 + 考點對映 + 易混 + 順序 + 出處。",
      "wb.eyebrow": "工作臺",
      "wb.title": "內容工具",
      "wb.lede": "一次只做一件事：選資料、選小節、選任務，執行；結果存本機生成物。",
      "wb.new": "新建講義（實驗）",
      "wb.mode": "模式",
      "wb.modeOriginal": "原題（逐字）",
      "wb.modeVariant": "變式",
      "wb.modeMock": "模擬",
      "wb.count": "題量",
      "wb.course": "課程",
      "wb.material": "資料 / 講義",
      "wb.chooseCourse": "請先選擇課程",
      "wb.chooseMaterial": "請選擇該課程的資料",
      "wb.basis": "生成依據",
      "wb.basisSection": "按講義",
      "wb.basisPages": "按資料頁",
      "wb.pagesInline": "按資料頁取材，不需要先有講義",
      "wb.modeLabel": "提取方式",
      "wb.modeOriginal2": "原題逐字（必須是資料原句）",
      "wb.modeVariant2": "變式改寫（可改寫，仍標出處）",
      "artifact.chipBase": "基礎檢查",
      "artifact.chipContent": "內容檢查",
      "artifact.chipFigures": "配圖",
      "artifact.chipCoverage": "講義覆蓋",
      "artifact.chipQuality": "內容質量",
      "artifact.detailPass": "通過",
      "artifact.detailRedo": "需重做",
      "artifact.detailGap": "有缺口",
      "artifact.detailUnchecked": "未檢查",
      "wb.lecture": "講義",
      "wb.section": "小節",
      "wb.noSections": "沒有小節",
      "wb.run": "執行",
      "wb.addBank": "加入題庫",
      "wb.addBankHint": "只加入可判分的單選題；可到課程訓練裡練習。",
      "wb.bankAdded": "已加入題庫：{n} 道題",
      "wb.bankFailed": "加入題庫失敗",
      "wb.bankNoChoice": "這份提取產物沒有可自動判分的單選題，不能加入題庫。",
      "wb.running": "執行中…",
      "wb.runningHint": "模型正在生成並過門禁，通常 10–40 秒。",
      "wb.runHint": "生成後仍需人工複核。",
      "wb.generating": "生成 + 門禁檢查中…",
      "wb.outputs": "生成物",
      "wb.recent": "最近 {n} 份",
      "wb.historyHint": "歷史生成物在「本課內容工具」；生成完成後會打開閱讀器。",
      "wb.noOutputs": "還沒有生成物。執行一次任務，這裡會出現結果。",
      "wb.noDocTitle": "還沒有結果",
      "wb.noDocText": "選資料和小節，點“執行”。結果會自動存到本機生成物。",
      "wb.selectFirst": "先選講義和小節",
      "wb.taskFailed": "任務失敗",
      "wb.readFailed": "讀取失敗",
      "wb.passToast": "機器門禁透過",
      "wb.partialToast": "部分覆蓋，未到 98%",
      "wb.failToast": "未透過門禁，結果已保留",
      "wb.resultOf": "結果 · {task}",
      "wb.allSections": "全部資料（不遺漏）",
      "wb.pageCoverage": "頁覆蓋 {cited}/{total} · {pct}%",
      "wb.partialBanner": "部分覆蓋，未到 98%",
      "wb.gateIssues": "門禁問題",
      "wb.machinePassedNote": "不是人工驗收；錯答案/教學價值仍需抽檢。",
      "wb.thPoint": "考點",
      "wb.thExplanation": "解釋",
      "wb.thPage": "頁",
      "wb.thTerm": "術語",
      "wb.thDefinition": "定義",
      "wb.thConfused": "易混",
      "wb.sourcePage": "第 {n} 頁",
      "wb.sourceNo": "原題 {n}",
      "wb.answer": "答案：",
      "wb.referenceAnswer": "參考答案：",
      "wb.choice": "選擇題",
      "wb.calculation": "計算題",
      "wb.shortAnswer": "簡答題",
      "wb.manualTitle": "含計算/簡答題",
      "wb.manualBody": "選擇題已做獨立答案審計；計算/簡答的參考答案需人工核對，不冒充自動判對。",
      "wb.oneLine": "一句話主線",
      "wb.concepts": "概念層級",
      "wb.causal": "因果鏈",
      "wb.examMap": "考點對映",
      "wb.confusions": "易混",
      "wb.order": "學習順序",
      "new.eyebrow": "新建課程",
      "new.title": "新建課程",
      "new.courseLede": "填寫課程資訊並上傳資料，儲存後進入課程。講義、提取、練習、出卷都在課程內單獨設定。",
      "new.back": "← 返回",
      "new.warningTitle": "先說清楚",
      "new.warningBody": "生成時會優先按資料大綱分段，缺頁會補“補充”段，並自動識別圖注；你填的重點/不考會進生成約束。試卷/答題紙會被拒絕。",
      "new.file": "資料（可多選，最多 20 份；PDF / PPT / PPTX / DOC / DOCX / 圖片）",
      "new.fileHint": "支援 PDF / PPT / PPTX / DOC / DOCX / 圖片，可多選。",
      "new.maxFiles": "一次最多 20 份資料。",
      "new.fileSelectTitle": "已上傳 {n} 份資料",
      "new.selectAll": "全選",
      "new.fileOrderHint": "已按章節號預排，可用 ↑↓ 調整；生成嚴格按此順序",
      "new.fileSelectHint": "生成時只使用勾選的資料；權重與勾選順序一致。",
      "new.selectedCount": "已勾選 {n} 份",
      "new.noFiles": "至少勾選一份資料。",
      "new.moveUp": "上移",
      "new.moveDown": "下移",
      "new.lectureTitle": "首份講義標題",
      "new.titlePlaceholder": "留空用檔名",
      "new.course": "課程名稱",
      "new.coursePlaceholder": "例如：電路 / 有機化學",
      "new.credits": "學分",
      "new.courseType": "課程性質",
      "new.schoolLevel": "學校層次",
      "new.difficulty": "自設難度",
      "new.ctMajor": "專業課",
      "new.ctBasic": "專業基礎課",
      "new.ctPublic": "公共基礎課",
      "new.ctElective": "選修課",
      "new.slFirst": "一本",
      "new.slSecond": "二本",
      "new.slCollege": "專科高職",
      "new.slOther": "其他",
      "new.diffEasy": "容易",
      "new.diffNormal": "中等",
      "new.diffHard": "較難",
      "new.target": "目標分",
      "new.days": "剩餘天數",
      "new.foundation": "基礎",
      "new.foundationWeak": "基礎較弱",
      "new.foundationNormal": "一般",
      "new.foundationStrong": "基礎較好",
      "new.multiTitle": "多資料合併（按權重）",
      "new.multiLede": "一次上傳多份資料，權重 1–5；高權重資料切得更細、篇幅更長，合併成一份講義。",
      "new.multiFiles": "資料（可多選，最多 20 份）",
      "new.weights": "每份權重（逗號分隔）",
      "new.weightsHint": "例如 5,3,1；順序與勾選順序一致，預設 1",
      "new.startMulti": "生成合並講義",
      "new.keyPoints": "重點（可多行）",
      "new.keyPointsHint": "每行一個，可寫權重 1–5：三要素法=5、換路定則=3；權重≥4 必須展開至少兩處 + 例題/易錯，只提一次會失敗",
      "new.customPrompt": "補充要求 / 自定義提示詞",
      "new.customPromptHint": "例：多舉生活類比、公式推導慢一點、每節先給一張結構圖；不違背資料事實",
      "new.excluded": "明確不考（可多行）",
      "new.excludedHint": "例：微分電路、積分電路；明確不考就不要寫",
      "new.persona": "人設（只改語氣）",
      "new.personaTeacher": "老師",
      "new.personaGentle": "溫柔小姐姐",
      "new.personaAcademic": "學術AI",
      "new.personaSunny": "陽光小哥哥",
      "new.personaHacker": "暴力極客",
      "new.start": "建立課程並生成首講",
      "new.startHint": "優先資料大綱，每段最多 8 頁；單份 ≤159 頁補齊全文；多份按順序與權重合併。生成需要幾分鐘，失敗會顯示原因。",
      "new.saveSources": "儲存課程",
      "new.saveSourcesHint": "儲存課程與資料；生成在課程內進行。",
      "new.savingSources": "正在儲存資料…",
      "new.saveSourcesTimeout": "儲存資料逾時，請重試；大檔案可先壓縮或拆分",
      "new.savedSources": "已儲存 {n} 份資料，課程已建立",
      "new.saveSourcesFailed": "資料儲存失敗",
      "new.saveJobDonePages": "資料已儲存，共 {pages} 頁",
      "new.saveLimitsHint": "最多 20 份、單份 200MB、合計 500MB；儲存會在後台繼續，可以離開這一頁。",
      "new.fastSave": "快速儲存（掃描件先跳過識別）",
      "new.fastSaveHint": "掃描件的文字識別會推遲到第一次生成時進行；文字版 PDF 不受影響。",
      "new.saveJobResume": "上次的資料還在後台儲存，繼續跟進中",
      "new.jobEyebrow": "生成中",
      "new.queued": "排隊",
      "new.elapsedOnly": "已用 {elapsed} · 正在估算剩餘時間…",
      "new.eta": "預計還要 {eta}",
      "onboard.introLead": "先看一遍課程、訓練、試卷怎麼連起來，再開始設定。",
      "new.elapsedEta": "已用 {elapsed} · 預計還要 {eta}",
      "new.cancel": "取消",
      "new.uploading": "上傳資料…",
      "new.uploadFailed": "上傳失敗（{status}）",
      "new.genFailed": "生成失敗",
      "new.jobDone": "生成完成：已進講義庫，內容複核還沒做",
      "new.complete": "完成",
      "new.jobDoneNote": "可以打開閱讀了。",
      "new.unknownError": "未知錯誤",
      "new.cancelled": "已取消",
      "new.jobReadFailed": "任務狀態讀取失敗",
      "ring.generating": "生成中",
      "ring.estimating": "處理中，請稍候",
      "ring.eta": "還剩 {eta}",
      "gen.locked": "生成中",
      "gen.navLocked": "生成進行中，請完成或取消後再切換頁面",
      "new.cancelRequested": "已請求取消",
      "new.cancelFailed": "取消失敗",
      "jobstep.ledger": "讀取資料 / 建立頁賬本",
      "jobstep.segment": "生成第 {i}/{n} 段：{label}",
      "jobstep.assemble": "裝配講義 / 跑 Gate / 生成 PDF",
      "jobstep.done": "完成：Gate 透過，等待逐頁複核",
      "jobstep.doneShort": "完成",
      "jobstep.cancelled": "已取消",
      "jobstep.failed": "失敗",
      "notes.eyebrow": "筆記",
      "notes.title": "筆記",
      "notes.lede": "閱讀器裡選中一段話，點「存筆記」；這裡按資料彙總。",
      "notes.goRead": "去閱讀",
      "notes.count": "條筆記",
      "notes.artifacts": "份資料",
      "notes.emptyTitle": "還沒有筆記",
      "notes.emptyText": "開啟講義，選中一段正文，點「存筆記」。",
      "notes.goLibrary": "去講義庫",
      "notes.viewLecture": "看講義",
      "notes.delete": "刪除",
      "notes.page": "第 {n} 頁",
      "notes.deleted": "已刪除",
      "notes.deleteFailed": "刪除失敗",
      "reader.back": "← 返回",
      "reader.pdf": "PDF 檢視",
      "reader.search": "搜尋",
      "reader.searchPh": "搜尋講義正文…",
      "reader.edit": "編輯",
      "reader.export": "匯出",
      "reader.exportPdf": "匯出 PDF",
      "reader.savePdf": "儲存 PDF 到桌面",
      "reader.saveWord": "儲存 Word 到桌面",
      "reader.exportWord": "匯出 Word",
      "reader.exportHtml": "匯出 HTML",
      "reader.print": "列印",
      "reader.editOn": "編輯模式已開啟：改動只在目前頁面，匯出 HTML 儲存副本",
      "reader.editOff": "已退出編輯",
      "reader.actionUnavailable": "閱讀器尚未載入完成，請稍後再試",
      "export.saving": "正在生成並儲存到桌面…",
      "export.savedTo": "已儲存到：{path}",
      "export.failed": "儲存失敗",
      "reader.practice": "練習",
      "reader.notFound": "講義不存在",
      "reader.notFoundText": "回講義庫。",
      "reader.backLibrary": "回講義庫",
    },
    en: {
      "ai.title": "AI tutor",
      "ai.general": "General study assistant",
      "ai.context": "Context",
      "ai.allLibrary": "All course materials",
      "ai.allPlaceholder": "Ask anything, or name a material: e.g. in the environmental engineering notes…",
      "ai.allHint": "Name a material to search all courses; chat normally or switch on web search.",
      "ai.placeholder": "Ask anything, or name a material…",
      "ai.send": "Send",
      "ai.thinking": "Thinking…",
      "ai.empty": "Ask anything: why does this work, quiz me, extract key points, or any study question.",
      "ai.failed": "AI request failed",
      "ai.note": "AI can be wrong; answers grounded in the lecture should be checked against the cited pages.",
      "ai.quickExplain": "Explain this section",
      "ai.quickQuiz": "Make 2 questions",
      "ai.quickPlan": "7-day plan",
      "ai.quickPoints": "Key points",
      "ai.agent": "Agent",
      "ai.agentPlan": "Plan",
      "ai.agentSources": "Sources",
      "ai.agentRun": "Run plan",
      "ai.agentCancel": "Cancel",
      "ai.agentNeedConfirm": "Needs confirmation",
      "ai.agentRuns": "Recent runs",
      "ai.agentNoRuns": "No agent runs yet",
      "ai.agentPlanner": "Planner",
      "ai.agentEdit": "Edit plan",
      "ai.agentApply": "Apply",
      "ai.agentSave": "Save workflow",
      "ai.agentWorkflows": "Workflows",
      "ai.agentResume": "Resume",
      "ai.agentReplan": "Replan",
      "ai.agentForm": "Form edit",
      "ai.agentAddStep": "Add step",
      "ai.agentRemove": "Remove",
      "ai.agentGoals": "Goals",
      "ai.agentGoalPlan": "Plan today",
      "ai.agentRunDue": "Run due goals",
      "ai.agentSavePrompt": "Name this workflow",
      "ai.whole": "Rewrite whole lecture",
      "ai.wholeRunning": "Rewriting and re-running Gate/PDF…",
      "ai.wholeDone": "Rewrite draft created",
      "ai.openDraft": "Open draft",
      "ai.capTitle": "What I can do",
      "ai.capExplain": "Explain / summarise",
      "ai.capExplainBody": "Concepts with section and page, or a whole paragraph rewrite.",
      "ai.capQuiz": "Quiz / variants",
      "ai.capQuizBody": "Choice, calculation or short answer from this lecture, with answers.",
      "ai.capPlan": "Study plan",
      "ai.capPlanBody": "A 7-day plan from due mistakes and weak topics, without invented sections.",
      "ai.capAgent": "Multi-step work",
      "ai.capAgentBody": "Plan tools, search, build papers or lectures; generation asks first.",
      "ai.capNote": "The home assistant searches all course materials; name one to narrow it.",
      "ai.advanced": "History / workflows / goals",
      "ai.useful": "Useful",
      "ai.useless": "Not useful",
      "ai.recorded": "Recorded",
      "ai.unsourced": "No lecture citation; verify before use",
      "ai.agentGoalEmpty": "Enter a goal before starting the agent",
      "ai.wholePrompt": "Enter a rewrite instruction first",

      "app.title": "TermFinale Study Desk",
      "brand.sub": "Study Desk",
      "foot.local": "Local-first · data stays on this machine",
      "foot.version": "v3.0 · Study Desk",
      "nav.home": "Control",
      "nav.guide": "Guide",
      "guide.title": "Guide",
      "guide.pendingTitle": "The guide is being written",
      "guide.pendingBody": "It will live here once ready. Until then, each page has a short hint you can follow.",
      "guide.firstUse": "First use — required reading",
      "guide.mustRead": "Read the guide",
      "guide.later": "Later",
      "guide.bannerHint": "Read this before your first course.",
      "settings.avatarHint": "Click to change avatar (optional)",
      "onboard.brandKicker": "TERMFINALE · STUDY WORKSPACE",
      "onboard.brandTitle": "A true all-in-one<br>final-exam review<br>system for students",
      "onboard.brandBody": "Courses, lectures, practice, review and papers, on one line.",
      "onboard.brandFoot": "Local first · no account · developer Lan",
      "onboard.step1": "Start",
      "onboard.step2": "How it works",
      "onboard.step3": "Profile",
      "onboard.stepLabel": "Step {n}",
      "onboard.welcomeKicker": "WELCOME",
      "onboard.welcomeTitle": "Welcome to<br>TermFinale",
      "onboard.welcomeLead": "No account needed. See how courses, training and papers connect, then choose a name.",
      "onboard.start": "Get started",
      "onboard.time": "About 2 minutes",
      "onboard.welcomeNote": "Local-first · no sign-up · about 2 minutes",
      "onboard.welcomeC1Title": "Courses & lectures",
      "onboard.welcomeC1Body": "Sources become a course and readable lectures by weight.",
      "onboard.welcomeC2Title": "Practice & review",
      "onboard.welcomeC2Body": "Generate from sections; mistakes return to review.",
      "onboard.welcomeC3Title": "Papers & self-test",
      "onboard.welcomeC3Body": "Build papers from a past-paper structure; auto-grade choices.",
      "onboard.introKicker": "HOW IT WORKS",
      "onboard.introTitle": "One course, one complete loop.",
      "onboard.row1": "Material becomes courses and lectures",
      "onboard.row1Body": "Lectures are filed under a course, cite source pages and keep original figures; the learning path stays traceable.",
      "onboard.row2": "Practice closes the loop",
      "onboard.row2Body": "New practice, question-bank practice and mistake review share one attempt record; every answer updates mastery and scheduling.",
      "onboard.row3": "Papers and AI stay traceable",
      "onboard.row3Body": "Formal papers can be taken with auto-graded choice questions; AI searches lectures or the web and sends mistakes to review.",
      "onboard.profileKicker": "PROFILE",
      "onboard.profileTitle": "What should we call you?",
      "onboard.profileLead": "Avatar is optional. Your name becomes the home greeting and can be changed later.",
      "onboard.avatarHint": "Upload avatar (optional)",
      "onboard.nameLabel": "Name / ID",
      "onboard.namePlaceholder": "",
      "onboard.profileNote": "You can change the avatar and name later in Settings.",
      "onboard.nameRequired": "Enter a name first.",
      "onboard.finish": "Finish and enter Control center",
      "onboard.back": "Back",
      "onboard.continue": "Continue",
      "onboard.saveFailed": "Save failed; please retry",
      "onboard.avatarTooBig": "Avatar must be under 350KB",
      "onboard.schoolLabel": "School",
      "onboard.schoolPlaceholder": "Type a few characters to match your school",
      "onboard.tierLabel": "School tier",
      "onboard.tierPlaceholder": "Select",
      "onboard.schoolRequired": "School, school tier and major are required",
      "onboard.majorLabel": "Major",
      "settings.schoolLabel": "School",
      "settings.schoolPlaceholder": "Type a few characters to match your school",
      "settings.schoolTierLabel": "School tier",
      "settings.schoolTierPlaceholder": "Select",
      "settings.schoolRequired": "Fill in school, school tier and major before saving",
      "settings.majorLabel": "Major",
      "onboard.title": "Three layers, one path",
      "onboard.body": "A course holds lectures; practice and review live under Training; exams are formal papers. Start with a course.",
      "onboard.dismiss": "Got it",
      "cc.continue": "Continue",
      "cc.start": "Start here",
      "cc.startAction": "Open courses",
      "cc.review": "Review due",
      "cc.dueCount": "{n} due",
      "cc.noneDue": "Nothing due",
      "nav.search": "Open courses & library",
      "search.title": "Search courses & materials",
      "search.placeholder": "Search courses, lecture titles or text…",
      "search.hint": "Type to search · ⌘K to open · Esc to close",
      "search.empty": "No matching results",
      "search.loading": "Searching…",
      "search.results": "{n} results",
      "search.course": "Course",
      "search.artifact": "Lecture",
      "search.content": "Text",
      "nav.groupLearn": "Learn",
      "nav.groupTrain": "Train",
      "nav.groupExam": "Assessment",
      "nav.groupData": "Reference",
      "nav.groupSystem": "System",
      "foot.localShort": "Local",
      "foot.localId": "Local ID",
      "focus.line1": "Read a page, drill one,",
      "focus.line2": "then review what's due.",
      "nav.library": "Courses",
      "nav.workbench": "Content tools",
      "nav.practice": "Practice",
      "nav.review": "Review",
      "nav.notes": "Notes",
      "nav.settings": "Settings",
      "nav.back": "Back",
      "nav.exam": "Exam builder",
      "exam.eyebrow": "EXAM",
      "exam.title": "Exam",
      "exam.lede": "Build a paper from a past-exam format or a blueprint.",
      "exam.artifact": "Knowledge scope (lecture)",
      "exam.subject": "Subject",
      "exam.subjectAuto": "Subject: {subject} (from course source)",
      "exam.limit": "Up to 50 questions per paper; split beyond that",
      "exam.longConfirm": "This paper is large. Generation may take several minutes and auditing runs in batches. Continue?",
      "exam.difficulty": "Difficulty (1–5)",
      "exam.mode": "Mode",
      "exam.types": "Question types (comma-separated)",
      "exam.typesHint": "Leave blank for defaults",
      "exam.blueprint": "Custom blueprint (optional)",
      "exam.blueprintHint": "e.g. 10 multiple choice = 30 pts; 4 calculations = 40 pts; 2 short answers = 30 pts",
      "exam.references": "Past exams (optional, up to 3)",
      "exam.referencesHint": "Change-numbers/variant need a past exam.",
      "exam.chooseRefs": "Choose past exams",
      "exam.noRefs": "No past exams selected",
      "exam.refRequired": "Change-numbers/variant mode requires at least one past exam; use mock/predict otherwise.",
      "exam.custom": "Extra requirements",
      "exam.customHint": "e.g. focus on switching rule; full calculation steps",
      "exam.start": "Generate paper",
      "exam.generating": "Building and auditing answers, usually 1–3 minutes…",
      "exam.failed": "Exam generation failed",
      "exam.total": "Total",
      "exam.paper": "Paper",
      "exam.showAnswers": "Show answers",
      "exam.hideAnswers": "Hide answers",
      "exam.print": "Print",
      "exam.export": "Export HTML",
      "exam.word": "Export Word",
      "exam.saveWord": "Save Word to Desktop",
      "exam.savePdf": "Save PDF to Desktop",
      "exam.selfTest": "Start self-test",
      "exam.selfTestHint": "Only multiple choice is auto-graded; other types need manual checking.",
      "exam.backPreview": "Back to paper",
      "exam.autoOnly": "Auto-graded multiple-choice questions: {n}",
      "exam.noChoice": "This paper has no auto-gradable multiple-choice questions.",
      "exam.submit": "Submit",
      "exam.submitted": "Submitted",
      "exam.score": "Score",
      "exam.autoResult": "Correct {correct} / {auto} auto-graded; answered {answered}.",
      "exam.autoScore": "auto-graded",
      "exam.manualNote": "Calculation and short-answer questions are not auto-graded; check them against the reference answers.",
      "exam.goScheduled": "Mistakes added to review",
      "exam.retry": "Take again",
      "exam.viewPaper": "View full paper",

      "exam.pdf": "Print / Save as PDF",
      "exam.edit": "Edit",
      "exam.editOn": "Edit mode: the paper text is now editable; click Edit again to exit",
      "exam.editOff": "Exited edit mode",
      "exam.figure": "Figure notes",
      "exam.answer": "Answer",
      "exam.analysis": "Analysis",
      "exam.noDoc": "No paper yet. Pick a scope and mode, then build.",
      "exam.modeChange": "Original with changed numbers",
      "exam.modeVariant": "Original variant",
      "exam.modeMock": "Mock",
      "exam.modePredict": "Prediction",
      "exam.subjectMath": "Calculus",
      "exam.subjectPhysics": "Physics",
      "exam.subjectCircuit": "Circuits",
      "exam.subjectMedical": "Medicine",
      "exam.subjectLiberal": "Humanities",
      "exam.subjectOther": "Other",
      "exam.points": "pts",
      "exam.source": "Source",
      "exam.paperMeta": "Total 100 pts · 120 minutes · Name ______ ID ______ Score ______",
      "exam.footnote": "Generated by the TermFinale agent for exam practice only; always check the source material.",
      "exam.type.choice": "Multiple choice",
      "exam.type.calculation": "Calculation",
      "exam.type.short_answer": "Short answer",
      "exam.type.fill_blank": "Fill in the blank",
      "exam.type.proof": "Proof",
      "exam.type.experiment": "Experiment",
      "exam.type.design": "Design",
      "exam.type.term": "Term explanation",
      "exam.type.case": "Case analysis",
      "exam.type.essay": "Essay",
      "crumb.library": "Library",
      "crumb.new": "New course",
      "crumb.course": "Course",
      "crumb.artifact": "Quality report",
      "crumb.read": "Reader",
      "aria.menu": "Menu",
      "aria.theme": "Toggle theme",
      "aria.langToEn": "Switch to English",
      "aria.langToZh": "Switch to Chinese",
      "lang.zh": "简体中文",
      "lang.hant": "繁體中文",
      "gen.lang": "Generation language",
      "gen.zh": "简体中文",
      "gen.hant": "繁體中文",
      "gen.en": "English",
      "gen.illustrations": "AI decorative background (~$0.025/image, not precise)",
      "lang.en": "English",
      "lang.label": "Language",
      "lang.meta": "Navigation, buttons, labels and status",
      "lang.note": 'Switches UI copy only. Course names, artifact titles, section titles and generated content keep their source language. The EN toggle inside the reader works independently.',
      "error.request": "Request failed ({status})",
      "error.network": "Cannot reach the network or local service. Check your connection and retry.",
      "error.actionFailed": "Action failed; please retry",
      "error.title": "Something went wrong",
      "error.load": "Failed to load",
      "error.retry": "Retry",
      "loading.default": "Loading…",
      "notFound.title": "Page not found",
      "notFound.text": "Head back to the library to continue.",
      "notFound.cta": "Go to library",
      "status.delivered": "Readable",
      "status.review": "Generated",
      "status.rejected": "Needs redo",
      "status.draft": "Draft",
      "status.due": "Due",
      "status.passed": "Passed",
      "status.passedShort": "Passed",
      "status.notPassed": "Needs redo",
      "status.notPassedShort": "Redo",
      "status.machinePassed": "Machine gate passed",
      "status.partialCoverage": "Partial coverage",
      "status.partialDelivery": "Partial delivery",
      "status.configured": "Configured",
      "status.notConfigured": "Not configured",
      "status.migrated": "Migrated",
      "status.pendingReview": "Generated",
      "status.migratedManual": "Migrated · manual check pending",
      "status.readReport": "Reports only, not auto-generated",
      "status.notDone": "Not done",
      "unit.lecturePages": (v) => `${v.n} lecture ${Number(v.n) === 1 ? "page" : "pages"}`,
      "unit.sourcePages": (v) => `${v.n} source ${Number(v.n) === 1 ? "page" : "pages"}`,
      "unit.lectures": (v) => plural(v.n, "lecture", "lectures"),
      "unit.sections": (v) => plural(v.n, "section", "sections"),
      "unit.figures": (v) => plural(v.n, "figure", "figures"),
      "unit.blocks": (v) => plural(v.n, "block", "blocks"),
      "unit.paragraphs": (v) => plural(v.n, "paragraph", "paragraphs"),
      "unit.pages": (v) => plural(v.n, "page", "pages"),
      "unit.notes": (v) => plural(v.n, "note", "notes"),
      "unit.sources": (v) => plural(v.n, "source", "sources"),
      "unit.pageN": (v) => `Page ${v.n}`,
      "sep.list": ", ",
      "meta.pages": "pages",
      "meta.sections": "sections",
      "meta.figures": "figures",
      "meta.items": "items",
      "meta.all": "All",
      "quality.noAudit": "No semantic audit",
      "quality.noAuditFile": "No coverage_audit.json — content cannot be counted as passed",
      "quality.structureGate": "Structure gate",
      "quality.content": "Content check",
      "quality.pdf": "PDF check",
      "quality.language": "Language check",
      "quality.semantic": "Content check",
      "quality.contentMetrics": "Content quality",
      "quality.citationSupport": "Citation support",
      "quality.termRecall": "Term recall",
      "quality.dupSentence": "Duplicate sentences",
      "quality.boilerplate": "Boilerplate density",
      "quality.waterTitle": "Duplicates / boilerplate",
      "quality.dupShort": "dup {n}%",
      "quality.boilerShort": "boiler {n}/1k",
      "quality.imageMode": "Image edition",
      "quality.imageModeDetail": "{images} source-page images / {pages} pages",
      "quality.metricsHint": "Computed locally: overlap with cited pages, term coverage, duplicate and boilerplate text.",
      "quality.fallbackNotice": "{n} section(s) could not be written by the model; they use the original pages: {labels}. They are still readable and cited.",
      "quality.coverage": "Coverage target",
      "quality.coverageMet": "{actual}% (tier target ≥{target}%)",
      "quality.coverageNoTier": "{actual}% (no tier)",
      "quality.figures": "Figures",
      "quality.pass": "Passed",
      "quality.fail": "Failed",
      "quality.zeroIssues": "0 hard issues",
      "quality.hasIssues": "Has hard issues",
      "quality.figureOk": "{n} ok",
      "quality.figureBad": " · {n} bad",
      "quality.figureFallback": "Figure",
      "quality.issue": "Issue",
      "quality.ok": "ok",
      "artifact.notFoundTitle": "Lecture not found",
      "artifact.notFoundText": "It may have been moved or deleted.",
      "artifact.backLibrary": "Back to library",
      "artifact.eyebrow": "Quality report",
      "artifact.meta": "{pages} source pages · {pdf} lecture pages · {sections} sections · {figures} figures",
      "artifact.read": "Start reading",
      "artifact.practice": "Practice",
      "artifact.backCourse": "← Back to course",
      "artifact.sections": "Sections",
      "artifact.sectionsHint": "Practice any section and the questions come from that section",
      "artifact.pageCol": "Pages",
      "artifact.noSections": "No sections.json",
      "artifact.practiceSection": "Practice this section",
      "artifact.figures": "Figures",
      "artifact.figuresCount": "{n} total",
      "artifact.noFigures": "No figure source report.",
      "artifact.figureSource": "Source: pp. {pages} · {origin} · {status}",
      "artifact.bannerRejectedTitle": "Hard gate failed — this cannot be delivered.",
      "artifact.bannerRejectedBody": "At least one of structure, content, PDF or language failed. Review the quality report below before deciding to regenerate.",
      "artifact.bannerReviewTitle": "Generated — you can start reading.",
      "artifact.bannerReviewBody": '{audit}. This is not "content passed"; it is only "needs review".',
      "artifact.bannerGoodTitle": "Readable: hard gate and semantic audit both passed.",
      "artifact.bannerGoodBody": "{audit}. Still spot-check key examples manually.",
      "artifact.rewrite": "Whole-document AI rewrite (draft)",
      "artifact.rewriteHint": "The original is untouched. A new draft is built and re-runs Gate/PDF; compare, keep or discard.",
      "artifact.rewriteInstruction": "Rewrite instruction",
      "artifact.rewritePlaceholder": "e.g. explain more plainly, add everyday analogies; keep all formulas, pages and examples",
      "artifact.rewriteStart": "Generate rewrite draft",
      "artifact.rewriteRunning": "Rewriting section by section and re-running Gate/PDF…",
      "artifact.rewriteDraft": "Draft generated",
      "artifact.rewriteKeep": "Open draft",
      "artifact.rewriteDiscard": "Discard draft",
      "artifact.rewriteDiff": "Rewrite diff",
      "artifact.acceptDraft": "Replace original with this draft",
      "artifact.acceptHint": "The original is backed up first, then replaced and re-runs Gate/PDF; automatic rollback on failure.",
      "artifact.acceptConfirm": "Replace the original with this draft? The original will be backed up first.",
      "artifact.restore": "Restore previous version",
      "artifact.restoreConfirm": "Restore the previous backup? The current version will also be backed up first.",
      "artifact.review": "Human review",
      "artifact.reviewHint": "Machine checks are not an instructor's sign-off; reviewer and date stay on this machine.",
      "artifact.nextStep": "Suggested order: read it once, then use Practice to check yourself; build a paper when you want a full review.",
      "artifact.runAudit": "Run content review",
      "artifact.auditRunning": "Reviewing page by page; large files take a while…",
      "artifact.auditDone": "Review done: content passed",
      "artifact.auditGaps": "Review done: {n} page(s) need work",
      "artifact.auditUnverified": "Review done: {n} page(s) unfinished; you can retry",
      "artifact.reviewer": "Reviewer",
      "artifact.reviewNotes": "Review notes (optional)",
      "artifact.saveReview": "Save review",
      "artifact.reviewed": "Human-reviewed",
      "artifact.constraints": "Generation constraints",
      "artifact.keyPoints": "Key points / weights",
      "artifact.excluded": "Explicitly excluded",
      "artifact.customPrompt": "Custom prompt",
      "artifact.missingPages": "Missing pages",
      "card.read": "Read",
      "card.quality": "Quality report",
      "card.practice": "Practice",
      "card.practiceThis": "Practice this one",
      "card.noCoverage": "Page coverage not recorded",
      "home.eyebrow": "One thing to do today",
      "home.continue": "Continue reading",
      "home.viewQuality": "View quality report",
      "home.dueLabel": "mistakes due",
      "home.readableStat": "readable lectures",
      "home.heroNote": 'Numbers come from the manifest and coverage_audit: readable means Gate passed with 0 partial / 0 missing in the semantic audit. An artifact without a report is marked "needs review".',
      "home.emptyEyebrow": "Get started",
      "home.emptyTitle": "No readable lectures yet",
      "home.emptyText": 'Generate a lecture from source material, or open an existing artifact from a course. Anything without a quality report is not marked "readable".',
      "home.emptyCta": "Go to Workbench",
      "home.emptyNote": 'v3 only shows artifacts with a quality report. Without one, an artifact is marked "needs review" instead of green "done".',
      "home.doNow": "Do now",
      "home.practiceEyebrow": "Practice",
      "home.practiceTitle": "Run a practice set",
      "home.practiceBody": "Three multiple-choice questions from one section of the current lecture. Grading happens on the server; wrong answers go to the mistake log.",
      "home.practiceCta": "Start practice →",
      "home.reviewTitleDue": (v) => `${v.n} due ${Number(v.n) === 1 ? "mistake" : "mistakes"}`,
      "home.reviewTitleNone": "Review queue is empty",
      "home.reviewBodyDue": "Clear the due items before new questions. Mistakes come back after 1/2/4/7 days.",
      "home.reviewBodyNone": "Nothing due does not mean 100% mastery. Do new questions or check mastery.",
      "home.reviewCta": "Go to review →",
      "home.workbenchEyebrow": "Workbench",
      "home.workbenchTitle": "Extract / Paper / Analysis",
      "home.workbenchBody": 'Key points, terms, original questions, papers and logic analysis. Each type has its own schema and is only marked "machine passed" after the gate.',
      "home.workbenchCta": "Open Workbench →",
      "home.courses": "Courses",
      "home.allCourses": "All {n}",
      "home.noCourseTitle": "No courses yet",
      "home.noCourseText": "Create a lecture in the Workbench.",
      "library.eyebrow": "Courses",
      "library.title": "Courses",
      "library.lede": "Browse lectures, quality reports and practice by course; generated files no longer pile up on the home page.",
      "library.backHome": "Back to Today",
      "library.emptyTitle": "No courses yet",
      "library.emptyText": "Create a course first, add sources and course info, then generate its first lecture.",
      "library.cta": "New course",
      "course.readableBadge": "{n} readable",
      "course.meta": "{n} lectures · {pages} pages · {figures} figures",
      "course.foot": "{delivered} readable · {review} to review",
      "course.open": "Open course →",
      "course.backAll": "← All courses",
      "course.new": "Generate lecture",
      "course.newCourse": "New course",
      "course.edit": "Edit course",
      "course.editDone": "Done editing",
      "course.finishEdit": "Done editing",
      "course.editLecture": "Edit",
      "course.editCourse": "Edit course materials",
      "course.generateLecture": "Generate lecture / edit materials",
      "course.deleteLecture": "Delete",
      "course.deleteLectureConfirm": "Permanently delete this source/lecture? Files, course records, practice and mistakes are removed too.",
      "course.deleteLectureDone": "Permanently deleted",
      "course.deleteLectureFailed": "Failed to delete lecture",
      "course.editTitle": "Course material & lecture",
      "course.editSectionSources": "Course material",
      "course.editSectionSourcesHint": "Keep or add sources and set their weights",
      "course.editSectionInfo": "Course information",
      "course.editSectionInfoHint": "Title, target, foundation, difficulty and constraints",
      "course.editSectionGenerate": "Generation settings",
      "course.editSectionGenerateHint": "Only affects voice and language",
      "course.editLede": "Edit course info, AI preference and raw sources; generate lectures inside the course.",
      "course.editBack": "Back to course",
      "course.editSourceLecture": "Lecture to edit",
      "course.editAddSources": "Add sources",
      "course.editNoSource": "No reusable sources",
      "course.editNoSourceBody": "Add new sources below before regenerating.",
      "course.editWeights": "Source weights (each, 1–5)",
      "course.editExistingSources": "Existing sources",
      "course.editExcludedSources": "Excluded sources ({n})",
      "course.editExcludedHint": "Check to restore a file to this selection; the file itself was not deleted.",
      "course.editKeepHint": "Checked sources are reused. Unchecking excludes a source from the next generation; it does not delete the file. Add new sources below.",
      "course.editChooseFiles": "Choose new sources",
      "course.editNoFiles": "No files selected",
      "course.editGenerate": "Save & regenerate",
      "course.editSaveOnly": "Save sources & settings",
      "course.editSaveOnlyDone": "Sources and settings saved; the current lecture was not rebuilt",
      "course.editParamsDone": "Settings saved",
      "course.editSaveOnlyFailed": "Failed to save sources",
      "course.pendingRebuild": "Sources updated · rebuild pending",
      "course.editGenerating": "Regenerating",
      "course.editDone": "New version generated; returning to course",
      "course.editFailed": "Regeneration failed",
      "course.archive": "Delete course",
      "course.archiveNote": "Delete permanently removes this course's user sources, lectures, papers, bank, mistakes and chat; bundled material is kept.",
      "course.archiveConfirm": "Permanently delete this course? User sources, lectures, papers, bank, mistakes and chat are removed; bundled material is kept.",
      "course.deleted": "Course deleted: {n} user items removed",
      "course.deleteFailed": "Failed to delete course",
      "course.overview": "Course overview",
      "course.settings": "Settings",
      "doc.delete": "Delete",
      "doc.rename": "Rename",
      "doc.back": "Back to workbench",
      "doc.unknownSource": "Unknown lecture",
      "doc.hits": "{n} matches",
      "doc.renamePrompt": "Enter a new paper title",
      "doc.renamed": "Renamed",
      "doc.renameFailed": "Rename failed",
      "doc.deleteConfirm": "Delete this output? This cannot be undone.",
      "doc.deleted": "Deleted",
      "doc.deleteFailed": "Delete failed",
      "course.training": "Training",
      "course.trainingNote": "Practice and due mistakes for this course only.",
      "course.newPractice": "New practice",
      "course.newPracticeNote": "Choose a lecture, then a section and count.",
      "course.practice": "Practice",
      "course.noLectures": "No lectures in this course yet.",
      "course.review": "Mistake review",
      "course.reviewNote": "Due and scheduled items are filtered to this course.",
      "course.openReview": "Open course review",
      "course.papers": "Exam",
      "course.papersNote": "Formal papers only.",
      "course.newPaper": "New paper",
      "course.cleanPapers": "Clean duplicates · {n}",
      "course.cleanPapersConfirm": "Delete older papers with the same title and keep the newest one? This cannot be undone.",
      "course.cleanPapersDone": "Cleaned {n} duplicate papers",
      "course.paperAll": "All · {n}",
      "course.paperValidated": "Passed · {n}",
      "course.paperReview": "Not passed · {n}",
      "course.selfTested": "Tested {score}/{total}",
      "course.paper": "Paper",
      "course.noPapers": "No papers yet",
      "course.noPapersNote": "Build a paper from lectures.",
      "course.tools": "Extract",
      "course.bankPractice": "Question bank practice",
      "bank.title": "Question bank",
      "bank.eyebrow": "BANK",
      "bank.lede": "Only original questions already in the bank. Deleting a question also removes its attempts and mistakes.",
      "bank.practice": "Start bank practice",
      "bank.manage": "Manage bank",
      "bank.count": "{n} questions",
      "bank.answer": "Answer {x}",
      "bank.emptyTitle": "Bank is empty",
      "bank.emptyText": "Extract original questions in Content tools, then add them to the bank.",
      "bank.deleteConfirm": "Delete this question from the bank? Its attempts and mistakes will also be removed.",
      "course.bankNote": "Add extracted original questions to the bank, then practice them for this lecture.",
      "course.bankEmpty": "No bank questions yet. Run “Extract original questions” in Content tools, then add the output to the bank.",
      "course.bankCount": "{n} questions",
      "course.targetProgress": "Target {target} · practised section average {current}",
      "course.targetNoData": "no practice yet",
      "course.targetUnset": "No target score set.",
      "course.toolsNote": "Key points, terms, questions, maps or analysis from lectures.",
      "course.openTools": "Open content tools",
      "course.noTools": "No extractions yet",
      "course.noToolsNote": "Choose a lecture and run one extraction.",

      "course.scopeTools": "Course tools",
      "course.lecturesTab": "Lectures",
      "course.structure": "Course structure",
      "course.structureNote": "Courses aggregate lectures. The lecture list is the second tab, not the overview.",
      "course.viewLectures": "View lectures",
      "course.lecturesCount": "lectures",
      "course.pages": "pages",
      "course.figures": "figures",
      "course.target": "target",
      "course.days": "days",
      "course.today": "today",
      "course.ended": "ended",
      "course.noDate": "No exam date",
      "course.setGoal": "Set a goal",
      "course.saveGoal": "Save course settings",
      "course.examDate": "Exam date",
      "course.targetScore": "Target score",
      "course.name": "Course name",
      "course.nameHint": "Leave blank to derive from lectures",
      "course.metaDetail": "{n} lectures · {pages} pages · {sections} sections · {figures} figures",
      "course.academicMeta": "{credits} credits · {type} · difficulty {difficulty}/5",
      "course.saveSettings": "Save course settings",
      "course.settingsHint": "Credits, course type and difficulty are saved locally; your profile school tier feeds the weights, and difficulty feeds the lecture prompt.",
      "course.readableStat": "readable",
      "course.reviewStat": "to review",
      "course.generateHere": "Build paper",
      "course.lectures": "Lectures",
      "course.materials": "Materials",
      "course.materialsEmpty": "No generated content yet",
      "course.materialsEmptyText": "Start from Lectures.",
      "course.sourceSaved": "Materials saved",
      "course.sourceCount": "{n} sources",
      "course.readSource": "Read material",
      "course.sourceListHint": "Saved sources; generate a lecture or use Content tools to extract points now.",
      "course.noLectureTitle": "No lecture generated yet",
      "course.noLectureText": "{n} sources are saved. Generate a lecture to read and practise.",
      "course.sourceOnlyHint": "No lecture yet. Saved sources can be used by Content tools; lecture generation is optional.",
      "course.sourceSavedHint": "Saved course sources",
      "course.qualityHint": "Quality reports are on each card",
      "course.emptyTitle": "This course has no lectures yet",
      "course.emptyText": "Upload a PDF or PPTX under Materials, pick some pages, then tap Generate lecture.",
      "course.notFoundTitle": "Course not found",
      "course.notFoundText": "Back to the course list.",
      "course.notFoundCta": "Back to courses",
      "practice.eyebrow": "Practice",
      "practice.title": "Practice",
      "practice.listLede": "Pick a lecture, then pick a section.",
      "practice.pickHint": "Choose a lecture under a course, then a section and count.",
      "practice.courseScope": "Current course: {name}",
      "practice.noLectureTitle": "No lecture in this course yet",
      "practice.noLectureText": "\"{name}\" only has saved sources; generate a lecture before practicing.",
      "practice.ungrouped": "No course",
      "practice.bankTitle": "Question bank practice",
      "practice.bankLede": "Practice original questions already added to the bank; grading and mistakes work the same way.",
      "practice.bankSource": "Question bank · extracted originals",
      "practice.bankHint": "Questions come directly from the bank; no model call.",
      "practice.bankStart": "Start bank practice",
      "practice.emptyTitle": "No lectures yet",
      "practice.emptyText": "The library is empty.",
      "practice.lede": "Questions come only from this section's lecture passages. Answers are graded on the server; mistakes go to the mistake log.",
      "practice.viewQuality": "View quality report",
      "practice.section": "Section",
      "practice.sectionPages": " (pp. {range})",
      "practice.count": "Questions",
      "practice.count3": "3 questions",
      "practice.count5": "5 questions",
      "practice.source": "Source",
      "practice.sourceValue": "Server-verified; answers are not sent before submission",
      "practice.start": "Generate questions",
      "practice.startHint": "10–30 seconds; failures surface as errors.",
      "practice.generating": "Generating questions from this section (lecture passages only)…",
      "practice.noQuestions": "The model returned no valid questions",
      "practice.generateFailed": "Question generation failed",
      "practice.retry": "Retry",
      "practice.cancel": "Cancel generation",
      "practice.resumed": "Resumed session: question {i} / {n}",
      "practice.restart": "Start over",
      "practice.progress": "Question {i} / {n}",
      "practice.sourcePage": "Source page {n}",
      "practice.submit": "Submit answer",
      "practice.submitHint": "Grading runs on the server; wrong answers are added to the mistake log.",
      "practice.correct": "Correct",
      "practice.wrong": "Wrong — added to the mistake log",
      "practice.answerText": "Correct answer: {letter}. {explanation}",
      "practice.sourceLine": "Source: page {n}",
      "practice.next": "Next question",
      "practice.finish": "See results",
      "practice.gradeFailed": "Grading failed",
      "practice.doneTitle": "Set complete",
      "practice.doneText": "{correct} / {total} correct ({acc}%). Wrong answers are in the mistake log and return after 1/2/4/7 days.",
      "practice.goReview": "Review mistakes",
      "practice.wrongScheduled": "{n} wrong answers are in the mistake log; review starts tomorrow.",
      "practice.noWrong": "No wrong answers in this set.",
      "practice.goScheduled": "View scheduled",
      "practice.again": "Practice another set",
      "review.eyebrow": "Review",
      "review.title": "Review",
      "review.lede": "Today shows only due mistakes; scheduled ones are listed separately. Mastery comes from real attempts; zero attempts shows —, not 100%.",
      "review.doNew": "New questions",
      "review.dueToday": "Due today",
      "review.forecast": "Next days: {list}",
      "review.totalWrong": "Total mistakes",
      "review.tabDue": "Today",
      "review.tabScheduled": "Scheduled",
      "review.scheduledCount": "Scheduled",
      "review.courseFilter": "Course filter",
      "review.allCourses": "All courses",
      "review.scheduledTitle": "Scheduled mistakes",
      "review.scheduledEmptyTitle": "No scheduled mistakes",
      "review.scheduledEmptyText": "Mistakes are scheduled by interval and appear here until due.",
      "review.nextDate": "Next {date}",
      "review.trackedSections": "Sections tracked",
      "review.dueTitle": "Due mistakes",
      "review.emptyTitle": "No mistakes due today",
      "review.emptyText": "This does not mean 100% mastery — just nothing due today. Try a new practice set.",
      "review.emptyCta": "Start a new set",
      "review.mastery": "Mastery",
      "review.noRecords": "No practice records yet. Finish a set to see real data here.",
      "review.wrongTimes": "Wrong {n} times",
      "review.showAnswer": "Show answer",
      "review.remembered": "Got it",
      "review.forgot": "Not yet",
      "review.correctAnswer": "Correct answer: ",
      "review.sourceLine": "Source: page {n}",
      "review.advance": "Moved to the next review interval",
      "review.reset": "Reset to 1 day later",
      "review.failed": "Action failed",
      "review.tableSection": "Section",
      "review.tableAttempts": "Attempts",
      "review.tableCorrect": "Correct",
      "review.tableAccuracy": "Accuracy",
      "review.tableScore": "Mastery",
      "settings.eyebrow": "Settings",
      "settings.title": "Settings",
      "settings.lede": "Local-first: materials and practice records stay on this machine; keys live only in the local .env.",
      "settings.appearance": "Appearance",
      "settings.themeMeta": "Site theme",
      "settings.light": "Light",
      "settings.dark": "Dark",
      "settings.model": "Models",
      "settings.readonly": "Read-only",
      "settings.keyLocal": "Local configuration",
      "settings.keyPlaceholder": "Paste a new key",
      "settings.keyPlaceholderSet": "Configured; leave blank to keep",
      "settings.saveKeys": "Save keys",
      "settings.testKeys": "Test connection",
      "settings.keyTesting": "Testing…",
      "settings.keySaved": "Keys saved and active",
      "settings.keyNoInput": "No new key entered; blank leaves it unchanged",
      "settings.keySaveFailed": "Failed to save keys",
      "settings.keyTestOk": "Connected",
      "settings.keyNotSet": "Not configured",
      "settings.keyTestFail": "Connection failed",
      "settings.textGeneration": "Text generation: ",
      "settings.deepseekKey": "DeepSeek key: ",
      "settings.keyNote": "Keys are written only to the local user .env; plaintext is never shown here. Blank save keeps the current key.",
      "settings.profile": "Profile",
      "settings.profileHint": "Stored locally and shown at the bottom left.",
      "settings.profileName": "Your name",
      "settings.saveProfile": "Save name",
      "settings.profileSaved": "Name saved",
      "user.default": "Learner",
      "settings.language": "Language",
      "settings.languageMeta": "Navigation, buttons, labels and status",
      "settings.data": "Study data",
      "settings.dataNote": "Practice records, mistakes, notes and chat all live here; nothing is uploaded.",
      "settings.migration": "Migration status",
      "settings.migrationMeta": "v3 only carries over what is trusted",
      "settings.migratedLine": "Lectures / reading / practice / review / notes: ",
      "settings.experimentalLine": "Experimental lecture generation (PDF/PPTX/DOCX + outline/page figures): ",
      "settings.tasksLine": "Extraction / papers / logic analysis: ",
      "settings.tasksLineTail": " (machine gate passed, not human acceptance)",
      "settings.auditLine": "Semantic audit: ",
      "settings.wordLine": "Native Word .docx for lectures: ",
      "settings.packLine": "Task Word export / packaging / notarization: ",
      "settings.wordPartial": "Wired, not Word-verified",
      "settings.release": "Release statement",
      "settings.releaseBody": 'v3 marks a lecture readable only when Gate, content/PDF/language checks and a semantic audit with 0 partial / 0 missing all pass. Word layout, human review and the 3.5 material gap are still unfinished; a better-looking page is not a release.',
      "task.extractPoints": "Key points",
      "task.extractPointsHint": "Key points + page numbers + explanations; every item must cite its source.",
      "task.extractNouns": "Terms",
      "task.extractNounsHint": "Terms + definitions + commonly confused terms + page numbers.",
      "task.extractQuestions": "Original questions",
      "task.extractQuestionsHint": "Verbatim questions + options + answers/explanations + original numbers/page numbers.",
      "task.paper": "Generate paper",
      "task.paperHint": "Original / variant / mock questions; unique options, answer inside the options, independent answer audit.",
      "task.analysis": "Logic analysis",
      "task.analysisHint": "Through-line + concept hierarchy + causal chain + key-point mapping + confusions + order + sources.",
      "wb.eyebrow": "Workbench",
      "wb.title": "Content tools",
      "wb.lede": "One task at a time: pick a lecture, a section and a task, then run it. Results are saved to local outputs.",
      "wb.new": "New lecture (experimental)",
      "wb.mode": "Mode",
      "wb.modeOriginal": "Original (verbatim)",
      "wb.modeVariant": "Variant",
      "wb.modeMock": "Mock",
      "wb.count": "Questions",
      "wb.course": "Course",
      "wb.material": "Source / lecture",
      "wb.chooseCourse": "Choose a course first",
      "wb.chooseMaterial": "Choose a source in this course",
      "wb.basis": "Basis",
      "wb.basisSection": "From lecture",
      "wb.basisPages": "From source pages",
      "wb.pagesInline": "Extract from source pages; no lecture needed",
      "wb.modeLabel": "Extraction",
      "wb.modeOriginal2": "Verbatim (must match source)",
      "wb.modeVariant2": "Adapted (rewritten, still cited)",
      "artifact.chipBase": "Base checks",
      "artifact.chipContent": "Content check",
      "artifact.chipFigures": "Figures",
      "artifact.chipCoverage": "Lecture coverage",
      "artifact.chipQuality": "Content quality",
      "artifact.detailPass": "Pass",
      "artifact.detailRedo": "Redo",
      "artifact.detailGap": "Gaps",
      "artifact.detailUnchecked": "Not checked",
      "wb.lecture": "Lecture",
      "wb.section": "Section",
      "wb.noSections": "No sections",
      "wb.run": "Run",
      "wb.addBank": "Add to bank",
      "wb.addBankHint": "Only auto-gradable multiple-choice questions; practice them in Course → Training.",
      "wb.bankAdded": "Added to bank: {n} questions",
      "wb.bankFailed": "Failed to add to bank",
      "wb.bankNoChoice": "This extraction has no auto-gradable multiple-choice questions, so it cannot enter the bank.",
      "wb.running": "Running…",
      "wb.runningHint": "The model is generating and running the gate; usually 10–40 seconds.",
      "wb.runHint": "Generated output still needs human review.",
      "wb.generating": "Generating + checking the gate…",
      "wb.outputs": "Outputs",
      "wb.recent": "Last {n}",
      "wb.noOutputs": "No outputs yet. Run a task and results will appear here.",
      "wb.noDocTitle": "No result yet",
      "wb.noDocText": 'Pick a lecture and section, then click "Run". Results are saved automatically to local outputs.',
      "wb.selectFirst": "Pick a lecture and section first",
      "wb.taskFailed": "Task failed",
      "wb.readFailed": "Failed to read",
      "wb.passToast": "Machine gate passed",
      "wb.partialToast": "Partial coverage — below 98%",
      "wb.failToast": "Checks failed; the result was kept",
      "wb.resultOf": "Result · {task}",
      "wb.allSections": "All material (no omission)",
      "wb.pageCoverage": "Page coverage {cited}/{total} · {pct}%",
      "wb.partialBanner": "Partial coverage — below 98%",
      "wb.gateIssues": "Check issues",
      "wb.machinePassedNote": "Not human acceptance; wrong answers and teaching value still need spot checks.",
      "wb.thPoint": "Key point",
      "wb.thExplanation": "Explanation",
      "wb.thPage": "Page",
      "wb.thTerm": "Term",
      "wb.thDefinition": "Definition",
      "wb.thConfused": "Confused with",
      "wb.sourcePage": "Page {n}",
      "wb.sourceNo": "Original {n}",
      "wb.answer": "Answer: ",
      "wb.referenceAnswer": "Reference answer: ",
      "wb.choice": "Multiple choice",
      "wb.calculation": "Calculation",
      "wb.shortAnswer": "Short answer",
      "wb.manualTitle": "Calculation / short-answer included",
      "wb.manualBody": "Choice questions were independently audited; calculation/short-answer reference answers need human checking — they are not auto-graded.",
      "wb.oneLine": "One-line through-line",
      "wb.concepts": "Concept hierarchy",
      "wb.causal": "Causal chain",
      "wb.examMap": "Key-point mapping",
      "wb.confusions": "Confusions",
      "wb.order": "Study order",
      "new.eyebrow": "New course",
      "new.title": "New course",
      "new.courseLede": "Fill in course info and upload sources. Lecture, extraction, practice and exam settings live inside the course.",
      "new.back": "← Back",
      "new.warningTitle": "Before you start",
      "new.warningBody": 'This is an experimental "page-by-page" pipeline: it does not build a textbook outline, does not add figures automatically, and adds no semantic audit, so the result is at most "needs review" and will never be marked "readable". Exam papers/answer sheets are rejected. Textbook-grade lectures still require chapter-by-chapter authoring plus human review.',
      "new.file": "Sources (multiple, up to 6; PDF / PPT / PPTX / DOC / DOCX / image)",
      "new.fileHint": "PDF / PPT / PPTX / DOC / DOCX / images; multiple files allowed.",
      "new.maxFiles": "Up to 20 sources at a time.",
      "new.fileSelectTitle": "{n} source(s) uploaded",
      "new.selectAll": "Select all",
      "new.fileOrderHint": "Pre-sorted by chapter; use ↑↓ to adjust. Generation follows this order.",
      "new.fileSelectHint": "Only checked sources are generated; weights follow checked order.",
      "new.selectedCount": "{n} selected",
      "new.noFiles": "Select at least one source.",
      "new.moveUp": "Move up",
      "new.moveDown": "Move down",
      "new.lectureTitle": "First lecture title",
      "new.titlePlaceholder": "Leave blank to use the filename",
      "new.course": "Course name",
      "new.coursePlaceholder": "e.g. Circuits / Organic Chemistry",
      "new.credits": "Credits",
      "new.courseType": "Course type",
      "new.schoolLevel": "School level",
      "new.difficulty": "Custom difficulty",
      "new.ctMajor": "Major course",
      "new.ctBasic": "Major foundation",
      "new.ctPublic": "General foundation",
      "new.ctElective": "Elective",
      "new.slFirst": "First-tier",
      "new.slSecond": "Second-tier",
      "new.slCollege": "Vocational college",
      "new.slOther": "Other",
      "new.diffEasy": "Easy",
      "new.diffNormal": "Medium",
      "new.diffHard": "Hard",
      "new.target": "Target score",
      "new.days": "Days left",
      "new.foundation": "Foundation",
      "new.foundationWeak": "Weak",
      "new.foundationNormal": "Average",
      "new.foundationStrong": "Strong",
      "new.multiTitle": "Merge multiple sources (weighted)",
      "new.multiLede": "Upload up to 20 sources with weights 1–5. Higher-weight sources get finer chunks and more space in the merged lecture.",
      "new.multiFiles": "Sources (multiple, up to 6)",
      "new.weights": "Weight per source (comma-separated)",
      "new.weightsHint": "e.g. 5,3,1 in checked order; default 1",
      "new.startMulti": "Generate merged lecture",
      "new.keyPoints": "Key points (one per line)",
      "new.keyPointsHint": "One per line, optional weight 1–5: three-element method=5, switching rule=3; weight ≥4 must be developed in at least two places plus an example/pitfall",
      "new.customPrompt": "Extra requirements / custom prompt",
      "new.customPromptHint": "e.g. more everyday analogies, slower derivations, a structure map per section; must not contradict the source",
      "new.excluded": "Explicitly not tested (one per line)",
      "new.excludedHint": "e.g. differentiator/integrator circuits; do not write these",
      "new.persona": "Persona (tone only)",
      "new.personaTeacher": "Teacher",
      "new.mastery": "Mastery",
      "new.masteryHint": "How well do you know this course right now?",
      "new.mastery1": "1 · Barely started",
      "new.mastery2": "2 · Heard of it",
      "new.mastery3": "3 · Average, keeping up",
      "new.mastery4": "4 · Fairly solid, want more",
      "new.mastery5": "5 · Strong, only gap-checking",
      "new.examDate": "Exam date",
      "new.examDateHint": "Optional; used to show days left in lectures and plans",
      "new.personaGentle": "Gentle guide",
      "new.personaAcademic": "Academic AI",
      "new.personaSunny": "Sunny guide",
      "new.personaHacker": "Hardcore geek",
      "new.start": "Create course & first lecture",
      "new.startHint": "Prefers the source outline, up to 8 pages per segment; fills all pages for a single source up to 159 pages. Multiple sources merge in order by weight. Generation takes a few minutes; failures show the reason.",
      "new.saveSources": "Save course",
      "new.saveSourcesHint": "Saves the course and sources; generation happens inside the course.",
      "new.savingSources": "Saving materials…",
      "new.saveSourcesTimeout": "Saving materials timed out; retry, or split/compress the file",
      "new.savedSources": "{n} materials saved; course created",
      "new.saveSourcesFailed": "Could not save materials",
      "new.saveJobDonePages": "Saved {pages} pages",
      "new.saveLimitsHint": "Up to 20 files, 200MB each, 500MB total. Saving continues in the background if you leave this page.",
      "new.fastSave": "Fast save (skip OCR for scans)",
      "new.fastSaveHint": "Scan OCR runs at the first generation instead; text PDFs are unaffected.",
      "new.saveJobResume": "Finishing the previous save in the background",
      "new.jobEyebrow": "Generating",
      "new.queued": "Queued",
      "new.elapsedOnly": "Elapsed {elapsed} · estimating remaining time…",
      "new.eta": "{eta} left",
      "onboard.introLead": "See how courses, training and papers connect, then start setup.",
      "new.elapsedEta": "Elapsed {elapsed} · about {eta} left",
      "new.cancel": "Cancel",
      "new.uploading": "Uploading source…",
      "new.uploadFailed": "Upload failed ({status})",
      "new.genFailed": "Generation failed",
      "new.jobDone": "Done: added to the library; the content review has not been done yet",
      "new.complete": "Done",
      "new.jobDoneNote": 'Status is "needs review", not "readable".',
      "new.unknownError": "Unknown error",
      "new.cancelled": "Cancelled",
      "new.jobReadFailed": "Failed to read job status",
      "ring.generating": "Generating",
      "ring.estimating": "Estimating…",
      "ring.eta": "{eta} left",
      "gen.locked": "Generating",
      "gen.navLocked": "Generation is running; finish or cancel before switching pages",
      "new.cancelRequested": "Cancellation requested",
      "new.cancelFailed": "Cancel failed",
      "jobstep.ledger": "Reading source / building page ledger",
      "jobstep.segment": "Generating segment {i}/{n}: {label}",
      "jobstep.assemble": "Assembling lecture / running Gate / generating PDF",
      "jobstep.done": "Done: Gate passed, awaiting page-by-page review",
      "jobstep.doneShort": "Done",
      "jobstep.cancelled": "Cancelled",
      "jobstep.failed": "Failed",
      "job.failedNext": "Try again later; pick fewer pages if the material is large.",
      "job.resume": "Resume",
      "job.resumeMissing": "No saved progress to resume; please start again.",
      "job.resumeStarted": "Resuming from where it stopped; hang on.",
      "notes.eyebrow": "Notes",
      "notes.title": "Notes",
      "notes.lede": 'Select a passage in the reader and click "Save note"; notes are grouped by source here.',
      "notes.goRead": "Go to reader",
      "notes.count": "notes",
      "notes.artifacts": "sources",
      "notes.emptyTitle": "No notes yet",
      "notes.emptyText": 'Open a lecture, select a passage and click "Save note".',
      "notes.goLibrary": "Go to library",
      "notes.viewLecture": "View lecture",
      "notes.delete": "Delete",
      "notes.page": "Page {n}",
      "notes.deleted": "Deleted",
      "notes.deleteFailed": "Delete failed",
      "reader.back": "← Back",
      "reader.pdf": "PDF viewer",
      "reader.search": "Search",
      "reader.searchPh": "Search lecture text…",
      "reader.edit": "Edit",
      "reader.export": "Export",
      "reader.exportPdf": "Export PDF",
      "reader.savePdf": "Save PDF to Desktop",
      "reader.saveWord": "Save Word to Desktop",
      "reader.exportWord": "Export Word",
      "reader.exportHtml": "Export HTML",
      "reader.print": "Print",
      "reader.editOn": "Edit mode on: changes stay in this page; export HTML to keep a copy",
      "reader.editOff": "Edit mode off",
      "reader.actionUnavailable": "Reader is still loading; try again in a moment",
      "export.saving": "Generating and saving to Desktop…",
      "export.savedTo": "Saved to: {path}",
      "export.failed": "Save failed",
      "reader.practice": "Practice",
      "reader.notFound": "Lecture not found",
      "reader.notFoundText": "Back to the library.",
      "reader.backLibrary": "Back to library",
      "settings.backup": "Backup",
      "settings.backupMeta": "ZIP · local file",
      "settings.backupNote": "Download a ZIP with the database, chat, lecture files and original uploads. Inspect it before restoring; never overwrite a database that is in use.",
      "settings.backupNow": "Back up now",
      "exam.afterGenerateHint": "The finished paper opens in a separate reader; previous papers live under Papers on the course page.",
      "exam.issueTitle": "Generation incomplete · {n} issues:",
      "exam.noArtifactTitle": "No lecture available for a paper",
      "exam.noArtifactText": "Create a lecture first, then choose its scope and mode.",
      "exam.subjectChem": "Chemistry",
      "exam.subjectCS": "Computer science",
      "exam.subjectBio": "Biology",
      "task.disclaimer": "Generated by TermFinale for revision reference; always check against the source material.",
      "task.edit": "Edit",
      "task.export": "Export HTML",
      "task.word": "Export Word",
      "task.pdf": "Export PDF",
      "task.print": "Print",
      "task.mindmap": "Mind map",
      "task.mindmapHint": "8–40 nodes with parent and page numbers; partial coverage is marked when pages are missing.",
      "wb.historyHint": "Past outputs live in Course tools; the reader opens after generation.",
    },
  };

  function t(key, vars = {}) {
    const table = I18N[state.lang] || I18N.zh;
    let value = table[key];
    if (value === undefined) value = I18N.zh[key];
    if (value === undefined) return key;
    if (typeof value === "function") return String(value(vars));
    return String(value).replace(/\{(\w+)\}/g, (match, name) =>
      vars[name] === undefined ? match : String(vars[name])
    );
  }

  function applyLang(next) {
    const lang = ["zh", "hant", "en"].includes(next) ? next : "zh";
    state.lang = lang;
    document.documentElement.lang = lang === "en" ? "en" : lang === "hant" ? "zh-Hant" : "zh-CN";
    localStorage.setItem("tf-ui-lang", lang);
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      el.setAttribute("aria-label", t(el.dataset.i18nAria));
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder));
    });
    document.title = t("app.title");
    const langBtn = document.getElementById("langBtn");
    if (langBtn) {
      const currentLabel = { zh: "简", hant: "繁", en: "EN" }[lang];
      langBtn.textContent = currentLabel;
      langBtn.setAttribute("aria-label", "切换界面语言");
      langBtn.title = "切换界面语言 / 切換介面語言 / Switch language";
    }
    document.addEventListener("click", (e) => {
    if (!activeGenerationJob) return;
    const a = e.target.closest && e.target.closest('a[href^="#/"]');
    if (!a) return;
    e.preventDefault();
    e.stopPropagation();
    toast(t("gen.navLocked"));
  }, true);

  window.addEventListener("afterprint", () => document.body.classList.remove("printing-doc"));
  document.querySelectorAll("[data-set-lang]").forEach((b) => {
      b.classList.toggle("on", b.dataset.setLang === lang);
      b.setAttribute("aria-pressed", b.dataset.setLang === lang ? "true" : "false");
    });
    const themeBtn = document.getElementById("themeBtn");
    if (themeBtn) themeBtn.setAttribute("aria-label", t("aria.theme"));
    const menuBtn = document.getElementById("menuBtn");
    if (menuBtn) menuBtn.setAttribute("aria-label", t("aria.menu"));
  }

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

  const fmt = (s) => String(s ?? "").trim();

  async function api(path, opts = {}) {
    const options = { headers: { "Content-Type": "application/json" }, ...opts };
    if (options.body && typeof options.body !== "string") options.body = JSON.stringify(options.body);
    let res;
    try {
      res = await fetch(path, options);
    } catch (e) {
      throw new Error(t("error.network"));
    }
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) {
      const msg = data && (data.detail || data.message) ? (data.detail || data.message) : t("error.request", { status: res.status });
      throw new Error(msg);
    }
    return data;
  }

  async function setLang(next) {
    const lang = ["zh", "hant", "en"].includes(next) ? next : "zh";
    const changed = lang !== state.lang;
    applyLang(lang);
    const jobs = [];
    if (changed) jobs.push(route());
    jobs.push(api("/api/settings", { method: "POST", body: { lang } }).catch(() => null));
    await Promise.all(jobs);
  }

  function toast(msg, ms) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    clearTimeout(toast._t);
    // 跳过页/降级原因这类信息比普通提示更需要读完时间。
    const hold = Math.max(1600, Math.min(9000, Number(ms) || 2600));
    toast._t = setTimeout(() => { toastEl.hidden = true; }, hold);
  }

  function requestErrorMessage(err, fallback = "") {
    const raw = String((err && err.message) || "").trim();
    if (!raw || /Failed to fetch|NetworkError|Load failed|fetch failed|Network request failed|The Internet connection appears to be offline/i.test(raw)) {
      return t("error.network");
    }
    return raw || fallback || t("error.actionFailed");
  }

  function math(root) {
    if (!window.renderMathInElement) return;
    try {
      window.renderMathInElement(root || view, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    } catch (e) { /* formula render failure must not break the page */ }
  }

  function applyTheme(theme) {
    const value = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = value;
    localStorage.setItem("tf-theme", value);
    const btn = document.getElementById("themeBtn");
    if (btn) {
      btn.innerHTML = value === "dark"
        ? '<svg class="nav-ico" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2 12h2M20 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>'
        : '<svg class="nav-ico" viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 0 1 9.5 4a7 7 0 1 0 10.5 10.5z"/></svg>';
    }
  }

  async function saveTheme(theme) {
    applyTheme(theme);
    try { await api("/api/settings", { method: "POST", body: { theme } }); } catch (e) { /* local theme takes effect first */ }
  }

  function applyProfile(s) {
    const name = String((s && s.name) || "").trim() || t("user.default");
    const nameEl = document.getElementById("userName");
    const avatarEl = document.getElementById("userAvatar");
    if (nameEl) nameEl.textContent = name;
    if (avatarEl) {
      const avatar = String((s && s.avatar) || "");
      if (avatar) { avatarEl.textContent = ""; avatarEl.style.backgroundImage = `url(${JSON.stringify(avatar)})`; avatarEl.classList.add("has-image"); }
      else { avatarEl.textContent = Array.from(name)[0] || "学"; avatarEl.style.backgroundImage = ""; avatarEl.classList.remove("has-image"); }
    }
    const greet = document.querySelector(".cc-greeting h1");
    if (greet) greet.textContent = greeting({ lang: state.lang }, name);
    const schoolRow = document.getElementById("userSchoolRow");
    if (schoolRow) {
      const school = String((s && s.school) || "").trim();
      const tier = String((s && s.school_tier) || "").trim();
      const major = String((s && s.major) || "").trim();
      if (school) {
        schoolRow.hidden = false;
        const schoolName = document.getElementById("userSchoolName");
        const majorEl = document.getElementById("userMajor");
        const schoolLogo = document.getElementById("userSchoolLogo");
        const fallback = document.getElementById("userSchoolFallback");
        if (schoolName) schoolName.textContent = school;
        if (majorEl) majorEl.textContent = major || "专业未填";
        if (schoolLogo) {
          const logo = String((s && s.school_logo) || "");
          if (logo) {
            schoolLogo.src = logo; schoolLogo.hidden = false;
            schoolLogo.onerror = () => { schoolLogo.hidden = true; if (fallback) { fallback.hidden = false; fallback.textContent = school.slice(0, 1); } };
            if (fallback) fallback.hidden = true;
          } else {
            schoolLogo.hidden = true;
            if (fallback) { fallback.hidden = false; fallback.textContent = school.slice(0, 1); }
          }
        }
      } else schoolRow.hidden = true;
    }
  }

  let profileAvatarDraft = "";

  async function saveKeys() {
    const ds = document.getElementById("deepseekKeyInput");
    const aliyun = document.getElementById("dashscopeKeyInput");
    const kimi = document.getElementById("kimiKeyInput");
    const payload = { deepseek: ds ? ds.value.trim() : "", dashscope: aliyun ? aliyun.value.trim() : "", kimi: kimi ? kimi.value.trim() : "" };
    if (!payload.deepseek && !payload.dashscope && !payload.kimi) { toast(t("settings.keyNoInput")); return; }
    const btn = document.getElementById("keySaveBtn");
    if (btn) btn.disabled = true;
    try {
      const r = await api("/api/settings/keys", { method: "POST", body: payload });
      const dsStatus = document.getElementById("deepseekKeyStatus");
      const asStatus = document.getElementById("dashscopeKeyStatus");
      if (dsStatus && r.deepseek !== undefined) { dsStatus.textContent = r.deepseek ? t("status.configured") : t("status.notConfigured"); dsStatus.className = `badge ${r.deepseek ? "badge-good" : "badge-bad"}`; }
      if (asStatus && r.dashscope !== undefined) { asStatus.textContent = r.dashscope ? t("status.configured") : t("status.notConfigured"); asStatus.className = `badge ${r.dashscope ? "badge-good" : "badge-bad"}`; }
      const kmStatus = document.getElementById("kimiKeyStatus");
      if (kmStatus && r.kimi !== undefined) { kmStatus.textContent = r.kimi ? t("status.configured") : t("status.notConfigured"); kmStatus.className = `badge ${r.kimi ? "badge-good" : "badge-bad"}`; }
      if (ds) ds.value = ""; if (aliyun) aliyun.value = "";
      toast(t("settings.keySaved"));
    } catch (e) { toast(e.message || t("settings.keySaveFailed")); }
    finally { if (btn) btn.disabled = false; }
  }

  async function testKeys() {
    const btn = document.getElementById("keyTestBtn");
    const out = document.getElementById("keyTestResult");
    if (btn) { btn.disabled = true; btn.textContent = t("settings.keyTesting"); }
    if (out) out.textContent = t("settings.keyTesting");
    try {
      const r = await api("/api/settings/test", { method: "POST", body: {} });
      const fmt = (name, v) => `${name}: ${v === "ok" ? t("settings.keyTestOk") : v === "未配置" ? t("settings.keyNotSet") : (v || t("settings.keyTestFail"))}`;
      if (out) out.textContent = `${fmt("DeepSeek", r.deepseek)} ｜ ${fmt("阿里云百炼", r.dashscope)} ｜ ${fmt("Kimi", r.kimi)}`;
    } catch (e) { if (out) out.textContent = e.message || t("settings.keyTestFail"); }
    finally { if (btn) { btn.disabled = false; btn.textContent = t("settings.testKeys"); } }
  }

  async function saveProfile() {
    const input = document.getElementById("profileName");
    if (!input) return;
    const name = input.value.trim();
    if (!name) { toast(t("settings.profileName")); return; }
    const schoolInput = document.getElementById("profileSchool");
    const tierInput = document.getElementById("profileSchoolTier");
    const majorInput = document.getElementById("profileMajor");
    const school = String(schoolInput ? schoolInput.value : "").trim();
    const tier = String(tierInput ? tierInput.value : "").trim();
    const major = String(majorInput ? majorInput.value : "").trim();
    if (!school || !tier || !major) { toast(t("settings.schoolRequired")); return; }
    const resolvedLogo = (schoolInput && schoolInput.dataset.logo) || (await resolveSchoolLogo(school)) || (state.settings && state.settings.school_logo) || "";
    try {
      const s = await api("/api/settings", { method: "POST", body: { name, avatar: profileAvatarDraft, school,
        school_tier: tier, school_logo: resolvedLogo, major } });
      state.settings = s;
      applyProfile(s);
      toast(t("settings.profileSaved"));
    } catch (e) { toast(e.message || t("error.request")); }
  }

  function qualityStatusLabel(q) {
    if (!q) return "";
    if (q.status === "delivered") return t("status.delivered");
    if (q.status === "review") return t("status.review");
    if (q.status === "rejected") return t("status.rejected");
    return String(q.status || "");
  }

  function docStatusLabel(status) {
    if (status === "validated") return t("status.passed");
    if (status === "partial") return t("status.partialDelivery");
    if (status === "rejected") return t("status.rejected");
    return status || t("status.draft");
  }

  // Coverage arrives as a server-formatted string (for example "85/85 页").
  // Its unit is metadata, not source content, so localize the unit in EN.
  function coverageLabel(value) {
    const raw = String(value ?? "").trim();
    if (!raw || state.lang !== "en") return raw;
    return raw
      .replace(/\s*页/g, ` ${t("meta.pages")}`)
      .replace(/\s*节/g, ` ${t("meta.sections")}`)
      .replace(/\s*图/g, ` ${t("meta.figures")}`)
      .replace(/\s*张/g, ` ${t("meta.items")}`)
      .replace(/全/g, t("meta.all"))
      .replace(/[、，]/g, ", ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function statusBadge(q) {
    const cls = q.status === "delivered" ? "good" : q.status === "review" ? "warn" : "bad";
    return `<span class="badge badge-${cls}"><i class="dot"></i>${esc(qualityStatusLabel(q))}</span>`;
  }

  function auditLine(q) {
    if (!q.audit_present) return t("quality.noAudit");
    const a = q.audit || {};
    const gaps = (a.partial || 0) + (a.missing || 0);
    if (state.lang === "en") return `${a.covered || 0} pages covered${gaps ? ` · ${gaps} to fill` : ""}`;
    if (state.lang === "hant") return `已覆蓋 ${a.covered || 0} 頁${gaps ? ` · 待補 ${gaps} 頁` : ""}`;
    return `已覆盖 ${a.covered || 0} 页${gaps ? ` · 待补 ${gaps} 页` : ""}`;
  }

  function cleanSourceName(name) {
    return String(name || "").replace(/^\d+_/, "").replace(/\.(pdf|pptx|docx|png|jpe?g|webp)$/i, "");
  }

  function artifactCard(a, opts = {}) {
    const q = a.quality;
    if (a.source_only) {
      const key = opts.courseKey || "";
      const editMode = !!opts.editMode;
      const editHref = `#/course/${encodeURIComponent(key)}/edit?artifact=${encodeURIComponent(a.id)}`;
      const href = editMode ? editHref : `#/read/${encodeURIComponent(a.id)}`;
      const sources = Array.isArray(a.sources) ? a.sources : [];
      const names = sources.map((x) => x && x.name).filter(Boolean);
      const displayTitle = (a.title === "课程资料" && names[0]) ? cleanSourceName(names[0]) : a.title;
      return `<article class="card click source-card ${editMode ? "card-editing" : ""}" onclick="if(!event.target.closest('a,button')) location.hash='${href}'">
        <div class="card-top"><div><h3 class="card-title">${esc(displayTitle)}</h3>
          <div class="card-meta"><span>${t("course.sourceSaved")}</span><span>${t("unit.sourcePages", { n: a.page_count || 0 })}</span><span>${t("course.sourceCount", { n: sources.length || 1 })}</span></div></div>
          <div class="card-top-right"><span class="badge badge-neutral">${t("course.sourceSaved")}</span>${editMode ? `<button class="card-delete" type="button" title="${t("course.deleteLecture")}" onclick="event.stopPropagation();act.deleteLecture('${esc(key)}','${esc(a.id)}')">${t("course.deleteLecture")}</button>` : ""}</div></div>
        <div class="card-body"><div>${esc(names.length ? names.join("、") : t("course.sourceSavedHint"))}</div>
          <div class="mt-8 small muted">${t("course.sourceOnlyHint")}</div></div>
        <div class="card-actions">${editMode ? `<a class="btn btn-primary" href="${editHref}">${t("course.editLecture")}</a>` : `<a class="btn btn-primary" href="${href}">${t("course.readSource")}</a><a class="btn btn-ghost" href="#/workbench?artifact=${encodeURIComponent(a.id)}">${t("course.openTools")}</a>`}</div>
      </article>`;
    }
    const pages = a.pdf_pages ? t("unit.lecturePages", { n: a.pdf_pages }) : "—";
    const src = a.page_count ? t("unit.sourcePages", { n: a.page_count }) : "";
    const editMode = !!opts.editMode;
    const key = opts.courseKey || "";
    const editHref = `#/course/${encodeURIComponent(key)}/edit?artifact=${encodeURIComponent(a.id)}`;
    const primaryHref = editMode ? editHref : (opts.primary === "practice"
      ? `#/practice/${encodeURIComponent(a.id)}`
      : `#/read/${encodeURIComponent(a.id)}`);
    const primaryText = editMode ? t("course.editLecture") : (opts.primary === "practice" ? t("card.practiceThis") : t("card.read"));
    const actions = editMode
      ? `<a class="btn btn-primary" href="${editHref}">${t("course.editLecture")}</a>`
      : `<a class="btn btn-primary" href="${primaryHref}">${primaryText}</a>
        <a class="btn btn-ghost" href="#/artifact/${encodeURIComponent(a.id)}">${t("card.quality")}</a>
        ${opts.practice === false ? "" : `<a class="btn btn-ghost" href="#/practice/${encodeURIComponent(a.id)}">${t("card.practice")}</a>`}`;
    return `<article class="card click ${opts.tone ? `tone-${opts.tone}` : ""} ${editMode ? "card-editing" : ""}" onclick="if(!event.target.closest('a,button')) location.hash='${editMode ? editHref : primaryHref}'">
      <div class="card-top">
        <div>
          <h3 class="card-title">${esc(a.title)}</h3>
          <div class="card-meta">
            <span>${esc(pages)}</span>${src ? `<span>${esc(src)}</span>` : ""}
            <span>${t("unit.sections", { n: a.sections || 0 })}</span><span>${t("unit.figures", { n: a.figures || 0 })}</span>
          </div>
        </div>
        <div class="card-top-right">${a.pending_regeneration ? `<span class="badge badge-warn">${t("course.pendingRebuild")}</span>` : ""}${statusBadge(q)}${editMode ? `<button class="card-delete" type="button" title="${t("course.deleteLecture")}" onclick="event.stopPropagation();act.deleteLecture('${esc(key)}','${esc(a.id)}')">${t("course.deleteLecture")}</button>` : ""}</div>
      </div>
      <div class="card-body">
        <div>${esc(a.coverage ? coverageLabel(a.coverage) : t("card.noCoverage"))}</div>
        <div class="mt-8 small">${esc(auditLine(q))}</div>
      </div>
      <div class="card-actions">${actions}</div>
    </article>`;
  }

  function empty(title, text, actions = "") {
    return `<div class="empty"><h3>${esc(title)}</h3><p>${esc(text)}</p>${actions}</div>`;
  }

  function errorBox(message, retry = "") {
    return `<div class="banner bad"><div><strong>${t("error.title")}</strong><div class="small">${esc(message)}</div></div>${retry}</div>`;
  }

  function loading(text = t("loading.default")) {
    return `<div class="loading"><span class="spinner"></span>${esc(text)}</div>`;
  }

  let subjectNavCache = null;
  let subjectNavPromise = null;

  function renderSubjectNav(courses) {
    const el = document.getElementById("subjectNav");
    if (!el) return;
    subjectNavCache = courses || [];
    el.innerHTML = subjectNavCache.length
      ? subjectNavCache.map((c) => '<a href="#/course/' + encodeURIComponent(c.key) + '" data-subject="' + esc(c.key) + '"><span class="nav-ico subject-dot" aria-hidden="true"></span><span>' + esc(c.name) + '</span></a>').join("")
      : '<span class="subject-nav-empty">还没有学科</span>';
    syncSubjectNav();
  }

  async function loadSubjectNav() {
    if (subjectNavCache || subjectNavPromise) return subjectNavPromise || Promise.resolve(subjectNavCache);
    subjectNavPromise = api("/api/courses").then((courses) => { renderSubjectNav(courses || []); return courses; }).catch(() => null).finally(() => { subjectNavPromise = null; });
    return subjectNavPromise;
  }

  function syncSubjectNav() {
    const hash = (location.hash || "#/").split("?")[0];
    document.querySelectorAll("[data-subject]").forEach((a) => {
      const key = a.getAttribute("href") || "";
      a.classList.toggle("active", hash === key || hash.startsWith(key + "/"));
    });
  }

  // 侧栏高亮块平滑跟随：只动 transform，避免 layout 抖动
  function moveNavIndicator() {
    const nav = document.querySelector(".nav");
    if (!nav) return;
    let ind = nav.querySelector(".nav-indicator");
    if (!ind) {
      ind = document.createElement("span");
      ind.className = "nav-indicator";
      ind.setAttribute("aria-hidden", "true");
      nav.appendChild(ind);
    }
    const active = nav.querySelector("a.active");
    if (!active) { ind.style.opacity = "0"; return; }
    const navBox = nav.getBoundingClientRect();
    const box = active.getBoundingClientRect();
    ind.style.opacity = "1";
    ind.style.transform = `translateY(${Math.round(box.top - navBox.top)}px)`;
    ind.style.height = `${Math.round(box.height)}px`;
  }

  // 卡片聚光：鼠标位置写入 --mx/--my（rAF 节流，只在卡片上生效）
  let spotRaf = 0;
  let spotTarget = null;
  function handleSpotlight(event) {
    const card = event.target && event.target.closest ? event.target.closest("[data-spotlight]") : null;
    if (!card) return;
    const box = card.getBoundingClientRect();
    const mx = ((event.clientX - box.left) / Math.max(1, box.width)) * 100;
    const my = ((event.clientY - box.top) / Math.max(1, box.height)) * 100;
    spotTarget = { card, mx, my };
    if (spotRaf) return;
    spotRaf = requestAnimationFrame(() => {
      spotRaf = 0;
      if (!spotTarget) return;
      spotTarget.card.style.setProperty("--mx", `${spotTarget.mx}%`);
      spotTarget.card.style.setProperty("--my", `${spotTarget.my}%`);
    });
  }
  document.addEventListener("pointermove", handleSpotlight, { passive: true });
  window.addEventListener("resize", () => requestAnimationFrame(moveNavIndicator));

  function setNav(name) {
    syncSubjectNav();
    document.querySelectorAll("[data-nav]").forEach((a) => {
      a.classList.toggle("active", a.dataset.nav === name);
    });
    requestAnimationFrame(moveNavIndicator);
  }

  function setCrumb(text) { crumb.textContent = text; }

  function pageRange(pages) {
    if (!pages || !pages.length) return "—";
    const a = Math.min(...pages), b = Math.max(...pages);
    return a === b ? String(a) : `${a}–${b}`;
  }

  function pageHead(eyebrow, title, lede, actions = "") {
    return `<div class="page-head">
      <div class="eyebrow">${esc(eyebrow)}</div>
      <h1>${esc(title)}</h1>
      ${lede ? `<p class="lede">${esc(lede)}</p>` : ""}
      ${actions ? `<div class="actions">${actions}</div>` : ""}
    </div>`;
  }

  function qualityItem(ok, title, detail) {
    const cls = ok === true ? "q-ok" : ok === false ? "q-bad" : "q-warn";
    const icon = ok === true ? "✓" : ok === false ? "!" : "?";
    return `<div class="q-item"><div class="q-icon ${cls}">${icon}</div><div class="q-text"><strong>${esc(title)}</strong><span>${esc(detail)}</span></div></div>`;
  }

  // ---------------- routes ----------------

  const SCHOOL_TIERS = ["985", "211", "一本", "二本", "专科高职"];

  async function loadSchoolCatalog() {
    if (schoolCatalog) return schoolCatalog;
    if (!schoolCatalogPromise) {
      schoolCatalogPromise = fetch("/static/schools.json")
        .then((r) => r.ok ? r.json() : [])
        .then((rows) => { schoolCatalog = Array.isArray(rows) ? rows : []; return schoolCatalog; })
        .catch(() => { schoolCatalog = []; return schoolCatalog; });
    }
    return schoolCatalogPromise;
  }

  function schoolTierOptions(selected) {
    return SCHOOL_TIERS.map((x) => `<option value="${x}" ${x === selected ? "selected" : ""}>${x}</option>`).join("");
  }

  function attachSchoolSearch(input, menu, onPick, onInput) {
    if (!input || !menu || input.dataset.schoolBound === "1") return;
    input.dataset.schoolBound = "1";
    let rows = [];
    const paint = (list) => {
      if (!list.length) { menu.hidden = true; return; }
      menu.innerHTML = list.map((s, i) => `<button type="button" data-school-index="${i}">
        ${s.logo ? `<img src="${esc(s.logo)}" alt="" loading="lazy" onerror="this.style.display='none'">` : `<span class="school-fallback">${esc(String(s.name || "校").slice(0, 1))}</span>`}
        <span>${esc(s.name)}</span></button>`).join("");
      menu.hidden = false;
      menu.querySelectorAll("[data-school-index]").forEach((b) => {
        b.addEventListener("mousedown", (e) => e.preventDefault());
        b.onclick = () => {
          const s = rows[Number(b.dataset.schoolIndex)];
          if (!s) return;
          input.value = s.name;
          menu.hidden = true;
          onPick && onPick(s);
        };
      });
    };
    input.addEventListener("input", async () => {
      const q = input.value.trim();
      onInput && onInput(q);
      if (!q) { menu.hidden = true; return; }
      const all = await loadSchoolCatalog();
      const ql = q.toLowerCase();
      rows = all.filter((s) => String(s.name || "").toLowerCase().includes(ql));
      if (!rows.some((s) => s.name === q)) rows.push({ name: q, tier: "", logo: "" });
      paint(rows);
    });
    input.addEventListener("focus", () => { if (input.value.trim()) input.dispatchEvent(new Event("input")); });
    input.addEventListener("blur", () => setTimeout(() => { menu.hidden = true; }, 180));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") menu.hidden = true;
      if (e.key === "Enter" && !menu.hidden) {
        const first = menu.querySelector("[data-school-index]");
        if (first) { e.preventDefault(); first.click(); }
      }
    });
  }

  function schoolSelectedHtml(school, logo) {
    if (!school) return "";
    return `<div class="school-selected">${logo ? `<img src="${esc(logo)}" alt="" onerror="this.style.display='none'">` : `<span class="school-fallback">${esc(String(school).slice(0, 1))}</span>`}<span><b>${esc(school)}</b></span></div>`;
  }

  function onboardingText() {
    return {
      steps: [
        { label: t("onboard.step1"), lead: t("onboard.welcomeLead") },
        { label: t("onboard.step2"), lead: t("onboard.introLead") },
        { label: t("onboard.step3"), lead: t("onboard.profileLead") },
      ],
    };
  }

  function renderOnboarding() {
    const el = document.getElementById("onboarding");
    if (!el || el.hidden) return;
    const name = onboardingName || (state.settings && state.settings.name !== t("user.default") ? state.settings.name : "");
    const initial = (name || "学").trim().slice(0, 1);
    const avatar = onboardingAvatar || (state.settings && state.settings.avatar) || "";
    const school = onboardingSchool || (state.settings && state.settings.school) || "";
    const schoolTier = onboardingSchoolTier || (state.settings && state.settings.school_tier) || "";
    const schoolLogo = onboardingSchoolLogo || (state.settings && state.settings.school_logo) || "";
    const major = onboardingMajor || (state.settings && state.settings.major) || "";
    const rows = `
      <div class="ob-rows">
        <div class="ob-row"><b>01</b><div><h3>${t("onboard.row1")}</h3><p>${t("onboard.row1Body")}</p></div></div>
        <div class="ob-row"><b>02</b><div><h3>${t("onboard.row2")}</h3><p>${t("onboard.row2Body")}</p></div></div>
        <div class="ob-row"><b>03</b><div><h3>${t("onboard.row3")}</h3><p>${t("onboard.row3Body")}</p></div></div>
      </div>`;
    const body = onboardingStep === 0
      ? `<h2 class="ob-welcome-hero">${t("onboard.welcomeTitle")}</h2>
          <div class="ob-actions"><button class="btn btn-dark" onclick="act.onboardNext()">${t("onboard.start")}</button></div>`
      : onboardingStep === 1
        ? `<div class="ob-eyebrow">${t("onboard.introKicker")}</div><h2>${t("onboard.introTitle")}</h2>${rows}<div class="ob-actions"><button class="btn btn-line" onclick="act.onboardBack()">${t("onboard.back")}</button><button class="btn btn-dark" onclick="act.onboardNext()">${t("onboard.continue")}</button></div>`
        : `<div class="ob-eyebrow">${t("onboard.profileKicker")}</div><h2>${t("onboard.profileTitle")}</h2>
          <div class="ob-profile"><label class="ob-avatar" for="onboardAvatarFile" title="${t("onboard.avatarHint")}">${avatar ? `<img src="${esc(avatar)}" alt="avatar">` : `<span>${esc(initial)}</span>`}<i>+</i></label><input id="onboardAvatarFile" type="file" accept="image/png,image/jpeg,image/webp" hidden>
            <div class="ob-profile-fields"><label>${t("onboard.nameLabel")}</label><input id="onboardName" maxlength="24" value="${esc(name)}" placeholder="${t("onboard.namePlaceholder")}" autocomplete="off"></div></div>
          <div class="ob-school-fields"><div class="school-combo"><label>${t("onboard.schoolLabel")}</label><input id="onboardSchool" maxlength="80" value="${esc(school)}" placeholder="" autocomplete="off"><div class="school-menu" id="onboardSchoolMenu" hidden></div></div>
            <div class="field"><label>${t("onboard.tierLabel")}</label><select id="onboardTier"><option value="">${t("onboard.tierPlaceholder")}</option>${schoolTierOptions(schoolTier)}</select></div></div>
          <div class="ob-major-field"><label>${t("onboard.majorLabel")}</label><input id="onboardMajor" maxlength="60" value="${esc(major)}" placeholder="" autocomplete="off"></div>
          <div id="onboardSchoolSelected">${schoolSelectedHtml(school, schoolLogo)}</div>
          <p class="ob-note">${t("onboard.profileNote")}</p>
          <div class="ob-error" id="onboardError" hidden>${t("onboard.nameRequired")}</div>
          <div class="ob-actions"><button class="btn btn-line" onclick="act.onboardBack()">${t("onboard.back")}</button><button class="btn btn-dark" onclick="act.onboardFinish()">${t("onboard.finish")}</button></div>`;
    el.innerHTML = `<canvas id="obParticles" class="ob-particles" aria-hidden="true"></canvas><div class="ob-glow ob-glow-a"></div><div class="ob-glow ob-glow-b"></div><div class="ob-orbit ob-orbit-a"></div><div class="ob-orbit ob-orbit-b"></div><div class="ob-shell"><aside class="ob-brand"><div class="ob-wordmark"><img class="ob-logo" src="/static/logo-mark.svg" alt="">TermFinale</div><div class="ob-brand-copy"><div class="ob-kicker">${t("onboard.brandKicker")}</div><h1>${t("onboard.brandTitle")}</h1><p>${t("onboard.brandBody")}</p></div></aside><main class="ob-stage"><header class="ob-top"><div class="ob-step-label">${String(onboardingStep + 1).padStart(2, "0")} / 03 · ${t("onboard.stepLabel", { n: onboardingStep + 1 })}</div><div class="ob-lang"><button data-ob-lang="zh" class="${state.lang === "zh" ? "on" : ""}">简</button><button data-ob-lang="hant" class="${state.lang === "hant" ? "on" : ""}">繁</button><button data-ob-lang="en" class="${state.lang === "en" ? "on" : ""}">EN</button></div></header><div class="ob-progress">${[0,1,2].map((i) => `<i class="${i <= onboardingStep ? "on" : ""}"></i>`).join("")}</div><div class="ob-content">${body}</div></main></div>`;
    el.querySelectorAll("[data-ob-lang]").forEach((b) => b.onclick = () => act.onboardLang(b.dataset.obLang));
    const input = document.getElementById("onboardName");
    if (input) {
      input.oninput = () => { onboardingName = input.value; };
      input.onkeydown = (e) => { if (e.key === "Enter") act.onboardFinish(); };
    }
    const schoolInput = document.getElementById("onboardSchool");
    const schoolMenu = document.getElementById("onboardSchoolMenu");
    const tierInput = document.getElementById("onboardTier");
    const majorInput = document.getElementById("onboardMajor");
    if (majorInput) majorInput.oninput = () => { onboardingMajor = majorInput.value; };
    if (schoolInput) {
      schoolInput.oninput = () => { onboardingSchool = schoolInput.value; onboardingSchoolLogo = ""; };
      attachSchoolSearch(schoolInput, schoolMenu, (s) => {
        onboardingSchool = s.name; onboardingSchoolLogo = s.logo || "";
        const box = document.getElementById("onboardSchoolSelected");
        if (box) box.innerHTML = schoolSelectedHtml(onboardingSchool, onboardingSchoolLogo);
      }, (q) => { onboardingSchool = q; });
    }
    if (tierInput) tierInput.onchange = () => { onboardingSchoolTier = tierInput.value; };
    const file = document.getElementById("onboardAvatarFile");
    if (file) file.onchange = () => {
      const f = file.files && file.files[0];
      if (!f) return;
      if (f.size > 350000) { toast(t("onboard.avatarTooBig")); return; }
      const reader = new FileReader();
      reader.onload = () => { onboardingAvatar = String(reader.result || ""); renderOnboarding(); };
      reader.readAsDataURL(f);
    };
    initOnboardingParticles();
  }

  function initOnboardingParticles() {
    const canvas = document.getElementById("obParticles");
    if (!canvas || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ctx = canvas.getContext("2d");
    let w = 0, h = 0, mx = -999, my = -999;
    const dots = Array.from({ length: 42 }, () => ({ x: Math.random(), y: Math.random(), r: Math.random() * 1.7 + .7, vx: (Math.random() - .5) * .00055, vy: (Math.random() - .5) * .00055 }));
    const size = () => { w = canvas.width = innerWidth * devicePixelRatio; h = canvas.height = innerHeight * devicePixelRatio; ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0); };
    const draw = () => {
      if (!canvas.isConnected) return;
      ctx.clearRect(0, 0, w, h);
      dots.forEach((d) => {
        d.x += d.vx; d.y += d.vy;
        if (d.x < 0 || d.x > 1) d.vx *= -1; if (d.y < 0 || d.y > 1) d.vy *= -1;
        const px = d.x * w / devicePixelRatio, py = d.y * h / devicePixelRatio;
        const near = Math.hypot(px - mx, py - my) < 120;
        ctx.beginPath(); ctx.arc(px, py, near ? d.r * 2.1 : d.r, 0, Math.PI * 2);
        ctx.fillStyle = near ? "rgba(223,255,63,.75)" : "rgba(93,103,72,.18)"; ctx.fill();
      });
      requestAnimationFrame(draw);
    };
    size(); addEventListener("resize", size, { once: false });
    const host = document.getElementById("onboarding");
    if (host) {
      host.onmousemove = (e) => { mx = e.clientX; my = e.clientY; };
      host.onmouseleave = () => { mx = my = -999; };
    }
    draw();
  }

  function showOnboarding() {
    const el = document.getElementById("onboarding");
    if (!el) return;
    el.hidden = false;
    document.body.classList.add("onboarding-mode");
    renderOnboarding();
  }

  function hideOnboarding() {
    const el = document.getElementById("onboarding");
    if (el) el.hidden = true;
    document.body.classList.remove("onboarding-mode");
  }

  function onboardLang(lang) {
    if (!["zh", "hant", "en"].includes(lang)) return;
    const input = document.getElementById("onboardName");
    if (input) onboardingName = input.value;
    const schoolInput = document.getElementById("onboardSchool");
    const tierInput = document.getElementById("onboardTier");
    if (schoolInput) onboardingSchool = schoolInput.value;
    if (tierInput) onboardingSchoolTier = tierInput.value;
    const majorInput = document.getElementById("onboardMajor"); if (majorInput) onboardingMajor = majorInput.value;
    state.lang = lang;
    localStorage.setItem("tf-ui-lang", lang);
    applyLang(lang);
    api("/api/settings", { method: "POST", body: { lang } }).catch(() => null);
    renderOnboarding();
  }

  function onboardNext() {
    if (onboardingStep === 2) return onboardFinish();
    const input = document.getElementById("onboardName");
    if (input) onboardingName = input.value;
    const schoolInput = document.getElementById("onboardSchool");
    const tierInput = document.getElementById("onboardTier");
    if (schoolInput) onboardingSchool = schoolInput.value;
    if (tierInput) onboardingSchoolTier = tierInput.value;
    const majorInput = document.getElementById("onboardMajor"); if (majorInput) onboardingMajor = majorInput.value;
    onboardingStep = Math.min(2, onboardingStep + 1);
    renderOnboarding();
  }

  function onboardBack() {
    const input = document.getElementById("onboardName");
    if (input) onboardingName = input.value;
    const schoolInput = document.getElementById("onboardSchool");
    const tierInput = document.getElementById("onboardTier");
    if (schoolInput) onboardingSchool = schoolInput.value;
    if (tierInput) onboardingSchoolTier = tierInput.value;
    const majorInput = document.getElementById("onboardMajor"); if (majorInput) onboardingMajor = majorInput.value;
    onboardingStep = Math.max(0, onboardingStep - 1);
    renderOnboarding();
  }

  async function resolveSchoolLogo(name) {
    if (!name) return "";
    const all = await loadSchoolCatalog();
    const hit = all.find((x) => x.name === name);
    return (hit && hit.logo) || "";
  }

  async function repairSchoolLogo(s) {
    if (!s || !s.school || s.school_logo) return;
    const logo = await resolveSchoolLogo(s.school);
    if (!logo) return;
    try {
      const ns = await api("/api/settings", { method: "POST", body: { school_logo: logo } });
      state.settings = ns; applyProfile(ns);
    } catch (e) {}
  }

  async function onboardFinish() {
    const input = document.getElementById("onboardName");
    const name = String((input ? input.value : onboardingName) || "").trim();
    const schoolInput = document.getElementById("onboardSchool");
    const tierInput = document.getElementById("onboardTier");
    const school = String((schoolInput ? schoolInput.value : onboardingSchool) || "").trim();
    const tier = String((tierInput ? tierInput.value : onboardingSchoolTier) || "").trim();
    const majorInput = document.getElementById("onboardMajor");
    const major = String((majorInput ? majorInput.value : onboardingMajor) || "").trim();
    if (!name) { const err = document.getElementById("onboardError"); if (err) err.hidden = false; if (input) input.focus(); return; }
    if (!school || !tier || !major) { const err = document.getElementById("onboardError"); if (err) { err.hidden = false; err.textContent = t("onboard.schoolRequired"); } if (!school && schoolInput) schoolInput.focus(); else if (majorInput) majorInput.focus(); return; }
    const resolvedLogo = onboardingSchoolLogo || (await resolveSchoolLogo(school)) || (state.settings && state.settings.school_logo) || "";
    try {
      const s = await api("/api/settings", { method: "POST", body: { name, avatar: onboardingAvatar || (state.settings && state.settings.avatar) || "",
        school, school_tier: tier, school_logo: resolvedLogo, major, onboarded: true } });
      state.settings = s;
      onboardingName = "";
      onboardingAvatar = "";
      onboardingSchool = "";
      onboardingSchoolTier = "";
      onboardingSchoolLogo = "";
      onboardingMajor = "";
      try { localStorage.removeItem("tf-guide-seen"); } catch (e) {}
      hideOnboarding();
      applyProfile(s);
      await route();
    } catch (e) { toast(e.message || t("onboard.saveFailed")); }
  }

  state.guide = state.guide || null;

  function guideBodyHtml(tab) {
    if (!tab) return `<div class="card"><h3 class="card-title">${t("guide.pendingTitle")}</h3><p class="muted">${t("guide.pendingBody")}</p></div>`;
    const sections = (tab.sections || []).map((sec) => {
      const paras = (sec.paragraphs || []).map((x) => `<p>${esc(x)}</p>`).join("");
      const bullets = (sec.bullets || []).length
        ? `<ul>${sec.bullets.map((x) => {
            if (x && typeof x === "object") {
              const text = esc(x.text || "");
              return `<li>${x.href ? `<a href="${esc(x.href)}" target="_blank" rel="noreferrer">${text}</a>` : text}</li>`;
            }
            return `<li>${esc(x)}</li>`;
          }).join("")}</ul>` : "";
      const steps = (sec.steps || []).length
        ? `<ol class="guide-steps">${sec.steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>` : "";
      const parasTail = (sec.paragraphs_tail || []).map((x) => `<p>${esc(x)}</p>`).join("");
      const table = (sec.table && Array.isArray(sec.table.rows) && sec.table.rows.length)
        ? `<div class="guide-table-wrap"><table class="guide-table"><thead><tr>${(sec.table.headers || []).map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${sec.table.rows.map((row) => `<tr>${row.map((cell) => {
            if (cell && typeof cell === "object") {
              const text = esc(cell.text || "");
              return `<td>${cell.href ? `<a href="${esc(cell.href)}" target="_blank" rel="noreferrer">${text}</a>` : text}</td>`;
            }
            return `<td>${esc(cell == null ? "" : cell)}</td>`;
          }).join("")}</tr>`).join("")}</tbody></table></div>` : "";
      const images = (sec.images || []).map((img) => {
        if (!img || !img.src) return "";
        const cap = img.caption ? `<figcaption>${esc(img.caption)}</figcaption>` : "";
        const w = Math.max(220, Math.min(640, Number(img.width) || 600));
        return `<figure class="guide-figure" style="max-width:${w}px"><img src="${esc(img.src)}" alt="${esc(img.alt || img.caption || "")}" loading="lazy">${cap}</figure>`;
      }).join("");
      return `<section class="guide-section"><h3>${esc(sec.heading || "")}</h3>${paras}${steps}${bullets}${parasTail}${table}${images}</section>`;
    }).join("");
    return `${tab.lede ? `<p class="guide-lede">${esc(tab.lede)}</p>` : ""}${sections}`;
  }

  async function renderGuide(seq) {
    try { localStorage.setItem("tf-guide-seen", "1"); } catch (e) {}
    if (!state.guide) {
      try {
        const res = await fetch("/static/guide.json", { cache: "no-store" });
        state.guide = res.ok ? await res.json() : { tabs: [] };
      } catch (e) {
        state.guide = { tabs: [], error: e.message || "说明页读取失败" };
      }
    }
    if (seq !== undefined && seq !== state.seq) return;
    const tabs = (state.guide && state.guide.tabs) || [];
    if (!tabs.length) {
      view.innerHTML = pageHead("", t("guide.title"), "", "") +
        `<div class="card mt-16"><h3 class="card-title">${t("guide.pendingTitle")}</h3>` +
        `<p class="muted">${t("guide.pendingBody")}</p></div>`;
      return;
    }
    const current = state.guideTab && tabs.some((x) => x.id === state.guideTab) ? state.guideTab : tabs[0].id;
    state.guideTab = current;
    const buttons = tabs.map((tab) => `<button type="button" data-tab="${esc(tab.id)}" class="${tab.id === current ? "on" : ""}">${esc(tab.label || tab.id)}</button>`).join("");
    view.innerHTML = pageHead("", t("guide.title"), "", "") +
      `<div class="guide-switch">${buttons}</div>
       <div id="guideBody" class="guide-page" style="min-height:calc(100vh - 300px)">${
         guideBodyHtml(tabs.find((x) => x.id === current))
       }</div>`;
    view.querySelectorAll(".guide-switch button").forEach((btn) => {
      btn.onclick = () => {
        state.guideTab = btn.dataset.tab;
        view.querySelectorAll(".guide-switch button").forEach((x) => x.classList.remove("on"));
        btn.classList.add("on");
        const body = document.getElementById("guideBody");
        if (body) body.innerHTML = guideBodyHtml(tabs.find((x) => x.id === state.guideTab));
      };
    });
  }

  function goBack(fallback, event) {
    if (event) event.preventDefault();
    const target = state.routeStack.pop();
    if (target && target !== location.hash) {
      state.skipPush = true;
      location.hash = target;
      return;
    }
    location.hash = fallback || "#/";
  }

  function canonicalHash(raw) {
    const [pathPart, queryPart] = String(raw || "#/").split("?");
    const query = queryPart ? "?" + queryPart : "";
    const clean = pathPart.replace(/\/+$/, "") || "#/";
    let target = clean;
    if (clean === "#/home" || clean === "#/index") target = "#/";
    else if (clean === "#/courses") target = "#/library";
    else if (clean === "#/drill") target = "#/practice";
    else if (clean === "#/exams") target = "#/exam";
    else if (clean === "#/reader") target = "#/read";
    else if (clean.startsWith("#/reader/")) target = "#/read/" + clean.slice("#/reader/".length);
    const tools = clean.match(/^#\/course\/([^/]+)\/tools$/);
    if (tools) target = "#/workbench?course=" + encodeURIComponent(decodeURIComponent(tools[1]));
    return target + query;
  }

  async function route() {
    const seq = ++state.seq;
    const rawHash = location.hash || "#/";
    const canonical = canonicalHash(rawHash);
    if (canonical !== rawHash) {
      try { history.replaceState(null, "", canonical); } catch (e) { location.hash = canonical; }
    }
    hideGenerationRing();
    view.classList.remove("home-view");
    const docOverlay = document.getElementById("docReaderOverlay");
    if (docOverlay) docOverlay.hidden = true;
    document.body.classList.remove("reading", "reader-iframe", "doc-reader-open");
    document.querySelector(".sidebar")?.classList.remove("open");
    const hash = location.hash || "#/";
    loadSubjectNav().catch(() => {});
    syncSubjectNav();
    const topBack = document.getElementById("topBack");
    if (topBack) {
      const ownBack = hash.startsWith("#/course") || hash.startsWith("#/new") || hash.startsWith("#/artifact") ||
        hash.startsWith("#/read") || hash.startsWith("#/bank");
      topBack.hidden = hash === "#/" || hash.startsWith("#/library") || ownBack;
    }
    if (state.lastRoute && state.lastRoute !== hash) {
      if (!state.skipPush) {
        state.routeStack.push(state.lastRoute);
        if (state.routeStack.length > 60) state.routeStack.shift();
      }
    }
    state.skipPush = false;
    state.lastRoute = hash;
    const [pathPart, queryPart] = hash.slice(1).split("?");
    const parts = pathPart.split("/").filter(Boolean);
    const query = new URLSearchParams(queryPart || "");
    try {
      if (parts.length === 0) { setNav("home"); setCrumb(""); await renderHome(seq); return; }
      if (parts[0] === "home" || parts[0] === "index") { location.hash = "#/"; return; }
      if (parts[0] === "library") { setNav("library"); setCrumb(t("nav.library")); await renderLibrary(seq); return; }
      if (parts[0] === "new") { setNav("workbench"); setCrumb(t("crumb.new")); renderNew(); return; }
      if (parts[0] === "workbench") { setNav("workbench"); setCrumb(t("nav.workbench")); await renderWorkbench(seq); return; }
      if (parts[0] === "course" && parts[1] && parts[2] === "edit") { setNav("library"); setCrumb(t("course.editTitle")); await renderCourseEdit(parts[1], seq, query); return; }
      if (parts[0] === "course" && parts[1] && parts[2] === "tools") { location.hash = "#/workbench"; return; }
      if (parts[0] === "course" && parts[1]) { setNav("library"); setCrumb(t("crumb.course")); await renderCourse(parts[1], parts[2] || "", seq); return; }
      if (parts[0] === "artifact" && parts[1]) { setNav("library"); setCrumb(t("crumb.artifact")); await renderArtifact(parts[1], seq); return; }
      if (parts[0] === "exam") { setNav("exam"); setCrumb(t("nav.exam")); await renderExam(seq); return; }
      if (parts[0] === "practice") { setNav("practice"); setCrumb(t("nav.practice")); await renderPractice(parts[1] || "", seq); return; }
      if (parts[0] === "review") { setNav("review"); setCrumb(t("nav.review")); await renderReview(seq); return; }
      if (parts[0] === "bank" && parts[1]) { setNav("library"); setCrumb(t("bank.title")); await renderBank(parts[1], seq); return; }
      if (parts[0] === "notes") { setNav("notes"); setCrumb(t("nav.notes")); await renderNotes(seq); return; }
      if (parts[0] === "settings") { setNav("settings"); setCrumb(t("nav.settings")); await renderSettings(seq); return; }
      if (parts[0] === "guide") { setNav("guide"); setCrumb(t("nav.guide")); await renderGuide(seq); return; }
      if (parts[0] === "pdf" && parts[1]) { setCrumb(t("reader.pdf")); await renderPdfViewer(parts[1], seq); return; }
      if (parts[0] === "read" && parts[1]) { setCrumb(t("crumb.read")); await renderReader(parts[1], seq, parts.slice(2).join("/")); return; }
      view.innerHTML = pageHead("404", t("notFound.title"), t("notFound.text"), `<a class="btn btn-primary" href="#/library">${t("notFound.cta")}</a>`);
    } catch (e) {
      if (seq !== state.seq) return;
      view.innerHTML = errorBox(e.message || t("error.load"), `<button class="btn btn-ghost" onclick="location.reload()">${t("error.retry")}</button>`);
    }
  }


  const COURSE_ICONS = {
    bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    hex: '<path d="m12 3 7 4v10l-7 4-7-4V7z"/><path d="M12 8v8M8.5 10v4M15.5 10v4"/>',
    pulse: '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
    flask: '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3"/><path d="M7 15h10"/>',
    book: '<path d="M5 5.5A2.5 2.5 0 0 1 7.5 3H19v18H7.5A2.5 2.5 0 0 1 5 18.5z"/><path d="M5 18.5A2.5 2.5 0 0 1 7.5 16H19"/>',
  };

  function courseCard(c, editing = false) {
    const icon = COURSE_ICONS[c.icon] || COURSE_ICONS.book;
    const href = `#/course/${encodeURIComponent(c.key)}`;
    const editHref = `#/course/${encodeURIComponent(c.key)}/edit`;
    const cd = c.exam_date ? countdown(c.exam_date) : null;
    const facts = [];
    if (c.target_score) facts.push(`${t("course.target")} ${c.target_score}`);
    if (cd) facts.push(cd.expired ? t("course.ended") : `${t("course.days")} ${cd.days}`);
    const meta = facts.join(" · ");
    const badge = c.delivered
      ? t("course.badgeLecture")
      : t("course.badgeSource");
    return `<a class="course-card course-${esc(c.color || "slate")} ${editing ? "course-card-editing" : ""}" data-spotlight href="${href}">
      <div class="course-top"><span class="course-icon"><svg viewBox="0 0 24 24">${icon}</svg></span>
        <span class="course-top-actions">${editing ? "" : `<span class="course-badge">${esc(badge)}</span>`}${editing ? `<button class="course-delete" type="button" title="${t("course.archive")}" onclick="event.preventDefault();event.stopPropagation();act.archiveCourse('${esc(c.key)}')">${t("course.deleteLecture")}</button>` : ""}</span></div>
      <h3>${esc(c.name)}</h3>
      ${meta ? `<div class="course-facts">${esc(meta)}</div>` : ""}
      <div class="course-foot">${editing ? `<button class="course-edit-cta" type="button" onclick="event.preventDefault();event.stopPropagation();location.hash='${editHref}'">${t("course.editLecture")}</button>` : `<span>${t("course.open")}</span>`}</div>
    </a>`;
  }

  function countdown(date) {
    const d = new Date(date + "T00:00:00");
    if (Number.isNaN(d.getTime())) return null;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const diff = Math.round((d - today) / 86400000);
    return { days: Math.max(0, diff), expired: diff < 0 };
  }

  function refreshCountdowns(root = document) {
    root.querySelectorAll("[data-exam]").forEach((el) => {
      const cd = countdown(el.dataset.exam || "");
      const b = el.querySelector("b"), s = el.querySelector("span");
      if (!cd) { if (b) b.textContent = "—"; if (s) s.textContent = t("course.noDate"); return; }
      if (b) b.textContent = String(cd.days);
      if (s) s.textContent = cd.expired ? t("course.ended") : cd.days === 0 ? t("course.today") : t("course.days");
    });
  }

  function greeting(L, name) {
    const n = String(name || "").trim() || t("user.default");
    const h = new Date().getHours();
    if (L.lang === "en") return `${h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"}, ${n}.`;
    if (L.lang === "hant") return `${h < 6 ? "夜深了" : h < 12 ? "早安" : h < 14 ? "午安" : h < 18 ? "下午好" : "晚上好"}，${n}。`;
    return `${h < 6 ? "夜深了" : h < 12 ? "早上好" : h < 14 ? "中午好" : h < 18 ? "下午好" : "晚上好"}，${n}。`;
  }

  async function renderHome(seq) {
    const [h, docs] = await Promise.all([
      api("/api/home"),
      api("/api/documents?limit=300").catch(() => []),
    ]);
    if (seq !== state.seq) return;
    view.classList.add("home-view");
    state.artifacts = h.artifacts || [];
    const courses = h.courses || [];
    renderSubjectNav(courses);
    const isEn = state.lang === "en";
    const isHant = state.lang === "hant";
    const L = isEn ? {
      eyebrow: "Overview", title: "Control center",
      statCourses: "Courses", statLectures: "Lectures", statPages: "Source pages",
      statQuestions: "Questions", statDue: "Due review",
      exams: "Exam countdown", recent: "Recent lectures", examsAll: "All courses",
      gauge: "Readable lectures", gaugeOk: "readable", gaugeRest: "rest",
      progress: "Course progress", quick: "Quick actions",
      newCourse: "New course", practice: "Practice", exam: "Build a paper", tools: "Content tools",
      noExam: "No exam dates yet. Set one in a course to see the countdown.",
      days: "days", today: "today", ended: "ended",
      lecturesUnit: "lectures", open: "Open",
    } : isHant ? {
      eyebrow: "總覽", title: "主控台",
      statCourses: "門課程", statLectures: "份講義", statPages: "頁資料",
      statQuestions: "道題目", statDue: "待複習",
      exams: "考試倒計時", recent: "最近講義", examsAll: "全部課程",
      gauge: "可讀講義", gaugeOk: "可讀", gaugeRest: "其餘",
      progress: "課程進度", quick: "快捷入口",
      newCourse: "新建課程", practice: "練習", exam: "出卷", tools: "內容工具",
      noExam: "還沒有設置考試時間；在課程裡填考試日期後會出現在這裡。",
      days: "天", today: "今天", ended: "已結束",
      lecturesUnit: "份講義", open: "打開",
    } : {
      eyebrow: "总览", title: "主控台",
      statCourses: "门课程", statLectures: "份讲义", statPages: "页资料",
      statQuestions: "道题目", statDue: "待复习",
      exams: "考试倒计时", recent: "最近讲义", examsAll: "全部课程",
      gauge: "可读讲义", gaugeOk: "可读", gaugeRest: "其余",
      progress: "课程进度", quick: "快捷入口",
      newCourse: "新建课程", practice: "练习", exam: "出卷", tools: "内容工具",
      noExam: "还没有设置考试时间；在课程里填考试日期后，这里会出现倒计时。",
      days: "天", today: "今天", ended: "已结束",
      lecturesUnit: "份讲义", open: "打开",
    };
    const lectures = courses.reduce((n, c) => n + ((c.artifact_ids || []).length), 0);
    const pages = courses.reduce((n, c) => n + (Number(c.pages) || 0), 0);
    const readable = (h.artifacts || []).filter((a) => (a.quality || {}).status === "delivered").length;
    const questions = (docs || []).reduce((n, d) => {
      const secs = (d.content && d.content.sections) || [];
      return n + secs.reduce((m, sec) => m + ((sec.questions || []).length), 0);
    }, 0);
    const due = Number(h.due_count || 0);
    const pct = lectures ? Math.max(0, Math.min(100, Math.round((readable / lectures) * 100))) : 0;

    const today = new Date(); today.setHours(0, 0, 0, 0);
    const examRows = courses.filter((c) => c.exam_date).map((c) => {
      const d = new Date(c.exam_date + "T00:00:00");
      const days = Number.isNaN(d.getTime()) ? null : Math.round((d - today) / 86400000);
      return { c, days };
    }).filter((x) => x.days !== null).sort((a, b) => a.days - b.days).slice(0, 5);
    const examHtml = examRows.length ? examRows.map(({ c, days }) => {
      const ended = days < 0;
      const label = ended ? L.ended : days === 0 ? L.today : `${days}<small>${L.days}</small>`;
      const meta = [c.exam_date, c.target_score ? `目标 ${c.target_score}` : "", `${(c.artifact_ids || []).length} ${L.lecturesUnit}`].filter(Boolean).join(" · ");
      return `<a class="cc-exam" href="#/course/${encodeURIComponent(c.key)}">
        <span class="days ${ended ? "ended" : ""}">${label}</span>
        <span class="who"><b>${esc(c.name)}</b><span>${esc(meta)}</span></span>
        <span class="go">${L.open} →</span>
      </a>`;
    }).join("") : "";
    const recentRows = [...(h.artifacts || [])].slice(0, 5).map((a) => `<a class="cc-exam" href="#/artifact/${encodeURIComponent(a.id)}">
      <span class="days">${Number(a.pdf_pages || a.page_count || 0)}<small>页</small></span>
      <span class="who"><b>${esc(a.title || a.id)}</b><span>${(a.sections || 0)} 节 · ${(a.quality || {}).label || ""}</span></span>
      <span class="go">${L.open} →</span></a>`).join("");
    const examTitle = examRows.length ? L.exams : L.recent;
    const examBody = examRows.length ? examHtml : (recentRows || `<div class="cc-empty">${L.noExam}</div>`);

    const topCourses = [...courses].sort((a, b) => (b.artifact_ids || []).length - (a.artifact_ids || []).length).slice(0, 5);
    const progressHtml = topCourses.map((c) => {
      const n = (c.artifact_ids || []).length;
      const ok = Number(c.delivered) || 0;
      const w = n ? Math.round((ok / n) * 100) : 0;
      return `<div class="cc-progress-row">
        <span class="nm">${esc(c.name)}</span>
        <span class="bar"><i style="width:${w}%"></i></span>
        <span class="num">${ok}/${n}</span>
      </div>`;
    }).join("") || `<div class="cc-empty">—</div>`;

    const icon = (d) => `<svg viewBox="0 0 24 24">${d}</svg>`;
    view.innerHTML = `<section class="cc-dash">
      <header class="cc-top">
        <div>
          <div class="eyebrow">${L.eyebrow}</div>
          <h1>${L.title}</h1>
          <div class="cc-sub">${esc(greeting(L, state.settings && state.settings.name))} · ${courses.length} ${L.statCourses} · ${lectures} ${L.statLectures}</div>
        </div>
        <div class="actions">
          <a class="btn btn-primary" href="#/new">＋ ${L.newCourse}</a>
          <a class="btn btn-ghost" href="#/review">${L.practice}</a>
        </div>
      </header>
      <div class="cc-summary">
        <div class="cc-sum"><b>${courses.length}</b><span>${L.statCourses}</span></div>
        <div class="cc-sum"><b>${lectures}</b><span>${L.statLectures}</span></div>
        <div class="cc-sum"><b>${pages}</b><span>${L.statPages}</span></div>
        <div class="cc-sum"><b>${questions}</b><span>${L.statQuestions}</span></div>
        <div class="cc-sum"><b>${due}</b><span>${L.statDue}</span></div>
      </div>
      <div class="cc-grid">
        <div class="cc-panel">
          <div class="cc-panel-head"><h2>${examTitle}</h2><a href="#/library">${L.examsAll} →</a></div>
          ${examBody}
        </div>
        <div class="cc-panel">
          <div class="cc-panel-head"><h2>${L.gauge}</h2><span class="small muted">${readable}/${lectures || 0}</span></div>
          <div class="cc-gauge">
            <div class="cc-gauge-ring" style="--pct:${pct}">
              <div class="cc-gauge-core"><b>${pct}%</b><span>${L.gaugeOk}</span></div>
            </div>
          </div>
          <div class="cc-gauge-legend"><span><i></i>${L.gaugeOk} ${readable}</span><span><i class="gray"></i>${L.gaugeRest} ${Math.max(0, lectures - readable)}</span></div>
        </div>
        <div class="cc-panel">
          <div class="cc-panel-head"><h2>${L.progress}</h2><a href="#/library">${L.examsAll} →</a></div>
          <div class="cc-progress">${progressHtml}</div>
        </div>
        <div class="cc-panel">
          <div class="cc-panel-head"><h2>${L.quick}</h2></div>
          <div class="cc-quick">
            <a href="#/new">${icon('<path d="M12 5v14M5 12h14"/>')}${L.newCourse}</a>
            <a href="#/review">${icon('<path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5"/>')}${L.practice}</a>
            <a href="#/exam">${icon('<path d="M7 3h10v18H7zM9 7h6M9 11h6M9 15h4"/>')}${L.exam}</a>
            <a href="#/workbench">${icon('<path d="M4 7h16M4 12h16M4 17h10"/>')}${L.tools}</a>
          </div>
        </div>
      </div>
    </section>`;
    math(view);
  }

  function initControl(L, stats) {
    const stage = document.getElementById("orbitStage");
    const nodes = [...document.querySelectorAll(".orbit-node")];
    const routes = { course: "#/library", drill: "#/practice", recall: "#/review", exam: "#/exam" };
    let active = "course";
    function paint(mode) {
      active = mode;
      nodes.forEach((n) => n.classList.toggle("on", n.dataset.mode === mode));
    }
    nodes.forEach((n) => {
      n.addEventListener("mouseenter", () => paint(n.dataset.mode));
      n.addEventListener("focus", () => paint(n.dataset.mode));
      n.addEventListener("click", () => { location.hash = routes[n.dataset.mode] || "#/library"; });
    });
    paint(active);
    // decorative particle field; no timer, no fake task
    const canvas = document.getElementById("ccParticles");
    if (canvas && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const ctx = canvas.getContext("2d");
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      let w = 0, h = 0, mx = -999, my = -999, raf = 0, last = 0, visible = true;
      const dots = Array.from({length: 36}, () => ({x: Math.random(), y: Math.random(), r: Math.random()*1.6+.6, vx: (Math.random()-.5)*.0007, vy: (Math.random()-.5)*.0007}));
      function size() {
        const r = stage.getBoundingClientRect();
        w = Math.max(1, r.width); h = Math.max(1, r.height);
        canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
      function draw(ts) {
        raf = 0;
        if (!canvas.isConnected || document.hidden || !visible) return;
        const dt = last ? Math.min(2.2, Math.max(.4, (ts - last) / 16.67)) : 1;
        last = ts;
        ctx.clearRect(0, 0, w, h);
        for (const d of dots) {
          d.x += d.vx * dt; d.y += d.vy * dt;
          if (d.x < 0 || d.x > 1) d.vx *= -1;
          if (d.y < 0 || d.y > 1) d.vy *= -1;
          const px = d.x * w, py = d.y * h;
          const dist = Math.hypot(px - mx, py - my);
          ctx.beginPath();
          ctx.arc(px, py, d.r * (dist < 90 ? 2 : 1), 0, Math.PI * 2);
          const dark = document.documentElement.dataset.theme === "dark";
          ctx.fillStyle = dist < 90 ? (dark ? "rgba(217,255,122,.95)" : "rgba(94,120,28,.95)")
            : (dark ? "rgba(205,226,177,.52)" : "rgba(66,82,51,.44)");
          ctx.fill();
        }
        raf = requestAnimationFrame(draw);
      }
      const start = () => { if (!raf && !document.hidden && visible) raf = requestAnimationFrame(draw); };
      size();
      if (window.ResizeObserver) new ResizeObserver(size).observe(stage); else addEventListener("resize", size);
      if (window.IntersectionObserver) {
        new IntersectionObserver((entries) => {
          visible = !!(entries[0] && entries[0].isIntersecting);
          if (visible) { last = 0; start(); }
        }, { threshold: .05 }).observe(stage);
      }
      document.addEventListener("visibilitychange", () => {
        if (!document.hidden) { last = 0; start(); }
      });
      stage.addEventListener("mousemove", (e) => { const r = stage.getBoundingClientRect(); mx = e.clientX-r.left; my = e.clientY-r.top; });
      stage.addEventListener("mouseleave", () => { mx = my = -999; });
      start();
    }
  }

  async function libraryEditToggle() {
    state.libraryEditing = !state.libraryEditing;
    await renderLibrary(++state.seq);
  }

  async function renderLibrary(seq) {
    const courses = await api("/api/courses");
    if (seq !== state.seq) return;
    const editing = !!state.libraryEditing;
    view.innerHTML = `<div class="library-head"><h1>${t("library.title")}</h1><div class="library-actions">${courses.length ? `<button class="btn ${editing ? "btn-primary" : "btn-ghost"}" type="button" onclick="act.libraryEditToggle()">${editing ? t("course.finishEdit") : t("course.edit")}</button>` : ""}<a class="btn btn-ghost" href="#/new">＋ ${t("course.newCourse")}</a></div></div>
      <div class="grid grid-3">${courses.map((c) => courseCard(c, editing)).join("") || empty(t("library.emptyTitle"), t("library.emptyText"), `<a class="btn btn-primary" href="#/new">${t("library.cta")}</a>`)}</div>`;
    math(view);
  }

  async function renderCourseEdit(key, seq, query) {
    let info;
    try { info = await api(`/api/courses/${encodeURIComponent(key)}/edit`); }
    catch (e) {
      if (seq !== state.seq) return;
      view.innerHTML = pageHead(t("course.editTitle"), t("course.editTitle"), t("course.editLede"), `<a class="btn btn-ghost" href="#" onclick="act.back('#/course/${encodeURIComponent(key)}', event)">${t("course.editBack")}</a>`);
      return;
    }
    if (seq !== state.seq) return;
    const c = info.course || {};
    setCurrentCourseKey(key, c.name || "");
    const arts = info.artifacts || [];
    const wanted = query.get("artifact") || "";
    const selected = arts.find((a) => a.id === wanted) || arts[0];
    if (!selected) {
      view.innerHTML = pageHead(t("course.editTitle"), t("course.editTitle"), t("course.editLede"), `<a class="btn btn-ghost" href="#" onclick="act.back('#/course/${encodeURIComponent(key)}', event)">${t("course.editBack")}</a>`) +
        empty(t("course.editNoSource"), t("course.editNoSourceBody"), `<a class="btn btn-primary" href="#/new">${t("library.cta")}</a>`);
      return;
    }
    const h = selected.header || {};
    const ep = selected.edit_params || {};
    const title = selected.title || ep.title || h.title || "";
    const daysValue = Math.max(1, Math.min(30, Number(ep.days_left || c.days_left) || 7));
    const foundationValue = ep.foundation || c.foundation || "基础较弱";
    const keyPointsValue = ep.key_points || c.key_points || "";
    const excludedValue = ep.excluded || c.excluded || "";
    const customValue = ep.custom_prompt || c.custom_prompt || "";
    const personaValue = ep.persona || "老师";
    const langValue = ep.gen_lang || "zh";
    const sourceRow = (src, checked) => `<div class="edit-source-row ${checked ? "" : "removed"}"><label class="check"><input type="checkbox" class="edit-source-check" data-source-name="${esc(src.name)}" ${checked ? "checked" : ""}> <span>${esc(src.name)}</span></label><input type="number" class="edit-source-weight" value="${Number(src.weight) || 1}" min="1" max="5" step="0.5" aria-label="weight"><span class="small muted">${Math.max(1, Math.round(src.size / 1024))} KB</span><button type="button" class="edit-source-remove" title="移除">×</button></div>`;
    const srcRows = (selected.sources || []).map((src) => sourceRow(src, true)).join("");
    const excludedRows = (selected.excluded_sources || []).map((src) => sourceRow(src, false)).join("");
    const artOptions = arts.map((a) => `<option value="${esc(a.id)}" ${a.id === selected.id ? "selected" : ""}>${esc(a.title || a.id)}</option>`).join("");
    view.innerHTML = pageHead(t("course.editTitle"), t("course.editTitle"), t("course.editLede"),
      `<a class="btn btn-ghost" href="#" onclick="act.back('#/course/${encodeURIComponent(key)}', event)">${t("course.editBack")}</a>`) +
      `<form id="courseEditForm" class="card" onsubmit="event.preventDefault();act.saveCourseEdit('${esc(key)}')">
        <section class="form-section">
          <div class="form-section-head"><h3>${t("course.editSectionSources")}</h3><p>${t("course.editSectionSourcesHint")}</p></div>
          <div class="form-grid">
            <div class="field wide"><label>${t("course.editSourceLecture")}</label><select id="editArtifact" onchange="location.hash='#/course/${encodeURIComponent(key)}/edit?artifact='+encodeURIComponent(this.value)">${artOptions}</select></div>
            <div class="field wide"><label>${t("course.editExistingSources")}</label><div class="edit-source-list">${srcRows || `<div class="small muted">${t("course.editNoSource")}</div>`}</div><div class="small muted mt-8">${t("course.editKeepHint")}</div>${excludedRows ? `<details class="edit-excluded"><summary>${t("course.editExcludedSources", { n: selected.excluded_sources.length })}</summary><div class="small muted mt-8">${t("course.editExcludedHint")}</div><div class="edit-source-list mt-8">${excludedRows}</div></details>` : ""}</div>
            <div class="field wide"><label>${t("course.editAddSources")}</label><label class="edit-file-picker" for="editNewFiles"><span class="edit-file-button">${t("course.editChooseFiles")}</span><span class="edit-file-names" id="editFileNames">${t("course.editNoFiles")}</span></label><input id="editNewFiles" name="files" type="file" multiple accept=".pdf,.ppt,.pptx,.doc,.docx,.png,.jpg,.jpeg,.webp" hidden><div class="small muted mt-8">${t("new.fileHint")}</div></div>
          </div>
        </section>
        <section class="form-section">
          <div class="form-section-head"><h3>${t("course.editSectionInfo")}</h3><p>${t("course.editSectionInfoHint")}</p></div>
          <div class="form-grid">
            <div class="field wide"><label>${t("course.name")}</label><input id="cpName" maxlength="80" value="${esc(c.name || "")}" placeholder="${t("course.nameHint")}"></div>
            <div class="field"><label>${t("new.credits")}</label><input id="cpCredits" type="number" min="0.5" max="10" step="0.5" value="${c.credits || 3}"></div>
            <div class="field"><label>${t("new.courseType")}</label><select id="cpType"><option value="专业课" ${c.course_type === "专业课" ? "selected" : ""}>${t("new.ctMajor")}</option><option value="专业基础课" ${c.course_type === "专业基础课" ? "selected" : ""}>${t("new.ctBasic")}</option><option value="公共基础课" ${c.course_type === "公共基础课" ? "selected" : ""}>${t("new.ctPublic")}</option><option value="选修课" ${c.course_type === "选修课" ? "selected" : ""}>${t("new.ctElective")}</option></select></div>
            <input type="hidden" id="editTitle" name="title" value="${esc(title)}">
            <div class="field"><label>${t("new.target")}</label><input id="cpTarget" name="target_score" type="number" min="60" max="100" value="${Math.max(60, Math.min(100, Number(c.target_score) || 80))}"></div>
            <div class="field"><label>${t("course.examDate")}</label><input id="cpExam" type="date" value="${esc(c.exam_date || "")}"></div>
            <div class="field wide"><button type="button" class="btn btn-ghost" onclick="act.saveCoursePrefs('${esc(key)}')">保存课程信息</button></div>
            <div class="field"><label>${t("new.days")}</label><input id="editDays" name="days_left" type="number" min="1" max="30" value="${daysValue}"></div>
            <div class="field"><label>${t("new.foundation")}</label><select name="foundation"><option value="基础较弱" ${foundationValue === "基础较弱" ? "selected" : ""}>${t("new.foundationWeak")}</option><option value="一般" ${foundationValue === "一般" ? "selected" : ""}>${t("new.foundationNormal")}</option><option value="基础较好" ${foundationValue === "基础较好" ? "selected" : ""}>${t("new.foundationStrong")}</option></select></div>
            <div class="field"><label>${t("new.difficulty")}</label><select id="cpDifficulty" name="difficulty">${[1,2,3,4,5].map((n) => `<option value="${n}" ${Number(c.difficulty || 3) === n ? "selected" : ""}>${n}</option>`).join("")}</select></div>
            <textarea name="key_points" hidden>${esc(keyPointsValue)}</textarea>
            <textarea name="excluded" hidden>${esc(excludedValue)}</textarea>
            <div class="field wide"><label>AI 总偏好</label><textarea name="custom_prompt" rows="2" placeholder="这门课希望 AI 一直记住的偏好，会应用到所有模块；可留空">${esc(customValue)}</textarea></div>
          </div>
        </section>
        <input type="hidden" name="persona" value="${esc(personaValue)}">
        <input type="hidden" name="gen_lang" value="${esc(langValue)}">
        <div class="actions"><button class="btn btn-primary" id="editSubmit" type="button" onclick="act.saveCourseEdit('${esc(key)}',false)">${t("course.editSaveOnly")}</button><span class="small muted" id="editStatus"></span></div>
      </form>`;
    view.querySelectorAll(".edit-source-remove").forEach((btn) => {
      btn.onclick = () => {
        const row = btn.closest(".edit-source-row");
        const cb = row && row.querySelector(".edit-source-check");
        if (cb) { cb.checked = false; row.classList.add("removed"); }
      };
    });
    view.querySelectorAll(".edit-source-check").forEach((cb) => {
      cb.onchange = () => { const row = cb.closest(".edit-source-row"); if (row) row.classList.toggle("removed", !cb.checked); };
    });
    const editFiles = document.getElementById("editNewFiles");
    const editFileNames = document.getElementById("editFileNames");
    if (editFiles && editFileNames) editFiles.onchange = () => {
      const names = Array.from(editFiles.files || []).map((f) => f.name);
      editFileNames.textContent = names.length ? names.join("、") : t("course.editNoFiles");
    };
    // Course edit is not a lecture generator: hide lecture-only fields and the
    // regenerate action; generation belongs to the lecture module.
    const hideNames = ["title", "key_points", "excluded", "persona", "gen_lang"];
    hideNames.forEach((name) => {
      const input = view.querySelector('[name="' + name + '"]');
      const field = input && input.closest(".field");
      if (field) field.hidden = true;
    });
    view.querySelectorAll(".edit-source-weight").forEach((x) => { x.hidden = true; });
    const artifactField = document.getElementById("editArtifact");
    if (artifactField && artifactField.closest(".field")) artifactField.closest(".field").hidden = true;
    const genSubmit = document.getElementById("editSubmit");
    if (genSubmit) {
      const section = genSubmit.closest(".form-section");
      if (section) section.hidden = true;
      genSubmit.hidden = true;
    }
    const saveOnly = document.getElementById("editSaveOnly");
    if (saveOnly) saveOnly.textContent = "保存课程";

    math(view);
  }

  async function saveCourseEdit(key, regenerate = true) {
    const form = document.getElementById("courseEditForm");
    if (!form) return;
    const checks = [...form.querySelectorAll(".edit-source-check:checked")];
    const keep = checks.map((x) => x.dataset.sourceName);
    const weights = checks.map((x) => {
      const row = x.closest(".edit-source-row");
      const w = row && row.querySelector(".edit-source-weight");
      return Math.max(1, Math.min(5, Number(w && w.value) || 1));
    });
    if (!keep.length && !(document.getElementById("editNewFiles").files || []).length) { toast(t("course.editNoSource")); return; }
    const btn = document.getElementById("editSubmit");
    const saveOnlyBtn = document.getElementById("editSaveOnly");
    const status = document.getElementById("editStatus");
    if (btn) btn.disabled = true;
    if (saveOnlyBtn) saveOnlyBtn.disabled = true;
    if (status) status.textContent = t("new.uploading");
    try {
      const fd = new FormData(form);
      const pickedNew = Array.from(document.getElementById("editNewFiles").files || []).filter((f) => f && f.name);
      if (!pickedNew.length) fd.delete("files");
      fd.set("keep", JSON.stringify(keep));
      fd.set("weights", JSON.stringify(weights.concat(Array.from({ length: (document.getElementById("editNewFiles").files || []).length }, () => 1))));
      fd.set("artifact_id", document.getElementById("editArtifact").value);
      fd.set("school_level", (state.settings && state.settings.school_tier) || "");
      if (!regenerate) {
        const res = await fetch(`/api/courses/${encodeURIComponent(key)}/save-edit`, { method: "POST", body: fd });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || t("course.editSaveOnlyFailed"));
        toast(data.pending_regeneration ? t("course.editSaveOnlyDone") : t("course.editParamsDone"));
        location.hash = `#/course/${encodeURIComponent(key)}`;
        return;
      }
      const res = await fetch(`/api/courses/${encodeURIComponent(key)}/generate-edit`, { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      lockGenerationJob(data.job_id, t("course.editGenerating"));
      pollCourseEditJob(data.job_id, key);
    } catch (e) {
      if (status) status.textContent = requestErrorMessage(e, regenerate ? t("course.editFailed") : t("course.editSaveOnlyFailed"));
      if (btn) btn.disabled = false;
      if (saveOnlyBtn) saveOnlyBtn.disabled = false;
    }
  }

  async function pollCourseEditJob(jobId, key) {
    const status = document.getElementById("editStatus");
    const btn = document.getElementById("editSubmit");
    try {
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (status) {
        const elapsed = Number(job.elapsed_s) || 0;
        const pct = Number(job.progress) || 0;
        const eta = estimateJobEta(job, "course-edit");
        showGenerationRing(pct, eta, job.step || t("course.editGenerating"));
        status.textContent = `${job.step || t("course.editGenerating")} ${pct}%` + (elapsed ? ` · ${t("new.elapsedOnly", { elapsed: formatDuration(elapsed) })}` : "");
      }
      if (job.status === "done") {
        hideGenerationRing();
        unlockGenerationJob();
        toast(t("course.editDone"));
        location.hash = `#/course/${encodeURIComponent(key)}`;
        return;
      }
      if (job.status === "failed") { hideGenerationRing(); unlockGenerationJob(); throw new Error(job.error || t("course.editFailed")); }
      if (job.status === "cancelled") { hideGenerationRing(); unlockGenerationJob(); if (btn) btn.disabled = false; if (status) status.textContent = t("new.cancelled"); return; }
      setTimeout(() => pollCourseEditJob(jobId, key), 1600);
    } catch (e) {
      if (status) status.textContent = requestErrorMessage(e, t("course.editFailed"));
      if (btn) btn.disabled = false;
    }
  }

  const TIER_LABELS = {
    standard: "标准讲义 · 覆盖 100%",
    premium: "精品讲义",
    broad: "高范围讲义",
    normal: "普通讲义",
  };
  let fuseRecalcSeq = 0;
  async function fuseRecalc() {
    const root = document.getElementById("fusionPanel");
    const box = document.getElementById("fuseTiers");
    if (!root || !box) return;
    const picked = [...root.querySelectorAll(".fuse-src:checked")].map((x) => ({
      artifact_id: x.value, total_pages: Number(x.dataset.pages) || 0, pages: [],
    }));
    const modeEl = root.querySelector('input[name="fuseMode"]:checked');
    const merge = !modeEl || modeEl.value === "merge";
    if (!merge) { box.textContent = ""; return; }
    if (picked.length < 2) { box.textContent = t("fuse.tiersNeedTwo"); return; }
    const seq = ++fuseRecalcSeq;
    box.textContent = t("fuse.tiersLoading");
    try {
      const res = await fetch("/api/lecture/plan", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ merge: true, materials: picked }),
      });
      const data = await res.json().catch(() => ({}));
      if (seq !== fuseRecalcSeq) return;
      if (!res.ok) {
        box.textContent = String(data.detail || "").includes("交集")
          ? t("fuse.tiersNone") : t("fuse.tiersError", { msg: data.detail || ("HTTP " + res.status) });
        return;
      }
      const tiers = data.merge_tiers || [];
      if (!tiers.length) { box.textContent = t("fuse.tiersNone"); return; }
      const labels = tiers.map((x) => TIER_LABELS[x] || x).join(" / ");
      box.textContent = t("fuse.tiersOk", { tiers: labels });
    } catch (e) {
      if (seq !== fuseRecalcSeq) return;
      box.textContent = t("fuse.tiersError", { msg: e.message || "" });
    }
  }

  async function startUnitExam(courseKey) {
    const input = document.getElementById("unitExamPages");
    const status = document.getElementById("unitExamStatus");
    const btn = document.getElementById("unitExamStart");
    const pages = parsePageSpec((input && input.value) || "");
    if (!pages || !pages.length) { toast(t("exam.unitNeedPages")); return; }
    let artifactId = "";
    try {
      const list = await api(`/api/courses/${encodeURIComponent(courseKey)}`);
      const arts = (list.artifacts || []).filter((a) => !a.source_only);
      // 没有讲义时允许直接用资料页出卷。
      artifactId = (arts[0] || (list.artifacts || [])[0] || {}).id || "";
    } catch (e) { /* 下面统一报错 */ }
    if (!artifactId) { toast(t("course.emptyText") || "这门课还没有资料"); return; }
    if (btn) btn.disabled = true;
    if (status) status.textContent = t("exam.unitRunning");
    lockGenerationJob("unit-exam", t("exam.unitRunning"));
    showGenerationRing(40, null, t("exam.unitRunning"));
    try {
      const doc = await api("/api/exam/units", { method: "POST", body: {
        artifact_id: artifactId, pages, count: Math.min(10, Math.max(3, pages.length)), subject: "",
      }});
      hideGenerationRing();
      unlockGenerationJob();
      if (btn) btn.disabled = false;
      if ((doc.skipped_pages || []).length) toast(t("exam.unitSkipped", { pages: doc.skipped_pages.join("、") }), 6000);
      if (status) status.textContent = doc.status === "validated" ? t("status.passedShort") : t("status.notPassedShort");
      location.hash = `#/exam?artifact=${encodeURIComponent(artifactId)}&doc=${encodeURIComponent(doc.id || "")}`;
    } catch (e) {
      hideGenerationRing();
      unlockGenerationJob();
      if (btn) btn.disabled = false;
      if (status) status.textContent = requestErrorMessage(e, t("exam.unitRunning"));
    }
  }

  async function startFusion(courseKey) {
    const root = document.getElementById("fusionPanel");
    if (!root) return;
    const picked = [...root.querySelectorAll(".fuse-src:checked")].map((x) => x.value);
    const modeEl = root.querySelector('input[name="fuseMode"]:checked');
    const merge = !modeEl || modeEl.value === "merge";
    const authorEl = document.getElementById("fuseAuthor");
    const status = document.getElementById("fuseStatus");
    const btn = document.getElementById("fuseStart");
    if (merge && picked.length < 2) { toast(t("fuse.needTwo")); return; }
    if (!picked.length) { toast(t("fuse.needOne")); return; }
    if (btn) btn.disabled = true;
    if (status) status.textContent = t("fuse.running");
    lockGenerationJob("fuse", t("fuse.running"));
    showGenerationRing(2, null, t("fuse.running"));
    try {
      const body = {
        materials: picked.map((id) => ({ artifact_id: id, pages: [] })),
        merge, mode: "fuse", author: !!(authorEl && authorEl.checked),
        title: (document.getElementById("fuseTitle") || {}).value || "",
        course: "",
      };
      const res = await fetch("/api/lecture/fuse-jobs", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      pollFuseJob(data.job_id, courseKey, merge);
    } catch (e) {
      hideGenerationRing();
      unlockGenerationJob();
      if (btn) btn.disabled = false;
      if (status) status.textContent = requestErrorMessage(e, t("fuse.failed"));
    }
  }

  async function pollFuseJob(jobId, courseKey, merge) {
    const status = document.getElementById("fuseStatus");
    const btn = document.getElementById("fuseStart");
    try {
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      const step = localizeJobStep(job.step || job.status);
      if (status) status.textContent = `${step} ${Number(job.progress) || 0}%`;
      showGenerationRing(Number(job.progress) || 0, estimateJobEta(job, "fuse"), step);
      if (job.status === "done") {
        hideGenerationRing();
        unlockGenerationJob();
        if (btn) btn.disabled = false;
        const result = job.result || {};
        const ids = result.merge ? [result.id].filter(Boolean) : (result.artifacts || []);
        if (status) status.textContent = merge ? t("fuse.oneDone") : t("fuse.done", { n: ids.length });
        toast(merge ? t("fuse.oneDone") : t("fuse.done", { n: ids.length }));
        location.hash = merge && ids[0]
          ? `#/read/${encodeURIComponent(ids[0])}`
          : `#/course/${encodeURIComponent(courseKey)}/lectures`;
        return;
      }
      if (job.status === "failed") throw new Error(job.error || t("fuse.failed"));
      if (job.status === "cancelled") {
        hideGenerationRing();
        unlockGenerationJob();
        if (btn) btn.disabled = false;
        if (status) status.textContent = t("new.cancelled");
        return;
      }
      setTimeout(() => pollFuseJob(jobId, courseKey, merge), 1500);
    } catch (e) {
      hideGenerationRing();
      unlockGenerationJob();
      if (btn) btn.disabled = false;
      if (status) status.textContent = requestErrorMessage(e, t("fuse.failed"));
    }
  }

  async function renderCourse(key, tab, seq) {
    let c;
    try { c = await api(`/api/courses/${encodeURIComponent(key)}`); }
    catch (e) {
      if (seq !== state.seq) return;
      view.innerHTML = pageHead("404", t("course.notFoundTitle"), t("course.notFoundText"), `<a class="btn btn-primary" href="#/library">${t("course.notFoundCta")}</a>`);
      return;
    }
    if (seq !== state.seq) return;
    state.course = c;
    setCurrentCourseKey(key, c.name || "");
    let [docs, review, bankCounts] = await Promise.all([
      api("/api/documents").catch(() => []),
      api("/api/review").catch(() => ({ due: [], scheduled: [] })),
      api("/api/bank/counts").catch(() => ({ counts: {} })),
    ]);
    if (seq !== state.seq) return;
    const ids = new Set(c.artifact_ids || []);
    const courseDocs = (docs || []).filter((d) => ids.has(d.artifact_id) && d.kind !== "paper");
    const examDocs = courseDocs.filter((d) => d.kind === "exam");
    const courseParams = new URLSearchParams(location.hash.split("?")[1] || "");
    const paperFilter = courseParams.get("paper") || "all";
    const shownExams = paperFilter === "validated" ? examDocs.filter((d) => d.status === "validated") : paperFilter === "review" ? examDocs.filter((d) => d.status !== "validated") : examDocs;
    const toolDocs = courseDocs.filter((d) => d.kind !== "exam");
    const due = (review.due || []).filter((x) => ids.has(x.artifact_id));
    const scheduled = (review.scheduled || []).filter((x) => ids.has(x.artifact_id));
    const masteryRows = (review.mastery || []).filter((x) => ids.has(x.artifact_id) && Number(x.attempts || 0) > 0);
    const masteryAvg = masteryRows.length ? Math.round(masteryRows.reduce((sum, x) => sum + Number(x.score || 0), 0) / masteryRows.length) : null;
    const target = Number(c.target_score || 0);
    const bank = bankCounts.counts || {};
    const bankRows = (c.artifacts || []).map((a) => ({ a, n: Number(bank[a.id] || 0) })).filter((x) => x.n > 0);
    const bankTotal = bankRows.reduce((sum, x) => sum + x.n, 0);
    const icon = COURSE_ICONS[c.icon] || COURSE_ICONS.book;
    const active = ["materials", "lectures", "extract", "practice", "papers"].includes(tab) ? tab : "materials";
    const courseArtifacts = c.artifacts || [];
    const sourceOnlyCount = courseArtifacts.filter((a) => a.source_only).length;
    const lectureCount = courseArtifacts.length - sourceOnlyCount;
    state.courseTab = active;
    const tabs = `<div class="course-tabs"><a class="${active === "materials" ? "on" : ""}" href="#/course/${encodeURIComponent(c.key)}/materials">${t("course.materials")}</a><a class="${active === "lectures" ? "on" : ""}" href="#/course/${encodeURIComponent(c.key)}/lectures">${t("course.lecturesTab")} · ${lectureCount}</a><a class="${active === "extract" ? "on" : ""}" href="#/course/${encodeURIComponent(c.key)}/extract">${t("course.tools")}</a><a class="${active === "practice" ? "on" : ""}" href="#/course/${encodeURIComponent(c.key)}/practice">${t("course.training")}</a><a class="${active === "papers" ? "on" : ""}" href="#/course/${encodeURIComponent(c.key)}/papers">${t("course.papers")}</a></div>`;
    const toolbar = "";
    const cd = c.exam_date ? countdown(c.exam_date) : null;
    const overview = `<section class="course-overview"><div class="course-overview-head"><div><div class="eyebrow">COURSE OVERVIEW</div><h2>${t("course.structure")}</h2><p>${t("course.structureNote")}</p></div><div class="course-facts"><div><b>${c.artifact_ids ? c.artifact_ids.length : 0}</b><span>${t("course.lecturesCount")}</span></div><div><b>${c.pages || 0}</b><span>${t("course.pages")}</span></div><div><b>${c.figures || 0}</b><span>${t("course.figures")}</span></div></div></div>
      <div class="course-goal-summary"><div><b>${c.target_score || "—"}</b><span>${t("course.target")}</span></div><div><b>${cd ? cd.days : "—"}</b><span>${cd ? (cd.expired ? t("course.ended") : (cd.days === 0 ? t("course.today") : t("course.days"))) : t("course.noDate")}</span></div></div>
      ${toolbar}</section>`;
    const sourceArtifacts = courseArtifacts.filter((a) => a.source_only);
    const readableArtifacts = courseArtifacts.filter((a) => !a.source_only);
    const shownArtifacts = readableArtifacts.slice(0, 12);
    const practiceArtifacts = shownArtifacts.filter((a, i, arr) => arr.findIndex((x) => x.title === a.title) === i).slice(0, 6);
    const sourceFirstName = sourceArtifacts[0] && sourceArtifacts[0].sources && sourceArtifacts[0].sources[0]
      ? cleanSourceName(sourceArtifacts[0].sources[0].name) : "";
    const courseDisplayName = (c.name === "课程资料" && sourceFirstName) ? sourceFirstName : c.name;
    const savedSourceNames = sourceArtifacts.flatMap((a) => (Array.isArray(a.sources) ? a.sources : []).map((x) => cleanSourceName(x && x.name)).filter(Boolean));
    const sourceOnlyEmpty = sourceArtifacts.length ? `<div class="source-shelf"><div class="eyebrow">${t("course.materials")}</div><h3>${t("course.noLectureTitle")}</h3><p>${t("course.noLectureText", { n: sourceArtifacts.length })}</p>${savedSourceNames.length ? `<div class="source-file-list">${savedSourceNames.map((n) => `<span>${esc(n)}</span>`).join("")}</div>` : ""}<div class="actions"><button class="btn btn-primary" type="button" id="tfGenerateLecture" onclick="window.tfPickSource('${esc(c.key)}')">${t("course.new")}</button></div></div>` : "";
    const lectureBlock = readableArtifacts.length ? `<section class="section-title"><h2>${t("course.lectures")}</h2><div class="actions"><span class="small muted">${t("course.qualityHint")}</span><button class="btn btn-primary" type="button" onclick="window.tfPickSource('${esc(c.key)}')">选择资料页</button><button class="btn btn-ghost" id="tfPreviewSelected" type="button" onclick="window.tfPreviewSelected('${esc(c.key)}')">预览已选页</button><button class="btn btn-primary" id="tfGenerateSelected" type="button" onclick="window.tfGenerateSelected('${esc(c.key)}')">继续生成</button><button class="btn btn-ghost" type="button" onclick="window.tfPickSource('${esc(c.key)}')">${t("course.new")}</button></div></section><div class="grid grid-2 course-lectures">${shownArtifacts.map((a, i) => artifactCard(a, { tone: i % 6, courseKey: c.key })).join("")}</div>` : "";
    const fuseCandidates = (sourceArtifacts.length ? sourceArtifacts : courseArtifacts).filter((a) => a && a.id);
    const fuseList = fuseCandidates.map((a) => `<label class="fuse-item"><input type="checkbox" class="fuse-src" value="${esc(a.id)}" data-pages="${Number(a.page_count || a.pages || 0)}" onchange="act.fuseRecalc()"><span class="fuse-name">${esc(cleanSourceName(a.title || a.id))}</span><span class="small muted">${t("fuse.pages", { n: a.page_count || a.pages || 0 })}</span></label>`).join("");
    const fusionPanel = `<section class="card flat course-fusion" id="fusionPanel"><div class="eyebrow">多资料</div><h3>${t("fuse.title")}</h3><p class="small muted">${t("fuse.lede")}</p>${fuseList ? `<div class="fuse-list">${fuseList}</div><div class="fuse-controls"><label class="radio-line"><input type="radio" name="fuseMode" value="merge" checked onchange="act.fuseRecalc()">${t("fuse.mergeOn")}</label><label class="radio-line"><input type="radio" name="fuseMode" value="separate" onchange="act.fuseRecalc()">${t("fuse.mergeOff")}</label><label class="radio-line"><input type="checkbox" id="fuseAuthor">${t("fuse.author")}</label></div><p class="small muted">${t("fuse.digestNote")}</p><p id="fuseTiers" class="small muted"></p><div class="fuse-actions"><input id="fuseTitle" class="fuse-title" maxlength="80" placeholder="${t("fuse.titlePlaceholder")}"><button class="btn btn-primary" type="button" id="fuseStart" onclick="act.startFusion('${esc(c.key)}')">${t("fuse.start")}</button></div><p id="fuseStatus" class="small muted"></p>` : `<p class="small muted">${t("fuse.empty")}</p>`}</section>`;
    const lectures = `${toolbar}${sourceOnlyEmpty}${fusionPanel}${lectureBlock || (sourceArtifacts.length ? "" : empty(t("course.emptyTitle"), t("course.emptyText")))}`;
    const sourceArt = sourceArtifacts[0] || courseArtifacts[0];
    let sourcePages = [];
    try { sourcePages = JSON.parse(localStorage.getItem("tf-pages-" + c.key + "-" + (sourceArt ? sourceArt.id : "")) || "[]"); } catch (e) { sourcePages = []; }
    const sourcePracticeRow = sourceArt ? (sourcePages.length
      ? '<a class="btn btn-ghost" href="#/practice/' + encodeURIComponent(sourceArt.id) + '?source=1&pages=' + encodeURIComponent(sourcePages.join(",")) + '">按资料页出题</a>'
      : '<button class="btn btn-ghost" type="button" onclick="window.tfPickSource(' + "'" + esc(c.key) + "'" + ')">选资料页后出题</button>') : "";
    const training = `<section class="course-tool-page"><div class="eyebrow">练习</div><h2>${t("course.training")}</h2><p class="course-settings-note">${t("course.trainingNote")}</p>
      <div class="course-train-grid"><div class="card flat"><h3>${t("course.newPractice")}</h3><p class="small muted">${t("course.newPracticeNote")}</p>
        <div class="course-practice-list">${practiceArtifacts.map((a) => `<a href="#/practice/${encodeURIComponent(a.id)}"><span>${esc(a.title)}</span><span>${t("course.practice")} →</span></a>`).join("") || `<span class="small muted">${sourceArtifacts.length ? t("course.sourceOnlyHint") : t("course.noLectures")}</span>`}</div><div class="actions mt-8">${sourcePracticeRow}</div></div>
        <div class="card flat"><h3>${t("course.review")}</h3><p class="small muted">${t("course.reviewNote")}</p><div class="course-review-counts"><div><b>${due.length}</b><span>${t("review.tabDue")}</span></div><div><b>${scheduled.length}</b><span>${t("review.tabScheduled")}</span></div></div><p class="course-target-progress">${target ? t("course.targetProgress", { target, current: masteryAvg === null ? t("course.targetNoData") : masteryAvg }) : t("course.targetUnset")}</p><a class="btn btn-ghost" href="#/review?course=${encodeURIComponent(c.key)}">${t("course.openReview")} →</a></div></div>
      <div class="card flat course-bank"><h3>${t("course.bankPractice")}</h3><p class="small muted">${t("course.bankNote")}</p>${bankRows.length ? `<div class="course-practice-list">${bankRows.map(({a,n}) => `<a href="#/practice/${encodeURIComponent(a.id)}?bank=1"><span>${esc(a.title)} · ${t("course.bankCount", { n })}</span><span>${t("course.practice")} →</span></a><a href="#/bank/${encodeURIComponent(a.id)}"><span>${t("bank.manage")}</span><span>→</span></a>`).join("")}</div>` : `<p class="small muted">${t("course.bankEmpty")}</p>`}</div></section>`;
    const examArt = readableArtifacts[0] || sourceArtifacts[0] || courseArtifacts[0] || null;
    const unitExamCard = examArt ? `<div class="card flat"><h3>${t("exam.unitTitle")}</h3><p class="small muted">${t("exam.unitLede")}</p><div class="fuse-actions"><input id="unitExamPages" class="fuse-title" placeholder="${t("exam.unitPages")}"><button class="btn btn-primary" type="button" id="unitExamStart" onclick="act.startUnitExam('${esc(c.key)}')">${t("exam.unitStart")}</button></div><p id="unitExamStatus" class="small muted"></p></div>` : "";
    const papers = `<section class="course-tool-page"><div class="eyebrow">出卷</div><h2>${t("course.papers")}</h2><p class="course-settings-note">${t("course.papersNote")}</p>${unitExamCard}
      <div class="actions mb-16">${examArt ? `<a class="btn btn-primary" href="#/exam?artifact=${encodeURIComponent(examArt.id)}">${t("course.newPaper")}</a>` : ""}${(() => { const seen = new Set(); const dup = examDocs.filter((d) => { const k = String(d.title || "").trim(); if (seen.has(k)) return true; seen.add(k); return false; }); return dup.length ? `<button class="btn btn-ghost" onclick="act.cleanPapers('${esc(c.key)}')">${t("course.cleanPapers", { n: dup.length })}</button>` : ""; })()}</div>
      <div class="course-filter-row"><a class="${paperFilter === "all" ? "on" : ""}" href="#/course/${encodeURIComponent(c.key)}/papers">${t("course.paperAll", { n: examDocs.length })}</a><a class="${paperFilter === "validated" ? "on" : ""}" href="#/course/${encodeURIComponent(c.key)}/papers?paper=validated">${t("course.paperValidated", { n: examDocs.filter((d) => d.status === "validated").length })}</a><a class="${paperFilter === "review" ? "on" : ""}" href="#/course/${encodeURIComponent(c.key)}/papers?paper=review">${t("course.paperReview", { n: examDocs.filter((d) => d.status !== "validated").length })}</a></div>
      ${shownExams.length ? `<div class="list">${shownExams.slice(0, 8).map((d) => `<div class="row doc-row"><a class="row-main" href="#/exam?artifact=${encodeURIComponent(d.artifact_id)}&doc=${encodeURIComponent(d.id)}"><div class="row-title">${esc(d.title || t("course.paper"))}${(() => { try { const a = JSON.parse(localStorage.getItem("tf-exam-attempt-" + d.id) || "null"); return a ? ` <span class="badge badge-neutral">${t("course.selfTested", { score: a.score, total: a.total })}</span>` : ""; } catch (e) { return ""; } })()}</div><div class="row-sub">${esc(docStatusLabel(d.status))} · ${esc(d.created_at)}</div></a><div class="doc-actions"><a href="#/exam?artifact=${encodeURIComponent(d.artifact_id)}&doc=${encodeURIComponent(d.id)}">→</a><button class="btn btn-ghost" onclick="act.renameDoc('${esc(d.id)}','${esc(d.title || "")}')">${t("doc.rename")}</button><button class="btn btn-ghost" onclick="act.deleteDoc('${esc(d.id)}')">${t("doc.delete")}</button></div></div>`).join("")}</div>` : `<div class="empty"><h3>${t("course.noPapers")}</h3><p>${t("course.noPapersNote")}</p></div>`}</section>`;

    const toolArt = (readableArtifacts[0] || (c.artifacts || [])[0]) || null;
    const toolCards = toolArt ? [
      ["extract_points", t("task.extractPoints")],
      ["extract_nouns", t("task.extractNouns")],
      ["extract_questions", t("task.extractQuestions")],
      ["analysis", t("task.analysis")],
    ].map((pair) => '<a class="btn btn-ghost" href="#/workbench?artifact=' + encodeURIComponent(toolArt.id) + '&kind=' + pair[0] + '">' + pair[1] + '</a>').join("") : "";

    const tools = `<section class="course-tool-page"><div class="eyebrow">提取</div><h2>${t("course.tools")}</h2><p class="course-settings-note">${t("course.toolsNote")}</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap">${toolCards}</div>
      ${toolDocs.length ? `<div class="list">${toolDocs.slice(0, 12).map((d) => {
        const src = (c.artifacts || []).find((a) => a.id === d.artifact_id) || {};
        const sourceTitle = src.title || t("doc.unknownSource");
        return `<div class="row doc-row"><a class="row-main" href="#/workbench?artifact=${encodeURIComponent(d.artifact_id)}&doc=${encodeURIComponent(d.id)}"><div class="row-title">${esc(sourceTitle)} · ${esc(taskLabel(d.kind))}</div><div class="row-sub">${esc(docSectionLabel(d))} · ${esc(docStatusLabel(d.status))} · ${esc(d.created_at)}</div></a><div class="doc-actions"><a href="#/workbench?artifact=${encodeURIComponent(d.artifact_id)}&doc=${encodeURIComponent(d.id)}">→</a><button class="btn btn-ghost" onclick="act.deleteDoc('${esc(d.id)}')">${t("doc.delete")}</button></div></div>`;
      }).join("")}</div>` : `<div class="empty"><h3>${t("course.noTools")}</h3><p>${t("course.noToolsNote")}</p></div>`}</section>`;
    const settings = `<section class="course-settings"><div class="eyebrow">COURSE SETTINGS</div><h2>${t("course.settings")}</h2><p class="course-settings-note">${t("course.structureNote")}</p><div class="course-goal-editor"><div class="field course-name-field"><label>${t("course.name")}</label><input id="cpName" maxlength="80" value="${esc(c.name || "")}" placeholder="${t("course.nameHint")}"></div><div class="field"><label>${t("new.credits")}</label><input id="cpCredits" type="number" min="0.5" max="10" step="0.5" value="${c.credits || 0.5}"></div><div class="field"><label>${t("new.courseType")}</label><select id="cpType"><option value="专业课" ${c.course_type === "专业课" ? "selected" : ""}>${t("new.ctMajor")}</option><option value="专业基础课" ${c.course_type === "专业基础课" ? "selected" : ""}>${t("new.ctBasic")}</option><option value="公共基础课" ${c.course_type === "公共基础课" ? "selected" : ""}>${t("new.ctPublic")}</option><option value="选修课" ${c.course_type === "选修课" ? "selected" : ""}>${t("new.ctElective")}</option></select></div><div class="field"><label>${t("new.difficulty")}</label><select id="cpDifficulty">${[1,2,3,4,5].map(n => `<option value="${n}" ${Number(c.difficulty || 3) === n ? "selected" : ""}>${n}</option>`).join("")}</select></div><div class="field"><label>${t("course.targetScore")}</label><input id="cpTarget" type="number" min="60" max="100" value="${c.target_score || 80}" placeholder="80"></div><div class="field"><label>${t("course.examDate")}</label><input id="cpExam" type="date" value="${esc(c.exam_date || "")}"></div><button class="btn btn-primary" onclick="act.saveCoursePrefs('${esc(c.key)}')">${t("course.saveSettings")}</button></div><p class="small muted mt-8">${t("course.settingsHint")}</p><div class="course-danger"><div><b>${t("course.archive")}</b><p>${t("course.archiveNote")}</p></div><button class="btn btn-danger" onclick="act.archiveCourse('${esc(c.key)}')">${t("course.archive")}</button></div></section>`;
    const materials = `<section class="course-tool-page"><div class="eyebrow">资料</div><h2>${t("course.materials")}</h2><p class="course-settings-note">只显示生成成果，原始资料在编辑课程。</p>${readableArtifacts.length ? `<div class="grid grid-2 course-lectures">${shownArtifacts.map((a, i) => artifactCard(a, { tone: i % 6, courseKey: c.key })).join("")}</div>` : empty(t("course.materialsEmpty"), t("course.materialsEmptyText"), `<button class="btn btn-primary" type="button" onclick="window.tfPickSource('${esc(c.key)}')">${t("course.new")}</button>`)}<p class="small muted mt-8">显示最近 12 份，共 ${readableArtifacts.length} 份。</p></section>`;
    view.innerHTML = `<div class="course-topbar"><a class="course-back" href="#" onclick="act.back('#/library', event)">${t("course.backAll")}</a><a class="btn btn-ghost" href="#/course/${encodeURIComponent(c.key)}/edit">编辑课程</a></div>
      <section class="course-hero course-${esc(c.color || "slate")}">
      <div class="course-hero-main">
        <div class="course-icon big"><svg viewBox="0 0 24 24">${icon}</svg></div>
        <h1>${esc(courseDisplayName)}</h1>
        <div class="course-meta">${t("course.metaDetail", { n: lectureCount, pages: c.pages || 0, sections: c.sections || 0, figures: c.figures || 0 })}${sourceOnlyCount ? ` · ${t("course.sourceCount", { n: sourceOnlyCount })}` : ""}</div>
        ${(c.credits || c.course_type) ? `<div class="course-meta academic-meta">${t("course.academicMeta", { credits: c.credits || "—", type: c.course_type || "未填", difficulty: c.difficulty || 3 })}</div>` : ""}
      </div>
      <div class="course-hero-side">${lectureCount ? `<div class="hero-stat"><strong>${c.delivered || 0}</strong><span>${t("course.readableStat")}</span></div>
        <div class="hero-stat"><strong>${c.review || 0}</strong><span>${t("course.reviewStat")}</span></div>` : `<div class="hero-stat"><strong>${sourceOnlyCount}</strong><span>${t("course.sourceSaved")}</span></div>`}
        </div>
    </section>` + tabs + (active === "practice" ? training : active === "papers" ? papers : active === "extract" ? tools : active === "lectures" ? lectures : materials);
    math(view);
  }

  async function courseEditToggle(key) {
    if (state.courseEditing && state.courseEditingKey === key) {
      state.courseEditing = false;
      state.courseEditingKey = "";
    } else {
      state.courseEditing = true;
      state.courseEditingKey = key;
    }
    await renderCourse(key, state.courseTab || "lectures", ++state.seq);
  }

  async function deleteLecture(key, artifactId) {
    if (!window.confirm(t("course.deleteLectureConfirm"))) return;
    try {
      await api(`/api/courses/${encodeURIComponent(key)}/artifacts/${encodeURIComponent(artifactId)}`, { method: "DELETE" });
      toast(t("course.deleteLectureDone"));
      const c = await api(`/api/courses/${encodeURIComponent(key)}`).catch(() => null);
      if (!c || !(c.artifact_ids || []).length) { location.hash = "#/library"; return; }
      state.courseEditing = true; state.courseEditingKey = key;
      await renderCourse(key, state.courseTab || "lectures", ++state.seq);
    } catch (e) { toast(e.message || t("course.deleteLectureFailed")); }
  }

  async function saveCoursePrefs(key) {
    const target = document.getElementById("cpTarget");
    const exam = document.getElementById("cpExam");
    const name = document.getElementById("cpName");
    const credits = document.getElementById("cpCredits");
    const courseType = document.getElementById("cpType");
    const difficulty = document.getElementById("cpDifficulty");
    try {
      await api(`/api/course-prefs/${encodeURIComponent(key)}`, {
        method: "PUT", body: { target_score: Number(target ? target.value : 0), exam_date: exam ? exam.value : "",
          display_name: name ? name.value : "", credits: Number(credits ? credits.value : 0),
          course_type: courseType ? courseType.value : "",
          school_level: (state.settings && state.settings.school_tier) || "",
          difficulty: Number(difficulty ? difficulty.value : 3) },
      });
      toast(t("settings.profileSaved"));
      await route();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }

  async function archiveCourse(key) {
    if (!confirm(t("course.archiveConfirm"))) return;
    try {
      const r = await api(`/api/courses/${encodeURIComponent(key)}`, { method: "DELETE" });
      toast(t("course.deleted", { n: r.archived }));
      location.hash = "#/library";
    } catch (e) { toast(e.message || t("course.deleteFailed")); }
  }

  async function acceptDraft(draftId, originalId) {
    if (!confirm(t("artifact.acceptConfirm"))) return;
    try {
      await api(`/api/artifacts/${encodeURIComponent(draftId)}/accept`, { method: "POST", body: {} });
      toast(t("artifact.acceptDraft"));
      location.hash = `#/artifact/${encodeURIComponent(originalId)}`;
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }

  async function restoreBackup(aid, name) {
    if (!confirm(t("artifact.restoreConfirm"))) return;
    try {
      await api(`/api/artifacts/${encodeURIComponent(aid)}/restore`, { method: "POST", body: { backup: name } });
      toast(t("artifact.restore"));
      await route();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }

  async function rewriteArtifact(aid) {
    const box = document.getElementById("rewriteResult");
    const btn = document.getElementById("rewriteBtn");
    const instruction = (document.getElementById("rewriteInstruction").value || "").trim();
    const genLang = document.getElementById("rewriteLang").value || "zh";
    if (!instruction) { toast(t("artifact.rewriteInstruction")); return; }
    if (btn) btn.disabled = true;
    if (box) box.innerHTML = `<div class="banner warn mt-16"><div>${t("artifact.rewriteRunning")}</div></div>`;
    try {
      const r = await api(`/api/artifacts/${encodeURIComponent(aid)}/rewrite`, { method: "POST", body: { instruction, gen_lang: genLang } });
      const diffs = (r.diffs || []).map((d) => `<div class="card flat mt-8"><h3 class="card-title">${esc(d.title || "")}</h3>
        <div class="grid grid-2 mt-8"><div><div class="small muted">${t("artifact.rewriteDiff")} A</div>${(d.before || []).map((x) => `<p class="small">${esc(x)}</p>`).join("")}</div>
        <div><div class="small muted">${t("artifact.rewriteDiff")} B</div>${(d.after || []).map((x) => `<p class="small">${esc(x)}</p>`).join("")}</div></div></div>`).join("");
      if (box) box.innerHTML = `<div class="banner good mt-16"><div><strong>${t("artifact.rewriteDraft")}</strong> · ${esc(r.draft_id)}</div></div>
        <div class="actions"><a class="btn btn-primary" href="#/artifact/${encodeURIComponent(r.draft_id)}">${t("artifact.rewriteKeep")}</a>
          <button class="btn btn-ghost" onclick="act.discardDraft('${esc(r.draft_id)}')">${t("artifact.rewriteDiscard")}</button></div>${diffs}`;
    } catch (e) {
      if (box) box.innerHTML = `<div class="banner bad mt-16"><div>${esc(e.message || t("error.actionFailed"))}</div></div>`;
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function discardDraft(id) {
    if (!confirm("丢弃这份 AI 改写草稿？原稿不受影响。")) return;
    try { await api(`/api/artifacts/${encodeURIComponent(id)}`, { method: "DELETE" }); toast(t("artifact.rewriteDiscard")); }
    catch (e) { toast(e.message || t("error.actionFailed")); }
  }

  async function saveReview(aid) {
    const reviewer = (document.getElementById("reviewerName").value || "").trim();
    const notes = (document.getElementById("reviewNotes").value || "").trim();
    if (!reviewer) { toast(t("artifact.reviewer")); return; }
    try {
      await api(`/api/artifacts/${encodeURIComponent(aid)}/review`, { method: "POST", body: { reviewer, notes } });
      toast(t("artifact.saveReview"));
      await route();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }

  async function renderArtifact(id, seq) {
    let a;
    try { a = await api(`/api/artifacts/${encodeURIComponent(id)}`); }
    catch (e) {
      if (seq !== state.seq) return;
      view.innerHTML = pageHead("404", t("artifact.notFoundTitle"), t("artifact.notFoundText"), `<a class="btn btn-primary" href="#/library">${t("artifact.backLibrary")}</a>`);
      return;
    }
    if (seq !== state.seq) return;
    state.artifact = a;
    let backups = [];
    if (!(a.constraints || {}).draft_of) {
      try { backups = await api(`/api/artifacts/${encodeURIComponent(a.id)}/backups`); } catch (e) { backups = []; }
    }
    let metrics = null;
    try { metrics = await api(`/api/artifacts/${encodeURIComponent(a.id)}/metrics`); } catch (e) { metrics = null; }
    const q = a.quality;
    const banner = q.status === "rejected"
      ? `<div class="banner bad"><div>这份讲义生成不完整，建议重新生成。</div></div>`
      : "";

    const baseOk = q.gate_passed && q.content_passed && q.pdf_passed && q.language_passed;
    const auditDetail = !q.audit_present ? t("artifact.detailUnchecked") : (q.audit_ok ? t("artifact.detailPass") : t("artifact.detailGap"));
    const quality = `<div class="quality quality-3">
      ${qualityItem(baseOk, t("artifact.chipBase"), baseOk ? t("artifact.detailPass") : t("artifact.detailRedo"))}
      ${qualityItem(q.audit_present ? q.audit_ok : null, t("artifact.chipContent"), auditDetail)}
      ${qualityItem(q.figures_bad === 0, t("artifact.chipFigures"), q.figures_ok ? `${q.figures_ok} 张` : "—")}
    </div>`;

    const auditButton = (!q.audit_present && q.gate_passed)
      ? `<div class="actions mt-16"><button class="btn btn-primary" id="runAuditBtn"
           onclick="act.runArtifactAudit('${esc(a.id)}')">${t("artifact.runAudit")}</button>
           <span class="small muted" id="auditStatus"></span></div>`
      : "";
    const metricsRow = (() => {
      if (!metrics) return "";
      if (metrics.image_mode) {
        return `<div class="quality mt-16">${qualityItem(true, t("quality.imageMode"),
          t("quality.imageModeDetail", { images: metrics.images || 0, pages: metrics.page_count || 0 }))}</div>`;
      }
      const support = metrics.citation_support;
      const recall = metrics.term_recall;
      const dup = metrics.dup_sentence;
      const boiler = metrics.boilerplate_per_1k;
      const supportOk = support === null || support === undefined ? null : support >= 0.5;
      const recallOk = recall === null || recall === undefined ? null : recall >= 0.5;
      const dupOk = dup === null || dup === undefined ? null : dup <= 0.1;
      const boilerOk = boiler === null || boiler === undefined ? null : boiler <= 300;
      const cov = metrics.coverage_percent;
      const covTarget = metrics.coverage_target;
      const covMet = metrics.coverage_met;
      const covDetail = covTarget === null || covTarget === undefined
        ? t("quality.coverageNoTier", { actual: cov })
        : t("quality.coverageMet", { actual: cov, target: covTarget });
      const contentOk = supportOk === false || recallOk === false || dupOk === false || boilerOk === false
        ? false : (supportOk === null || recallOk === null ? null : true);
      const contentDetail = [
        support === null || support === undefined ? null : `有依据 ${Math.round(support * 100)}%`,
        recall === null || recall === undefined ? null : `重点词 ${Math.round(recall * 100)}%`,
      ].filter(Boolean).join(" · ") || "—";
      return `<div class="quality quality-3 mt-16" id="artifactMetrics">
        ${qualityItem(covMet, t("artifact.chipCoverage"), covDetail)}
        ${qualityItem(contentOk, t("artifact.chipQuality"), contentDetail)}
      </div>`;
    })();

    const cons = a.constraints || {};
    const consRows = [
      cons.key_points ? `<div><strong>${t("artifact.keyPoints")}：</strong>${esc(cons.key_points)}</div>` : "",
      cons.excluded ? `<div><strong>${t("artifact.excluded")}：</strong>${esc(cons.excluded)}</div>` : "",
      cons.custom_prompt ? `<div><strong>${t("artifact.customPrompt")}：</strong>${esc(cons.custom_prompt)}</div>` : "",
    ].filter(Boolean).join("");
    const constraints = consRows ? `<div class="card mt-16"><h3 class="card-title">${t("artifact.constraints")}</h3><div class="card-body small">${consRows}</div></div>` : "";


    const sections = (a.section_list || []).map((s) => `<tr>
      <td><strong>${esc(s.title)}</strong><div class="small muted">${t("unit.blocks", { n: s.blocks })} · ${t("unit.paragraphs", { n: s.paragraphs })} · ${t("unit.figures", { n: s.figures })}</div></td>
      <td class="num">${pageRange(s.pages)}</td>
      <td class="right"><a class="btn btn-ghost" href="#/practice/${encodeURIComponent(a.id)}?section=${encodeURIComponent(s.id)}">${t("artifact.practiceSection")}</a></td>
    </tr>`).join("");

    const figures = (a.figure_list || []).map((f) => `<div class="row"><div class="row-main">
      <div class="row-title">${esc(f.caption || f.image_id || t("quality.figureFallback"))}</div>
      <div class="row-sub">${t("artifact.figureSource", { pages: (f.source_pages || []).join(t("sep.list")), origin: esc(f.origin || ""), status: esc(f.status || "") })}</div>
    </div>${f.status === "ok" ? `<span class="badge badge-good">${t("quality.ok")}</span>` : `<span class="badge badge-bad">${esc(f.issue || t("quality.issue"))}</span>`}</div>`).join("");

    view.innerHTML = pageHead(t("artifact.eyebrow"), a.title, t("artifact.meta", { pages: a.page_count || "—", pdf: a.pdf_pages || "—", sections: a.sections || 0, figures: a.figures || 0 }),
      `<a class="btn btn-primary" href="#/read/${encodeURIComponent(a.id)}">${t("artifact.read")}</a>
       <a class="btn btn-ghost" href="#/pdf/${encodeURIComponent(a.id)}">PDF</a>
       ${a.word_available ? `<button class="btn btn-ghost" type="button" onclick="act.saveReaderFile('${esc(a.id)}','docx')">Word</button>` : ""}
       <a class="btn btn-ghost" href="#/practice/${encodeURIComponent(a.id)}">${t("artifact.practice")}</a>`) +
      banner + auditButton + `<div class="mt-16">${quality}</div>${metricsRow}${constraints}` +
      `<section class="section-title"><h2>${t("artifact.sections")}</h2><span class="small muted">${t("artifact.sectionsHint")}</span></section>
       <div class="table-wrap"><table class="table"><thead><tr><th>${t("artifact.sections")}</th><th>${t("artifact.pageCol")}</th><th></th></tr></thead><tbody>${sections || `<tr><td colspan="3" class="muted">${t("artifact.noSections")}</td></tr>`}</tbody></table></div>` +
      ((a.figure_list || []).length
        ? `<section class="section-title"><h2>${t("artifact.figures")}</h2><span class="small muted">${t("artifact.figuresCount", { n: a.figure_list.length })}</span></section><div class="list">${figures}</div>`
        : "") +
      `<div class="card mt-16"><h3 class="card-title">${t("artifact.rewrite")}</h3>
        <div class="card-body small muted mb-8">${t("artifact.rewriteHint")}</div>
        <div class="form-grid"><div class="field wide"><label>${t("artifact.rewriteInstruction")}</label>
          <textarea id="rewriteInstruction" rows="2" placeholder="${esc(t("artifact.rewritePlaceholder"))}"></textarea></div>
          <div class="field"><label>${t("gen.lang")}</label><select id="rewriteLang"><option value="zh">${t("gen.zh")}</option><option value="hant">${t("gen.hant")}</option><option value="en">${t("gen.en")}</option></select></div></div>
        <div class="actions"><button class="btn btn-primary" id="rewriteBtn" onclick="act.rewriteArtifact('${esc(a.id)}')">${t("artifact.rewriteStart")}</button></div>
        <div id="rewriteResult"></div></div>` +
      `${(a.constraints || {}).draft_of ? `<div class="banner warn mt-16"><div><strong>${t("artifact.acceptDraft")}</strong><div class="small">${t("artifact.acceptHint")}</div>
        <div class="actions"><button class="btn btn-primary" onclick="act.acceptDraft('${esc(a.id)}','${esc(a.constraints.draft_of)}')">${t("artifact.acceptDraft")}</button></div></div>` : ""}
       ${backups && backups.length ? `<div class="card mt-16"><h3 class="card-title">${t("artifact.restore")}</h3>
         <div class="actions">${backups.slice(0, 3).map((b) => `<button class="btn btn-ghost" onclick="act.restoreBackup('${esc(a.id)}','${esc(b.name)}')">${esc(b.created_at)}</button>`).join("")}</div></div>` : ""}
       <div class="actions"><a class="btn btn-ghost" href="#" onclick="act.back('#/course/${encodeURIComponent(a.course_key || "")}', event)">${t("artifact.backCourse")}</a></div>`;
    math(view);
  }

  function practiceSetup(a) {
    const p = state.practice;
    const options = (a.section_list || []).map((s) => `<option value="${esc(s.id)}" ${p.section === s.id ? "selected" : ""}>${esc(s.title)}${s.pages.length ? t("practice.sectionPages", { range: pageRange(s.pages) }) : ""}</option>`).join("");
    const bank = p.mode === "bank";
    const source = p.mode === "source";
    return pageHead(t("practice.eyebrow"), source ? "按资料页练习" : (bank ? t("practice.bankTitle") : t("practice.title")), source ? "从原始资料页出题，错题仍进本课错题本。" : (bank ? t("practice.bankLede") : t("practice.lede")),
      `<a class="btn btn-ghost" href="#/artifact/${encodeURIComponent(a.id)}">${t("practice.viewQuality")}</a>`) +
      `<div class="card"><div class="form-grid">
        ${(bank || source) ? "" : `<div class="field"><label>${t("practice.section")}</label><select id="pSection">${options}</select></div>`}
        <div class="field"><label>${t("practice.count")}</label><select id="pCount"><option value="3">${t("practice.count3")}</option><option value="5">${t("practice.count5")}</option></select></div>
        <div class="field"><label>${t("practice.source")}</label><input value="${esc(source ? ("资料页 " + (p.sourcePages || []).join(",")) : (bank ? t("practice.bankSource") : t("practice.sourceValue")))}" disabled></div>
      </div><div class="actions"><button class="btn btn-primary" id="pStart">${source ? "开始出题" : (bank ? t("practice.bankStart") : t("practice.start"))}</button><span class="small muted">${source ? "只依据这几页，不扩到全书。" : (bank ? t("practice.bankHint") : t("practice.startHint"))}</span></div></div>
      <div id="pBody"></div>`;
  }


  function examAttemptKey(id) { return `tf-exam-attempt-${id}`; }

  function examFigureMarkup(q, doc, seen) {
    const key = q.figure_asset || q.figure_data || "";
    if (!key || seen.has(key)) return "";
    const wants = /如图|图中|图示|下图|上图|示意图|figure|diagram/i.test(String(q.stem || ""));
    if (!q.figure_data && !wants) return "";
    seen.add(key);
    if (q.figure_data) {
      return `<figure class="exam-source-figure ai-schematic"><img src="${q.figure_data}" alt="${esc(q.figure_caption || "AI 结构示意图")}" loading="lazy"><figcaption>${esc(q.figure_caption || "AI 结构示意图")}</figcaption></figure>`;
    }
    return `<figure class="exam-source-figure"><img src="/artifact/${encodeURIComponent(doc.artifact_id || "")}/${q.figure_asset}" alt="${esc(q.figure_caption || "资料原图")}" loading="lazy"><figcaption>${esc(q.figure_caption || "资料原图")}</figcaption></figure>`;
  }

  function examPaper(doc) {
    const c = doc.content || {};
    const sections = c.sections || [];
    const typeName = (v) => t(`exam.type.${v || "choice"}`);
    let n = 0;
    const seenFigures = new Set();
    const body = sections.map((sec, si) => `<section class="exam-section">
      <h3>${esc(sec.name || `${typeName(sec.type)}`)} <span class="small muted">（${(sec.questions || []).length}${(sec.questions || []).length !== sec.count ? ` / ${sec.count}` : ""} 题 · ${sec.score} 分）</span></h3>
      ${(sec.questions || []).map((q) => {
        n++;
        const isChoice = q.qtype === "choice";
        const showFigure = examFigureMarkup(q, doc, seenFigures);
        return `<div class="exam-q">
          <div class="exam-stem"><strong>${n}.</strong> ${esc(q.stem)} <span class="score-tag">${q.score} ${t("exam.points")}</span></div>
          ${showFigure}
          ${q.figure_description && !/^无图\s*$/i.test(String(q.figure_description).trim()) && !/无需配图/.test(String(q.figure_description)) ? `<div class="exam-figure"><strong>${t("exam.figure")}：</strong>${esc(q.figure_description)}</div>` : ""}
          ${isChoice ? `<div class="exam-options">${(q.options || []).map((o, j) => `<div><span class="letter">${String.fromCharCode(65 + j)}</span>${esc(o)}</div>`).join("")}</div>` : ""}
          <div class="exam-answer" hidden><strong>${t("exam.answer")}：</strong>${esc(isChoice ? (String.fromCharCode(65 + q.answer)) : (q.answer_text || "需人工核对"))}
            <div class="mt-8"><strong>${t("exam.analysis")}：</strong>${esc(q.analysis || "")}</div>
            ${q.source_page ? `<div class="small muted mt-8">${t("exam.source")}：第 ${q.source_page} 页${q.provenance ? ` · ${esc(q.provenance)}` : ""}</div>` : ""}
          </div>
        </div>`;
      }).join("")}
    </section>`).join("");
    const issues = [...new Set((doc.issues || []).map((x) => String(x)))].filter(Boolean);
    return `<div class="paper-back"><button class="btn btn-ghost" type="button" onclick="act.back('#/exam', event)">← ${t("reader.back").replace("← ", "")}</button></div>${issues.length ? `<div class="exam-issues"><strong>${t("exam.issueTitle", { n: issues.length })}</strong><span>${issues.slice(0, 3).map((x) => esc(x)).join(" · ")}${issues.length > 3 ? " · …" : ""}</span></div>` : ""}
    <div class="paper-toolbar">
      <span class="badge ${doc.status === "validated" ? "badge-good" : "badge-bad"}">${doc.status === "validated" ? "机器检查通过" : "需重做"}</span>
      <strong>${t("exam.total")}：${c.total_score || 0} 分</strong>
      <button class="btn btn-primary" onclick="act.examStart()">${t("exam.selfTest")}</button>
      <button class="btn btn-ghost" onclick="act.examAnswers()">${t("exam.showAnswers")}</button>
      <button class="btn btn-ghost" onclick="act.examEdit()">${t("exam.edit")}</button>
      <button class="btn btn-ghost" onclick="window.print()">${t("exam.print")}</button>
      <button class="btn btn-ghost" onclick="act.examExport()">${t("exam.export")}</button>
      <button class="btn btn-ghost" onclick="act.examWord()">${t("exam.word")}</button>
      <button class="btn btn-ghost" onclick="act.saveDocumentFile('${esc(state.exam && state.exam.doc && state.exam.doc.id || "")}','docx')">${t("exam.saveWord")}</button>
      <button class="btn btn-ghost" onclick="act.saveDocumentFile('${esc(state.exam && state.exam.doc && state.exam.doc.id || "")}','pdf')">${t("exam.savePdf")}</button>
    </div>
    <article class="exam-paper" id="examPaper">
      <header class="exam-head"><div class="small muted">${esc(c.subject || "")} · ${esc(c.mode || "")} · 难度 ${c.difficulty || "—"}/5</div>
        <h2>${esc(doc.title || "训练试卷")}</h2>
        <div class="small">${t("exam.paperMeta")}</div></header>
      ${body}
      <div class="exam-footnote">${t("exam.footnote")}</div>
    </article>`;
  }

  function examChoiceQuestions(doc) {
    const out = [];
    for (const sec of (doc.content || {}).sections || []) {
      for (const q of sec.questions || []) {
        if (q.qtype && q.qtype !== "choice") continue;
        if (!Array.isArray(q.options) || q.options.length < 2) continue;
        if (!Number.isInteger(Number(q.answer))) continue;
        out.push({ ...q, section: sec.name || "" });
      }
    }
    return out;
  }

  function examAnswerView(doc) {
    const qs = examChoiceQuestions(doc);
    const answers = state.exam.answers || {};
    const seenFigures = new Set();
    let n = 0;
    const body = qs.map((q, i) => {
      n++;
      const selected = answers[String(i)];
      return `<div class="exam-q exam-answerable"><div class="exam-stem"><strong>${n}.</strong> ${esc(q.stem)} <span class="score-tag">${q.score || 0} ${t("exam.points")}</span></div>
        ${examFigureMarkup(q, doc, seenFigures)}
        <div class="exam-options">${(q.options || []).map((o, j) => `<button type="button" class="option ${selected === j ? "selected" : ""}" onclick="act.examSelect(${i},${j})"><span class="letter">${String.fromCharCode(65 + j)}</span><span>${esc(o)}</span></button>`).join("")}</div></div>`;
    }).join("");
    return `<div class="paper-toolbar"><strong>${t("exam.selfTest")}</strong><span class="small muted">${t("exam.selfTestHint")}</span><button class="btn btn-ghost" onclick="act.examBack()">${t("exam.backPreview")}</button></div>
      <article class="exam-paper" id="examPaper"><header class="exam-head"><h2>${esc(doc.title || "")}</h2><div class="small">${t("exam.autoOnly", { n: qs.length })}</div></header>${body || `<div class="empty"><h3>${t("exam.noChoice")}</h3></div>`}
      <div class="actions"><button class="btn btn-primary" onclick="act.examSubmit()" ${qs.length ? "" : "disabled"}>${t("exam.submit")}</button></div></article>`;
  }

  function examAttemptView(doc, result) {
    return `<div class="card exam-result"><div class="eyebrow">${t("exam.submitted")}</div><h2>${t("exam.score")}：${result.score} / ${result.total} <span class="small muted">${t("exam.autoScore")}</span></h2>
      <p>${t("exam.autoResult", { correct: result.correct, auto: result.auto_total, answered: result.answered })}</p>
      <p class="small muted">${t("exam.manualNote")}</p>
      <div class="actions"><a class="btn btn-primary" href="#/review?tab=scheduled">${t("exam.goScheduled")}</a>
        <button class="btn btn-ghost" onclick="act.examStart()">${t("exam.retry")}</button>
        <button class="btn btn-ghost" onclick="act.examBack()">${t("exam.viewPaper")}</button></div></div>`;
  }

  function paintExamResult() {
    const doc = state.exam && state.exam.doc;
    const box = document.getElementById("examResult");
    if (!doc || !box) return;
    box.innerHTML = state.exam.answering ? examAnswerView(doc) : state.exam.attempt ? examAttemptView(doc, state.exam.attempt) : examPaper(doc);
    math(box);
  }

  function examStart() {
    if (!state.exam || !state.exam.doc) return;
    try { localStorage.removeItem(examAttemptKey(state.exam.doc.id)); } catch (e) {}
    state.exam.answers = {};
    state.exam.answering = true;
    state.exam.attempt = null;
    paintExamResult();
  }

  function examSelect(i, j) {
    if (!state.exam.answering) return;
    state.exam.answers = state.exam.answers || {};
    state.exam.answers[String(i)] = j;
    paintExamResult();
  }

  function examBack() {
    if (!state.exam) return;
    state.exam.answering = false;
    state.exam.attempt = null;
    paintExamResult();
  }

  async function examSubmit() {
    if (!state.exam || !state.exam.doc) return;
    const btn = document.querySelector("#examResult .btn-primary");
    if (btn) btn.disabled = true;
    try {
      const r = await api("/api/exam/attempts", { method: "POST", body: { doc_id: state.exam.doc.id, answers: state.exam.answers || {} } });
      state.exam.answering = false;
      state.exam.attempt = r;
      try { localStorage.setItem(examAttemptKey(state.exam.doc.id), JSON.stringify(r)); } catch (e) {}
      paintExamResult();
    } catch (e) {
      toast(e.message || t("exam.failed"));
      if (btn) btn.disabled = false;
    }
  }

  function inferExamSubject(a) {
    const text = `${a && a.course || ""} ${a && a.title || ""}`;
    if (/电路|电工|电学/.test(text)) return "电路";
    if (/高数|数学|微积分|线性代数|概率/.test(text)) return "高等数学";
    if (/物理/.test(text)) return "物理";
    if (/化学/.test(text)) return "化学";
    if (/计算机|算法|编程|数据结构|操作系统/.test(text)) return "计算机";
    if (/生物|细胞|遗传|生态/.test(text)) return "生物";
    if (/医学|解剖|病理|生理|护理|药理|临床|中医/.test(text)) return "医学";
    if (/历史|政治|文学|经济|金融|法律|法学|哲学|社会/.test(text)) return "文科";
    return "其他";
  }

  async function renderExam(seq) {
    const [items, docs, courses] = await Promise.all([
      api("/api/artifacts"), api("/api/documents").catch(() => []), api("/api/courses").catch(() => []),
    ]);
    if (seq !== state.seq) return;
    const prev = state.exam || {};
    const exams = (docs || []).filter((d) => d.kind === "exam");
    const examParams = new URLSearchParams(location.hash.split("?")[1] || "");
    const wanted = examParams.get("artifact") || "";
    const wantedDoc = examParams.get("doc") || "";
    const wantedArt = items.find((a) => a.id === wanted);
    let courseKey = examParams.get("course") || currentCourseKey() || (wantedArt && wantedArt.course_key) || (items[0] && items[0].course_key) || (courses[0] && courses[0].key) || "";
    const courseArtifacts = items.filter((a) => a.course_key === courseKey);
    const selectedArtifact = wantedArt && wantedArt.course_key === courseKey
      ? wanted : (courseArtifacts[0] ? courseArtifacts[0].id : "");
    const selectedDoc = wantedDoc ? (exams.find((d) => d.id === wantedDoc) || null) : null;
    let savedAttempt = null;
    if (selectedDoc) {
      try { savedAttempt = JSON.parse(localStorage.getItem(examAttemptKey(selectedDoc.id)) || "null"); } catch (e) {}
    }
    state.exam = { artifacts: items, courses, courseKey, doc: selectedDoc, exams, pickArtifact: selectedArtifact, attempt: savedAttempt, answering: false };
    if (!items.length) {
      view.innerHTML = pageHead(t("exam.eyebrow"), t("exam.title"), t("exam.lede"), "") +
        empty(t("exam.noArtifactTitle"), t("exam.noArtifactText"), `<a class="btn btn-primary" href="#/new">${t("library.cta")}</a>`);
      return;
    }
    const courseOpts = (courses || []).map((c) => `<option value="${esc(c.key)}" ${c.key === courseKey ? "selected" : ""}>${esc(c.name)}</option>`).join("");
    const opts = courseArtifacts.map((a) => `<option value="${esc(a.id)}" ${a.id === selectedArtifact ? "selected" : ""}>${esc(a.title)}</option>`).join("");
    if (wantedDoc && selectedDoc) {
      document.body.classList.add("reading");
      view.innerHTML = `<div class="reader-shell exam-reader-shell">
        <div class="reader-bar">
          <img class="reader-logo" src="/static/logo-mark.svg" alt="TermFinale">
          <a class="btn btn-ghost" href="#" onclick="act.back('#/exam', event)">${t("reader.back")}</a>
          <div class="reader-title">${esc(selectedDoc.title || t("exam.paper"))} · ${selectedDoc.status === "validated" ? t("quality.ok") : t("status.review")}</div>
        </div>
        <div class="exam-reader-body" id="examResult">${savedAttempt ? examAttemptView(selectedDoc, savedAttempt) : examPaper(selectedDoc)}</div>
      </div>`;
      math(view);
      return;
    }
    view.innerHTML = pageHead(t("exam.eyebrow"), t("exam.title"), t("exam.lede"), "") +
      `<form id="examForm">
        <div class="resource-strip">
          <div class="field"><label>${t("wb.course")}</label><select id="examCourse" onchange="location.hash='#/exam?course='+encodeURIComponent(this.value)">${courseOpts}</select></div>
          <div class="field"><label>${t("wb.material")}</label><select name="artifact_id" id="examArtifact">${opts || `<option value="">${t("wb.chooseMaterial")}</option>`}</select></div>
        </div>
        <p class="small muted mb-8" id="examSubjectHint"></p>
        <div class="card">
        <div class="form-grid">
          <input type="hidden" name="subject" id="examSubject" value="${esc(inferExamSubject(courseArtifacts.find((a) => a.id === selectedArtifact)))}">
          <div class="field"><label>${t("exam.difficulty")}</label><select name="difficulty"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option></select></div>
          <div class="field"><label>${t("exam.mode")}</label><select name="mode">
            <option value="change_numbers">${t("exam.modeChange")}</option><option value="variant">${t("exam.modeVariant")}</option>
            <option value="mock" selected>${t("exam.modeMock")}</option><option value="predict">${t("exam.modePredict")}</option></select></div>
          <div class="field"><label>${t("exam.types")}</label><input name="types" placeholder="${esc(t("exam.typesHint"))}"></div>
          <div class="field"><label>${t("exam.references")}</label><label class="edit-file-picker" for="examRefs"><span class="edit-file-button">${t("exam.chooseRefs")}</span><span class="edit-file-names" id="examRefNames">${t("exam.noRefs")}</span></label><input id="examRefs" type="file" name="references" accept=".pdf,.ppt,.pptx,.doc,.docx,.png,.jpg,.jpeg,.webp" multiple hidden></div>
          <div class="field wide"><label class="small muted" style="display:flex;gap:8px;align-items:center;justify-content:flex-start;width:fit-content;text-align:left"><input type="checkbox" name="allow_non_question" value="1" style="width:auto;padding:0;border:0;background:none"><span style="flex:0 0 auto;text-align:left">参考文件不是题目时，按模拟出卷继续</span></label></div>
          <div class="field wide"><label>${t("exam.blueprint")}</label><textarea name="blueprint" rows="2" placeholder="${esc(t("exam.blueprintHint"))}"></textarea><div class="small muted mt-8">${t("exam.limit")}</div></div>
          <div class="field wide"><label>${t("exam.custom")}</label><textarea name="custom_prompt" rows="2" placeholder="${esc(t("exam.customHint"))}"></textarea></div>
        </div>
        <div class="actions"><button class="btn btn-primary" type="submit" id="examSubmit">${t("exam.start")}</button>
          <button class="btn btn-ghost" type="button" id="examCancel" hidden onclick="act.cancelExam()">${t("new.cancel")}</button>
          <span class="small muted" id="examMsg">${t("exam.referencesHint")}</span></div>
        </div>
      </form>
      <p class="small muted mt-8">${t("exam.afterGenerateHint")}</p>`;
    const examArtifact = document.getElementById("examArtifact");
    const examSubject = document.getElementById("examSubject");
    const applyInferredSubject = () => {
      if (!examArtifact || !examSubject) return;
      const art = items.find((x) => x.id === examArtifact.value);
      const subject = inferExamSubject(art);
      examSubject.value = subject;
      const hint = document.getElementById("examSubjectHint");
      if (hint) hint.textContent = t("exam.subjectAuto", { subject });
    };
    if (examArtifact) examArtifact.addEventListener("change", applyInferredSubject);
    applyInferredSubject();
    const examForm = document.getElementById("examForm");
    const examRefInput = document.getElementById("examRefs");
    const examRefNames = document.getElementById("examRefNames");
    const examMode = examForm.querySelector('select[name="mode"]');
    const examSubmit = document.getElementById("examSubmit");
    const examMsg = document.getElementById("examMsg");
    const examNeedsRef = () => examMode && ["change_numbers", "variant"].includes(examMode.value);
    const examHasRef = () => !!(examRefInput && examRefInput.files && examRefInput.files.length);
    const syncExamRefs = () => {
      const n = examRefInput && examRefInput.files ? examRefInput.files.length : 0;
      if (examRefNames) examRefNames.textContent = n ? Array.from(examRefInput.files).map((f) => f.name).join("、") : t("exam.noRefs");
      const needs = examNeedsRef();
      if (examSubmit) examSubmit.disabled = needs && !examHasRef();
      if (examMsg) examMsg.textContent = needs && !examHasRef() ? t("exam.refRequired") : t("exam.referencesHint");
      Array.from(examMode.options).forEach((opt) => {
        if (["change_numbers", "variant"].includes(opt.value)) opt.disabled = !examHasRef();
      });
      if (needs && !examHasRef()) examMode.value = "mock";
    };
    if (examRefInput) examRefInput.addEventListener("change", syncExamRefs);
    if (examMode) examMode.addEventListener("change", syncExamRefs);
    syncExamRefs();
    examForm.addEventListener("submit", (e) => {
      e.preventDefault();
      if (examNeedsRef() && !examHasRef()) { toast(t("exam.refRequired")); return; }
      const bp = String((examForm.querySelector('textarea[name="blueprint"]') || {}).value || "");
      const counts = [...bp.matchAll(/(\d+)\s*(?:道|个)?\s*(?:选择|填空|计算|简答|证明|名词|案例|论述|实验|设计)/g)]
        .map((m) => Number(m[1])).filter((n) => n > 0);
      const total = counts.reduce((a, b) => a + b, 0);
      if (total > 50) { toast(t("exam.limit")); return; }
      if (total >= 25 && !confirm(t("exam.longConfirm"))) return;
      startExam(new FormData(examForm));
    });
    math(view);
  }

  async function startExam(fd) {
    const mode = String(fd.get("mode") || "");
    const refs = fd.getAll("references").filter((f) => f && f.name);
    if (["change_numbers", "variant"].includes(mode) && !refs.length) { toast(t("exam.refRequired")); return; }
    const btn = document.getElementById("examSubmit");
    const msg = document.getElementById("examMsg");
    const cancel = document.getElementById("examCancel");
    if (btn) btn.disabled = true;
    if (cancel) cancel.hidden = false;
    if (msg) msg.textContent = t("exam.generating");
    try {
      const res = await fetch("/api/exam/jobs", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || t("exam.failed"));
      state.exam.jobId = data.job_id;
      lockGenerationJob(data.job_id, t("exam.generating"));
      pollExamJob(data.job_id);
    } catch (e) {
      if (msg) msg.innerHTML = `<span class="badge badge-bad">${esc(requestErrorMessage(e, t("exam.failed")))}</span>`;
      if (btn) btn.disabled = false;
      if (cancel) cancel.hidden = true;
    }
  }

  async function pollExamJob(jobId) {
    const msg = document.getElementById("examMsg");
    const btn = document.getElementById("examSubmit");
    const cancel = document.getElementById("examCancel");
    try {
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (msg) {
        const elapsed = Number(job.elapsed_s) || 0;
        const pct = Number(job.progress) || 0;
        const eta = estimateJobEta(job, "exam");
        showGenerationRing(pct, eta, job.step || t("exam.generating"));
        msg.textContent = `${job.step || t("exam.generating")} ${pct}%` + (elapsed ? ` · ${t("new.elapsedOnly", { elapsed: formatDuration(elapsed) })}` : "") + (eta ? ` · ${t("new.eta", { eta: formatDuration(eta) })}` : "");
      }
      if (job.status === "done") {
        hideGenerationRing();
        unlockGenerationJob();
        const doc = jobResult(job);
        state.exam.doc = doc;
        const docId = doc && (doc.id || (doc.doc && doc.doc.id));
        if (docId) {
          const artifact = doc.artifact_id || (state.exam && state.exam.pickArtifact) || "";
          location.hash = `#/exam?artifact=${encodeURIComponent(artifact)}&doc=${encodeURIComponent(docId)}`;
          return;
        }
        const box = document.getElementById("examResult");
        if (box) box.innerHTML = examPaper(doc);
        math(box);
        if (btn) btn.disabled = false;
        if (cancel) cancel.hidden = true;
        return;
      }
      if (job.status === "failed") { hideGenerationRing(); unlockGenerationJob(); throw new Error(job.error || t("exam.failed")); }
      if (job.status === "cancelled") { hideGenerationRing(); unlockGenerationJob(); if (msg) msg.textContent = t("new.cancelled"); if (btn) btn.disabled = false; if (cancel) cancel.hidden = true; return; }
      setTimeout(() => pollExamJob(jobId), 1500);
    } catch (e) {
      if (msg) msg.innerHTML = `<span class="badge badge-bad">${esc(requestErrorMessage(e, t("exam.failed")))}</span>`;
      if (btn) btn.disabled = false;
      if (cancel) cancel.hidden = true;
    }
  }

  async function cancelExam() {
    if (!state.exam.jobId) return;
    try { await api(`/api/jobs/${encodeURIComponent(state.exam.jobId)}/cancel`, { method: "POST", body: {} }); }
    catch (e) { toast(e.message || t("new.cancelFailed")); }
  }

  function examAnswers() {
    const paper = document.getElementById("examPaper");
    if (!paper) return;
    const hidden = paper.querySelector(".exam-answer")?.hidden;
    paper.querySelectorAll(".exam-answer").forEach((el) => { el.hidden = !hidden; });
  }
  function examEdit() {
    const paper = document.getElementById("examPaper");
    if (!paper) return;
    const next = paper.contentEditable !== "true";
    paper.contentEditable = next ? "true" : "false";
    paper.classList.toggle("is-editing", next);
    toast(next ? t("exam.editOn") : t("exam.editOff"));
  }
  function examDownload(name, html) {
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 3000);
  }
  function examExport() {
    const paper = document.getElementById("examPaper");
    if (!paper) return;
    const css = `body{margin:0;background:#f0eee8;font-family:"Songti SC",SimSun,serif;color:#1f2529;line-height:1.9}
      .exam-paper{max-width:900px;margin:24px auto;background:#fff;padding:48px 56px;box-shadow:0 2px 18px rgba(0,0,0,.08)}
      .paper-toolbar,.exam-answer{display:none!important}.exam-source-figure{max-width:100%;text-align:center;margin:14px 0}
      .exam-source-figure img{max-width:100%;height:auto}.exam-options{display:grid;grid-template-columns:1fr 1fr;gap:6px 20px}
      .exam-q{margin:18px 0;break-inside:avoid}.exam-stem{font-size:15px}.score-tag{float:right;color:#777}
      .exam-section h3{border-bottom:1px solid #bbb;padding-bottom:6px;margin-top:26px}.exam-head{text-align:center;border-bottom:2px solid #222;padding-bottom:18px}
      .export-back{position:fixed;left:18px;top:14px;z-index:1000;display:flex;align-items:center;gap:8px}.export-back img{width:25px;height:25px;object-fit:contain}.export-back b{font:600 12px -apple-system,sans-serif}.export-back a{display:inline-block;padding:8px 12px;border:1px solid #bbb;border-radius:6px;background:#fff;color:#245c73;text-decoration:none;font:13px -apple-system,sans-serif}`;
    const examDoc = state.exam && state.exam.doc;
    const examArtifact = examDoc && examDoc.artifact_id ? examDoc.artifact_id : "";
    const appBack = `${location.origin}/#/exam${examArtifact ? `?artifact=${encodeURIComponent(examArtifact)}` : ""}`;
    const backBar = `<div class="export-back"><img src="${location.origin}/static/logo-mark.svg" alt=""><b>TermFinale</b><a href="${appBack}" target="_top">← 返回上一级</a></div>`;
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>${esc(state.exam?.doc?.title || "试卷")}</title><style>${css}</style></head><body>${backBar}${paper.outerHTML}</body></html>`;
    saveDocumentFile(examDoc?.id || "", "html", html);
  }
  function examWord() {
    const doc = state.exam && state.exam.doc;
    if (!doc || !doc.id) { toast(t("exam.failed")); return; }
    saveDocumentFile(doc.id, "docx");
  }

  function startPracticePick() {
    const select = document.getElementById("pPickArtifact");
    if (!select || !select.value) return;
    location.hash = `#/practice/${encodeURIComponent(select.value)}`;
  }

  function practiceKey(id) { return `tf-practice-${id}`; }

  function savePracticeSession(p) {
    if (!p || !p.artifact || !p.questions || !p.questions.length) return;
    if (p.index >= p.questions.length) { localStorage.removeItem(practiceKey(p.artifact.id)); return; }
    try {
      localStorage.setItem(practiceKey(p.artifact.id), JSON.stringify({
        artifactId: p.artifact.id, mode: p.mode || "generate", section: p.section,
        count: p.count, questions: p.questions, index: p.index,
        correct: p.correct, answered: p.answered, wrong: p.wrong,
      }));
    } catch (e) { /* local storage can be unavailable */ }
  }

  function loadPracticeSession(id) {
    try {
      const raw = localStorage.getItem(practiceKey(id));
      if (!raw) return null;
      const p = JSON.parse(raw);
      if (!p || p.artifactId !== id || !Array.isArray(p.questions) || !p.questions.length) return null;
      if (p.index >= p.questions.length) { localStorage.removeItem(practiceKey(id)); return null; }
      return p;
    } catch (e) { return null; }
  }

  function clearPracticeSession(id) {
    try { localStorage.removeItem(practiceKey(id)); } catch (e) {}
  }

  async function renderBank(id, seq) {
    const [a, data] = await Promise.all([api(`/api/artifacts/${encodeURIComponent(id)}`), api(`/api/bank?artifact_id=${encodeURIComponent(id)}`)]);
    if (seq !== state.seq) return;
    const questions = data.questions || [];
    const rows = questions.map((q) => `<div class="card bank-q"><div class="card-top"><div><h3 class="card-title">${esc(q.stem)}</h3><div class="card-meta"><span>${esc(q.section)}</span><span>${q.page ? t("unit.pageN", { n: q.page }) : ""}</span><span>${t("bank.answer", { x: String.fromCharCode(65 + Number(q.answer)) })}</span></div></div><button class="btn btn-ghost" onclick="act.deleteBankQuestion('${esc(q.id)}','${esc(a.id)}')">${t("doc.delete")}</button></div><div class="small muted">${(q.options || []).map((o, i) => `${String.fromCharCode(65 + i)}. ${esc(o)}`).join(" · ")}</div></div>`).join("");
    view.innerHTML = pageHead(t("bank.eyebrow"), t("bank.title"), t("bank.lede"),
      `<a class="btn btn-primary" href="#/practice/${encodeURIComponent(a.id)}?bank=1">${t("bank.practice")}</a>`) +
      `<div class="small muted mb-16">${esc(a.title)} · ${t("bank.count", { n: questions.length })}</div>` +
      (rows ? `<div class="list">${rows}</div>` : empty(t("bank.emptyTitle"), t("bank.emptyText"), `<a class="btn btn-primary" href="#/workbench?artifact=${encodeURIComponent(a.id)}">${t("course.openTools")}</a>`));
  }

  async function renderPractice(id, seq) {
    if (!id) {
      const [allItems, courses] = await Promise.all([api("/api/artifacts"), api("/api/courses").catch(() => [])]);
      if (seq !== state.seq) return;
      const practiceParams = new URLSearchParams(location.hash.split("?")[1] || "");
      const courseFilter = practiceParams.get("course") || currentCourseKey() || ((courses[0] && courses[0].key) || "");
      const items = (courseFilter ? allItems.filter((a) => a.course_key === courseFilter) : allItems)
        .filter((a) => !a.source_only);
      state.artifacts = items;
      const byCourse = new Map();
      (courses || []).forEach((c) => byCourse.set(c.key, c));
      const groups = new Map();
      items.forEach((a) => {
        const key = a.course_key || "";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(a);
      });
      const options = items.map((a) => `<option value="${esc(a.id)}">${esc(a.title)} · ${esc(qualityStatusLabel(a.quality))}</option>`).join("");
      const course = courseFilter ? byCourse.get(courseFilter) : null;
      const courseOpts = (courses || []).map((c) => `<option value="${esc(c.key)}" ${c.key === courseFilter ? "selected" : ""}>${esc(c.name)}</option>`).join("");
      const scope = course ? `<div class="small muted mb-8">${t("practice.courseScope", { name: course.name })}</div>` : "";
      view.innerHTML = pageHead(t("practice.eyebrow"), t("practice.title"), t("practice.listLede"), "") +
        `<div class="resource-strip">
          <div class="field"><label>${t("wb.course")}</label><select id="pPickCourse" onchange="location.hash='#/practice?course='+encodeURIComponent(this.value)">${courseOpts || `<option value="">${t("wb.chooseCourse")}</option>`}</select></div>
          <div class="field"><label>${t("wb.material")}</label><select id="pPickArtifact">${options || `<option value="">${t("wb.chooseMaterial")}</option>`}</select></div>
        </div>
        <div class="card practice-picker">${scope}<div class="small muted mb-8">${t("practice.pickHint")}</div>
        <div class="practice-pick-row"><button class="btn btn-primary" onclick="act.startPracticePick()" ${items.length ? "" : "disabled"}>${t("practice.start")}</button></div></div>`;
      if (!items.length) {
        const course = courseFilter ? byCourse.get(courseFilter) : null;
        view.innerHTML = pageHead(t("practice.eyebrow"), t("practice.title"), t("practice.listLede"), "") +
          empty(t("practice.noLectureTitle"), t("practice.noLectureText", { name: course ? course.name : "" }), courseFilter ? `<button class="btn btn-primary" type="button" onclick="window.tfPickSource('${esc(courseFilter)}')">${t("course.generateLecture")}</button>` : "");
      }
      return;
    }
    const a = await api(`/api/artifacts/${encodeURIComponent(id)}`);
    if (seq !== state.seq) return;
    const q = new URLSearchParams(location.hash.split("?")[1] || "");
    const first = q.get("section") || (a.section_list[0] && a.section_list[0].id) || "";
    const bank = q.get("bank") === "1";
    const sourceMode = q.get("source") === "1";
    const sourcePages = (q.get("pages") || "").split(",").map((x) => Number(x)).filter((x) => Number.isFinite(x) && x > 0);
    state.practice = { artifact: a, section: first, count: 3, mode: sourceMode ? "source" : (bank ? "bank" : "generate"), sourcePages, questions: null, index: 0, selected: null, result: null, correct: 0, answered: 0, wrong: 0 };
    const saved = loadPracticeSession(a.id);
    if (saved && saved.mode === state.practice.mode) {
      state.practice = { ...state.practice, ...saved, artifact: a };
      view.innerHTML = `<div class="resume-banner"><span>${t("practice.resumed", { i: saved.index + 1, n: saved.questions.length })}</span><button class="btn btn-ghost" onclick="act.practiceRestart('${encodeURIComponent(a.id)}')">${t("practice.restart")}</button></div><div id="pBody"></div>`;
      paintQuestion();
      return;
    }
    view.innerHTML = practiceSetup(a);
    document.getElementById("pStart").onclick = () => startQuestions();
    const pSection = document.getElementById("pSection");
    if (pSection) pSection.onchange = (e) => { state.practice.section = e.target.value; };
    const pCount = document.getElementById("pCount");
    if (pCount) pCount.onchange = (e) => { state.practice.count = Number(e.target.value); };
    math(view);
  }

  function paintPracticeBody(html) {
    const body = document.getElementById("pBody");
    if (body) body.innerHTML = html;
    math(body || view);
  }

  async function importBank(docId) {
    try {
      const r = await api(`/api/documents/${encodeURIComponent(docId)}/bank`, { method: "POST", body: {} });
      toast(t("wb.bankAdded", { n: r.count || 0 }));
    } catch (e) { toast(e.message || t("wb.bankFailed")); }
  }

  async function startQuestions() {
    const p = state.practice;
    if (!p) return;
    p.questions = null; p.index = 0; p.selected = null; p.result = null; p.correct = 0; p.answered = 0; p.wrong = 0;
    clearPracticeSession(p.artifact.id);
    const start = document.getElementById("pStart");
    if (start) start.disabled = true;
    p.abort = new AbortController();
    lockGenerationJob("practice", t("practice.generating"));
    paintPracticeBody(`<div class="loading"><span class="spinner"></span>${t("practice.generating")}<button class="btn btn-ghost" onclick="act.cancelPractice()">${t("practice.cancel")}</button></div>`);
    try {
      const endpoint = p.mode === "bank" ? "/api/practice/bank" : (p.mode === "source" ? "/api/practice/source" : "/api/practice");
      const body = p.mode === "bank"
        ? { artifact_id: p.artifact.id, count: p.count }
        : (p.mode === "source" ? { artifact_id: p.artifact.id, pages: p.sourcePages || [], count: p.count } : { artifact_id: p.artifact.id, section: p.section, count: p.count });
      const data = await api(endpoint, { method: "POST", body, signal: p.abort.signal });
      p.abort = null;
      p.questions = data.questions || [];
      if (!p.questions.length) throw new Error(t("practice.noQuestions"));
      if ((data.skipped_pages || []).length) {
        toast(t("practice.skippedPages", { pages: data.skipped_pages.join("、") }), 6000);
      }
      unlockGenerationJob();
      savePracticeSession(p);
      paintQuestion();
    } catch (e) {
      if (e.name === "AbortError") { p.abort = null; unlockGenerationJob(); await route(); return; }
      p.abort = null;
      unlockGenerationJob();
      paintPracticeBody(errorBox(e.message || t("practice.generateFailed"), `<button class="btn btn-ghost" id="pRetry">${t("practice.retry")}</button>`));
      const retry = document.getElementById("pRetry");
      if (retry) retry.onclick = () => startQuestions();
    }
  }

  function cancelPractice() {
    if (state.practice && state.practice.abort) {
      try { state.practice.abort.abort(); } catch (e) {}
      state.practice.abort = null;
    }
  }

  async function practiceRestart(id) {
    clearPracticeSession(decodeURIComponent(id));
    state.practice = null;
    await route();
  }

  function paintQuestion() {
    const p = state.practice;
    if (!p || !p.questions) return;
    if (p.index >= p.questions.length) { paintSummary(); return; }
    const q = p.questions[p.index];
    p.selected = null; p.result = null;
    const opts = q.options.map((o, i) => `<button class="option" data-opt="${i}" onclick="act.selectOption(${i})">
      <span class="letter">${String.fromCharCode(65 + i)}</span><span>${esc(o)}</span></button>`).join("");
    paintPracticeBody(`<div class="question">
      <div class="q-progress"><span>${t("practice.progress", { i: p.index + 1, n: p.questions.length })}</span><div class="q-bar"><i style="width:${Math.round(((p.index) / p.questions.length) * 100)}%"></i></div><span>${q.page ? t("practice.sourcePage", { n: q.page }) : ""}</span></div>
      <div class="card"><div class="q-stem">${String(q.stem).split("\n").map((x) => `<p>${esc(x)}</p>`).join("")}</div>
      <div class="options" id="qOptions">${opts}</div>
      <div class="actions"><button class="btn btn-primary" id="qSubmit" disabled onclick="act.submitAnswer()">${t("practice.submit")}</button><span class="small muted">${t("practice.submitHint")}</span></div>
      <div id="qResult"></div></div></div>`);
  }

  function selectOption(i) {
    const p = state.practice;
    if (!p || p.result) return;
    p.selected = i;
    document.querySelectorAll("#qOptions .option").forEach((el, idx) => el.classList.toggle("selected", idx === i));
    const btn = document.getElementById("qSubmit");
    if (btn) btn.disabled = false;
  }

  async function submitAnswer() {
    const p = state.practice;
    if (!p || p.selected === null || p.result) return;
    const btn = document.getElementById("qSubmit");
    if (btn) btn.disabled = true;
    try {
      const r = await api("/api/attempts", { method: "POST", body: { question_id: p.questions[p.index].id, chosen: p.selected } });
      p.result = r; p.answered += 1; if (r.correct) p.correct += 1; else p.wrong += 1;
      paintResult();
    } catch (e) {
      toast(e.message || t("practice.gradeFailed"));
      if (btn) btn.disabled = false;
    }
  }

  function paintResult() {
    const p = state.practice;
    if (!p || !p.result) return;
    document.querySelectorAll("#qOptions .option").forEach((el, idx) => {
      el.disabled = true;
      if (idx === p.result.answer) el.classList.add("correct");
      if (idx === p.selected && !p.result.correct) el.classList.add("wrong");
    });
    const last = p.index === p.questions.length - 1;
    const resultBox = document.getElementById("qResult");
    resultBox.innerHTML = `<div class="result ${p.result.correct ? "good" : "bad"}">
      <strong>${p.result.correct ? t("practice.correct") : t("practice.wrong")}</strong>
      <p>${t("practice.answerText", { letter: String.fromCharCode(65 + p.result.answer), explanation: esc(p.result.explanation || "") })}</p>
      <div class="page">${p.result.page ? t("practice.sourceLine", { n: p.result.page }) : ""}</div>
    </div><div class="actions"><button class="btn btn-primary" onclick="act.nextQuestion()">${last ? t("practice.finish") : t("practice.next")}</button></div>`;
    math(resultBox);
  }

  function nextQuestion() {
    const p = state.practice;
    if (!p) return;
    p.index += 1;
    savePracticeSession(p);
    paintQuestion();
  }

  function paintSummary() {
    const p = state.practice;
    if (!p) return;
    clearPracticeSession(p.artifact.id);
    const total = p.questions.length;
    const acc = total ? Math.round((p.correct / total) * 100) : 0;
    const wrong = p.wrong || 0;
    const next = wrong
      ? `<p class="review-next">${t("practice.wrongScheduled", { n: wrong })}</p><div class="actions"><a class="btn btn-ghost" href="#/review?tab=scheduled">${t("practice.goScheduled")}</a>`
      : `<p class="review-next">${t("practice.noWrong")}</p><div class="actions">`;
    paintPracticeBody(`<div class="card"><div class="eyebrow">DONE</div><h2>${t("practice.doneTitle")}</h2>
      <p class="lede">${t("practice.doneText", { correct: p.correct, total, acc })}</p>
      ${next}
      <button class="btn btn-primary" onclick="act.startQuestions()">${t("practice.again")}</button>
      <a class="btn btn-ghost" href="#/artifact/${encodeURIComponent(p.artifact.id)}">${t("practice.viewQuality")}</a></div></div>`);
  }

  async function renderReview(seq) {
    const [r, items, courses] = await Promise.all([api("/api/review"), api("/api/artifacts"), api("/api/courses").catch(() => [])]);
    if (seq !== state.seq) return;
    state.review = r;
    state.review.revealed = {};
    const params = new URLSearchParams(location.hash.split("?")[1] || "");
    const tab = params.get("tab") === "scheduled" ? "scheduled" : "due";
    const courseKey = params.get("course") || currentCourseKey() || "";
    const byCourse = new Map((courses || []).map((c) => [c.key, c]));
    const artifactCourse = new Map((items || []).map((a) => [a.id, a.course_key || ""]));
    const inCourse = (x) => !courseKey || artifactCourse.get(x.artifact_id) === courseKey;
    const titles = Object.fromEntries(items.map((a) => [a.id, a.title]));
    const due = (r.due || []).filter(inCourse);
    const scheduled = (r.scheduled || []).filter(inCourse);
    const mastery = (r.mastery || []).filter(inCourse);
    const link = (nextTab, nextCourse = courseKey) => {
      const q = new URLSearchParams();
      if (nextTab && nextTab !== "due") q.set("tab", nextTab);
      if (nextCourse) q.set("course", nextCourse);
      return "#/review" + (q.toString() ? "?" + q.toString() : "");
    };
    const courseOptions = `<option value="">${t("review.allCourses")}</option>` + (courses || []).map((c) => `<option value="${esc(c.key)}" ${c.key === courseKey ? "selected" : ""}>${esc(c.name)}</option>`).join("");
    const dueCards = due.map((m) => `<div class="card review-card" data-mid="${m.id}">
      <div class="card-top"><div><h3 class="card-title">${esc(m.stem)}</h3>
        <div class="card-meta"><span>${esc(titles[m.artifact_id] || m.artifact_id)}</span><span>${esc(m.section)}</span><span>${t("review.wrongTimes", { n: m.wrong_count })}</span>${m.page ? `<span>${t("unit.pageN", { n: m.page })}</span>` : ""}</div></div>
        <span class="badge badge-warn">${t("status.due")}</span></div>
      <div class="options mt-16">${(m.options || []).map((o, i) => `<div class="option"><span class="letter">${String.fromCharCode(65 + i)}</span><span>${esc(o)}</span></div>`).join("")}</div>
      <div id="rev-${m.id}"></div>
      <div class="actions"><button class="btn btn-ghost" onclick="act.revealReview(${m.id})">${t("review.showAnswer")}</button>
        <button class="btn btn-primary" onclick="act.reviewResult(${m.id}, 'remembered')">${t("review.remembered")}</button>
        <button class="btn btn-ghost" onclick="act.reviewResult(${m.id}, 'forgot')">${t("review.forgot")}</button></div>
    </div>`).join("");
    const scheduledCards = scheduled.map((m) => `<div class="card review-card scheduled">
      <div class="card-top"><div><h3 class="card-title">${esc(m.stem)}</h3>
        <div class="card-meta"><span>${esc(titles[m.artifact_id] || m.artifact_id)}</span><span>${esc(m.section)}</span><span>${t("review.wrongTimes", { n: m.wrong_count })}</span></div></div>
        <span class="badge badge-neutral">${t("review.nextDate", { date: esc(m.next_review) })}</span></div>
    </div>`).join("");
    const totalWrong = courseKey ? due.length + scheduled.length : r.all_count;
    const masteryHtml = mastery.map((x) => {
      const pct = x.score === null || x.score === undefined ? 0 : Math.round(x.score);
      const conf = Math.round((x.confidence || 0) * 100);
      return `<tr><td><strong>${esc(titles[x.artifact_id] || x.artifact_id)}</strong><div class="small muted">${esc(x.section)}</div></td>
        <td class="num">${x.attempts}</td><td class="num">${x.correct}</td>
        <td>${x.accuracy === null ? "—" : Math.round(x.accuracy * 100) + "%"}</td>
        <td><span class="mastery-bar"><i style="width:${pct}%"></i></span> <span class="small">${x.score === null || x.score === undefined ? "—" : pct + "% · " + conf + "%"}</span></td></tr>`;
    }).join("");
    const tabs = `<div class="review-tabs"><a class="${tab === "due" ? "on" : ""}" href="${link("due")}">${t("review.tabDue")} · ${due.length}</a><a class="${tab === "scheduled" ? "on" : ""}" href="${link("scheduled")}">${t("review.tabScheduled")} · ${scheduled.length}</a><select id="revCourse" aria-label="${t("review.courseFilter")}" onchange="location.hash=this.value ? '#/review?${tab === "scheduled" ? "tab=scheduled&" : ""}course='+encodeURIComponent(this.value) : '${link(tab, "")}'">${courseOptions}</select></div>`;
    const doNewHref = "#/practice" + (courseKey ? `?course=${encodeURIComponent(courseKey)}` : "");
    const content = tab === "scheduled"
      ? (scheduledCards ? `<div class="list">${scheduledCards}</div>` : empty(t("review.scheduledEmptyTitle"), t("review.scheduledEmptyText")))
      : (dueCards ? `<div class="list">${dueCards}</div>` : empty(t("review.emptyTitle"), t("review.emptyText"), `<a class="btn btn-primary" href="${doNewHref}">${t("review.emptyCta")}</a>`));
    const forecast = (r.forecast || []).filter((x) => x.due > 0);
    const forecastLine = forecast.length
      ? `<p class="small muted mt-8">${t("review.forecast", { list: forecast.map((x) => `${esc(String(x.date).slice(5))} · ${x.due}`).join("　") })}</p>`
      : "";
    view.innerHTML = pageHead(t("review.eyebrow"), t("review.title"), t("review.lede"),
      `<a class="btn btn-ghost" href="${doNewHref}">${t("review.doNew")}</a>`) +
      `<div class="stat-row"><div class="stat warn"><strong>${due.length}</strong><span>${t("review.dueToday")}</span></div>
        <div class="stat"><strong>${scheduled.length}</strong><span>${t("review.scheduledCount")}</span></div>
        <div class="stat"><strong>${totalWrong}</strong><span>${t("review.totalWrong")}</span></div></div>` +
      forecastLine +
      tabs + `<section class="section-title"><h2>${tab === "scheduled" ? t("review.scheduledTitle") : t("review.dueTitle")}</h2></section>` + content +
      `<section class="section-title"><h2>${t("review.mastery")}</h2></section>` +
      (masteryHtml ? `<div class="table-wrap"><table class="table"><thead><tr><th>${t("review.tableSection")}</th><th>${t("review.tableAttempts")}</th><th>${t("review.tableCorrect")}</th><th>${t("review.tableAccuracy")}</th><th>${t("review.tableScore")}</th></tr></thead><tbody>${masteryHtml}</tbody></table></div>` : `<div class="muted small">${t("review.noRecords")}</div>`);
    math(view);
  }

  function revealReview(mid) {
    const m = (state.review.due || []).find((x) => x.id === mid);
    if (!m) return;
    const box = document.getElementById(`rev-${mid}`);
    if (!box) return;
    box.innerHTML = `<div class="review-answer"><p><strong>${t("review.correctAnswer")}</strong>${String.fromCharCode(65 + m.answer)}</p><p>${esc(m.explanation || "")}</p>${m.page ? `<p class="small muted">${t("review.sourceLine", { n: m.page })}</p>` : ""}</div>`;
  }

  async function reviewResult(mid, result) {
    try {
      await api(`/api/review/${mid}`, { method: "POST", body: { result } });
      toast(result === "remembered" ? t("review.advance") : t("review.reset"));
      await route();
    } catch (e) { toast(e.message || t("review.failed")); }
  }

  async function renderSettings(seq) {
    const s = await api("/api/settings");
    if (seq !== state.seq) return;
    state.settings = s;
    profileAvatarDraft = s.avatar || "";
    const theme = document.documentElement.dataset.theme || s.theme || "light";
    const activeLang = state.lang;
    view.innerHTML = pageHead(t("settings.eyebrow"), t("settings.title"), t("settings.lede"), "") +
      `<div class="grid grid-2">
        <div class="card"><h3 class="card-title">${t("settings.profile")}</h3><div class="card-meta">${t("settings.profileHint")}</div>
          <div class="card-body"><div class="settings-profile-row"><label class="settings-avatar" for="profileAvatarFile" title="${t("settings.avatarHint")}">${s.avatar ? `<img src="${esc(s.avatar)}" alt="avatar">` : esc(Array.from(s.name || t("user.default"))[0] || "学")}<i>+</i></label><input id="profileAvatarFile" type="file" accept="image/png,image/jpeg,image/webp" hidden>
          <div class="field" style="flex:1"><label>${t("settings.profileName")}</label><input id="profileName" maxlength="24" value="${esc(s.name || "")}"></div></div>
          <div class="ob-school-fields settings-school-fields"><div class="school-combo"><label>${t("settings.schoolLabel")}</label><input id="profileSchool" maxlength="80" value="${esc(s.school || "")}" placeholder="" autocomplete="off"><div class="school-menu" id="profileSchoolMenu" hidden></div></div><div class="field"><label>${t("settings.schoolTierLabel")}</label><select id="profileSchoolTier"><option value="">${t("settings.schoolTierPlaceholder")}</option>${schoolTierOptions(s.school_tier || "")}</select></div></div>
          <div id="profileSchoolSelected">${schoolSelectedHtml(s.school || "", s.school_logo || "")}</div><div class="field mt-8"><label>${t("settings.majorLabel")}</label><input id="profileMajor" maxlength="60" value="${esc(s.major || "")}" placeholder="" autocomplete="off"></div></div>
          <div class="actions"><button class="btn btn-primary" onclick="act.saveProfile()">${t("settings.saveProfile")}</button><span class="small muted">${t("settings.avatarHint")}</span></div></div>
        <div class="card"><h3 class="card-title">${t("settings.appearance")}</h3><div class="card-meta">${t("settings.themeMeta")}</div>
          <div class="actions"><button class="btn ${theme === "light" ? "btn-primary" : "btn-ghost"}" onclick="act.setTheme('light')">${t("settings.light")}</button>
          <button class="btn ${theme === "dark" ? "btn-primary" : "btn-ghost"}" onclick="act.setTheme('dark')">${t("settings.dark")}</button></div></div>
        <div class="card"><h3 class="card-title">${t("settings.model")}</h3><div class="card-meta">${t("settings.keyLocal")}</div>
          <div class="card-body">
            <div>${t("settings.textGeneration")}<span class="mono">${esc(s.model)}</span></div>
            <div class="key-status-row"><span>DeepSeek</span><span id="deepseekKeyStatus" class="badge ${s.deepseek ? "badge-good" : "badge-bad"}">${s.deepseek ? t("status.configured") : t("status.notConfigured")}</span></div>
            <div class="key-status-row"><span>阿里云百炼</span><span id="dashscopeKeyStatus" class="badge ${s.dashscope ? "badge-good" : "badge-bad"}">${s.dashscope ? t("status.configured") : t("status.notConfigured")}</span></div>
            <div class="key-status-row"><span>Kimi（Moonshot）</span><span id="kimiKeyStatus" class="badge ${s.kimi ? "badge-good" : "badge-bad"}">${s.kimi ? t("status.configured") : t("status.notConfigured")}</span></div>
            <div class="key-edit-grid">
              <div class="field"><label>DEEPSEEK API KEY</label><input id="deepseekKeyInput" type="password" autocomplete="new-password" placeholder="${s.deepseek ? t("settings.keyPlaceholderSet") : t("settings.keyPlaceholder")}"></div>
              <div class="field"><label>阿里云百炼 API KEY</label><input id="dashscopeKeyInput" type="password" autocomplete="new-password" placeholder="${s.dashscope ? t("settings.keyPlaceholderSet") : t("settings.keyPlaceholder")}"></div>
              <div class="field"><label>KIMI API KEY（可选）</label><input id="kimiKeyInput" type="password" autocomplete="new-password" placeholder="${s.kimi ? t("settings.keyPlaceholderSet") : t("settings.keyPlaceholder")}"></div>
            </div>
            <div class="actions"><button class="btn btn-primary" id="keySaveBtn" onclick="act.saveKeys()">${t("settings.saveKeys")}</button>
              <button class="btn btn-ghost" id="keyTestBtn" onclick="act.testKeys()">${t("settings.testKeys")}</button></div>
            <div id="keyTestResult" class="small muted mt-8"></div>
            <div class="small muted mt-8">${t("settings.keyNote")}</div>
          </div></div>
        <div class="card"><h3 class="card-title">${t("settings.language")}</h3><div class="card-meta">${t("settings.languageMeta")}</div>
          <div class="card-body">${t("lang.note")}</div>
          <div class="actions">
            <button class="btn ${activeLang === "zh" ? "btn-primary" : "btn-ghost"}" onclick="act.setLang('zh')">${t("lang.zh")}</button>
            <button class="btn ${activeLang === "hant" ? "btn-primary" : "btn-ghost"}" onclick="act.setLang('hant')">${t("lang.hant")}</button>
            <button class="btn ${activeLang === "en" ? "btn-primary" : "btn-ghost"}" onclick="act.setLang('en')">${t("lang.en")}</button>
          </div></div>
        <div class="card"><h3 class="card-title">${t("settings.data")}</h3><div class="card-meta">SQLite</div>
          <div class="card-body"><div class="mono small">${esc(s.db)}</div>
          <div class="small muted mt-8">${t("settings.dataNote")}</div></div></div>
        <div class="card"><h3 class="card-title">${t("settings.backup")}</h3><div class="card-meta">${t("settings.backupMeta")}</div>
          <div class="card-body"><div class="small muted">${t("settings.backupNote")}</div></div>
          <div class="actions"><a class="btn btn-primary" href="/api/backup">${t("settings.backupNow")}</a></div></div>
      </div>`;
    const avatarFile = document.getElementById("profileAvatarFile");
    if (avatarFile) avatarFile.onchange = () => setProfileAvatar(avatarFile);
    const pSchool = document.getElementById("profileSchool"), pMenu = document.getElementById("profileSchoolMenu"), pTier = document.getElementById("profileSchoolTier");
    if (pSchool) attachSchoolSearch(pSchool, pMenu, (x) => {
      const box = document.getElementById("profileSchoolSelected");
      if (box) box.innerHTML = schoolSelectedHtml(x.name, x.logo || "");
      pSchool.dataset.logo = x.logo || "";
    });
  }

  function setProfileAvatar(fileInput) {
    const f = fileInput.files && fileInput.files[0];
    if (!f) return;
    if (f.size > 350000) { toast(t("onboard.avatarTooBig")); return; }
    const reader = new FileReader();
    reader.onload = () => {
      profileAvatarDraft = String(reader.result || "");
      const box = document.querySelector(".settings-avatar");
      if (box) box.innerHTML = `<img src="${esc(profileAvatarDraft)}" alt="avatar"><i>+</i>`;
    };
    reader.readAsDataURL(f);
  }




  const TASKS = [
    { kind: "extract_points", labelKey: "task.extractPoints", hintKey: "task.extractPointsHint" },
    { kind: "extract_nouns", labelKey: "task.extractNouns", hintKey: "task.extractNounsHint" },
    { kind: "extract_questions", labelKey: "task.extractQuestions", hintKey: "task.extractQuestionsHint" },
    { kind: "mindmap", labelKey: "task.mindmap", hintKey: "task.mindmapHint" },
    { kind: "analysis", labelKey: "task.analysis", hintKey: "task.analysisHint" },
  ];

  function taskLabel(kind) {
    const task = TASKS.find((x) => x.kind === kind);
    return task ? t(task.labelKey) : kind;
  }

  function taskHint(kind) {
    const task = TASKS.find((x) => x.kind === kind);
    return task ? t(task.hintKey) : "";
  }

  function docSectionLabel(doc) {
    const sec = String((doc && doc.section) || "");
    if (!sec || sec === "__all__") return t("wb.allSections");
    return sec.split("（")[0];
  }

  function taskDocSource(doc) {
    const w = state.workbench || {};
    const art = (w.artifacts || []).find((a) => a.id === (doc && doc.artifact_id)) || {};
    return {
      title: art.title || (doc && doc.artifact_title) || (doc && doc.title) || t("doc.unknownSource"),
      course: art.course || "",
      section: docSectionLabel(doc),
      task: taskLabel(doc && doc.kind),
    };
  }

  function openDocReader(doc) {
    if (!doc) return;
    const src = taskDocSource(doc);
    const overlay = document.getElementById("docReaderOverlay");
    if (!overlay) return;
    const title = document.getElementById("docReaderTitle");
    const kicker = document.getElementById("docReaderKicker");
    const meta = document.getElementById("docReaderMeta");
    const paper = document.getElementById("docReaderPaper");
    if (kicker) kicker.textContent = `${src.course ? src.course + " · " : ""}${src.title}`;
    if (title) title.textContent = src.title;
    if (meta) meta.textContent = `${src.task} · ${src.section} · ${docStatusLabel(doc.status)} · ${(doc.created_at || "").replace("T", " ")}`;
    const printHead = `<div class="doc-print-head"><h1>${esc(src.title)}</h1><p>${esc(src.task)} · ${esc(src.section)} · TermFinale</p></div>`;
    if (paper) paper.innerHTML = printHead + taskResult(doc);
    overlay.hidden = false;
    document.body.classList.add("doc-reader-open");
    const input = document.getElementById("docSearchInput");
    if (input) {
      input.value = "";
      input.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); docReaderSearch(); } };
    }
  }

  function closeDocReader(event) {
    if (event && event.target && event.target.closest && event.target.closest("button")) {
      // explicit button click
    }
    const overlay = document.getElementById("docReaderOverlay");
    if (overlay) overlay.hidden = true;
    document.body.classList.remove("doc-reader-open");
  }

  function clearDocHits(root) {
    if (!root) return;
    root.querySelectorAll("mark.doc-hit").forEach((m) => {
      const text = document.createTextNode(m.textContent || "");
      m.replaceWith(text);
    });
    root.normalize();
  }

  function docReaderSearch() {
    const paper = document.getElementById("docReaderPaper");
    const input = document.getElementById("docSearchInput");
    if (!paper || !input) return;
    clearDocHits(paper);
    const q = input.value.trim();
    if (!q) return;
    const walker = document.createTreeWalker(paper, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (node.parentElement && node.parentElement.closest("button,input,script,style,mark")) return NodeFilter.FILTER_REJECT;
        return node.nodeValue.toLowerCase().includes(q.toLowerCase()) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    let count = 0;
    nodes.forEach((node) => {
      const text = node.nodeValue || "";
      const lower = text.toLowerCase(), needle = q.toLowerCase();
      let from = 0, at = lower.indexOf(needle);
      if (at < 0) return;
      const frag = document.createDocumentFragment();
      while (at >= 0) {
        frag.appendChild(document.createTextNode(text.slice(from, at)));
        const mark = document.createElement("mark");
        mark.className = "doc-hit";
        mark.textContent = text.slice(at, at + q.length);
        frag.appendChild(mark);
        count += 1;
        from = at + q.length;
        at = lower.indexOf(needle, from);
      }
      frag.appendChild(document.createTextNode(text.slice(from)));
      node.replaceWith(frag);
    });
    const first = paper.querySelector("mark.doc-hit");
    if (first) first.scrollIntoView({ block: "center" });
    toast(count ? t("doc.hits", { n: count }) : t("search.empty"));
  }

  function printDocReader() {
    const overlay = document.getElementById("docReaderOverlay");
    if (!overlay || overlay.hidden) return;
    document.body.classList.add("printing-doc");
    setTimeout(() => window.print(), 60);
  }

  function statusPill(status) {
    if (status === "validated") return `<span class="badge badge-good">${t("status.machinePassed")}</span>`;
    if (status === "partial") return `<span class="badge badge-warn">${t("status.partialDelivery")}</span>`;
    if (status === "rejected") return `<span class="badge badge-bad">${t("status.rejected")}</span>`;
    return `<span class="badge badge-warn">${esc(status || t("status.draft"))}</span>`;
  }

  function taskResult(doc) {
    if (!doc) return `<div class="empty"><h3>${t("wb.noDocTitle")}</h3><p>${t("wb.noDocText")}</p></div>`;
    const c = doc.content || {};
    const cov = doc.coverage || {};
    const issues = (doc.issues || []).map((x) => `<li>${esc(x)}</li>`).join("");
    const kind = doc.kind;
    let body = "";
    if (kind === "extract_points") {
      body = `<div class="table-wrap"><table class="table"><thead><tr><th>${t("wb.thPoint")}</th><th>${t("wb.thExplanation")}</th><th>${t("wb.thPage")}</th></tr></thead><tbody>
        ${(c.items || []).map((x) => `<tr><td><strong>${esc(x.point)}</strong></td><td>${esc(x.detail || "")}</td><td class="num">${x.page}${x.page_end && x.page_end !== x.page ? `–${x.page_end}` : ""}</td></tr>`).join("")}
      </tbody></table></div>`;
    } else if (kind === "extract_nouns") {
      body = `<div class="table-wrap"><div class="actions mb-8"><button class="btn btn-ghost" type="button" onclick="this.closest('.table-wrap').classList.toggle('recall-mode')">默写模式</button></div><table class="table"><thead><tr><th>${t("wb.thTerm")}</th><th>${t("wb.thDefinition")}</th><th>${t("wb.thConfused")}</th><th>${t("wb.thPage")}</th></tr></thead><tbody>
        ${(c.items || []).map((x) => `<tr><td><strong>${esc(x.term)}</strong></td><td>${esc(x.definition)}</td><td>${esc(x.confused_with || "—")}</td><td class="num">${x.page}${x.page_end && x.page_end !== x.page ? `–${x.page_end}` : ""}</td></tr>`).join("")}
      </tbody></table></div>`;
    } else if (kind === "extract_questions" || kind === "paper") {
      const qs = c.questions || c.items || [];
      const manual = qs.some((q) => q.qtype && q.qtype !== "choice") || (c.answer_audit && c.answer_audit.manual);
      body = `${manual ? `<div class="banner warn"><div><strong>含计算/简答题</strong><div class="small">选择题已做独立答案审计；计算/简答的参考答案需人工核对，不冒充自动判对。</div></div></div>` : ""}
        <div class="list">${qs.map((q, i) => {
          const isChoice = (!q.qtype || q.qtype === "choice") && Array.isArray(q.options) && q.options.length > 0;
          const letters = {0: "A", 1: "B", 2: "C", 3: "D"};
          const answerText = isChoice ? (letters[q.answer] || q.answer_text || "") : (q.answer_text || q.answer || "原卷未给答案");
          const typeLabel = q.qtype === "calculation" ? t("wb.calculation") : q.qtype === "short_answer" ? t("wb.shortAnswer") : (q.qtype === "choice" ? t("wb.choice") : "");
          return `<div class="card flat">
            <div class="card-top"><div><h3 class="card-title">${i + 1}. ${esc(q.stem)}</h3>
              <div class="card-meta">${typeLabel ? `${typeLabel} · ` : ""}${q.source_page ? `${t("wb.sourcePage", { n: q.source_page })}` : ""}${q.source_no ? ` · ${t("wb.sourceNo", { n: esc(q.source_no) })}` : ""}${q.provenance ? ` · ${esc(q.provenance)}` : ""}</div></div>
              ${statusPill(doc.status)}</div>
            ${isChoice ? `<div class="options mt-16">${(q.options || []).map((o, j) => `<div class="option ${j === q.answer ? "correct" : ""}"><span class="letter">${String.fromCharCode(65 + j)}</span><span>${esc(o)}</span></div>`).join("")}</div>` : ""}
            <div class="review-answer"><p><strong>${isChoice ? t("wb.answer") : t("wb.referenceAnswer")}</strong>${esc(answerText)}</p><p>${esc(q.analysis || "")}</p></div>
          </div>`;
        }).join("")}</div>${kind === "extract_questions" && doc.id ? (() => {
          const bankable = (c.items || c.questions || []).filter((q) => (!q.qtype || q.qtype === "choice") && Array.isArray(q.options) && q.options.length >= 2 && Number.isInteger(Number(q.answer))).length;
          return bankable ? `<div class="actions mt-16"><button class="btn btn-primary" onclick="act.importBank('${esc(doc.id)}')">${t("wb.addBank")}</button><span class="small muted">${t("wb.addBankHint")}</span></div>` : `<p class="small muted mt-16">${t("wb.bankNoChoice")}</p>`;
        })() : ""}`;
    } else if (kind === "mindmap") {
      const nodes = c.nodes || [];
      const depth = (n) => {
        let d = 0, cur = n;
        while (cur && cur.parent && d < 8) {
          cur = nodes.find((x) => x.id === cur.parent); d++;
        }
        return d;
      };
      body = `<div class="list">${nodes.map((n) => `<div class="row" style="padding-left:${depth(n) * 18}px">
        <div class="row-main"><div class="row-title">${esc(n.label)}</div><div class="row-sub">第 ${n.page}${n.page_end && n.page_end !== n.page ? `–${n.page_end}` : ""} 页</div></div>
      </div>`).join("")}</div>`;
    } else if (kind === "analysis") {
      body = `<div class="grid grid-2">
        <div class="card"><div class="eyebrow">${t("wb.oneLine")}</div><h3 class="card-title">${esc(c.one_line || "")}</h3></div>
        <div class="card"><div class="eyebrow">${t("wb.concepts")}</div><div class="tags">${(c.concepts || []).map((x) => `<span class="badge badge-neutral">${esc(x)}</span>`).join("")}</div></div>
      </div>
      <div class="card mt-16"><div class="eyebrow">${t("wb.causal")}</div><ol>${(c.causal_chain || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ol></div>
      <div class="grid grid-2 mt-16">
        <div class="card"><div class="eyebrow">${t("wb.examMap")}</div><ul>${(c.exam_map || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
        <div class="card"><div class="eyebrow">${t("wb.confusions")}</div><ul>${(c.confusions || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      </div>
      <div class="card mt-16"><div class="eyebrow">${t("wb.order")}</div><ol>${(c.order || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ol></div>`;
    }
    const taskTools = doc.id ? `<div class="paper-toolbar task-toolbar"><button class="btn btn-ghost" type="button" onclick="act.taskExportHtml()">${t("task.export")}</button><button class="btn btn-ghost" type="button" onclick="act.saveDocumentFile('${esc(doc.id)}','docx')">${t("task.word")}</button><button class="btn btn-ghost" type="button" onclick="act.saveDocumentFile('${esc(doc.id)}','pdf')">${t("task.pdf")}</button><button class="btn btn-ghost" type="button" onclick="act.printDocReader()">${t("task.print")}</button><button class="btn btn-ghost" type="button" onclick="act.taskEdit()">${t("task.edit")}</button></div>` : "";
    return `<div class="card" id="taskResultCard">
      ${taskTools}
      <div class="card-top"><div><div class="eyebrow">${t("wb.resultOf", { task: esc(taskLabel(kind)) })}</div><h3 class="card-title">${esc(doc.title || "")}</h3>
        <div class="card-meta">${t("wb.pageCoverage", { cited: cov.pages_cited ? cov.pages_cited.length : 0, total: cov.pages ? cov.pages.length : 0, pct: Math.round((cov.coverage || 0) * 100) })}</div></div>
        ${statusPill(doc.status)}</div>
      ${issues ? `<div class="banner ${doc.status === "partial" ? "warn" : "bad"} mt-16"><div><strong>${doc.status === "partial" ? t("wb.partialBanner") : t("wb.gateIssues")}</strong><ul class="small">${issues}</ul></div></div>` : `<div class="banner good mt-16"><div><strong>${t("status.machinePassed")}</strong><div class="small">${t("wb.machinePassedNote")}</div></div></div>`}
      <div class="mt-16">${body}</div>
      <div class="small muted mt-16">${t("task.disclaimer")}</div>
    </div>`;
  }

  async function renderWorkbench(seq) {
    const [items, docs, courses] = await Promise.all([
      api("/api/artifacts"), api("/api/documents"), api("/api/courses").catch(() => []),
    ]);
    if (seq !== state.seq) return;
    const prev = state.workbench || {};
    const wbParams = new URLSearchParams(location.hash.split("?")[1] || "");
    const wanted = wbParams.get("artifact") || "";
    const wantedArt = items.find((a) => a.id === wanted);
    let courseKey = wbParams.get("course") || currentCourseKey() || prev.courseKey || "";
    if (wantedArt) courseKey = wantedArt.course_key || courseKey;
    if (courseKey && !courses.some((c) => c.key === courseKey)) courseKey = "";
    const inCourse = items.filter((a) => a.course_key === courseKey);
    const aid = wantedArt && wantedArt.course_key === courseKey ? wanted : "";
    let detail = null;
    if (aid) {
      try { detail = await api(`/api/artifacts/${encodeURIComponent(aid)}`); } catch (e) { detail = null; }
    }
    state.workbench = {
      artifacts: items, docs, courses, artifactId: aid, detail, courseKey,
      sectionId: prev.artifactId === aid ? (prev.sectionId || (detail && detail.section_list[0] ? detail.section_list[0].id : ""))
        : (detail && detail.section_list[0] ? detail.section_list[0].id : ""),
      kind: wbParams.get("kind") || prev.kind || "extract_points", mode: prev.mode || "original",
      count: prev.count || 3, genLang: prev.genLang || "zh", doc: prev.doc || null, loading: false, error: "",
    };
    paintWorkbench();
    const wantedDoc = wbParams.get("doc") || "";
    if (wantedDoc) loadDoc(wantedDoc);
  }

  function paintWorkbench() {
    const w = state.workbench;
    if (!w) return;
    const tabs = TASKS.map((task) => `<button class="tab ${w.kind === task.kind ? "active" : ""}" onclick="act.wbKind('${task.kind}')">${t(task.labelKey)}</button>`).join("");
    const courseOptions = `<option value="">${t("wb.chooseCourse")}</option>` + (w.courses || []).map((c) => `<option value="${esc(c.key)}" ${c.key === w.courseKey ? "selected" : ""}>${esc(c.name)}</option>`).join("");
    const courseArtifacts = (w.artifacts || []).filter((a) => a.course_key === w.courseKey);
    const artOptions = `<option value="" disabled hidden ${w.artifactId ? "" : "selected"}>${t("wb.chooseMaterial")}</option>` + courseArtifacts.map((a) => `<option value="${esc(a.id)}" ${a.id === w.artifactId ? "selected" : ""}>${esc(a.title)} · ${esc(qualityStatusLabel(a.quality))}</option>`).join("");
    const hasArtifact = !!w.artifactId;
    const secOptions = (hasArtifact && w.detail ? (w.detail.section_list || []).map((s) => `<option value="${esc(s.id)}" ${s.id === w.sectionId ? "selected" : ""}>${esc(s.title)}</option>`).join("") : "");
    const sourceMode = w.sourceMode || (hasArtifact && !(w.detail && (w.detail.section_list || []).length) ? "pages" : "section");
    const sectionField = sourceMode === "pages"
      ? `<div class="field"><label>${t("wb.pagesLabel")}</label><input id="wbPages" placeholder="1-20" value="${(() => { try { const sp = JSON.parse(localStorage.getItem("tf-pages-" + (w.courseKey || "") + "-" + (w.artifactId || "")) || "[]"); return sp.length ? esc(sp.join(",")) : ""; } catch (e) { return ""; } })()}"><span class="small muted">${t("wb.pagesInline")}</span></div>`
      : `<div class="field"><label>${t("wb.section")}</label><select id="wbSection" onchange="act.wbSection(this.value)" ${hasArtifact ? "" : "disabled"}>${secOptions || `<option>${hasArtifact ? t("wb.noSections") : t("wb.chooseMaterial")}</option>`}</select></div>`;
    const sourceSwitch = `<div class="wb-source-switch"><span class="small muted">${t("wb.basis")}</span>
      <button class="btn ${sourceMode === "section" ? "btn-primary" : "btn-ghost"}" type="button" onclick="act.wbSourceMode('section')">${t("wb.basisSection")}</button>
      <button class="btn ${sourceMode === "pages" ? "btn-primary" : "btn-ghost"}" type="button" onclick="act.wbSourceMode('pages')">${t("wb.basisPages")}</button></div>`;
    const resourceBar = `<div class="resource-bar">
      <div class="resource-strip">
        <div class="field"><label>${t("wb.course")}</label><select id="wbCourse" onchange="act.wbCourse(this.value)">${courseOptions}</select></div>
        <div class="field"><label>${t("wb.material")}</label><select id="wbArtifact" onchange="act.wbArtifact(this.value)">${artOptions}</select></div>
        ${sectionField}
      </div>
    </div>`;
    const hint = taskHint(w.kind);
    const mode = w.mode || (sourceMode === "pages" && w.kind === "extract_questions" ? "variant" : "original");
    const extra = w.kind === "extract_questions" ? `<div class="field"><label>${t("wb.modeLabel")}</label><select id="wbMode" onchange="act.wbMode(this.value)">
        <option value="original" ${mode === "original" ? "selected" : ""}>${t("wb.modeOriginal2")}</option>
        <option value="variant" ${mode === "variant" ? "selected" : ""}>${t("wb.modeVariant2")}</option>
      </select></div>` : "";
    const count = (w.kind === "extract_questions") ? `<div class="field"><label>${t("wb.count")}</label><input id="wbCount" type="number" min="1" max="5" value="${w.count}" onchange="act.wbCount(this.value)"></div>` : "";
    const visibleDocs = (w.docs || []).filter((d) => d.kind !== "paper" && d.artifact_id === w.artifactId);
    const docs = visibleDocs.slice(0, 8).map((d) => {
      const src = (w.artifacts || []).find((a) => a.id === d.artifact_id) || {};
      const sourceTitle = src.title || (w.detail && w.detail.title) || t("doc.unknownSource");
      return `<div class="row doc-row"><button class="row-main" style="text-align:left" onclick="act.loadDoc('${esc(d.id)}')">
      <div class="row-title">${esc(sourceTitle)} · ${esc(taskLabel(d.kind))}</div><div class="row-sub">${esc(docSectionLabel(d))} · ${esc(docStatusLabel(d.status))} · ${esc(d.created_at)}</div>
    </button><div class="doc-actions"><span class="badge ${d.status === "validated" ? "badge-good" : "badge-bad"}">${d.status === "validated" ? t("status.passedShort") : t("status.notPassedShort")}</span><button class="btn btn-ghost" onclick="act.renameDoc('${esc(d.id)}','${esc(d.title || "")}')">${t("doc.rename")}</button><button class="btn btn-ghost" onclick="act.deleteDoc('${esc(d.id)}')">${t("doc.delete")}</button></div></div>`;
    }).join("");
    view.innerHTML = pageHead("", t("wb.title"), t("wb.lede"), "") +
      `<div class="tabs">${tabs}</div>${sourceSwitch}${resourceBar}
      <div class="card"><div class="small muted mb-8">${esc(sourceMode === "pages" ? (t("wb.pagesHint") || "按资料页取材，不需要先有讲义") : hint)}</div>
        <div class="form-grid">
          ${extra}${count}
          <div class="field"><label>${t("gen.lang")}</label><select id="wbGenLang" onchange="act.wbGenLang(this.value)">
            <option value="zh" ${w.genLang === "zh" ? "selected" : ""}>${t("gen.zh")}</option>
            <option value="hant" ${w.genLang === "hant" ? "selected" : ""}>${t("gen.hant")}</option>
            <option value="en" ${w.genLang === "en" ? "selected" : ""}>${t("gen.en")}</option></select></div>
        </div>
        <div class="actions"><button class="btn btn-primary" id="wbRun" onclick="act.runTask()" ${(w.loading || !w.artifactId || (sourceMode === "section" && !w.sectionId)) ? "disabled" : ""}>${w.loading ? t("wb.running") : t("wb.run")}</button>
          ${w.loading && w.jobId ? `<button class="btn btn-ghost" onclick="act.cancelTask()">${t("new.cancel")}</button>` : ""}
          </div>
      </div>
      ${w.error ? errorBox(w.error) : ""}
      <div class="mt-16" id="wbResult">${w.loading ? loading(t("wb.generating")) : ""}</div>
      <p class="small muted mt-8">${t("wb.historyHint")}</p>`;
    math(view);
  }

  async function wbCourse(key) {
    const w = state.workbench;
    if (!w) return;
    w.courseKey = key || "";
    w.artifactId = "";
    w.detail = null;
    w.sectionId = "";
    paintWorkbench();
  }

  function parsePageSpec(raw) {
    const text = String(raw || "").replace(/[，、\s]+/g, ",").trim();
    if (!text) return [];
    const out = [];
    for (const part of text.split(",")) {
      if (!part) continue;
      const m = part.match(/^(\d+)\s*[-~—]\s*(\d+)$/);
      if (m) {
        const a = Number(m[1]), b = Number(m[2]);
        if (a > b) return null;
        for (let i = a; i <= b; i += 1) out.push(i);
      } else if (/^\d+$/.test(part)) {
        out.push(Number(part));
      } else {
        return null;
      }
    }
    return [...new Set(out)].sort((a, b) => a - b);
  }

  async function wbArtifact(aid) {
    const w = state.workbench;
    if (!w) return;
    w.artifactId = aid;
    if (w.sourceMode === undefined) w.sourceMode = "section";
    try { w.detail = await api(`/api/artifacts/${encodeURIComponent(aid)}`); } catch (e) { w.detail = null; }
    w.sectionId = w.detail && w.detail.section_list[0] ? w.detail.section_list[0].id : "";
    paintWorkbench();
  }

  function wbSourceMode(mode) {
    const w = state.workbench;
    if (!w) return;
    w.sourceMode = mode === "pages" ? "pages" : "section";
    if (w.kind === "extract_questions") w.mode = w.sourceMode === "pages" ? "variant" : "original";
    paintWorkbench();
  }

  function wbKind(kind) { state.workbench.kind = kind; paintWorkbench(); }
  function wbSection(sid) { state.workbench.sectionId = sid; }
  function wbMode(mode) { state.workbench.mode = mode; }
  function wbCount(n) { state.workbench.count = Math.max(1, Math.min(5, Number(n) || 3)); }
  function wbGenLang(lang) { state.workbench.genLang = ["zh", "hant", "en"].includes(lang) ? lang : "zh"; }

  async function runTask() {
    const w = state.workbench;
    if (!w || w.loading) return;
    if ((w.sourceMode || "section") === "pages") { return runUnitsTask(); }
    if (!w.artifactId || !w.sectionId) { toast(t("wb.selectFirst")); return; }
    w.loading = true; w.error = ""; w.doc = null; w.jobId = null; paintWorkbench();
    try {
      const res = await api("/api/tasks/jobs", { method: "POST", body: {
        kind: w.kind, artifact_id: w.artifactId, section: w.sectionId, mode: w.mode, count: w.count,
        gen_lang: w.genLang || "zh",
      }});
      w.jobId = res.job_id; paintWorkbench();
      lockGenerationJob(res.job_id, t("wb.generating"));
      pollTaskJob(res.job_id);
    } catch (e) {
      w.loading = false; w.jobId = null; w.error = e.message || t("wb.taskFailed"); paintWorkbench();
    }
  }

  async function runUnitsTask() {
    const w = state.workbench;
    if (!w || w.loading) return;
    if (!w.artifactId) { toast(t("wb.selectFirst")); return; }
    const raw = (document.getElementById("wbPages") || {}).value || "";
    const pages = parsePageSpec(raw);
    if (!pages) { toast(t("wb.pagesEmpty")); return; }
    if (!pages.length) { toast(t("wb.pagesEmpty")); return; }
    if (pages.length > 200) { toast(t("wb.pagesEmpty")); return; }
    if (w.kind === "analysis") { toast(t("wb.sourcePages")); return; }
    w.loading = true; w.error = ""; w.doc = null; paintWorkbench();
    lockGenerationJob("units", t("wb.unitRunning"));
    showGenerationRing(30, null, t("wb.unitRunning"));
    try {
      const doc = await api("/api/tasks/units", { method: "POST", body: {
        kind: w.kind, artifact_id: w.artifactId, pages, gen_lang: w.genLang || "zh",
        mode: w.mode || (w.kind === "extract_questions" ? "variant" : "original"),
      }});
      hideGenerationRing();
      unlockGenerationJob();
      w.loading = false;
      w.docs = await api("/api/documents").catch(() => w.docs);
      w.doc = doc;
      paintWorkbench();
      openDocReader(doc);
      const skipped = (doc.content && doc.content.skipped_pages) || [];
      if (skipped.length) toast(t("wb.unitSkipped", { pages: skipped.join(",") }), 6000);
      else toast(doc.status === "validated" ? t("wb.passToast") : t("wb.failToast"));
    } catch (e) {
      hideGenerationRing();
      unlockGenerationJob();
      w.loading = false;
      w.error = e.message || t("wb.taskFailed");
      paintWorkbench();
    }
  }

  async function pollTaskJob(jobId) {
    const w = state.workbench;
    try {
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (job.status === "done") {
        hideGenerationRing();
        unlockGenerationJob();
        const doc = jobResult(job);
        w.doc = doc; w.loading = false; w.jobId = null;
        try { w.docs = await api("/api/documents"); } catch (e) {}
        paintWorkbench();
        openDocReader(doc);
        toast(doc.status === "validated" ? t("wb.passToast") : (doc.status === "partial" ? t("wb.partialToast") : t("wb.failToast")));
        return;
      }
      if (job.status === "failed") { hideGenerationRing(); unlockGenerationJob(); throw new Error(job.error || t("wb.taskFailed")); }
      if (job.status === "cancelled") {
        hideGenerationRing();
        unlockGenerationJob();
        w.loading = false; w.jobId = null; w.error = t("new.cancelled"); paintWorkbench(); return;
      }
      const box = document.getElementById("wbResult");
      if (box) {
        const elapsed = Number(job.elapsed_s) || 0;
        const pct = Number(job.progress) || 0;
        const eta = estimateJobEta(job, "workbench");
        showGenerationRing(pct, eta, job.step || t("wb.generating"));
        box.innerHTML = loading(`${job.step || t("wb.generating")} ${pct}%` + (elapsed ? ` · ${t("new.elapsedOnly", { elapsed: formatDuration(elapsed) })}` : "") + (eta ? ` · ${t("new.eta", { eta: formatDuration(eta) })}` : ""));
      }
      setTimeout(() => pollTaskJob(jobId), 1400);
    } catch (e) {
      w.loading = false; w.jobId = null; w.error = e.message || t("wb.taskFailed"); paintWorkbench();
    }
  }

  async function cancelTask() {
    const w = state.workbench;
    if (!w || !w.jobId) return;
    try { await api(`/api/jobs/${encodeURIComponent(w.jobId)}/cancel`, { method: "POST", body: {} }); }
    catch (e) { toast(e.message || t("new.cancelFailed")); }
  }

  function taskExportHtml() {
    const card = document.getElementById("taskResultCard");
    if (!card) return;
    const doc = state.workbench && state.workbench.doc;
    const back = doc && doc.id ? `${location.origin}/#/workbench?doc=${encodeURIComponent(doc.id)}` : `${location.origin}/#/workbench`;
    const backBar = `<div class="export-back"><img src="${location.origin}/static/logo-mark.svg" alt=""><b>TermFinale</b><a href="${back}" target="_top">← 返回上一级</a></div>`;
    const html = `<html><head><meta charset="utf-8"><style>body{font-family:SimSun;line-height:1.8}.paper-toolbar,.task-toolbar{display:none!important}.export-back{position:fixed;left:16px;top:12px;display:flex;align-items:center;gap:8px}.export-back img{width:25px;height:25px;object-fit:contain}.export-back b{font:600 12px -apple-system,sans-serif}.export-back a{display:inline-block;padding:7px 11px;border:1px solid #bbb;border-radius:5px;background:#fff;color:#245c73;text-decoration:none;font:12px -apple-system,sans-serif}</style></head><body>${backBar}${card.innerHTML}</body></html>`;
    saveDocumentFile(doc && doc.id || "", "html", html);
  }
  function taskEdit() {
    const card = document.getElementById("taskResultCard");
    if (card) card.contentEditable = card.contentEditable === "true" ? "false" : "true";
  }

  async function cleanPapers(key) {
    if (!confirm(t("course.cleanPapersConfirm"))) return;
    const course = state.course;
    if (!course) return;
    const ids = new Set(course.artifact_ids || []);
    const docs = (await api("/api/documents").catch(() => [])).filter((d) => d.kind === "exam" && ids.has(d.artifact_id));
    const seen = new Set();
    const duplicates = docs.filter((d) => {
      const k = String(d.title || "").trim();
      if (seen.has(k)) return true;
      seen.add(k); return false;
    });
    for (const d of duplicates) {
      await api(`/api/documents/${encodeURIComponent(d.id)}`, { method: "DELETE" }).catch(() => null);
    }
    toast(t("course.cleanPapersDone", { n: duplicates.length }));
    await route();
  }

  async function renameDoc(did, current) {
    const title = prompt(t("doc.renamePrompt"), current || "");
    if (!title || !title.trim()) return;
    try {
      await api(`/api/documents/${encodeURIComponent(did)}`, { method: "PATCH", body: { title: title.trim() } });
      toast(t("doc.renamed"));
      await route();
    } catch (e) { toast(e.message || t("doc.renameFailed")); }
  }

  async function deleteBankQuestion(qid, aid) {
    if (!confirm(t("bank.deleteConfirm"))) return;
    try {
      await api(`/api/bank/${encodeURIComponent(qid)}`, { method: "DELETE" });
      await route();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }

  async function deleteDoc(did) {
    if (!confirm(t("doc.deleteConfirm"))) return;
    try {
      await api(`/api/documents/${encodeURIComponent(did)}`, { method: "DELETE" });
      toast(t("doc.deleted"));
      await route();
    } catch (e) { toast(e.message || t("doc.deleteFailed")); }
  }

  async function loadDoc(did) {
    const w = state.workbench;
    if (!w) return;
    try {
      const doc = await api(`/api/documents/${encodeURIComponent(did)}`);
      w.doc = doc; w.error = ""; paintWorkbench(); openDocReader(doc);
    } catch (e) { toast(e.message || t("wb.readFailed")); }
  }

  function renderNew() {
    const newQuery = new URLSearchParams((location.hash.split("?")[1] || ""));
    const prefillCourse = newQuery.get("course") || "";
    view.innerHTML = pageHead(t("new.eyebrow"), t("course.newCourse"), t("new.courseLede"),
      `<a class="btn btn-ghost" href="#" onclick="act.back('#/library', event)">${t("new.back")}</a>`) +
      `<form class="card" id="newForm">
        <div class="form-grid">
          <div class="field wide"><label>${t("new.file")}</label><label class="edit-file-picker" for="newFiles"><span class="edit-file-button">${t("course.editChooseFiles")}</span><span class="edit-file-names" id="newFileNames">${t("course.editNoFiles")}</span></label><input id="newFiles" type="file" name="file" accept=".pdf,.ppt,.pptx,.doc,.docx,.png,.jpg,.jpeg,.webp" multiple hidden><div class="small muted mt-8">${t("new.fileHint")}</div><div class="file-selection" id="fileSelection" hidden></div></div>
          
          <div class="field"><label>${t("new.course")}</label><input name="course" value="${esc(prefillCourse)}" placeholder="${esc(t("new.coursePlaceholder"))}"></div>
          <div class="field"><label>${t("new.credits")}</label><input type="number" name="credits" value="3" min="0.5" max="10" step="0.5"></div>
          <div class="field"><label>${t("new.courseType")}</label><select name="course_type">
            <option value="专业课">${t("new.ctMajor")}</option><option value="专业基础课">${t("new.ctBasic")}</option>
            <option value="公共基础课">${t("new.ctPublic")}</option><option value="选修课">${t("new.ctElective")}</option></select></div>
          
          <div class="field"><label>${t("new.difficulty")}</label><select name="difficulty">
            <option value="1">1 · ${t("new.diffEasy")}</option><option value="2">2</option><option value="3" selected>3 · ${t("new.diffNormal")}</option>
            <option value="4">4</option><option value="5">5 · ${t("new.diffHard")}</option></select></div>
          <div class="field"><label>${t("new.mastery")}</label><select name="mastery">
            <option value="1">${t("new.mastery1")}</option><option value="2">${t("new.mastery2")}</option>
            <option value="3" selected>${t("new.mastery3")}</option><option value="4">${t("new.mastery4")}</option>
            <option value="5">${t("new.mastery5")}</option></select><div class="small muted mt-8">${t("new.masteryHint")}</div></div>
          <div class="field"><label>${t("new.examDate")}</label><input type="date" name="exam_date"><div class="small muted mt-8">${t("new.examDateHint")}</div></div>
          
          
          
        </div>
        <div class="field wide"><label>AI 总偏好</label><textarea name="ai_preference" rows="2" placeholder="这门课希望 AI 一直记住的偏好，会应用到所有模块；可留空"></textarea></div>
        <div class="actions"><button class="btn btn-primary" type="button" id="newSaveSources">${t("new.saveSources")}</button>
        <span class="small muted">${t("new.saveSourcesHint")}</span></div>
        <p class="small muted mt-8">${t("new.saveLimitsHint")}</p>
        <label class="check mt-8"><input type="checkbox" id="newFastSave" checked> ${t("new.fastSave")}</label>
        <p class="small muted mt-4">${t("new.fastSaveHint")}</p>
      </form>
      <div class="card mt-16" id="jobCard" hidden>
        <div class="eyebrow">${t("new.jobEyebrow")}</div>
        <h2 id="jobStep">${t("new.queued")}</h2>
        <div class="q-bar"><i id="jobBar" style="width:0%"></i></div>
        <div class="small muted mt-8" id="jobMsg"></div>
        <div class="job-eta" id="jobEta" hidden></div>
        <div class="actions"><button class="btn btn-ghost" id="jobCancel">${t("new.cancel")}</button></div>
      </div>`;
    let pendingFiles = [];
    const fileInput = document.getElementById("newFiles");
    const fileSelection = document.getElementById("fileSelection");

    function chapterRank(name) {
      const m = String(name || "").match(/(?:第\s*([0-9一二三四五六七八九十百]+)\s*[章节]|chapter\s*([0-9]+))/i);
      if (!m) return 9999;
      const raw = m[1] || m[2];
      if (/^[0-9]+$/.test(raw)) return parseInt(raw, 10);
      const digits = { "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9 };
      if (raw === "十") return 10;
      if (/^[一二三四五六七八九]?十[一二三四五六七八九]?$/.test(raw)) {
        const [before, after] = raw.split("十");
        return (digits[before] || 1) * 10 + (digits[after] || 0);
      }
      return digits[raw] || 9999;
    }

    function sortPending(files) {
      return files.map((file, index) => ({ file, index, rank: chapterRank(file.name) })).sort((a, b) => {
        if (a.rank !== b.rank) return a.rank - b.rank;
        if (a.rank === 9999) return a.index - b.index;
        return a.file.name.localeCompare(b.file.name, undefined, { numeric: true });
      });
    }

    let pendingSelected = new Set();

    function renderFileSelection() {
      if (!fileSelection) return;
      if (!pendingFiles.length) { fileSelection.hidden = true; fileSelection.innerHTML = ""; return; }
      fileSelection.hidden = false;
      const rows = pendingFiles.map((file, i) => {
        const kb = Math.max(1, Math.round(file.size / 1024));
        const checked = pendingSelected.has(file) ? " checked" : "";
        return `<div class="file-choice"><label class="file-choice-main"><input type="checkbox" data-file-choice="${i}"${checked}><b>${String(i + 1).padStart(2, "0")}</b><span class="file-choice-name">${esc(file.name)}</span><span class="file-choice-size">${kb} KB</span></label><span class="file-order-controls"><button type="button" data-move="${i}" data-dir="-1" title="${t("new.moveUp")}" ${i === 0 ? "disabled" : ""}>↑</button><button type="button" data-move="${i}" data-dir="1" title="${t("new.moveDown")}" ${i === pendingFiles.length - 1 ? "disabled" : ""}>↓</button></span></div>`;
      }).join("");
      fileSelection.innerHTML = `<div class="file-selection-head"><strong>${t("new.fileSelectTitle", { n: pendingFiles.length })}</strong><label class="check"><input type="checkbox" id="fileSelectAll"> ${t("new.selectAll")}</label><span class="small muted">${t("new.fileOrderHint")}</span></div>${rows}<div class="file-selection-foot"><span class="small muted">${t("new.fileSelectHint")}</span><span class="small muted" id="fileSelectedCount"></span></div>`;
      const update = () => {
        const chosen = Array.from(fileSelection.querySelectorAll("[data-file-choice]"));
        pendingSelected = new Set(chosen.filter((x) => x.checked).map((x) => pendingFiles[Number(x.dataset.fileChoice)]).filter(Boolean));
        const n = chosen.filter((x) => x.checked).length;
        const count = document.getElementById("fileSelectedCount");
        if (count) count.textContent = t("new.selectedCount", { n });
        const all = document.getElementById("fileSelectAll");
        if (all) all.checked = n === chosen.length && n > 0;
      };
      fileSelection.querySelectorAll("[data-file-choice]").forEach((x) => x.addEventListener("change", update));
      const all = document.getElementById("fileSelectAll");
      if (all) all.addEventListener("change", () => {
        fileSelection.querySelectorAll("[data-file-choice]").forEach((x) => { x.checked = all.checked; });
        update();
      });
      fileSelection.querySelectorAll("[data-move]").forEach((btn) => btn.addEventListener("click", (e) => {
        e.preventDefault(); e.stopPropagation();
        const from = Number(btn.dataset.move), dir = Number(btn.dataset.dir), to = from + dir;
        if (to < 0 || to >= pendingFiles.length) return;
        const selectedFiles = new Set(pendingSelected);
        [pendingFiles[from], pendingFiles[to]] = [pendingFiles[to], pendingFiles[from]];
        pendingSelected = new Set(pendingFiles.filter((f) => selectedFiles.has(f)));
        renderFileSelection();
      }));
      update();
    }

    if (fileInput) fileInput.addEventListener("change", () => {
      const picked = Array.from(fileInput.files || []).filter((f) => f && f.name);
      const key = (f) => `${f.name}|${f.size}|${f.lastModified || 0}`;
      const oldSelected = new Set((pendingFiles || []).filter((f) => pendingSelected.has(f)).map(key));
      const merged = [...(pendingFiles || []), ...picked];
      const seen = new Set();
      const unique = merged.filter((f) => {
        const k = key(f);
        if (seen.has(k)) return false;
        seen.add(k); return true;
      });
      if (unique.length > 20) toast(t("new.maxFiles"));
      pendingFiles = sortPending(unique.slice(0, 20)).map((x) => x.file);
      const newKeys = new Set(picked.map(key));
      pendingSelected = new Set(pendingFiles.filter((f) => oldSelected.has(key(f)) || newKeys.has(key(f))));
      const names = document.getElementById("newFileNames");
      if (names) names.textContent = pendingFiles.length ? pendingFiles.map((f) => f.name).join("、") : t("course.editNoFiles");
      renderFileSelection();
      // Allow choosing the same file again later after removing it.
      fileInput.value = "";
    });

    const chosenFiles = () => Array.from(fileSelection ? fileSelection.querySelectorAll("[data-file-choice]") : [])
      .filter((x) => x.checked)
      .map((x) => pendingFiles[Number(x.dataset.fileChoice)])
      .filter(Boolean);
    let savePollTimer = null;
    let saveJobId = "";

    function saveJobHint(step, pct, sec) {
      const btn = document.getElementById("newSaveSources");
      if (!btn) return;
      btn.textContent = `${step || t("new.savingSources")} ${pct ? Math.round(pct) + "%" : ""} · ${formatDuration(sec)}`.trim();
    }

    async function pollSaveJob(jobId, opts = {}) {
      const started = opts.started || Date.now();
      saveJobId = jobId;
      while (saveJobId === jobId) {
        let job = null;
        try { job = await api(`/api/jobs/${encodeURIComponent(jobId)}`); } catch (e) { job = null; }
        const sec = Math.floor((Date.now() - started) / 1000);
        if (job) {
          saveJobHint(job.step || "", job.progress || 0, sec);
          if (job.status === "done") {
            saveJobId = "";
            try { localStorage.removeItem("tf-save-job"); } catch (e) {}
            const r = job.result || {};
            const courseKey = r.course_key || "";
            toast(t("new.saveJobDonePages", { pages: Number(r.pages || 0) }));
            if (courseKey && location.hash.startsWith("#/new")) {
              location.hash = `#/course/${encodeURIComponent(courseKey)}/lectures`;
            }
            return;
          }
          if (job.status === "failed" || job.status === "cancelled") {
            saveJobId = "";
            try { localStorage.removeItem("tf-save-job"); } catch (e) {}
            toast(job.error || t("new.saveSourcesFailed"));
            return;
          }
        }
        await new Promise((r) => setTimeout(r, 1200));
      }
    }

    function resumeSaveJob() {
      let saved = null;
      try { saved = JSON.parse(localStorage.getItem("tf-save-job") || "null"); } catch (e) {}
      if (!saved || !saved.id || Date.now() - Number(saved.at || 0) > 30 * 60 * 1000) return;
      toast(t("new.saveJobResume"));
      pollSaveJob(saved.id, { started: Number(saved.at) || Date.now() });
    }

    const saveSources = async (event) => {
      if (event) event.preventDefault();
      if (saveJobId) return;
      const chosen = chosenFiles();
      if (!chosen.length) { toast(t("new.noFiles")); return; }
      const form = document.getElementById("newForm");
      const btn = document.getElementById("newSaveSources");
      const submit = document.getElementById("newSubmit");
      if (btn) { btn.disabled = true; btn.textContent = `${t("new.savingSources")} · 上传中`; }
      if (submit) submit.disabled = true;
      const started = Date.now();
      try {
        const out = new FormData(form);
        out.delete("file");
        out.delete("files");
        const mastery = Math.max(1, Math.min(5, Number(out.get("mastery") || 3)));
        const examDate = String(out.get("exam_date") || "").slice(0, 10);
        const daysLeft = examDate
          ? Math.max(1, Math.min(30, Math.ceil((new Date(examDate + "T23:59:59") - new Date()) / 86400000)))
          : 7;
        out.set("target_score", String(mastery >= 4 ? 90 : mastery <= 2 ? 75 : 80));
        out.set("days_left", String(daysLeft));
        out.set("foundation", mastery <= 2 ? "基础较弱" : mastery === 3 ? "一般" : "基础较好");
        out.set("mastery", String(mastery));
        out.set("exam_date", examDate);
        const fastBox = document.getElementById("newFastSave");
        out.set("fast_save", fastBox && fastBox.checked ? "true" : "false");
        chosen.forEach((f) => out.append("files", f));
        const res = await fetch("/api/courses/save-sources/jobs", { method: "POST", body: out });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || t("new.saveSourcesFailed"));
        try { localStorage.setItem("tf-save-job", JSON.stringify({ id: data.job_id, at: Date.now() })); } catch (e) {}
        await pollSaveJob(data.job_id, { started });
      } catch (e) {
        toast(requestErrorMessage(e, t("new.saveSourcesFailed")));
      } finally {
        if (btn) { btn.disabled = false; btn.textContent = t("new.saveSources"); }
        if (submit) submit.disabled = false;
      }
    };

    const saveBtn = document.getElementById("newSaveSources");
    if (saveBtn) saveBtn.addEventListener("click", saveSources);

    const newForm = document.getElementById("newForm");
    if (newForm) newForm.addEventListener("submit", (e) => { e.preventDefault(); saveSources(e); });
    resumeSaveJob();
  }

  let pollTimer = null;
  let currentJob = "";
  let activeGenerationJob = null;
  let pendingCourseMeta = null;

  function localizeJobStep(step) {
    const raw = String(step || "");
    if (state.lang !== "en" || !raw) return raw;
    const exact = {
      "读取资料 / 建立页账本": t("jobstep.ledger"),
      "装配讲义 / 跑 Gate / 生成 PDF": t("jobstep.assemble"),
      "完成：Gate 通过，等待逐页复核": t("jobstep.done"),
      "完成": t("jobstep.doneShort"),
      "已取消": t("jobstep.cancelled"),
      "失败": t("jobstep.failed"),
    };
    if (exact[raw]) return exact[raw];
    const m = raw.match(/^生成第 (\d+)\/(\d+) 段：(.*)$/);
    if (m) return t("jobstep.segment", { i: m[1], n: m[2], label: m[3] });
    return raw;
  }

  function setGenDisabled(value) {
    ["newSubmit"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.disabled = value;
    });
  }

  let jobEtaState = null;

  function formatDuration(seconds) {
    const s = Math.max(0, Math.round(Number(seconds) || 0));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return m ? `${m}分${String(r).padStart(2, "0")}秒` : `${r}秒`;
  }

  const genEtaStates = new Map();
  const RING_CIRC = 2 * Math.PI * 52;

  function estimateJobEta(job, key) {
    // 不再用进度反推剩余时间：进度非线性时会从 5 秒涨到几分钟。
    // 只显示已用时间，避免“预计时间无限增长”。
    return null;
  }

  function showGenerationRing(pct, eta, label = "") {
    const ring = document.getElementById("genRing");
    const arc = document.getElementById("genRingArc");
    const pctEl = document.getElementById("genRingPct");
    const etaEl = document.getElementById("genRingEta");
    const labEl = document.getElementById("genRingLabel");
    if (!ring || !arc) return;
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    ring.hidden = false;
    arc.style.strokeDasharray = String(RING_CIRC);
    arc.style.strokeDashoffset = String(RING_CIRC * (1 - p / 100));
    if (pctEl) pctEl.textContent = `${Math.round(p)}%`;
    if (etaEl) etaEl.textContent = eta == null ? t("ring.estimating") : t("ring.eta", { eta: formatDuration(eta) });
    if (labEl) labEl.textContent = String(label || t("ring.generating")).slice(0, 42);
  }

  function lockGenerationJob(jobId, label) {
    activeGenerationJob = { id: String(jobId || ""), route: location.hash || "#/" };
    document.body.classList.add("generation-locked");
    showGenerationRing(0, null, label || t("gen.locked"));
  }

  function unlockGenerationJob() {
    activeGenerationJob = null;
    document.body.classList.remove("generation-locked");
    hideGenerationRing();
  }

  function hideGenerationRing() {
    const ring = document.getElementById("genRing");
    if (ring) ring.hidden = true;
  }

  function updateJobEta(job) {
    const el = document.getElementById("jobEta");
    if (!el) return;
    if (!jobEtaState) jobEtaState = { startedAt: Date.now() };
    const elapsed = Number(job.elapsed_s) || Math.round((Date.now() - jobEtaState.startedAt) / 1000);
    const step = String(job.step || "");
    const m = step.match(/(\d+)\s*\/\s*(\d+)\s*段/);
    const progress = Number(job.progress) || 0;
    const eta = null;
    showGenerationRing(progress, eta, step || t("ring.generating"));
    if (job.status === "done") {
      el.hidden = true;
      hideGenerationRing();
      return;
    }
    el.hidden = false;
    el.textContent = eta == null
      ? t("new.elapsedOnly", { elapsed: formatDuration(elapsed) })
      : t("new.elapsedEta", { elapsed: formatDuration(elapsed), eta: "" });
    el.dataset.eta = eta == null ? "" : String(eta);
  }

  async function persistPendingCourse(artifact) {
    const meta = pendingCourseMeta;
    pendingCourseMeta = null;
    if (!meta || !artifact || !artifact.course_key) return;
    try {
      let current = {};
      try { current = await api(`/api/courses/${encodeURIComponent(artifact.course_key)}`); } catch (e) {}
      await api(`/api/course-prefs/${encodeURIComponent(artifact.course_key)}`, {
        method: "PUT", body: {
          target_score: Number(meta.target || current.target_score || 0),
          exam_date: current.exam_date || "",
          display_name: meta.course || current.name || artifact.course || "",
          credits: Number(meta.credits || current.credits || 0),
          course_type: meta.courseType || current.course_type || "",
          school_level: meta.schoolLevel || current.school_level || "",
          difficulty: Number(meta.difficulty || current.difficulty || 3),
        },
      });
    } catch (e) { /* 生成成功但元数据保存失败时，不把整次任务判失败 */ }
  }

  async function startGeneration(fd, endpoint = "/api/generate") {
    pendingCourseMeta = {
      course: String(fd.get("course") || ""), credits: String(fd.get("credits") || ""),
      courseType: String(fd.get("course_type") || ""), schoolLevel: String((state.settings && state.settings.school_tier) || ""),
      difficulty: String(fd.get("difficulty") || "3"), target: String(fd.get("target_score") || "80"),
    };
    const difficulty = Number(pendingCourseMeta.difficulty || 3);
    const custom = String(fd.get("custom_prompt") || "").trim();
    fd.set("school_level", String((state.settings && state.settings.school_tier) || ""));
    fd.set("custom_prompt", `${custom}${custom ? "\n" : ""}课程信息：${pendingCourseMeta.credits || "未填"} 学分，${pendingCourseMeta.courseType || "未填"}，学校层次 ${pendingCourseMeta.schoolLevel || "未填"}，自设难度 ${difficulty}/5。请按这个难度调整讲解深度、例题难度和推导详略；资料权重仍决定篇幅分配。`);
    const card = document.getElementById("jobCard");
    if (!card) return;
    card.hidden = false;
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    document.getElementById("jobStep").textContent = t("new.uploading");
    document.getElementById("jobBar").style.width = "2%";
    document.getElementById("jobMsg").textContent = "";
    showGenerationRing(2, null, t("new.uploading"));
    jobEtaState = null;
    const etaEl = document.getElementById("jobEta");
    if (etaEl) { etaEl.hidden = true; etaEl.textContent = ""; }
    setGenDisabled(true);
    try {
      const res = await fetch(endpoint, { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || t("new.uploadFailed", { status: res.status }));
      currentJob = data.job_id;
      lockGenerationJob(currentJob, t("new.jobEyebrow"));
      const cancel = document.getElementById("jobCancel");
      if (cancel) { cancel.hidden = false; cancel.onclick = () => act.cancelGeneration(currentJob); }
      pollJob(currentJob);
    } catch (e) {
      const step = document.getElementById("jobStep");
      const msg = document.getElementById("jobMsg");
      if (step) step.textContent = t("new.genFailed");
      if (msg) msg.innerHTML = `<span class="badge badge-bad">${esc(requestErrorMessage(e, t("new.genFailed")))}</span>`;
      hideGenerationRing();
      unlockGenerationJob();
      setGenDisabled(false);
      const cancel = document.getElementById("jobCancel");
      if (cancel) cancel.hidden = true;
    }
  }

  async function pollJob(jobId) {
    clearTimeout(pollTimer);
    const stepEl = document.getElementById("jobStep");
    if (!stepEl) return;
    try {
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      if (!document.getElementById("jobStep")) return;
      document.getElementById("jobStep").textContent = localizeJobStep(job.step || job.status);
      document.getElementById("jobBar").style.width = `${job.progress || 0}%`;
      document.getElementById("jobMsg").textContent = job.status === "failed" ? (job.error || "") : "";
      updateJobEta(job);
      if (job.status === "done") {
        hideGenerationRing();
        unlockGenerationJob();
        setGenDisabled(false);
        const a = job.result && job.result.artifact ? job.result.artifact : null;
        const aid = a ? a.id : (job.result && job.result.id) || "";
        await persistPendingCourse(a);
        document.getElementById("jobStep").textContent = t("new.jobDone");
        document.getElementById("jobMsg").innerHTML = `${aid ? `<a class="btn btn-primary" href="#/artifact/${encodeURIComponent(aid)}">${t("card.quality")}</a> <a class="btn btn-ghost" href="#/read/${encodeURIComponent(aid)}">${t("card.read")}</a>` : t("new.complete")} <span class="small muted">${t("new.jobDoneNote")}</span>`;
        return;
      }
      if (job.status === "failed") {
        hideGenerationRing();
        unlockGenerationJob();
        setGenDisabled(false);
        currentJob = "";
        const cancelFail = document.getElementById("jobCancel");
        if (cancelFail) cancelFail.hidden = true;
        const etaFail = document.getElementById("jobEta");
        if (etaFail) etaFail.hidden = true;
        document.getElementById("jobStep").textContent = t("new.genFailed");
        const resumeBtn = job.resumable
          ? `<button class="btn btn-primary mt-8" onclick="act.resumeJob('${esc(jobId)}','${esc(job.kind || "lecture")}')">${t("job.resume")}</button>`
          : "";
        document.getElementById("jobMsg").innerHTML =
          `<span class="badge badge-bad">${esc(job.error || t("new.unknownError"))}</span>` +
          `<div class="small muted mt-8">${t("job.failedNext")}</div>${resumeBtn}`;
        return;
      }
      if (job.status === "cancelled") {
        hideGenerationRing();
        unlockGenerationJob();
        setGenDisabled(false);
        currentJob = "";
        const cancelCancel = document.getElementById("jobCancel");
        if (cancelCancel) cancelCancel.hidden = true;
        document.getElementById("jobStep").textContent = t("new.cancelled");
        return;
      }
      pollTimer = setTimeout(() => pollJob(jobId), 1600);
    } catch (e) {
      const msg = document.getElementById("jobMsg");
      if (msg) msg.textContent = e.message || t("new.jobReadFailed");
      pollTimer = setTimeout(() => pollJob(jobId), 2500);
    }
  }

  async function cancelGeneration(jobId) {
    try { await api(`/api/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST" }); toast(t("new.cancelRequested")); }
    catch (e) { toast(e.message || t("new.cancelFailed")); }
  }

  async function renderNotes(seq) {
    const [notes, items, courses] = await Promise.all([
      api("/api/notes"), api("/api/artifacts"), api("/api/courses").catch(() => []),
    ]);
    if (seq !== state.seq) return;
    const titles = Object.fromEntries(items.map((a) => [a.id, a.title]));
    const nParams = new URLSearchParams(location.hash.split("?")[1] || "");
    const ck = nParams.get("course") === "all" ? "" : (nParams.get("course") || currentCourseKey());
    const byId = Object.fromEntries(items.map((a) => [a.id, a]));
    const visibleNotes = ck ? notes.filter((n) => (byId[n.artifact_id] || {}).course_key === ck) : notes;
    const courseOptions = `<option value="all" ${ck ? "" : "selected"}>${t("review.allCourses")}</option>` + (courses || []).map((c) => `<option value="${esc(c.key)}" ${c.key === ck ? "selected" : ""}>${esc(c.name)}</option>`).join("");
    const rows = visibleNotes.map((n) => `<div class="row">
      <div class="row-main"><div class="row-title">${esc(n.text).slice(0, 280)}</div>
        <div class="row-sub">${esc(titles[n.artifact_id] || n.artifact_id)}${n.section ? ` · ${esc(n.section)}` : ""}${n.page ? ` · ${t("notes.page", { n: n.page })}` : ""} · ${esc(n.created_at)}</div></div>
      <div class="row-actions"><a class="btn btn-ghost" href="#/artifact/${encodeURIComponent(n.artifact_id)}">${t("notes.viewLecture")}</a>
        <button class="btn btn-ghost" onclick="act.deleteNote(${n.id})">${t("notes.delete")}</button></div>
    </div>`).join("");
    view.innerHTML = pageHead(t("notes.eyebrow"), t("notes.title"), t("notes.lede"), `<a class="btn btn-ghost" href="#" onclick="act.back('#/library', event)">${t("notes.goRead")}</a>`) +
      `<div class="resource-strip"><div class="field"><label>${t("wb.course")}</label><select onchange="location.hash='#/notes'+(this.value==='all'?'?course=all':'?course='+encodeURIComponent(this.value))">${courseOptions}</select></div></div>
       <div class="stat-row"><div class="stat"><strong>${visibleNotes.length}</strong><span>${t("notes.count")}</span></div>
        <div class="stat"><strong>${new Set(visibleNotes.map((n) => n.artifact_id)).size}</strong><span>${t("notes.artifacts")}</span></div></div>` +
      (rows ? `<div class="list mt-16">${rows}</div>` : `<div class="mt-16">${empty(t("notes.emptyTitle"), t("notes.emptyText"), `<a class="btn btn-primary" href="#/library">${t("notes.goLibrary")}</a>`)}</div>`);
    math(view);
  }

  async function deleteNote(id) {
    try { await api(`/api/notes/${id}`, { method: "DELETE" }); toast(t("notes.deleted")); await route(); }
    catch (e) { toast(e.message || t("notes.deleteFailed")); }
  }

  function readerFrameReady(frame) {
    try {
      const doc = frame.contentDocument;
      if (!doc) return;
      const style = doc.createElement("style");
      style.id = "tf-reader-alignment-fix";
      style.textContent = ".kicker,.course,.subtitle,.meta{text-indent:0!important}#tfSearchBtn,#tfEditBtn,#tfExportBtn{display:none!important}";
      doc.head.appendChild(style);
      const lib = doc.getElementById("tfLibLink");
      if (lib) { lib.target = "_top"; lib.href = "/#/library"; }
    } catch (e) { /* cross-origin static reader */ }
  }

  let readerSearchHits = [];
  let readerSearchIndex = -1;

  function readerSearchFrame() {
    const frame = document.querySelector(".reader-frame");
    return frame && frame.contentWindow;
  }

  function readerSearchUpdate() {
    const count = document.getElementById("readerSearchTopCount");
    if (!count) return;
    const n = readerSearchHits.length;
    const i = readerSearchIndex;
    count.textContent = n ? `${i >= 0 ? i + 1 : 1} / ${n}` : "0";
  }

  function readerSearchClear() {
    const frame = document.querySelector(".reader-frame");
    const doc = frame && frame.contentDocument;
    if (doc) {
      doc.querySelectorAll("mark.tf-parent-hit").forEach((m) => {
        const t = doc.createTextNode(m.textContent || "");
        if (m.parentNode) m.parentNode.replaceChild(t, m);
      });
      doc.body.normalize();
    }
    readerSearchHits = [];
    readerSearchIndex = -1;
    readerSearchUpdate();
  }

  function readerSearchToggle() {
    const panel = document.getElementById("readerSearchTop");
    if (!panel) return;
    panel.hidden = !panel.hidden;
    if (!panel.hidden) {
      readerSearchClear();
      const input = document.getElementById("readerSearchTopInput");
      if (input) { input.value = ""; setTimeout(() => input.focus(), 30); }
    } else {
      readerSearchClear();
    }
  }

  function readerSearchRun() {
    const frame = document.querySelector(".reader-frame");
    const doc = frame && frame.contentDocument;
    const input = document.getElementById("readerSearchTopInput");
    if (!doc || !input) { toast(t("reader.actionUnavailable")); return; }
    readerSearchClear();
    const q = input.value.trim();
    if (!q) return;
    const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (parent && parent.closest("script,style,.tf-reader-tools,.tf-search-bar,.tf-ai-panel,.tf-export-menu,.tf-practice")) return NodeFilter.FILTER_REJECT;
        return node.nodeValue.toLowerCase().includes(q.toLowerCase()) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const text = node.nodeValue || "";
      const lower = text.toLowerCase(), needle = q.toLowerCase();
      let at = lower.indexOf(needle), from = 0;
      if (at < 0) return;
      const frag = doc.createDocumentFragment();
      while (at >= 0) {
        frag.appendChild(doc.createTextNode(text.slice(from, at)));
        const mark = doc.createElement("mark");
        mark.className = "tf-parent-hit";
        mark.textContent = text.slice(at, at + q.length);
        mark.style.background = "#d8ff42";
        mark.style.color = "#172016";
        mark.style.borderRadius = "2px";
        frag.appendChild(mark);
        readerSearchHits.push(mark);
        from = at + q.length;
        at = lower.indexOf(needle, from);
      }
      frag.appendChild(doc.createTextNode(text.slice(from)));
      node.parentNode.replaceChild(frag, node);
    });
    if (readerSearchHits.length) {
      readerSearchIndex = 0;
      const first = readerSearchHits[0];
      first.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    readerSearchUpdate();
  }

  function readerSearchStep(step) {
    if (!readerSearchHits.length) return;
    readerSearchIndex = (readerSearchIndex + step + readerSearchHits.length) % readerSearchHits.length;
    readerSearchHits.forEach((m) => { m.style.outline = ""; });
    const hit = readerSearchHits[readerSearchIndex];
    hit.style.outline = "2px solid #172016";
    hit.scrollIntoView({ behavior: "smooth", block: "center" });
    readerSearchUpdate();
  }

  function readerSearchClose() {
    const panel = document.getElementById("readerSearchTop");
    if (panel) panel.hidden = true;
    readerSearchClear();
  }

  function readerAction(action, event) {
    if (event) { event.preventDefault(); event.stopPropagation(); }
    const frame = document.querySelector(".reader-frame");
    const doc = frame && frame.contentDocument;
    if (action === "export") {
      const menu = document.getElementById("readerExportMenu");
      if (menu) menu.hidden = !menu.hidden;
      return;
    }
    if (action === "search") {
      readerSearchToggle();
      return;
    }
    if (action === "print") {
      try { frame && frame.contentWindow && frame.contentWindow.print(); } catch (e) { toast(String(e)); }
      return;
    }
    const internal = { edit: "tfEditBtn" }[action];
    const btn = internal && doc && doc.getElementById(internal);
    if (!btn) { toast(t("reader.actionUnavailable")); return; }
    btn.click();
    if (action === "edit") {
      const editing = doc.querySelector(".lecture")?.getAttribute("contenteditable") === "true";
      toast(editing ? t("reader.editOn") : t("reader.editOff"));
    }
  }

  async function saveHtmlToDesktop(name, html) {
    const r = await api("/api/save-html", { method: "POST", body: { name, html } });
    toast(t("export.savedTo", { path: r.path || "" }));
  }

  async function saveReaderFile(id, fmt) {
    toast(t("export.saving"));
    try {
      if (fmt === "html") {
        const res = await fetch(`/api/artifacts/${encodeURIComponent(id)}/export.html`);
        if (!res.ok) throw new Error(t("export.failed"));
        const html = await res.text();
        await saveHtmlToDesktop(`TermFinale-${id}.html`, html);
        return;
      }
      const r = await api(`/api/artifacts/${encodeURIComponent(id)}/save?fmt=${encodeURIComponent(fmt)}`, { method: "POST", body: {} });
      toast(t("export.savedTo", { path: r.path || "" }));
    } catch (e) { toast(requestErrorMessage(e, t("export.failed"))); }
  }

  function setDocReaderSaveStatus(text) {
    const el = document.getElementById("docReaderSaveStatus");
    if (el) el.textContent = text || "";
  }

  async function saveDocReaderFile(fmt) {
    const doc = state.workbench && state.workbench.doc;
    if (!doc || !doc.id) { toast(t("exam.failed")); return; }
    await saveDocumentFile(doc.id, fmt);
  }

  async function saveDocumentFile(id, fmt, html = "") {
    const status = t("export.saving");
    setDocReaderSaveStatus(status);
    toast(status);
    try {
      if (fmt === "html") {
        if (!html) throw new Error(t("export.failed"));
        await saveHtmlToDesktop(`TermFinale-${id}.html`, html);
        return;
      }
      const r = await api(`/api/documents/${encodeURIComponent(id)}/save?fmt=${encodeURIComponent(fmt)}`, { method: "POST", body: {} });
      toast(t("export.savedTo", { path: r.path || "" }));
      setDocReaderSaveStatus(t("export.savedTo", { path: r.path || "" }));
    } catch (e) { toast(e.message || t("export.failed")); setDocReaderSaveStatus(e.message || t("export.failed")); }
  }

  async function renderPdfViewer(id, seq) {
    let a;
    try { a = await api(`/api/artifacts/${encodeURIComponent(id)}`); }
    catch (e) { view.innerHTML = errorBox(e.message || t("error.load"), `<a class="btn btn-ghost" href="#/library">${t("reader.backLibrary")}</a>`); return; }
    if (seq !== state.seq) return;
    document.body.classList.add("reading", "reader-iframe");
    view.innerHTML = `<div class="reader-shell">
      <div class="reader-bar">
        <img class="reader-logo" src="/static/logo-mark.svg" alt="TermFinale">
        <a class="btn btn-ghost" href="#" onclick="act.back('#/read/${encodeURIComponent(id)}', event)">${t("reader.back")}</a>
        <div class="reader-title">${esc(a.title)} · PDF</div>
        <button class="btn btn-ghost" type="button" onclick="act.saveReaderFile('${esc(id)}','pdf')">${t("reader.savePdf")}</button>
        <a class="btn btn-ghost" href="/artifact/${encodeURIComponent(id)}/lecture.pdf" download>${t("reader.exportPdf")}</a>
      </div>
      <iframe class="reader-frame pdf-frame" src="/artifact/${encodeURIComponent(id)}/lecture.pdf" title="${esc(a.title)} PDF"></iframe>
    </div>`;
  }

  async function renderReader(id, seq, anchor = "") {
    let a;
    try { a = await api(`/api/artifacts/${encodeURIComponent(id)}`); }
    catch (e) {
      if (seq !== state.seq) return;
      view.innerHTML = pageHead("404", t("reader.notFound"), t("reader.notFoundText"), `<a class="btn btn-primary" href="#/library">${t("reader.backLibrary")}</a>`);
      return;
    }
    if (seq !== state.seq) return;
    try { localStorage.setItem("tf-last-read", JSON.stringify({ id: a.id, title: a.title, ts: Date.now() })); } catch (e) {}
    document.body.classList.add("reading", "reader-iframe");
    view.innerHTML = `<div class="reader-shell">
      <div class="reader-bar">
        <img class="reader-logo" src="/static/logo-mark.svg" alt="TermFinale">
        <a class="btn btn-ghost" href="#" onclick="act.back('#/library', event)">${t("reader.back")}</a>
        <div class="reader-title">${esc(a.title)} · ${esc(qualityStatusLabel(a.quality))}</div>
        <div class="reader-actions">
          <button class="btn btn-ghost" type="button" onclick="act.readerAction('search', event)">${t("reader.search")}</button>
          <button class="btn btn-ghost" type="button" onclick="act.readerAction('edit', event)">${t("reader.edit")}</button>
          <div class="reader-export-wrap">
            <button class="btn btn-ghost" type="button" onclick="act.readerAction('export', event)">${t("reader.export")}</button>
            <div class="reader-export-menu" id="readerExportMenu" hidden>
              <a href="#/pdf/${encodeURIComponent(id)}">${t("reader.exportPdf")}</a>
              <button type="button" onclick="act.saveReaderFile('${esc(id)}','pdf')">${t("reader.savePdf")}</button>
              <button type="button" onclick="act.saveReaderFile('${esc(id)}','docx')">${t("reader.exportWord")}</button>
              <button type="button" onclick="act.saveReaderFile('${esc(id)}','html')">${t("reader.exportHtml")}</button>
              <button type="button" onclick="act.readerAction('print', event)">${t("reader.print")}</button>
            </div>
          </div>
        </div>
      </div>
      <div class="reader-search-top" id="readerSearchTop" hidden>
        <input id="readerSearchTopInput" type="search" placeholder="${t("reader.searchPh")}" aria-label="${t("reader.searchPh")}" onkeydown="if(event.key==='Enter'){event.preventDefault();act.readerSearchRun();}if(event.key==='Escape'){event.preventDefault();act.readerSearchClose();}">
        <span class="reader-search-count" id="readerSearchTopCount">0</span>
        <button type="button" class="btn btn-ghost" onclick="act.readerSearchStep(-1)" aria-label="previous">↑</button>
        <button type="button" class="btn btn-ghost" onclick="act.readerSearchStep(1)" aria-label="next">↓</button>
        <button type="button" class="btn btn-ghost" onclick="act.readerSearchClose()">×</button>
      </div>
      <iframe class="reader-frame" onload="act.readerFrameReady(this)" src="/artifact/${encodeURIComponent(id)}/lecture.html?embed=1${anchor ? (anchor.indexOf("page/") === 0 ? "&page=" + encodeURIComponent(anchor.slice(5)) : "#" + encodeURIComponent(anchor)) : ""}" title="${esc(a.title)}"></iframe>
    </div>`;
  }

  // ---------------- actions ----------------

  async function setTheme(theme) { await saveTheme(theme); }

  window.act = {
    back: goBack,
    readerFrameReady,
    readerAction,
    setTheme,
    setLang,
    selectOption,
    submitAnswer,
    nextQuestion,
    startQuestions,
    importBank,
    deleteDoc,
    deleteBankQuestion,
    onboardLang,
    onboardNext,
    onboardBack,
    onboardFinish,
    renameDoc,
    cleanPapers,
    startPracticePick,
    cancelPractice,
    practiceRestart,
    revealReview,
    reviewResult,
    deleteNote,
    archiveCourse,
    saveCoursePrefs,
    saveCourseEdit,
    courseEditToggle,
    libraryEditToggle,
    deleteLecture,
    startGeneration,
    startFusion,
    startUnitExam,
    fuseRecalc,
    cancelGeneration,
    wbCourse,
    wbArtifact,
    wbKind,
    wbSourceMode,
    wbSourceMode,
    wbSection,
    wbMode,
    wbCount,
    wbGenLang,
    runTask,
    cancelTask,
    loadDoc,
    saveProfile,
    saveKeys,
    testKeys,
    aiQuick,
    aiAgent,
    aiFormEdit,
    aiAddStep,
    aiRemoveStep,
    aiApplyForm,
    aiEditPlan,
    aiApplyPlan,
    aiSaveWorkflow,
    aiLoadWorkflow,
    aiGoalPlan,
    aiRunDueGoals,
    aiRunAgent,
    aiFeedback,
    aiReplan,
    resumeAgent,
    resumeJob,
    runArtifactAudit,
    cancelAgent,
    aiWhole,
    startExam,
    cancelExam,
    examAnswers,
    examStart,
    examSelect,
    examSubmit,
    examBack,
    examEdit,
    examExport,
    examWord,
    saveReaderFile,
    saveDocumentFile,
    saveDocReaderFile,
    taskExportHtml,
    taskEdit,
    openDocReader,
    closeDocReader,
    docReaderSearch,
    printDocReader,
    readerSearchToggle,
    readerSearchRun,
    readerSearchStep,
    readerSearchClose,
    saveReview,
    rewriteArtifact,
    discardDraft,
    acceptDraft,
    restoreBackup,
  };

  window.addEventListener("afterprint", () => document.body.classList.remove("printing-doc"));
  document.querySelectorAll("[data-set-lang]").forEach((b) => {
    b.onclick = () => setLang(b.dataset.setLang);
  });
  document.getElementById("langBtn").onclick = () => {
    const order = ["zh", "hant", "en"];
    setLang(order[(order.indexOf(state.lang) + 1) % order.length]);
  };
  document.getElementById("themeBtn").onclick = () => {
    const now = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    saveTheme(now);
  };
  document.getElementById("menuBtn").onclick = () => {
    document.querySelector(".sidebar")?.classList.toggle("open");
  };
  initSearch();
  window.addEventListener("tf-pages-saved", () => { if (/^#\/(course|practice)\//.test(location.hash)) route(); });
  let aiSelectBtn = null;
  function hideAiSelect() {
    if (aiSelectBtn) { aiSelectBtn.remove(); aiSelectBtn = null; }
  }
  document.addEventListener("mouseup", (ev) => {
    if (aiSelectBtn && aiSelectBtn.contains(ev.target)) return;
    setTimeout(() => {
      const sel = window.getSelection ? window.getSelection() : null;
      const text = sel ? String(sel.toString() || "").trim() : "";
      if (!text || text.length < 3 || text.length > 1200) { hideAiSelect(); return; }
      const anchor = sel.anchorNode;
      const host = anchor && (anchor.nodeType === 1 ? anchor : anchor.parentElement);
      if (host && host.closest("input,textarea,select,[contenteditable='true'],[contenteditable='']")) { hideAiSelect(); return; }
      hideAiSelect();
      const rect = sel.getRangeAt(0).getBoundingClientRect();
      const panel = document.createElement("div");
      panel.style.cssText = "position:fixed;z-index:10020;left:" + Math.max(12, rect.left + rect.width / 2 - 62) + "px;top:" + Math.max(12, rect.top - 42) + "px;display:flex;gap:6px;padding:4px;border-radius:99px;background:#fff;box-shadow:0 6px 18px rgba(0,0,0,.2)";
      const ask = document.createElement("button");
      ask.type = "button";
      ask.textContent = "问 AI";
      ask.style.cssText = "height:28px;padding:0 10px;border:0;border-radius:99px;background:#1f2328;color:#fff;font-size:12px;cursor:pointer";
      ask.onclick = (e) => {
        e.preventDefault(); e.stopPropagation(); hideAiSelect();
        openAI().then(() => {
          const input = document.getElementById("aiInput");
          if (!input) return;
          input.value = "请结合当前资料解释这段内容：\n" + text;
          input.focus();
          input.setSelectionRange(input.value.length, input.value.length);
        });
      };
      const noteBtn = document.createElement("button");
      noteBtn.type = "button";
      noteBtn.textContent = "加笔记";
      noteBtn.style.cssText = "height:28px;padding:0 10px;border:0;border-radius:99px;background:#f2f0e9;color:#3b3a35;font-size:12px;cursor:pointer";
      noteBtn.onclick = async (e) => {
        e.preventDefault(); e.stopPropagation(); hideAiSelect();
        const aid = aiArtifactId();
        if (!aid) { toast("先在阅读器里打开一份资料"); return; }
        try {
          await api("/api/notes", { method: "POST", body: { artifact_id: aid, text: text } });
          toast("已加入笔记");
        } catch (err) { toast("笔记保存失败：" + err.message); }
      };
      panel.appendChild(ask); panel.appendChild(noteBtn);
      document.body.appendChild(panel);
      aiSelectBtn = panel;
    }, 0);
  });
  document.addEventListener("scroll", hideAiSelect, true);
  document.getElementById("aiFab").onclick = openAI;

  const aiWebBtn = document.getElementById("aiWeb");
  if (aiWebBtn) aiWebBtn.onclick = () => { state.ai.web = !state.ai.web; try { localStorage.setItem("tf-ai-web", state.ai.web ? "1" : "0"); } catch (e) {} aiRender(); };
  const aiDeepBtn = document.getElementById("aiDeep");
  if (aiDeepBtn) aiDeepBtn.onclick = () => toggleDeep();
  const aiStop = document.getElementById("aiStop");
  if (aiStop) aiStop.onclick = () => { try { state.ai.abort && state.ai.abort.abort(); } catch (e) {} };
  const aiMobile = document.getElementById("aiFabMobile");
  if (aiMobile) aiMobile.onclick = openAI;
  document.getElementById("aiClose").onclick = closeAI;
  document.getElementById("aiForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = document.getElementById("aiInput");
    const text = input.value;
    input.value = "";
    sendAI(text, "chat");
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && state.ai.open) closeAI();
  });


  function jobResult(job) {
    const v = job && job.result;
    if (!v) return {};
    if (typeof v === "string") { try { return JSON.parse(v); } catch (e) { return {}; } }
    return v;
  }

  let searchTimer = null;
  let searchSeq = 0;

  function searchKindLabel(kind) {
    return t(kind === "course" ? "search.course" : kind === "artifact" ? "search.artifact" : "search.content");
  }

  function renderSearchResults(data) {
    const box = document.getElementById("searchResults");
    const meta = document.getElementById("searchTitle");
    if (!box || !meta) return;
    const results = (data && data.results) || [];
    if (!results.length) {
      meta.textContent = t("search.title");
      box.innerHTML = `<div class="search-empty">${esc(t("search.empty"))}</div>`;
      return;
    }
    meta.textContent = t("search.results", { n: results.length });
    box.innerHTML = results.map((r) => `<a class="search-result" href="${esc(r.href || "#")}" data-search-href="${esc(r.href || "#")}">
      <span class="search-type">${esc(searchKindLabel(r.kind))}</span>
      <span class="search-result-main"><span class="search-result-title">${esc(r.title || "")}</span>
      ${r.subtitle ? `<span class="search-result-sub">${esc(r.subtitle)}</span>` : ""}
      ${r.snippet ? `<span class="search-result-snippet">${esc(r.snippet)}</span>` : ""}</span></a>`).join("");
  }

  async function searchNow() {
    const input = document.getElementById("searchInput");
    const box = document.getElementById("searchResults");
    const meta = document.getElementById("searchTitle");
    if (!input || !box) return;
    const q = input.value.trim();
    if (!q) {
      ++searchSeq;
      if (meta) meta.textContent = t("search.title");
      box.innerHTML = `<div class="search-hint">${esc(t("search.hint"))}</div>`;
      return;
    }
    const seq = ++searchSeq;
    box.innerHTML = `<div class="search-hint">${esc(t("search.loading"))}</div>`;
    try {
      const data = await api("/api/search?q=" + encodeURIComponent(q) + "&limit=12");
      if (seq !== searchSeq) return;
      renderSearchResults(data);
    } catch (e) {
      if (seq !== searchSeq) return;
      box.innerHTML = `<div class="search-empty">${esc(e.message || t("search.empty"))}</div>`;
    }
  }

  function openSearch() {
    const overlay = document.getElementById("searchOverlay");
    const input = document.getElementById("searchInput");
    if (!overlay || !input) return;
    state.ai.open = false;
    const drawer = document.getElementById("aiDrawer");
    if (drawer) drawer.hidden = true;
    overlay.hidden = false;
    input.focus();
    input.select();
    searchNow();
  }

  function closeSearch() {
    const overlay = document.getElementById("searchOverlay");
    if (overlay) overlay.hidden = true;
  }

  function initSearch() {
    const trigger = document.getElementById("commandSearch");
    const overlay = document.getElementById("searchOverlay");
    const input = document.getElementById("searchInput");
    const box = document.getElementById("searchResults");
    const close = document.getElementById("searchClose");
    if (trigger) trigger.onclick = openSearch;
    if (close) close.onclick = closeSearch;
    if (overlay) overlay.onclick = (e) => { if (e.target === overlay) closeSearch(); };
    if (input) {
      input.addEventListener("input", () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(searchNow, 160);
      });
      input.addEventListener("keydown", (e) => {
        if (e.key === "Escape") { e.preventDefault(); closeSearch(); }
        if (e.key === "Enter") {
          const first = box && box.querySelector("a[data-search-href]");
          if (first) { e.preventDefault(); closeSearch(); location.hash = first.getAttribute("href"); }
        }
      });
    }
    if (box) box.addEventListener("click", (e) => {
      const a = e.target.closest("a[data-search-href]");
      if (!a) return;
      e.preventDefault();
      closeSearch();
      location.hash = a.getAttribute("href");
    });
    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openSearch(); }
      if (e.key === "Escape") closeSearch();
    });
  }

  function aiArtifactId() {
    const hash = String(location.hash || "");
    const m = hash.match(/^#\/(?:read|artifact|practice)\/([^/?]+)/);
    if (m) return decodeURIComponent(m[1]);
    const exam = hash.match(/^#\/exam(?:\?|$)/);
    if (exam) {
      const params = new URLSearchParams(hash.split("?")[1] || "");
      if (params.get("artifact")) return decodeURIComponent(params.get("artifact"));
      if (state.exam && state.exam.doc && state.exam.doc.artifact_id) return state.exam.doc.artifact_id;
    }
    // 课程页不强行绑定第一份讲义：全局检索该课程/全部资料，页面正文做当前上下文。
    return "";
  }

  function aiArtifactTitle() {
    const aid = state.ai.artifactId;
    const found = (state.artifacts || []).find((a) => a.id === aid) || (state.artifact && state.artifact.id === aid ? state.artifact : null);
    return found ? found.title : t("ai.allLibrary");
  }

  function aiPageContext() {
    const view = document.getElementById("view");
    return view ? String(view.innerText || "").slice(0, 8000) : "";
  }

  function aiSelection() {
    try { return String(window.getSelection ? window.getSelection().toString() : "").slice(0, 1200); } catch (e) { return ""; }
  }

  function aiSessionKey() {
    return state.ai.artifactId || "__assistant__";
  }

  function mdAI(text) {
    let out = esc(text || "");
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) => {
      const safe = url.replace(/"/g, "%22");
      return `<a href="${safe}" target="_blank" rel="noreferrer">${label}</a>`;
    });
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    // Keep math on one logical line for KaTeX; newlines inside $$...$$ break parsing.
    out = out.replace(/\$\$([\s\S]*?)\$\$/g, (_, body) => "$$" + body.replace(/\n/g, " ") + "$$");
    out = out.replace(/\$([^$\n]+)\$/g, (_, body) => "$" + body.replace(/\n/g, " ") + "$");
    return out.replace(/\n/g, "<br>");
  }

  function aiRender() {
    const drawer = document.getElementById("aiDrawer");
    if (!drawer || !state.ai.open) return;
    document.getElementById("aiTitle").textContent = t("ai.title");
    const allLibrary = !state.ai.artifactId;
    document.getElementById("aiContext").textContent = `${t("ai.context")}：${allLibrary ? t("ai.allLibrary") : aiArtifactTitle()}${state.ai.web ? " · 联网" : ""}`;
    const webBtn = document.getElementById("aiWeb");
    if (webBtn) { webBtn.classList.toggle("on", !!state.ai.web); webBtn.textContent = state.ai.web ? "联网已开" : "联网"; }
    const deepBtn = document.getElementById("aiDeep");
    if (deepBtn) { deepBtn.classList.toggle("on", !!state.ai.deep); deepBtn.textContent = state.ai.deep ? "深度思考已开" : "深度思考"; deepBtn.title = state.ai.deep ? "已锁定完整思考；再点关闭" : "打开后复杂问题会思考更久、更稳"; }
    document.getElementById("aiInput").placeholder = allLibrary ? t("ai.allPlaceholder") : t("ai.placeholder");
    document.getElementById("aiSend").textContent = t("ai.send");
    document.getElementById("aiNote").textContent = t("ai.note") + (allLibrary ? ` · ${t("ai.allHint")}` : "") + (state.ai.deep ? " · 深度思考" : "") + (state.ai.usage ? ` · ${state.ai.usage.used}/${state.ai.usage.max} tokens` : "");
    const stop = document.getElementById("aiStop");
    if (stop) stop.hidden = !state.ai.busy;
    const quick = document.getElementById("aiQuick");
    quick.innerHTML = `<button type="button" onclick="act.aiQuick('explain')">${state.ai.artifactId ? t("ai.quickExplain") : t("ai.capExplain")}</button>
      <button type="button" onclick="act.aiQuick('quiz')">${t("ai.quickQuiz")}</button>
      <button type="button" onclick="act.aiAgent()">${t("ai.agent")}</button>` +
      (state.ai.artifactId ? `<button type="button" onclick="act.aiQuick('points')">${t("ai.quickPoints")}</button>
         <button type="button" onclick="act.aiWhole()">${t("ai.whole")}</button>` : "");
    const box = document.getElementById("aiMessages");
    const msgs = state.ai.messages || [];
    const draft = state.ai.rewriteDoc ? `<div class="ai-msg assistant"><strong>${t("ai.wholeDone")}</strong><div class="mt-8"><a class="btn btn-ghost" href="#/artifact/${encodeURIComponent(state.ai.rewriteDoc.draft_id)}">${t("ai.openDraft")}</a></div></div>` : "";
    const ap = state.ai.agentPlan;
    const planCard = ap ? `<div class="ai-msg assistant"><strong>${t("ai.agentPlan")}</strong>
      <div class="small muted mt-8">${t("ai.agentPlanner")}：${esc(ap.planner || "fallback")} · ${esc(ap.note || "")}</div>
      ${(ap.steps || []).map((s, i) => `<div class="small mt-8">${i + 1}. ${esc(s.tool)} ${s.requires_confirmation ? `<span class="badge badge-warn">${t("ai.agentNeedConfirm")}</span>` : ""}</div>`).join("")}
      ${state.ai.planForm ? aiPlanForm(ap) : state.ai.planEditing ? `<textarea id="aiPlanEdit" rows="5" class="mt-8" style="width:100%">${esc(JSON.stringify(ap.steps || [], null, 2))}</textarea>
        <div class="actions mt-8"><button class="btn btn-primary" onclick="act.aiApplyPlan()">${t("ai.agentApply")}</button></div>` :
        `<div class="actions mt-8"><button class="btn btn-primary" onclick="act.aiRunAgent()">${t("ai.agentRun")}</button>
        <button class="btn btn-ghost" onclick="act.aiFormEdit()">${t("ai.agentForm")}</button>
        <button class="btn btn-ghost" onclick="act.aiEditPlan()">${t("ai.agentEdit")}</button>
        <button class="btn btn-ghost" onclick="act.aiSaveWorkflow()">${t("ai.agentSave")}</button>
        ${state.ai.busy && state.ai.agentJobId ? `<button class="btn btn-ghost" onclick="act.cancelAgent()">${t("ai.agentCancel")}</button>` : ""}</div>`}</div>` : "";
    const ar = state.ai.agentResult;
    const agentCard = ar ? `<div class="ai-msg assistant"><strong>${t("ai.agent")}</strong>
      <div class="small muted mt-8">${t("ai.agentPlan")}</div>
      ${(ar.plan || []).map((s, i) => `<div class="small">${i + 1}. ${esc(s.tool)} · ${s.ok === false ? "失败" : "完成"}</div>`).join("")}
      <div class="mt-8">${mdAI(ar.answer || "")}</div>
      ${(ar.citations || []).length ? `<div class="ai-src-row">${ar.citations.slice(0,6).map((c) => String(c).startsWith("http") ? `<a class="ai-src-chip web" href="${esc(c)}" target="_blank" rel="noreferrer">🌐 ${esc(c)}</a>` : `<span class="ai-src-chip">${esc(c)}</span>`).join("")}</div>` : ""}
      ${(ar.actions || []).map((x) => `<a class="btn btn-ghost mt-8" href="${esc(x.href)}">${esc(x.label)}</a>`).join(" ")}
      ${ar.ok === false && state.ai.lastAgentJobId ? `<button class="btn btn-primary mt-8" onclick="act.aiReplan()">${t("ai.agentReplan")}</button>` : ""}
    </div>` : "";
    const runs = (state.ai.agentRuns || []).length ? `<div class="ai-msg assistant"><strong>${t("ai.agentRuns")}</strong>${state.ai.agentRuns.map((x) => `<div class="small mt-8">${esc(x.status)} · ${esc(x.goal || x.step || "")}</div>`).join("")}</div>` : "";
    const wfs = (state.ai.workflows || []).length ? `<div class="ai-msg assistant"><strong>${t("ai.agentWorkflows")}</strong>${state.ai.workflows.map((x, i) => `<div class="small mt-8">${esc(x.name)} v${x.version || 1} <button class="btn btn-ghost" onclick="act.aiLoadWorkflow(${i})">${t("ai.agentRun")}</button></div>`).join("")}</div>` : "";
    const goals = (state.ai.goals || []).length ? `<div class="ai-msg assistant"><strong>${t("ai.agentGoals")}</strong>${state.ai.goals.map((g) => `<div class="small mt-8">${esc(g.goal)} · ${esc(g.next_run || "")} <button class="btn btn-ghost" onclick="act.aiGoalPlan(${g.id})">${t("ai.agentGoalPlan")}</button></div>`).join("")}<div class="actions mt-8"><button class="btn btn-ghost" onclick="act.aiRunDueGoals()">${t("ai.agentRunDue")}</button></div></div>` : "";
    const msgHtml = msgs.map((m, mi) => {
      if (m.role === "user") return `<div class="ai-msg user">${esc(m.content || "")}</div>`;
      const cites = /第\s*\d+\s*页|《[^》]+》|讲义|资料/.test(m.content || "");
      const showSrc = m.mode !== "chat" || cites;
      const src = showSrc ? (m.sources || []).slice(0, 5).map((s) => {
        if (s.url) return `<a class="ai-src-chip web" href="${esc(s.url)}" target="_blank" rel="noreferrer">🌐 ${esc(s.title || s.url)}</a>`;
        const pages = (s.pages || []).map((p) => `p.${p}`).join(", ");
        const label = [s.artifact, pages, s.section].filter(Boolean).join(" · ");
        const target = (s.pages && s.pages.length) ? `page/${s.pages[0]}` : (s.anchor || "");
        const href = s.artifact_id ? `#/read/${encodeURIComponent(s.artifact_id)}${target ? "/" + target : ""}` : "#";
        return `<a class="ai-src-chip" href="${href}">${esc(label)}</a>`;
      }).join("") : "";
      const unsourced = m.role === "assistant" && !m.streaming && m.mode !== "chat" && !(m.sources || []).length ? `<div class="ai-unsourced">${t("ai.unsourced")}</div>` : "";
      const fb = m.role === "assistant" && !m.streaming ? `<div class="ai-feedback"><button type="button" data-fb="1" onclick="act.aiFeedback(${mi},1)" class="${m.feedback === 1 ? "on" : ""}">${t("ai.useful")}</button><button type="button" data-fb="-1" onclick="act.aiFeedback(${mi},-1)" class="${m.feedback === -1 ? "on" : ""}">${t("ai.useless")}</button>${m.feedback ? `<span>${t("ai.recorded")}</span>` : ""}</div>` : "";
      return `<div class="ai-msg assistant">${mdAI(m.content || "")}${src ? `<div class="ai-src-row">${src}</div>` : ""}${unsourced}${fb}</div>`;
    }).join("");
    const capability = `<div class="ai-msg assistant ai-capabilities"><strong>${t("ai.capTitle")}</strong>
      <div class="ai-cap-grid"><div><b>${t("ai.capExplain")}</b><span>${t("ai.capExplainBody")}</span></div><div><b>${t("ai.capQuiz")}</b><span>${t("ai.capQuizBody")}</span></div><div><b>${t("ai.capAgent")}</b><span>${t("ai.capAgentBody")}</span></div></div>
      <p class="ai-cap-note">${t("ai.capNote")}</p></div>`;
    const advanced = (runs || wfs || goals) ? `<details class="ai-advanced"><summary>${t("ai.advanced")}</summary>${runs}${wfs}${goals}</details>` : "";
    box.innerHTML = (msgs.length ? msgHtml : capability) +
      (state.ai.busy ? `<div class="ai-msg assistant pending">${t("ai.thinking")}${state.ai.wait ? ` ${state.ai.wait}s` : ""}</div>` : "") + planCard + draft + agentCard + advanced;
    if (msgs.length || state.ai.busy || planCard || agentCard) box.scrollTop = box.scrollHeight;
    else box.scrollTop = 0;
    math(box);
  }

  async function openAI() {
    const drawer = document.getElementById("aiDrawer");
    if (!drawer) return;
    state.ai.open = true;
    state.ai.artifactId = aiArtifactId();
    drawer.hidden = false;
    state.ai.busy = false;
    state.ai.messages = [];
    try {
      state.ai.agentRuns = await api("/api/agent/runs?limit=5").catch(() => []);
      state.ai.workflows = await api("/api/agent/workflows?limit=8").catch(() => []);
      state.ai.tools = (await api("/api/agent/tools").catch(() => ({ tools: [] }))).tools || [];
      state.ai.goals = await api("/api/agent/goals/due").catch(() => []);
      state.ai.usage = await api("/api/usage").catch(() => null);
      const r = await api(`/api/chat/${encodeURIComponent(aiSessionKey())}`);
      state.ai.messages = (r.messages || []).slice(-30).map((m) => {
        let sources = [];
        try { sources = (JSON.parse(m.meta || "{}").sources) || []; } catch (e) {}
        return { role: m.role, content: m.content, sources };
      });
    } catch (e) { /* start empty */ }
    aiRender();
    document.getElementById("aiInput").focus();
  }

  function toggleDeep() {
    state.ai.deep = !state.ai.deep;
    try { localStorage.setItem("tf-ai-deep", state.ai.deep ? "1" : "0"); } catch (e) {}
    aiRender();
  }

  function closeAI() {
    state.ai.open = false;
    const drawer = document.getElementById("aiDrawer");
    if (drawer) drawer.hidden = true;
  }

  async function sendAI(text, mode = "chat") {
    const q = String(text || "").trim();
    if (!q || state.ai.busy) return;
    const history = state.ai.messages.slice(-20).map((m) => ({ role: m.role, content: m.content }));
    state.ai.messages.push({ role: "user", content: q });
    const msg = { role: "assistant", content: "", sources: [], streaming: true, mode };
    state.ai.messages.push(msg);
    state.ai.busy = true;
    state.ai.wait = 0;
    state.ai.abort = new AbortController();
    aiRender();
    const body = { question: q, artifact_id: state.ai.artifactId, mode, history, lang: state.lang,
      web: !!state.ai.web, deep: !!state.ai.deep, context: aiPageContext(), selection: aiSelection() };
    try {
      const res = await fetch("/api/ask/stream", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body), signal: state.ai.abort.signal,
      });
      if (!res.ok || !res.body) throw new Error(`stream ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "", lastPaint = 0;
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf("\n\n")) >= 0) {
          const raw = buffer.slice(0, idx).replace(/^data:\s*/, "").trim();
          buffer = buffer.slice(idx + 2);
          if (!raw) continue;
          let ev;
          try { ev = JSON.parse(raw); } catch (e) { continue; }
          if (ev.type === "sources") msg.sources = ev.sources || [];
          else if (ev.type === "thinking") { state.ai.wait = Number(ev.elapsed) || 0; aiRender(); }
          else if (ev.type === "delta") msg.content += ev.text || "";
          else if (ev.type === "error") throw new Error(ev.error || t("ai.failed"));
          else if (ev.type === "done") msg.streaming = false;
          if (Date.now() - lastPaint > 45) { lastPaint = Date.now(); aiRender(); }
        }
      }
      msg.streaming = false;
      state.ai.busy = false;
      state.ai.wait = 0;
      state.ai.abort = null;
      aiRender();
    } catch (e) {
      const aborted = e && e.name === "AbortError";
      msg.streaming = false;
      state.ai.busy = false;
      state.ai.abort = null;
      if (aborted) {
        if (!msg.content) msg.content = "已停止。";
        aiRender();
        return;
      }
      // 旧服务或流式失败时回退到普通接口，避免功能不可用。
      if (!msg.content) {
        state.ai.messages.pop();
        try {
          const r = await api("/api/ask", { method: "POST", body });
          state.ai.messages.push({ role: "assistant", content: r.answer || "", sources: r.sources || [] });
        } catch (err) {
          state.ai.messages.push({ role: "assistant", content: `${t("ai.failed")}：${requestErrorMessage(err)}` });
        }
      } else {
        msg.content += `\n\n${t("ai.failed")}`;
      }
      aiRender();
    }
  }

  function aiPlanForm(ap) {
    return `<div class="ai-plan-form">${(ap.steps || []).map((s, i) => `<div class="field mt-8"><label>${i + 1}. ${esc(s.tool)}</label><textarea data-plan-args="${i}" rows="2" style="width:100%">${esc(JSON.stringify(s.args || {}, null, 2))}</textarea></div>`).join("")}<div class="actions mt-8"><button class="btn btn-primary" onclick="act.aiApplyForm()">${t("ai.agentApply")}</button><button class="btn btn-ghost" onclick="act.aiAddStep()">${t("ai.agentAddStep")}</button></div></div>`;
  }

  async function aiAgent() {
    const input = document.getElementById("aiInput");
    const goal = (input && input.value || "").trim();
    if (!goal) { toast(t("ai.agentGoalEmpty")); return; }
    state.ai.busy = true; aiRender();
    try {
      const r = await api("/api/agent/plan", { method: "POST", body: {
        goal, artifact_id: state.ai.artifactId, llm: true,
      }});
      state.ai.agentGoal = goal;
      state.ai.agentPlan = r;
      state.ai.planForm = false; state.ai.planEditing = false; state.ai.agentResult = null;
    } catch (e) { toast(e.message || t("error.actionFailed")); }
    state.ai.busy = false; aiRender();
  }

  async function aiRunAgent() {
    const ap = state.ai.agentPlan;
    if (!ap) return;
    state.ai.busy = true; aiRender();
    try {
      const r = await api("/api/agent/jobs?confirm=true", { method: "POST", body: {
        goal: state.ai.agentGoal || ap.goal || "执行计划", artifact_id: state.ai.artifactId,
        steps: ap.steps || [], llm: true, auto_repair: true,
      }});
      state.ai.agentJobId = r.job_id; state.ai.lastAgentJobId = r.job_id;
      await pollAgent(r.job_id);
    } catch (e) { toast(e.message || t("error.actionFailed")); state.ai.busy = false; aiRender(); }
  }

  async function pollAgent(jobId) {
    for (let i = 0; i < 240; i++) {
      await new Promise((r) => setTimeout(r, 1200));
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`).catch(() => null);
      if (!job) continue;
      if (job.status === "done" || job.status === "failed" || job.status === "cancelled") {
        state.ai.agentResult = jobResult(job);
        state.ai.busy = false; state.ai.agentJobId = null;
        state.ai.agentRuns = await api("/api/agent/runs?limit=5").catch(() => state.ai.agentRuns || []);
        aiRender(); return;
      }
    }
    state.ai.busy = false; aiRender();
  }

  async function cancelAgent() {
    if (!state.ai.agentJobId) return;
    await api(`/api/jobs/${encodeURIComponent(state.ai.agentJobId)}/cancel`, { method: "POST" }).catch(() => null);
    state.ai.busy = false; aiRender();
  }

  async function aiReplan() {
    if (!state.ai.lastAgentJobId) return;
    try {
      const r = await api(`/api/agent/runs/${encodeURIComponent(state.ai.lastAgentJobId)}/replan`, { method: "POST" });
      state.ai.agentPlan = { ...(state.ai.agentPlan || {}), steps: r.steps || r.plan || [], note: r.note || "" };
      state.ai.agentResult = null; state.ai.lastAgentJobId = null; aiRender();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }

  async function aiResume() {
    if (!state.ai.lastAgentJobId) return;
    try {
      const r = await api(`/api/agent/runs/${encodeURIComponent(state.ai.lastAgentJobId)}/resume`, { method: "POST" });
      state.ai.busy = true; state.ai.agentJobId = r.job_id; state.ai.lastAgentJobId = r.job_id; aiRender();
      await pollAgent(r.job_id);
    } catch (e) { toast(e.message || t("error.actionFailed")); state.ai.busy = false; aiRender(); }
  }

  function aiFormEdit() { state.ai.planForm = !state.ai.planForm; state.ai.planEditing = false; aiRender(); }
  function aiAddStep() {
    state.ai.agentPlan.steps = state.ai.agentPlan.steps || [];
    state.ai.agentPlan.steps.push({ tool: "search_material", args: {}, why: "", requires_confirmation: false });
    aiRender();
  }
  function aiRemoveStep(i) {
    if (!state.ai.agentPlan || !state.ai.agentPlan.steps) return;
    state.ai.agentPlan.steps.splice(i, 1); aiRender();
  }
  function aiApplyForm() {
    const ap = state.ai.agentPlan; if (!ap) return;
    document.querySelectorAll("[data-plan-args]").forEach((el) => {
      const i = Number(el.dataset.planArgs);
      try { ap.steps[i].args = JSON.parse(el.value || "{}"); } catch (e) { /* keep */ }
    });
    state.ai.planForm = false; aiRender();
  }
  function aiEditPlan() { state.ai.planEditing = !state.ai.planEditing; state.ai.planForm = false; aiRender(); }
  function aiApplyPlan() {
    const el = document.getElementById("aiPlanEdit"); if (!el) return;
    try {
      const steps = JSON.parse(el.value);
      if (!Array.isArray(steps)) throw new Error("steps 必须是数组");
      state.ai.agentPlan.steps = steps; state.ai.planEditing = false; aiRender();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }
  async function aiSaveWorkflow() {
    const ap = state.ai.agentPlan; if (!ap) return;
    const name = prompt(t("ai.agentSavePrompt"), state.ai.agentGoal || "workflow");
    if (!name) return;
    try {
      await api("/api/agent/workflows", { method: "POST", body: { name, steps: ap.steps || [] } });
      state.ai.workflows = await api("/api/agent/workflows?limit=8").catch(() => state.ai.workflows || []);
      aiRender();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }
  function aiLoadWorkflow(i) {
    const wf = (state.ai.workflows || [])[i]; if (!wf) return;
    state.ai.agentPlan = { goal: wf.name, steps: wf.steps || [], planner: "workflow", note: `v${wf.version || 1}` };
    state.ai.agentGoal = wf.name; aiRender();
  }
  async function aiGoalPlan(gid) {
    try {
      const r = await api(`/api/agent/goals/${encodeURIComponent(gid)}/plan`, { method: "POST" });
      state.ai.agentPlan = r; state.ai.agentGoal = r.goal || ""; aiRender();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }
  async function aiRunDueGoals() {
    try {
      const r = await api("/api/agent/goals/run-due", { method: "POST" });
      toast(JSON.stringify(r).slice(0, 120));
      state.ai.goals = await api("/api/agent/goals/due").catch(() => []);
      aiRender();
    } catch (e) { toast(e.message || t("error.actionFailed")); }
  }

  async function runArtifactAudit(aid) {
    const btn = document.getElementById("runAuditBtn");
    const status = document.getElementById("auditStatus");
    if (btn) btn.disabled = true;
    if (status) status.textContent = t("artifact.auditRunning");
    try {
      const r = await api(`/api/artifacts/${encodeURIComponent(aid)}/audit`, { method: "POST" });
      const counts = (r && r.counts) || {};
      const gaps = (counts.partial || 0) + (counts.missing || 0);
      const unverified = counts.unverified || 0;
      toast(gaps ? t("artifact.auditGaps", { n: gaps })
        : unverified ? t("artifact.auditUnverified", { n: unverified })
        : t("artifact.auditDone"));
      await route();
    } catch (e) {
      if (status) status.textContent = requestErrorMessage(e, t("error.actionFailed"));
      if (btn) btn.disabled = false;
    }
  }

  async function resumeJob(jobId, kind) {
    const path = kind === "exam" ? `/api/exam/jobs/${encodeURIComponent(jobId)}/resume`
                                 : `/api/lectures/jobs/${encodeURIComponent(jobId)}/resume`;
    try {
      const r = await api(path, { method: "POST" });
      const next = (r && (r.job_id || r.id)) || "";
      if (!next) throw new Error(t("job.resumeMissing"));
      toast(t("job.resumeStarted"));
      const card = document.getElementById("jobCard");
      if (card) card.hidden = false;
      document.getElementById("jobMsg").textContent = "";
      lockGenerationJob(next, t("new.jobEyebrow"));
      return pollJob(next);
    } catch (e) {
      toast(requestErrorMessage(e, t("job.resumeMissing")));
    }
  }

  function resumeAgent() { return aiResume(); }

  async function aiWhole() {
    if (!state.ai.artifactId) { toast(t("ai.general")); return; }
    const input = document.getElementById("aiInput");
    const instruction = (input && input.value || "").trim();
    if (!instruction) { toast(t("ai.wholePrompt")); return; }
    state.ai.busy = true; aiRender();
    try {
      const r = await api(`/api/artifacts/${encodeURIComponent(state.ai.artifactId)}/rewrite`, {
        method: "POST", body: { instruction, gen_lang: state.lang },
      });
      state.ai.rewriteDoc = r;
    } catch (e) { toast(e.message || t("error.actionFailed")); }
    state.ai.busy = false; aiRender();
  }

  async function aiFeedback(index, rating) {
    const m = (state.ai.messages || [])[index];
    if (!m || m.role !== "assistant") return;
    m.feedback = rating;
    const prev = [...state.ai.messages.slice(0, index)].reverse().find((x) => x.role === "user");
    try {
      await api("/api/feedback", { method: "POST", body: {
        artifact_id: state.ai.artifactId, question: prev ? prev.content : "",
        answer: m.content || "", rating,
      }});
    } catch (e) { /* local state still reflects */ }
    aiRender();
  }

  async function aiQuick(kind) {
    const scoped = state.ai.artifactId ? "当前资料" : "全部讲义";
    if (kind === "quiz") return sendAI(`请基于${scoped}出 2 道单选题：先题干和 4 个选项，再给答案和解析，标出处页。`, "quiz");
    if (kind === "plan") return sendAI(`请基于${scoped}给我 7 天复习计划，每天一个重点和一个小练习。`, "plan");
    if (kind === "points") return sendAI(`请提炼${scoped}的重点考点，按考试权重排序，每条标页码；明确不考的内容不要写。`, "explain");
    return sendAI(`请用零基础能懂的方式解释${scoped}的核心内容，按小节/考点组织，并标页码。`, "explain");
  }

  async function init() {
    const savedTheme = localStorage.getItem("tf-theme");
    applyTheme(savedTheme || "light");
    const savedLang = localStorage.getItem("tf-ui-lang");
    applyLang(["zh", "hant", "en"].includes(savedLang) ? savedLang : "zh");
    try {
      const s = await api("/api/settings");
      state.settings = s;
      applyProfile(s);
      repairSchoolLogo(s);
      if (!savedTheme && s.theme) applyTheme(s.theme);
      if (!savedLang && s.lang) applyLang(s.lang);
      if (!s.onboarded) {
        const c = canonicalHash(location.hash || "#/");
        if (c !== location.hash) { try { history.replaceState(null, "", c); } catch (e) { location.hash = c; } }
        showOnboarding();
        return;
      }
    } catch (e) { /* keep the shell usable when the backend is down */ }
    try {
      state.ai.web = localStorage.getItem("tf-ai-web") === "1";
      state.ai.deep = localStorage.getItem("tf-ai-deep") === "1";
    } catch (e) { /* ignore */ }
    await route();
  }


  function _verTuple(v) {
    return String(v || "").replace(/^v/i, "").split(".").map((x) => parseInt(x, 10) || 0);
  }
  function _verGt(a, b) {
    const x = _verTuple(a), y = _verTuple(b);
    for (let i = 0; i < Math.max(x.length, y.length); i++) {
      if ((x[i] || 0) > (y[i] || 0)) return true;
      if ((x[i] || 0) < (y[i] || 0)) return false;
    }
    return false;
  }
  async function checkUpdate() {
    try {
      const health = await api("/api/health");
      const local = String(health.app_version || "");
      if (!local || local === "0.0.0") return;
      const urls = [
        "https://cdn.jsdelivr.net/gh/Shuai-Lin2006/TermFinale@main/docs/version.json",
        "https://raw.githubusercontent.com/Shuai-Lin2006/TermFinale/main/docs/version.json",
      ];
      let remote = null;
      for (const u of urls) {
        try {
          const r = await fetch(u, { cache: "no-store" });
          if (r.ok) { remote = await r.json(); break; }
        } catch (e) { /* try next */ }
      }
      if (!remote || !_verGt(remote.version, local)) return;
      const key = "tf-update-dismissed-" + remote.version;
      if (localStorage.getItem(key) === "1") return;
      const box = document.createElement("div");
      box.id = "tfUpdateBanner";
      box.innerHTML = `<div><strong>发现新版本 v${remote.version}</strong><div class="tf-update-note">${remote.notes || "建议更新到最新版"}</div></div>
        <div class="tf-update-actions"><a href="${remote.url || "https://shuai-lin2006.github.io/TermFinale/"}" target="_blank" rel="noreferrer">查看更新</a><button type="button" id="tfUpdateClose">×</button></div>`;
      document.body.appendChild(box);
      box.querySelector("#tfUpdateClose").onclick = () => { localStorage.setItem(key, "1"); box.remove(); };
    } catch (e) { /* 更新检查失败不影响使用 */ }
  }

  setInterval(() => refreshCountdowns(document), 60000);
  setTimeout(checkUpdate, 1800);

  window.addEventListener("hashchange", () => {
    route();
    if (state.ai.open) openAI();
  });
  init();
})();
