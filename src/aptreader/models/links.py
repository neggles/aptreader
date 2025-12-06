import logging

import reflex as rx
from sqlmodel import Field, SQLModel

logger = logging.getLogger(__name__)


@rx.ModelRegistry.register
class PackageDistributionLink(SQLModel, table=True):
    """Association table for many-to-many relationship between packages and distributions."""

    package_id: int = Field(foreign_key="package.id", primary_key=True)
    distribution_id: int = Field(foreign_key="distribution.id", primary_key=True)


@rx.ModelRegistry.register
class PackageComponentLink(SQLModel, table=True):
    """Association table for many-to-many relationship between packages and components."""

    package_id: int = Field(foreign_key="package.id", primary_key=True)
    component_id: int = Field(foreign_key="component.id", primary_key=True)


@rx.ModelRegistry.register
class PackageArchitectureLink(SQLModel, table=True):
    """Association table for many-to-many relationship between packages and architectures."""

    package_id: int = Field(foreign_key="package.id", primary_key=True)
    architecture_id: int = Field(foreign_key="architecture.id", primary_key=True)
