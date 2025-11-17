from __future__ import annotations

import os
import glob
import re
import weakref
from typing import Callable, Optional, List

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QKeyEvent, QShortcut, QKeySequence, QTextDocument
    from PyQt6.QtWidgets import QLineEdit, QTextEdit, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel
except ImportError as exc:  # pragma: no cover - UI layer
    raise RuntimeError("PyQt6 is required to use TerminalWidget") from exc

from .constants import MAX_TERMINAL_OUTPUT_LINES
from .models import AppConfig
from .terminal_backend import TerminalBackend
from .themes import get_theme


class AutoCompleteLineEdit(QLineEdit):
    """Line edit with file path auto-completion support"""

    def __init__(self, parent: Optional[QWidget] = None, cwd: str = ""):
        super().__init__(parent)
        self.cwd = cwd or os.getcwd()
        self._completion_matches: List[str] = []
        self._completion_index = 0

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Tab:
            self._handle_tab_completion()
            event.accept()
        else:
            # Reset completion state on any other key
            self._completion_matches = []
            self._completion_index = 0
            super().keyPressEvent(event)

    def _handle_tab_completion(self):
        text = self.text()
        cursor_pos = self.cursorPosition()

        # Extract the word/path at cursor position
        before_cursor = text[:cursor_pos]
        after_cursor = text[cursor_pos:]

        # Find the last token (simplified - split by spaces)
        tokens = before_cursor.split()
        if not tokens:
            return

        partial = tokens[-1]
        prefix = " ".join(tokens[:-1])
        if prefix:
            prefix += " "

        # If we're cycling through completions, use the stored matches
        if not self._completion_matches:
            self._completion_matches = self._get_completions(partial)
            self._completion_index = 0

        if not self._completion_matches:
            return

        # Cycle through matches
        match = self._completion_matches[self._completion_index]
        self._completion_index = (self._completion_index + 1) % len(self._completion_matches)

        # Update the text
        new_text = prefix + match + after_cursor
        self.setText(new_text)
        self.setCursorPosition(len(prefix) + len(match))

    def _get_completions(self, partial: str) -> List[str]:
        """Get file/directory completions for a partial path"""
        try:
            # Handle absolute vs relative paths
            if os.path.isabs(partial):
                search_pattern = partial + "*"
            else:
                search_pattern = os.path.join(self.cwd, partial + "*")

            # Get matching files/directories
            matches = glob.glob(search_pattern)

            # Convert to relative paths if the input was relative
            if not os.path.isabs(partial):
                matches = [os.path.relpath(m, self.cwd) for m in matches]

            # Add trailing slash for directories
            matches = [m + os.sep if os.path.isdir(os.path.join(self.cwd, m)) else m for m in matches]

            # Sort and return unique matches
            return sorted(set(matches))
        except Exception:
            return []


class TerminalWidget(QWidget):
    output_received = pyqtSignal(str)
    exit_received = pyqtSignal(int)

    def __init__(
        self,
        backend: TerminalBackend,
        parent: Optional[QWidget] = None,
        command_handler: Optional[Callable[[str], bool]] = None,
        app_config: Optional[AppConfig] = None,
    ):
        super().__init__(parent)
        self.backend = backend
        self._command_handler = command_handler

        # Use app_config or create default
        if app_config is None:
            from .models import AppConfig
            app_config = AppConfig()
        self.app_config = app_config

        # Get theme colors
        theme = get_theme(app_config.theme)

        self.output_view = QTextEdit(self)
        self.output_view.setReadOnly(True)
        self.output_view.setAcceptRichText(True)
        self.output_view.setUndoRedoEnabled(False)
        self.output_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Apply theme from config
        self.output_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme['terminal_bg']};
                color: {theme['terminal_fg']};
                font-family: {app_config.font_family}, Consolas, 'Cascadia Code', 'Courier New', monospace;
                font-size: {app_config.font_size}pt;
                selection-background-color: {theme['selection_bg']};
                selection-color: {theme['selection_fg']};
            }}
        """)

        self.input_field = AutoCompleteLineEdit(self, cwd=backend.cwd)
        self.input_field.setPlaceholderText("输入命令后回车 (Tab 键自动补全)")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme['input_bg']};
                color: {theme['input_fg']};
                font-family: {app_config.font_family}, Consolas, 'Cascadia Code', 'Courier New', monospace;
                font-size: {app_config.font_size}pt;
                border: 1px solid {theme['input_border']};
                padding: 4px;
            }}
        """)
        self.input_field.returnPressed.connect(self._handle_input)

        # Set default format with theme colors
        self._default_format = QTextCharFormat()
        self._default_format.setForeground(QColor(theme['terminal_fg']))
        self._default_format.setBackground(QColor(theme['terminal_bg']))
        self._current_format = QTextCharFormat(self._default_format)

        # Match SGR codes (m) and other CSI sequences
        self._ansi_pattern = re.compile(r"\x1B\[[0-9;?]*[a-zA-Z]")
        self._sgr_pattern = re.compile(r"\x1B\[(?P<code>[0-9;]*)m")

        # Search bar (hidden by default)
        self.search_bar = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(4, 2, 4, 2)
        search_layout.addWidget(QLabel("查找:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索文本...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._find_next)
        search_layout.addWidget(self.search_input, stretch=1)

        self.prev_btn = QPushButton("上一个")
        self.prev_btn.clicked.connect(self._find_previous)
        search_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("下一个")
        self.next_btn.clicked.connect(self._find_next)
        search_layout.addWidget(self.next_btn)

        self.match_case_btn = QPushButton("区分大小写")
        self.match_case_btn.setCheckable(True)
        self.match_case_btn.clicked.connect(self._on_search_text_changed)
        search_layout.addWidget(self.match_case_btn)

        self.search_count_label = QLabel("")
        search_layout.addWidget(self.search_count_label)

        close_btn = QPushButton("✕")
        close_btn.setMaximumWidth(30)
        close_btn.clicked.connect(self._hide_search_bar)
        search_layout.addWidget(close_btn)

        self.search_bar.setLayout(search_layout)
        self.search_bar.hide()

        # Search state
        self._search_matches: List[QTextCursor] = []
        self._current_match_index = -1

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.output_view, stretch=1)
        layout.addWidget(self.search_bar, stretch=0)
        layout.addWidget(self.input_field, stretch=0)
        self.setLayout(layout)

        # Add Ctrl+F shortcut for search
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self._show_search_bar)

        # Add Esc shortcut to close search bar
        esc_shortcut = QShortcut(QKeySequence("Esc"), self.search_bar)
        esc_shortcut.activated.connect(self._hide_search_bar)

        self.output_received.connect(self._append_output)
        self.exit_received.connect(self._handle_exit)
        self._output_forwarder = None
        self._exit_forwarder = None
        self._attach_backend_signals(backend)
        backend.start()
        self.input_field.setFocus(Qt.FocusReason.OtherFocusReason)

    def set_command_handler(self, handler: Optional[Callable[[str], bool]]):
        self._command_handler = handler

    def _handle_input(self):
        text = self.input_field.text()
        if not text:
            return
        if self._command_handler and self._command_handler(text):
            self.input_field.clear()
            return
        self.backend.send(text + "\n")
        self.input_field.clear()

    def _append_output(self, data: str):
        # Remove carriage returns and common terminal control sequences
        data = data.replace("\r\n", "\n").replace("\r", "")
        for chunk, fmt in self._parse_ansi(data):
            if not chunk:
                continue
            cursor = self.output_view.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(chunk, fmt)
            self.output_view.setTextCursor(cursor)

        # Limit the number of lines in the output buffer
        self._trim_output_buffer()

        # Scroll to bottom
        self.output_view.verticalScrollBar().setValue(self.output_view.verticalScrollBar().maximum())

    def _trim_output_buffer(self):
        """Trim output buffer to maximum number of lines."""
        doc = self.output_view.document()
        block_count = doc.blockCount()

        if block_count > MAX_TERMINAL_OUTPUT_LINES:
            # Calculate how many lines to remove
            lines_to_remove = block_count - MAX_TERMINAL_OUTPUT_LINES

            # Create cursor at the beginning
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)

            # Select lines to remove
            for _ in range(lines_to_remove):
                cursor.movePosition(
                    QTextCursor.MoveOperation.Down,
                    QTextCursor.MoveMode.KeepAnchor
                )

            # Remove the selected text
            cursor.removeSelectedText()
            cursor.deleteChar()  # Remove the trailing newline

    def _handle_exit(self, code: int):
        self.input_field.setDisabled(True)
        self.input_field.setPlaceholderText(f"Process exited ({code})")

    def display_system_message(self, message: str):
        self._append_output(message + "\n")

    def _show_search_bar(self):
        """Show the search bar and focus on search input."""
        self.search_bar.show()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _hide_search_bar(self):
        """Hide the search bar and clear highlights."""
        self.search_bar.hide()
        self._clear_search_highlights()
        self.input_field.setFocus()

    def _on_search_text_changed(self):
        """Handle search text change - find all matches."""
        search_text = self.search_input.text()
        if not search_text:
            self._clear_search_highlights()
            self.search_count_label.setText("")
            return

        # Clear previous highlights
        self._clear_search_highlights()

        # Find all matches
        self._search_matches = []
        doc = self.output_view.document()

        # Set search flags
        flags = QTextDocument.FindFlag(0)
        if self.match_case_btn.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively

        # Find all occurrences
        cursor = QTextCursor(doc)
        while True:
            cursor = doc.find(search_text, cursor, flags)
            if cursor.isNull():
                break
            self._search_matches.append(QTextCursor(cursor))

        # Update count label
        if self._search_matches:
            self.search_count_label.setText(f"{len(self._search_matches)} 个匹配")
            self._current_match_index = 0
            self._highlight_all_matches()
        else:
            self.search_count_label.setText("未找到")
            self._current_match_index = -1

    def _find_next(self):
        """Find and highlight next match."""
        if not self._search_matches:
            return

        self._current_match_index = (self._current_match_index + 1) % len(self._search_matches)
        self._highlight_all_matches()
        self._scroll_to_current_match()

    def _find_previous(self):
        """Find and highlight previous match."""
        if not self._search_matches:
            return

        self._current_match_index = (self._current_match_index - 1) % len(self._search_matches)
        self._highlight_all_matches()
        self._scroll_to_current_match()

    def _highlight_all_matches(self):
        """Highlight all matches with current match in different color."""
        selections = []

        for i, match_cursor in enumerate(self._search_matches):
            extra_selection = QTextEdit.ExtraSelection()
            extra_selection.cursor = match_cursor

            # Different color for current match
            if i == self._current_match_index:
                extra_selection.format.setBackground(QColor("#FFA500"))  # Orange
            else:
                extra_selection.format.setBackground(QColor("#FFFF00"))  # Yellow

            selections.append(extra_selection)

        self.output_view.setExtraSelections(selections)

        # Update count label
        if self._search_matches:
            self.search_count_label.setText(
                f"{self._current_match_index + 1}/{len(self._search_matches)}"
            )

    def _scroll_to_current_match(self):
        """Scroll to the current match."""
        if self._current_match_index < 0 or self._current_match_index >= len(self._search_matches):
            return

        current_cursor = self._search_matches[self._current_match_index]
        self.output_view.setTextCursor(current_cursor)
        self.output_view.ensureCursorVisible()

    def _clear_search_highlights(self):
        """Clear all search highlights."""
        self.output_view.setExtraSelections([])
        self._search_matches = []
        self._current_match_index = -1

    def _attach_backend_signals(self, backend: TerminalBackend):
        weak_self = weakref.ref(self)

        def forward_output(data: str):
            widget = weak_self()
            if not widget:
                return
            widget.output_received.emit(data)

        def forward_exit(code: int):
            widget = weak_self()
            if not widget:
                return
            widget.exit_received.emit(code)

        self._output_forwarder = forward_output
        self._exit_forwarder = forward_exit
        backend.output.connect(forward_output)
        backend.exited.connect(forward_exit)

    def _parse_ansi(self, data: str):
        # First, remove all non-SGR ANSI sequences
        cleaned = ""
        index = 0
        for match in self._ansi_pattern.finditer(data):
            start, end = match.span()
            cleaned += data[index:start]
            seq = match.group(0)
            # Only keep SGR (Select Graphic Rendition) sequences
            if seq[-1] == 'm':
                cleaned += seq
            index = end
        cleaned += data[index:]

        # Now parse SGR sequences for formatting
        index = 0
        for match in self._sgr_pattern.finditer(cleaned):
            start, end = match.span()
            if start > index:
                yield cleaned[index:start], QTextCharFormat(self._current_format)
            self._apply_ansi(match.group("code"))
            index = end
        if index < len(cleaned):
            yield cleaned[index:], QTextCharFormat(self._current_format)

    def _apply_ansi(self, code: str):
        if not code:
            self._current_format = QTextCharFormat(self._default_format)
            return
        for token in code.split(";"):
            if not token:
                continue
            value = int(token)
            if value == 0:
                self._current_format = QTextCharFormat(self._default_format)
            elif value == 1:
                self._current_format.setFontWeight(QFont.Weight.Bold)
            elif value == 22:
                self._current_format.setFontWeight(QFont.Weight.Normal)
            elif 30 <= value <= 37:
                color = _ansi_color(value - 30)
                self._current_format.setForeground(QColor(color))
            elif value == 39:
                self._current_format.setForeground(self._default_format.foreground())
            elif 40 <= value <= 47:
                color = _ansi_color(value - 40)
                self._current_format.setBackground(QColor(color))
            elif value == 49:
                self._current_format.setBackground(self._default_format.background())


def _ansi_color(code: int) -> str:
    # PowerShell-style color palette
    palette = [
        "#000000",  # black
        "#E74856",  # red (PowerShell red)
        "#16C60C",  # green (PowerShell green)
        "#F9F1A5",  # yellow (PowerShell yellow)
        "#3B78FF",  # blue (PowerShell blue)
        "#B4009E",  # magenta (PowerShell magenta)
        "#61D6D6",  # cyan (PowerShell cyan)
        "#CCCCCC",  # white (PowerShell gray)
    ]
    return palette[code % len(palette)]
