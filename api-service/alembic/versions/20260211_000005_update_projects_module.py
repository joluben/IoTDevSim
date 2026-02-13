"""
Update projects table for Projects module

- Make owner_id nullable
- Remove is_public, max_connections columns
- Add transmission_status, tags, auto_reset_counter, is_archived, archived_at
- Add connection_id FK to connections
- Add device_count denormalized counter
- Add indexes for search and filtering

Revision ID: 000005_projects_module
Revises: 000004_devices_module
Create Date: 2026-02-11 18:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000005_projects_module'
down_revision = '000004_devices_module'
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
    # ── Remove columns not needed ──
    if _column_exists('projects', 'is_public'):
        op.drop_column('projects', 'is_public')

    if _column_exists('projects', 'max_connections'):
        op.drop_column('projects', 'max_connections')

    # ── Make owner_id nullable ──
    if _column_exists('projects', 'owner_id'):
        op.alter_column(
            'projects', 'owner_id',
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=True
        )

    # ── Add new columns ──
    if not _column_exists('projects', 'transmission_status'):
        op.add_column('projects', sa.Column(
            'transmission_status',
            sa.String(20),
            nullable=False,
            server_default='inactive'
        ))

    if not _column_exists('projects', 'tags'):
        op.add_column('projects', sa.Column(
            'tags',
            postgresql.JSONB,
            nullable=False,
            server_default='[]'
        ))

    if not _column_exists('projects', 'auto_reset_counter'):
        op.add_column('projects', sa.Column(
            'auto_reset_counter',
            sa.Boolean(),
            nullable=False,
            server_default='false'
        ))

    if not _column_exists('projects', 'is_archived'):
        op.add_column('projects', sa.Column(
            'is_archived',
            sa.Boolean(),
            nullable=False,
            server_default='false'
        ))

    if not _column_exists('projects', 'archived_at'):
        op.add_column('projects', sa.Column(
            'archived_at',
            sa.DateTime(timezone=True),
            nullable=True
        ))

    if not _column_exists('projects', 'connection_id'):
        op.add_column('projects', sa.Column(
            'connection_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('connections.id', ondelete='SET NULL'),
            nullable=True
        ))

    if not _column_exists('projects', 'device_count'):
        op.add_column('projects', sa.Column(
            'device_count',
            sa.Integer(),
            nullable=False,
            server_default='0'
        ))

    # ── Add indexes ──
    if not _index_exists('ix_project_transmission_status'):
        op.create_index('ix_project_transmission_status', 'projects', ['transmission_status'])

    if not _index_exists('ix_project_is_archived'):
        op.create_index('ix_project_is_archived', 'projects', ['is_archived'])

    if not _index_exists('ix_project_connection'):
        op.create_index('ix_project_connection', 'projects', ['connection_id'])


def downgrade() -> None:
    # Drop new indexes
    for idx in ['ix_project_connection', 'ix_project_is_archived', 'ix_project_transmission_status']:
        if _index_exists(idx):
            op.drop_index(idx, table_name='projects')

    # Drop new columns
    for col in ['device_count', 'connection_id', 'archived_at', 'is_archived',
                'auto_reset_counter', 'tags', 'transmission_status']:
        if _column_exists('projects', col):
            op.drop_column('projects', col)

    # Restore owner_id as non-nullable
    if _column_exists('projects', 'owner_id'):
        op.alter_column(
            'projects', 'owner_id',
            existing_type=postgresql.UUID(as_uuid=True),
            nullable=False
        )

    # Restore removed columns
    if not _column_exists('projects', 'is_public'):
        op.add_column('projects', sa.Column(
            'is_public', sa.Boolean(), nullable=False, server_default='false'
        ))

    if not _column_exists('projects', 'max_connections'):
        op.add_column('projects', sa.Column(
            'max_connections', sa.Integer(), nullable=False, server_default='100'
        ))
