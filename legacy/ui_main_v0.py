import customtkinter as ctk
import sys
import json
import os

# ==========================================
# 🍎 全局设计规范
# ==========================================
FONT_FAMILY = "PingFang SC"
FONT_HUGE = (FONT_FAMILY, 90, "bold")
FONT_H1 = (FONT_FAMILY, 32, "bold")
FONT_H2 = (FONT_FAMILY, 22, "bold")
FONT_BODY = (FONT_FAMILY, 16, "normal")
FONT_SUBTITLE = (FONT_FAMILY, 14, "normal")

BG_COLOR = ("#FAFAFA", "#121212")
TEXT_COLOR = ("#1D1D1F", "#F5F5F7")
BODY_TEXT_COLOR = ("#424245", "#A1A1A6")
SUB_TEXT_COLOR = ("#86868B", "#86868B")
ACCENT_COLOR = "#007AFF"

CONFIG_FILE = "user_config.json"

# ==========================================
# 🌐 翻译字典 (新增第三页文本)
# ==========================================
TRANSLATIONS = {
    "zh": {
        "welcome": "欢迎来到",
        "desc": "这是一款帮助大学生用来快速复习期末考试的强大工具",
        "btn_guide": "查看使用说明",
        "hint": "请先阅读使用说明",
        "nav_log": "更新日志",
        "nav_about": "关于作者",
        "theme_dark": "暗黑模式",
        "theme_light": "亮色模式",
        "lang_btn": "EN",
        "back_btn": "← 返回",
        "guide_title": "TermFinale 使用指南",
        "demo_title": "界面与功能演示",
        "start_btn": "开始复习之路 →",
        # 👇 第三页文本
        "name_title": "怎么称呼您？",
        "name_placeholder": "请输入你的名字或昵称",
        "continue_btn": "继续 →",
        "name_empty_warning": "名字不能为空哦",

        "guide_body": """期末复习，你是否也面临这些问题：
几百页的PPT不知从何看起；
老师划的重点毫无逻辑；
直接去问网页AI，不仅字数超限，还经常胡编乱造、弄错公式；
有些时候，甚至连基本的化学结构式，电路图都无法识别。

TermFinale 为解决这些痛点而生。
它不是一个简单的AI聊天框，而是一个全自动的期末复习流水线。

操作流程非常简单：
第一步：导入你的杂乱课件（PPT / PDF）。
第二步：根据指示填入你的基本情况，我们会为你生成完全个性化复习系统。
第三步：你甚至可以选择一个喜欢的AI导师讲解风格。

在你上传完成后，后台会做这些工作：

1. 本地深度解析
剔除课件中的冗余信息与排版乱码，自动抽离并保存核心配图。

2. 多模态全学科识别
内置视觉大模型，可自动识别并解析电路图、化学结构式、医学解剖图等复杂图表。

3. 智能调度算法
内置动态权重计算引擎。根据剩余天数与目标分数，自动规划“保命流”或“硬核流”复习路线。

4. AI 导师人设
提供五种不同风格的讲解模式（严谨教授、暴躁极客、温柔学姐等），适配不同学习习惯。

5. 个性化组卷与模拟（进阶模块）
打破只看不练的假象。系统将根据你的知识薄弱点，AI动态生成针对性变式题；复习末期提供全真模拟卷，还原真实考试节奏。"""
    },
    "en": {
        "welcome": "Welcome to",
        "desc": "A powerful tool for college students to quickly prepare for final exams",
        "btn_guide": "View Instructions",
        "hint": "Please read the instructions first",
        "nav_log": "Changelog",
        "nav_about": "About",
        "theme_dark": "Dark Mode",
        "theme_light": "Light Mode",
        "lang_btn": "中",
        "back_btn": "← Back",
        "guide_title": "TermFinale Guide",
        "demo_title": "UI & Feature Demo",
        "start_btn": "Start Journey →",
        # 👇 Page 3 Text
        "name_title": "What should we call you?",
        "name_placeholder": "Enter your name or nickname",
        "continue_btn": "Continue →",
        "name_empty_warning": "Name cannot be empty",

        "guide_body": """Facing these problems during finals?
Hundreds of PPT slides, no clue where to start.
Messy key points.
Web AI fails on long text and breaks formulas.
Cannot recognize chemistry structures or circuit diagrams.

TermFinale is built for this.

Workflow:
1. Upload your messy files (PPT / PDF).
2. Enter your info for a personalized system.
3. Choose your AI tutor style.

What we do:
1. Local Deep Parsing
Removes noise and extracts core images.
2. Multi-modal Recognition
Parses circuits, chemistry, and medical charts.
3. Smart Scheduling
Plans 'Survival' or 'Hardcore' routes based on days left.
4. AI Tutor Personas
5 different styles for different habits.
5. Mock Exams
Generates variants targeting weaknesses."""
    }
}


class TermFinaleApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TermFinale")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(fg_color=BG_COLOR)

        self.current_lang = "zh"
        self.scroll_frame = None

        self.setup_navbar(show_back=False)
        self.show_welcome_screen()

    def setup_navbar(self, show_back=False):
        if hasattr(self, 'nav_frame') and self.nav_frame.winfo_exists():
            self.nav_frame.destroy()

        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.nav_frame.pack(side="top", fill="x", padx=40, pady=(20, 0))

        nav_left = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        nav_left.pack(side="left")
        text = TRANSLATIONS[self.current_lang]

        if show_back:
            ctk.CTkButton(
                nav_left, text=text["back_btn"], width=70, height=30,
                font=FONT_SUBTITLE, fg_color="transparent", text_color=SUB_TEXT_COLOR,
                hover_color=("#E5E5E5", "#2A2A2A"), command=self.show_guide_screen
            ).pack()

        nav_right = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        nav_right.pack(side="right")

        ctk.CTkButton(nav_right, text=text["nav_log"], width=70, height=30, font=FONT_SUBTITLE, fg_color="transparent",
                      text_color=SUB_TEXT_COLOR, hover_color=("#E5E5E5", "#2A2A2A")).pack(side="left", padx=10)
        ctk.CTkButton(nav_right, text=text["nav_about"], width=70, height=30, font=FONT_SUBTITLE,
                      fg_color="transparent", text_color=SUB_TEXT_COLOR, hover_color=("#E5E5E5", "#2A2A2A")).pack(
            side="left", padx=(10, 30))
        ctk.CTkButton(nav_right, text=text["lang_btn"], width=40, height=30, font=FONT_SUBTITLE, fg_color="transparent",
                      text_color=SUB_TEXT_COLOR, hover_color=("#E5E5E5", "#2A2A2A"), command=self.toggle_language).pack(
            side="left", padx=10)

        self.theme_switch = ctk.CTkSwitch(nav_right, text=text["theme_dark"], font=FONT_SUBTITLE,
                                          text_color=SUB_TEXT_COLOR, command=self.toggle_theme)
        self.theme_switch.pack(side="left")
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()

    def clear_ui(self):
        for widget in self.winfo_children():
            if widget != self.nav_frame:
                widget.destroy()

    # ==========================================
    # 页面 1：欢迎界面
    # ==========================================
    def show_welcome_screen(self):
        self.setup_navbar(show_back=False)
        self.clear_ui()
        text = TRANSLATIONS[self.current_lang]

        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(center_frame, text=text["welcome"], font=FONT_H1, text_color=SUB_TEXT_COLOR).pack(pady=(0, 10))
        ctk.CTkLabel(center_frame, text="Term Finale", font=FONT_HUGE, text_color=TEXT_COLOR).pack(pady=(0, 20))
        ctk.CTkLabel(center_frame, text=text["desc"], font=FONT_BODY, text_color=BODY_TEXT_COLOR).pack(pady=(0, 50))

        ctk.CTkButton(
            center_frame, text=text["btn_guide"], width=240, height=50, font=FONT_BODY,
            fg_color="transparent", border_width=1.5, border_color=TEXT_COLOR, text_color=TEXT_COLOR,
            hover_color=("#E5E5E5", "#2A2A2A"), corner_radius=25, command=self.show_guide_screen
        ).pack()
        ctk.CTkLabel(center_frame, text=text["hint"], font=("PingFang SC", 13), text_color=SUB_TEXT_COLOR).pack(
            pady=(20, 0))

    # ==========================================
    # 页面 2：使用说明
    # ==========================================
    def show_guide_screen(self):
        self.setup_navbar(show_back=True)
        self.clear_ui()
        text = TRANSLATIONS[self.current_lang]

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=SUB_TEXT_COLOR)
        self.scroll_frame.pack(fill="both", expand=True, padx=40, pady=10)

        content_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", width=800)
        content_frame.pack(anchor="center", pady=40)

        ctk.CTkLabel(content_frame, text=text["guide_title"], font=FONT_H1, text_color=TEXT_COLOR, anchor="w").pack(
            fill="x", pady=(0, 40))

        lines = text["guide_body"].split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                ctk.CTkLabel(content_frame, text="", height=10).pack()
                continue

            if line[0].isdigit() or line.startswith("第") or line.startswith("在你"):
                ctk.CTkLabel(
                    content_frame, text=line, font=FONT_H2, text_color=TEXT_COLOR,
                    justify="left", anchor="w", wraplength=800
                ).pack(fill="x", pady=(15, 5))
            else:
                ctk.CTkLabel(
                    content_frame, text=line, font=FONT_BODY, text_color=BODY_TEXT_COLOR,
                    justify="left", anchor="w", wraplength=800
                ).pack(fill="x", pady=2)

        ctk.CTkLabel(content_frame, text=text["demo_title"], font=FONT_H1, text_color=TEXT_COLOR, anchor="w").pack(
            fill="x", pady=(50, 20))

        demo_placeholder = ctk.CTkFrame(content_frame, fg_color=("#E5E5E5", "#1A1A1A"), height=400, corner_radius=0)
        demo_placeholder.pack(fill="x", pady=10)
        ctk.CTkLabel(demo_placeholder, text="[此处放置演示图与视频]", text_color=SUB_TEXT_COLOR).pack(expand=True)

        ctk.CTkButton(
            content_frame, text=text["start_btn"], width=240, height=55, font=FONT_H2,
            fg_color=ACCENT_COLOR, hover_color="#0056b3", corner_radius=27,
            command=self.show_name_entry_screen
        ).pack(pady=60)

        self.after(100, lambda: self.bind_all_scroll(self.scroll_frame))

    # ==========================================
    # 页面 3：怎么称呼您？
    # ==========================================
    def show_name_entry_screen(self):
        self.setup_navbar(show_back=True)  # 保留返回按钮
        self.clear_ui()
        text = TRANSLATIONS[self.current_lang]

        # 居中容器
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.45, anchor="center")

        # 大标题
        ctk.CTkLabel(
            center_frame, text=text["name_title"],
            font=FONT_H1, text_color=TEXT_COLOR
        ).pack(pady=(0, 40))

        # 输入框 (加个漂亮的边框和圆角)
        self.name_entry = ctk.CTkEntry(
            center_frame,
            width=400,
            height=50,
            font=FONT_BODY,
            placeholder_text=text["name_placeholder"],
            corner_radius=10,
            border_width=1.5,
            border_color=SUB_TEXT_COLOR,
            fg_color=("#FFFFFF", "#1A1A1A")
        )
        self.name_entry.pack(pady=(0, 10))

        # 错误提示标签 (默认隐藏)
        self.error_label = ctk.CTkLabel(
            center_frame, text=text["name_empty_warning"],
            text_color="#FF3B30", font=("PingFang SC", 12)
        )
        self.error_label.pack(pady=(0, 20))
        self.error_label.pack_forget()

        # 继续按钮
        ctk.CTkButton(
            center_frame,
            text=text["continue_btn"],
            width=400,
            height=50,
            font=FONT_BODY,
            fg_color=ACCENT_COLOR,
            hover_color="#0056b3",
            corner_radius=10,
            command=self.save_and_continue
        ).pack()

    def save_and_continue(self):
        """保存用户输入的名字"""
        name = self.name_entry.get().strip()
        if not name:
            # 如果为空，显示红色警告
            self.error_label.pack(pady=(0, 20))
            self.name_entry.configure(border_color="#FF3B30")  # 边框变红
            return

        # 保存到本地 json 文件
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"username": name}, f, ensure_ascii=False)
        except Exception as e:
            print(f"保存失败: {e}")

        # 进入主控台 (下一关)
        self.show_main_dashboard(name)

    # ==========================================
    # 页面 4：主控台 (待开发)
    # ==========================================
    def show_main_dashboard(self, name):
        self.clear_ui()
        text = TRANSLATIONS[self.current_lang]

        # 这里暂时留白，等下节课写主界面
        ctk.CTkLabel(self, text=f"欢迎进入主控台，{name}！", font=FONT_H1, text_color=TEXT_COLOR).pack(expand=True)

    # ==========================================
    # 通用功能
    # ==========================================
    def bind_all_scroll(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)
        for child in widget.winfo_children():
            self.bind_all_scroll(child)

    def _on_mousewheel(self, event):
        if not self.scroll_frame: return
        if sys.platform == "darwin":
            self.scroll_frame._parent_canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            self.scroll_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def toggle_language(self):
        self.current_lang = "en" if self.current_lang == "zh" else "zh"
        # 为了简单起见，切换语言直接回到首页
        self.show_welcome_screen()

    def toggle_theme(self):
        text = TRANSLATIONS[self.current_lang]
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
            self.theme_switch.configure(text=text["theme_dark"])
        else:
            ctk.set_appearance_mode("Light")
            self.theme_switch.configure(text=text["theme_light"])


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = TermFinaleApp()
    app.mainloop()