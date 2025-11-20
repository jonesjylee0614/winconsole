MAIN_WINDOW_STYLESHEET = """
    QMainWindow {
        background-color: #1E1E1E;
    }
    QToolBar {
        background-color: #2D2D2D;
        border: none;
        padding: 4px;
        spacing: 8px;
    }
    QToolBar QLabel {
        color: #CCCCCC;
        padding: 2px;
    }
    QPushButton {
        background-color: #0E639C;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 2px;
    }
    QPushButton:hover {
        background-color: #1177BB;
    }
    QPushButton:pressed {
        background-color: #0D5A8F;
    }
    QComboBox {
        background-color: #3C3C3C;
        color: #CCCCCC;
        border: 1px solid #555555;
        padding: 4px;
        border-radius: 2px;
    }
    QComboBox:hover {
        border: 1px solid #007ACC;
    }
    QComboBox::drop-down {
        border: none;
    }
    QLineEdit {
        background-color: #3C3C3C;
        color: #CCCCCC;
        border: 1px solid #555555;
        padding: 4px;
        border-radius: 2px;
    }
    QLineEdit:focus {
        border: 1px solid #007ACC;
    }
    QListWidget {
        background-color: #252526;
        color: #CCCCCC;
        border: none;
        outline: none;
    }
    QListWidget::item {
        padding: 4px;
        border-bottom: 1px solid #3C3C3C;
    }
    QListWidget::item:selected {
        background-color: #094771;
    }
    QListWidget::item:hover {
        background-color: #2A2D2E;
    }
    QSplitter::handle {
        background-color: #3C3C3C;
        width: 1px;
    }
    QLabel {
        color: #CCCCCC;
    }
"""
