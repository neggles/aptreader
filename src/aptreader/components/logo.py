import reflex as rx


def logo() -> rx.Component:
    """The logo component.

    Returns:
        rx.Component: The logo component.
    """
    return rx.hstack(
        rx.icon("package"),
        rx.text("aptreader", weight="bold"),
        align="center",
        justify="between",
        spacing="2",
    )
