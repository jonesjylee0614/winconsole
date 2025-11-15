from __future__ import annotations

import sys

try:
    from PyQt6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - UI layer
    raise RuntimeError("PyQt6 is required to launch the application") from exc

from .main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
