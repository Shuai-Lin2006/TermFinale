import customtkinter as ctk
import json
import os
import re
import threading
import time
import datetime
from tkinter import filedialog
import tkinter.messagebox as messagebox
from loguru import logger

from models.user_profile import CourseInfo
from core.parser import extract_text_from_file
from core.ai_engine import generate_super_guide
from core.exam_engine import generate_logic_analysis, generate_extraction, generate_exam_paper
from core.exporter import export_to_html
from core.database import init_db, get_db_session, Course as DBCourse, GeneratedFile as DBGeneratedFile, \
    Material as DBMaterial, UserConfig as DBUserConfig
from core import config, paths
from core.logger import setup_logging, install_exception_hooks
from core.personas import PERSONA_LABELS, persona_from_label
from core.platform_utils import open_path
from services import guide_service, review_service
from app.desktop import theme
from app.desktop.components import (Card, EmptyState, GhostButton, PrimaryButton,
                                    SectionTitle, StatTile, StyledOptionMenu, Toast)

# Windows 高 DPI（必须在创建窗口前设置）
if os.name == "nt":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# 视觉常量统一来自 app/desktop/theme.py（跨平台字体、色板、间距）
FONT_FAMILY = theme.FONT_FAMILY
FONT_HUGE = theme.FONT_HUGE
FONT_H1 = theme.FONT_H1
FONT_H2 = theme.FONT_H2
FONT_BODY = theme.FONT_BODY
FONT_SUBTITLE = theme.FONT_SUBTITLE

BG_COLOR = theme.BG_COLOR
SIDEBAR_COLOR = theme.SIDEBAR_COLOR
CARD_COLOR = theme.CARD_COLOR
TEXT_COLOR = theme.TEXT_COLOR
SUB_TEXT_COLOR = theme.SUB_TEXT_COLOR
ACCENT_COLOR = theme.ACCENT_COLOR
DANGER_COLOR = theme.DANGER_COLOR
SUCCESS_COLOR = theme.SUCCESS_COLOR
WARNING_COLOR = theme.WARNING_COLOR



TRANSLATIONS = {
    "zh": {
        "welcome": "欢迎来到", "desc": "这是一款 真·个性化 大学生期末复习平台", "start": "开启复习之旅",
        "how_call": "怎么称呼您？", "name_ph": "请输入您的名字", "next": "→", "back": "←",
        "manual_title": "使用说明",
        "manual_text": "1. 新建科目，输入考试信息与目标分数。\n2. 上传你的 PPT、PDF 或 Word 资料。\n3. 选择保命/硬核模式，AI 将为你生成专属讲义。\n4. 在讲义中点击名词查看解释，一键导出 PDF。\n\n注意：开启复习之旅后，将不会再出现引导页面。",
        "welcome_back": "欢迎回来，{}！", "new_task": "+ 新建科目", "delete_mode": "🗑️ 删除模式",
        "exit_delete": "退出删除", "no_course": "暂无科目，请点击新建",
        "today_motto": "今日寄语", "urgency": "紧迫度",
        "change_info": "更改资料 / 参数", "gen_guide": "🚀 生成讲义", "review": "📚 复习模式",
        "note": "📝 自定义笔记", "all_files": "📁 全部资料", "error": "错误", "ok": "确定",
        "course_name": "课程名称", "major": "专业",
        "school": "学校层级 (影响基础难度评估)", "credits": "学分 (学分越高，复习价值越大)",
        "is_major": "是否专业课 (专业课权重更高)", "difficulty": "自估难度 (你对该课的主观感觉)",
        "target": "目标分数 (目标越高，所需时间越多)", "days": "剩余天数 (越少越紧迫)",
        "upload_title": "上传资料", "finish_save": "完成并保存", "select_file": "点击选择文件",
        "upload_core": "核心重点 (老师划重点/真题，必填)", "upload_ref": "参考资料 (教材/课件，选填)",
        "weight_title": "⚖️ 核心/参考资料权重比例", "weight_desc": "决定 AI 参考哪边更多 (默认 核心8 : 参考2)",
        "mode_select": "讲义生成模式", "persona_select": "选择你的 AI 导师人设 (影响讲解风格)",
        "lang_select": "🌐 讲义语言",
        "full_mode": "全量讲义\n(适合时间充裕，想学透原理，内容详尽)",
        "key_mode": "精简讲义\n(适合时间紧迫，只讲核心拿分套路，大白话)",
        "history_guide": "📄 历史生成记录：", "no_history": "暂无历史记录",
        "gen_ing": "生成中...", "gen_success": "生成成功！", "preview": "🎉 文档已生成完毕",
        "open_edge": "🌐 在 Edge 中打开", "export_pdf": "🖨️ 导出为 PDF",
        "print_tips": "已经为您打开网页，请点击网页右上角的【🖨️ 导出 / 打印 PDF】即可导出！",
        "warn_safe": "✅ 时间充裕：按部就班推进即可。建议深挖原理冲击高分。",
        "warn_danger": "🚨 预警：复习时间紧张！为了保命拿分，强烈建议选择【精简讲义】。",
        "review_menu_title": "📚 复习模式中心",
        "review_ai_analysis": "🧠 AI 逻辑分析", "review_ai_analysis_desc": "梳理知识脉络，生成思维导图或逻辑链",
        "review_extract": "🔍 资料提取", "review_extract_desc": "自动提取核心名词、考点、带解析的题目",
        "review_train": "📝 训练模式", "review_train_desc": "根据真题或模拟仿真，生成整套冲刺试卷",
        "select_materials": "请选择要分析的资料 (可多选)：",
        "mindmap": "思维导图 (Mermaid 流程图)", "text_logic": "文本逻辑链 (详细推导)",
        "extract_nouns": "名词解释", "extract_points": "核心考点", "extract_questions": "提取题目",
        "with_answer": "包含答案与解析", "without_answer": "仅生成纯题目",
        "num_sets": "生成套数：", "generate_btn": "🚀 开始生成",
        "do_not_leave": "⚠️ 生成中，请不要关闭或离开此页面！",
        "note_title": "📝 自定义笔记模式", "note_save": "保存笔记", "note_saved": "笔记已保存！",
        "all_files_title": "📁 全部资料归档", "file_type_guide": "专属讲义", "file_type_analysis": "逻辑分析",
        "file_type_extract": "资料提取", "file_type_exam": "训练试卷", "file_type_note": "自定义笔记",
        "is_exam_paper": "以上资料包含【历年真题】(解锁真题参考)",
        "train_difficulty": "难度等级：", "train_sets": "生成套数：",
        "paper_mode": "出题基准：", "paper_default": "AI 智能生成默认卷型", "paper_diy": "自定义题型结构",
        "paper_exam": "参考历年真题风格",
        "diy_score_tips": "当前总分：{} / 100 分",
        "diy_score_warn": "注意：您设置的总分为 {} 分，不是 100 分。确定要这样生成吗？",
        "stop_btn": "🛑 停止生成", "time_est": "预计剩余时间：{}",
        "train_type_title": "训练模式重点："
    },
    "en": {
        "welcome": "Welcome to", "desc": "Your Personalized Final Exam Prep Platform", "start": "Start Journey",
        "how_call": "What should we call you?", "name_ph": "Enter your name", "next": "→", "back": "←",
        "manual_title": "User Manual",
        "manual_text": "1. Create a subject.\n2. Upload PPT/PDF/Word.\n3. Choose mode for guide.\n4. Export to PDF.\n\nNote: Onboarding won't appear again.",
        "welcome_back": "Welcome back, {}!", "new_task": "+ New Subject", "delete_mode": "🗑️ Delete Mode",
        "exit_delete": "Exit Delete", "no_course": "No subjects, please create one",
        "today_motto": "Motto", "urgency": "Urgency",
        "change_info": "Change Info", "gen_guide": "🚀 Generate Guide", "review": "📚 Review Mode",
        "note": "📝 Custom Notes", "all_files": "📁 All Files", "error": "Error", "ok": "OK",
        "course_name": "Course Name", "major": "Major", "school": "School Level", "credits": "Credits",
        "is_major": "Is Major?", "difficulty": "Subjective Difficulty", "target": "Target Score", "days": "Days Left",
        "upload_title": "Upload Materials", "finish_save": "Save", "select_file": "Select File",
        "upload_core": "Core Materials", "upload_ref": "Reference Materials",
        "weight_title": "⚖️ Weight Ratio", "weight_desc": "Core vs Reference (Default 8:2)",
        "mode_select": "Guide Mode", "persona_select": "Select AI Persona",
        "lang_select": "🌐 Language",
        "full_mode": "Full Guide\n(Detailed content)", "key_mode": "Key Points\n(Quick scoring)",
        "history_guide": "📄 History:", "no_history": "No history",
        "gen_ing": "Generating...", "gen_success": "Success!", "preview": "🎉 Document Generated",
        "open_edge": "🌐 Open in Edge", "export_pdf": "🖨️ Export PDF",
        "print_tips": "Click the green button in the web page.",
        "warn_safe": "✅ Plenty of time.", "warn_danger": "🚨 Warning: Time is tight!",
        "review_menu_title": "📚 Review Mode Center",
        "review_ai_analysis": "🧠 Logic Analysis", "review_ai_analysis_desc": "Generate mindmaps",
        "review_extract": "🔍 Extraction", "review_extract_desc": "Extract nouns, points, questions",
        "review_train": "📝 Training Mode", "review_train_desc": "Generate mock exams",
        "select_materials": "Select materials:", "mindmap": "Mindmap", "text_logic": "Text Logic",
        "extract_nouns": "Nouns", "extract_points": "Key Points", "extract_questions": "Questions",
        "with_answer": "With Answers", "without_answer": "Without Answers",
        "num_sets": "Sets: ", "generate_btn": "🚀 Generate", "do_not_leave": "⚠️ Do not close!",
        "note_title": "📝 Custom Notes", "note_save": "Save Note", "note_saved": "Note Saved!",
        "all_files_title": "📁 All Files Archive", "file_type_guide": "Guide", "file_type_analysis": "Analysis",
        "file_type_extract": "Extraction", "file_type_exam": "Mock Exam", "file_type_note": "Note",
        "is_exam_paper": "Contains [Past Exam Papers]", "train_difficulty": "Difficulty: ", "train_sets": "Sets: ",
        "paper_mode": "Paper Base: ", "paper_default": "AI Default", "paper_diy": "DIY Structure",
        "paper_exam": "Ref Past Exam",
        "diy_score_tips": "Total: {} / 100", "diy_score_warn": "Total score is {}. Generate anyway?",
        "stop_btn": "🛑 Stop Generation", "time_est": "Est. time left: {}",
        "train_type_title": "Training Focus: "
    }
}

# 打包后 CWD 是 "/"，写相对路径会 PermissionError → 必须落用户数据目录
CONFIG_FILE = str(paths.data_dir() / "user_config.json")
LEGACY_CONFIG_FILES = [str(paths.project_root() / "user_config.json")]


class TermFinaleApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TermFinale")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(fg_color=BG_COLOR)

        setup_logging()
        migration = paths.migrate_legacy()
        install_exception_hooks(self)
        logger.info("启动 | {} | 迁移={}", paths.describe(), migration)
        init_db()

        if config.missing_keys():
            logger.warning("缺少 API Key：{}（可在设置页填写）", "、".join(config.missing_keys()))
        self.current_lang = "zh"
        self.user_name = self.load_user_config()
        self.history_courses = []
        self.user_motto = self.load_user_motto()

        self.current_view = "onboarding_1"
        self.view_args = {}
        self.is_delete_mode = False

        self.temp_data = {}
        self.temp_materials = []
        self.core_ratio = 0.8
        self.selected_materials = []
        self.diy_data = {}

        self.stop_event = threading.Event()
        self.start_time = 0
        self.materials_loaded = False

        self.load_history_from_db()

        if not self.user_name:
            self.show_onboarding_1()
        else:
            self.show_dashboard()

    def t(self, key):
        return TRANSLATIONS[self.current_lang].get(key, key)

    def toggle_language(self):
        self.current_lang = "en" if self.current_lang == "zh" else "zh"
        self.show_dashboard() if self.user_name else self.show_onboarding_1()

    def load_user_config(self):
        """读用户配置：优先用户数据目录，其次兼容源码目录（开发期）。"""
        for path in [CONFIG_FILE, *LEGACY_CONFIG_FILES]:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                return cfg.get("name", cfg.get("username", ""))
            except Exception as exc:  # noqa: BLE001
                logger.warning("读取用户配置失败 {}: {}", path, exc)
        return ""

    def load_user_motto(self):
        db = get_db_session()
        cfg = db.query(DBUserConfig).first()
        if not cfg: cfg = DBUserConfig(); db.add(cfg); db.commit()
        motto = cfg.motto
        db.close()
        return motto

    def clear_ui(self):
        for widget in self.winfo_children(): widget.destroy()
        self.lift()
        self.focus_force()

    def build_top_nav(self, show_back=False, back_command=None):
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(side="top", fill="x", padx=40, pady=20)
        if show_back and back_command:
            ctk.CTkButton(nav, text=self.t("back"), width=50, font=FONT_H2, fg_color="transparent",
                          text_color=TEXT_COLOR, hover_color="#E5E5E5", command=back_command).pack(side="left")
        ctk.CTkButton(nav, text="⚙ 设置", width=70, font=FONT_SUBTITLE, fg_color="transparent",
                      text_color=SUB_TEXT_COLOR, border_width=1, border_color="#E5E5E5",
                      hover_color="#E5E5E5", command=self.show_settings).pack(side="right", padx=(0, 8))
        ctk.CTkButton(nav, text="中 / EN", width=70, font=FONT_SUBTITLE, fg_color="transparent",
                      text_color=SUB_TEXT_COLOR, border_width=1, border_color=SUB_TEXT_COLOR, hover_color="#E5E5E5",
                      command=self.toggle_language).pack(side="right")

    def show_onboarding_1(self):
        self.current_view = "onboarding_1"
        self.clear_ui()
        self.build_top_nav()
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(center, text=self.t("welcome"), font=FONT_H2, text_color=SUB_TEXT_COLOR).pack(pady=(0, 10))
        ctk.CTkLabel(center, text="TermFinale", font=FONT_HUGE, text_color=ACCENT_COLOR).pack(pady=(0, 20))
        ctk.CTkLabel(center, text=self.t("desc"), font=FONT_H2, text_color=TEXT_COLOR).pack(pady=(0, 60))
        ctk.CTkButton(center, text=self.t("next"), font=FONT_H1, width=100, height=50, fg_color=ACCENT_COLOR,
                      command=self.show_onboarding_2).pack()

    def show_onboarding_2(self):
        self.current_view = "onboarding_2"
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_onboarding_1)
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(center, text=self.t("how_call"), font=FONT_H1, text_color=TEXT_COLOR).pack(pady=(0, 40))
        entry_name = ctk.CTkEntry(center, width=350, height=50, font=FONT_BODY, placeholder_text=self.t("name_ph"),
                                  fg_color=CARD_COLOR, border_color=SUB_TEXT_COLOR)
        entry_name.pack(pady=(0, 30))

        def next_step():
            name = entry_name.get().strip()
            if not name:
                entry_name.configure(border_color=DANGER_COLOR)
                return
            self.user_name = name
            saved = True
            try:
                os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump({"name": name}, f, ensure_ascii=False)
            except OSError as exc:
                saved = False
                logger.error("保存用户名失败 {}: {}", CONFIG_FILE, exc)
            self.show_onboarding_3()
            if not saved:
                Toast.show(self, "名字本次有效，但保存失败，下次启动需要重填", "warning", 5000)

        ctk.CTkButton(center, text=self.t("next"), font=FONT_H1, width=350, height=50, fg_color=ACCENT_COLOR,
                      command=next_step).pack()

    def show_onboarding_3(self):
        self.current_view = "onboarding_3"
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_onboarding_2)
        scroll = self._page_scroll()
        ctk.CTkLabel(scroll, text=self.t("manual_title"), font=FONT_H1, text_color=TEXT_COLOR).pack(pady=(10, 20))
        manual_box = ctk.CTkFrame(scroll, fg_color=CARD_COLOR, corner_radius=16, border_width=1, border_color="#E5E5E5")
        manual_box.pack(pady=(0, 30), fill="x", ipadx=30, ipady=30)
        ctk.CTkLabel(manual_box, text="😭 期末复习，你是否也面临这些问题？", font=FONT_H2, text_color=DANGER_COLOR).pack(
            anchor="w", padx=20, pady=(0, 10))
        ctk.CTkLabel(manual_box,
                     text="几百页的 PPT 不知从何看起；老师划的重点毫无逻辑；\n直接去问网页 AI，不仅字数超限，还经常胡编乱造、弄错公式；\n有些时候，甚至连基本的化学结构式、电路图都无法识别。",
                     font=FONT_BODY, text_color=SUB_TEXT_COLOR, justify="left").pack(anchor="w", padx=20, pady=(0, 20))
        ctk.CTkLabel(manual_box, text="✨ TermFinale 为解决这些痛点而生", font=FONT_H2, text_color=ACCENT_COLOR).pack(
            anchor="w", padx=20, pady=(0, 10))
        ctk.CTkLabel(manual_box, text="它不是简单的 AI 聊天框，而是全自动期末复习流水线。", font=FONT_BODY,
                     text_color=TEXT_COLOR).pack(anchor="w", padx=20, pady=(0, 20))
        ctk.CTkLabel(manual_box, text="📋 操作流程非常简单：", font=FONT_H2).pack(anchor="w", padx=20, pady=(0, 5))
        ctk.CTkLabel(manual_box,
                     text="第一步：导入你的杂乱课件 (PPT / PDF / Word)。\n第二步：填入你的基本情况，我们会为你生成完全个性化复习系统。\n第三步：选择一个喜欢的 AI 导师风格，坐等极美讲义生成。",
                     font=FONT_BODY, text_color=TEXT_COLOR, justify="left").pack(anchor="w", padx=40, pady=(0, 20))
        ctk.CTkLabel(manual_box, text="⚙️ 在你上传完成后，后台会做这些工作：", font=FONT_H2).pack(anchor="w", padx=20,
                                                                                                pady=(0, 5))
        ctk.CTkLabel(manual_box,
                     text="1. 本地深度解析：剔除冗余信息与排版乱码，自动抽离并保存核心配图。\n2. 多模态全学科识别：内置视觉大模型，可自动解析电路图、化学结构式、解剖图等复杂图表。\n3. 智能调度算法：根据剩余天数与目标分数，自动规划“保命流”或“硬核流”路线。\n4. AI 导师人设：五种不同风格（严谨教授、暴躁极客、温柔学姐等），适配不同学习习惯。\n5. 个性化组卷：打破只看不练的假象，AI 动态生成针对性变式题与全真模拟卷。",
                     font=FONT_BODY, text_color=TEXT_COLOR, justify="left").pack(anchor="w", padx=40, pady=(0, 20))
        ctk.CTkLabel(scroll, text="请注意：开启复习之旅后，将不再出现引导页面。", font=FONT_SUBTITLE,
                     text_color=SUB_TEXT_COLOR).pack(pady=(0, 10))
        ctk.CTkButton(scroll, text=self.t("next"), font=FONT_H1, width=350, height=50, fg_color=ACCENT_COLOR,
                      command=self.show_onboarding_4).pack(pady=20)

    def show_onboarding_4(self):
        self.current_view = "onboarding_4"
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_onboarding_3)
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(center, text=f"{self.t('welcome_back').format(self.user_name)}", font=FONT_HUGE,
                     text_color=TEXT_COLOR).pack(pady=(0, 50))
        ctk.CTkButton(center, text=self.t("start"), font=FONT_H1, width=300, height=60, fg_color=ACCENT_COLOR,
                      command=self.show_dashboard).pack(pady=(0, 30))

    # ------------------------------------------------------------------ #
    # 仪表盘
    # ------------------------------------------------------------------ #
    @staticmethod
    def _greeting() -> str:
        hour = datetime.datetime.now().hour
        if hour < 6:
            return "夜深了"
        if hour < 12:
            return "早上好"
        if hour < 18:
            return "下午好"
        return "晚上好"

    def _dashboard_stats(self) -> dict:
        courses = self.history_courses
        if not courses:
            return {"nearest_days": None, "nearest_name": "", "count": 0, "files": 0,
                    "avg_weight": 0.0, "suggest_daily": 0}
        db = get_db_session()
        try:
            files = db.query(DBGeneratedFile).count()
        finally:
            db.close()

        nearest = min(courses, key=lambda c: c["days_left"])
        weights, suggest = [], 0
        for c in courses:
            info = self._course_info(c)
            ev = info.evaluate()
            weights.append(ev["final_priority_weight"])
            if c["id"] == nearest["id"]:
                suggest = ev["suggested_daily_hours"]
        return {"nearest_days": nearest["days_left"], "nearest_name": nearest["name"],
                "count": len(courses), "files": files,
                "avg_weight": round(sum(weights) / len(weights), 1),
                "suggest_daily": suggest}

    @staticmethod
    def _course_info(course: dict) -> CourseInfo:
        return CourseInfo(name=course["name"], school_level=course["school"], major=course["major"],
                          is_core_major=course["is_major"], credits=course["credits"],
                          days_left=course["days_left"], target_score=course["target_score"],
                          user_difficulty=course["difficulty"])

    def _bind_click(self, widget, callback):
        widget.bind("<Button-1>", lambda _e: callback())
        for child in widget.winfo_children():
            self._bind_click(child, callback)

    def _course_card(self, parent, course: dict, index: int):
        info = self._course_info(course)
        ev = info.evaluate()
        tone = (theme.DANGER_COLOR if ev["status"] == "极度危险"
                else theme.WARNING_COLOR if ev["status"] == "时间紧迫" else theme.SUCCESS_COLOR)

        card = Card(parent, corner_radius=theme.RADIUS["md"])
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=theme.SPACE["lg"], pady=(theme.SPACE["md"], 0))
        ctk.CTkLabel(head, text=f"📚 {course['name']}", font=FONT_H2, text_color=TEXT_COLOR,
                     anchor="w").pack(side="left")
        ctk.CTkLabel(head, text=f"{ev['final_priority_weight']:.0f}", font=FONT_H2,
                     text_color=tone).pack(side="right")
        ctk.CTkLabel(card, text=f"剩余 {course['days_left']} 天 · 目标 {course['target_score']} 分 · "
                               f"{ev['status']}",
                     font=FONT_SUBTITLE, text_color=SUB_TEXT_COLOR, anchor="w").pack(
            fill="x", padx=theme.SPACE["lg"], pady=(2, 0))
        bar = ctk.CTkProgressBar(card, height=6, progress_color=tone,
                                 fg_color=theme.palette().surface_alt)
        bar.pack(fill="x", padx=theme.SPACE["lg"], pady=theme.SPACE["sm"])
        bar.set(min(1.0, ev["final_priority_weight"] / 100))
        ctk.CTkLabel(card, text=f"建议每天 {ev['suggested_daily_hours']:g} 小时",
                     font=FONT_SUBTITLE, text_color=SUB_TEXT_COLOR, anchor="w").pack(
            fill="x", padx=theme.SPACE["lg"], pady=(0, theme.SPACE["md"]))
        self._bind_click(card, lambda: self.show_course_actions(course, index))
        return card

    def show_dashboard(self):
        self.current_view = "dashboard"
        self.clear_ui()
        self.build_top_nav()

        # 侧栏
        sidebar = ctk.CTkFrame(self, width=250, fg_color=SIDEBAR_COLOR, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        ctk.CTkLabel(sidebar, text="TermFinale", font=FONT_H1, text_color=ACCENT_COLOR).pack(
            pady=(28, 18), padx=20, anchor="w")

        btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        if not self.is_delete_mode:
            PrimaryButton(btn_frame, text=self.t("new_task"),
                          command=lambda: self.show_course_setup(), height=38).pack(fill="x", pady=(0, 8))
            ctk.CTkButton(btn_frame, text=self.t("delete_mode"), font=FONT_BODY, height=32,
                          fg_color=theme.palette().surface_alt, text_color=DANGER_COLOR,
                          hover_color=theme.palette().border,
                          command=self.enter_delete_mode).pack(fill="x")
        else:
            ctk.CTkButton(btn_frame, text=self.t("exit_delete"), font=FONT_BODY, height=38,
                          fg_color=DANGER_COLOR, command=self.exit_delete_mode).pack(fill="x")

        self.sidebar_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.sidebar_list.pack(fill="both", expand=True, padx=8)
        self.render_history_list()

        # 主区
        main_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main_area.pack(side="right", fill="both", expand=True, padx=theme.SPACE["2xl"], pady=0)

        head = ctk.CTkFrame(main_area, fg_color="transparent")
        head.pack(fill="x", pady=(theme.SPACE["xl"], 0))
        ctk.CTkLabel(head, text=f"{self._greeting()}，{self.user_name}",
                     font=FONT_H1, text_color=TEXT_COLOR, anchor="w").pack(side="left")
        ctk.CTkLabel(head, text=datetime.datetime.now().strftime("%m月%d日"),
                     font=FONT_BODY, text_color=SUB_TEXT_COLOR).pack(side="right")

        motto = ctk.CTkFrame(main_area, fg_color="transparent")
        motto.pack(fill="x", pady=(theme.SPACE["xs"], theme.SPACE["lg"]))
        ctk.CTkLabel(motto, text=f"「 {self.user_motto} 」", font=FONT_BODY,
                     text_color=SUB_TEXT_COLOR).pack(side="left")
        GhostButton(motto, text="修改", command=self.edit_motto, height=26).pack(
            side="left", padx=theme.SPACE["sm"])

        if config.missing_keys():
            warning = Card(main_area, fg_color="#FFF6E5", border_color=theme.WARNING_COLOR)
            warning.pack(fill="x", pady=(0, theme.SPACE["lg"]))
            wleft = ctk.CTkFrame(warning, fg_color="transparent")
            wleft.pack(side="left", fill="x", expand=True, padx=theme.SPACE["lg"], pady=theme.SPACE["md"])
            ctk.CTkLabel(wleft, text="⚠️ 还没有配置 API Key，AI 功能暂时不可用",
                         font=FONT_BODY, text_color=TEXT_COLOR, anchor="w").pack(fill="x")
            ctk.CTkLabel(wleft, text="点右侧按钮填入 DeepSeek Key 即可开始生成（Key 只保存在本机）",
                         font=FONT_SUBTITLE, text_color=SUB_TEXT_COLOR, anchor="w").pack(fill="x")
            PrimaryButton(warning, text="去配置", command=self.show_settings, width=96).pack(
                side="right", padx=theme.SPACE["lg"])

        stats = self._dashboard_stats()
        if not stats["count"]:
            EmptyState(main_area, "📭", "还没有课程",
                       "点左侧「新建科目」，填一下考试信息就能开始").pack(pady=60)
            return

        tiles = ctk.CTkFrame(main_area, fg_color="transparent")
        tiles.pack(fill="x", pady=(0, theme.SPACE["lg"]))
        tones = ("danger" if (stats["nearest_days"] or 99) <= 3
                 else "warning" if (stats["nearest_days"] or 99) <= 7 else "success")
        for i, (label, value, hint, tone) in enumerate([
            ("最近考试", f"{stats['nearest_days']} 天", stats["nearest_name"], tones),
            ("在学课程", str(stats["count"]), f"平均紧迫度 {stats['avg_weight']:.0f}", "text"),
            ("已生成资料", str(stats["files"]), "讲义 / 试卷 / 笔记", "text"),
        ]):
            tile = StatTile(tiles, label, value, hint, tone)
            tile.pack(side="left", fill="both", expand=True, padx=(0 if i == 0 else theme.SPACE["md"], 0))
            tile.configure(width=260)

        SectionTitle(main_area, "课程概览", "点卡片进入操作").pack(fill="x", pady=(0, theme.SPACE["sm"]))
        visible = min(6, len(self.history_courses))
        for start in range(0, visible, 2):
            row = ctk.CTkFrame(main_area, fg_color="transparent")
            row.pack(fill="x", pady=(0, theme.SPACE["md"]))
            for offset in range(2):
                slot = start + offset
                if slot < visible:
                    card = self._course_card(row, self.history_courses[slot], slot)
                else:  # 奇数个课程时补一个透明占位，保持两栏等宽
                    card = ctk.CTkFrame(row, fg_color="transparent")
                card.pack(side="left", fill="both", expand=True,
                          padx=(0 if offset == 0 else theme.SPACE["md"], 0))

        advice = Card(main_area)
        advice.pack(fill="x", pady=(theme.SPACE["sm"], theme.SPACE["2xl"]))
        inner = ctk.CTkFrame(advice, fg_color="transparent")
        inner.pack(fill="x", padx=theme.SPACE["lg"], pady=theme.SPACE["lg"])
        ctk.CTkLabel(inner, text="🎯 今日建议", font=FONT_H2, text_color=TEXT_COLOR,
                     anchor="w").pack(fill="x")
        urgent = (stats["nearest_days"] or 99) <= 3
        lines = [
            f"离《{stats['nearest_name']}》只剩 {stats['nearest_days']} 天，"
            f"建议每天投入 {stats['suggest_daily']:g} 小时",
            "先出「精简讲义」只保必考，再刷 1 套模拟卷" if urgent
            else "先出「全量讲义」吃透原理，再用逻辑分析串成线",
            "做完题立刻在「训练模式」里对答案，错题记进笔记",
        ]
        for line in lines:
            ctk.CTkLabel(inner, text=f"· {line}", font=FONT_BODY, text_color=SUB_TEXT_COLOR,
                         anchor="w", justify="left", wraplength=760).pack(fill="x", pady=2)

    def show_settings(self):
        """API Key 设置页：首次启动与之后随时可进。"""
        self.current_view = "settings"
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        scroll = self._page_scroll()
        SectionTitle(scroll, "设置 · API Key",
                     "Key 只保存在本机用户数据目录，不会上传；换 Key 直接覆盖即可").pack(
            fill="x", pady=(10, 12))

        card = Card(scroll)
        card.pack(fill="x", pady=8)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.SPACE["xl"], pady=theme.SPACE["lg"])

        status = config.key_status()

        def add_field(label: str, name: str, hint: str):
            ctk.CTkLabel(inner, text=label, font=FONT_H2, text_color=TEXT_COLOR,
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(inner, text=hint, font=FONT_SUBTITLE, text_color=SUB_TEXT_COLOR,
                         anchor="w", wraplength=720, justify="left").pack(fill="x", pady=(2, 6))
            entry = ctk.CTkEntry(inner, show="•", width=520, font=FONT_BODY,
                                 placeholder_text="已配置，留空表示不修改" if status.get(name) else "sk-...")
            entry.pack(anchor="w", pady=(0, theme.SPACE["lg"]))
            return entry

        ds_entry = add_field("DeepSeek API Key（文本生成，必填）", "DEEPSEEK_API_KEY",
                             "在 platform.deepseek.com 创建。没有它无法生成讲义 / 提取 / 试卷。")
        qw_entry = add_field("阿里云百炼 API Key（图片说明，选填）", "DASHSCOPE_API_KEY",
                             "不填也能用，只是图片下方显示「第 N 页配图」。")

        result = ctk.CTkLabel(inner, text="", font=FONT_SUBTITLE, text_color=SUB_TEXT_COLOR,
                              anchor="w", wraplength=720, justify="left")
        result.pack(fill="x")

        def collect():
            return {"DEEPSEEK_API_KEY": ds_entry.get().strip() or config.get_key("DEEPSEEK_API_KEY"),
                    "DASHSCOPE_API_KEY": qw_entry.get().strip() or config.get_key("DASHSCOPE_API_KEY")}

        def save():
            entered = {"DEEPSEEK_API_KEY": ds_entry.get().strip(),
                       "DASHSCOPE_API_KEY": qw_entry.get().strip()}
            saved = [name for name, value in entered.items() if value]
            for name in saved:
                config.save_key(name, entered[name])
            if not config.get_key("DEEPSEEK_API_KEY"):
                result.configure(text="请先填写 DeepSeek Key（必填）", text_color=DANGER_COLOR)
                return
            Toast.show(self, "已保存", "success")
            self.show_dashboard()

        def clear():
            config.clear_key("DEEPSEEK_API_KEY")
            config.clear_key("DASHSCOPE_API_KEY")
            ds_entry.delete(0, "end")
            qw_entry.delete(0, "end")
            result.configure(text="已清除本机保存的 Key", text_color=SUB_TEXT_COLOR)

        def test():
            values = collect()
            if not values["DEEPSEEK_API_KEY"] and not values["DASHSCOPE_API_KEY"]:
                result.configure(text="请先填写 Key", text_color=DANGER_COLOR)
                return
            result.configure(text="测试中…", text_color=SUB_TEXT_COLOR)

            def work():
                from openai import OpenAI

                lines = []
                if values["DEEPSEEK_API_KEY"]:
                    try:
                        OpenAI(api_key=values["DEEPSEEK_API_KEY"],
                               base_url="https://api.deepseek.com").models.list()
                        lines.append("DeepSeek ✅")
                    except Exception as exc:  # noqa: BLE001
                        lines.append(f"DeepSeek ❌ {type(exc).__name__}")
                if values["DASHSCOPE_API_KEY"]:
                    try:
                        OpenAI(api_key=values["DASHSCOPE_API_KEY"],
                               base_url="https://dashscope.aliyuncs.com/compatible-mode/v1").models.list()
                        lines.append("百炼 ✅")
                    except Exception as exc:  # noqa: BLE001
                        lines.append(f"百炼 ❌ {type(exc).__name__}")
                self.after(0, lambda: result.configure(text=" · ".join(lines),
                                                       text_color=SUB_TEXT_COLOR))

            threading.Thread(target=work, daemon=True).start()

        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.pack(fill="x", pady=(theme.SPACE["md"], 0))
        PrimaryButton(btns, text="保存", command=save, width=110).pack(side="left")
        GhostButton(btns, text="测试连接", command=test, width=110).pack(side="left", padx=theme.SPACE["sm"])
        GhostButton(btns, text="清除本机 Key", command=clear, width=130).pack(side="left")
        GhostButton(btns, text="稍后配置", command=self.show_dashboard, width=110).pack(side="right")

    def edit_motto(self):
        dialog = ctk.CTkInputDialog(text="请输入新的励志名言：", title="修改名言")
        new_motto = dialog.get_input()
        if new_motto:
            db = get_db_session()
            cfg = db.query(DBUserConfig).first()
            cfg.motto = new_motto
            db.commit()
            db.close()
            self.user_motto = new_motto
            self.show_dashboard()

    def enter_delete_mode(self):
        self.is_delete_mode = True
        self.show_dashboard()

    def exit_delete_mode(self):
        self.is_delete_mode = False
        self.show_dashboard()

    def render_history_list(self):
        for widget in self.sidebar_list.winfo_children(): widget.destroy()
        if not self.history_courses:
            ctk.CTkLabel(self.sidebar_list, text=self.t("no_course"), text_color=SUB_TEXT_COLOR).pack(pady=20)
            return

        for idx, course in enumerate(self.history_courses):
            try:
                info = CourseInfo(name=course["name"], school_level=course["school"], major=course["major"],
                                  is_core_major=course["is_major"], credits=course["credits"],
                                  days_left=course["days_left"], target_score=course["target_score"],
                                  user_difficulty=course["difficulty"])
                ev = info.evaluate()
                score = int(ev['final_priority_weight'])
                s_color = DANGER_COLOR if ev['status'] == "极度危险" else (
                    SUCCESS_COLOR if ev['status'] == "安全充裕" else WARNING_COLOR)
            except:
                score, s_color = 0, TEXT_COLOR

            card = ctk.CTkFrame(self.sidebar_list, fg_color="#F9F9F9", corner_radius=8, border_width=1,
                                border_color="#E5E5E5")
            card.pack(fill="x", pady=5, padx=5, ipady=5)
            if self.is_delete_mode:
                card.configure(border_color=DANGER_COLOR, border_width=2)
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=5)
                ctk.CTkLabel(row, text=f"📚 {course['name']}", font=FONT_BODY, text_color=TEXT_COLOR).pack(side="left")
                ctk.CTkButton(row, text="✖", width=30, height=30, fg_color=DANGER_COLOR, hover_color="#C62828",
                              command=lambda i=idx: self.delete_course(i)).pack(side="right")
            else:
                btn = ctk.CTkButton(card, text=f"📚 {course['name']}", font=FONT_BODY, fg_color="transparent",
                                    text_color=TEXT_COLOR, hover_color="#E5E5E5", anchor="w",
                                    command=lambda c=course, i=idx: self.show_course_actions(c, i))
                btn.pack(fill="x", padx=10, pady=(5, 5))
                ctk.CTkLabel(card, text=f"{self.t('urgency')}: {score}分", font=FONT_SUBTITLE, text_color=s_color).pack(
                    anchor="w", padx=10, pady=(0, 5))

    def delete_course(self, index):
        course = self.history_courses[index]
        if not messagebox.askyesno(
                "删除课程",
                f"确定删除【{course['name']}】吗？\n\n"
                "只会删除本软件生成的讲义/试卷/笔记记录；\n"
                "你上传的原始课件不会被删除。"):
            return
        db = get_db_session()
        try:
            c = db.query(DBCourse).filter(DBCourse.id == course["id"]).first()
            if c:
                # 只清理由本软件生成的产物；materials.file_path 指向用户的原始文件，绝不能删
                for g in c.generated_files:
                    try:
                        if os.path.exists(g.file_path):
                            os.remove(g.file_path)
                    except OSError as exc:
                        logger.warning("删除生成物失败 {}: {}", g.file_path, exc)
                logger.info("删除课程 {}（保留 {} 份原始资料）", course["name"], len(c.materials))
                db.delete(c)
                db.commit()
            self.history_courses.pop(index)
            self.show_dashboard()
        except Exception as e:
            logger.error(e)
            db.rollback()
        finally:
            db.close()

    def show_course_actions(self, course, index):
        dialog = ctk.CTkToplevel(self)
        dialog.title(course["name"])
        dialog.geometry("450x620")
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color=BG_COLOR)
        center_x = self.winfo_x() + 375
        center_y = self.winfo_y() + 90
        dialog.geometry(f"+{center_x}+{center_y}")
        ctk.CTkLabel(dialog, text=course["name"], font=FONT_H1, text_color=TEXT_COLOR).pack(pady=(30, 5))
        ctk.CTkLabel(dialog, text=f"目标: {course['target_score']} | 剩余: {course['days_left']}天", font=FONT_BODY,
                     text_color=SUB_TEXT_COLOR).pack(pady=(0, 20))
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=(10, 20))

        def edit_action():
            self.materials_loaded = False
            dialog.destroy()
            self.show_course_setup(is_edit=True, index=index, course_data=course)

        ctk.CTkButton(btn_frame, text=self.t("change_info"), font=FONT_BODY, height=40, fg_color="#E5E5E5",
                      text_color=TEXT_COLOR, command=edit_action).pack(fill="x", pady=5)
        ctk.CTkButton(btn_frame, text=self.t("gen_guide"), font=FONT_BODY, height=40, fg_color=ACCENT_COLOR,
                      command=lambda: [dialog.destroy(), self.show_generation_mode_select(course, index)]).pack(
            fill="x", pady=5)
        ctk.CTkButton(btn_frame, text=self.t("review"), font=FONT_BODY, height=40, fg_color="#F0F8FF",
                      text_color=ACCENT_COLOR, border_width=1, border_color=ACCENT_COLOR,
                      command=lambda: [dialog.destroy(), self.show_review_menu(course, index)]).pack(fill="x", pady=5)
        ctk.CTkButton(btn_frame, text=self.t("note"), font=FONT_BODY, height=40, fg_color="transparent", border_width=1,
                      border_color="#E5E5E5", command=lambda: [dialog.destroy(), self.show_notes(course, index)]).pack(
            fill="x", pady=5)
        ctk.CTkButton(btn_frame, text=self.t("all_files"), font=FONT_BODY, height=40, fg_color="transparent",
                      border_width=1, border_color="#E5E5E5",
                      command=lambda: [dialog.destroy(), self.show_all_files(course, index)]).pack(fill="x", pady=5)

    def show_course_setup(self, is_edit=False, index=-1, course_data=None):
        self.current_view = "course_setup"
        self.view_args = {"is_edit": is_edit, "index": index, "course_data": course_data}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        scroll = self._page_scroll()
        form = ctk.CTkFrame(scroll, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#E5E5E5")
        form.pack(fill="x", pady=10, ipadx=20, ipady=20)

        def create_row(label, widget_type, options=None, default=""):
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", pady=10)
            ctk.CTkLabel(row, text=label, font=FONT_BODY, width=180, anchor="w").pack(side="left")
            if widget_type == "entry":
                w = ctk.CTkEntry(row, font=FONT_BODY, width=300)
                if default: w.insert(0, default)
                w.pack(side="left", padx=20)
                return w
            else:
                w = StyledOptionMenu(row, values=options, font=FONT_BODY, width=300)
                if default in options: w.set(default)
                w.pack(side="left", padx=20)
                return w

        self.entry_course = create_row(self.t("course_name"), "entry",
                                       default=course_data.get("name", "") if course_data else "")
        self.entry_major = create_row(self.t("major"), "entry",
                                      default=course_data.get("major", "") if course_data else "")
        self.school_menu = create_row(self.t("school"), "menu", ["985", "211", "普通一本", "普通二本", "专科"],
                                      default=course_data.get("school", "普通二本") if course_data else "普通二本")
        self.menu_credits = create_row(self.t("credits"), "menu", ["1.0", "2.0", "3.0", "4.0", "5.0", "6.0"],
                                       default=str(course_data.get("credits", "2.0")) if course_data else "2.0")
        self.menu_ismajor = create_row(self.t("is_major"), "menu", ["是", "否"],
                                       default="是" if course_data and course_data.get("is_major") else "否")
        self.menu_difficulty = create_row(self.t("difficulty"), "menu", ["1星", "2星", "3星", "4星", "5星"],
                                          default=f"{course_data.get('difficulty', 3)}星" if course_data else "3星")
        self.menu_score = create_row(self.t("target"), "menu", ["60", "70", "80", "90", "100"],
                                     default=str(course_data.get("target_score", "60")) if course_data else "60")
        days_options = [str(i) for i in range(1, 11)] + ["14", "21", "30", "45", "60", "90"]
        self.menu_days = create_row(self.t("days"), "menu", days_options,
                                    default=str(course_data.get("days_left", "7")) if course_data else "7")
        bottom = ctk.CTkFrame(scroll, fg_color="transparent")
        bottom.pack(fill="x", pady=30)
        ctk.CTkButton(bottom, text=self.t("next"), font=FONT_BODY, fg_color=ACCENT_COLOR, height=45,
                      command=lambda: self.handle_course_submit(is_edit, index)).pack(side="right")

    def handle_course_submit(self, is_edit, index):
        name = self.entry_course.get().strip()
        if not name: return
        data = {"name": name, "major": self.entry_major.get() or "未知", "school": self.school_menu.get(),
                "credits": float(self.menu_credits.get()), "is_major": self.menu_ismajor.get() == "是",
                "difficulty": int(self.menu_difficulty.get()[0]), "target_score": int(self.menu_score.get()),
                "days_left": int(self.menu_days.get()), "persona": "温柔小姐姐"}
        if is_edit:
            data["id"] = self.history_courses[index]["id"]
            self.show_upload_setup(course=data, index=index, is_edit=True)
        else:
            self.temp_data = data
            self.temp_materials = []
            self.materials_loaded = False
            self.show_upload_setup(course=self.temp_data, is_edit=False)

    def show_upload_setup(self, course=None, index=-1, is_edit=False):
        self.current_view = "upload_setup"
        self.view_args = {"course": course, "index": index, "is_edit": is_edit}

        if is_edit and not self.materials_loaded:
            self.temp_materials = []  # 防止反复进出编辑页时累加重复材料
            db = get_db_session()
            mats = db.query(DBMaterial).filter(DBMaterial.course_id == course["id"]).all()
            for m in mats:
                self.temp_materials.append({"id": m.id, "path": m.file_path, "type": m.file_type, "name": m.filename})
            db.close()
            self.materials_loaded = True

        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=lambda: self.show_course_setup(is_edit, index, course))
        self.upload_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.upload_scroll.pack(fill="both", expand=True, padx=60, pady=10)

        self.core_card = ctk.CTkFrame(self.upload_scroll, fg_color=CARD_COLOR, corner_radius=12, border_width=2, height=10,
                                      border_color=ACCENT_COLOR)
        self.core_card.pack(fill="x", pady=10, ipadx=20, ipady=20)
        ctk.CTkLabel(self.core_card, text=self.t("upload_core"), font=FONT_H2, text_color=ACCENT_COLOR).pack(anchor="w")
        ctk.CTkButton(self.core_card, text="+ " + self.t("select_file"), command=lambda: self.pick_file("core")).pack(
            pady=10)

        self.core_list_frame = ctk.CTkFrame(self.core_card, fg_color="transparent", height=10)
        self.core_list_frame.pack(fill="x")

        self.ref_card = ctk.CTkFrame(self.upload_scroll, fg_color=CARD_COLOR, corner_radius=12, border_width=1, height=10,
                                     border_color="#E5E5E5")
        self.ref_card.pack(fill="x", pady=10, ipadx=20, ipady=20)
        ctk.CTkLabel(self.ref_card, text=self.t("upload_ref"), font=FONT_H2).pack(anchor="w")
        ctk.CTkButton(self.ref_card, text="+ " + self.t("select_file"), command=lambda: self.pick_file("ref")).pack(
            pady=10)

        self.ref_list_frame = ctk.CTkFrame(self.ref_card, fg_color="transparent", height=10)
        self.ref_list_frame.pack(fill="x")

        self.weight_card = ctk.CTkFrame(self.upload_scroll, fg_color=CARD_COLOR, corner_radius=12, border_width=1, height=10,
                                        border_color="#E5E5E5")
        ctk.CTkLabel(self.weight_card, text=self.t("weight_title"), font=FONT_H2, text_color=ACCENT_COLOR).pack(
            anchor="w")
        ctk.CTkLabel(self.weight_card, text=self.t("weight_desc"), font=FONT_SUBTITLE, text_color=SUB_TEXT_COLOR).pack(
            anchor="w", pady=(0, 10))

        slider_frame = ctk.CTkFrame(self.weight_card, fg_color="transparent")
        slider_frame.pack(fill="x", pady=10)
        self.ratio_label = ctk.CTkLabel(slider_frame, text="核心 80% / 参考 20%", font=FONT_BODY, width=160)
        self.ratio_label.pack(side="left")

        def update_ratio(value):
            core_p = int(value * 100)
            ref_p = 100 - core_p
            self.core_ratio = value
            self.ratio_label.configure(text=f"核心 {core_p}% / 参考 {ref_p}%")

        self.weight_slider = ctk.CTkSlider(slider_frame, from_=0.0, to=1.0, number_of_steps=10, command=update_ratio)
        self.weight_slider.set(self.core_ratio)
        self.weight_slider.pack(side="left", fill="x", expand=True, padx=20)

        self.bottom_frame = ctk.CTkFrame(self.upload_scroll, fg_color="transparent")
        self.bottom_frame.pack(fill="x", pady=30)
        ctk.CTkButton(self.bottom_frame, text=self.t("finish_save"), font=FONT_BODY, fg_color=SUCCESS_COLOR, height=45,
                      command=lambda: self.finish_project(course, index, is_edit)).pack(side="right")

        self.refresh_material_ui()

    def refresh_material_ui(self):
        for widget in self.core_list_frame.winfo_children(): widget.destroy()
        for widget in self.ref_list_frame.winfo_children(): widget.destroy()

        for idx, m in enumerate(self.temp_materials):
            target_frame = self.core_list_frame if m["type"] == "core" else self.ref_list_frame
            row = ctk.CTkFrame(target_frame, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=2)
            ctk.CTkLabel(row, text=f"📄 {m['name']}", font=FONT_BODY, text_color=TEXT_COLOR).pack(side="left")

            def do_delete(event, target_m=m, target_row=row):
                if target_m in self.temp_materials:
                    self.temp_materials.remove(target_m)
                target_row.destroy()
                self.update_idletasks()
                self.check_weight_visibility()

            btn = ctk.CTkButton(row, text="✖ 移除", width=60, height=25, fg_color="transparent",
                                text_color=DANGER_COLOR)
            btn.pack(side="right")
            btn.bind("<Button-1>", do_delete)

        self.check_weight_visibility()

    def check_weight_visibility(self):
        has_core = any(m["type"] == "core" for m in self.temp_materials)
        has_ref = any(m["type"] == "ref" for m in self.temp_materials)

        self.weight_card.pack_forget()
        self.bottom_frame.pack_forget()

        self.bottom_frame.pack(fill="x", pady=30)

        if has_core and has_ref:
            self.weight_card.pack(fill="x", pady=10, ipadx=20, ipady=20, before=self.bottom_frame)
        elif has_core:
            self.core_ratio = 1.0
        elif has_ref:
            self.core_ratio = 0.0

    def pick_file(self, ftype):
        if len(self.temp_materials) >= 5:
            messagebox.showwarning("上传限制", "为了防止解析超时崩溃，单次最多只能上传 5 份资料！")
            return
        path = filedialog.askopenfilename(filetypes=[("Docs", "*.pptx *.pdf *.docx")])
        if path:
            self.temp_materials.append({"path": path, "type": ftype, "name": os.path.basename(path)})
            self.refresh_material_ui()

    def finish_project(self, course, index, is_edit=False):
        db_id = course.get("id") if is_edit else None
        db = get_db_session()
        try:
            if db_id:
                c = db.query(DBCourse).filter(DBCourse.id == db_id).first()
            else:
                c = DBCourse();
                db.add(c)
            c.name, c.major, c.school_level = course["name"], course["major"], course["school"]
            c.credits, c.days_left, c.target_score = course["credits"], course["days_left"], course["target_score"]
            c.user_difficulty, c.is_major, c.persona = course["difficulty"], course["is_major"], course["persona"]
            db.commit()
            if is_edit:
                db.query(DBMaterial).filter(DBMaterial.course_id == c.id).delete()
                db.commit()
            for m in self.temp_materials:
                db.add(DBMaterial(course_id=c.id, file_path=m["path"], file_type=m["type"], filename=m["name"]))
            db.commit()
            self.load_history_from_db()
            self.temp_materials = []
            self.show_dashboard()
        except Exception as e:
            logger.error(e);
            db.rollback()
        finally:
            db.close()

    def show_generation_mode_select(self, course, index):
        self.current_view = "mode_select"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        info = CourseInfo(name=course["name"], school_level=course["school"], major=course["major"],
                          is_core_major=course["is_major"], credits=course["credits"], days_left=course["days_left"],
                          target_score=course["target_score"], user_difficulty=course["difficulty"])
        ev = info.evaluate()
        is_danger = ev['final_priority_weight'] >= 75 or ev['status'] == "极度危险"

        scroll = self._page_scroll()

        ctk.CTkLabel(scroll, text=self.t("persona_select"), font=FONT_H2).pack(anchor="w", pady=(10, 5))
        persona_menu = StyledOptionMenu(scroll, values=list(PERSONA_LABELS.keys()),
                                         font=FONT_BODY, width=400)
        persona_menu.pack(anchor="w", pady=(0, 20))

        ctk.CTkLabel(scroll, text=self.t("lang_select"), font=FONT_H2).pack(anchor="w", pady=(10, 5))
        lang_menu = StyledOptionMenu(scroll, values=["中文", "English"], font=FONT_BODY, width=400)
        lang_menu.set("中文")
        lang_menu.pack(anchor="w", pady=(0, 30))

        warn_text = self.t("warn_danger") if is_danger else self.t("warn_safe")
        ctk.CTkLabel(scroll, text=warn_text, font=FONT_H2, text_color=(DANGER_COLOR if is_danger else SUCCESS_COLOR),
                     wraplength=800, justify="left").pack(anchor="w", pady=(0, 20))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)

        def start(mode):
            self.start_generation(course, index, mode, persona_from_label(persona_menu.get()), lang_menu.get())

        ctk.CTkButton(btn_frame, text=self.t("full_mode"), font=FONT_H2, width=300, height=100, fg_color=CARD_COLOR,
                      text_color=TEXT_COLOR, border_width=1, border_color="#E5E5E5",
                      command=lambda: start("full")).pack(side="left", padx=(0, 20))
        ctk.CTkButton(btn_frame, text=self.t("key_mode"), font=FONT_H2, width=300, height=100,
                      fg_color="#F0F8FF", text_color=ACCENT_COLOR, border_width=2,
                      border_color=ACCENT_COLOR, command=lambda: start("key")).pack(side="left")

        ctk.CTkLabel(scroll, text=self.t("history_guide"), font=FONT_H2).pack(anchor="w", pady=(40, 10))
        db = get_db_session()
        files = db.query(DBGeneratedFile).filter(DBGeneratedFile.course_id == course["id"],
                                                 DBGeneratedFile.file_type == "guide").order_by(
            DBGeneratedFile.id.desc()).all()
        db.close()
        if not files:
            ctk.CTkLabel(scroll, text=self.t("no_history"), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=20)
        else:
            for f in files:
                row = ctk.CTkFrame(scroll, fg_color=CARD_COLOR, corner_radius=8, border_width=1, border_color="#E5E5E5")
                row.pack(fill="x", pady=5)
                ctk.CTkLabel(row, text=f"📄 {os.path.basename(f.file_path)}", font=FONT_BODY).pack(side="left", padx=15,
                                                                                                  pady=10)
                ctk.CTkButton(row, text="打开", width=60, height=30, font=FONT_SUBTITLE, fg_color=ACCENT_COLOR,
                              text_color="#FFFFFF", command=lambda p=f.file_path: self.open_file(p)).pack(
                    side="right", padx=15)

    def start_generation(self, course, index, mode, persona, lang="中文"):
        if config.missing_keys():
            Toast.show(self, "请先在设置里配置 API Key", "warning", 3000)
            self.show_settings()
            return
        config_file = CONFIG_FILE
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        daily_limit = 20
        cfg = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except:
                pass
        usage = cfg.get("usage", {})
        if usage.get("date") != today_str: usage = {"date": today_str, "count": 0}
        if usage["count"] >= daily_limit:
            messagebox.showerror("内测限制", f"您今日的 AI 生成次数（{daily_limit}次）已用完，请明天再试！")
            return
        usage["count"] += 1
        cfg["usage"] = usage
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False)

        self.clear_ui()
        self.stop_event.clear()
        self.start_time = time.time()

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(center, text=self.t("gen_ing"), font=FONT_H1).pack(pady=(0, 20))
        self.progress_label = ctk.CTkLabel(center, text="🚀 正在初始化 AI 引擎...", font=FONT_H2,
                                           text_color=ACCENT_COLOR)
        self.progress_label.pack(pady=(0, 10))
        self.time_label = ctk.CTkLabel(center, text=self.t("time_est").format("计算中..."), font=FONT_SUBTITLE,
                                       text_color=SUB_TEXT_COLOR)
        self.time_label.pack(pady=(0, 10))
        self.progressbar = ctk.CTkProgressBar(center, width=400)
        self.progressbar.pack(pady=20)
        self.progressbar.set(0)
        ctk.CTkLabel(center, text=self.t("do_not_leave"), font=FONT_H2, text_color=DANGER_COLOR).pack(pady=(10, 10))
        ctk.CTkButton(center, text=self.t("stop_btn"), font=FONT_H2, fg_color=DANGER_COLOR,
                      command=self.stop_generation).pack(pady=10)

        threading.Thread(target=self.run_backend_task,
                         args=(course, index, mode, persona, self.core_ratio, lang)).start()

    def stop_generation(self):
        self.stop_event.set()
        messagebox.showinfo("已中断", "生成任务已停止，即将返回主页。")
        self.after(0, self.show_dashboard)

    def run_backend_task(self, course, index, mode, persona, core_ratio, lang):
        """线程入口：调用服务层生成讲义，进度由 _on_service_progress 桥接到主线程。"""
        try:
            result = guide_service.run_guide(
                course,
                mode=mode,
                persona=persona,
                core_ratio=core_ratio,
                lang=lang,
                on_progress=self._on_service_progress,
                stop_event=self.stop_event,
            )
        except Exception as exc:
            logger.error("讲义生成失败: {}", exc)
            if not self.stop_event.is_set():
                self.after(0, lambda: messagebox.showerror(self.t("error"), str(exc)))
                self.after(0, self.show_dashboard)
            return
        if result and not self.stop_event.is_set():
            self.after(0, lambda: self.show_preview_screen(result.output_path))

    def _show_progress_page(self, initial_text="🚀 正在准备数据与网络请求..."):
        """生成中页面（讲义与复习共用）。"""
        self.clear_ui()
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(center, text=self.t("gen_ing"), font=FONT_H1).pack(pady=(0, 20))
        self.progress_label = ctk.CTkLabel(center, text=initial_text, font=FONT_H2,
                                           text_color=ACCENT_COLOR)
        self.progress_label.pack(pady=(0, 10))
        self.time_label = ctk.CTkLabel(center, text=self.t("time_est").format("计算中..."),
                                       font=FONT_SUBTITLE, text_color=SUB_TEXT_COLOR)
        self.time_label.pack(pady=(0, 10))
        self._progress_started = time.time()
        self._eta_seconds = None
        self._tick_progress()
        self.progressbar = ctk.CTkProgressBar(center, width=400)
        self.progressbar.pack(pady=20)
        self.progressbar.set(0)
        ctk.CTkLabel(center, text=self.t("do_not_leave"), font=FONT_H2,
                     text_color=DANGER_COLOR).pack(pady=(10, 10))
        ctk.CTkButton(center, text=self.t("stop_btn"), font=FONT_H2, fg_color=DANGER_COLOR,
                      command=self.stop_generation).pack(pady=10)

    def _tick_progress(self):
        """每秒刷新计时，避免长时间只有"计算中..."像卡死。"""
        label = getattr(self, "time_label", None)
        try:
            if label is None or not label.winfo_exists():
                return
        except Exception:
            return
        elapsed = int(time.time() - getattr(self, "_progress_started", time.time()))
        eta = getattr(self, "_eta_seconds", None)
        remain = "估算中" if eta is None else f"{eta // 60:02d}:{eta % 60:02d}"
        try:
            label.configure(text=f"已用 {elapsed // 60:02d}:{elapsed % 60:02d} · 预计剩余 {remain}")
        except Exception:
            return
        self.after(1000, self._tick_progress)

    def _on_service_progress(self, event):
        """服务层回调（工作线程）→ 通过 after 回到主线程；控件已销毁时静默跳过。"""
        def apply():
            try:
                label = getattr(self, "progress_label", None)
                if label is not None and label.winfo_exists():
                    label.configure(text=event.message)
                bar = getattr(self, "progressbar", None)
                if bar is not None and bar.winfo_exists():
                    bar.set(max(0.0, min(1.0, event.value)))
                if event.eta_seconds is not None:
                    self._eta_seconds = event.eta_seconds
            except Exception:  # 控件销毁/窗口关闭，属正常竞态
                pass

        self.after(0, apply)

    def _page_scroll(self, width: int = 860):
        """居中定宽的页面容器：宽屏下内容不会全挤在左侧。"""
        holder = ctk.CTkFrame(self, fg_color="transparent")
        holder.pack(fill="both", expand=True)
        scroll = ctk.CTkScrollableFrame(holder, fg_color="transparent", width=width)
        scroll.pack(fill="y", expand=True, pady=10)
        return scroll

    def _action_card(self, parent, title: str, desc: str, command):
        """整行可点的功能卡：标题 + 说明 + 进入按钮（修掉窄卡片文字被裁）。"""
        card = Card(parent)
        card.pack(fill="x", pady=theme.SPACE["xs"])
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=theme.SPACE["lg"], pady=theme.SPACE["md"])
        ctk.CTkLabel(left, text=title, font=FONT_H2, text_color=TEXT_COLOR, anchor="w").pack(fill="x")
        ctk.CTkLabel(left, text=desc, font=FONT_SUBTITLE, text_color=SUB_TEXT_COLOR, anchor="w",
                     justify="left", wraplength=720).pack(fill="x")
        GhostButton(card, text="进入 →", command=command, width=84).pack(side="right", padx=theme.SPACE["lg"])
        return card

    def show_review_menu(self, course, index):
        self.current_view = "review_menu"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        scroll = self._page_scroll()
        ctk.CTkLabel(scroll, text=self.t("review_menu_title"), font=FONT_H1).pack(anchor="w", pady=(10, 30))
        self._action_card(scroll, self.t("review_ai_analysis"), self.t("review_ai_analysis_desc"),
                          lambda: self.show_ai_analysis(course, index))
        self._action_card(scroll, self.t("review_extract"), self.t("review_extract_desc"),
                          lambda: self.show_extract(course, index))
        self._action_card(scroll, self.t("review_train"), self.t("review_train_desc"),
                          lambda: self.show_training(course, index))

        ctk.CTkLabel(scroll, text=self.t("history_guide"), font=FONT_H2).pack(anchor="w", pady=(20, 10))
        db = get_db_session()
        files = db.query(DBGeneratedFile).filter(DBGeneratedFile.course_id == course["id"],
                                                 DBGeneratedFile.file_type != "guide").order_by(
            DBGeneratedFile.id.desc()).all()
        db.close()
        if not files:
            ctk.CTkLabel(scroll, text=self.t("no_history"), text_color=SUB_TEXT_COLOR).pack(anchor="w", padx=20)
        else:
            for f in files:
                row = ctk.CTkFrame(scroll, fg_color=CARD_COLOR, corner_radius=8, border_width=1, border_color="#E5E5E5")
                row.pack(fill="x", pady=5)
                type_name = {"analysis": "🧠 逻辑分析", "extract": "🔍 资料提取", "exam": "📝 试卷"}.get(f.file_type,
                                                                                                      "文档")
                ctk.CTkLabel(row, text=f"{type_name} | {os.path.basename(f.file_path)}", font=FONT_BODY).pack(
                    side="left", padx=15, pady=10)
                ctk.CTkButton(row, text="打开", width=60, height=30, font=FONT_SUBTITLE, fg_color=ACCENT_COLOR,
                              text_color="#FFFFFF", command=lambda p=f.file_path: self.open_file(p)).pack(
                    side="right", padx=15)

    def render_material_checkboxes(self, parent, course_id):
        ctk.CTkLabel(parent, text=self.t("select_materials"), font=FONT_H2).pack(anchor="w", pady=(10, 5))
        db = get_db_session()
        mats = db.query(DBMaterial).filter(DBMaterial.course_id == course_id).all()
        db.close()
        self.selected_materials = []
        for m in mats:
            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(parent, text=f"📄 {m.filename}", variable=var, font=FONT_BODY).pack(anchor="w", padx=20,
                                                                                               pady=5)
            self.selected_materials.append((m, var))

    def get_selected_texts(self):
        texts = []
        for m, var in self.selected_materials:
            if var.get():
                pages = extract_text_from_file(m.file_path)
                texts.extend(pages)
        return "\n\n".join(texts)

    def show_ai_analysis(self, course, index):
        self.current_view = "ai_analysis"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=lambda: self.show_review_menu(course, index))
        scroll = self._page_scroll()
        SectionTitle(scroll, self.t("review_ai_analysis"), "一次生成：知识图谱 + 因果链 + 对照表").pack(fill="x", pady=(10, 8))
        self.render_material_checkboxes(scroll, course["id"])
        ctk.CTkLabel(scroll, text="一次生成：知识图谱 + 因果链 + 概念对照表（图与文在同一页，互补而非二选一）",
                     font=FONT_BODY, text_color=SUB_TEXT_COLOR, wraplength=780,
                     justify="left").pack(anchor="w", pady=(20, 20))

        def start():
            text = self.get_selected_texts()
            if not text: messagebox.showerror(self.t("error"), "请勾选有效资料！"); return
            self.run_generation_task(course, index, "analysis", text, mode="bundle")

        ctk.CTkButton(scroll, text=self.t("generate_btn"), font=FONT_H2, height=50, fg_color=ACCENT_COLOR,
                      command=start).pack(anchor="e", pady=30, padx=60)

    def show_extract(self, course, index):
        self.current_view = "extract"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=lambda: self.show_review_menu(course, index))
        scroll = self._page_scroll()
        SectionTitle(scroll, self.t("review_extract"), "按页提取，自动去重并报告覆盖率").pack(fill="x", pady=(10, 8))
        self.render_material_checkboxes(scroll, course["id"])
        ctk.CTkLabel(scroll, text="提取内容：", font=FONT_H2).pack(anchor="w", pady=(20, 5))
        type_var = ctk.StringVar(value="nouns")
        ctk.CTkRadioButton(scroll, text=self.t("extract_nouns"), variable=type_var, value="nouns", font=FONT_BODY).pack(
            anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(scroll, text=self.t("extract_points"), variable=type_var, value="points",
                           font=FONT_BODY).pack(anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(scroll, text=self.t("extract_questions"), variable=type_var, value="questions",
                           font=FONT_BODY).pack(anchor="w", padx=20, pady=5)
        ans_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(scroll, text=self.t("with_answer"), variable=ans_var, font=FONT_BODY).pack(anchor="w", padx=40,
                                                                                                   pady=10)

        def start():
            text = self.get_selected_texts()
            if not text: messagebox.showerror(self.t("error"), "请勾选有效资料！"); return
            self.run_generation_task(course, index, "extract", text, extract_type=type_var.get(),
                                     with_answer=ans_var.get())

        ctk.CTkButton(scroll, text=self.t("generate_btn"), font=FONT_H2, height=50, fg_color=ACCENT_COLOR,
                      command=start).pack(anchor="e", pady=30, padx=60)

    def show_training(self, course, index):
        self.current_view = "training"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=lambda: self.show_review_menu(course, index))
        scroll = self._page_scroll()
        SectionTitle(scroll, self.t("review_train"), "按目标分出卷，生成后自动验卷").pack(fill="x", pady=(10, 8))
        self.render_material_checkboxes(scroll, course["id"])

        is_exam_paper_var = ctk.BooleanVar(value=False)
        paper_mode_var = ctk.StringVar(value="default")

        train_focus_var = ctk.StringVar(value="mock")

        ctk.CTkLabel(scroll, text=self.t("paper_mode"), font=FONT_H2).pack(anchor="w", pady=(10, 5))
        rb_default = ctk.CTkRadioButton(scroll, text=self.t("paper_default"), variable=paper_mode_var, value="default",
                                        font=FONT_BODY)
        rb_default.pack(anchor="w", padx=20, pady=5)
        rb_diy = ctk.CTkRadioButton(scroll, text=self.t("paper_diy"), variable=paper_mode_var, value="diy",
                                    font=FONT_BODY)
        rb_diy.pack(anchor="w", padx=20, pady=5)

        diy_frame = ctk.CTkFrame(scroll, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#E5E5E5")

        def build_diy_ui():
            for widget in diy_frame.winfo_children(): widget.destroy()
            self.diy_data = {}
            types = ["单选题", "多选题", "判断题", "填空题", "名词解释", "简答题", "计算题", "证明题", "推论题",
                     "综合题"]
            score_label = ctk.CTkLabel(diy_frame, text=self.t("diy_score_tips").format(0), font=FONT_H2,
                                       text_color=ACCENT_COLOR)
            score_label.pack(anchor="w", padx=20, pady=(15, 5))

            def calc_score(*args):
                total = 0
                for q_type, data in self.diy_data.items():
                    if data["check_var"].get():
                        try:
                            total += int(data["qty_entry"].get() or 0) * float(data["score_entry"].get() or 0)
                        except:
                            pass
                score_label.configure(text=self.t("diy_score_tips").format(total),
                                      text_color=(SUCCESS_COLOR if total == 100 else DANGER_COLOR))

            header = ctk.CTkFrame(diy_frame, fg_color="transparent")
            header.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(header, text="题型", font=FONT_SUBTITLE, width=100).pack(side="left")
            ctk.CTkLabel(header, text="数量", font=FONT_SUBTITLE, width=80).pack(side="left", padx=10)
            ctk.CTkLabel(header, text="单题分值", font=FONT_SUBTITLE, width=80).pack(side="left")
            for q_type in types:
                row = ctk.CTkFrame(diy_frame, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=5)
                check_var = ctk.BooleanVar(value=False)
                cb = ctk.CTkCheckBox(row, text=q_type, variable=check_var, font=FONT_BODY, width=100,
                                     command=calc_score)
                cb.pack(side="left")
                qty_entry = ctk.CTkEntry(row, width=80, placeholder_text="数量")
                qty_entry.pack(side="left", padx=10)
                qty_entry.bind("<KeyRelease>", calc_score)
                score_entry = ctk.CTkEntry(row, width=80, placeholder_text="分值")
                score_entry.pack(side="left")
                score_entry.bind("<KeyRelease>", calc_score)
                self.diy_data[q_type] = {"check_var": check_var, "qty_entry": qty_entry, "score_entry": score_entry}

        def toggle_diy():
            if paper_mode_var.get() == "diy":
                diy_frame.pack(fill="x", padx=40, pady=15);
                build_diy_ui()
            else:
                diy_frame.pack_forget()

        rb_default.configure(command=toggle_diy)
        rb_diy.configure(command=toggle_diy)

        focus_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        focus_frame.pack(fill="x", pady=10)

        ctk.CTkCheckBox(scroll, text=self.t("is_exam_paper"), variable=is_exam_paper_var,
                        font=(FONT_FAMILY, 14, "bold"), text_color=ACCENT_COLOR).pack(anchor="w", padx=0, pady=(10, 10))

        def rebuild_focus_ui():
            for w in focus_frame.winfo_children(): w.destroy()
            ctk.CTkLabel(focus_frame, text=self.t("train_type_title"), font=FONT_H2).pack(anchor="w", pady=(0, 5))

            if is_exam_paper_var.get():
                ctk.CTkRadioButton(focus_frame, text="原题改数练习 (保持背景，只改数字)", variable=train_focus_var,
                                   value="original", font=FONT_BODY).pack(anchor="w", padx=20, pady=5)
                ctk.CTkRadioButton(focus_frame, text="原题变式练习 (改变设问角度)", variable=train_focus_var,
                                   value="variant", font=FONT_BODY).pack(anchor="w", padx=20, pady=5)
                ctk.CTkRadioButton(focus_frame, text="模拟练习 (全新模拟期末难度)", variable=train_focus_var,
                                   value="mock", font=FONT_BODY).pack(anchor="w", padx=20, pady=5)
                ctk.CTkRadioButton(focus_frame, text="预测仿真 (高频考点冲刺押题)", variable=train_focus_var,
                                   value="predict", font=FONT_BODY).pack(anchor="w", padx=20, pady=5)
                train_focus_var.set("original")
            else:
                ctk.CTkRadioButton(focus_frame, text="模拟练习 (全新模拟期末难度)", variable=train_focus_var,
                                   value="mock", font=FONT_BODY).pack(anchor="w", padx=20, pady=5)
                ctk.CTkRadioButton(focus_frame, text="预测仿真 (高频考点冲刺押题)", variable=train_focus_var,
                                   value="predict", font=FONT_BODY).pack(anchor="w", padx=20, pady=5)
                train_focus_var.set("mock")

        is_exam_paper_var.trace_add("write", lambda *args: rebuild_focus_ui())
        rebuild_focus_ui()

        row3 = ctk.CTkFrame(scroll, fg_color="transparent")
        row3.pack(anchor="w", pady=10)
        ctk.CTkLabel(row3, text=self.t("train_difficulty"), font=FONT_H2).pack(side="left")
        diff_var = StyledOptionMenu(row3,
                                     values=["1星 (基础)", "2星 (中等)", "3星 (常规期末)", "4星 (拔高)", "5星 (地狱)"],
                                     font=FONT_BODY)
        diff_var.set("3星 (常规期末)")
        diff_var.pack(side="left", padx=10)

        row4 = ctk.CTkFrame(scroll, fg_color="transparent")
        row4.pack(anchor="w", pady=10)
        ctk.CTkLabel(row4, text=self.t("train_sets"), font=FONT_H2).pack(side="left")
        sets_var = StyledOptionMenu(row4, values=["1", "2", "3", "4", "5"], font=FONT_BODY)
        sets_var.set("1")
        sets_var.pack(side="left", padx=10)

        ctk.CTkLabel(scroll, text=self.t("lang_select"), font=FONT_H2).pack(anchor="w", pady=(10, 5))
        train_lang_menu = StyledOptionMenu(scroll, values=["中文", "English"], font=FONT_BODY, width=400)
        train_lang_menu.set("中文")
        train_lang_menu.pack(anchor="w", pady=(0, 20))

        def start():
            text = self.get_selected_texts()
            if not text: messagebox.showerror(self.t("error"), "请勾选有效资料！"); return
            diff_val = int(diff_var.get()[0])
            diy_config = ""
            if paper_mode_var.get() == "diy":
                parts = []
                total_score = 0
                for q_type, data in self.diy_data.items():
                    if data["check_var"].get():
                        try:
                            qty = int(data["qty_entry"].get() or 0)
                            sc = float(data["score_entry"].get() or 0)
                            if qty > 0 and sc > 0:
                                parts.append(f"{q_type} {qty} 道，每题 {sc} 分")
                                total_score += qty * sc
                        except:
                            pass
                if not parts: messagebox.showwarning("提示", "您选择了自定义试卷，但没有勾选任何有效题型与数量！"); return
                if total_score != 100 and not messagebox.askyesno("分值警告",
                                                                  self.t("diy_score_warn").format(total_score)): return
                diy_config = "、".join(parts) + f"。总分 {total_score} 分。"

            u_ctx = {"target_score": course["target_score"], "school_level": course["school"],
                     "is_major": course["is_major"]}
            self.run_generation_task(course, index, "exam", text, train_type=train_focus_var.get(),
                                     num_sets=int(sets_var.get()), difficulty=diff_val, diy_config=diy_config,
                                     user_context=u_ctx, lang=train_lang_menu.get())

        ctk.CTkButton(scroll, text=self.t("generate_btn"), font=FONT_H2, height=50, fg_color=ACCENT_COLOR,
                      command=start).pack(anchor="e", pady=30, padx=60)

    def run_generation_task(self, course, index, task_type, text, **kwargs):
        if config.missing_keys():
            Toast.show(self, "请先在设置里配置 API Key", "warning", 3000)
            self.show_settings()
            return
        """线程入口：调用复习服务，UI 只负责展示进度。"""
        self.stop_event.clear()
        self.start_time = time.time()
        self._show_progress_page()

        def task():
            try:
                result = review_service.run_review(
                    course,
                    task_type,
                    text,
                    extract_type=kwargs.get("extract_type"),
                    with_answer=kwargs.get("with_answer", True),
                    mode=kwargs.get("mode", "mindmap"),
                    train_type=kwargs.get("train_type"),
                    num_sets=kwargs.get("num_sets", 1),
                    difficulty=kwargs.get("difficulty", 3),
                    diy_config=kwargs.get("diy_config", ""),
                    user_context=kwargs.get("user_context"),
                    lang=kwargs.get("lang", "中文"),
                    on_progress=self._on_service_progress,
                    stop_event=self.stop_event,
                )
            except Exception as exc:
                logger.error("复习任务失败: {}", exc)
                if not self.stop_event.is_set():
                    self.after(0, lambda: messagebox.showerror(self.t("error"), str(exc)))
                    self.after(0, self.show_dashboard)
                return
            if result and not self.stop_event.is_set():
                self.after(0, lambda: self.show_preview_screen(result.output_path))

        threading.Thread(target=task, daemon=True).start()

    def show_notes(self, course, index):
        self.current_view = "notes"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        ctk.CTkLabel(self, text=self.t("note_title"), font=FONT_H1).pack(anchor="w", padx=60, pady=(20, 10))
        db = get_db_session()
        note_record = db.query(DBGeneratedFile).filter(DBGeneratedFile.course_id == course["id"],
                                                       DBGeneratedFile.file_type == "note").first()
        db.close()
        initial_text = ""
        if note_record and os.path.exists(note_record.file_path):
            with open(note_record.file_path, "r", encoding="utf-8") as f: initial_text = f.read()
        self.textbox = ctk.CTkTextbox(self, font=FONT_BODY, width=800, height=500, fg_color=CARD_COLOR,
                                      text_color=TEXT_COLOR)
        self.textbox.pack(padx=60, pady=10, fill="both", expand=True)
        self.textbox.insert("1.0", initial_text)

        def save_note():
            text_content = self.textbox.get("1.0", "end-1c")
            time_str = time.strftime("%m%d_%H%M", time.localtime())
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop): desktop = os.path.abspath(".")
            output_filename = os.path.join(desktop, f"{course['name']}_笔记_{time_str}.txt")
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(text_content)
            db = get_db_session()
            if note_record:
                old_note = db.query(DBGeneratedFile).filter(DBGeneratedFile.id == note_record.id).first()
                if old_note and os.path.exists(old_note.file_path) and old_note.file_path != output_filename: os.remove(
                    old_note.file_path)
                if old_note: old_note.file_path = output_filename; old_note.created_at = time_str
            else:
                db.add(DBGeneratedFile(course_id=course["id"], file_path=output_filename, created_at=time_str,
                                       file_type="note"))
            db.commit()
            db.close()
            Toast.show(self, self.t("note_saved"), "success")

        ctk.CTkButton(self, text=self.t("note_save"), font=FONT_H2, height=45, fg_color=SUCCESS_COLOR,
                      command=save_note).pack(pady=20)

    def show_all_files(self, course, index):
        self.current_view = "all_files"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        scroll = self._page_scroll()
        ctk.CTkLabel(scroll, text=self.t("all_files_title"), font=FONT_H1).pack(anchor="w", pady=(10, 30))
        db = get_db_session()
        files = db.query(DBGeneratedFile).filter(DBGeneratedFile.course_id == course["id"]).order_by(
            DBGeneratedFile.id.desc()).all()
        db.close()
        if not files:
            ctk.CTkLabel(scroll, text="暂无任何生成资料", text_color=SUB_TEXT_COLOR).pack(pady=20)
            return
        grouped = {"guide": [], "analysis": [], "extract": [], "exam": [], "note": []}
        for f in files:
            if f.file_type in grouped: grouped[f.file_type].append(f)
        type_names = {"guide": self.t("file_type_guide"), "analysis": self.t("file_type_analysis"),
                      "extract": self.t("file_type_extract"), "exam": self.t("file_type_exam"),
                      "note": self.t("file_type_note")}
        for ftype, f_list in grouped.items():
            if not f_list: continue
            ctk.CTkLabel(scroll, text=type_names[ftype], font=FONT_H2, text_color=ACCENT_COLOR).pack(anchor="w",
                                                                                                     pady=(20, 10))
            for f in f_list:
                row = ctk.CTkFrame(scroll, fg_color=CARD_COLOR, corner_radius=8, border_width=1, border_color="#E5E5E5")
                row.pack(fill="x", pady=5)
                ctk.CTkLabel(row, text=f"📄 {os.path.basename(f.file_path)}", font=FONT_BODY).pack(side="left", padx=15,
                                                                                                  pady=10)

                def open_f(path=f.file_path):
                    open_path(path)

                ctk.CTkButton(row, text="打开", width=60, height=30, font=FONT_SUBTITLE, fg_color=ACCENT_COLOR,
                              text_color="#FFFFFF", command=open_f).pack(side="right", padx=15)

    def open_file(self, path):
        open_path(path)

    def show_preview_screen(self, html_path):
        self.current_view = "preview"
        self.view_args = {"html_path": html_path}
        self.clear_ui()
        self.build_top_nav()
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(center, text="🎉", font=("Arial", 60)).pack(pady=(0, 10))
        ctk.CTkLabel(center, text=self.t("preview"), font=FONT_H1).pack(pady=(0, 40))

        def open_and_print(): self.open_file(html_path); Toast.show(self, self.t("print_tips"), "info", duration=5000)

        btn_frame = ctk.CTkFrame(center, fg_color="transparent")
        btn_frame.pack()
        ctk.CTkButton(btn_frame, text=self.t("open_edge"), font=FONT_H2, width=260, height=55, fg_color=ACCENT_COLOR,
                      command=lambda: self.open_file(html_path)).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text=self.t("export_pdf"), font=FONT_H2, width=260, height=55, fg_color=SUCCESS_COLOR,
                      command=open_and_print).pack(side="left", padx=10)
        ctk.CTkButton(center, text=self.t("back"), font=FONT_BODY, width=100, fg_color="transparent",
                      text_color=SUB_TEXT_COLOR, command=self.show_dashboard).pack(pady=40)

    def load_history_from_db(self):
        self.history_courses = []
        db = get_db_session()
        for c in db.query(DBCourse).all():
            self.history_courses.append({
                "id": c.id, "name": c.name, "major": c.major, "school": c.school_level,
                "credits": c.credits, "is_major": c.is_major, "difficulty": c.user_difficulty,
                "target_score": c.target_score, "days_left": c.days_left, "persona": c.persona
            })
        db.close()


def run():
    """应用入口（launcher 与 PyInstaller 都调用这里）。"""
    app = TermFinaleApp()
    app.mainloop()


if __name__ == "__main__":
    run()