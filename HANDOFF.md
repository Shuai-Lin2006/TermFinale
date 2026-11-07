# TermFinale 交接（新会话必读）

## 产品
TermFinale：Mac/Windows 桌面期末复习软件，Electron + FastAPI + SQLite，本地优先。
终极目标：比“把资料直接丢给顶级 AI + 强提示词”更可靠、更完整、更能坚持学完；可证明覆盖了什么、错在哪里。
边界：150页内逐页精准；150页以上章节概览；辅助复习，不替代老师划重点。

## 当前架构
- Electron 壳：~/Applications/TermFinale.app，后端 8903，源码 desktop_shell/main.js
- Web UI：web/*.html，assets/app.js、app.css
- 后端：server/app.py；服务：services/guide_service.py、review_service.py
- 解析：core/parser.py；OCR：core/ai_vision.py、qwen-vl-ocr
- 数据库/路径：core/database.py、core/paths.py
- 数据目录：~/Library/Application Support/TermFinale；不要重置

## 已完成
- Electron 独立窗口、启动器、Cmd+R、标题栏安全区
- 课程详情页、文件列表、返回层级、课程/生成物分层
- 16份PDF/PPTX：160/160任务成功
- ≤150页逐页提取；40页39/40、85页文字页77/77
- 图片页OCR：8/8单页验证成功，但主流程回填未稳定
- 4个旧.ppt已转pptx
- 公式渲染验证：真实讲义KaTeX 549节点
- 1001页分类修正 lecture
- PDF/Word导出抽测正常

## 已知失败/未完成
- 85页正式流程仍74~77，8张纯图片页未回填
- 171页提取106/171；1001页只试跑前20页
- 终极高数：提取超范围16处（极限/积分）
- 终极化学：命名违规 讲义14/提取27/试卷2
- 三份终极测试文件：~/Desktop/暴力测试最终/终极*
- 测试数据污染、按钮审计、真题逐题核对、签名/Windows未做
- 当前任务：每个生成模块独立约束 + 生成后硬校验（违规即失败、重试2次、UI每任务独立约束）

## 最高优先级
1. 任务级约束：讲义/提取/试卷各自范围、排除项
2. validate_output：排除词、页码、题型、答案
3. 85页图片页OCR回填
4. 150页精准；1000页概览
5. 真题校验、数据隔离、全按钮审计
6. 评测集、UI重构、学习闭环
7. Mac签名/公证、Windows、官网/GitHub

## 规矩
- 不重置用户数据
- 没验证不写“通过”
- 不删原资料
- 数据/测试课程 BATCH*/TEST*/FINAL* 需隔离
