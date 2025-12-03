import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

chip_props = {
    "radius": "full",
    "variant": "surface",
    "size": "3",
    "cursor": "pointer",
    "style": {"_hover": {"opacity": 0.75}},
}


class BasicChipsState(rx.State):
    items: set[str] = set()
    selected: set[str] = set()

    @rx.event
    def add_selected(self, item: str):
        self.selected.add(item)

    @rx.event
    def remove_selected(self, item: str):
        self.selected.remove(item)

    @rx.event
    def add_all_selected(self):
        self.selected.update(self.items)

    @rx.event
    def clear_selected(self):
        self.selected.clear()

    @rx.var
    def unselected(self) -> list[str]:
        return list(self.items - self.selected)


def action_button(
    icon: str,
    label: str,
    on_click: callable,
    color_scheme: LiteralAccentColor,
) -> rx.Component:
    return rx.button(
        rx.icon(icon, size=16),
        label,
        variant="soft",
        size="2",
        on_click=on_click,
        color_scheme=color_scheme,
        cursor="pointer",
    )


def selected_item_chip(item: str) -> rx.Component:
    return rx.badge(
        item,
        rx.icon("circle-x", size=18),
        color_scheme="green",
        **chip_props,
        on_click=BasicChipsState.remove_selected(item),
    )


def unselected_item_chip(item: str) -> rx.Component:
    return rx.cond(
        BasicChipsState.selected.contains(item),
        rx.fragment(),
        rx.badge(
            item,
            rx.icon("circle-plus", size=18),
            color_scheme="gray",
            **chip_props,
            on_click=BasicChipsState.add_selected(item),
        ),
    )


def selector(title: str, icon: str = "book") -> rx.Component:
    return rx.vstack(
        rx.flex(
            rx.hstack(
                rx.icon(icon, size=20),
                rx.heading(title, size="4"),
                spacing="1",
                align="center",
                width="100%",
                justify_content=["end", "start"],
            ),
            rx.hstack(
                action_button("plus", "Add All", BasicChipsState.add_all_selected, "green"),
                action_button("trash", "Clear All", BasicChipsState.clear_selected, "tomato"),
                spacing="2",
                justify="end",
                width="100%",
            ),
            justify="between",
            flex_direction=["column", "row"],
            align="center",
            spacing="2",
            margin_bottom="10px",
            width="100%",
        ),
        # Selected Items
        rx.flex(
            rx.foreach(BasicChipsState.selected, selected_item_chip),
            wrap="wrap",
            spacing="2",
            justify_content="start",
        ),
        rx.divider(),
        # Unselected Items
        rx.flex(
            rx.foreach(BasicChipsState.unselected, unselected_item_chip),
            wrap="wrap",
            spacing="2",
            justify_content="start",
        ),
        justify_content="start",
        align_items="start",
        width="100%",
    )
