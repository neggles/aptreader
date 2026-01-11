"""Packages browsing page."""

import logging

import reflex as rx
import sqlmodel as sm
from sqlalchemy.orm import selectinload

from aptreader.models.packages import Architecture, Component, Package
from aptreader.models.repository import Distribution

logger = logging.getLogger(__name__)


class PackagesState(rx.State):
    current_distro: Distribution | None
    packages: list[Package] = []

    component_filter: str = "all"
    architecture_filter: str = "all"
    search_value: str = ""
    max_results: int = 250

    @rx.event
    def set_distribution(self, distribution: Distribution | None):
        self.current_distro = distribution
        self.component_filter = "all"
        self.architecture_filter = "all"
        self.search_value = ""
        self.load_packages()

    @rx.event
    def load_packages(self):
        if self.current_distro is None:
            self.packages = []
            return

        with rx.session() as session:
            query = Package.select().where(Package.distribution_id == self.current_distro.id)

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
                        Package.name.ilike(search),  # type: ignore
                        Package.description.ilike(search),  # type: ignore
                    )
                )

            query = query.order_by(Package.name).limit(self.max_results)
            rows = session.exec(query).all()

            self.packages = list(rows)

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
        if self.current_distro is None:
            return None
        with rx.session() as session:
            return session.get(Distribution, self.current_distro.id, populate_existing=True)

    @rx.var
    def component_options(self) -> list[str]:
        if self.current_distro is None:
            return []
        with rx.session() as session:
            dist = session.get(
                Distribution,
                self.current_distro.id,
                options=[selectinload(Distribution.components)],  # type: ignore
                populate_existing=True,
            )
            if not dist:
                return []
            dist.components.sort(key=lambda c: c.name.lower())
            results = [c.name for c in dist.components]
            return results

    @rx.var
    def architecture_options(self) -> list[str]:
        if self.current_distro is None:
            return []
        with rx.session() as session:
            dist = session.get(
                Distribution,
                self.current_distro.id,
                options=[selectinload(Distribution.architectures)],  # type: ignore
                populate_existing=True,
            )
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
