"""Application state for aptreader."""

from pathlib import Path

import reflex as rx

from aptreader.models import Repository
from aptreader.repository import RepositoryManager

from .settings import SettingsState


class AppState(rx.State):
    """Application state for repository browsing."""

    repo_url: str = ""
    repo_loaded: bool = False
    status_message: str = ""
    error_message: str = ""
    repository: Repository | None = None
    selected_release: str = ""
    selected_component: str = ""

    @rx.event
    async def on_load(self):
        settings = await self.get_state(SettingsState)

    def set_repo_url(self, url: str):
        """Update the repository URL."""
        self.repo_url = url
        self.error_message = ""

    async def load_repository(self):
        """Load and parse the APT repository."""
        if not self.repo_url:
            self.error_message = "Please enter a repository URL"
            return

        self.status_message = f"Loading repository: {self.repo_url}..."
        self.error_message = ""
        self.repo_loaded = False

        cache_dir = SettingsState.cache_dir
        if not cache_dir:
            # Default to <repo_root>/.cache/aptreader
            import os

            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(repo_root, ".cache", "aptreader")
            SettingsState.cache_dir = cache_dir

        try:
            manager = RepositoryManager(cache_dir=Path(cache_dir))
            # For now, try loading jammy (Ubuntu 22.04) as an example
            # In the future, we'll detect available distributions
            self.repository = await manager.load_repository(
                self.repo_url, dist="dists/jammy", components=["main", "universe"]
            )
            self.repo_loaded = True
            self.status_message = "Repository loaded successfully!"

            # Set default selections
            if self.repository.releases:
                self.selected_release = list(self.repository.releases.keys())[0]
                release = self.repository.releases[self.selected_release]
                if release.components:
                    self.selected_component = list(release.components.keys())[0]

        except Exception as e:
            self.error_message = f"Error loading repository: {str(e)}"
            self.status_message = ""
            self.repo_loaded = False

    def select_release(self, release: str):
        """Select a release to display."""
        self.selected_release = release
        if self.repository and release in self.repository.releases:
            components = self.repository.releases[release].components
            if components:
                self.selected_component = list(components.keys())[0]

    def select_component(self, component: str):
        """Select a component to display."""
        self.selected_component = component
