import reflex as rx

from aptreader.components.repo_select import repo_select
from aptreader.models.packages import Package
from aptreader.states.packages import PackagesState


def packages_filters() -> rx.Component:
    return rx.flex(
        repo_select(),
        rx.spacer(),
        rx.select(
            PackagesState.component_filter_options,
            value=PackagesState.component_filter,
            label="Component",
            on_change=PackagesState.set_component_filter,
            width="200px",
            min_width="200px",
        ),
        rx.select(
            PackagesState.architecture_filter_options,
            value=PackagesState.architecture_filter,
            label="Architecture",
            on_change=PackagesState.set_architecture_filter,
            width="200px",
            min_width="200px",
        ),
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Filter by package name...",
            value=PackagesState.search_value,
            on_change=PackagesState.set_search_value,
            width="280px",
            min_width="280px",
        ),
        rx.badge(
            rx.text(f"{PackagesState.packages_count} shown (limit {PackagesState.max_results})"),
            color_scheme="gray",
            variant="outline",
            size="2",
        ),
        direction="row",
        align="center",
        spacing="3",
        wrap="wrap",
        width="100%",
    )


def format_size(val: int | float | None) -> str:
    if val is None:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024:
            return f"{val:.1f} {unit}"
        val /= 1024
    return f"{val:.1f} PB"


def show_package(pkg: Package) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(rx.text(pkg.name, weight="bold")),
        rx.table.cell(rx.text(pkg.version, "-")),
        rx.table.cell(rx.badge(pkg.components, color_scheme="blue", size="1")),
        rx.table.cell(rx.badge(pkg.architectures, color_scheme="mint", size="1")),
        rx.table.cell(rx.text(pkg.size_str, size="2")),
        rx.table.cell(rx.text(pkg.description, size="2", max_width="38ch", white_space="normal")),
        rx.table.cell(
            rx.vstack(
                rx.code(pkg.filename, size="1", max_width="42ch"),
                rx.cond(
                    pkg.homepage,
                    rx.link("Homepage", href=pkg.homepage, is_external=True, size="1"),
                    rx.fragment(),
                ),
                spacing="1",
                align="start",
            )
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="start",
    )


def packages_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Name"),
                rx.table.column_header_cell("Version"),
                rx.table.column_header_cell("Component"),
                rx.table.column_header_cell("Arch"),
                rx.table.column_header_cell("Size"),
                rx.table.column_header_cell("Description"),
                rx.table.column_header_cell("Files"),
            )
        ),
        rx.table.body(
            rx.cond(
                PackagesState.packages,
                rx.foreach(PackagesState.packages, show_package),
                rx.table.row(
                    rx.table.cell(
                        rx.text("No packages match your filters."),
                        col_span=7,
                        align="center",
                    )
                ),
            )
        ),
        variant="surface",
        size="3",
        width="100%",
        on_mount=PackagesState.load_from_route,
    )
