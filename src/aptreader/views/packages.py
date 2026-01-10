import reflex as rx

from aptreader.components.selectors import distro_select, repo_select
from aptreader.models.packages import Package
from aptreader.states.packages import PackagesState


def packages_filters() -> rx.Component:
    return rx.flex(
        repo_select(),
        distro_select(),
        rx.spacer(),
        rx.card(
            rx.hstack(
                rx.select(
                    PackagesState.component_filter_options,
                    value=PackagesState.component_filter,
                    placeholder="Component",
                    on_change=PackagesState.set_component_filter,
                    width="200px",
                    min_width="200px",
                ),
                rx.select(
                    PackagesState.architecture_filter_options,
                    value=PackagesState.architecture_filter,
                    placeholder="Architecture",
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
            )
        ),
        justify="end",
        align="center",
        align_items="stretch",
        spacing="3",
        width="100%",
    )


def show_package(pkg: Package) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(rx.text(pkg.name, weight="bold")),
        rx.table.cell(rx.text(pkg.version, "-")),
        rx.table.cell(rx.badge(pkg.component, color_scheme="blue", size="1")),
        rx.table.cell(rx.badge(pkg.architecture, color_scheme="mint", size="1")),
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


def packages_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                _header_cell("Name", "package", max_w="min"),
                _header_cell("Version", "tag", max_w="min"),
                _header_cell("Component", "layers", max_w="min"),
                _header_cell("Arch", "cpu", w="min"),
                _header_cell("Size", "database", w="min"),
                _header_cell("Description", "text"),
                _header_cell("Link", "folder", w="min"),
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
