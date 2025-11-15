from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from winconsole.models import SessionAction, SessionOverrides, SessionTemplate
from winconsole.session_manager import SessionManager


@dataclass
class DummyBailian:
    answer: Optional[str] = None

    def enabled(self):
        return True

    def suggest_tab_name(self, context: Dict[str, str]) -> Optional[str]:
        return self.answer


def _template(template_id: str, title_format: Optional[str] = None) -> SessionTemplate:
    return SessionTemplate(
        id=template_id,
        name=template_id.capitalize(),
        cmd="python",
        args=["-V"],
        cwd=".",
        tags=["x"],
        title_format=title_format,
    )


def test_session_manager_default_naming_sequence():
    manager = SessionManager([_template("alpha")])
    s1 = manager.create_session("alpha")
    s2 = manager.create_session("alpha")
    assert s1.display_name == "Alpha#1"
    assert s2.display_name.startswith("Alpha#")
    assert s1.id != s2.id


def test_session_manager_custom_format_and_override():
    manager = SessionManager([_template("beta", "{name}-{index}-{project}")])
    overrides = SessionOverrides(metadata={"project": "proj"})
    runtime = {"project": "console"}
    session = manager.create_session("beta", overrides, runtime)
    assert session.display_name == "Beta-1-console"


def test_session_manager_bailian_override():
    bailian = DummyBailian(answer="Intelligent Tab")
    manager = SessionManager([_template("gamma")], bailian_client=bailian)
    session = manager.create_session("gamma")
    assert session.display_name == "Intelligent Tab"


def test_session_inherits_template_metadata():
    template = SessionTemplate(
        id="delta",
        name="Delta",
        cmd="bash",
        description="Inspect delta app",
        hints=["run tests"],
        actions=[SessionAction(label="Run", command="npm test")],
        encoding="latin-1",
    )
    manager = SessionManager([template])
    session = manager.create_session("delta")
    assert session.description == "Inspect delta app"
    assert session.hints == ["run tests"]
    assert session.actions[0].command == "npm test"
    assert session.encoding == "latin-1"
    assert session.current_shell == ""
