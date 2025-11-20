from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..constants import ACTION_BUTTON_RESET_DELAY_MS
from ..models import Session, SessionAction, SessionState
from ..terminal_backend import TerminalBackend
from ..terminal_widget import TerminalWidget
from ..utils import is_tui_program, open_in_external_terminal


@dataclass(frozen=True)
class _ShellProfile:
    aliases: List[str]
    label: str
    cmd: str
    args: List[str]
    encoding: str
    cwd: Optional[str] = None


def _clear_layout(layout: QVBoxLayout | QHBoxLayout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
        child_layout = item.layout()
        if child_layout:
            _clear_layout(child_layout)  # type: ignore[arg-type]


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

        # Add "Open in External Terminal" button for TUI programs
        if is_tui_program(session.cmd):
            self.external_btn = QToolButton()
            self.external_btn.setText("在外部终端打开")
            self.external_btn.setToolTip("此程序需要完整终端支持，建议在 Windows Terminal 中运行")
            self.external_btn.clicked.connect(self._handle_open_external)
            self.external_btn.setStyleSheet("background-color: #FF9800; color: white;")
            top_row.addWidget(self.external_btn)

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

        # Show TUI warning if applicable
        if is_tui_program(session.cmd):
            self._show_tui_warning()

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
        self.terminal.output_view.setFocus(Qt.FocusReason.OtherFocusReason)

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
        """Handle commands before sending to backend.

        Returns True if command was handled internally.
        """
        key = text.strip()
        if not key:
            return False

        tokens = key.split()
        command = tokens[0].lower()

        # Check if it's a TUI program
        if is_tui_program(command):
            # Create a custom message box with three options
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("检测到 TUI 程序")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText(
                f"⚠️  检测到 TUI 程序: {command}\n\n"
                f"此程序需要完整的终端模拟器支持（VT100/xterm），\n"
                f"在 WinConsole 中可能无法正常工作（菜单不显示、输入异常等）。"
            )
            msg_box.setInformativeText("请选择如何处理:")

            # Add three buttons
            run_cmd_btn = msg_box.addButton(
                f"运行 {command}",
                QMessageBox.ButtonRole.YesRole
            )
            run_cmd_btn.setToolTip(f"在外部终端执行: {key}")

            open_shell_btn = msg_box.addButton(
                "打开交互式 Shell",
                QMessageBox.ButtonRole.AcceptRole
            )
            open_shell_btn.setToolTip("打开外部终端的交互式 shell，你可以手动运行命令")

            try_here_btn = msg_box.addButton(
                "仍在此处尝试",
                QMessageBox.ButtonRole.NoRole
            )
            try_here_btn.setToolTip("在当前 WinConsole 中运行（可能有问题）")

            msg_box.setDefaultButton(run_cmd_btn)

            # Show dialog and get result
            msg_box.exec()
            reply = msg_box.clickedButton()

            if reply == run_cmd_btn:
                # Option 1: Run command in external terminal
                cmd_to_run = self.session.cmd
                args_to_run = []

                # Construct proper command based on current shell type
                if self._is_wsl_command(cmd_to_run):
                    # For WSL, use: wsl bash -l -c "command"
                    # -l ensures login shell (loads .bashrc, etc.)
                    args_to_run = ["bash", "-l", "-c", key]
                elif "bash" in cmd_to_run.lower():
                    # For bash: bash -l -c "command"
                    args_to_run = ["-l", "-c", key]
                elif "powershell" in cmd_to_run.lower():
                    # For PowerShell: powershell -Command "command"
                    args_to_run = ["-Command", key]
                elif "cmd" in cmd_to_run.lower():
                    # For cmd: cmd /k "command"
                    args_to_run = ["/k", key]
                else:
                    # Fallback: just run the command directly
                    cmd_to_run = command
                    args_to_run = tokens[1:]

                success = open_in_external_terminal(
                    cmd_to_run,
                    args_to_run,
                    self.session.cwd
                )

                if success:
                    self.terminal.display_system_message(
                        f"✓ 已在外部终端启动: {key}\n"
                        f"提示: 如果外部终端报错 \"找不到文件\"，可能是因为:\n"
                        f"  1. 命令 '{command}' 不在 PATH 中\n"
                        f"  2. 需要先激活特定环境 (如 conda activate)\n"
                        f"  3. 命令拼写错误\n"
                        f"\n建议: 如果命令总是失败，请选择 \"打开交互式 Shell\" 选项。\n"
                    )
                else:
                    self.terminal.display_system_message(
                        f"✗ 无法启动外部终端\n"
                        f"请手动在 Windows Terminal 中:\n"
                        f"  1. 启动 WSL\n"
                        f"  2. 切换到目录: {self.session.cwd}\n"
                        f"  3. 运行命令: {key}\n"
                    )

                return True  # Command handled, don't send to backend

            elif reply == open_shell_btn:
                # Option 2: Open interactive shell in external terminal
                cmd_to_run = self.session.cmd
                args_to_run = list(self.session.args) if self.session.args else []

                # For WSL/bash, just open the shell without running a command
                if self._is_wsl_command(cmd_to_run) and not args_to_run:
                    args_to_run = self._default_wsl_args()

                success = open_in_external_terminal(
                    cmd_to_run,
                    args_to_run,
                    self.session.cwd
                )

                if success:
                    self.terminal.display_system_message(
                        f"✓ 已在外部终端打开交互式 shell\n"
                        f"你可以手动运行: {key}\n"
                    )
                else:
                    self.terminal.display_system_message(
                        f"✗ 无法启动外部终端\n"
                    )

                return True  # Command handled, don't send to backend

            else:
                # Option 3: User chose to run in current terminal anyway
                self._warn_tui_command(command)
                # Fall through to let it run

        # Check for shell switching
        profile = self._alias_map.get(command)
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

    def _show_tui_warning(self):
        """Show warning for TUI programs that may not work correctly."""
        msg = (
            f"⚠️  检测到 TUI 程序：{os.path.basename(self.session.cmd)}\n\n"
            "WinConsole 是一个多标签进程管理器，不是完整的终端模拟器。\n"
            "TUI 程序（如 codex、vim、htop）需要完整的 VT100/xterm 支持，\n"
            "在当前环境中可能无法正常工作（菜单不显示、输入异常等）。\n\n"
            "建议点击顶部的 \"在外部终端打开\" 按钮，\n"
            "在 Windows Terminal 或 cmd 中运行以获得完整功能。"
        )
        self.terminal.display_system_message(msg)

    def _warn_tui_command(self, command: str):
        """Show inline warning when user tries to run a TUI program."""
        msg = (
            f"\n⚠️  警告：检测到 TUI 程序 '{command}'\n"
            "此程序需要完整的终端模拟器支持（VT100/xterm），在 WinConsole 中可能无法正常工作。\n"
            "如果遇到菜单无法选择、输入异常等问题，请使用以下方法之一：\n\n"
            "1. 点击顶部的橙色 \"在外部终端打开\" 按钮，在 Windows Terminal 中运行\n"
            "2. 或者手动在 Windows Terminal / cmd 中运行此命令\n"
        )
        self.terminal.display_system_message(msg)

    def _handle_open_external(self):
        """Open current session in external terminal (Windows Terminal or cmd)."""
        success = open_in_external_terminal(
            self.session.cmd,
            self.session.args,
            self.session.cwd
        )

        if success:
            msg = (
                f"已在外部终端打开 {self.session.display_name}\n\n"
                "提示：TUI 程序（如 codex、vim、htop）需要完整的终端仿真支持。\n"
                "在外部终端中，这些程序的交互功能将完全正常。"
            )
            QMessageBox.information(self, "已打开外部终端", msg)
        else:
            QMessageBox.warning(
                self,
                "打开失败",
                "无法启动外部终端。请确保系统中已安装 Windows Terminal 或 cmd.exe。"
            )

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
        self.terminal.output_view.setFocus(Qt.FocusReason.OtherFocusReason)

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
