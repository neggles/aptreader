import reflex as rx
import reflex_enterprise as rxe

from aptreader.pages.packages import PackagesState


def packages_filters() -> rx.Component:
    return rx.flex(
        rx.vstack(
            rx.text(PackagesState.distribution_title, size="5", weight="bold"),
            spacing="1",
        ),
        rx.spacer(),
        rx.select(
            PackagesState.component_filter_options,
            value=PackagesState.component_filter,
            label="Component",
            on_change=PackagesState.set_component_filter,
            width="200px",
        ),
        rx.select(
            PackagesState.architecture_filter_options,
            value=PackagesState.architecture_filter,
            label="Architecture",
            on_change=PackagesState.set_architecture_filter,
            width="200px",
        ),
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Filter by package name...",
            value=PackagesState.search_value,
            on_change=PackagesState.set_search_value,
            width="280px",
        ),
        rx.badge(
            rx.hstack(
                rx.text(PackagesState.packages_count, weight="bold"),
                rx.text(" shown (limit "),
                rx.text(PackagesState.max_results),
                rx.text(")"),
                spacing="1",
                align="center",
            ),
            color_scheme="gray",
            size="2",
        ),
        align="center",
        spacing="3",
        wrap="wrap",
        width="100%",
    )


def show_package(pkg: dict) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(rx.text(pkg.get("name", "-"), weight="bold")),
        rx.table.cell(rx.text(pkg.get("version", "-"))),
        rx.table.cell(rx.badge(pkg.get("component", "-"), color_scheme="blue", size="1")),
        rx.table.cell(rx.badge(pkg.get("architecture", "-"), color_scheme="mint", size="1")),
        rx.table.cell(
            rx.text(
                rxe.mantine.number_formatter(
                    pkg.get("size"),
                )
            )
        ),
        rx.table.cell(
            rx.text(
                pkg.get("description", "-"),
                size="2",
                max_width="38ch",
                white_space="normal",
            )
        ),
        rx.table.cell(
            rx.vstack(
                rx.code(pkg.get("filename", ""), size="1", max_width="42ch"),
                rx.cond(
                    pkg.get("homepage"),
                    rx.link("Homepage", href=pkg.get("homepage"), is_external=True, size="1"),
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
