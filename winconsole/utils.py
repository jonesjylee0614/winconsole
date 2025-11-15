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

    def suggest_tab_name(self, context: Dict[str, str]) -> Optional[str]:
        prompt = (
            "You are an assistant that crafts concise terminal tab titles.\n"
            "Use <= 24 characters. Avoid punctuation beyond dash/space.\n"
            f"Context: {json.dumps(context, ensure_ascii=False)}"
        )
        try:
            response = self.generate(prompt)
            candidate = response.text.strip()
            if not candidate:
                return None
            candidate = candidate.splitlines()[0].strip()
            return candidate[:48]
        except BailianError as exc:
            LOG.warning("Bailian suggestion failed: %s", exc)
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
