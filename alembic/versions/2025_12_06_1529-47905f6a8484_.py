"""empty message

Revision ID: 47905f6a8484
Revises: 19736cab8aa5
Create Date: 2025-12-06 15:29:48.681761+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47905f6a8484"
down_revision: str | Sequence[str] | None = "19736cab8aa5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("package", schema=None) as batch_op:
        batch_op.add_column(sa.Column("repository_id", sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            batch_op.f("fk_package_repository"), "repository", ["repository_id"], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("package", schema=None) as batch_op:
        batch_op.drop_column("repository_id")
