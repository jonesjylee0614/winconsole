from __future__ import annotations

import re
import weakref
from typing import Callable, Optional

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
    from PyQt6.QtWidgets import QLineEdit, QTextEdit, QVBoxLayout, QWidget
except ImportError as exc:  # pragma: no cover - UI layer
    raise RuntimeError("PyQt6 is required to use TerminalWidget") from exc

from .terminal_backend import TerminalBackend


class TerminalWidget(QWidget):
    output_received = pyqtSignal(str)
    exit_received = pyqtSignal(int)

    def __init__(
        self,
        backend: TerminalBackend,
        parent: Optional[QWidget] = None,
        command_handler: Optional[Callable[[str], bool]] = None,
    ):
        super().__init__(parent)
        self.backend = backend
        self._command_handler = command_handler
        self.output_view = QTextEdit(self)
        self.output_view.setReadOnly(True)
        self.output_view.setAcceptRichText(True)
        self.output_view.setUndoRedoEnabled(False)
        self.output_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.output_view.setStyleSheet("font-family: Consolas, 'Cascadia Code', monospace; font-size: 12px;")
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("输入命令后回车")
        self.input_field.returnPressed.connect(self._handle_input)
        self._default_format = QTextCharFormat()
        self._current_format = QTextCharFormat(self._default_format)
        self._ansi_pattern = re.compile(r"\x1B\[(?P<code>[0-9;]*)m")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.output_view, stretch=1)
        layout.addWidget(self.input_field, stretch=0)
        self.setLayout(layout)

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
        for chunk, fmt in self._parse_ansi(data):
            if not chunk:
                continue
            cursor = self.output_view.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(chunk.replace("\r", ""), fmt)
            self.output_view.setTextCursor(cursor)
        self.output_view.verticalScrollBar().setValue(self.output_view.verticalScrollBar().maximum())

    def _handle_exit(self, code: int):
        self.input_field.setDisabled(True)
        self.input_field.setPlaceholderText(f"Process exited ({code})")

    def display_system_message(self, message: str):
        self._append_output(message + "\n")

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
        index = 0
        for match in self._ansi_pattern.finditer(data):
            start, end = match.span()
            if start > index:
                yield data[index:start], QTextCharFormat(self._current_format)
            self._apply_ansi(match.group("code"))
            index = end
        if index < len(data):
            yield data[index:], QTextCharFormat(self._current_format)

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
    palette = [
        "#000000",  # black
        "#AA0000",  # red
        "#00AA00",  # green
        "#AA5500",  # yellow
        "#0000AA",  # blue
        "#AA00AA",  # magenta
        "#00AAAA",  # cyan
        "#AAAAAA",  # white
    ]
    return palette[code % len(palette)]
