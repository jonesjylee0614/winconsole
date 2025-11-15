from __future__ import annotations

import itertools
import logging
from typing import Dict, Iterable, List, Optional

from .models import Session, SessionOverrides, SessionState, SessionTemplate, merge_metadata
from .utils import EventHook

LOG = logging.getLogger("winconsole")


class SessionManager:
    def __init__(self, templates: Iterable[SessionTemplate], bailian_client=None):
        self.templates: Dict[str, SessionTemplate] = {tpl.id: tpl for tpl in templates}
        self.sessions: Dict[str, Session] = {}
        self.session_created = EventHook()
        self.session_removed = EventHook()
        self.session_updated = EventHook()
        self._name_counters: Dict[str, itertools.count] = {}
        self._bailian = bailian_client

    # Template operations
    def list_templates(self) -> List[SessionTemplate]:
        return list(self.templates.values())

    def get_template(self, template_id: str) -> SessionTemplate:
        return self.templates[template_id]

    # Session operations
    def create_session(
        self,
        template_id: str,
        overrides: Optional[SessionOverrides] = None,
        runtime_state: Optional[Dict[str, str]] = None,
    ) -> Session:
        template = self.get_template(template_id)
        runtime_state = runtime_state or {}
        index = self._next_index(template.id)
        name = self.derive_tab_title(template, overrides, runtime_state, index)
        session = Session.from_template(template, display_name=name, overrides=overrides)
        ai_name = self._maybe_apply_bailian(template, overrides, runtime_state, index)
        if ai_name:
            session.display_name = ai_name
        session.state = SessionState.RUNNING
        self.sessions[session.id] = session
        self.session_created.emit(session)
        return session

    def remove_session(self, session_id: str):
        session = self.sessions.pop(session_id, None)
        if session:
            self.session_removed.emit(session)

    def update_session(self, session: Session):
        self.sessions[session.id] = session
        self.session_updated.emit(session)

    # Naming
    def derive_tab_title(
        self,
        template: SessionTemplate,
        overrides: Optional[SessionOverrides],
        runtime_state: Optional[Dict[str, str]],
        index: int,
    ) -> str:
        runtime_state = runtime_state or {}
        if overrides and overrides.custom_name:
            return overrides.custom_name
        context = merge_metadata(template, overrides, runtime_state, index=index)
        template_format = template.title_format
        if template_format:
            try:
                return template_format.format_map(_SafeDict(context))
            except KeyError as exc:
                LOG.debug("Missing placeholder %s in title_format", exc)
        default_name = f"{template.name}#{index}"
        collision_guard = default_name
        suffix = 1
        while any(sess.display_name == collision_guard for sess in self.sessions.values()):
            collision_guard = f"{default_name}-{suffix}"
            suffix += 1
        return collision_guard

    def _next_index(self, template_id: str) -> int:
        counter = self._name_counters.get(template_id)
        if not counter:
            counter = itertools.count(1)
            self._name_counters[template_id] = counter
        return next(counter)

    def _maybe_apply_bailian(
        self,
        template: SessionTemplate,
        overrides: Optional[SessionOverrides],
        runtime: Dict[str, str],
        index: int,
    ) -> Optional[str]:
        if not self._bailian or not getattr(self._bailian, "enabled", lambda: False)():
            return None
        context = merge_metadata(template, overrides, runtime, index=index)
        context["existing"] = [s.display_name for s in self.sessions.values()]
        suggestion = self._bailian.suggest_tab_name(context)
        if suggestion:
            LOG.info("Bailian suggested tab name: %s", suggestion)
        return suggestion


class _SafeDict(dict):
    def __missing__(self, key):
        return ""
