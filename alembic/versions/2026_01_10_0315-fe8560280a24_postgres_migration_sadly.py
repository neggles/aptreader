"""postgres migration, sadly

Revision ID: fe8560280a24
Revises:
Create Date: 2026-01-10 03:15:18.908712+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fe8560280a24"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "repository",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "last_fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_repository_name"), "repository", ["name"], unique=True)
    op.create_index(op.f("ix_repository_url"), "repository", ["url"], unique=True)
    op.create_table(
        "architecture",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repository.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "name", name="uq_architecture_distribution_name"),
    )
    op.create_index(op.f("ix_architecture_name"), "architecture", ["name"], unique=False)
    op.create_table(
        "component",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repository.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "name", name="uq_component_distribution_name"),
    )
    op.create_index(op.f("ix_component_name"), "component", ["name"], unique=False)
    op.create_table(
        "distribution",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("date", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("origin", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("suite", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("version", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("codename", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("architecture_names", sa.JSON(), nullable=False),
        sa.Column("component_names", sa.JSON(), nullable=False),
        sa.Column("raw", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column(
            "last_fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["repository_id"], ["repository.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "name", name="uq_distribution_repository_name"),
    )
    op.create_index(op.f("ix_distribution_name"), "distribution", ["name"], unique=False)
    op.create_table(
        "distributionarchitecturelink",
        sa.Column("distribution_id", sa.Integer(), nullable=False),
        sa.Column("architecture_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["architecture_id"], ["architecture.id"]),
        sa.ForeignKeyConstraint(["distribution_id"], ["distribution.id"]),
        sa.PrimaryKeyConstraint("distribution_id", "architecture_id"),
    )
    op.create_index(
        "ix_dist_arch_distribution_architecture",
        "distributionarchitecturelink",
        ["distribution_id", "architecture_id"],
        unique=False,
    )
    op.create_table(
        "distributioncomponentlink",
        sa.Column("distribution_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["component.id"]),
        sa.ForeignKeyConstraint(["distribution_id"], ["distribution.id"]),
        sa.PrimaryKeyConstraint("distribution_id", "component_id"),
    )
    op.create_index(
        "ix_dist_comp_distribution_component",
        "distributioncomponentlink",
        ["distribution_id", "component_id"],
        unique=False,
    )
    op.create_table(
        "package",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("version", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("section", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("priority", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("installed_size", sa.BigInteger(), nullable=True),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("maintainer", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("homepage", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description_md5", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("checksum_md5", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("checksum_sha1", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("checksum_sha256", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("raw_control", sa.JSON(), nullable=True),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("distribution_id", sa.Integer(), nullable=False),
        sa.Column("component_id", sa.Integer(), nullable=False),
        sa.Column("architecture_id", sa.Integer(), nullable=False),
        sa.Column(
            "last_fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["architecture_id"], ["architecture.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["component_id"], ["component.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["distribution_id"], ["distribution.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repository.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "distribution_id",
            "component_id",
            "architecture_id",
            "name",
            "version",
            name="uq_package_distribution_component_architecture_name_version",
        ),
    )
    op.create_index(op.f("ix_package_name"), "package", ["name"], unique=False)
    op.create_index(op.f("ix_package_version"), "package", ["version"], unique=False)
    op.create_table(
        "distributionpackagelink",
        sa.Column("distribution_id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["distribution_id"], ["distribution.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["package.id"]),
        sa.PrimaryKeyConstraint("distribution_id", "package_id"),
    )
    op.create_index(
        "ix_dist_pkg_distribution_package",
        "distributionpackagelink",
        ["distribution_id", "package_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_dist_pkg_distribution_package", table_name="distributionpackagelink")
    op.drop_table("distributionpackagelink")
    op.drop_index(op.f("ix_package_version"), table_name="package")
    op.drop_index(op.f("ix_package_name"), table_name="package")
    op.drop_table("package")
    op.drop_index("ix_dist_comp_distribution_component", table_name="distributioncomponentlink")
    op.drop_table("distributioncomponentlink")
    op.drop_index("ix_dist_arch_distribution_architecture", table_name="distributionarchitecturelink")
    op.drop_table("distributionarchitecturelink")
    op.drop_index(op.f("ix_distribution_name"), table_name="distribution")
    op.drop_table("distribution")
    op.drop_index(op.f("ix_component_name"), table_name="component")
    op.drop_table("component")
    op.drop_index(op.f("ix_architecture_name"), table_name="architecture")
    op.drop_table("architecture")
    op.drop_index(op.f("ix_repository_url"), table_name="repository")
    op.drop_index(op.f("ix_repository_name"), table_name="repository")
    op.drop_table("repository")
