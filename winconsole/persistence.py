"""Session persistence and state management for WinConsole."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .models import Session, SessionOverrides, SessionState

LOG = logging.getLogger("winconsole")

# Constants
DEFAULT_STATE_FILENAME = "session_state.json"
STATE_FILE_VERSION = "1.0"


class SessionStatePersistence:
    """Handles saving and loading session state to/from disk."""

    def __init__(self, state_dir: Optional[Path] = None):
        """Initialize persistence manager.

        Args:
            state_dir: Directory to store state files. Defaults to ~/.winconsole/
        """
        if state_dir is None:
            state_dir = Path.home() / ".winconsole"

        self.state_dir = state_dir
        self.state_file = self.state_dir / DEFAULT_STATE_FILENAME

        # Ensure directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_sessions(self, sessions: Dict[str, Session]) -> bool:
        """Save all sessions to state file.

        Args:
            sessions: Dictionary of session ID to Session objects

        Returns:
            True if save was successful, False otherwise
        """
        try:
            state_data = {
                "version": STATE_FILE_VERSION,
                "sessions": []
            }

            for session in sessions.values():
                # Only save sessions that are still running or recently exited
                session_data = {
                    "id": session.id,
                    "template_id": session.template_id,
                    "display_name": session.display_name,
                    "description": session.description,
                    "current_shell": session.current_shell,
                    "overrides": {
                        "custom_name": session.display_name if session.display_name else None,
                        "cwd": session.cwd if session.cwd else None,
                        "env": session.env if session.env else {},
                    },
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                }
                state_data["sessions"].append(session_data)

            # Write to temporary file first, then rename for atomic write
            temp_file = self.state_file.with_suffix(".tmp")
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.state_file)

            LOG.info("Saved %d sessions to %s", len(sessions), self.state_file)
            return True

        except Exception as exc:
            LOG.error("Failed to save session state: %s", exc)
            return False

    def load_sessions(self) -> List[Dict]:
        """Load saved sessions from state file.

        Returns:
            List of session data dictionaries, or empty list if load fails
        """
        if not self.state_file.exists():
            LOG.info("No saved state file found at %s", self.state_file)
            return []

        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                state_data = json.load(f)

            # Validate version
            version = state_data.get("version", "unknown")
            if version != STATE_FILE_VERSION:
                LOG.warning("State file version mismatch: expected %s, got %s",
                           STATE_FILE_VERSION, version)

            sessions = state_data.get("sessions", [])
            LOG.info("Loaded %d sessions from %s", len(sessions), self.state_file)
            return sessions

        except json.JSONDecodeError as exc:
            LOG.error("Failed to parse state file: %s", exc)
            return []
        except Exception as exc:
            LOG.error("Failed to load session state: %s", exc)
            return []

    def clear_state(self) -> bool:
        """Clear all saved session state.

        Returns:
            True if clear was successful, False otherwise
        """
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                LOG.info("Cleared session state file")
            return True
        except Exception as exc:
            LOG.error("Failed to clear state file: %s", exc)
            return False
