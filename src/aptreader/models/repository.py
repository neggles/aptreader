import logging
from datetime import datetime

import reflex as rx
import sqlmodel as sm
from dateutil.parser import parse as parse_date
from pydantic import computed_field
from sqlmodel import JSON, Field, Relationship, UniqueConstraint, func, select

from aptreader.models import Architecture, Component, Package

from .links import DistributionArchitectureLink, DistributionComponentLink, DistributionPackageLink

logger = logging.getLogger(__name__)


# fmt: off
ORDERED_COMPONENTS = [
    "main", "contrib", "non-free", "non-free-firmware",
    "restricted", "universe", "multiverse",
]
N_ORDERED_COMPONENTS = len(ORDERED_COMPONENTS)

ORDERED_ARCHITECTURES = [
    "i386", "amd64", "amd64v3",
    "armel", "armhf", "arm64", "aarch64",
    "riscv32", "riscv64",
    "mipsel", "mips64el",
    "la64", "loongarch64",
    "powerpc", "ppc32", "ppc64el",
    "s390", "s390x",
]
N_ORDERED_ARCHITECTURES = len(ORDERED_ARCHITECTURES)
# fmt: on


class Distribution(rx.Model, table=True):
    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_distribution_repository_name"),)

    name: str = Field(index=True)
    date: str | None = Field(default=None)
    description: str | None = Field(default=None)
    origin: str | None = Field(default=None)
    suite: str | None = Field(default=None)
    version: str | None = Field(default=None)
    codename: str | None = Field(default=None)
    architecture_names: list[str] = Field(sa_type=JSON, default_factory=list)
    component_names: list[str] = Field(sa_type=JSON, default_factory=list)
    raw: str | None = Field(default=None, repr=False)

    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE")
    repository: "Repository" = Relationship(
        back_populates="distributions",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    components: list["Component"] = Relationship(
        back_populates="distributions",
        link_model=DistributionComponentLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    architectures: list["Architecture"] = Relationship(
        back_populates="distributions",
        link_model=DistributionArchitectureLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    packages: list["Package"] = Relationship(
        back_populates="distribution",
        link_model=DistributionPackageLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    last_fetched_at: datetime | None = Field(
        default=None,
        sa_column=sm.Column(
            "last_fetched_at",
            sm.DateTime(timezone=True),
            server_default=sm.func.now(),
            onupdate=sm.func.now(),
            nullable=False,
        ),
    )

    @computed_field
    @property
    def format_date(self) -> str | None:
        """Get the parsed date as a datetime object."""
        if self.date is None:
            return None
        try:
            date_val = parse_date(self.date)
            return date_val.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse date '{self.date}': {e}")
            return None

    @computed_field
    @property
    def format_last_fetched_at(self) -> str | None:
        """Get the parsed date as a datetime object."""
        if self.last_fetched_at is None:
            return None
        try:
            return self.last_fetched_at.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse date '{self.last_fetched_at}': {e}")
            return None

    @computed_field
    @property
    def format_components(self) -> list[str]:
        """Get the components sorted in a preferred order."""
        not_in_ordered = sorted([c for c in self.component_names if c not in ORDERED_COMPONENTS])

        def sort_fn(c):
            if c in ORDERED_COMPONENTS:
                return ORDERED_COMPONENTS.index(c)
            return N_ORDERED_COMPONENTS + not_in_ordered.index(c)

        return sorted(self.component_names, key=sort_fn)

    @computed_field
    @property
    def format_architectures(self) -> list[str]:
        """Get the architectures sorted in a preferred order."""

        not_in_ordered = sorted([c for c in self.architecture_names if c not in ORDERED_ARCHITECTURES])

        def sort_fn(c):
            if c in ORDERED_ARCHITECTURES:
                return ORDERED_ARCHITECTURES.index(c)
            return N_ORDERED_ARCHITECTURES + not_in_ordered.index(c)

        return sorted(self.architecture_names, key=sort_fn)

    @computed_field
    @property
    def package_count(self) -> int:
        """Get the number of packages for this distribution."""
        with rx.session() as session:
            q = (
                select(func.count())
                .select_from(Package)
                .where(Package.repository_id == self.repository_id, Package.distribution_id == self.id)
            )
            count = session.scalar(q)
            return count if count is not None else 0


class Repository(rx.Model, table=True):
    """The apt repository model."""

    name: str = Field(index=True, unique=True)
    url: str = Field(index=True, unique=True)

    distributions: list["Distribution"] = Relationship(back_populates="repository", cascade_delete=True)
    components: list["Component"] = Relationship(back_populates="repository", cascade_delete=True)
    architectures: list["Architecture"] = Relationship(back_populates="repository", cascade_delete=True)
    packages: list["Package"] = Relationship(back_populates="repository")

    last_fetched_at: datetime | None = Field(
        default=None,
        sa_column=sm.Column(
            "last_fetched_at",
            sm.DateTime(timezone=True),
            server_default=sm.func.now(),
            onupdate=sm.func.now(),
            nullable=False,
        ),
    )

    @computed_field
    @property
    def repo_distribution_count(self) -> int:
        """Get the number of distributions for this repository."""
        with rx.session() as session:
            q = select(func.count()).select_from(Distribution).where(Distribution.repository_id == self.id)
            count = session.scalar(q)
            return count or 0

    @computed_field
    @property
    def package_count(self) -> int:
        """Get the number of packages for this repository."""
        with rx.session() as session:
            q = select(func.count()).select_from(Package).where(Package.repository_id == self.id)
            count = session.scalar(q)
            return count if count is not None else 0
