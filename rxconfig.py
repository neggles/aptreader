import reflex as rx

from aptreader.constants import DB_URL

config = rx.Config(
    app_name="aptreader",
    db_url=DB_URL,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    cors_allowed_origins=["*"],
    show_built_with_reflex=False,
)
