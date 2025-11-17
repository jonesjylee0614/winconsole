"""Theme definitions for WinConsole terminal widgets."""

from __future__ import annotations

from typing import Dict

# Theme color definitions
ThemeColors = Dict[str, str]

THEMES: Dict[str, ThemeColors] = {
    "dark": {
        "terminal_bg": "#012456",
        "terminal_fg": "#CCCCCC",
        "input_bg": "#012456",
        "input_fg": "#CCCCCC",
        "input_border": "#3A5F8A",
        "selection_bg": "#FFFFFF",
        "selection_fg": "#000000",
    },
    "light": {
        "terminal_bg": "#FFFFFF",
        "terminal_fg": "#000000",
        "input_bg": "#F5F5F5",
        "input_fg": "#000000",
        "input_border": "#CCCCCC",
        "selection_bg": "#0078D7",
        "selection_fg": "#FFFFFF",
    },
    "solarized-dark": {
        "terminal_bg": "#002B36",
        "terminal_fg": "#839496",
        "input_bg": "#002B36",
        "input_fg": "#839496",
        "input_border": "#073642",
        "selection_bg": "#586E75",
        "selection_fg": "#FDF6E3",
    },
    "monokai": {
        "terminal_bg": "#272822",
        "terminal_fg": "#F8F8F2",
        "input_bg": "#272822",
        "input_fg": "#F8F8F2",
        "input_border": "#49483E",
        "selection_bg": "#49483E",
        "selection_fg": "#F8F8F2",
    },
}


def get_theme(theme_name: str) -> ThemeColors:
    """Get theme colors by name, fallback to dark theme if not found.

    Args:
        theme_name: Name of the theme

    Returns:
        Dictionary of theme colors
    """
    return THEMES.get(theme_name, THEMES["dark"])


def get_available_themes() -> list[str]:
    """Get list of available theme names.

    Returns:
        List of theme names
    """
    return list(THEMES.keys())
