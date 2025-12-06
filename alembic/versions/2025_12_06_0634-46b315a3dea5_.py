"""empty message

Revision ID: 46b315a3dea5
Revises: 462a2aff3e48
Create Date: 2025-12-06 06:34:45.312501+00:00

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "46b315a3dea5"
down_revision: str | Sequence[str] | None = "462a2aff3e48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("package") as batch_op:
        batch_op.add_column(sa.Column("repository_id", sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            "fk_package_repository_id_repository", "repository", ["repository_id"], ["id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("package") as batch_op:
        batch_op.drop_column("repository_id")
