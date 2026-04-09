import logging
from typing import TYPE_CHECKING

import reflex as rx
from sqlmodel import Field, Index, SQLModel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@rx.ModelRegistry.register
class DistributionArchitectureLink(SQLModel, table=True):
    """Association table for many-to-many relationship between distributions and architectures."""

    __table_args__ = (Index("ix_dist_arch_distribution_architecture", "distribution_id", "architecture_id"),)

    distribution_id: int = Field(foreign_key="distribution.id", primary_key=True)
    architecture_id: int = Field(foreign_key="architecture.id", primary_key=True)

    # see https://sqlmodel.tiangolo.com/tutorial/many-to-many/link-with-extra-fields/
    # for some context on these commented out relationships
    # distribution: "Distribution" = Relationship(back_populates="architectures")
    # architecture: "Architecture" = Relationship(back_populates="distributions")


@rx.ModelRegistry.register
class DistributionComponentLink(SQLModel, table=True):
    """Association table for many-to-many relationship between distributions and components."""

    __table_args__ = (Index("ix_dist_comp_distribution_component", "distribution_id", "component_id"),)

    distribution_id: int = Field(foreign_key="distribution.id", primary_key=True)
    component_id: int = Field(foreign_key="component.id", primary_key=True)

    # distribution: "Distribution" = Relationship(back_populates="components")
    # component: "Component" = Relationship(back_populates="distributions")


@rx.ModelRegistry.register
class DistributionPackageLink(SQLModel, table=True):
    """Association table for many-to-many relationship between distributions and packages."""

    __table_args__ = (Index("ix_dist_pkg_distribution_package", "distribution_id", "package_id"),)

    distribution_id: int = Field(foreign_key="distribution.id", primary_key=True)
    package_id: int = Field(foreign_key="package.id", primary_key=True)

    # distribution: "Distribution" = Relationship(back_populates="packages")
    # package: "Package" = Relationship(back_populates="distributions")
