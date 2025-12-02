import reflex as rx

config = rx.Config(
    app_name="aptreader",
    app_module_import="aptreader",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
)
