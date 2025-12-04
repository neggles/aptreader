"""Distributions page for viewing repository distributions."""

import logging

import reflex as rx

from aptreader.backend.backend import AppState
from aptreader.templates import template
from aptreader.views.distributions import distributions_table

logger = logging.getLogger(__name__)


@template(route="/distributions/[[...splat]]", title="Distributions", on_load=AppState.load_repositories)
def distributions() -> rx.Component:
    """Distributions page component."""

    return rx.vstack(
        rx.heading("distributions", size="9", margin_bottom="2rem"),
        rx.box(
            distributions_table(),
            width="100%",
        ),
        size="4",
        width="100%",
        padding="0",
    )
