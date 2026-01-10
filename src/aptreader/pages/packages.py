"""Packages browsing page."""

import reflex as rx

from aptreader.states import PackagesState
from aptreader.templates import template
from aptreader.views.packages import packages_filters, packages_table


@template(
    route="/packages/[[...splat]]",
    title="Packages",
    on_load=[PackagesState.load_from_route],
)
def packages() -> rx.Component:
    return rx.vstack(
        rx.heading("packages", size="9", margin_bottom="2rem"),
        packages_filters(),
        packages_table(),
        width="100%",
        spacing="4",
    )
