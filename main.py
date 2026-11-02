import customtkinter as ctk
import json
import os
import re
import threading
import time
import subprocess
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
from core import paths
from core.logger import setup_logging, install_exception_hooks

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

FONT_FAMILY = "PingFang SC"
FONT_HUGE = (FONT_FAMILY, 46, "bold")
FONT_H1 = (FONT_FAMILY, 26, "bold")
FONT_H2 = (FONT_FAMILY, 18, "bold")
FONT_BODY = (FONT_FAMILY, 14, "normal")
FONT_SUBTITLE = (FONT_FAMILY, 12, "normal")

BG_COLOR = "#F5F5F7"
SIDEBAR_COLOR = "#FFFFFF"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#1D1D1F"
SUB_TEXT_COLOR = "#86868B"
ACCENT_COLOR = "#007AFF"
DANGER_COLOR = "#FF3B30"
SUCCESS_COLOR = "#34C759"
WARNING_COLOR = "#FF9500"

OUTROS = {
    "zh": {
        "老师": "## 🎓 结语\n同学们，书山有路勤为径。这份讲义里浓缩了期末最核心的考点，老师能帮你们的就到这里了。剩下的路，需要你们自己去考场上走。不要怕，深呼吸，把这几天背的公式稳稳地写在卷子上。祝你们旗开得胜，老师等你们的好消息！",
        "学术AI": "## 🎓 结语\n数据解析完毕。当前讲义已包含通过最优算法提取的核心知识拓扑。请考生按照既定逻辑执行复习，避免非必要的情绪波动。预祝在即将到来的期末考试中，运算无误，得分最大化。",
        "暴力极客": "## 🎓 结语\n行了，能教的都教了！别再搁这儿磨叽了，赶紧把这些公式给我死死刻在脑子里！考场上遇到不会的，也给我把公式列上去蹭步骤分！少废话，滚去复习，明天干翻那张卷子！听懂没有？！",
        "温柔小姐姐": "## 🎓 结语\n宝宝，看到这里你真的已经很棒啦，辛苦了呢~🥺 复习是一件很枯燥的事情，但你一直坚持到了现在，姐姐真的很为你骄傲。今晚不要再熬夜啦，乖乖早点睡，把讲义里姐姐划的重点再看最后一眼。明天考试别紧张，你那么聪明，一定没问题的。姐姐会一直在你身后陪着你，等你的好消息哦~抱抱~🌸✨",
        "阳光小哥哥": "## 🎓 结语\n兄弟，能坚持看完这份讲义，你已经击败了80%的人。复习确实很累，但你要相信，你熬过的夜、刷过的题，都会变成卷子上的分数。别给自己太大压力，按我给你的步骤和套路来，稳扎稳打就行。去考场上放手一搏吧，别怕，有我在，你一定能行。祝你逢考必过！"
    },
    "en": {
        "老师": "## 🎓 Conclusion\nStudents, there is no royal road to learning. This guide contains the core exam points. I've done what I can. The rest is up to you. Don't be afraid, take a deep breath, and write those formulas steadily. Good luck!",
        "学术AI": "## 🎓 Conclusion\nData analysis complete. Core knowledge topology extracted. Proceed with your review as scheduled. Emotional fluctuations are unnecessary. Maximize your score. End of transmission.",
        "暴力极客": "## 🎓 Conclusion\nAlright, that's all I got! Stop dawdling and memorize these formulas! Even if you don't know the answer, write down the formulas for partial credit! Stop whining and go crush that exam!",
        "温柔小姐姐": "## 🎓 Conclusion\nDarling, you're doing amazing and working so hard~🥺 It's a tough journey, but I'm so proud of you. Get some sleep tonight, review my highlights one last time. Don't be nervous tomorrow, you're smart and you'll do great. I'm always here for you~ Hugs~🌸✨",
        "阳光小哥哥": "## 🎓 Conclusion\nBro, if you made it through this guide, you're already ahead of 80% of people. It's tiring, but your hard work will pay off. Don't stress, just follow my steps. Go out there and give it your all. I believe in you! You got this."
    }
}

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
        "is_exam_paper": "☑️ 以上资料包含【历年真题】 (解锁真题参考)",
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
        "is_exam_paper": "☑️ Contains [Past Exam Papers]", "train_difficulty": "Difficulty: ", "train_sets": "Sets: ",
        "paper_mode": "Paper Base: ", "paper_default": "AI Default", "paper_diy": "DIY Structure",
        "paper_exam": "Ref Past Exam",
        "diy_score_tips": "Total: {} / 100", "diy_score_warn": "Total score is {}. Generate anyway?",
        "stop_btn": "🛑 Stop Generation", "time_est": "Est. time left: {}",
        "train_type_title": "Training Focus: "
    }
}

CONFIG_FILE = "user_config.json"


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
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("name", cfg.get("username", ""))
            except:
                pass
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
            if not name: entry_name.configure(border_color=DANGER_COLOR); return
            self.user_name = name
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump({"name": name}, f, ensure_ascii=False)
            self.show_onboarding_3()

        ctk.CTkButton(center, text=self.t("next"), font=FONT_H1, width=350, height=50, fg_color=ACCENT_COLOR,
                      command=next_step).pack()

    def show_onboarding_3(self):
        self.current_view = "onboarding_3"
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_onboarding_2)
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=100, pady=10)
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

    def show_dashboard(self):
        self.current_view = "dashboard"
        self.clear_ui()
        self.build_top_nav()

        sidebar = ctk.CTkFrame(self, width=280, fg_color=SIDEBAR_COLOR, corner_radius=0, border_width=1,
                               border_color="#E5E5E5")
        sidebar.pack(side="left", fill="y")

        ctk.CTkLabel(sidebar, text="TermFinale", font=FONT_H1, text_color=ACCENT_COLOR).pack(pady=(30, 20), padx=20,
                                                                                             anchor="w")
        btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        if not self.is_delete_mode:
            ctk.CTkButton(btn_frame, text=self.t("new_task"), font=FONT_H2, height=40, fg_color=ACCENT_COLOR,
                          command=lambda: self.show_course_setup()).pack(fill="x", pady=(0, 10))
            ctk.CTkButton(btn_frame, text=self.t("delete_mode"), font=FONT_BODY, height=35, fg_color="#FFEBEE",
                          text_color=DANGER_COLOR, hover_color="#FFCDD2", command=self.enter_delete_mode).pack(fill="x")
        else:
            ctk.CTkButton(btn_frame, text=self.t("exit_delete"), font=FONT_H2, height=40, fg_color=DANGER_COLOR,
                          command=self.exit_delete_mode).pack(fill="x")

        self.sidebar_list = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.sidebar_list.pack(fill="both", expand=True, padx=10)
        self.render_history_list()

        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.pack(side="right", fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(main_area, text=self.t("welcome_back").format(self.user_name), font=FONT_HUGE,
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(40, 10))
        motto_frame = ctk.CTkFrame(main_area, fg_color="transparent")
        motto_frame.pack(anchor="w", pady=(0, 40))
        ctk.CTkLabel(motto_frame, text=f"「 {self.user_motto} 」", font=FONT_H2, text_color=SUB_TEXT_COLOR).pack(
            side="left")
        ctk.CTkButton(motto_frame, text="⚙️", width=30, height=30, fg_color="transparent", hover_color="#E5E5E5",
                      text_color=SUB_TEXT_COLOR, command=self.edit_motto).pack(side="left", padx=10)

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
        if not messagebox.askyesno(self.t("error"), f"确定删除【{course['name']}】吗？"): return
        db = get_db_session()
        try:
            c = db.query(DBCourse).filter(DBCourse.id == course["id"]).first()
            if c:
                for m in c.materials:
                    if os.path.exists(m.file_path): os.remove(m.file_path)
                for g in c.generated_files:
                    if os.path.exists(g.file_path): os.remove(g.file_path)
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
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=100, pady=10)
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
                w = ctk.CTkOptionMenu(row, values=options, font=FONT_BODY, width=300)
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
            db = get_db_session()
            mats = db.query(DBMaterial).filter(DBMaterial.course_id == course["id"]).all()
            for m in mats:
                self.temp_materials.append({"id": m.id, "path": m.file_path, "type": m.file_type, "name": m.filename})
            db.close()
            self.materials_loaded = True

        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=lambda: self.show_course_setup(is_edit, index, course))
        self.upload_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.upload_scroll.pack(fill="both", expand=True, padx=100, pady=10)

        self.core_card = ctk.CTkFrame(self.upload_scroll, fg_color=CARD_COLOR, corner_radius=12, border_width=2,
                                      border_color=ACCENT_COLOR)
        self.core_card.pack(fill="x", pady=10, ipadx=20, ipady=20)
        ctk.CTkLabel(self.core_card, text=self.t("upload_core"), font=FONT_H2, text_color=ACCENT_COLOR).pack(anchor="w")
        ctk.CTkButton(self.core_card, text="+ " + self.t("select_file"), command=lambda: self.pick_file("core")).pack(
            pady=10)

        self.core_list_frame = ctk.CTkFrame(self.core_card, fg_color="transparent")
        self.core_list_frame.pack(fill="x")

        self.ref_card = ctk.CTkFrame(self.upload_scroll, fg_color=CARD_COLOR, corner_radius=12, border_width=1,
                                     border_color="#E5E5E5")
        self.ref_card.pack(fill="x", pady=10, ipadx=20, ipady=20)
        ctk.CTkLabel(self.ref_card, text=self.t("upload_ref"), font=FONT_H2).pack(anchor="w")
        ctk.CTkButton(self.ref_card, text="+ " + self.t("select_file"), command=lambda: self.pick_file("ref")).pack(
            pady=10)

        self.ref_list_frame = ctk.CTkFrame(self.ref_card, fg_color="transparent")
        self.ref_list_frame.pack(fill="x")

        self.weight_card = ctk.CTkFrame(self.upload_scroll, fg_color=CARD_COLOR, corner_radius=12, border_width=1,
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

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=100, pady=10)

        ctk.CTkLabel(scroll, text=self.t("persona_select"), font=FONT_H2).pack(anchor="w", pady=(10, 5))
        persona_menu = ctk.CTkOptionMenu(scroll,
                                         values=["温柔小姐姐 (适合零基础)", "学术AI (极简硬核)", "老师 (严谨推导)",
                                                 "温柔小哥哥 (逻辑清晰)", "暴力极客 (极限施压)"], font=FONT_BODY,
                                         width=400)
        persona_menu.pack(anchor="w", pady=(0, 20))

        ctk.CTkLabel(scroll, text=self.t("lang_select"), font=FONT_H2).pack(anchor="w", pady=(10, 5))
        lang_menu = ctk.CTkOptionMenu(scroll, values=["中文", "English"], font=FONT_BODY, width=400)
        lang_menu.set("中文")
        lang_menu.pack(anchor="w", pady=(0, 30))

        warn_text = self.t("warn_danger") if is_danger else self.t("warn_safe")
        ctk.CTkLabel(scroll, text=warn_text, font=FONT_H2, text_color=(DANGER_COLOR if is_danger else SUCCESS_COLOR),
                     wraplength=800, justify="left").pack(anchor="w", pady=(0, 20))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)

        def start(mode):
            self.start_generation(course, index, mode, persona_menu.get().split(" ")[0], lang_menu.get())

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
                ctk.CTkButton(row, text="打开", width=60, height=30, font=FONT_SUBTITLE, fg_color="#F0F8FF",
                              text_color=ACCENT_COLOR, command=lambda p=f.file_path: self.open_file(p)).pack(
                    side="right", padx=15)

    def start_generation(self, course, index, mode, persona, lang="中文"):
        config_file = "user_config.json"
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
        try:
            db = get_db_session()
            materials = db.query(DBMaterial).filter(DBMaterial.course_id == course["id"]).all()
            if not materials: raise Exception("没有找到任何上传资料")

            core_pages, ref_pages = [], []
            for m in materials:
                if self.stop_event.is_set(): return
                self.update_progress(f"📖 正在解析文件: {m.filename}...", 0.1)
                pages = extract_text_from_file(m.file_path)
                if m.file_type == "core":
                    core_pages.extend(pages)
                else:
                    ref_pages.extend(pages)
            db.close()

            chunks = []

            weight_prompt = ""
            if core_pages and ref_pages:
                if core_ratio > 0.5:
                    weight_prompt = f"本轮生成以【核心重点】为绝对主导（占 {int(core_ratio * 100)}%），【参考资料】仅作辅助补充。遇到冲突时，必须无条件以核心重点为准！"
                elif core_ratio < 0.5:
                    weight_prompt = f"本轮生成以【参考资料】为主要框架（占 {int((1 - core_ratio) * 100)}%），【核心重点】作为点睛之笔。"
                else:
                    weight_prompt = "本轮生成综合参考【核心重点】与【参考资料】，请提取双方的精华进行融合。"
            elif core_pages:
                weight_prompt = "本轮生成纯粹基于【核心重点】，禁止自行发散。"
            elif ref_pages:
                weight_prompt = "本轮生成纯粹基于【参考资料】，请仔细梳理全部知识点。"

            max_pages = 15
            if core_pages and ref_pages:
                core_limit = int(max_pages * core_ratio)
                ref_limit = max_pages - core_limit
                core_pages = core_pages[:max(1, core_limit)]
                ref_pages = ref_pages[:max(1, ref_limit)]

            def build_chunks(pages, prefix_tag):
                local_chunks = []
                for i in range(0, len(pages), 2):
                    chunk_items = pages[i:i + 2]
                    content = "\n\n".join(chunk_items)
                    if not content.strip(): continue
                    if i > 0 and len(pages[i - 1]) > 150:
                        content = "【上一页回顾...】\n" + pages[i - 1][-150:] + "\n\n" + content
                    local_chunks.append((f"{prefix_tag}", content))
                return local_chunks

            chunks.extend(build_chunks(core_pages, "【核心重点】"))
            chunks.extend(build_chunks(ref_pages, "【参考资料】"))

            info = CourseInfo(name=course["name"], school_level=course["school"], major=course["major"],
                              is_core_major=course["is_major"], credits=course["credits"],
                              days_left=course["days_left"], target_score=course["target_score"],
                              user_difficulty=course["difficulty"])
            results = []
            total_chunks = len(chunks)

            for i, (tag, content) in enumerate(chunks):
                if self.stop_event.is_set(): return

                elapsed = time.time() - self.start_time
                if i > 0:
                    avg_time = elapsed / i
                    remain = int(avg_time * (total_chunks - i))
                    self.after(0, lambda r=remain: self.time_label.configure(
                        text=self.t("time_est").format(f"{r // 60}分{r % 60}秒")))

                self.update_progress(f"🧠 AI导师正在梳理考点... ({i + 1}/{total_chunks})",
                                     0.1 + (i / total_chunks) * 0.8)

                img_tags = re.findall(r'\[\[\[IMAGE:.*?\]\]\]', content)

                user_choice = "option_1_保命流" if mode == "key" else "option_2_硬核流"
                md = generate_super_guide(f"{tag}\n{content}", info, persona=persona, user_choice=user_choice,
                                          weight_prompt=weight_prompt, lang=lang)

                if md and "跳过" not in md and len(md.strip()) > 20:
                    missing_tags = [t for t in img_tags if t not in md]
                    if missing_tags:
                        for img_tag in missing_tags:
                            parts = md.split("\n\n", 1)
                            if len(parts) > 1:
                                md = parts[0] + f"\n\n{img_tag}\n\n" + parts[1]
                            else:
                                md += f"\n\n{img_tag}\n"
                    results.append(md)

            if not results: raise Exception("未提取到有效考点")
            if self.stop_event.is_set(): return

            self.update_progress("🎨 正在排版公式、图片与高亮名词...", 0.9)

            clean_results = []
            for md in results:
                md = re.sub(r'【结语】.*', '', md, flags=re.DOTALL)
                md = re.sub(r'## 🎓 结语.*', '', md, flags=re.DOTALL)
                md = re.sub(r'### 🎓 结语.*', '', md, flags=re.DOTALL)
                clean_results.append(md.strip())

            final_markdown = "\n\n---\n\n".join(clean_results)

            outro_lang = "en" if lang == "English" else "zh"
            final_markdown += f"\n\n---\n\n{OUTROS[outro_lang].get(persona, OUTROS[outro_lang]['温柔小姐姐'])}"

            time_str = time.strftime("%m%d_%H%M", time.localtime())
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop): desktop = os.path.abspath(".")
            mode_str = "精简" if mode == "key" else "全量"
            output_filename = os.path.join(desktop, f"{course['name']}_{mode_str}_{time_str}.html")

            export_to_html(final_markdown, output_file=output_filename, course=info, persona=persona,
                           doc_type="专属讲义", lang=lang)

            db = get_db_session()
            db.add(DBGeneratedFile(course_id=course["id"], file_path=output_filename, created_at=time_str,
                                   file_type="guide"))
            db.commit()
            db.close()
            self.update_progress("✅ 渲染完成，即将打开...", 1.0)
            time.sleep(0.5)
            self.after(0, lambda: self.show_preview_screen(output_filename))
        except Exception as e:
            logger.error(f"生成失败: {e}")
            if not self.stop_event.is_set():
                self.after(0, lambda: messagebox.showerror(self.t("error"), str(e)))
                self.after(0, self.show_dashboard)

    def update_progress(self, text, value):
        self.after(0, lambda: self.progress_label.configure(text=text))
        self.after(0, lambda: self.progressbar.set(value))

    def show_review_menu(self, course, index):
        self.current_view = "review_menu"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=100, pady=10)
        ctk.CTkLabel(scroll, text=self.t("review_menu_title"), font=FONT_H1).pack(anchor="w", pady=(10, 30))
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 40))
        ctk.CTkButton(btn_frame, text=f"{self.t('review_ai_analysis')}\n{self.t('review_ai_analysis_desc')}",
                      font=FONT_H2, width=280, height=120, fg_color=CARD_COLOR, text_color=TEXT_COLOR, border_width=1,
                      border_color="#E5E5E5", command=lambda: self.show_ai_analysis(course, index)).pack(side="left",
                                                                                                         padx=(0, 20))
        ctk.CTkButton(btn_frame, text=f"{self.t('review_extract')}\n{self.t('review_extract_desc')}", font=FONT_H2,
                      width=280, height=120, fg_color=CARD_COLOR, text_color=TEXT_COLOR, border_width=1,
                      border_color="#E5E5E5", command=lambda: self.show_extract(course, index)).pack(side="left",
                                                                                                     padx=(0, 20))
        ctk.CTkButton(btn_frame, text=f"{self.t('review_train')}\n{self.t('review_train_desc')}", font=FONT_H2,
                      width=280, height=120, fg_color=CARD_COLOR, text_color=TEXT_COLOR, border_width=1,
                      border_color="#E5E5E5", command=lambda: self.show_training(course, index)).pack(side="left")

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
                ctk.CTkButton(row, text="打开", width=60, height=30, font=FONT_SUBTITLE, fg_color="#F0F8FF",
                              text_color=ACCENT_COLOR, command=lambda p=f.file_path: self.open_file(p)).pack(
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
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=100, pady=10)
        ctk.CTkLabel(scroll, text=self.t("review_ai_analysis"), font=FONT_H1).pack(anchor="w", pady=(10, 20))
        self.render_material_checkboxes(scroll, course["id"])
        ctk.CTkLabel(scroll, text="生成类型：", font=FONT_H2).pack(anchor="w", pady=(20, 5))
        mode_var = ctk.StringVar(value="mindmap")
        ctk.CTkRadioButton(scroll, text=self.t("mindmap"), variable=mode_var, value="mindmap", font=FONT_BODY).pack(
            anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(scroll, text=self.t("text_logic"), variable=mode_var, value="text_logic",
                           font=FONT_BODY).pack(anchor="w", padx=20, pady=5)

        def start():
            text = self.get_selected_texts()
            if not text: messagebox.showerror(self.t("error"), "请勾选有效资料！"); return
            self.run_generation_task(course, index, "analysis", text, mode=mode_var.get())

        ctk.CTkButton(scroll, text=self.t("generate_btn"), font=FONT_H2, height=50, fg_color=ACCENT_COLOR,
                      command=start).pack(pady=40)

    def show_extract(self, course, index):
        self.current_view = "extract"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=lambda: self.show_review_menu(course, index))
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=100, pady=10)
        ctk.CTkLabel(scroll, text=self.t("review_extract"), font=FONT_H1).pack(anchor="w", pady=(10, 20))
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
                      command=start).pack(pady=40)

    def show_training(self, course, index):
        self.current_view = "training"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=lambda: self.show_review_menu(course, index))
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=100, pady=10)
        ctk.CTkLabel(scroll, text=self.t("review_train"), font=FONT_H1).pack(anchor="w", pady=(10, 20))
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
        diff_var = ctk.CTkOptionMenu(row3,
                                     values=["1星 (基础)", "2星 (中等)", "3星 (常规期末)", "4星 (拔高)", "5星 (地狱)"],
                                     font=FONT_BODY)
        diff_var.set("3星 (常规期末)")
        diff_var.pack(side="left", padx=10)

        row4 = ctk.CTkFrame(scroll, fg_color="transparent")
        row4.pack(anchor="w", pady=10)
        ctk.CTkLabel(row4, text=self.t("train_sets"), font=FONT_H2).pack(side="left")
        sets_var = ctk.CTkOptionMenu(row4, values=["1", "2", "3", "4", "5"], font=FONT_BODY)
        sets_var.set("1")
        sets_var.pack(side="left", padx=10)

        ctk.CTkLabel(scroll, text=self.t("lang_select"), font=FONT_H2).pack(anchor="w", pady=(10, 5))
        train_lang_menu = ctk.CTkOptionMenu(scroll, values=["中文", "English"], font=FONT_BODY, width=400)
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
                      command=start).pack(pady=40)

    def run_generation_task(self, course, index, task_type, text, **kwargs):
        self.clear_ui()
        self.stop_event.clear()
        self.start_time = time.time()

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(center, text=self.t("gen_ing"), font=FONT_H1).pack(pady=(0, 20))
        self.progress_label = ctk.CTkLabel(center, text="🚀 正在准备数据与网络请求...", font=FONT_H2,
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

        def task():
            try:
                info = CourseInfo(name=course["name"], school_level=course["school"], major=course["major"],
                                  is_core_major=course["is_major"], credits=course["credits"],
                                  days_left=course["days_left"], target_score=course["target_score"],
                                  user_difficulty=course["difficulty"])

                if task_type == "extract":
                    chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)]
                    results = []
                    for i, chunk in enumerate(chunks):
                        if self.stop_event.is_set(): return
                        elapsed = time.time() - self.start_time
                        if i > 0:
                            remain = int((elapsed / i) * (len(chunks) - i))
                            self.after(0, lambda r=remain: self.time_label.configure(
                                text=self.t("time_est").format(f"{r // 60}分{r % 60}秒")))
                        self.update_progress(f"🔍 正在提取区块 {i + 1}/{len(chunks)}...", (i + 1) / len(chunks))
                        md = generate_extraction(chunk, kwargs.get("extract_type"), kwargs.get("with_answer"))
                        if md:
                            md = re.sub(r'以下是.*?考题。', '', md)
                            md = re.sub(r'以下是.*?提取.*?：', '', md)
                            results.append(md)
                    md = "\n\n".join(results)
                    doc_name = "资料提取"

                elif task_type == "analysis":
                    self.update_progress("🧠 AI 正在扫描文本，构建思维拓扑图...", 0.4)
                    md = generate_logic_analysis(text, kwargs.get("mode", "mindmap"))
                    doc_name = "逻辑分析" if kwargs.get("mode") == "text_logic" else "思维导图"

                elif task_type == "exam":
                    self.update_progress("📝 命题组长正在疯狂敲键盘，为你量身定制试卷题目...", 0.4)
                    md = generate_exam_paper(text, kwargs.get("train_type"), kwargs.get("num_sets"),
                                             kwargs.get("difficulty", 3), kwargs.get("diy_config", ""),
                                             kwargs.get("user_context"), kwargs.get("lang", "中文"))
                    doc_name = "训练试卷"

                if not md: raise Exception("生成结果为空")
                if self.stop_event.is_set(): return

                self.update_progress("🎨 正在渲染排版，并为你检查公式与换行...", 0.8)
                time_str = time.strftime("%m%d_%H%M", time.localtime())
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                if not os.path.exists(desktop): desktop = os.path.abspath(".")
                output_filename = os.path.join(desktop, f"{course['name']}_{doc_name}_{time_str}.html")

                export_to_html(md, output_file=output_filename, course=info, persona="AI", doc_type=doc_name,
                               lang=kwargs.get("lang", "中文"))

                db = get_db_session()
                db.add(DBGeneratedFile(course_id=course["id"], file_path=output_filename, created_at=time_str,
                                       file_type=task_type))
                db.commit()
                db.close()
                self.update_progress("✅ 渲染成功，准备展示！", 1.0)
                time.sleep(0.5)
                if not self.stop_event.is_set(): self.after(0, lambda: self.show_preview_screen(output_filename))
            except Exception as e:
                logger.error(f"生成失败: {e}")
                if not self.stop_event.is_set():
                    self.after(0, lambda: messagebox.showerror(self.t("error"), str(e)))
                    self.after(0, self.show_dashboard)

        threading.Thread(target=task).start()

    def show_notes(self, course, index):
        self.current_view = "notes"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        ctk.CTkLabel(self, text=self.t("note_title"), font=FONT_H1).pack(anchor="w", padx=100, pady=(20, 10))
        db = get_db_session()
        note_record = db.query(DBGeneratedFile).filter(DBGeneratedFile.course_id == course["id"],
                                                       DBGeneratedFile.file_type == "note").first()
        db.close()
        initial_text = ""
        if note_record and os.path.exists(note_record.file_path):
            with open(note_record.file_path, "r", encoding="utf-8") as f: initial_text = f.read()
        self.textbox = ctk.CTkTextbox(self, font=FONT_BODY, width=800, height=500, fg_color=CARD_COLOR,
                                      text_color=TEXT_COLOR)
        self.textbox.pack(padx=100, pady=10, fill="both", expand=True)
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
            messagebox.showinfo(self.t("ok"), self.t("note_saved"))

        ctk.CTkButton(self, text=self.t("note_save"), font=FONT_H2, height=45, fg_color=SUCCESS_COLOR,
                      command=save_note).pack(pady=20)

    def show_all_files(self, course, index):
        self.current_view = "all_files"
        self.view_args = {"course": course, "index": index}
        self.clear_ui()
        self.build_top_nav(show_back=True, back_command=self.show_dashboard)
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=100, pady=10)
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
                    if not os.path.exists(path): return
                    if path.endswith(".txt"):
                        subprocess.run(["open", path])
                    else:
                        try:
                            subprocess.run(["open", "-a", "Microsoft Edge", f"file://{path}"])
                        except:
                            subprocess.run(["open", f"file://{path}"])

                ctk.CTkButton(row, text="打开", width=60, height=30, font=FONT_SUBTITLE, fg_color="#F0F8FF",
                              text_color=ACCENT_COLOR, command=open_f).pack(side="right", padx=15)

    def open_file(self, path):
        if os.path.exists(path):
            try:
                subprocess.run(["open", "-a", "Microsoft Edge", f"file://{path}"])
            except:
                subprocess.run(["open", f"file://{path}"])

    def show_preview_screen(self, html_path):
        self.current_view = "preview"
        self.view_args = {"html_path": html_path}
        self.clear_ui()
        self.build_top_nav()
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(center, text="🎉", font=("Arial", 60)).pack(pady=(0, 10))
        ctk.CTkLabel(center, text=self.t("preview"), font=FONT_H1).pack(pady=(0, 40))

        def open_and_print(): self.open_file(html_path); messagebox.showinfo(self.t("ok"), self.t("print_tips"))

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


if __name__ == "__main__":
    app = TermFinaleApp()
    app.mainloop()