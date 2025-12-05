"""manymany

Revision ID: 246db1c6dac7
Revises: ab662e724d7d
Create Date: 2025-12-05 15:23:48.717275+00:00

"""

from typing import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "246db1c6dac7"
down_revision: str | Sequence[str] | None = "ab662e724d7d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "architecture",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.AutoString(), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distribution_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["distribution_id"], ["distribution.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("distribution_id", "name"),
    )
    with op.batch_alter_table("architecture") as batch_op:
        batch_op.create_index(batch_op.f("ix_architecture_name"), ["name"], unique=False)

    op.create_table(
        "component",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.AutoString(), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distribution_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["distribution_id"], ["distribution.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("distribution_id", "name"),
    )
    with op.batch_alter_table("component") as batch_op:
        batch_op.create_index(batch_op.f("ix_component_name"), ["name"], unique=False)

    op.create_table(
        "package",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.AutoString(), nullable=False),
        sa.Column("version", sqlmodel.AutoString(), nullable=False),
        sa.Column("section", sqlmodel.AutoString(), nullable=True),
        sa.Column("priority", sqlmodel.AutoString(), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("installed_size", sa.Integer(), nullable=True),
        sa.Column("filename", sqlmodel.AutoString(), nullable=True),
        sa.Column("source", sqlmodel.AutoString(), nullable=True),
        sa.Column("maintainer", sqlmodel.AutoString(), nullable=True),
        sa.Column("homepage", sqlmodel.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.AutoString(), nullable=True),
        sa.Column("description_md5", sqlmodel.AutoString(), nullable=True),
        sa.Column("checksum_md5", sqlmodel.AutoString(), nullable=True),
        sa.Column("checksum_sha1", sqlmodel.AutoString(), nullable=True),
        sa.Column("checksum_sha256", sqlmodel.AutoString(), nullable=True),
        sa.Column("tags", sqlmodel.AutoString(), nullable=True),
        sa.Column("raw_control", sa.JSON(), nullable=True),
        sa.Column("distribution_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("architecture_id", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["architecture_id"], ["architecture.id"]),
        sa.ForeignKeyConstraint(["component_id"], ["component.id"]),
        sa.ForeignKeyConstraint(["distribution_id"], ["distribution.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("distribution_id", "component_id", "architecture_id", "name", "version"),
    )
    with op.batch_alter_table("package") as batch_op:
        batch_op.create_index("ix_package_component_arch", ["component_id", "architecture_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_package_name"), ["name"], unique=False)
        batch_op.create_index(batch_op.f("ix_package_version"), ["version"], unique=False)

    op.create_table(
        "packagearchitecturelink",
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("architecture_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["architecture_id"], ["architecture.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["package.id"]),
        sa.PrimaryKeyConstraint("package_id", "architecture_id"),
    )
    op.create_table(
        "packagecomponentlink",
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["component.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["package.id"]),
        sa.PrimaryKeyConstraint("package_id", "component_id"),
    )
    op.create_table(
        "packagedistributionlink",
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("distribution_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["distribution_id"], ["distribution.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["package.id"]),
        sa.PrimaryKeyConstraint("package_id", "distribution_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("packagedistributionlink")
    op.drop_table("packagecomponentlink")
    op.drop_table("packagearchitecturelink")
    with op.batch_alter_table("package") as batch_op:
        batch_op.drop_index(batch_op.f("ix_package_version"))
        batch_op.drop_index(batch_op.f("ix_package_name"))
        batch_op.drop_index("ix_package_component_arch")

    op.drop_table("package")
    with op.batch_alter_table("component") as batch_op:
        batch_op.drop_index(batch_op.f("ix_component_name"))

    op.drop_table("component")
    with op.batch_alter_table("architecture") as batch_op:
        batch_op.drop_index(batch_op.f("ix_architecture_name"))

    op.drop_table("architecture")
