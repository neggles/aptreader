import logging

import reflex as rx
from reflex.constants.colors import COLORS

from aptreader.backend.backend import AppState
from aptreader.components.selectors import repo_select
from aptreader.models import Distribution
from aptreader.states.distributions import DistributionsState

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
        ("armel", "amber"), ("armhf", "amber"), ("arm64", "amber"), ("aarch64", "amber"),
        ("riscv32", "bronze"), ("riscv64", "brown"),
        ("powerpc", "teal"), ("ppc32", "teal"), ("ppc64el", "jade"), ("ppc64", "jade"),
        ("s390", "yellow"), ("s390x", "yellow"),
        ("mips64el", "green"), ("mipsel", "green"),
        ("loong64", "ruby"), ("loongarch64", "ruby"),
        ("sw64", "plum"),
        "var(--accent-color)",
    )
# fmt: on


def show_distribution(dist: Distribution):
    """Display a single distribution in a table row."""

    return rx.table.row(
        rx.table.row_header_cell(rx.text(dist.codename, size="2")),
        rx.table.cell(rx.text(dist.suite, size="2")),
        rx.table.cell(rx.text(dist.origin, size="2")),
        rx.table.cell(rx.text(dist.version, size="2")),
        rx.table.cell(
            rx.cond(
                dist.components,
                rx.flex(
                    rx.foreach(
                        dist.format_components,
                        lambda comp: rx.badge(comp, color_scheme=component_to_color(comp)),
                    ),
                    spacing="1",
                    wrap="wrap",
                ),
                rx.text("-"),
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
                    spacing="1",
                    wrap="wrap",
                ),
                rx.text("-"),
            ),
        ),
        rx.table.cell(rx.text(f"{dist.package_count}", size="2")),
        rx.table.cell(
            rx.text(
                rx.cond(dist.format_date, dist.format_date, "-"),
                class_name="no-wrap-whitespace",
                font_family="var(--font-mono)",
                size="2",
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(dist.last_fetched_at, dist.format_last_fetched_at, "-"),
                class_name="no-wrap-whitespace",
                font_family="var(--font-mono)",
                size="2",
            ),
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
                rx.icon_button(
                    rx.icon("bug", size=18),
                    size="2",
                    variant="soft",
                    color_scheme="red",
                    on_click=rx.console_log(
                        f"Distribution details: arches={dist.architectures}, components={dist.components}"
                    ),
                ),
                spacing="2",
            ),
            align="center",
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def _header_cell(
    text: str,
    icon: str,
    nowrap: bool = False,
    w: str | int | None = None,
    min_w: str | int | None = None,
    font: str | None = None,
    **kwargs,
) -> rx.Component:
    """Create a table header cell with icon."""
    return rx.table.column_header_cell(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text, font_family=font),
            align="center",
            spacing="2",
        ),
        class_name=(
            rx.cond(nowrap, "no-wrap-whitespace", None),
            rx.cond(w is not None, f"w-{w}", None),
            rx.cond(min_w is not None, f"min-w-{min_w}", None),
        ),
        **kwargs,
    )


def package_fetch_status() -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.match(
                AppState.package_fetch_progress,
                (range(100), rx.spinner(size="2")),
                (100, rx.icon("list-check", size=18, color=rx.color("green", 6))),
                rx.icon("list", size=18),
            ),
            rx.cond(
                AppState.package_fetch_progress < 100,
                rx.progress(
                    value=AppState.package_fetch_progress,
                    size="1",
                    width="100px",
                ),
                rx.fragment(),
            ),
            rx.cond(
                AppState.package_fetch_message,
                rx.text(AppState.package_fetch_message),
                rx.text("Idle"),
            ),
            spacing="3",
            align="center",
        ),
        color_scheme=rx.cond(
            AppState.is_fetching_packages == True,  # noqa: E712
            "blue",
            "grass",
        ),
        justify="end",
        display="flex",
        padding="0.75rem 1rem",
    )


def distributions_table() -> rx.Component:
    """Display table of distributions."""

    return rx.vstack(
        rx.flex(
            repo_select(),
            package_fetch_status(),
            rx.spacer(),
            rx.card(
                rx.hstack(
                    rx.select(
                        DistributionsState.component_filter_options,
                        value=DistributionsState.component_filter,
                        placeholder="Component",
                        on_change=DistributionsState.set_component_filter,
                        width="200px",
                        min_width="200px",
                    ),
                    rx.select(
                        DistributionsState.architecture_filter_options,
                        value=DistributionsState.architecture_filter,
                        placeholder="Architecture",
                        on_change=DistributionsState.set_architecture_filter,
                        width="200px",
                        min_width="200px",
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("search")),
                        placeholder="Filter by package name...",
                        value=DistributionsState.search_value,
                        on_change=DistributionsState.set_search_value,
                        width="280px",
                        min_width="280px",
                    ),
                )
            ),
            justify="end",
            align="center",
            align_items="stretch",
            spacing="3",
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    _header_cell("Codename", "tag"),
                    _header_cell("Suite", "folder"),
                    _header_cell("Origin", "globe"),
                    _header_cell("Version", "hash"),
                    _header_cell("Components", "package"),
                    _header_cell("Architectures", "cpu"),
                    _header_cell("Packages", "boxes"),
                    _header_cell("Released", "calendar", nowrap=True, min_w="fit"),
                    _header_cell("Last Fetched", "clock", nowrap=True, min_w="fit"),
                    _header_cell("Actions", "package-search"),
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
    )
