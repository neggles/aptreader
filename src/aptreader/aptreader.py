"""aptreader: APT repository browser and metadata scraper."""

import logging

import reflex as rx
import socketio
from rich.logging import RichHandler

from aptreader.pages import *  # noqa: F403

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            tracebacks_suppress=[socketio],
        )
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# Create the Reflex app
app = rx.App(
    theme=rx.theme(appearance="dark", has_background=True, radius="full", accent_color="violet"),
)
