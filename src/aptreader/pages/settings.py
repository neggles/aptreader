import reflex as rx

from aptreader.states.settings import SettingsState
from aptreader.templates import template


@template(route="/settings", on_load=SettingsState.on_load)
def settings() -> rx.Component:
    """Settings panel for configuring cache directory and other options."""
    return rx.vstack(
        rx.heading("Settings", size="6", margin_bottom="1em"),
        rx.text("Configure aptreader options below.", color="gray", margin_bottom="1em"),
        rx.input(
            label="Cache Directory",
            value=SettingsState.cache_dir_str,
            on_change=SettingsState.set_cache_dir,
            width="100%",
            placeholder="e.g. ~/.cache/aptreader",
        ),
        rx.button(
            "Save Settings",
            on_click=SettingsState.save_settings,
            margin_top="1em",
        ),
        rx.cond(
            SettingsState.message is not None,
            rx.text(SettingsState.message, color="green", margin_top="1em"),
        ),
        spacing="2",
        width="100%",
        padding="1em",
        border="1px solid #e0e0e0",
        border_radius="8px",
    )
