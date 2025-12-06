import logging

from aptreader.constants import ASYNC_DB_URL, DB_URL

logger = logging.getLogger(__name__)

try:
    import reflex as rx
    import reflex_enterprise as rxe
except ImportError:
    logger.warning("Reflex Enterprise not found; using open-source Reflex, some things may not work.")
    import reflex as rx
    import reflex as rxe


config = rxe.Config(
    app_name="aptreader",
    db_url=DB_URL,
    async_db_url=ASYNC_DB_URL,
    plugins=[
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.SitemapPlugin(),
    ],
    cors_allowed_origins=["*"],
)
