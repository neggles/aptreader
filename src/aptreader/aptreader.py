"""aptreader: APT repository browser and metadata scraper."""

import logging

import reflex as rx

from aptreader.pages import *  # noqa: F403

logger = logging.getLogger(__name__)


# Create the Reflex app
app = rx.App(
    theme=rx.theme(
        color_mode="dark",
        has_background=True,
        appearance="dark",
        accent_color="violet",
        panel_background="translucent",
        radius="large",
    ),
    stylesheets=[
        "/styles.css",
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap",
    ],
)
