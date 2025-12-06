import logging

import reflex as rx
from reflex.constants.colors import COLORS

from aptreader.backend.backend import AppState
from aptreader.components.repo_select import repo_select
from aptreader.models import Distribution

logger = logging.getLogger(__name__)

color_names = list(COLORS)


def component_to_color(component: str):
    return rx.match(
        component,
        ("main", "grass"),
        ("contrib", "orange"),
        ("non-free", "tomato"),
        ("non-free-firmware", "tomato"),
        ("restricted", "red"),
        ("universe", "iris"),
        ("multiverse", "cyan"),
        "gray",
    )


# fmt: off
def architecture_to_color(architecture: str):
    return rx.match(
        architecture,
        ("i386", "blue"), ("amd64", "indigo"), ("amd64v3", "iris"),
        ("armel", "red"), ("armhf", "red"), ("arm64", "ruby"), ("aarch64", "ruby"),
        ("riscv32", "bronze"), ("riscv64", "brown"),
        ("powerpc", "teal"), ("ppc32", "teal"), ("ppc64el", "jade"), ("ppc64", "jade"),
        ("s390", "yellow"), ("s390x", "amber"),
        "var(--accent-color)",
    )
# fmt: on


def show_distribution(dist: Distribution):
    """Display a single distribution in a table row."""
    return rx.table.row(
        rx.table.row_header_cell(rx.text(dist.codename, size="2")),
        rx.table.cell(rx.text(dist.suite, size="2")),
        rx.table.cell(rx.text(dist.origin)),
        rx.table.cell(rx.text(dist.version)),
        rx.table.cell(
            rx.cond(
                dist.components,
                rx.flex(
                    rx.foreach(
                        dist.format_components,
                        lambda comp: rx.badge(comp, color_scheme=component_to_color(comp)),
                    ),
                    spacing="2",
                    wrap="wrap",
                ),
                "-",
            ),
        ),
        rx.table.cell(
            rx.cond(
                dist.architectures,
                rx.flex(
                    rx.foreach(
                        dist.format_architectures,
                        lambda arch: rx.badge(arch, color_scheme=architecture_to_color(arch)),
                    ),
                    spacing="2",
                    wrap="wrap",
                ),
                "-",
            ),
        ),
        rx.table.cell(
            rx.text(
                rx.cond(dist.format_date, dist.format_date, "-"),
                wrap="nowrap",
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.icon_button(
                    rx.icon("package-plus", size=18),
                    size="2",
                    variant="soft",
                    color_scheme="indigo",
                    loading=rx.cond(AppState.package_fetch_distribution_id == dist.id, True, False),
                    disabled=AppState.is_fetching_packages,
                    on_click=rx.cond(
                        dist.id is not None, AppState.fetch_distribution_packages(dist.id), rx.noop()
                    ),
                ),
                rx.link(
                    rx.icon_button(
                        rx.icon("package-search", size=18),
                        size="2",
                        variant="surface",
                        color_scheme="blue",
                    ),
                    href=f"/packages/{dist.id}" if dist.id is not None else "/packages",
                ),
                spacing="2",
            ),
            align="center",
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


@rx.event
def load_distributions(state: AppState):
    """Load distributions for a specific repository."""
    if "distributions/" not in state.router.url.path:
        return rx.noop()
    route_splat = state.router.url.query_parameters.get("splat", [])
    if not route_splat:
        return rx.noop()

    repo_id = route_splat[0]
    if repo_id is None:
        logger.warning("No repository ID in state")
        return rx.noop()
    if isinstance(repo_id, str) and not repo_id.isdigit():
        logger.error(f"Invalid repository ID: {repo_id}")
        return rx.noop()

    repo_id = int(repo_id)
    if state.current_repo is None or state.current_repo.id != repo_id:
        logger.info(f"Updating current repository ID to {repo_id}")
        state.set_current_repo_id(repo_id)

    if state.current_repo is None:
        return rx.toast.warning(f"Repository ID {repo_id} not found.")
    return rx.toast.info(f"Loaded distributions for {state.current_repo.name}.")


def _header_cell(text: str, icon: str, **kwargs) -> rx.Component:
    """Create a table header cell with icon."""
    return rx.table.column_header_cell(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text),
            align="center",
            spacing="2",
        ),
        **kwargs,
    )


def distributions_table() -> rx.Component:
    """Display table of distributions."""

    return rx.fragment(
        rx.cond(
            AppState.current_repo is not None,
            rx.vstack(
                repo_select(),
                rx.cond(
                    AppState.is_fetching_packages,
                    rx.callout(
                        rx.hstack(
                            rx.spinner(size="2"),
                            rx.vstack(
                                rx.text(
                                    rx.cond(
                                        AppState.package_fetch_message,
                                        AppState.package_fetch_message,
                                        "Fetching packages...",
                                    )
                                ),
                                rx.text(
                                    rx.cond(
                                        AppState.package_fetch_distribution_id != -1,
                                        f"Distribution ID {AppState.package_fetch_distribution_id}",
                                        "",
                                    ),
                                    size="2",
                                    color=rx.color("gray", 10),
                                ),
                                spacing="1",
                                align="start",
                            ),
                            rx.progress(
                                value=AppState.package_fetch_progress,
                                size="1",
                                width="160px",
                            ),
                            spacing="3",
                            align="center",
                        ),
                        color_scheme="indigo",
                        size="2",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    AppState.distributions,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _header_cell("Codename", "tag"),
                                _header_cell("Suite", "folder"),
                                _header_cell("Origin", "globe"),
                                _header_cell("Version", "hash"),
                                _header_cell("Components", "package"),
                                _header_cell("Architectures", "cpu"),
                                _header_cell("Released", "calendar"),
                                _header_cell("Packages", "package-search"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(AppState.distributions, show_distribution),
                        ),
                        size="3",
                        width="100%",
                        class_name="table-fixed",
                        variant="surface",
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
        on_mount=load_distributions(),
    )
