"""aptreader: APT repository browser and metadata scraper."""

import logging

import socketio
from rich.logging import RichHandler

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

try:
    import reflex as rx
    import reflex_enterprise as rxe
except ImportError:
    logger.warning("Reflex Enterprise not found; using open-source Reflex, some things may not work.")
    import reflex as rx
    import reflex as rxe

# this should not be imported until after reflex is imported
from aptreader.pages import *  # noqa: F403, E402

# Create the Reflex app
app = rxe.App(
    theme=rx.theme(appearance="dark", has_background=True, radius="full", accent_color="violet"),
)
