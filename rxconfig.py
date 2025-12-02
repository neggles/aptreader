import reflex as rx

config = rx.Config(
    app_name="aptreader",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
    cors_allowed_origins=["*"],
    env=rx.Env.DEV,
)
