"""桌面端主题：颜色 / 间距 / 圆角 / 字体（纯数据，可被 Web 端复用）。

以前 39 处裸颜色、150 处硬编码间距散在 1395 行里，改一次风格要动几十处。
现在所有视觉常量从这里取。
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    danger: str
    success: str
    warning: str


LIGHT = Palette(
    bg="#F5F5F7",
    surface="#FFFFFF",
    surface_alt="#F2F2F4",
    border="#E5E5E5",
    text="#1D1D1F",
    text_muted="#86868B",
    accent="#007AFF",
    accent_hover="#0062CC",
    danger="#FF3B30",
    success="#34C759",
    warning="#FF9500",
)

DARK = Palette(
    bg="#121212",
    surface="#1C1C1E",
    surface_alt="#2C2C2E",
    border="#3A3A3C",
    text="#F5F5F7",
    text_muted="#98989F",
    accent="#0A84FF",
    accent_hover="#409CFF",
    danger="#FF453A",
    success="#30D158",
    warning="#FF9F0A",
)

_current: Palette = LIGHT

# 8pt 网格
SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "2xl": 32, "3xl": 48}
RADIUS = {"sm": 8, "md": 12, "lg": 16, "pill": 999}


def _default_family() -> str:
    if sys.platform == "darwin":
        return "PingFang SC"
    if os.name == "nt":
        return "Microsoft YaHei UI"
    return "Noto Sans CJK SC"


FONT_FAMILY = _default_family()
FONT_HUGE = (FONT_FAMILY, 42, "bold")
FONT_H1 = (FONT_FAMILY, 26, "bold")
FONT_H2 = (FONT_FAMILY, 18, "bold")
FONT_BODY = (FONT_FAMILY, 14, "normal")
FONT_SUBTITLE = (FONT_FAMILY, 12, "normal")
FONT_MONO = ("Menlo" if sys.platform == "darwin" else "Consolas", 13, "normal")


def palette() -> Palette:
    return _current


def set_dark(enabled: bool) -> Palette:
    global _current
    _current = DARK if enabled else LIGHT
    return _current


def font(size: int, weight: str = "normal") -> tuple:
    return (FONT_FAMILY, size, weight)


# 向后兼容：main.py 里大量使用这些名字
BG_COLOR = LIGHT.bg
SIDEBAR_COLOR = LIGHT.surface
CARD_COLOR = LIGHT.surface
TEXT_COLOR = LIGHT.text
SUB_TEXT_COLOR = LIGHT.text_muted
ACCENT_COLOR = LIGHT.accent
DANGER_COLOR = LIGHT.danger
SUCCESS_COLOR = LIGHT.success
WARNING_COLOR = LIGHT.warning
BORDER_COLOR = LIGHT.border
