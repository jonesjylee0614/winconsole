from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import os

try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QKeySequence, QShortcut
    from PyQt6.QtWidgets import (
        QComboBox,
        QDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QStackedWidget,
        QToolBar,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - UI layer
    raise RuntimeError("PyQt6 is required to launch the UI") from exc

from .config_loader import load_app_config, load_session_templates
from .constants import ACTION_BUTTON_RESET_DELAY_MS, APP_NAME
from .models import Session, SessionAction, SessionOverrides, SessionState
from .session_manager import SessionManager
from .terminal_backend import TerminalBackend
from .terminal_widget import TerminalWidget
from .utils import BailianClient


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


@dataclass(frozen=True)
class _ShellProfile:
    aliases: List[str]
    label: str
    cmd: str
    args: List[str]
    encoding: str
    cwd: Optional[str] = None


class SessionDetailWidget(QWidget):
    BUILTIN_SHELLS: List[_ShellProfile] = [
        _ShellProfile(["wsl"], "WSL (bash)", "wsl.exe", [], "utf-8"),
        _ShellProfile(["cmd", "command prompt"], "Command Prompt", "cmd.exe", [], "gbk"),
        _ShellProfile(["powershell", "pwsh"], "PowerShell", "powershell.exe", [], "gbk"),
        _ShellProfile(["bash"], "Bash", "bash", ["-l"], "utf-8"),
    ]

    def __init__(self, session: Session, on_session_updated, app_config=None):
        super().__init__()
        self.session = session
        self._on_session_updated = on_session_updated
        self._app_config = app_config
        self._alias_map = self._build_shell_alias_map()
        self.backend = self._create_backend(session)
        self.terminal = TerminalWidget(
            self.backend,
            command_handler=self._handle_pre_send,
            app_config=app_config
        )
        self.terminal.exit_received.connect(self._handle_backend_exit)

        self.header_frame = QFrame(self)
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(6, 6, 6, 6)
        header_layout.setSpacing(4)
        top_row = QHBoxLayout()
        self.name_label = QLabel()
        title_font = self.name_label.font()
        title_font.setPointSize(title_font.pointSize() + 1)
        title_font.setBold(True)
        self.name_label.setFont(title_font)
        top_row.addWidget(self.name_label)
        top_row.addStretch()
        self.state_label = QLabel()
        self.state_label.setStyleSheet("font-weight: bold;")
        top_row.addWidget(self.state_label)
        self.restart_btn = QToolButton()
        self.restart_btn.setText("重启 Shell")
        self.restart_btn.clicked.connect(self._handle_restart_shell)
        top_row.addWidget(self.restart_btn)
        header_layout.addLayout(top_row)

        info_grid = QGridLayout()
        info_grid.setVerticalSpacing(2)
        info_grid.addWidget(QLabel("Shell:"), 0, 0)
        self.shell_label = QLabel()
        info_grid.addWidget(self.shell_label, 0, 1)
        info_grid.addWidget(QLabel("路径:"), 0, 2)
        self.cwd_label = QLabel()
        self.cwd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_grid.addWidget(self.cwd_label, 0, 3)
        info_grid.addWidget(QLabel("标签:"), 1, 0)
        self.tags_label = QLabel()
        self.tags_label.setWordWrap(True)
        info_grid.addWidget(self.tags_label, 1, 1, 1, 3)
        header_layout.addLayout(info_grid)

        desc_row = QHBoxLayout()
        desc_label = QLabel("描述:")
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        desc_row.addWidget(desc_label)
        desc_row.addWidget(self.description_label, stretch=1)
        self.edit_desc_btn = QToolButton()
        self.edit_desc_btn.setText("编辑")
        self.edit_desc_btn.clicked.connect(self._handle_edit_description)
        desc_row.addWidget(self.edit_desc_btn)
        header_layout.addLayout(desc_row)
        self.header_frame.setLayout(header_layout)

        self.hint_frame = QFrame(self)
        hint_layout = QHBoxLayout()
        hint_layout.setContentsMargins(6, 6, 6, 6)
        hint_layout.setSpacing(6)
        hints_box = QVBoxLayout()
        hints_title = QLabel("提示")
        hints_title.setStyleSheet("font-weight: bold;")
        hints_box.addWidget(hints_title)
        self.hints_layout = QVBoxLayout()
        hints_box.addLayout(self.hints_layout)
        self.shell_hint_label = QLabel("输入 wsl / cmd / powershell 以切换 Shell")
        self.shell_hint_label.setStyleSheet("color: #555555; font-size: 11px;")
        hints_box.addWidget(self.shell_hint_label)
        hint_layout.addLayout(hints_box, stretch=1)
        actions_box = QVBoxLayout()
        actions_title = QLabel("常用操作")
        actions_title.setStyleSheet("font-weight: bold;")
        actions_box.addWidget(actions_title)
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(6)
        self._action_buttons: Dict[str, QPushButton] = {}
        actions_box.addLayout(self.actions_layout)
        hint_layout.addLayout(actions_box, stretch=0)
        self.hint_frame.setLayout(hint_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.header_frame)
        layout.addWidget(self.terminal, stretch=1)
        layout.addWidget(self.hint_frame)
        self.setLayout(layout)
        self.refresh(session)
        if not self.session.current_shell:
            self.session.current_shell = self._current_shell_label(self.session.cmd)
            self._on_session_updated(self.session)

    def refresh(self, session: Session):
        self.session = session
        self.name_label.setText(session.display_name)
        label = session.current_shell or self._current_shell_label(session.cmd)
        self.shell_label.setText(label)
        self.cwd_label.setText(session.cwd or "-")
        tags = " ".join(f"[{tag}]" for tag in session.tags) if session.tags else "[无标签]"
        self.tags_label.setText(tags)
        self.description_label.setText(session.description or "暂无描述")
        self._update_state_label(session.state)
        self._rebuild_hints(session.hints)
        self._rebuild_actions(session.actions)

    def _update_state_label(self, state: SessionState, exit_code: Optional[int] = None):
        if state == SessionState.RUNNING:
            self.state_label.setText('<span style="color:#2ecc71;">●</span> 运行中')
        elif state == SessionState.EXITED:
            details = f"(code {exit_code})" if exit_code is not None else ""
            self.state_label.setText(f'<span style="color:#999999;">○</span> 已退出 {details}'.strip())
        else:
            self.state_label.setText('<span style="color:#f1c40f;">•</span> 等待启动')

    def _rebuild_hints(self, hints: List[str]):
        _clear_layout(self.hints_layout)
        if hints:
            for hint in hints:
                label = QLabel(f"• {hint}")
                label.setWordWrap(True)
                self.hints_layout.addWidget(label)
        else:
            placeholder = QLabel("暂无提示")
            placeholder.setStyleSheet("color: #777777;")
            self.hints_layout.addWidget(placeholder)

    def _rebuild_actions(self, actions: List[SessionAction]):
        _clear_layout(self.actions_layout)
        self._action_buttons.clear()
        if actions:
            for action in actions:
                button = QPushButton(action.label)
                button.setProperty("action_label", action.label)
                button.setToolTip(action.command)
                button.clicked.connect(lambda _=False, act=action: self._handle_action_triggered(act))
                self._action_buttons[action.label] = button
                self.actions_layout.addWidget(button)
        else:
            placeholder = QLabel("未配置操作")
            placeholder.setStyleSheet("color: #777777;")
            self.actions_layout.addWidget(placeholder)

    def _handle_action_triggered(self, action: SessionAction):
        button = self._action_buttons.get(action.label)
        if button:
            button.setEnabled(False)
            button.setText(f"{action.label} (执行中)")
        self.terminal.display_system_message(f"[Action] {action.label}: {action.command}")
        self._send_command(action.command)
        if button:
            QTimer.singleShot(
                ACTION_BUTTON_RESET_DELAY_MS,
                lambda btn=button, label=action.label: self._reset_action_button(btn, label),
            )

    def _reset_action_button(self, button: QPushButton, label: str):
        button.setEnabled(True)
        button.setText(label)

    def run_default_action(self) -> bool:
        if not self.session.actions:
            return False
        self._handle_action_triggered(self.session.actions[0])
        return True

    def _send_command(self, command: str):
        payload = command.rstrip("\n") + "\n"
        self.backend.send(payload)

    def focus_terminal(self):
        self.terminal.input_field.setFocus(Qt.FocusReason.OtherFocusReason)

    def shutdown(self):
        self.backend.terminate()

    def _handle_edit_description(self):
        text, ok = QInputDialog.getMultiLineText(
            self,
            "编辑描述",
            "描述内容：",
            self.session.description,
        )
        if not ok:
            return
        self.session.description = text.strip()
        self._on_session_updated(self.session)
        self.refresh(self.session)

    def _current_shell_label(self, command: str) -> str:
        command_lower = command.lower()
        for profile in self.BUILTIN_SHELLS:
            if any(alias in command_lower for alias in profile.aliases):
                return profile.label
        if "cmd.exe" in command_lower:
            return "Command Prompt"
        if "powershell" in command_lower:
            return "PowerShell"
        if "wsl" in command_lower:
            return "WSL"
        if "bash" in command_lower:
            return "Bash"
        return Path(command).name or command

    def _handle_backend_exit(self, code: int):
        self.session.state = SessionState.EXITED
        self._on_session_updated(self.session)
        self._update_state_label(SessionState.EXITED, code)
        self.terminal.display_system_message(f"进程已退出 (code {code})")

    def _build_shell_alias_map(self) -> Dict[str, _ShellProfile]:
        mapping: Dict[str, _ShellProfile] = {}
        for profile in self.BUILTIN_SHELLS:
            for alias in profile.aliases:
                mapping[alias.lower()] = profile
        return mapping

    def _handle_pre_send(self, text: str) -> bool:
        key = text.strip()
        if not key:
            return False
        tokens = key.split()
        alias = tokens[0].lower()
        profile = self._alias_map.get(alias)
        if not profile:
            return False
        extra_args = tokens[1:]
        self._switch_shell(profile, extra_args)
        return True

    def _handle_restart_shell(self):
        self.terminal.display_system_message("正在重启当前 shell …")
        self.backend.terminate()
        self.session.state = SessionState.RUNNING
        self.backend = self._create_backend(self.session)
        self._replace_terminal_widget()
        self._on_session_updated(self.session)
        label = self.session.current_shell or self._current_shell_label(self.session.cmd)
        self.terminal.display_system_message(f"已重启 {label}")

    def _switch_shell(self, profile: _ShellProfile, extra_args: List[str]):
        self.terminal.display_system_message(f"正在切换到 {profile.label} …")
        self.backend.terminate()
        args = list(profile.args)
        if extra_args:
            args.extend(extra_args)
        self.session.cmd = profile.cmd
        self.session.args = args
        self.session.encoding = profile.encoding
        self.session.cwd = profile.cwd or self.session.cwd
        self.session.state = SessionState.RUNNING
        self.session.current_shell = profile.label
        self.backend = self._create_backend(self.session)
        self._replace_terminal_widget()
        self.shell_label.setText(profile.label)
        self._on_session_updated(self.session)
        self.terminal.display_system_message(f"已切换到 {profile.label}")

    def _replace_terminal_widget(self):
        layout = self.layout()
        if not layout:
            return
        index = layout.indexOf(self.terminal)
        layout.removeWidget(self.terminal)
        self.terminal.deleteLater()
        self.terminal = TerminalWidget(
            self.backend,
            command_handler=self._handle_pre_send,
            app_config=self._app_config
        )
        self.terminal.exit_received.connect(self._handle_backend_exit)
        layout.insertWidget(max(1, index), self.terminal, stretch=1)
        self.terminal.input_field.setFocus(Qt.FocusReason.OtherFocusReason)

    def _create_backend(self, session: Session) -> TerminalBackend:
        args = list(session.args)
        if self._is_wsl_command(session.cmd) and not args:
            args = self._default_wsl_args()
            session.args = list(args)
        return TerminalBackend(
            session.cmd,
            args,
            session.cwd,
            session.env,
            encoding=session.encoding,
        )

    def _is_wsl_command(self, command: str) -> bool:
        return "wsl" in command.lower()

    def _default_wsl_args(self) -> List[str]:
        return [
            "--",
            "bash",
            "-lc",
            "source ~/.bashrc >/dev/null 2>&1; exec bash -l",
        ]


def _clear_layout(layout: QVBoxLayout | QHBoxLayout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
        child_layout = item.layout()
        if child_layout:
            _clear_layout(child_layout)  # type: ignore[arg-type]


class MainWindow(QMainWindow):
    def __init__(self, config_path: str = "config/app.yaml", template_path: str = "config/sessions.yaml"):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self._ensure_pywinpty()
        self.app_config = load_app_config(config_path)
        bailian = None
        if self.app_config.bailian.enabled and self.app_config.bailian.effective_key():
            bailian = BailianClient(
                api_key=self.app_config.bailian.effective_key(),
                model=self.app_config.bailian.model,
                endpoint=self.app_config.bailian.endpoint,
            )
        templates = load_session_templates(template_path)
        self.manager = SessionManager(templates, bailian_client=bailian)
        self.manager.session_created.connect(self._on_session_created)
        self.manager.session_removed.connect(self._on_session_removed)
        self.manager.session_updated.connect(self._on_session_updated)

        self._session_views: Dict[str, SessionDetailWidget] = {}
        self._session_items: Dict[str, QListWidgetItem] = {}
        self._session_list_widgets: Dict[str, SessionListItemWidget] = {}

        self._build_ui()
        self._setup_shortcuts()
        self._load_initial_sessions()

    def _build_ui(self):
        toolbar = QToolBar("Templates")
        self.addToolBar(toolbar)
        self.template_selector = QComboBox()
        for tpl in self.manager.list_templates():
            self.template_selector.addItem(tpl.name, tpl.id)
        toolbar.addWidget(QLabel("模板:"))
        toolbar.addWidget(self.template_selector)
        create_btn = QPushButton("创建会话")
        create_btn.clicked.connect(self._handle_create_session)
        toolbar.addWidget(create_btn)
        help_btn = QPushButton("?")
        help_btn.setToolTip("查看快捷键提示")
        help_btn.clicked.connect(self._show_shortcuts)
        toolbar.addWidget(help_btn)

        splitter = QSplitter()
        left_container = QWidget()
        left_layout = QVBoxLayout()
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索会话/描述/路径")
        self.search_input.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self.search_input)
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("全部标签", None)
        self.tag_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.tag_filter)
        left_layout.addLayout(filter_row)
        self.session_list = QListWidget()
        self.session_list.currentRowChanged.connect(self._on_session_selected)
        left_layout.addWidget(self.session_list)
        left_container.setLayout(left_layout)
        splitter.addWidget(left_container)

        self.terminal_stack = QStackedWidget()
        self.empty_state = QLabel(
            "还没有任何会话。\n点击“创建会话”，或在 config/sessions.yaml 中配置模板。"
        )
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setWordWrap(True)
        self.terminal_stack.addWidget(self.empty_state)
        splitter.addWidget(self.terminal_stack)
        splitter.setStretchFactor(1, 1)

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._populate_tag_filter()
        self.terminal_stack.setCurrentWidget(self.empty_state)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._handle_create_session)
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self._handle_close_session)
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(lambda: self._select_relative_session(1))
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(lambda: self._select_relative_session(-1))
        QShortcut(QKeySequence("F5"), self).activated.connect(self._run_default_action)

    def _populate_tag_filter(self):
        """Populate tag filter with tags from templates."""
        tags = sorted({tag for tpl in self.manager.list_templates() for tag in tpl.tags})
        for tag in tags:
            self.tag_filter.addItem(tag, tag)

    def _refresh_tag_filter(self):
        """Refresh tag filter with current session tags."""
        # Save current selection
        current_tag = self.tag_filter.currentData()

        # Clear and rebuild
        self.tag_filter.clear()
        self.tag_filter.addItem("全部标签", None)

        # Collect all unique tags from templates and current sessions
        tags = set()
        for tpl in self.manager.list_templates():
            tags.update(tpl.tags)
        for session in self.manager.sessions.values():
            tags.update(session.tags)

        # Add sorted tags
        for tag in sorted(tags):
            self.tag_filter.addItem(tag, tag)

        # Restore selection if possible
        if current_tag:
            index = self.tag_filter.findData(current_tag)
            if index >= 0:
                self.tag_filter.setCurrentIndex(index)

    def _load_initial_sessions(self):
        if not self.manager.list_templates():
            QMessageBox.information(self, "提示", "未找到任何模板，先在 config/sessions.yaml 中配置")
            return

        # Try to restore previous sessions first
        restored_count = self.manager.restore_state()

        # If no sessions were restored, create a default one
        if restored_count == 0:
            first_template = self.manager.list_templates()[0]
            self.manager.create_session(first_template.id)

    def _handle_create_session(self):
        data = self.template_selector.currentData()
        if not data:
            return
        overrides = SessionOverrides()
        runtime = {"project": "default", "env": "local"}
        self.manager.create_session(data, overrides, runtime)

    def _handle_close_session(self):
        session_id = self._get_current_session_id()
        if session_id:
            self.manager.remove_session(session_id)

    def _run_default_action(self):
        session_id = self._get_current_session_id()
        if not session_id:
            return
        view = self._session_views.get(session_id)
        if not view:
            return
        if not view.run_default_action():
            QMessageBox.information(self, "提示", "当前会话未配置常用操作")

    def _select_relative_session(self, delta: int):
        visible_rows = [idx for idx in range(self.session_list.count()) if not self.session_list.item(idx).isHidden()]
        if not visible_rows:
            return
        current_row = self.session_list.currentRow()
        if current_row not in visible_rows:
            target_row = visible_rows[0]
        else:
            pos = visible_rows.index(current_row)
            target_row = visible_rows[(pos + delta) % len(visible_rows)]
        self.session_list.setCurrentRow(target_row)

    def _get_current_session_id(self) -> Optional[str]:
        item = self.session_list.currentItem()
        if not item or item.isHidden():
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _apply_filters(self):
        query = self.search_input.text().strip().lower()
        tag_filter = self.tag_filter.currentData()
        for idx in range(self.session_list.count()):
            item = self.session_list.item(idx)
            session_id = item.data(Qt.ItemDataRole.UserRole)
            session = self.manager.sessions.get(session_id)  # type: ignore[attr-defined]
            if not session:
                item.setHidden(True)
                continue
            matches = True
            if query:
                haystack = " ".join(
                    [
                        session.display_name.lower(),
                        session.description.lower(),
                        (session.cwd or "").lower(),
                    ]
                )
                matches = query in haystack
            if matches and tag_filter:
                matches = tag_filter in session.tags
            item.setHidden(not matches)
        current = self.session_list.currentItem()
        if not current or current.isHidden():
            self._select_first_visible()

    def _select_first_visible(self):
        for idx in range(self.session_list.count()):
            item = self.session_list.item(idx)
            if not item.isHidden():
                self.session_list.setCurrentRow(idx)
                return
        self.session_list.clearSelection()
        self.terminal_stack.setCurrentWidget(self.empty_state)

    def _focus_on_session(self, session_id: str):
        item = self._session_items.get(session_id)
        view = self._session_views.get(session_id)
        if not item or not view:
            return
        row = self.session_list.row(item)
        self.session_list.setCurrentRow(row)
        self.terminal_stack.setCurrentWidget(view)
        view.focus_terminal()

    def _on_session_created(self, session: Session):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, session.id)
        widget = SessionListItemWidget(session)
        item.setSizeHint(widget.sizeHint())
        self.session_list.addItem(item)
        self.session_list.setItemWidget(item, widget)
        self._session_items[session.id] = item
        self._session_list_widgets[session.id] = widget

        detail = SessionDetailWidget(session, self.manager.update_session, self.app_config)
        self._session_views[session.id] = detail
        self.terminal_stack.addWidget(detail)

        # Refresh tag filter with new tags
        self._refresh_tag_filter()

        self._apply_filters()
        self._focus_on_session(session.id)
        self._refresh_placeholder_visibility()

    def _on_session_removed(self, session: Session):
        item = self._session_items.pop(session.id, None)
        widget = self._session_list_widgets.pop(session.id, None)
        if item:
            row = self.session_list.row(item)
            self.session_list.takeItem(row)
        if widget:
            widget.deleteLater()
        detail = self._session_views.pop(session.id, None)
        if detail:
            detail.shutdown()
            self.terminal_stack.removeWidget(detail)
            detail.deleteLater()
        self._refresh_placeholder_visibility()
        self._select_first_visible()

    def _on_session_updated(self, session: Session):
        view = self._session_views.get(session.id)
        if view:
            view.refresh(session)
        widget = self._session_list_widgets.get(session.id)
        if widget:
            widget.refresh(session)

        # Refresh tag filter in case tags were updated
        self._refresh_tag_filter()

        self._apply_filters()

    def _refresh_placeholder_visibility(self):
        if not self._session_views:
            self.terminal_stack.setCurrentWidget(self.empty_state)

    def _on_session_selected(self, row: int):
        if row < 0:
            self.terminal_stack.setCurrentWidget(self.empty_state)
            return
        item = self.session_list.item(row)
        if not item or item.isHidden():
            self.terminal_stack.setCurrentWidget(self.empty_state)
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        view = self._session_views.get(session_id)
        if view:
            self.terminal_stack.setCurrentWidget(view)
            view.focus_terminal()

    def _show_shortcuts(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("快捷键")
        layout = QVBoxLayout(dialog)
        shortcuts = [
            ("Ctrl+N", "新建会话"),
            ("Ctrl+W", "关闭当前会话"),
            ("Ctrl+Tab", "切换到下一个可见会话"),
            ("Ctrl+Shift+Tab", "切换到上一个可见会话"),
            ("F5", "执行第一个常用操作"),
        ]
        for keys, desc in shortcuts:
            row = QHBoxLayout()
            key_label = QLabel(keys)
            key_label.setStyleSheet("font-weight: bold;")
            row.addWidget(key_label)
            row.addWidget(QLabel(desc), stretch=1)
            layout.addLayout(row)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()

    def _ensure_pywinpty(self):
        if os.name != "nt":
            return
        from .terminal_backend import pywinpty

        if pywinpty is None:
            QMessageBox.critical(
                self,
                "缺少依赖",
                "WinConsole 需要安装 pywinpty 才能在 Windows 上提供交互式终端。\n"
                "请在当前环境中执行以下命令后重启应用：\n"
                "  pip install pywinpty\n或\n  conda install -c conda-forge pywinpty",
            )
            raise SystemExit(1)

    def closeEvent(self, event):
        """Handle window close event - save session state before closing."""
        # Save current sessions to disk
        self.manager.save_state()

        # Shutdown all session backends
        for view in self._session_views.values():
            view.shutdown()

        event.accept()
