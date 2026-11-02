"""桌面端组件库：把「每页手写十行属性」收敛成可复用控件。

设计约束：
- 一律从 theme 取色与间距，不写裸色值；
- 不阻塞、不弹模态框（用 Toast 代替 messagebox 的提示类场景）；
- 只做展示，不承载业务逻辑。
"""
from __future__ import annotations

import customtkinter as ctk

from app.desktop import theme


class Card(ctk.CTkFrame):
    """统一卡片：白底、1px 边框、12 圆角。"""

    def __init__(self, master, **kwargs):
        p = theme.palette()
        kwargs.setdefault("fg_color", p.surface)
        kwargs.setdefault("corner_radius", theme.RADIUS["md"])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", p.border)
        super().__init__(master, **kwargs)


class SectionTitle(ctk.CTkFrame):
    """标题 + 可选副标题。"""

    def __init__(self, master, title: str, subtitle: str | None = None, **kwargs):
        p = theme.palette()
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=title, font=theme.FONT_H2, text_color=p.text,
                     anchor="w").pack(fill="x")
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, font=theme.FONT_SUBTITLE, text_color=p.text_muted,
                         anchor="w", justify="left").pack(fill="x", pady=(2, 0))


class PrimaryButton(ctk.CTkButton):
    def __init__(self, master, text: str, command=None, **kwargs):
        p = theme.palette()
        kwargs.setdefault("fg_color", p.accent)
        kwargs.setdefault("hover_color", p.accent_hover)
        kwargs.setdefault("text_color", "#FFFFFF")
        kwargs.setdefault("corner_radius", theme.RADIUS["sm"])
        kwargs.setdefault("font", theme.FONT_BODY)
        kwargs.setdefault("height", 40)
        super().__init__(master, text=text, command=command, **kwargs)


class GhostButton(ctk.CTkButton):
    """次级按钮：描边、透明底 —— 替代原来对比度过低的一批按钮。"""

    def __init__(self, master, text: str, command=None, **kwargs):
        p = theme.palette()
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", p.surface_alt)
        kwargs.setdefault("text_color", p.accent)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", p.border)
        kwargs.setdefault("corner_radius", theme.RADIUS["sm"])
        kwargs.setdefault("font", theme.FONT_SUBTITLE)
        kwargs.setdefault("height", 30)
        super().__init__(master, text=text, command=command, **kwargs)


class StyledOptionMenu(ctk.CTkOptionMenu):
    """统一成白底细边框，修掉「整条蓝色块」（U1）。"""

    def __init__(self, master, **kwargs):
        p = theme.palette()
        kwargs.setdefault("fg_color", p.surface_alt)
        kwargs.setdefault("text_color", p.text)
        kwargs.setdefault("button_color", p.border)
        kwargs.setdefault("button_hover_color", p.border)
        kwargs.setdefault("dropdown_fg_color", p.surface)
        kwargs.setdefault("dropdown_text_color", p.text)
        kwargs.setdefault("dropdown_hover_color", p.surface_alt)
        kwargs.setdefault("corner_radius", theme.RADIUS["sm"])
        kwargs.setdefault("font", theme.FONT_BODY)
        kwargs.setdefault("height", 36)
        super().__init__(master, **kwargs)


class ListRow(Card):
    """一行：标题 + 可选说明 + 右侧动作按钮。"""

    def __init__(self, master, title: str, meta: str = "", action_text: str | None = None,
                 action=None, **kwargs):
        p = theme.palette()
        kwargs.setdefault("corner_radius", theme.RADIUS["sm"])
        super().__init__(master, **kwargs)
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=theme.SPACE["md"], pady=theme.SPACE["sm"])
        ctk.CTkLabel(left, text=title, font=theme.FONT_BODY, text_color=p.text,
                     anchor="w").pack(fill="x")
        if meta:
            ctk.CTkLabel(left, text=meta, font=theme.FONT_SUBTITLE, text_color=p.text_muted,
                         anchor="w").pack(fill="x")
        if action_text and action:
            GhostButton(self, text=action_text, command=action, width=70).pack(
                side="right", padx=theme.SPACE["md"])


class StatTile(Card):
    """指标块：数值 + 标签 + 提示。"""

    def __init__(self, master, label: str, value: str, hint: str = "", tone: str = "text", **kwargs):
        p = theme.palette()
        kwargs.setdefault("corner_radius", theme.RADIUS["md"])
        super().__init__(master, **kwargs)
        color = getattr(p, tone, p.text)
        ctk.CTkLabel(self, text=label, font=theme.FONT_SUBTITLE, text_color=p.text_muted,
                     anchor="w").pack(fill="x", padx=theme.SPACE["lg"], pady=(theme.SPACE["md"], 0))
        ctk.CTkLabel(self, text=value, font=theme.FONT_H1, text_color=color,
                     anchor="w").pack(fill="x", padx=theme.SPACE["lg"])
        if hint:
            ctk.CTkLabel(self, text=hint, font=theme.FONT_SUBTITLE, text_color=p.text_muted,
                         anchor="w").pack(fill="x", padx=theme.SPACE["lg"],
                                          pady=(0, theme.SPACE["md"]))


class EmptyState(ctk.CTkFrame):
    def __init__(self, master, icon: str = "📭", title: str = "暂无内容", hint: str = "", **kwargs):
        p = theme.palette()
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=icon, font=(theme.FONT_FAMILY, 30)).pack(pady=(theme.SPACE["lg"], 0))
        ctk.CTkLabel(self, text=title, font=theme.FONT_H2, text_color=p.text).pack()
        if hint:
            ctk.CTkLabel(self, text=hint, font=theme.FONT_SUBTITLE, text_color=p.text_muted,
                         wraplength=420, justify="center").pack(pady=(2, 0))


class Toast:
    """非阻塞提示，替代提示类 messagebox。"""

    @staticmethod
    def show(root, message: str, kind: str = "info", duration: int = 2400) -> None:
        p = theme.palette()
        color = {"info": p.text, "success": p.success, "error": p.danger,
                 "warning": p.warning}.get(kind, p.text)
        try:
            label = ctk.CTkLabel(root, text=message, fg_color=color, text_color="#FFFFFF",
                                 corner_radius=theme.RADIUS["sm"], padx=theme.SPACE["lg"],
                                 pady=theme.SPACE["sm"], font=theme.FONT_BODY)
            label.place(relx=0.5, rely=0.95, anchor="s")
            label.lift()
            label.after(duration, label.destroy)
        except Exception:  # 窗口已销毁
            pass
