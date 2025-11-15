"""
WinConsole Manager - PyQt based session orchestrator.
"""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]


def _load_version() -> str:
    try:
        return version("winconsole")
    except PackageNotFoundError:
        return "0.1.0"


__version__ = _load_version()
