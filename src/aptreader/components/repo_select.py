import logging
from cProfile import label

import reflex as rx
from reflex.event import EventType

from aptreader.backend.backend import AppState
from aptreader.models.repository import Repository

logger = logging.getLogger(__name__)


class RepoSelectState(rx.State):
    @rx.event
    async def update_repo_select(self, repo_name: str) -> EventType:
        """Set the current repository."""
        logger.info(f"Selected repository: {repo_name}")

        state: AppState = await self.get_state(AppState)
        if repo_name == state.current_repo_name:
            return rx.noop()

        if repo_name is not None:
            state.set_current_repo_name(repo_name)
            repo_id = state.current_repo.id if state.current_repo else None
            return rx.redirect(f"/distributions/{repo_id}" if repo_id else "/distributions")


def repo_select() -> rx.Component:
    """Repository selection dropdown component.

    Returns:
        The repository selection component.

    """
    return rx.select(
        AppState.repository_names,
        value=AppState.current_repo_name,
        on_change=RepoSelectState.update_repo_select,
        label="Select Repository",
        width="10%",
    )
