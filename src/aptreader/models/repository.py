import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import reflex as rx
import sqlmodel as sm
from dateutil.parser import parse as parse_date
from pydantic import computed_field
from sqlmodel import JSON, DateTime, Field, Relationship, func, select

if TYPE_CHECKING:
    from aptreader.models.packages import Architecture, Component

from aptreader.models import Package

from .links import PackageDistributionLink

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
    architectures: list[str] = Field(sa_type=JSON, default_factory=list)
    components: list[str] = Field(sa_type=JSON, default_factory=list)
    date: str | None = Field(default=None)
    description: str | None = Field(default=None)
    origin: str
    suite: str
    version: str
    codename: str
    raw: str | None = Field(default=None, repr=False)

    repository_id: int = Field(default=None, foreign_key="repository.id")
    repository: "Repository" = Relationship(
        back_populates="distributions", sa_relationship_kwargs={"lazy": "selectin"}
    )

    component_rows: list["Component"] = Relationship(back_populates="distribution")
    architecture_rows: list["Architecture"] = Relationship(back_populates="distribution")
    packages: list["Package"] = Relationship(
        back_populates="distributions", link_model=PackageDistributionLink
    )

    @computed_field
    @property
    def format_date(self) -> str | None:
        """Get the parsed date as a datetime object."""
        if self.date is None:
            return None
        try:
            update_time = parse_date(self.date)
            return update_time.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse date '{self.date}': {e}")
            return None

    @computed_field
    @property
    def format_components(self) -> list[str]:
        """Get the components sorted in a preferred order."""
        not_in_ordered = sorted([c for c in self.components if c not in ORDERED_COMPONENTS])

        def sort_fn(c):
            if c in ORDERED_COMPONENTS:
                return ORDERED_COMPONENTS.index(c)
            return N_ORDERED_COMPONENTS + not_in_ordered.index(c)

        return sorted(self.components, key=sort_fn)

    @computed_field
    @property
    def format_architectures(self) -> list[str]:
        """Get the architectures sorted in a preferred order."""

        not_in_ordered = sorted([c for c in self.architectures if c not in ORDERED_ARCHITECTURES])

        def sort_fn(c):
            if c in ORDERED_ARCHITECTURES:
                return ORDERED_ARCHITECTURES.index(c)
            return N_ORDERED_ARCHITECTURES + not_in_ordered.index(c)

        return sorted(self.architectures, key=sort_fn)


class Repository(rx.Model, table=True):
    """The apt repository model."""

    name: str = Field(index=True, unique=True)
    url: str = Field(index=True, unique=True)
    update_ts: datetime = Field(
        default=datetime.now(tz=UTC),
        sa_column=sm.Column(
            "update_ts",
            DateTime(timezone=True),
            server_default=sm.func.now(),
            onupdate=sm.func.now(),
            nullable=False,
        ),
    )

    distributions: list["Distribution"] = Relationship(back_populates="repository", cascade_delete=True)
    packages: list["Package"] = Relationship(back_populates="repository", cascade_delete=True)

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
