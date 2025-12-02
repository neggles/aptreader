"""aptreader: APT repository browser and metadata scraper."""

import reflex as rx
import typer

cli = typer.Typer()


class AppState(rx.State):
    """Application state for repository browsing."""

    repo_url: str = ""
    repo_loaded: bool = False
    status_message: str = ""

    def set_repo_url(self, url: str):
        """Update the repository URL."""
        self.repo_url = url

    def load_repository(self):
        """Load and parse the APT repository."""
        if not self.repo_url:
            self.status_message = "Please enter a repository URL"
            return

        self.status_message = f"Loading repository: {self.repo_url}..."
        # TODO: Implement repository downloading and parsing
        self.repo_loaded = True
        self.status_message = f"Repository loaded successfully"


def index() -> rx.Component:
    """Main page component."""
    return rx.container(
        rx.heading("aptreader", size="9", margin_bottom="1em"),
        rx.text(
            "Browse APT repository metadata, packages, and files",
            color="gray",
            margin_bottom="2em",
        ),
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
                    color=rx.cond(
                        AppState.repo_loaded,
                        "green",
                        "gray",
                    ),
                ),
            ),
            spacing="2",
            width="100%",
        ),
        max_width="800px",
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

