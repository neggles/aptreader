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
    component_filter: list[str] = []
    architecture_filter: list[str] = []
    available_components: list[str] = []
    available_architectures: list[str] = []

    @rx.event
    async def on_load(self):
        settings = await self.get_state(SettingsState)
        if settings.cache_dir:
            settings.cache_dir.mkdir(parents=True, exist_ok=True)

    def set_repo_url(self, url: str):
        """Update the repository URL."""
        self.repo_url = url
        self.error_message = ""

    @rx.event(background=True)
    async def load_repository(self):
        async with self:
            settings = await self.get_state(SettingsState)
            cache_dir = settings.cache_dir

            """Load and parse the APT repository."""
            if not self.repo_url:
                self.error_message = "Please enter a repository URL"
                return

            self.status_message = f"Loading repository: {self.repo_url}..."
            self.error_message = ""
            self.repo_loaded = False

        try:
            manager = RepositoryManager(cache_dir=Path(cache_dir))
            async with self:
                component_filter = self.component_filter or None
                architecture_filter = self.architecture_filter or None
                self.repository = await manager.load_repository(
                    self.repo_url,
                    components=component_filter,
                    architectures=architecture_filter,
                )
                self.repo_loaded = True
                release_count = len(self.repository.releases)
                plural = "release" if release_count == 1 else "releases"
                self.status_message = f"Repository loaded successfully ({release_count} {plural})!"

                # Set default selections
                if self.repository.releases:
                    self.selected_release = list(self.repository.releases.keys())[0]
                    release = self.repository.releases[self.selected_release]
                    if release.components:
                        self.selected_component = list(release.components.keys())[0]

                component_candidates: list[str] = []
                architecture_candidates: list[str] = []
                for release in self.repository.releases.values():
                    if release.available_components:
                        component_candidates.extend(release.available_components)
                    elif release.components:
                        component_candidates.extend(release.components.keys())
                    architecture_candidates.extend(
                        [arch for arch in release.architectures if arch not in {"all", "source"}]
                    )

                if component_candidates:
                    self.available_components = list(dict.fromkeys(component_candidates))
                if architecture_candidates:
                    self.available_architectures = list(dict.fromkeys(architecture_candidates))

        except Exception as e:
            self.error_message = f"Error loading repository: {str(e)}"
            self.status_message = ""
            self.repo_loaded = False
            raise e

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
