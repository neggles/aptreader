"""empty message

Revision ID: 462a2aff3e48
Revises: 246db1c6dac7
Create Date: 2025-12-05 16:48:00.922472+00:00

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "462a2aff3e48"
down_revision: str | Sequence[str] | None = "246db1c6dac7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("package", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_package_component_arch"))
        batch_op.drop_constraint(batch_op.f("uq_package_distribution_id"), type_="unique")
        batch_op.create_unique_constraint("uq_name_version", ["name", "version"])
        batch_op.drop_constraint(batch_op.f("fk_package_architecture_id_architecture"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_package_distribution_id_distribution"), type_="foreignkey")
        batch_op.drop_constraint(batch_op.f("fk_package_component_id_component"), type_="foreignkey")
        batch_op.drop_column("component_id")
        batch_op.drop_column("distribution_id")
        batch_op.drop_column("architecture_id")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("package", schema=None) as batch_op:
        batch_op.add_column(sa.Column("architecture_id", sa.INTEGER(), nullable=False))
        batch_op.add_column(sa.Column("distribution_id", sa.INTEGER(), nullable=False))
        batch_op.add_column(sa.Column("component_id", sa.INTEGER(), nullable=False))
        batch_op.create_foreign_key(
            batch_op.f("fk_package_component_id_component"), "component", ["component_id"], ["id"]
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_package_distribution_id_distribution"), "distribution", ["distribution_id"], ["id"]
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_package_architecture_id_architecture"), "architecture", ["architecture_id"], ["id"]
        )
        batch_op.drop_constraint("uq_name_version", type_="unique")
        batch_op.create_unique_constraint(
            batch_op.f("uq_package_distribution_id"),
            ["distribution_id", "component_id", "architecture_id", "name", "version"],
        )
        batch_op.create_index(
            batch_op.f("ix_package_component_arch"), ["component_id", "architecture_id"], unique=False
        )
