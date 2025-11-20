from __future__ import annotations

import os
import subprocess
import sys
import threading
import locale
from typing import Dict, List, Optional

from .utils import EventHook, expand_env

try:
    import winpty as pywinpty  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pywinpty = None

# Import pty for Linux/WSL support
try:
    import pty
    import select
    import fcntl
    import struct
    import termios
    HAS_PTY = True
except ImportError:  # pragma: no cover - Windows without WSL
    HAS_PTY = False


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
        self._master_fd = None  # For Unix PTY
        self.encoding = encoding or _guess_encoding(cmd)

    def start(self):
        if self._process or self._master_fd:
            return
        if pywinpty:
            self._start_pywinpty()
        elif HAS_PTY and sys.platform != "win32":
            self._start_unix_pty()
        else:
            self._start_subprocess()

    def send(self, data: str):
        payload = data
        if pywinpty and self._pty_process:
            self._pty_process.write(payload)
            return
        if self._master_fd is not None:
            # Unix PTY
            try:
                encoded = _safe_encode(payload, self.encoding)
                os.write(self._master_fd, encoded)
            except OSError:
                pass  # PTY closed
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
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None
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
                except (EOFError, ConnectionAbortedError, OSError):
                    break
                if not chunk:
                    break
                self.output.emit(chunk)
            self.exited.emit(0)

        self._reader_thread = threading.Thread(target=reader, daemon=True)
        self._reader_thread.start()

    def _start_unix_pty(self):  # pragma: no cover - requires Unix/Linux
        """Start process with Unix PTY for full terminal support (interactive menus, etc)."""
        if not HAS_PTY:
            # Fallback to subprocess if PTY not available
            self._start_subprocess()
            return

        try:
            # Create a pseudo-terminal
            master_fd, slave_fd = pty.openpty()
            self._master_fd = master_fd

            # Set terminal size (default 80x24)
            _set_pty_size(master_fd, 24, 80)

            # Configure terminal for proper interactive behavior
            # Let the child process set its own terminal modes
            # We just ensure TERM is set correctly
            if 'TERM' not in self.env:
                self.env['TERM'] = 'xterm-256color'

            # Fork and exec in child process
            pid = os.fork()
            if pid == 0:
                # Child process
                os.close(master_fd)

                # Create new session and set controlling terminal
                os.setsid()

                # Set slave as stdin/stdout/stderr
                os.dup2(slave_fd, 0)  # stdin
                os.dup2(slave_fd, 1)  # stdout
                os.dup2(slave_fd, 2)  # stderr

                if slave_fd > 2:
                    os.close(slave_fd)

                # Change to working directory
                os.chdir(self.cwd)

                # Execute command
                os.execvpe(self.cmd, [self.cmd] + self.args, self.env)
            else:
                # Parent process
                os.close(slave_fd)
                self._process = type('Process', (), {'pid': pid})()  # Store PID

                # Set master to non-blocking
                flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
                fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

                def reader():
                    while True:
                        try:
                            # Use select to check if data is available
                            ready, _, _ = select.select([master_fd], [], [], 0.1)
                            if not ready:
                                # Check if child process is still alive
                                try:
                                    pid_status, status = os.waitpid(pid, os.WNOHANG)
                                    if pid_status != 0:
                                        # Process exited
                                        exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 1
                                        self.exited.emit(exit_code)
                                        break
                                except ChildProcessError:
                                    # Process already exited
                                    self.exited.emit(0)
                                    break
                                continue

                            chunk = os.read(master_fd, 4096)
                            if not chunk:
                                break
                            text = _safe_decode(chunk, self.encoding)
                            self.output.emit(text)
                        except OSError:
                            # PTY closed
                            break

                    # Clean up
                    try:
                        os.close(master_fd)
                    except OSError:
                        pass
                    self._master_fd = None

                    # Wait for child process
                    try:
                        os.waitpid(pid, 0)
                    except ChildProcessError:
                        pass

                self._reader_thread = threading.Thread(target=reader, daemon=True)
                self._reader_thread.start()

        except Exception as e:
            # Fallback to subprocess on any error
            import logging
            logging.warning(f"Failed to start Unix PTY: {e}, falling back to subprocess")
            if self._master_fd is not None:
                try:
                    os.close(self._master_fd)
                except OSError:
                    pass
                self._master_fd = None
            self._start_subprocess()

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


def _set_pty_size(fd: int, rows: int, cols: int):
    """Set the size of a PTY."""
    if not HAS_PTY:
        return
    try:
        # TIOCSWINSZ ioctl to set window size
        size = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, size)
    except Exception:
        pass  # Ignore errors setting PTY size
