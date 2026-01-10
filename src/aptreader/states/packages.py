"""Packages browsing page."""

import logging

import reflex as rx
import sqlmodel as sm

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
        if "packages" not in self.router.url.path:
            logger.info("Not on packages route; skipping load_from_route.")
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
            query = Package.select().where(Package.distribution_id == self.distribution_id)

            if self.component_filter not in {"", "all"}:
                component = session.exec(
                    Component.select().where(
                        Component.repository_id == Package.repository_id,
                        Component.name == self.component_filter,
                    )
                ).one_or_none()
                if component is None:
                    self.packages = []
                    return
                query = query.where(Package.component == component)

            if self.architecture_filter not in {"", "all"}:
                architecture = session.exec(
                    Architecture.select().where(
                        Architecture.repository_id == Package.repository_id,
                        Architecture.name == self.architecture_filter,
                    )
                ).one_or_none()
                if architecture is None:
                    self.packages = []
                    return
                query = query.where(Package.architecture == architecture)

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

            formatted: list[dict] = []
            for pkg in rows:
                formatted.append(
                    {
                        "id": pkg.id,
                        "name": pkg.name,
                        "version": pkg.version,
                        "component": pkg.component.name if pkg.component else "-",
                        "architecture": pkg.architecture.name if pkg.architecture else "-",
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
            dist = session.get(Distribution, self.distribution_id)
            if not dist:
                return []
            dist.components.sort(key=lambda c: c.name.lower())
            results = [c.name for c in dist.components]
            return results

    @rx.var
    def architecture_options(self) -> list[str]:
        if self.distribution_id is None:
            return []
        with rx.session() as session:
            dist = session.get(Distribution, self.distribution_id)
            if not dist:
                return []
            dist.architectures.sort(key=lambda a: a.name.lower())
            results = [a.name for a in dist.architectures]
            return results

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
        if not distribution:
            return "No distribution selected"

        dist_name = distribution.name if distribution.name else None
        dist_codename = distribution.codename if distribution.codename else None
        if dist_name and dist_codename:
            return f"{dist_name} ({dist_codename})"
        elif dist_name:
            return dist_name
        elif dist_codename:
            return dist_codename
        else:
            return "Unnamed Distribution"
