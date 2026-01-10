import logging

import reflex as rx
from reflex.plugins.shared_tailwind import TailwindConfig

from aptreader.constants import ASYNC_DB_URL, DB_URL

# number of parallel threads to use for fetching package data
FETCH_PARALLEL = 8

logger = logging.getLogger(__name__)

tailwind_config = TailwindConfig(
    plugins=["@tailwindcss/typography"],
)

config = rx.Config(
    app_name="aptreader",
    db_url=DB_URL,
    async_db_url=ASYNC_DB_URL,
    backend_port=3001,
    plugins=[
        rx.plugins.TailwindV4Plugin(tailwind_config),
        rx.plugins.SitemapPlugin(),
    ],
    cors_allowed_origins=["*"],
)
