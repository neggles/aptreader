"""Models for distribution components, architectures, and packages."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import reflex as rx
from sqlalchemy import Index, UniqueConstraint
from sqlmodel import JSON, Column, DateTime, Field, Relationship

if TYPE_CHECKING:  # pragma: no cover
    from aptreader.models.repository import Distribution

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
    distribution: "Distribution" = Relationship(back_populates="component_rows")

    packages: list = Relationship(back_populates="component", link_model=PackageComponentLink)


class Architecture(rx.Model, table=True):
    """APT architecture (e.g., amd64) available for a distribution."""

    __table_args__ = (UniqueConstraint("distribution_id", "name"),)

    name: str = Field(index=True)
    last_fetched_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
    )

    distribution_id: int = Field(foreign_key="distribution.id")
    distribution: "Distribution" = Relationship(back_populates="architecture_rows")

    packages: list = Relationship(back_populates="architecture", link_model=PackageArchitectureLink)


class Package(rx.Model, table=True):
    """Stored metadata for a single package entry from Packages.gz."""

    __table_args__ = (
        UniqueConstraint("distribution_id", "component_id", "architecture_id", "name", "version"),
        Index("ix_package_component_arch", "component_id", "architecture_id"),
    )

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
    raw_control: dict | None = Field(sa_type=JSON, default=None)

    distribution_id: int = Field(foreign_key="distribution.id")
    component_id: int = Field(foreign_key="component.id")
    architecture_id: int = Field(foreign_key="architecture.id")

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
