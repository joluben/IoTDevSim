"""
Initial schema for IoT DevSim v2

Revision ID: 000001_initial
Revises: 
Create Date: 2025-09-20 16:50:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create custom ENUM types
    device_type = postgresql.ENUM('sensor', 'actuator', 'gateway', 'controller', 'hybrid', name='devicetype')
    device_status = postgresql.ENUM('online', 'offline', 'error', 'maintenance', 'unknown', name='devicestatus')
    connection_type = postgresql.ENUM('mqtt', 'http', 'websocket', 'tcp', 'udp', 'coap', 'custom', name='connectiontype')
    connection_status = postgresql.ENUM('active', 'inactive', 'error', 'pending', name='connectionstatus')

    device_type.create(op.get_bind(), checkfirst=True)
    device_status.create(op.get_bind(), checkfirst=True)
    connection_type.create(op.get_bind(), checkfirst=True)
    connection_status.create(op.get_bind(), checkfirst=True)

    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('roles', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_is_active', 'users', ['is_active'])

    # projects
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('max_devices', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('max_connections', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
    )
    op.create_index('ix_projects_name', 'projects', ['name'])
    op.create_index('ix_projects_is_active', 'projects', ['is_active'])
    op.create_index('ix_projects_owner', 'projects', ['owner_id'])

    # devices
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('device_type', device_type, nullable=False),
        sa.Column('manufacturer', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('firmware_version', sa.String(length=50), nullable=True),
        sa.Column('status', device_status, nullable=False, server_default=sa.text("'offline'")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('mac_address', sa.String(length=17), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('simulation_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('simulation_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
    )
    op.create_index('ix_device_project_type', 'devices', ['project_id', 'device_type'])
    op.create_index('ix_device_project_status', 'devices', ['project_id', 'status'])
    op.create_index('ix_device_project_active', 'devices', ['project_id', 'is_active'])
    op.create_index('ix_device_unique_id_project', 'devices', ['device_id', 'project_id'], unique=True)

    # connections
    op.create_table(
        'connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('connection_type', connection_type, nullable=False),
        sa.Column('protocol_version', sa.String(length=20), nullable=True),
        sa.Column('status', connection_status, nullable=False, server_default=sa.text("'inactive'")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('source_device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('target_device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('qos_level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retain_messages', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('throughput_bps', sa.Integer(), nullable=True),
        sa.Column('packet_loss_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('max_message_size', sa.Integer(), nullable=False, server_default='1024'),
        sa.Column('rate_limit_per_second', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('simulation_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('simulation_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('total_messages_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_messages_received', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_bytes_sent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_bytes_received', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_connection_project_type', 'connections', ['project_id', 'connection_type'])
    op.create_index('ix_connection_project_status', 'connections', ['project_id', 'status'])
    op.create_index('ix_connection_devices', 'connections', ['source_device_id', 'target_device_id'])
    op.create_index('ix_connection_source_device', 'connections', ['source_device_id'])
    op.create_index('ix_connection_target_device', 'connections', ['target_device_id'])
    op.create_index('ix_connection_activity', 'connections', ['last_activity_at'])

    # transmission_logs
    op.create_table(
        'transmission_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('connections.id'), nullable=True),
        sa.Column('message_type', sa.String(length=50), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('payload_size', sa.Integer(), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=True),
        sa.Column('message_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('protocol', sa.String(length=20), nullable=False),
        sa.Column('topic', sa.String(length=255), nullable=True),
        sa.Column('qos_level', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('simulation_batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index('ix_transmission_log_timestamp_device', 'transmission_logs', ['timestamp', 'device_id'])
    op.create_index('ix_transmission_log_timestamp_connection', 'transmission_logs', ['timestamp', 'connection_id'])
    op.create_index('ix_transmission_log_device_type_time', 'transmission_logs', ['device_id', 'message_type', 'timestamp'])
    op.create_index('ix_transmission_log_connection_direction', 'transmission_logs', ['connection_id', 'direction', 'timestamp'])
    op.create_index('ix_transmission_log_status_time', 'transmission_logs', ['status', 'timestamp'])
    op.create_index('ix_transmission_log_protocol_time', 'transmission_logs', ['protocol', 'timestamp'])
    op.create_index('ix_transmission_log_simulation', 'transmission_logs', ['is_simulated', 'timestamp'])
    op.create_index('ix_transmission_log_batch', 'transmission_logs', ['simulation_batch_id', 'timestamp'])
    op.create_index('ix_transmission_log_hash', 'transmission_logs', ['payload_hash'])

    # BRIN index for timestamp (large table optimization)
    op.execute("CREATE INDEX IF NOT EXISTS brin_transmission_log_timestamp ON transmission_logs USING BRIN (timestamp)")


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('brin_transmission_log_timestamp', table_name=None)
    op.drop_table('transmission_logs')
    op.drop_table('connections')
    op.drop_table('devices')
    op.drop_table('projects')
    op.drop_table('users')

    # Drop enum types
    connection_status = postgresql.ENUM(name='connectionstatus')
    connection_type = postgresql.ENUM(name='connectiontype')
    device_status = postgresql.ENUM(name='devicestatus')
    device_type = postgresql.ENUM(name='devicetype')

    connection_status.drop(op.get_bind(), checkfirst=True)
    connection_type.drop(op.get_bind(), checkfirst=True)
    device_status.drop(op.get_bind(), checkfirst=True)
    device_type.drop(op.get_bind(), checkfirst=True)
