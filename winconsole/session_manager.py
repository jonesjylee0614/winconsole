from __future__ import annotations

import itertools
import logging
from typing import Dict, Iterable, List, Optional

from .models import Session, SessionOverrides, SessionState, SessionTemplate, merge_metadata
from .persistence import SessionStatePersistence
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
        self._persistence = SessionStatePersistence()

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

    def save_state(self) -> bool:
        """Save all current sessions to disk.

        Returns:
            True if save was successful, False otherwise
        """
        return self._persistence.save_sessions(self.sessions)

    def restore_state(self, emit_events: bool = True) -> int:
        """Restore sessions from saved state.

        Args:
            emit_events: Whether to emit session_created events for restored sessions

        Returns:
            Number of sessions successfully restored
        """
        saved_sessions = self._persistence.load_sessions()
        restored_count = 0

        for session_data in saved_sessions:
            try:
                template_id = session_data.get("template_id")
                if not template_id or template_id not in self.templates:
                    LOG.warning("Skipping session with invalid template_id: %s", template_id)
                    continue

                # Create overrides from saved data
                overrides_data = session_data.get("overrides", {})
                overrides = SessionOverrides(
                    custom_name=overrides_data.get("custom_name"),
                    cwd=overrides_data.get("cwd"),
                    env=overrides_data.get("env", {}),
                )

                # Create the session
                session = self.create_session(template_id, overrides)

                # Restore additional properties
                if session_data.get("description"):
                    session.description = session_data["description"]
                if session_data.get("current_shell"):
                    session.current_shell = session_data["current_shell"]
                if session_data.get("display_name"):
                    session.display_name = session_data["display_name"]

                # Update the session to apply changes
                self.update_session(session)

                restored_count += 1
                LOG.info("Restored session: %s (template: %s)",
                        session.display_name, template_id)

            except Exception as exc:
                LOG.error("Failed to restore session: %s", exc)
                continue

        LOG.info("Restored %d sessions from saved state", restored_count)
        return restored_count

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
