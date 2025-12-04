"""aptreader: APT repository browser and metadata scraper."""

import logging

import reflex as rx
from rich.logging import RichHandler

from aptreader.pages import *  # noqa: F403

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Create the Reflex app
app = rx.App(
    theme=rx.theme(appearance="dark", has_background=True, radius="full", accent_color="violet"),
)
