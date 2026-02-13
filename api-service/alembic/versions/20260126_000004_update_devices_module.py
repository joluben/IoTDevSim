"""
Update devices table for new Devices module

- Change device_type from ENUM to String(20) (sensor/datalogger only)
- Change status from ENUM to String(20) (idle/transmitting/error/paused)
- Make project_id nullable
- Add transmission fields (transmission_enabled, transmission_frequency, transmission_config, current_row_index, last_transmission_at)
- Add tags JSONB field
- Remove simulation_enabled, simulation_config, configuration columns
- Update device_id to String(8) with unique constraint
- Replace old indexes with new ones
- Create device_datasets association table if not exists
- Add is_encrypted column to datasets

Revision ID: 000004_devices_module
Revises: 000003_datasets
Create Date: 2026-01-26 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000004_devices_module'
down_revision = '000003_datasets'
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


def _table_exists(table_name):
    """Check if a table exists."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    # ==================== Drop old indexes (if they exist) ====================
    for idx in ['ix_device_project_type', 'ix_device_project_status',
                'ix_device_project_active', 'ix_device_unique_id_project']:
        if _index_exists(idx):
            op.drop_index(idx, table_name='devices')

    # ==================== Change device_type from ENUM to String ====================
    op.add_column('devices', sa.Column('device_type_new', sa.String(20), nullable=True))
    op.execute("""
        UPDATE devices SET device_type_new = CASE
            WHEN device_type::text = 'sensor' THEN 'sensor'
            WHEN device_type::text = 'actuator' THEN 'sensor'
            WHEN device_type::text = 'gateway' THEN 'datalogger'
            WHEN device_type::text = 'controller' THEN 'sensor'
            WHEN device_type::text = 'hybrid' THEN 'datalogger'
            ELSE 'sensor'
        END
    """)
    op.alter_column('devices', 'device_type_new', nullable=False)
    op.drop_column('devices', 'device_type')
    op.alter_column('devices', 'device_type_new', new_column_name='device_type')

    # ==================== Change status from ENUM to String ====================
    op.add_column('devices', sa.Column('status_new', sa.String(20), nullable=True))
    op.execute("""
        UPDATE devices SET status_new = CASE
            WHEN status::text = 'online' THEN 'idle'
            WHEN status::text = 'offline' THEN 'idle'
            WHEN status::text = 'error' THEN 'error'
            WHEN status::text = 'maintenance' THEN 'paused'
            WHEN status::text = 'unknown' THEN 'idle'
            ELSE 'idle'
        END
    """)
    op.alter_column('devices', 'status_new', nullable=False, server_default='idle')
    op.drop_column('devices', 'status')
    op.alter_column('devices', 'status_new', new_column_name='status')

    # ==================== Make project_id nullable ====================
    op.alter_column('devices', 'project_id', nullable=True)

    # ==================== Change device_id to String(8) with unique ====================
    op.alter_column('devices', 'device_id', type_=sa.String(8))
    op.create_unique_constraint('uq_devices_device_id', 'devices', ['device_id'])

    # ==================== Add new columns (only if they don't exist) ====================
    if not _column_exists('devices', 'tags'):
        op.add_column('devices', sa.Column(
            'tags', postgresql.JSONB(astext_type=sa.Text()),
            nullable=False, server_default=sa.text("'[]'::jsonb")
        ))
    if not _column_exists('devices', 'transmission_enabled'):
        op.add_column('devices', sa.Column(
            'transmission_enabled', sa.Boolean(),
            nullable=False, server_default=sa.text('false')
        ))
    if not _column_exists('devices', 'transmission_frequency'):
        op.add_column('devices', sa.Column(
            'transmission_frequency', sa.Integer(), nullable=True
        ))
    if not _column_exists('devices', 'transmission_config'):
        op.add_column('devices', sa.Column(
            'transmission_config', postgresql.JSONB(astext_type=sa.Text()),
            nullable=False, server_default=sa.text("'{}'::jsonb")
        ))
    if not _column_exists('devices', 'current_row_index'):
        op.add_column('devices', sa.Column(
            'current_row_index', sa.Integer(),
            nullable=False, server_default='0'
        ))
    if not _column_exists('devices', 'last_transmission_at'):
        op.add_column('devices', sa.Column(
            'last_transmission_at', sa.DateTime(timezone=True), nullable=True
        ))

    if not _column_exists('devices', 'connection_id'):
        op.add_column('devices', sa.Column(
            'connection_id', postgresql.UUID(as_uuid=True), nullable=True
        ))
        op.create_foreign_key(
            'fk_devices_connection_id', 'devices', 'connections',
            ['connection_id'], ['id']
        )

    # ==================== Remove old columns (if they exist) ====================
    if _column_exists('devices', 'simulation_enabled'):
        op.drop_column('devices', 'simulation_enabled')
    if _column_exists('devices', 'simulation_config'):
        op.drop_column('devices', 'simulation_config')
    if _column_exists('devices', 'configuration'):
        op.drop_column('devices', 'configuration')

    # ==================== Convert json columns to jsonb ====================
    op.alter_column('devices', 'capabilities',
                    type_=postgresql.JSONB(astext_type=sa.Text()),
                    postgresql_using='capabilities::jsonb',
                    server_default=sa.text("'[]'::jsonb"))
    op.alter_column('devices', 'device_metadata',
                    type_=postgresql.JSONB(astext_type=sa.Text()),
                    postgresql_using='device_metadata::jsonb',
                    server_default=sa.text("'{}'::jsonb"))

    # ==================== Create new indexes ====================
    if not _index_exists('ix_device_type_active'):
        op.create_index('ix_device_type_active', 'devices', ['device_type', 'is_active'])
    if not _index_exists('ix_device_transmission'):
        op.create_index('ix_device_transmission', 'devices', ['transmission_enabled', 'is_active'])
    if not _index_exists('ix_device_project'):
        op.create_index('ix_device_project', 'devices', ['project_id'])
    if not _index_exists('ix_device_connection'):
        op.create_index('ix_device_connection', 'devices', ['connection_id'])
    if not _index_exists('ix_device_status'):
        op.create_index('ix_device_status', 'devices', ['status'])
    if not _index_exists('ix_device_device_id'):
        op.create_index('ix_device_device_id', 'devices', ['device_id'])

    # ==================== Create device_datasets table ====================
    if not _table_exists('device_datasets'):
        op.create_table(
            'device_datasets',
            sa.Column('device_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('devices.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('dataset_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('datasets.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('linked_at', sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column('config', postgresql.JSONB(astext_type=sa.Text()),
                      nullable=False, server_default=sa.text("'{}'::jsonb")),
        )

    # ==================== Add is_encrypted to datasets if missing ====================
    if not _column_exists('datasets', 'is_encrypted'):
        op.add_column('datasets', sa.Column(
            'is_encrypted', sa.Boolean(), nullable=False, server_default=sa.text('false')
        ))

    # ==================== Rename datasets.metadata -> custom_metadata if needed ====================
    if _column_exists('datasets', 'metadata') and not _column_exists('datasets', 'custom_metadata'):
        op.alter_column('datasets', 'metadata', new_column_name='custom_metadata')


def downgrade() -> None:
    # Reverse custom_metadata rename
    op.alter_column('datasets', 'custom_metadata', new_column_name='metadata')

    # Drop is_encrypted from datasets
    op.drop_column('datasets', 'is_encrypted')

    # Drop device_datasets table
    op.drop_table('device_datasets')

    # Drop new indexes
    op.drop_index('ix_device_device_id', table_name='devices')
    op.drop_index('ix_device_status', table_name='devices')
    op.drop_index('ix_device_connection', table_name='devices')
    op.drop_index('ix_device_project', table_name='devices')
    op.drop_index('ix_device_transmission', table_name='devices')
    op.drop_index('ix_device_type_active', table_name='devices')

    # Rename device_metadata back to metadata
    op.alter_column('devices', 'device_metadata', new_column_name='metadata')

    # Remove new columns
    op.drop_column('devices', 'connection_id')
    op.drop_column('devices', 'last_transmission_at')
    op.drop_column('devices', 'current_row_index')
    op.drop_column('devices', 'transmission_config')
    op.drop_column('devices', 'transmission_frequency')
    op.drop_column('devices', 'transmission_enabled')
    op.drop_column('devices', 'tags')

    # Restore device_id to String(64)
    op.drop_constraint('uq_devices_device_id', 'devices', type_='unique')
    op.alter_column('devices', 'device_id', type_=sa.String(64))

    # Make project_id non-nullable again
    op.alter_column('devices', 'project_id', nullable=False)

    # Add back old columns
    op.add_column('devices', sa.Column(
        'configuration', postgresql.JSONB(astext_type=sa.Text()),
        nullable=False, server_default=sa.text("'{}'::jsonb")
    ))
    op.add_column('devices', sa.Column(
        'simulation_config', postgresql.JSONB(astext_type=sa.Text()),
        nullable=False, server_default=sa.text("'{}'::jsonb")
    ))
    op.add_column('devices', sa.Column(
        'simulation_enabled', sa.Boolean(),
        nullable=False, server_default=sa.text('false')
    ))

    # Restore status to ENUM
    device_status = postgresql.ENUM('online', 'offline', 'error', 'maintenance', 'unknown', name='devicestatus')
    device_status.create(op.get_bind(), checkfirst=True)
    op.add_column('devices', sa.Column('status_old', device_status, nullable=True))
    op.execute("""
        UPDATE devices SET status_old = CASE
            WHEN status = 'idle' THEN 'offline'::devicestatus
            WHEN status = 'transmitting' THEN 'online'::devicestatus
            WHEN status = 'error' THEN 'error'::devicestatus
            WHEN status = 'paused' THEN 'maintenance'::devicestatus
            ELSE 'offline'::devicestatus
        END
    """)
    op.alter_column('devices', 'status_old', nullable=False, server_default=sa.text("'offline'"))
    op.drop_column('devices', 'status')
    op.alter_column('devices', 'status_old', new_column_name='status')

    # Restore device_type to ENUM
    device_type = postgresql.ENUM('sensor', 'actuator', 'gateway', 'controller', 'hybrid', name='devicetype')
    device_type.create(op.get_bind(), checkfirst=True)
    op.add_column('devices', sa.Column('device_type_old', device_type, nullable=True))
    op.execute("""
        UPDATE devices SET device_type_old = CASE
            WHEN device_type = 'sensor' THEN 'sensor'::devicetype
            WHEN device_type = 'datalogger' THEN 'gateway'::devicetype
            ELSE 'sensor'::devicetype
        END
    """)
    op.alter_column('devices', 'device_type_old', nullable=False)
    op.drop_column('devices', 'device_type')
    op.alter_column('devices', 'device_type_old', new_column_name='device_type')

    # Restore old indexes
    op.create_index('ix_device_project_type', 'devices', ['project_id', 'device_type'])
    op.create_index('ix_device_project_status', 'devices', ['project_id', 'status'])
    op.create_index('ix_device_project_active', 'devices', ['project_id', 'is_active'])
    op.create_index('ix_device_unique_id_project', 'devices', ['device_id', 'project_id'], unique=True)
