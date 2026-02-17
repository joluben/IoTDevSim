"""
Make project_id nullable in transmission_logs

This migration ensures project_id column is nullable to allow
direct device transmission without project assignment.

Revision ID: 000007_logs_project_nullable
Revises: 000006_logs_project
Create Date: 2026-02-17 11:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000007_logs_project_nullable'
down_revision = '000006_logs_project'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Check if a column exists in a table (PostgreSQL)."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [c['name'] for c in insp.get_columns(table)]
    return column in columns


def upgrade() -> None:
    # Make project_id nullable
    if _column_exists('transmission_logs', 'project_id'):
        op.alter_column('transmission_logs', 'project_id',
                        existing_type=postgresql.UUID(as_uuid=True),
                        nullable=True)


def downgrade() -> None:
    # Revert to non-nullable (may fail if nulls exist)
    if _column_exists('transmission_logs', 'project_id'):
        op.alter_column('transmission_logs', 'project_id',
                        existing_type=postgresql.UUID(as_uuid=True),
                        nullable=False)
