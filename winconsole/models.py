from __future__ import annotations

import datetime as _dt
import itertools
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional


class SessionState(Enum):
    CREATED = auto()
    RUNNING = auto()
    EXITED = auto()


@dataclass
class SessionAction:
    label: str
    command: str


@dataclass
class SessionTemplate:
    id: str
    name: str
    cmd: str
    args: List[str] = field(default_factory=list)
    cwd: str = ""
    tags: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    title_format: Optional[str] = None
    description: Optional[str] = None
    hints: List[str] = field(default_factory=list)
    actions: List[SessionAction] = field(default_factory=list)
    encoding: Optional[str] = None

    def resolved_cwd(self) -> Path:
        raw = self.cwd or "."
        return Path(Path(raw).expanduser())


@dataclass
class SessionOverrides:
    custom_name: Optional[str] = None
    cwd: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Session:
    id: str
    template_id: str
    display_name: str
    cmd: str
    args: List[str]
    cwd: str
    tags: List[str]
    env: Dict[str, str]
    state: SessionState = SessionState.CREATED
    created_at: _dt.datetime = field(default_factory=_dt.datetime.utcnow)
    remarks: str = ""
    pid: Optional[int] = None
    description: str = ""
    hints: List[str] = field(default_factory=list)
    actions: List[SessionAction] = field(default_factory=list)
    encoding: Optional[str] = None
    current_shell: str = ""

    @classmethod
    def from_template(
        cls,
        template: SessionTemplate,
        *,
        display_name: str,
        overrides: Optional[SessionOverrides] = None,
    ) -> "Session":
        overrides = overrides or SessionOverrides()
        cwd = overrides.cwd or template.cwd
        env = {**template.env, **overrides.env}
        return cls(
            id=_generate_session_id(template.id),
            template_id=template.id,
            display_name=display_name,
            cmd=template.cmd,
            args=list(template.args),
            cwd=cwd,
            tags=list(template.tags),
            env=env,
            description=template.description or "",
            hints=list(template.hints),
            actions=[SessionAction(action.label, action.command) for action in template.actions],
            encoding=template.encoding,
            current_shell="",
        )


def _generate_session_id(template_id: str) -> str:
    timestamp = _dt.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    short = "".join(ch for ch in template_id if ch.isalnum())[:8]
    suffix = uuid.uuid4().hex[:6]
    return f"{short or 'session'}-{timestamp}-{suffix}"


@dataclass
class BailianConfig:
    enabled: bool = False
    api_key: str = ""
    model: str = "qwen-plus"
    endpoint: str = ""

    def effective_key(self) -> str:
        return self.api_key or ""


@dataclass
class AppConfig:
    theme: str = "vscode-dark"  # 默认使用 VS Code 深色主题
    font_family: str = "Cascadia Code"
    font_size: int = 12
    bailian: BailianConfig = field(default_factory=BailianConfig)


def merge_metadata(
    template: SessionTemplate,
    overrides: Optional[SessionOverrides],
    runtime: Dict[str, str],
    *,
    index: Optional[int] = None,
) -> Dict[str, str]:
    result = {
        "name": template.name,
        "template_id": template.id,
        "tags": ",".join(template.tags),
        "cwd": overrides.cwd if overrides and overrides.cwd else template.cwd,
    }
    if index is not None:
        result["index"] = str(index)
    if overrides:
        result.update(overrides.metadata)
    result.update({k: v for k, v in runtime.items() if v})
    return result


def sequence_counter():
    counter = itertools.count(1)
    return lambda: next(counter)
