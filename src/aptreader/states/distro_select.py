import logging

import reflex as rx
import sqlmodel as sm
from reflex.event import EventType

from aptreader.backend.backend import AppState
from aptreader.models.repository import Distribution

logger = logging.getLogger(__name__)


class DistroSelectState(rx.State):
    current_distro: Distribution | None

    @rx.var
    def current_distro_name(self) -> str:
        return self.current_distro.name if self.current_distro else "None"

    @rx.var
    async def available_distro_names(self) -> list[str]:
        app_state = await self.get_state(AppState)
        return app_state.distribution_names

    @rx.event
    async def load_from_route(self):
        """Load the current repository on component load."""
        # check the route for current distro id
        split_route = self.router.url.path.rsplit("/", 1)
        route_distro_id = split_route[-1] if split_route[-1].isdigit() else None
        if route_distro_id is not None:
            if isinstance(route_distro_id, str) and route_distro_id.isdigit():
                await self.select_distro_id(int(route_distro_id))
            else:
                logger.error(f"Invalid repository ID in route: {route_distro_id}")

    @rx.event
    async def select_distro_id(self, distro_id: int) -> EventType:
        if distro_id == (self.current_distro.id if self.current_distro else None):
            return rx.noop()

        async with rx.asession() as session:
            distro = await session.get(Distribution, distro_id)
            if not distro:
                logger.error(f"Distribution with ID {distro_id} not found in database.")
                return rx.toast.error(f"Distribution with ID {distro_id} not found.")
        return await self.select_repo(distro)

    @rx.event
    async def select_distro_name(self, distro_name: str) -> EventType:
        """Set the current repository by name."""

        if distro_name == self.current_distro_name:
            logger.debug("Selected repository is the same as current; no action taken.")
            return rx.noop()

        if distro_name is not None:
            async with rx.asession() as session:
                stmt = sm.select(Distribution).where(Distribution.name == distro_name)
                result = await session.exec(stmt)
                distro = result.one_or_none()
                return await self.select_repo(distro)

    @rx.event
    async def select_repo(self, distro: Distribution | None) -> EventType:
        """Set the current repository object."""
        if distro is None:
            logger.error("No repository provided to select.")
            return rx.toast.error("Selected repository not found.")
        if self.current_distro == distro:
            logger.debug("Requested repository is unchanged, not updating.")
            return rx.noop()
        else:
            logger.info(f"Selected repository {distro.name} {distro.id=}")
            self.current_distro = distro

        app_state = await self.get_state(AppState)
        app_state.current_distro = self.current_distro

        split_route = app_state.router.url.path.rsplit("/", 1)
        last_part = split_route[-1]
        if len(split_route) == 1 or last_part == "" or not last_part.isdigit():
            logger.info(f"Distribution ID change: null -> {distro.id}, updating route")
            return rx.redirect(f"{'/'.join(split_route)}/{distro.id}")
        elif last_part != str(distro.id):
            logger.info(f"Distribution ID change: {last_part} -> {distro.id}, updating route")
            return [
                rx.redirect(f"{'/'.join(split_route[:-1])}/{distro.id}"),
                rx.toast.info(f"Selected repository: {distro.name}"),
            ]
        else:
            logger.info("Distribution ID unchanged; no route update needed.")
            return rx.toast.info(f"Selected repository: {distro.name}")
