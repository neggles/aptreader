"""jsonB

Revision ID: e08b369edf30
Revises: 1f750c462c84
Create Date: 2026-01-15 14:25:12.836033+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e08b369edf30"
down_revision: str | Sequence[str] | None = "1f750c462c84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "distribution",
        "architecture_names",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=False,
        postgresql_using="architecture_names::jsonb",
    )
    op.alter_column(
        "distribution",
        "component_names",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=False,
        postgresql_using="component_names::jsonb",
    )
    op.alter_column(
        "package",
        "raw_control",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
        postgresql_using="raw_control::jsonb",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "package",
        "raw_control",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=True,
        postgresql_using="raw_control::json",
    )
    op.alter_column(
        "distribution",
        "component_names",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=False,
        postgresql_using="component_names::json",
    )
    op.alter_column(
        "distribution",
        "architecture_names",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=False,
        postgresql_using="architecture_names::json",
    )
