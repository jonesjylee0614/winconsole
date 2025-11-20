from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .config_loader import load_app_config, load_session_templates
from .constants import APP_NAME
from .session_manager import SessionManager
from .ui.session_detail import SessionDetailWidget
from .ui.session_list import SessionListItemWidget
from .ui.styles import MAIN_WINDOW_STYLESHEET
from .utils import BailianClient


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
        # Apply modern dark theme matching PowerShell aesthetics
        self.setStyleSheet(MAIN_WINDOW_STYLESHEET)

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
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)
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

        # Collect all unique tags from templates and current sessions
        tags = set()
        for tpl in self.manager.list_templates():
            tags.update(tpl.tags)
        for session in self.manager.sessions.values():
            tags.update(session.tags)
        
        sorted_tags = sorted(tags)

        # Check if we really need to update (optimization)
        current_items = [self.tag_filter.itemText(i) for i in range(1, self.tag_filter.count())]
        if current_items == sorted_tags:
            return

        # Clear and rebuild
        self.tag_filter.clear()
        self.tag_filter.addItem("全部标签", None)

        for tag in sorted_tags:
            self.tag_filter.addItem(tag, tag)

        # Restore selection if possible
        index = self.tag_filter.findData(current_tag)
        if index >= 0:
            self.tag_filter.setCurrentIndex(index)

    def _load_initial_sessions(self):
        # In a real app, we might load persisted sessions here
        pass

    def _ensure_pywinpty(self):
        try:
            import winpty  # noqa: F401
        except ImportError:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Missing Dependency",
                "pywinpty is required but not installed.\nPlease install it with: pip install pywinpty"
            )

    def _handle_create_session(self):
        template_id = self.template_selector.currentData()
        if not template_id:
            return
        self.manager.create_session(template_id)

    def _on_session_created(self, session):
        # Create list item
        item = QListWidgetItem(self.session_list)
        item.setData(Qt.ItemDataRole.UserRole, session.id)
        # Set size hint for custom widget
        item.setSizeHint(SessionListItemWidget(session).sizeHint())
        self.session_list.addItem(item)
        self._session_items[session.id] = item

        # Create custom widget for list item
        widget = SessionListItemWidget(session)
        self.session_list.setItemWidget(item, widget)
        self._session_list_widgets[session.id] = widget

        # Create detail view
        detail = SessionDetailWidget(session, self._on_session_updated_from_view, self.app_config)
        self.terminal_stack.addWidget(detail)
        self._session_views[session.id] = detail

        # Select the new session
        self.session_list.setCurrentItem(item)
        
        # Update tags
        self._refresh_tag_filter()

    def _on_session_removed(self, session_id: str):
        if session_id in self._session_views:
            view = self._session_views.pop(session_id)
            self.terminal_stack.removeWidget(view)
            view.shutdown()
            view.deleteLater()

        if session_id in self._session_items:
            item = self._session_items.pop(session_id)
            row = self.session_list.row(item)
            self.session_list.takeItem(row)
            
        if session_id in self._session_list_widgets:
            self._session_list_widgets.pop(session_id)

        if self.session_list.count() == 0:
            self.terminal_stack.setCurrentWidget(self.empty_state)
            
        # Update tags
        self._refresh_tag_filter()

    def _on_session_updated(self, session):
        if session.id in self._session_list_widgets:
            self._session_list_widgets[session.id].refresh(session)
        if session.id in self._session_views:
            self._session_views[session.id].refresh(session)
        
        # Update tags (in case tags changed)
        self._refresh_tag_filter()

    def _on_session_updated_from_view(self, session):
        # Callback from detail view (e.g. description changed)
        self.manager.update_session(session)

    def _on_session_selected(self, row: int):
        if row < 0:
            return
        item = self.session_list.item(row)
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id in self._session_views:
            view = self._session_views[session_id]
            self.terminal_stack.setCurrentWidget(view)
            view.focus_terminal()

    def _handle_close_session(self):
        item = self.session_list.currentItem()
        if not item:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        self.manager.remove_session(session_id)

    def _select_relative_session(self, delta: int):
        count = self.session_list.count()
        if count <= 1:
            return
        current = self.session_list.currentRow()
        next_row = (current + delta) % count
        self.session_list.setCurrentRow(next_row)

    def _run_default_action(self):
        current_widget = self.terminal_stack.currentWidget()
        if isinstance(current_widget, SessionDetailWidget):
            current_widget.run_default_action()

    def _show_shortcuts(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "快捷键",
            "Ctrl+N: 创建新会话\n"
            "Ctrl+W: 关闭当前会话\n"
            "Ctrl+Tab: 下一个会话\n"
            "Ctrl+Shift+Tab: 上一个会话\n"
            "F5: 运行默认操作\n"
            "Ctrl+F: 在终端中查找"
        )

    def _apply_filters(self):
        search_text = self.search_input.text().lower()
        tag_filter = self.tag_filter.currentData()

        for i in range(self.session_list.count()):
            item = self.session_list.item(i)
            session_id = item.data(Qt.ItemDataRole.UserRole)
            session = self.manager.sessions.get(session_id)
            
            if not session:
                continue

            # Check tag filter
            if tag_filter and tag_filter not in session.tags:
                item.setHidden(True)
                continue

            # Check search text
            if search_text:
                matches = (
                    search_text in session.display_name.lower() or
                    search_text in (session.description or "").lower() or
                    search_text in (session.cwd or "").lower()
                )
                if not matches:
                    item.setHidden(True)
                    continue

            item.setHidden(False)
