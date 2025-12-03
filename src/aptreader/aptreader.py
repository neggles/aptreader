"""aptreader: APT repository browser and metadata scraper."""

import logging

import reflex as rx

from aptreader.pages import *  # noqa: F403

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the Reflex app
app = rx.App(
    theme=rx.theme(appearance="dark", has_background=True, radius="full", accent_color="violet"),
)
