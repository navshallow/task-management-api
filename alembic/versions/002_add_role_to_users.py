"""Add role column to users

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add role column with default 'user'."""
    op.add_column(
        "users",
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
    )
    # Remove server_default after existing rows are populated
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    """Drop role column."""
    op.drop_column("users", "role")
