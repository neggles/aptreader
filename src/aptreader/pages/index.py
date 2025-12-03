"""Main index page for aptreader."""

from email.policy import default

import reflex as rx

from aptreader.states.app import AppState
from aptreader.templates import template


@template(route="/", title="Repositories", on_load=AppState.on_load)
def index() -> rx.Component:
    """Main page component."""
    return rx.container(
        rx.heading("aptreader", size="9", margin_bottom="1em"),
        rx.text(
            "Browse APT repository metadata, packages, and files",
            color="gray",
            margin_bottom="2em",
        ),
        # Repository URL input section
        rx.vstack(
            rx.heading("Repository URL", size="5", margin_bottom="0.5em"),
            rx.input(
                placeholder="http://archive.ubuntu.com/ubuntu",
                value=AppState.repo_url,
                on_change=AppState.set_repo_url,
                width="100%",
            ),
            rx.box(
                rx.heading("Components", size="4", margin_bottom="0.5em"),
                rx.text(
                    "Select specific components or leave empty to include every component declared by the repo.",
                    color="gray",
                    margin_bottom="0.5em",
                    size="2",
                ),
                rx.checkbox_group.root(
                    rx.foreach(
                        AppState.available_components,
                        lambda comp: rx.checkbox_group.item(comp, value=comp),
                    ),
                    default_value=AppState.component_filter,
                ),
                padding="1em",
                border="1px solid #e0e0e0",
                border_radius="8px",
                width="100%",
            ),
            rx.box(
                rx.heading("Architectures", size="4", margin_bottom="0.5em"),
                rx.text(
                    "Choose which architectures to download (clear all to fetch every architecture).",
                    color="gray",
                    margin_bottom="0.5em",
                    size="2",
                ),
                rx.checkbox_group.root(
                    rx.foreach(
                        AppState.available_architectures,
                        lambda arch: rx.checkbox_group.item(arch, value=arch),
                    ),
                    default_value=AppState.architecture_filter,
                ),
                padding="1em",
                border="1px solid #e0e0e0",
                border_radius="8px",
                width="100%",
            ),
            rx.button(
                "Load Repository",
                on_click=AppState.load_repository,
                margin_top="1em",
            ),
            rx.cond(
                AppState.status_message != "",
                rx.text(AppState.status_message, margin_top="1em", color="green"),
            ),
            rx.cond(
                AppState.error_message != "",
                rx.text(AppState.error_message, margin_top="1em", color="red"),
            ),
            spacing="2",
            width="100%",
            margin_bottom="2em",
        ),
        # Repository browser section
        rx.cond(
            AppState.repo_loaded,
            rx.vstack(
                rx.divider(),
                rx.heading("Repository Contents", size="6", margin_top="1em", margin_bottom="1em"),
                # Release and component summary
                rx.cond(
                    AppState.repository is not None,
                    rx.vstack(
                        rx.foreach(
                            AppState.repository.releases,
                            lambda release_item: rx.box(
                                rx.heading(f"Release: {release_item[0]}", size="4"),
                                rx.text(
                                    f"Codename: {release_item[1].codename}",
                                    color="gray",
                                ),
                                rx.text(
                                    f"Suite: {release_item[1].suite}",
                                    color="gray",
                                ),
                                padding="1em",
                                border="1px solid #e0e0e0",
                                border_radius="8px",
                                margin_bottom="1em",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                width="100%",
            ),
        ),
        max_width="1200px",
        padding="2em",
    )
