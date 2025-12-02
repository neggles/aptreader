"""aptreader: APT repository browser and metadata scraper."""

import asyncio
from pathlib import Path

import reflex as rx
import typer

from .models import Repository
from .repository import RepositoryManager

cli = typer.Typer()


class AppState(rx.State):
    """Application state for repository browsing."""

    repo_url: str = ""
    repo_loaded: bool = False
    status_message: str = ""
    error_message: str = ""
    repository: Repository | None = None
    selected_release: str = ""
    selected_component: str = ""

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

        try:
            manager = RepositoryManager()
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


def index() -> rx.Component:
    """Main page component."""
    return rx.container(
        rx.heading("aptreader", size="9", margin_bottom="1em"),
        rx.text(
            "Browse APT repository metadata, packages, and files",
            color="gray",
            margin_bottom="2em",
        ),
        # Repository URL input section
        rx.vstack(
            rx.heading("Repository URL", size="5", margin_bottom="0.5em"),
            rx.input(
                placeholder="http://archive.ubuntu.com/ubuntu",
                value=AppState.repo_url,
                on_change=AppState.set_repo_url,
                width="100%",
            ),
            rx.button(
                "Load Repository",
                on_click=AppState.load_repository,
                margin_top="1em",
            ),
            rx.cond(
                AppState.status_message != "",
                rx.text(
                    AppState.status_message,
                    margin_top="1em",
                    color="green",
                ),
            ),
            rx.cond(
                AppState.error_message != "",
                rx.text(
                    AppState.error_message,
                    margin_top="1em",
                    color="red",
                ),
            ),
            spacing="2",
            width="100%",
            margin_bottom="2em",
        ),
        # Repository browser section
        rx.cond(
            AppState.repo_loaded,
            rx.vstack(
                rx.divider(),
                rx.heading("Repository Contents", size="6", margin_top="1em", margin_bottom="1em"),
                # Release and component summary
                rx.cond(
                    AppState.repository != None,
                    rx.vstack(
                        rx.foreach(
                            AppState.repository.releases,
                            lambda release_name, _: rx.box(
                                rx.heading(f"Release: {release_name}", size="4"),
                                rx.text(
                                    f"Components: {', '.join(AppState.repository.releases[release_name].components.keys())}",
                                    color="gray",
                                ),
                                rx.text(
                                    f"Total packages: {sum(len(comp.packages) for comp in AppState.repository.releases[release_name].components.values())}",
                                    color="gray",
                                ),
                                padding="1em",
                                border="1px solid #e0e0e0",
                                border_radius="8px",
                                margin_bottom="1em",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                width="100%",
            ),
        ),
        max_width="1200px",
        padding="2em",
    )


# Create the Reflex app
app = rx.App()
app.add_page(index, route="/")


@cli.command()
def run(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(3000, help="Port to bind to"),
):
    """Start the aptreader web server."""
    typer.echo(f"Starting aptreader on {host}:{port}")
    # Note: Reflex needs to be run via its CLI, so we'll shell out to it
    import subprocess
    subprocess.run(["reflex", "run", "--loglevel", "info"])


def main() -> None:
    """Main entry point for the aptreader CLI."""
    cli()


if __name__ == "__main__":
    app()

