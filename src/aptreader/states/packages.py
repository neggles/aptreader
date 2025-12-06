"""Packages browsing page."""

import logging

import reflex as rx
import sqlmodel as sm
from sqlmodel import select

from aptreader.models.packages import Architecture, Component, Package
from aptreader.models.repository import Distribution

logger = logging.getLogger(__name__)


class PackagesState(rx.State):
    distribution_id: int | None = None
    packages: list[dict] = []
    component_filter: str = "all"
    architecture_filter: str = "all"
    search_value: str = ""
    max_results: int = 250

    @rx.event
    def set_distribution(self, distribution_id: int | None):
        self.distribution_id = distribution_id
        self.component_filter = "all"
        self.architecture_filter = "all"
        self.search_value = ""
        self.load_packages()

    @rx.event
    def load_from_route(self):
        if "packages/" not in self.router.url.path:
            return rx.noop()
        route_splat = self.router.url.query_parameters.get("splat", [])
        if not route_splat:
            return rx.noop()
        dist_id = route_splat[0]
        if isinstance(dist_id, str) and dist_id.isdigit():
            dist_id_int = int(dist_id)
            if dist_id_int != self.distribution_id:
                self.set_distribution(dist_id_int)
        return rx.noop()

    @rx.event
    def load_packages(self):
        if self.distribution_id is None:
            self.packages = []
            return

        with rx.session() as session:
            query = select(Package).where(sm.any_(Package.distributions).id == self.distribution_id)

            if self.component_filter not in {"", "all"}:
                component = session.exec(
                    select(Component).where(
                        Component.distribution_id == self.distribution_id,
                        Component.name == self.component_filter,
                    )
                ).one_or_none()
                if component is None:
                    self.packages = []
                    return
                query = query.where(sm.any_(Package.components) == component)

            if self.architecture_filter not in {"", "all"}:
                architecture = session.exec(
                    select(Architecture).where(
                        Architecture.distribution_id == self.distribution_id,
                        Architecture.name == self.architecture_filter,
                    )
                ).one_or_none()
                if architecture is None:
                    self.packages = []
                    return
                query = query.where(architecture.id == sm.any_(Package.architectures))

            if self.search_value:
                search = f"%{self.search_value.lower()}%"
                query = query.where(
                    sm.or_(
                        sm.func.lower(Package.name).like(search),
                        sm.func.lower(Package.description).like(search),
                    )
                )

            query = query.order_by(Package.name).limit(self.max_results)
            rows = session.exec(query).all()
            component_ids = {comp.id for pkg in rows for comp in pkg.components if comp.id is not None}
            architecture_ids = {arch.id for pkg in rows for arch in pkg.architectures if arch.id is not None}

            component_map: dict[int, str] = {}
            if component_ids:
                component_rows = session.exec(
                    select(Component).where(Component.distribution_id == self.distribution_id)
                ).all()
                component_map = {
                    comp.id: comp.name
                    for comp in component_rows
                    if comp.id is not None and comp.id in component_ids
                }

            architecture_map: dict[int, str] = {}
            if architecture_ids:
                architecture_rows = session.exec(
                    select(Architecture).where(Architecture.distribution_id == self.distribution_id)
                ).all()
                architecture_map = {
                    arch.id: arch.name
                    for arch in architecture_rows
                    if arch.id is not None and arch.id in architecture_ids
                }

            formatted: list[dict] = []
            for pkg in rows:
                formatted.append(
                    {
                        "id": pkg.id,
                        "name": pkg.name,
                        "version": pkg.version,
                        "component": component_map.get(
                            pkg.components[0].id if pkg.components else None,  # type: ignore
                            "-",
                        ),
                        "architecture": architecture_map.get(
                            pkg.architectures[0].id if pkg.architectures else None,  # type: ignore
                            "-",
                        ),
                        "size": pkg.size,
                        "installed_size": pkg.installed_size,
                        "description": pkg.description,
                        "filename": pkg.filename,
                        "homepage": pkg.homepage,
                        "source": pkg.source,
                        "checksum_sha256": pkg.checksum_sha256,
                    }
                )
            self.packages = formatted

    @rx.event
    def set_component_filter(self, value: str):
        self.component_filter = value or "all"
        self.load_packages()

    @rx.event
    def set_architecture_filter(self, value: str):
        self.architecture_filter = value or "all"
        self.load_packages()

    @rx.event
    def set_search_value(self, value: str):
        self.search_value = value or ""
        self.load_packages()

    @rx.var
    def distribution(self) -> Distribution | None:
        if self.distribution_id is None:
            return None
        with rx.session() as session:
            return session.get(Distribution, self.distribution_id, populate_existing=True)

    @rx.var
    def component_options(self) -> list[str]:
        if self.distribution_id is None:
            return []
        with rx.session() as session:
            results = session.exec(
                select(Component.name)
                .where(Component.distribution_id == self.distribution_id)
                .order_by(Component.name)
            ).all()
            return list(results)

    @rx.var
    def architecture_options(self) -> list[str]:
        if self.distribution_id is None:
            return []
        with rx.session() as session:
            results = session.exec(
                select(Architecture.name)
                .where(Architecture.distribution_id == self.distribution_id)
                .order_by(Architecture.name)
            ).all()
            return list(results)

    @rx.var
    def component_filter_options(self) -> list[str]:
        options = self.component_options
        return ["all", *options] if options else ["all"]

    @rx.var
    def architecture_filter_options(self) -> list[str]:
        options = self.architecture_options
        return ["all", *options] if options else ["all"]

    @rx.var
    def packages_count(self) -> int:
        return len(self.packages)

    @rx.var
    def distribution_title(self) -> str:
        distribution = self.distribution
        return distribution.codename if distribution else "No distribution selected"
