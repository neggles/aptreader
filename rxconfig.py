import logging

import reflex as rx

from aptreader.constants import ASYNC_DB_URL, DB_URL

logger = logging.getLogger(__name__)


config = rx.Config(
    app_name="aptreader",
    db_url=DB_URL,
    async_db_url=ASYNC_DB_URL,
    plugins=[
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.SitemapPlugin(),
    ],
    cors_allowed_origins=["*"],
)
