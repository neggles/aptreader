"""Settings component for configuring aptreader options."""

from pathlib import Path

import reflex as rx

DEFAULT_CACHE_DIR = Path.cwd() / ".cache" / "aptreader"  # Default cache directory


class SettingsState(rx.State):
    """State for application settings."""

    cache_dir: Path = DEFAULT_CACHE_DIR
    message: str | None = None

    @rx.event
    def on_load(self):
        pass

    @rx.var
    def cache_dir_str(self) -> str:
        """Get the current cache directory as a string."""
        return str(self.cache_dir) if self.cache_dir else ""

    @rx.event
    def set_cache_dir(self, value: str):
        """Update the cache directory path."""
        self.cache_dir = Path(value) if value else None
        self.message = ""

    @rx.event
    def save_settings(self):
        """Save settings and provide feedback."""
        self.message = "Settings saved."
