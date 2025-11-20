"""Constants used throughout WinConsole."""

from __future__ import annotations

# Application constants
APP_NAME = "WinConsole Manager"
APP_ORG_NAME = "WinConsole"
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

# Terminal constants
MAX_TERMINAL_OUTPUT_LINES = 2000
DEFAULT_TERMINAL_FONT_FAMILY = "Cascadia Code"
DEFAULT_TERMINAL_FONT_SIZE = 12

# Action button constants
ACTION_BUTTON_RESET_DELAY_MS = 1500

# File paths
DEFAULT_CONFIG_DIR = ".winconsole"
DEFAULT_STATE_FILE = "session_state.json"
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "winconsole.log"

# Logging
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Session state
STATE_FILE_VERSION = "1.0"

# Bailian API
BAILIAN_MAX_RETRIES = 2
BAILIAN_RETRY_BASE_DELAY = 0.5  # seconds
BAILIAN_DEFAULT_TIMEOUT = 5.0  # seconds

# TUI programs that require full terminal emulation
# These programs use advanced terminal features (raw mode, ANSI sequences, etc.)
# and may not work correctly in simplified terminal implementations
TUI_PROGRAMS = {
    # AI coding assistants
    'codex', 'claude', 'aider', 'cursor',

    # Editors
    'vim', 'nvim', 'neovim', 'vi', 'nano', 'emacs', 'micro',

    # System monitors
    'htop', 'top', 'btop', 'gotop', 'ytop', 'glances',

    # File managers
    'mc', 'ranger', 'nnn', 'lf', 'vifm',

    # Other TUI tools
    'tmux', 'screen', 'weechat', 'irssi', 'mutt', 'lynx', 'w3m',
    'tig', 'lazygit', 'gitui', 'ncdu', 'cmus', 'ncmpcpp',
}
