import logging
from typing import Any, ClassVar

import reflex as rx
import sqlmodel as sm
from reflex.event import EventType

from aptreader.backend.backend import AppState
from aptreader.models.repository import Repository

logger = logging.getLogger(__name__)


class RepoSelectState(rx.State):
    current_repo: Repository | None

    DEFAULT_PROPS: ClassVar[dict[str, Any]] = {
        "label": "Repository",
        "placeholder": "Select...",
        "width": "10%",
    }

    @rx.event
    def load_from_route(self):
        """Load the current repository on component load."""
        # check the route for current repo id
        route_repo_id = self.router.url.query_parameters.get("splat", [None])[0]
        if route_repo_id is not None:
            if isinstance(route_repo_id, str) and route_repo_id.isdigit():
                self.select_repo_id(int(route_repo_id))
            else:
                logger.error(f"Invalid repository ID in route: {route_repo_id}")

    @rx.event
    async def select_repo_id(self, repo_id: int) -> EventType:
        if repo_id == (self.current_repo.id if self.current_repo else None):
            return rx.noop()

        async with rx.asession() as session:
            repo = await session.get(Repository, repo_id)
            if not repo:
                logger.error(f"Repository with ID {repo_id} not found in database.")
                return rx.toast.error(f"Repository with ID {repo_id} not found.")
        return await self._select_repo(repo)

    @rx.event
    async def select_repo_name(self, repo_name: str) -> EventType:
        """Set the current repository."""

        if repo_name == self.current_repo_name:
            logger.debug("Selected repository is the same as current; no action taken.")
            return rx.noop()

        if repo_name is not None:
            async with rx.asession() as session:
                stmt = sm.select(Repository).where(Repository.name == repo_name)
                result = await session.exec(stmt)
                repo = result.one_or_none()
                return await self.select_repo(repo)

    @rx.event
    async def select_repo(self, repo: Repository | None) -> EventType:
        """Set the current repository by ID."""
        if repo is None:
            logger.error("No repository provided to select.")
            return rx.toast.error("Selected repository not found.")
        if self.current_repo == repo:
            logger.debug("Requested repository is unchanged, not updating.")
            return rx.noop()
        else:
            logger.info(f"Selected repository {repo.name} {repo.id=})")
            self.current_repo = repo

        app_state = await self.get_state(AppState)
        app_state.current_repo = self.current_repo

        current_route = self.router.url.path
        return [rx.redirect(current_route), rx.toast.info(f"Selected repository: {repo.name}")]

    @rx.var
    def current_repo_name(self) -> str | None:
        return self.current_repo.name if self.current_repo else None

    @rx.var
    async def available_repo_names(self) -> list[str]:
        app_state = await self.get_state(AppState)
        return app_state.repository_names


def repo_select(**props) -> rx.Component:
    props = {**RepoSelectState.DEFAULT_PROPS, **props}
    # Create the select component
    return rx.select(
        RepoSelectState.available_repo_names,
        value=RepoSelectState.current_repo_name,
        on_change=RepoSelectState.select_repo_name,
        **props,
    )
