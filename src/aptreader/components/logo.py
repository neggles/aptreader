import reflex as rx


def logo() -> rx.Component:
    """The logo component.

    Returns:
        rx.Component: The logo component.
    """
    return rx.hstack(
        rx.color_mode_cond(
            rx.image(src="/package-dark.svg", height="1.5em"),
            rx.image(src="/package-light.svg", height="1.5em"),
        ),
        rx.text("aptreader", size="4", weight="bold"),
        align="center",
        spacing="2",
    )
