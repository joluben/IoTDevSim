"""
Add project_id to transmission_logs table

This migration adds project_id column to transmission_logs to ensure
project statistics persist even when devices are moved to other projects.

Revision ID: 000006_logs_project
Revises: 000005_projects_module
Create Date: 2026-02-12 11:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000006_logs_project'
down_revision = '000005_projects_module'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Check if a column exists in a table (PostgreSQL)."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [c['name'] for c in insp.get_columns(table)]
    return column in columns


def _index_exists(index_name):
    """Check if an index exists (PostgreSQL)."""
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    return result.fetchone() is not None


def upgrade() -> None:
    # Add project_id column to transmission_logs
    if not _column_exists('transmission_logs', 'project_id'):
        op.add_column('transmission_logs', sa.Column(
            'project_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('projects.id', ondelete='CASCADE'),
            nullable=True,  # Allow null initially for existing data
            index=True
        ))

    # Create index for project_id queries
    if not _index_exists('ix_transmission_log_project_id'):
        op.create_index('ix_transmission_log_project_id', 'transmission_logs', ['project_id'])

    # Note: A data migration should be run to populate project_id for existing logs
    # based on device.project_id at the time of transmission


def downgrade() -> None:
    # Drop index
    if _index_exists('ix_transmission_log_project_id'):
        op.drop_index('ix_transmission_log_project_id', table_name='transmission_logs')

    # Drop column
    if _column_exists('transmission_logs', 'project_id'):
        op.drop_column('transmission_logs', 'project_id')
