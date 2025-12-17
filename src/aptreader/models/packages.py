"""Models for distribution components, architectures, and packages."""

from datetime import datetime
from typing import TYPE_CHECKING

import reflex as rx
import sqlmodel as sm
from pydantic import ByteSize, computed_field
from sqlmodel import JSON, BigInteger, Field, Relationship, UniqueConstraint

from aptreader.models.links import DistributionArchitectureLink, DistributionComponentLink

if TYPE_CHECKING:
    from aptreader.models.repository import Distribution, Repository


class Component(rx.Model, table=True):
    """APT component (e.g., main, universe) tied to a distribution."""

    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_component_distribution_name"),)

    name: str = Field(index=True, unique=True)
    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE")
    repository: "Repository" = Relationship(
        back_populates="components",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    distributions: list["Distribution"] = Relationship(
        back_populates="components",
        link_model=DistributionComponentLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Architecture(rx.Model, table=True):
    """APT architecture (e.g., amd64) available for a distribution."""

    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_architecture_distribution_name"),)

    name: str = Field(index=True, unique=True)
    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE")
    repository: "Repository" = Relationship(
        back_populates="architectures",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    distributions: list["Distribution"] = Relationship(
        back_populates="architectures",
        link_model=DistributionArchitectureLink,
        sa_relationship_kwargs={"lazy": "selectin"},
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
    )

    name: str = Field(index=True)
    version: str = Field(index=True)
    section: str | None = None
    priority: str | None = None
    size: ByteSize | None = Field(default=None, sa_type=BigInteger)
    installed_size: ByteSize | None = Field(default=None, sa_type=BigInteger)
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
    raw_control: dict | None = Field(default=None, sa_type=JSON, repr=False)

    repository_id: int = Field(foreign_key="repository.id", ondelete="CASCADE")
    repository: "Repository" = Relationship(
        back_populates="packages",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    distribution_id: int = Field(foreign_key="distribution.id", ondelete="CASCADE")
    distribution: "Distribution" = Relationship(
        back_populates="packages",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    component_id: int = Field(foreign_key="component.id", ondelete="CASCADE")
    component: "Component" = Relationship(sa_relationship_kwargs={"lazy": "selectin"})
    architecture_id: int = Field(foreign_key="architecture.id", ondelete="CASCADE")
    architecture: "Architecture" = Relationship(sa_relationship_kwargs={"lazy": "selectin"})

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
    def size_str(self) -> str:
        """Package size formatted as a human-readable string."""
        if self.size is None:
            return "-"
        return self.size.human_readable()

    @computed_field
    @property
    def installed_size_str(self) -> str:
        """Package size formatted as a human-readable string."""
        if self.installed_size is None:
            return "-"
        return self.installed_size.human_readable()
