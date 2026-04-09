import logging
from datetime import UTC, datetime

import reflex as rx
from dateutil.parser import parse as parse_date
from pydantic import AwareDatetime, ByteSize, computed_field, field_validator
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import Mapped
from sqlmodel import (
    BigInteger,
    Column,
    DateTime,
    Field,
    Index,
    Relationship,
    UniqueConstraint,
    func,
    select,
)

from aptreader.constants import UNIX_EPOCH_START
from aptreader.models.links import (
    DistributionArchitectureLink,
    DistributionComponentLink,
    DistributionPackageLink,
)
from aptreader.utils import stringify_size

logger = logging.getLogger(__name__)


class Distribution(rx.Model, table=True):
    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_distribution_repository_name"),)

    name: str = Field(index=True)
    date: AwareDatetime = Field(
        default=UNIX_EPOCH_START,
        sa_column=Column(pg.TIMESTAMP(timezone=True), index=True),
    )
    description: str | None = Field(None)
    origin: str | None = Field(None)
    suite: str | None = Field(None)
    version: str | None = Field(None)
    codename: str | None = Field(None)
    architecture_names: list[str] = Field(sa_type=pg.JSONB, default_factory=list)
    component_names: list[str] = Field(sa_type=pg.JSONB, default_factory=list)
    raw: str | None = Field(None, repr=False, schema_extra=dict(deferred=True))

    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE")
    repository: Mapped["Repository"] = Relationship(
        back_populates="distributions",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    components: Mapped[list["Component"]] = Relationship(
        back_populates="distributions",
        link_model=DistributionComponentLink,
        passive_deletes=True,
    )

    architectures: Mapped[list["Architecture"]] = Relationship(
        back_populates="distributions",
        link_model=DistributionArchitectureLink,
        passive_deletes=True,
    )

    packages: Mapped[list["Package"]] = Relationship(
        back_populates="distribution",
        link_model=DistributionPackageLink,
        passive_deletes=True,
    )

    last_fetched_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            "last_fetched_at",
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )

    @field_validator("architecture_names", "component_names", mode="after")
    def _sort_list(cls, v: list[str] | None) -> list[str]:
        if v is None:
            return []
        return sorted(v)

    @field_validator("date", mode="before")
    def _parse_date_field(cls, v: str | datetime | None) -> datetime:
        """Validate and parse the date field."""
        if isinstance(v, datetime):
            return v
        if v is None:
            return UNIX_EPOCH_START
        try:
            return parse_date(v).astimezone(UTC)
        except (ValueError, TypeError):
            logger.exception(f"Failed to parse date '{v}'")
            return UNIX_EPOCH_START

    @computed_field(repr=False)
    @property
    def format_date(self) -> str | None:
        """Get the parsed date as a pretty string."""
        return self.date.strftime("%Y-%m-%d %H:%M:%S %Z")

    @computed_field(repr=False)
    @property
    def format_last_fetched_at(self) -> str | None:
        """Get the parsed date as a pretty string."""
        if self.last_fetched_at is None:
            return None
        try:
            return self.last_fetched_at.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse date '{self.last_fetched_at}': {e}")
            return None

    @computed_field(repr=False)
    @property
    def package_count(self) -> int:
        """Get the number of packages for this distribution."""

        with rx.session() as session:
            stmt = (
                select(func.count())
                .select_from(Package)
                .where(Package.repository_id == self.repository_id, Package.distribution_id == self.id)
            )
            count = session.exec(stmt).one_or_none() or 0

            return count


class Component(rx.Model, table=True):
    """APT component (e.g., main, universe) tied to a distribution."""

    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_component_distribution_name"),)

    name: str = Field(index=True)
    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE")
    repository: "Repository" = Relationship(
        back_populates="components",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    distributions: list["Distribution"] = Relationship(
        back_populates="components",
        link_model=DistributionComponentLink,
    )


class Architecture(rx.Model, table=True):
    """APT architecture (e.g., amd64) available for a distribution."""

    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_architecture_distribution_name"),)

    name: str = Field(index=True)
    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE")
    repository: "Repository" = Relationship(
        back_populates="architectures",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    distributions: list["Distribution"] = Relationship(
        back_populates="architectures",
        link_model=DistributionArchitectureLink,
    )


class Package(rx.Model, table=True):
    """Stored metadata for a single package entry from Packages.gz."""

    __table_args__ = (
        UniqueConstraint(
            "distribution_id",
            "component_id",
            "architecture_id",
            "name",
            "version",
            name="uq_package_distribution_component_architecture_name_version",
        ),
        Index(
            "ix_package_name_version",
            "name",
            "version",
        ),
    )

    name: str = Field(index=True)
    version: str = Field()
    section: str | None = Field(None)
    priority: str | None = Field(None)
    size: ByteSize | None = Field(None, sa_type=BigInteger)
    installed_size: ByteSize | None = Field(None, sa_type=BigInteger)
    filename: str | None = Field(None)
    source: str | None = Field(None)
    maintainer: str | None = Field(None)
    homepage: str | None = Field(None)
    description: str | None = Field(None)
    description_md5: str | None = Field(None)
    checksum_md5: str | None = Field(None)
    checksum_sha1: str | None = Field(None)
    checksum_sha256: str | None = Field(None)
    tags: str | None = Field(None)
    raw_control: dict | None = Field(None, sa_type=pg.JSONB, repr=False)

    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE")
    repository: Mapped["Repository"] = Relationship(
        back_populates="packages",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    distribution_id: int = Field(foreign_key="distribution.id", ondelete="CASCADE")
    distribution: Mapped["Distribution"] = Relationship(
        back_populates="packages",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    component_id: int = Field(foreign_key="component.id", ondelete="CASCADE")
    component: Mapped["Component"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    architecture_id: int = Field(foreign_key="architecture.id", ondelete="CASCADE")
    architecture: Mapped["Architecture"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    last_fetched_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(
            "last_fetched_at",
            pg.TIMESTAMP(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )

    @computed_field
    @property
    def size_str(self) -> str:
        """Package size formatted as a human-readable string."""
        if self.size is None:
            return "-"
        return stringify_size(self.size)

    @computed_field
    @property
    def installed_size_str(self) -> str:
        """Package size formatted as a human-readable string."""
        if self.installed_size is None:
            return "-"
        return stringify_size(self.installed_size)


class Repository(rx.Model, table=True):
    """The apt repository model."""

    name: str = Field(index=True, unique=True)
    url: str = Field(index=True, unique=True)

    distributions: list["Distribution"] = Relationship(
        back_populates="repository",
    )
    components: list["Component"] = Relationship(
        back_populates="repository",
    )
    architectures: list["Architecture"] = Relationship(
        back_populates="repository",
    )
    packages: list["Package"] = Relationship(
        back_populates="repository",
    )

    last_fetched_at: AwareDatetime | None = Field(
        default=None,
        sa_column=Column(
            "last_fetched_at",
            pg.TIMESTAMP(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )

    @computed_field
    @property
    def distribution_count(self) -> int:
        """Get the number of distributions for this repository."""
        with rx.session() as session:
            stmt = select(func.count()).select_from(Package).where(Package.repository_id == self.id)
            count = session.exec(stmt).one_or_none() or 0
            return count

    @computed_field
    @property
    def package_count(self) -> int:
        """Get the number of packages for this repository."""
        with rx.session() as session:
            stmt = select(func.count()).select_from(Distribution).where(Distribution.repository_id == self.id)
            count = session.exec(stmt).one_or_none() or 0
            return count
