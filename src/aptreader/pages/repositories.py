"""Main index page for aptreader."""

import reflex as rx

from aptreader.backend.backend import AppState
from aptreader.templates import template
from aptreader.views.repositories import repositories_table


class RepositoriesState(rx.State):
    """State for the repositories page."""

    pass


@template(route="/", title="Repositories")
def repositories() -> rx.Component:
    """Main page component."""
    return rx.vstack(
        rx.heading("repositories", size="9", margin_bottom="2rem"),
        rx.box(
            repositories_table(),
            width="100%",
        ),
        size="4",
        width="100%",
        padding="0",
    )
