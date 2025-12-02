"""aptreader: APT repository browser and metadata scraper."""

import subprocess

import reflex as rx
import typer

from .pages.index import index

cli = typer.Typer()


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
    subprocess.run(["reflex", "run", "--loglevel", "info"])


def main() -> None:
    """Main entry point for the aptreader CLI."""
    cli()


if __name__ == "__main__":
    app()
