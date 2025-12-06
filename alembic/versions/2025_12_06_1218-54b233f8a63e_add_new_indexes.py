"""add new indexes

Revision ID: 54b233f8a63e
Revises: 4bb1ffbc00d3
Create Date: 2025-12-06 12:18:09.563251+00:00

"""

from typing import Sequence

from alembic import op

from aptreader.db import NAMING_CONVENTION

# revision identifiers, used by Alembic.
revision: str = "54b233f8a63e"
down_revision: str | Sequence[str] | None = "4bb1ffbc00d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("architecture", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(batch_op.f("uq_architecture_distribution_id"), type_="unique")
        batch_op.create_unique_constraint("uq_architecture_distribution_name", ["distribution_id", "name"])
        batch_op.drop_constraint(
            batch_op.f("fk_architecture_distribution_id_distribution"), type_="foreignkey"
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_architecture_distribution_id_distribution"),
            "distribution",
            ["distribution_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("component", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint(batch_op.f("uq_component_distribution_id"), type_="unique")
        batch_op.create_unique_constraint("uq_component_distribution_name", ["distribution_id", "name"])
        batch_op.drop_constraint(batch_op.f("fk_component_distribution_id_distribution"), type_="foreignkey")
        batch_op.create_foreign_key(
            batch_op.f("fk_component_distribution_id_distribution"),
            "distribution",
            ["distribution_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("distribution", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_unique_constraint(
            "uq_distribution_repository_codename", ["repository_id", "codename"]
        )
        batch_op.drop_constraint(batch_op.f("fk_distribution_repository_id_repository"), type_="foreignkey")
        batch_op.create_foreign_key(
            batch_op.f("fk_distribution_repository_id_repository"),
            "repository",
            ["repository_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("package", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_unique_constraint(
            "uq_package_repository_name_version", ["repository_id", "name", "version"]
        )
        batch_op.drop_constraint(batch_op.f("fk_package_repository_id_repository"), type_="foreignkey")
        batch_op.create_foreign_key(
            batch_op.f("fk_package_repository_id_repository"),
            "repository",
            ["repository_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table(
        "packagearchitecturelink", schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.create_index(
            "ix_pkg_arch_architecture_package", ["architecture_id", "package_id"], unique=False
        )

    with op.batch_alter_table(
        "packagecomponentlink", schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.create_index(
            "ix_pkg_component_component_package", ["component_id", "package_id"], unique=False
        )

    with op.batch_alter_table(
        "packagedistributionlink", schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.create_index(
            "ix_pkg_dist_distribution_package", ["distribution_id", "package_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "packagedistributionlink", schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_index("ix_pkg_dist_distribution_package")

    with op.batch_alter_table(
        "packagecomponentlink", schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_index("ix_pkg_component_component_package")

    with op.batch_alter_table(
        "packagearchitecturelink", schema=None, naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_index("ix_pkg_arch_architecture_package")

    with op.batch_alter_table("package", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_foreign_key(
            batch_op.f("fk_package_repository_id_repository"), "repository", ["repository_id"], ["id"]
        )
        batch_op.drop_constraint("uq_package_repository_name_version", type_="unique")

    with op.batch_alter_table("distribution", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_foreign_key(
            batch_op.f("fk_distribution_repository_id_repository"), "repository", ["repository_id"], ["id"]
        )
        batch_op.drop_constraint("uq_distribution_repository_codename", type_="unique")

    with op.batch_alter_table("component", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_foreign_key(
            batch_op.f("fk_component_distribution_id_distribution"),
            "distribution",
            ["distribution_id"],
            ["id"],
        )
        batch_op.drop_constraint("uq_component_distribution_name", type_="unique")
        batch_op.create_unique_constraint(
            batch_op.f("uq_component_distribution_id"), ["distribution_id", "name"]
        )

    with op.batch_alter_table("architecture", schema=None, naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.create_foreign_key(
            batch_op.f("fk_architecture_distribution_id_distribution"),
            "distribution",
            ["distribution_id"],
            ["id"],
        )
        batch_op.drop_constraint("uq_architecture_distribution_name", type_="unique")
        batch_op.create_unique_constraint(
            batch_op.f("uq_architecture_distribution_id"), ["distribution_id", "name"]
        )
