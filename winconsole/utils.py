from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, Optional

LOG = logging.getLogger("winconsole")


class BailianError(RuntimeError):
    pass


@dataclass
class BailianResponse:
    text: str
    metadata: Dict[str, str]


class BailianClient:
    def __init__(self, *, api_key: str, model: str, endpoint: str, timeout: float = 5.0):
        self.api_key = api_key.strip()
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout

    def enabled(self) -> bool:
        return bool(self.api_key and self.endpoint)

    def generate(self, prompt: str) -> BailianResponse:
        if not self.enabled():
            raise BailianError("Bailian client misconfigured")
        payload = {
            "model": self.model,
            "input": {"messages": [{"role": "user", "content": prompt}]},
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise BailianError(f"HTTP error {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise BailianError(f"Network error {exc.reason}") from exc
        text = (
            parsed.get("output", {})
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return BailianResponse(text=text.strip(), metadata={"request_id": parsed.get("request_id", "")})

    def suggest_tab_name(self, context: Dict[str, str], max_retries: int = 2) -> Optional[str]:
        """Suggest a tab name using Bailian AI with retry logic.

        Args:
            context: Context information for the suggestion
            max_retries: Maximum number of retry attempts (default: 2)

        Returns:
            Suggested tab name or None if all attempts fail
        """
        prompt = (
            "You are an assistant that crafts concise terminal tab titles.\n"
            "Use <= 24 characters. Avoid punctuation beyond dash/space.\n"
            f"Context: {json.dumps(context, ensure_ascii=False)}"
        )

        for attempt in range(max_retries + 1):
            try:
                response = self.generate(prompt)
                candidate = response.text.strip()
                if not candidate:
                    return None
                candidate = candidate.splitlines()[0].strip()
                return candidate[:48]
            except BailianError as exc:
                if attempt < max_retries:
                    # Exponential backoff: 0.5s, 1s
                    delay = 0.5 * (2 ** attempt)
                    LOG.warning("Bailian suggestion failed (attempt %d/%d): %s. Retrying in %.1fs...",
                               attempt + 1, max_retries + 1, exc, delay)
                    time.sleep(delay)
                    continue
                else:
                    LOG.warning("Bailian suggestion failed after %d attempts: %s", max_retries + 1, exc)
                    return None

        return None


class EventHook:
    def __init__(self):
        self._subscribers: list[Callable] = []
        self._lock = threading.Lock()

    def connect(self, callback: Callable):
        with self._lock:
            self._subscribers.append(callback)

    def emit(self, *args, **kwargs):
        with self._lock:
            subscribers = list(self._subscribers)
        for callback in subscribers:
            callback(*args, **kwargs)


def expand_env(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def throttle(delay: float):
    def decorator(func):
        last_call = {"timestamp": 0.0}
        lock = threading.Lock()

        def wrapper(*args, **kwargs):
            with lock:
                now = time.monotonic()
                if now - last_call["timestamp"] < delay:
                    return None
                last_call["timestamp"] = now
            return func(*args, **kwargs)

        return wrapper

    return decorator


def is_tui_program(cmd: str) -> bool:
    """Check if a command is a TUI program that requires full terminal emulation.

    Args:
        cmd: Command name or path

    Returns:
        True if the command is a known TUI program
    """
    from .constants import TUI_PROGRAMS

    # Get just the program name (without path)
    program_name = os.path.basename(cmd).lower()

    # Remove common extensions
    if program_name.endswith('.exe'):
        program_name = program_name[:-4]

    return program_name in TUI_PROGRAMS


def open_in_external_terminal(cmd: str, args: list[str], cwd: str) -> bool:
    """Open a command in an external terminal (Windows Terminal or cmd).

    Args:
        cmd: Command to run
        args: Command arguments
        cwd: Working directory

    Returns:
        True if successfully launched
    """
    import subprocess
    import shutil

    # Combine command and args for display
    full_cmd = cmd
    if args:
        full_cmd += ' ' + ' '.join(args)

    try:
        # Try Windows Terminal first (wt.exe)
        if shutil.which('wt.exe') or shutil.which('wt'):
            # Windows Terminal syntax:
            # wt.exe -d <directory> -- <command> <args...>
            # Note: No '--' between -d and command, just before the actual command
            wt_cmd = ['wt.exe', '-d', cwd, cmd] + args
            LOG.info(f"Launching Windows Terminal: {wt_cmd}")
            subprocess.Popen(wt_cmd, shell=False)
            LOG.info(f"Opened in Windows Terminal: {full_cmd}")
            return True
    except Exception as e:
        LOG.warning(f"Failed to open in Windows Terminal: {e}")

    try:
        # Fallback to cmd.exe
        # Use /k to keep window open after command exits
        cmd_exe = ['cmd.exe', '/k', f'cd /d "{cwd}" && {full_cmd}']
        LOG.info(f"Launching cmd.exe: {cmd_exe}")
        subprocess.Popen(cmd_exe, shell=False, cwd=cwd)
        LOG.info(f"Opened in cmd.exe: {full_cmd}")
        return True
    except Exception as e:
        LOG.error(f"Failed to open in cmd.exe: {e}")
        return False
