import logging

import reflex as rx

from aptreader.states import RepoSelectState

logger = logging.getLogger(__name__)


def repo_select(**props) -> rx.Component:
    props = {**RepoSelectState.DEFAULT_PROPS, **props}
    # Create the select component
    return rx.select(
        RepoSelectState.available_repo_names,
        value=RepoSelectState.current_repo_name,
        on_change=RepoSelectState.select_repo_name,
        **props,
    )
