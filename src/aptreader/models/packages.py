"""Models for distribution components, architectures, and packages."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import reflex as rx
from sqlalchemy import UniqueConstraint
from sqlmodel import JSON, Column, DateTime, Field, Relationship

if TYPE_CHECKING:
    from aptreader.models.repository import Distribution, Repository
from .links import PackageArchitectureLink, PackageComponentLink, PackageDistributionLink


class Component(rx.Model, table=True):
    """APT component (e.g., main, universe) tied to a distribution."""

    __table_args__ = (UniqueConstraint("distribution_id", "name"),)

    name: str = Field(index=True)
    last_fetched_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

    distribution_id: int = Field(foreign_key="distribution.id")
    distribution: "Distribution" = Relationship(
        back_populates="component_rows", sa_relationship_kwargs={"lazy": "selectin"}
    )

    packages: list["Package"] = Relationship(
        back_populates="components",
        link_model=PackageComponentLink,
    )


class Architecture(rx.Model, table=True):
    """APT architecture (e.g., amd64) available for a distribution."""

    __table_args__ = (UniqueConstraint("distribution_id", "name"),)

    name: str = Field(index=True)
    last_fetched_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

    distribution_id: int = Field(foreign_key="distribution.id")
    distribution: "Distribution" = Relationship(
        back_populates="architecture_rows", sa_relationship_kwargs={"lazy": "selectin"}
    )

    packages: list["Package"] = Relationship(
        back_populates="architectures",
        link_model=PackageArchitectureLink,
    )


class Package(rx.Model, table=True):
    """Stored metadata for a single package entry from Packages.gz."""

    name: str = Field(index=True)
    version: str = Field(index=True)
    section: str | None = None
    priority: str | None = None
    size: int | None = None
    installed_size: int | None = None
    filename: str | None = None
    source: str | None = None
    maintainer: str | None = None
    homepage: str | None = None
    description: str | None = None
    description_md5: str | None = None
    checksum_md5: str | None = None
    checksum_sha1: str | None = None
    checksum_sha256: str | None = None
    tags: str | None = None
    raw_control: dict | None = Field(
        sa_type=JSON,
        default=None,
    )

    repository_id: int = Field(default=None, foreign_key="repository.id")
    repository: "Repository" = Relationship(
        back_populates="packages",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    distributions: list["Distribution"] = Relationship(
        back_populates="packages",
        link_model=PackageDistributionLink,
    )
    components: list["Component"] = Relationship(
        back_populates="packages",
        link_model=PackageComponentLink,
    )
    architectures: list["Architecture"] = Relationship(
        back_populates="packages",
        link_model=PackageArchitectureLink,
    )

    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
