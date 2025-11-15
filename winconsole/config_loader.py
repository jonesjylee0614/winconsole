from __future__ import annotations

import os
from pathlib import Path
from typing import List

import yaml

from .models import AppConfig, BailianConfig, SessionAction, SessionTemplate


def _read_yaml(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_session_templates(path: str) -> List[SessionTemplate]:
    data = _read_yaml(Path(path))
    if not data:
        return []
    templates: List[SessionTemplate] = []
    for item in data:
        hints = [str(h) for h in item.get("hints", []) or [] if isinstance(h, str)]
        actions = []
        for action in item.get("actions", []) or []:
            if not isinstance(action, dict):
                continue
            label = action.get("label")
            command = action.get("command")
            if not label or not command:
                continue
            actions.append(SessionAction(label=label, command=command))
        templates.append(
            SessionTemplate(
                id=item["id"],
                name=item["name"],
                cmd=item["cmd"],
                args=item.get("args", []) or [],
                cwd=item.get("cwd", ""),
                tags=item.get("tags", []) or [],
                env=item.get("env", {}) or {},
                title_format=item.get("title_format"),
                description=item.get("description"),
                hints=hints,
                actions=actions,
                encoding=item.get("encoding"),
            )
        )
    return templates


def load_app_config(path: str) -> AppConfig:
    data = _read_yaml(Path(path)) or {}
    bailian_cfg = data.get("bailian", {}) or {}
    effective_key = bailian_cfg.get("api_key", "")
    env_key = os.environ.get("BAILIAN_API_KEY")
    if env_key:
        effective_key = env_key
    bailian = BailianConfig(
        enabled=bool(bailian_cfg.get("enabled", False)),
        api_key=effective_key,
        model=bailian_cfg.get("model", "qwen-plus"),
        endpoint=bailian_cfg.get("endpoint", ""),
    )
    return AppConfig(
        theme=data.get("theme", "light"),
        font_family=data.get("font_family", "Cascadia Code"),
        font_size=int(data.get("font_size", 12)),
        bailian=bailian,
    )
