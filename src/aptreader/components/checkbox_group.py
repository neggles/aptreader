import reflex as rx


class CBoxGroupState(rx.State):
    choices: dict[str, bool] = {}

    def check_choice(self, value: bool, key: str):
        self.choices[key] = value

    @rx.var
    def checked_choices(self) -> str:
        choices = [k for k, v in self.choices.items() if v]
        return " / ".join(choices) if choices else "None"


def checkbox_group(label: str, options: list[str]) -> rx.Component:
    """A checkbox group component.

    Args:
        label: The label for the checkbox group.
        options: The list of options for the checkboxes.

    Returns:
        The checkbox group component.
    """
    state = CBoxGroupState()
    for option in options:
        state.choices[option] = False

    return rx.vstack(
        rx.text(label, font_size="1.1em", font_weight="600", margin_bottom="0.5em"),
        rx.vstack(
            rx.foreach(
                options,
                lambda option: rx.checkbox(
                    option,
                    value=option,
                    on_change=state.check_choice,
                ),
            ),
            spacing="1",
        ),
        spacing="1.5",
    )
