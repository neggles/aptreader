import logging

import reflex as rx

from aptreader.states import DistributionsState, DistroSelectState, RepoSelectState

logger = logging.getLogger(__name__)


def repo_select(button: rx.Component | None = None) -> rx.Component:
    # Create the select component

    return rx.card(
        rx.hstack(
            rx.text("Repository"),
            rx.select(
                RepoSelectState.available_repo_names,
                value=RepoSelectState.current_repo_name,
                on_change=RepoSelectState.select_repo_name,
                min_width="240px",
                width="240px",
            ),
            rx.cond(button, button, None),
            spacing="3",
            align="center",
        ),
        justify="end",
        display="flex",
        padding="0.75rem 1rem",
    )


def distro_select() -> rx.Component:
    # Create the select component
    return rx.card(
        rx.hstack(
            rx.text("Distribution"),
            rx.select(
                DistributionsState.distribution_names,
                value=DistroSelectState.current_distro_name,
                on_change=DistroSelectState.select_distro_name,
                min_width="240px",
                width="240px",
            ),
            spacing="3",
            align="center",
        ),
        justify="end",
        display="flex",
        padding="0.75rem 1rem",
    )
