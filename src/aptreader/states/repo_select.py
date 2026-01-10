import logging

import reflex as rx
import sqlmodel as sm
from reflex.event import EventType

from aptreader.backend.backend import AppState
from aptreader.models.repository import Repository

logger = logging.getLogger(__name__)


class RepoSelectState(rx.State):
    current_repo: Repository | None

    @rx.var
    def current_repo_name(self) -> str:
        return self.current_repo.name if self.current_repo else "None"

    @rx.var
    async def available_repo_names(self) -> list[str]:
        app_state = await self.get_state(AppState)
        return app_state.repository_names

    @rx.event
    async def load_from_route(self):
        """Load the current repository on component load."""
        # check the route for current repo id
        split_route = self.router.url.path.rsplit("/", 1)
        route_repo_id = split_route[-1] if split_route[-1].isdigit() else None
        if route_repo_id is not None:
            if isinstance(route_repo_id, str) and route_repo_id.isdigit():
                await self.select_repo_id(int(route_repo_id))
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
        return await self.select_repo(repo)

    @rx.event
    async def select_repo_name(self, repo_name: str) -> EventType:
        """Set the current repository by name."""

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
        """Set the current repository object."""
        if repo is None:
            logger.error("No repository provided to select.")
            return rx.toast.error("Selected repository not found.")
        if self.current_repo == repo:
            logger.debug("Requested repository is unchanged, not updating.")
            return rx.noop()
        else:
            logger.info(f"Selected repository {repo.name} {repo.id=}")
            self.current_repo = repo

        app_state = await self.get_state(AppState)
        app_state.current_repo = self.current_repo

        split_route = app_state.router.url.path.rsplit("/", 1)
        if "distributions" not in self.router.url.path:
            return rx.noop()

        last_part = split_route[-1]
        if len(split_route) == 1 or last_part == "" or not last_part.isdigit():
            logger.info(f"Repository ID change: null -> {repo.id}, updating route")
            return rx.redirect(f"{'/'.join(split_route)}/{repo.id}")
        elif last_part != str(repo.id):
            logger.info(f"Repository ID change: {last_part} -> {repo.id}, updating route")
            return [
                rx.redirect(f"{'/'.join(split_route[:-1])}/{repo.id}"),
                rx.toast.info(f"Selected repository: {repo.name}"),
            ]
        else:
            logger.info("Repository ID unchanged; no route update needed.")
            return rx.toast.info(f"Selected repository: {repo.name}")
