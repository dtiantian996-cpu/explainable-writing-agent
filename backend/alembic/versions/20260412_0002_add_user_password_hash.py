"""add user password hash

Revision ID: 20260412_0002
Revises: 20260409_0001
Create Date: 2026-04-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260412_0002"
down_revision: str | None = "20260409_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)


def downgrade() -> None:
    op.drop_column("users", "password_hash")
