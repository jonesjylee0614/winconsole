"""Theme definitions for WinConsole terminal widgets."""

from __future__ import annotations

from typing import Dict

# Theme color definitions
ThemeColors = Dict[str, str]

THEMES: Dict[str, ThemeColors] = {
    "vscode-dark": {
        # VS Code 默认深色主题 - 黑底高亮
        "terminal_bg": "#1E1E1E",  # 纯黑背景
        "terminal_fg": "#CCCCCC",  # 浅灰色文字
        "input_bg": "#1E1E1E",
        "input_fg": "#CCCCCC",
        "input_border": "#1E1E1E",
        "selection_bg": "#264F78",  # 蓝色选中
        "selection_fg": "#FFFFFF",
        "cursor_color": "#AEAFAD",  # 灰白色光标
    },
    "dracula": {
        # Dracula 主题 - 紫色系高对比
        "terminal_bg": "#282A36",  # 深灰紫背景
        "terminal_fg": "#F8F8F2",  # 浅色文字
        "input_bg": "#282A36",
        "input_fg": "#F8F8F2",
        "input_border": "#282A36",
        "selection_bg": "#44475A",  # 紫灰选中
        "selection_fg": "#F8F8F2",
        "cursor_color": "#F8F8F2",  # 白色光标
    },
    "one-dark": {
        # Atom One Dark 主题 - 流行的深色主题
        "terminal_bg": "#282C34",  # 深灰蓝背景
        "terminal_fg": "#ABB2BF",  # 浅灰文字
        "input_bg": "#282C34",
        "input_fg": "#ABB2BF",
        "input_border": "#282C34",
        "selection_bg": "#3E4451",  # 灰蓝选中
        "selection_fg": "#ABB2BF",
        "cursor_color": "#528BFF",  # 蓝色光标
    },
    "monokai": {
        # Monokai 主题 - 经典深色高对比
        "terminal_bg": "#272822",  # 深灰绿背景
        "terminal_fg": "#F8F8F2",  # 几乎白色文字
        "input_bg": "#272822",
        "input_fg": "#F8F8F2",
        "input_border": "#272822",
        "selection_bg": "#49483E",  # 深灰选中
        "selection_fg": "#F8F8F2",
        "cursor_color": "#F8F8F0",  # 白色光标
    },
    "github-dark": {
        # GitHub Dark 主题
        "terminal_bg": "#0D1117",  # 深黑背景
        "terminal_fg": "#C9D1D9",  # 浅灰文字
        "input_bg": "#0D1117",
        "input_fg": "#C9D1D9",
        "input_border": "#0D1117",
        "selection_bg": "#1F6FEB",  # GitHub 蓝选中
        "selection_fg": "#FFFFFF",
        "cursor_color": "#58A6FF",  # 亮蓝光标
    },
    "powershell": {
        # Windows Terminal PowerShell 风格（保留兼容性）
        "terminal_bg": "#012456",  # PowerShell 深蓝色背景
        "terminal_fg": "#CCCCCC",
        "input_bg": "#012456",
        "input_fg": "#CCCCCC",
        "input_border": "#012456",
        "selection_bg": "#FFFFFF",
        "selection_fg": "#000000",
        "cursor_color": "#FFFFFF",
    },
    "solarized-dark": {
        # Solarized Dark 主题
        "terminal_bg": "#002B36",
        "terminal_fg": "#839496",
        "input_bg": "#002B36",
        "input_fg": "#839496",
        "input_border": "#073642",
        "selection_bg": "#586E75",
        "selection_fg": "#FDF6E3",
        "cursor_color": "#839496",
    },
    "light": {
        # 浅色主题
        "terminal_bg": "#FFFFFF",
        "terminal_fg": "#000000",
        "input_bg": "#F5F5F5",
        "input_fg": "#000000",
        "input_border": "#CCCCCC",
        "selection_bg": "#0078D7",
        "selection_fg": "#FFFFFF",
        "cursor_color": "#000000",
    },
}


def get_theme(theme_name: str) -> ThemeColors:
    """Get theme colors by name, fallback to vscode-dark if not found.

    Args:
        theme_name: Name of the theme

    Returns:
        Dictionary of theme colors
    """
    return THEMES.get(theme_name, THEMES["vscode-dark"])


def get_available_themes() -> list[str]:
    """Get list of available theme names.

    Returns:
        List of theme names
    """
    return list(THEMES.keys())
