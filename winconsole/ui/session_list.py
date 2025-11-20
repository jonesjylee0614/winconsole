from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..models import Session, SessionState


class SessionListItemWidget(QWidget):
    def __init__(self, session: Session, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._session = session
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        self.name_label = QLabel()
        name_font = self.name_label.font()
        name_font.setBold(True)
        self.name_label.setFont(name_font)
        self.path_label = QLabel()
        self.path_label.setStyleSheet("color: #666666;")
        self.tags_label = QLabel()
        self.tags_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.name_label)
        layout.addWidget(self.path_label)
        layout.addWidget(self.tags_label)
        self.setLayout(layout)
        self.refresh(session)

    def refresh(self, session: Session):
        self._session = session
        self.name_label.setText(f"{session.display_name} {self._state_badge(session.state)}")
        self.path_label.setText(f"路径: {self._format_path(session.cwd)}")
        tags = " ".join(f"[{tag}]" for tag in session.tags) if session.tags else "[无标签]"
        self.tags_label.setText(tags)

    def _format_path(self, cwd: str) -> str:
        if not cwd:
            return "默认目录"
        path = Path(cwd)
        tail = path.name or str(path)
        if len(str(path)) == len(tail):
            return tail
        return f".../{tail}"

    def _state_badge(self, state: SessionState) -> str:
        if state == SessionState.RUNNING:
            return "●"
        if state == SessionState.EXITED:
            return "○"
        return "•"
