from os import getenv

import reflex as rx

db_url = getenv("APTREADER_DB_URL", "sqlite:///aptreader.db")

config = rx.Config(
    app_name="aptreader",
    db_url=db_url,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    cors_allowed_origins=["*"],
)
