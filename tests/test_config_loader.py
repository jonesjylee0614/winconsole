from __future__ import annotations

import os
from pathlib import Path

from winconsole.config_loader import load_app_config, load_session_templates


def test_load_session_templates(tmp_path: Path):
    data = """
- id: alpha
  name: Alpha
  cmd: python
  args: ["-V"]
  cwd: "~"
  tags: ["test"]
  description: "Sample session"
  hints:
    - "hint 1"
  actions:
    - label: "Show version"
      command: "python -V"
  encoding: "latin-1"
"""
    target = tmp_path / "sessions.yaml"
    target.write_text(data, encoding="utf-8")
    templates = load_session_templates(str(target))
    assert len(templates) == 1
    tpl = templates[0]
    assert tpl.id == "alpha"
    assert tpl.args == ["-V"]
    assert tpl.description == "Sample session"
    assert tpl.hints == ["hint 1"]
    assert tpl.actions[0].label == "Show version"
    assert tpl.actions[0].command == "python -V"
    assert tpl.encoding == "latin-1"


def test_load_app_config_with_env_override(tmp_path: Path, monkeypatch):
    data = """
theme: "dark"
font_family: "Fira Code"
font_size: 14
bailian:
  enabled: true
  api_key: "SHOULD_NOT_USE"
  model: "qwen-turbo"
  endpoint: "https://example.com"
"""
    target = tmp_path / "app.yaml"
    target.write_text(data, encoding="utf-8")
    monkeypatch.setenv("BAILIAN_API_KEY", "ENV_KEY")
    config = load_app_config(str(target))
    assert config.theme == "dark"
    assert config.font_family == "Fira Code"
    assert config.font_size == 14
    assert config.bailian.enabled is True
    assert config.bailian.api_key == "ENV_KEY"
    assert config.bailian.model == "qwen-turbo"
