import asyncio

import reflex as rx

from ..backend.backend import Repository, State
from ..components.form_field import form_field


def show_repository(repo: Repository):
    return rx.table.row(
        rx.table.cell(repo.name),
        rx.table.cell(repo.url),
        rx.table.cell(repo.update_ts),
        rx.table.cell(
            rx.hstack(
                update_repository_dialog(repo),
                rx.icon_button(
                    rx.icon("trash-2", size=22),
                    on_click=lambda: State.delete_repository(repo.id),
                    size="2",
                    variant="solid",
                    color_scheme="red",
                ),
                align="end",
            )
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def add_repository_button() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text("Add Repository", size="4", display=["none", "none", "block"]),
                size="3",
            ),
        ),
        rx.dialog.content(
            rx.hstack(
                rx.badge(
                    rx.icon("archive", size=34),
                    color_scheme="grass",
                    radius="full",
                    padding="0.65rem",
                ),
                rx.vstack(
                    rx.dialog.title(
                        "Add New Repository",
                        weight="bold",
                        margin="0",
                    ),
                    rx.dialog.description(
                        "Fill in the repository's info",
                    ),
                    spacing="1",
                    height="100%",
                    align_items="start",
                ),
                height="100%",
                spacing="4",
                margin_bottom="1.5em",
                align_items="center",
                width="100%",
            ),
            rx.flex(
                rx.form.root(
                    rx.flex(
                        # Name
                        form_field(
                            "Name",
                            "Repository Name",
                            "text",
                            "name",
                            "user",
                        ),
                        # URL
                        form_field(
                            "URL",
                            "Repository URL",
                            "text",
                            "url",
                            "link-2",
                        ),
                        direction="column",
                        spacing="3",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                color_scheme="gray",
                            ),
                        ),
                        rx.form.submit(
                            rx.dialog.close(
                                rx.button("Submit Repository"),
                            ),
                            as_child=True,
                        ),
                        padding_top="2em",
                        spacing="3",
                        mt="4",
                        justify="end",
                    ),
                    on_submit=State.add_repository_to_db,
                    reset_on_submit=False,
                ),
                width="100%",
                direction="column",
                spacing="4",
            ),
            max_width="450px",
            padding="1.5em",
            border=f"2px solid {rx.color('accent', 7)}",
            border_radius="25px",
        ),
    )


def update_repository_dialog(repo: Repository):
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("square-pen"),
                rx.text("Edit", size="3"),
                color_scheme="blue",
                size="2",
                variant="solid",
                on_click=lambda: State.get_repository(repo),
            ),
        ),
        rx.dialog.content(
            rx.hstack(
                rx.badge(
                    rx.icon(tag="square-pen"),
                    color_scheme="grass",
                    radius="full",
                    padding="0.65rem",
                ),
                rx.vstack(
                    rx.dialog.title(
                        "Edit Repository",
                        weight="bold",
                        margin="0",
                    ),
                    spacing="1",
                    height="100%",
                    align_items="start",
                ),
                height="100%",
                spacing="4",
                margin_bottom="1.5em",
                align_items="center",
                width="100%",
            ),
            rx.flex(
                rx.form.root(
                    rx.flex(
                        # Name
                        form_field("Name", "Repository Name", "text", "name", "user", repo.name),
                        # URL
                        form_field("URL", "Repository URL", "text", "url", "link-2", repo.url),
                        direction="column",
                        spacing="3",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft", color_scheme="gray"),
                        ),
                        rx.form.submit(
                            rx.dialog.close(rx.button("Update Repository")),
                            as_child=True,
                        ),
                        padding_top="2em",
                        spacing="3",
                        mt="4",
                        justify="end",
                    ),
                    on_submit=State.update_repository_in_db,
                    reset_on_submit=False,
                ),
                width="100%",
                direction="column",
                spacing="4",
            ),
            max_width="450px",
            padding="1.5em",
            border=f"2px solid {rx.color('accent', 7)}",
            border_radius="25px",
        ),
    )


def _header_cell(text: str, icon: str, max_width: str | None = None) -> rx.Component:
    return rx.table.column_header_cell(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text),
            align="center",
            spacing="2",
        ),
        max_width=max_width,
    )


class SpinnerState(rx.State):
    loading: bool = False

    @rx.event(background=True)
    async def start_loading(self):
        async with self:
            self.loading = True
        State.load_repositories(True)
        async with self:
            self.loading = False


def repositories_table():
    return rx.fragment(
        rx.flex(
            add_repository_button(),
            rx.spacer(),
            rx.button(
                rx.icon(
                    "refresh-cw",
                    style={"animation": rx.cond(SpinnerState.loading, "spin 1s linear infinite", "none")},
                ),
                rx.text("Reload repositories", size="3", display=["none", "none", "block"]),
                size="3",
                on_click=SpinnerState.start_loading,
            ),
            rx.cond(
                State.sort_reverse,
                rx.icon(
                    "arrow-down-z-a",
                    size=28,
                    stroke_width=1.5,
                    cursor="pointer",
                    on_click=State.toggle_sort,
                ),
                rx.icon(
                    "arrow-down-a-z",
                    size=28,
                    stroke_width=1.5,
                    cursor="pointer",
                    on_click=State.toggle_sort,
                ),
            ),
            rx.select(
                ["name", "url", "update_ts"],
                placeholder="Sort By: Name",
                size="3",
                on_change=lambda sort_value: State.sort_values(sort_value),
            ),
            rx.input(
                rx.input.slot(rx.icon("search")),
                placeholder="Search here...",
                size="3",
                max_width="240px",
                width="100%",
                variant="surface",
                on_change=lambda value: State.filter_values(value),
            ),
            justify="end",
            align="center",
            spacing="3",
            wrap="wrap",
            width="100%",
            padding_bottom="1em",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    _header_cell("Name", "user"),
                    _header_cell("URL", "link-2"),
                    _header_cell("Last Updated", "calendar"),
                    _header_cell("Actions", "cog", max_width="100px"),
                ),
            ),
            rx.table.body(
                rx.foreach(State.repositories, show_repository),
            ),
            variant="surface",
            size="3",
            width="100%",
            on_mount=State.load_repositories,
        ),
    )
