"""Distributions page for viewing repository distributions."""

import logging

import reflex as rx

from aptreader.backend.backend import Distribution, Repository, State
from aptreader.templates import template

logger = logging.getLogger(__name__)


def show_distribution(dist: Distribution):
    """Display a single distribution in a table row."""
    return rx.table.row(
        rx.table.cell(dist.codename),
        rx.table.cell(dist.suite),
        rx.table.cell(dist.origin),
        rx.table.cell(dist.version),
        rx.table.cell(
            rx.cond(
                dist.architectures,
                rx.hstack(
                    rx.foreach(dist.architectures, lambda arch: rx.text(arch)),
                ),
                "-",
            )
        ),
        rx.table.cell(
            rx.cond(
                dist.components,
                rx.hstack(rx.foreach(dist.components, lambda comp: rx.text(comp))),
                "-",
            )
        ),
        rx.table.cell(dist.date),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def _header_cell(text: str, icon: str) -> rx.Component:
    """Create a table header cell with icon."""
    return rx.table.column_header_cell(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text),
            align="center",
            spacing="2",
        ),
    )


@rx.event
def load_distributions(state: State, repo_id: int | str):
    """Load distributions for a specific repository."""
    if isinstance(repo_id, str) and repo_id.isdigit():
        repo_id = int(repo_id)
    else:
        return

    State.set_current_repo(repo_id)

    with rx.session() as session:
        repo = session.get(Repository, repo_id)
        if not repo:
            state.distributions = []
            return
        # Load distributions for this repository
        from sqlmodel import select as sm_select

        distributions = session.exec(
            sm_select(Distribution).where(Distribution.repository_id == repo_id)
        ).all()
        state.distributions = list(distributions)


def distributions_table() -> rx.Component:
    """Display table of distributions."""
    return rx.fragment(
        rx.cond(
            State.current_repo is not None,
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        rx.cond(
                            State.current_repo,
                            State.current_repo.name,  # type: ignore
                            "Repository",
                        ),
                        size="7",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("arrow-left"),
                        rx.text("Back to Repositories", size="3"),
                        size="3",
                        on_click=rx.redirect("/"),
                    ),
                    width="100%",
                    align="center",
                    margin_bottom="1em",
                ),
                rx.text(
                    rx.cond(
                        State.current_repo,
                        State.current_repo.url,  # type: ignore
                        "",
                    ),
                    size="3",
                    color=rx.color("gray", 11),
                    margin_bottom="1em",
                ),
                rx.cond(
                    State.distributions,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _header_cell("Codename", "tag"),
                                _header_cell("Suite", "folder"),
                                _header_cell("Origin", "globe"),
                                _header_cell("Version", "hash"),
                                _header_cell("Architectures", "cpu"),
                                _header_cell("Components", "package"),
                                _header_cell("Date", "calendar"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(State.distributions, show_distribution),
                        ),
                        variant="surface",
                        size="3",
                        width="100%",
                    ),
                    rx.callout(
                        rx.text(
                            "No distributions found. Click the download button on the repositories page to fetch them."
                        ),
                        color_scheme="gray",
                        size="2",
                    ),
                ),
                width="100%",
            ),
            rx.callout(
                rx.text("Select a repository to view distributions"),
                color_scheme="gray",
                size="2",
            ),
        ),
    )


@template(route="/distributions/[repo_id]", title="Distributions")
def distributions() -> rx.Component:
    """Distributions page."""
    # Get repo_id from router
    repo_id = rx.State.repo_id  # type: ignore

    State.set_current_repo(repo_id)

    return rx.vstack(
        distributions_table(),
        size="4",
        width="100%",
        padding="0",
        on_mount=load_distributions(repo_id),
    )
