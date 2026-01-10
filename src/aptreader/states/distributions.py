"""Distributions browsing page."""

import logging

import reflex as rx
import sqlmodel as sm
from sqlalchemy.orm import selectinload

from aptreader.models import Distribution, Repository

logger = logging.getLogger(__name__)


class DistributionsState(rx.State):
    current_repo: Repository | None
    distributions: list[Distribution] = []

    component_filter: str = "all"
    architecture_filter: str = "all"
    search_value: str = ""
    max_results: int = 250

    @rx.var
    def current_repo_id(self) -> int | None:
        return self.current_repo.id if self.current_repo else None

    @rx.event
    def load_distributions(self):
        if self.current_repo_id is None:
            self.distributions = []
            return

        with rx.session() as session:
            query = Distribution.select().where(Distribution.repository_id == self.current_repo_id)

            if self.search_value:
                search = f"%{self.search_value.lower()}%"
                query = query.where(
                    sm.or_(
                        sm.func.lower(Distribution.name).like(search),
                        sm.func.lower(Distribution.codename).like(search),
                        sm.func.lower(Distribution.description).like(search),
                        sm.func.lower(Distribution.version).like(search),
                        sm.func.lower(Distribution.origin).like(search),
                        sm.func.lower(Distribution.suite).like(search),
                    )
                )

            query = query.order_by(Distribution.name).limit(self.max_results)
            rows = session.exec(query).all()
            self.distributions = list(rows)

    @rx.event
    def set_component_filter(self, value: str):
        self.component_filter = value or "all"
        self.load_distributions()

    @rx.event
    def set_architecture_filter(self, value: str):
        self.architecture_filter = value or "all"
        self.load_distributions()

    @rx.event
    def set_search_value(self, value: str):
        self.search_value = value or ""
        self.load_distributions()

    @rx.var
    def component_options(self) -> list[str]:
        if self.current_repo_id is None:
            return []
        with rx.session() as session:
            repo = session.get(
                Repository,
                self.current_repo_id,
                options=[selectinload(Repository.components)],  # type: ignore
                populate_existing=True,
            )
            if not repo:
                return []
            repo.components.sort(key=lambda c: c.name.lower())
            results = [c.name for c in repo.components]
            return results

    @rx.var
    def architecture_options(self) -> list[str]:
        if self.current_repo_id is None:
            return []
        with rx.session() as session:
            repo = session.get(
                Repository,
                self.current_repo_id,
                options=[selectinload(Repository.architectures)],  # type: ignore
                populate_existing=True,
            )
            if not repo:
                return []
            repo.architectures.sort(key=lambda a: a.name.lower())
            results = [a.name for a in repo.architectures]
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
    def distributions_count(self) -> int:
        return len(self.distributions)
