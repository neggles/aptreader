"""Application state for aptreader."""

from pathlib import Path

import reflex as rx

from ....temp.oldfiles.states.settings import SettingsState


class AppState(rx.State):
    """Application state for repository browsing."""
