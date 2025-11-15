from __future__ import annotations

import os
import subprocess
import threading
import locale
from typing import Dict, List, Optional

from .utils import EventHook, expand_env

try:
    import winpty as pywinpty  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pywinpty = None


class TerminalBackend:
    """
    Simplified backend that reads stdout/stderr in a worker thread.
    Falls back to subprocess pipes when pywinpty is unavailable.
    """

    def __init__(
        self,
        cmd: str,
        args: Optional[List[str]] = None,
        cwd: str = "",
        env: Optional[Dict[str, str]] = None,
        encoding: Optional[str] = None,
    ):
        self.cmd = cmd
        self.args = args or []
        self.cwd = expand_env(cwd or os.getcwd())
        self.env = {**os.environ, **(env or {})}
        self.output = EventHook()
        self.exited = EventHook()
        self._process = None
        self._reader_thread: Optional[threading.Thread] = None
        self._pty_process = None
        self.encoding = encoding or _guess_encoding(cmd)

    def start(self):
        if self._process:
            return
        if pywinpty:
            self._start_pywinpty()
        else:
            self._start_subprocess()

    def send(self, data: str):
        payload = data
        if pywinpty and self._pty_process:
            self._pty_process.write(payload)
            return
        if self._process and self._process.stdin:
            stream = self._process.stdin
            if not stream:
                return
            encoded = _safe_encode(payload, self.encoding)
            stream.write(encoded)
            self._process.stdin.flush()

    def terminate(self):
        if self._pty_process:
            self._pty_process.close()
        if self._process:
            self._process.terminate()

    # Internal helpers
    def _start_pywinpty(self):  # pragma: no cover - requires pywinpty
        spawn = pywinpty.PtyProcess.spawn([self.cmd, *self.args], cwd=self.cwd, env=self.env)
        self._pty_process = spawn

        def reader():
            while True:
                try:
                    chunk = spawn.read(1024)
                except EOFError:
                    break
                if not chunk:
                    break
                self.output.emit(chunk)
            self.exited.emit(0)

        self._reader_thread = threading.Thread(target=reader, daemon=True)
        self._reader_thread.start()

    def _start_subprocess(self):
        self._process = subprocess.Popen(
            [self.cmd, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.cwd,
            env=self.env,
            bufsize=0,
            universal_newlines=False,
        )

        def reader():
            assert self._process is not None
            stdout = self._process.stdout
            assert stdout is not None
            while True:
                chunk = stdout.read(4096)
                if not chunk:
                    break
                text = _safe_decode(chunk, self.encoding)
                self.output.emit(text)
            rc = self._process.wait()
            self.exited.emit(rc)

        self._reader_thread = threading.Thread(target=reader, daemon=True)
        self._reader_thread.start()


def _guess_encoding(cmd: str) -> str:
    cmd_lower = cmd.lower()
    if "wsl" in cmd_lower or "bash" in cmd_lower or "/bin/" in cmd_lower:
        return "utf-8"
    try:
        encoding = locale.getpreferredencoding(False)
    except Exception:
        encoding = ""
    return encoding or "utf-8"


def _safe_encode(data: str, encoding: str) -> bytes:
    try:
        return data.encode(encoding, errors="replace")
    except LookupError:
        return data.encode("utf-8", errors="replace")


def _safe_decode(data: bytes, encoding: str) -> str:
    try:
        return data.decode(encoding, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")
