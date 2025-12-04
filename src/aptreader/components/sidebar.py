"""Sidebar component for the app."""

import reflex as rx

from aptreader import styles
from aptreader.backend.backend import AppState

from .logo import logo


def sidebar_header() -> rx.Component:
    """Sidebar header.

    Returns:
        The sidebar header component.

    """
    return rx.hstack(
        logo(),
        rx.spacer(),
        align="center",
        width="100%",
        padding="0.35em",
        margin_bottom="1em",
    )


def sidebar_footer() -> rx.Component:
    """Sidebar footer.

    Returns:
        The sidebar footer component.

    """
    return rx.hstack(
        rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
        rx.spacer(),
        justify="start",
        align="center",
        width="100%",
        padding="0.35em",
    )


def sidebar_item_icon(icon: str) -> rx.Component:
    return rx.icon(icon, size=18)


def sidebar_item(text: str, url: str) -> rx.Component:
    """Sidebar item.

    Args:
        text: The text of the item.
        url: The URL of the item.

    Returns:
        rx.Component: The sidebar item component.

    """
    # Whether the item is active.
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & text == "Repositories"
    )

    link_url = url.split("/[[...splat]]")[0] if "/[[...splat]]" in url else url

    return rx.link(
        rx.hstack(
            rx.match(
                text,
                ("Repositories", sidebar_item_icon("square-library")),
                ("Distributions", sidebar_item_icon("library")),
                ("Packages", sidebar_item_icon("package")),
                ("Settings", sidebar_item_icon("settings")),
                sidebar_item_icon("layout-dashboard"),
            ),
            rx.text(text, size="3", weight="regular"),
            color=rx.cond(
                active,
                styles.accent_text_color,
                styles.text_color,
            ),
            style={
                "_hover": {
                    "background_color": rx.cond(
                        active,
                        styles.accent_bg_color,
                        styles.gray_bg_color,
                    ),
                    "color": rx.cond(
                        active,
                        styles.accent_text_color,
                        styles.text_color,
                    ),
                    "opacity": "1",
                },
                "opacity": rx.cond(
                    active,
                    "1",
                    "0.95",
                ),
            },
            align="center",
            border_radius=styles.border_radius,
            width="100%",
            spacing="2",
            padding="0.35em",
        ),
        underline="none",
        href=link_url,
        width="100%",
    )


def sidebar() -> rx.Component:
    """The sidebar.

    Returns:
        The sidebar component.
    """
    from reflex.config import get_config
    from reflex.page import DECORATED_PAGES

    from aptreader.constants import ORDERED_PAGE_ROUTES

    pages = [page_dict for (_, page_dict) in DECORATED_PAGES[get_config().app_name]]

    ordered_pages = sorted(
        pages,
        key=lambda page: (
            ORDERED_PAGE_ROUTES.index(page["route"])
            if page["route"] in ORDERED_PAGE_ROUTES
            else len(ORDERED_PAGE_ROUTES)
        ),
    )

    return rx.flex(
        rx.vstack(
            sidebar_header(),
            rx.vstack(
                *[
                    sidebar_item(
                        text=page.get("title", page["route"].strip("/").capitalize()),
                        url=page["route"],
                    )
                    for page in ordered_pages
                ],
                spacing="1",
                width="100%",
            ),
            rx.spacer(),
            sidebar_footer(),
            justify="end",
            align="end",
            width=styles.sidebar_content_width,
            height="100dvh",
            padding="1em",
        ),
        display=["none", "none", "none", "none", "none", "flex"],
        max_width=styles.sidebar_width,
        width="auto",
        height="100%",
        position="sticky",
        justify="end",
        top="0px",
        left="0px",
        flex="1",
        bg=rx.color("gray", 2),
    )
