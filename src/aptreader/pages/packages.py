"""Packages browsing page."""

import reflex as rx

from aptreader.backend.backend import AppState
from aptreader.states import PackagesState
from aptreader.states.repo_select import RepoSelectState
from aptreader.templates import template
from aptreader.views.packages import packages_table


@template(
    route="/packages/[[...splat]]",
    title="Packages",
    on_load=[AppState.load_repositories, RepoSelectState.load_from_state, PackagesState.load_packages],
)
def packages() -> rx.Component:
    return rx.vstack(
        rx.heading("packages", size="9", margin_bottom="2rem"),
        rx.box(
            packages_table(),
            width="100%",
        ),
        size="4",
        width="100%",
        padding="0",
    )
