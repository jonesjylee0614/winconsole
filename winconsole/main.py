from __future__ import annotations

import logging
import sys
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - UI layer
    raise RuntimeError("PyQt6 is required to launch the application") from exc

from .constants import (
    APP_NAME,
    APP_ORG_NAME,
    DEFAULT_CONFIG_DIR,
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
)
from .main_window import MainWindow


def setup_logging(log_level: str = DEFAULT_LOG_LEVEL) -> None:
    """Configure global logging for WinConsole.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory
    log_dir = Path.home() / DEFAULT_CONFIG_DIR / DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create formatters
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # File handler (always INFO level or higher)
    log_file = log_dir / DEFAULT_LOG_FILE
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Console handler (uses specified log level)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Log startup message
    logging.info("=" * 60)
    logging.info("WinConsole Manager starting")
    logging.info("Log file: %s", log_file)
    logging.info("=" * 60)


def main():
    """Launch the WinConsole Manager application."""
    # Setup logging first
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG_NAME)

    try:
        window = MainWindow()
        window.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        window.show()

        logging.info("Application window displayed")
        exit_code = app.exec()

        logging.info("Application exiting with code %d", exit_code)
        sys.exit(exit_code)

    except Exception as exc:
        logging.exception("Fatal error during application startup: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
