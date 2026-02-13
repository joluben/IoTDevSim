"""
Update connections table for IoT protocol support

Revision ID: 000002_iot_protocols
Revises: 000001_initial
Create Date: 2025-01-22 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000002_iot_protocols'
down_revision = '000001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old connection_type and connection_status enums
    op.execute("ALTER TABLE connections ALTER COLUMN connection_type TYPE varchar(50)")
    op.execute("ALTER TABLE connections ALTER COLUMN status TYPE varchar(50)")
    op.execute("DROP TYPE IF EXISTS connectiontype CASCADE")
    op.execute("DROP TYPE IF EXISTS connectionstatus CASCADE")
    
    # Create new protocol_type and connection_status enums
    protocol_type = postgresql.ENUM('mqtt', 'http', 'https', 'kafka', name='protocoltype')
    connection_status = postgresql.ENUM('untested', 'success', 'failed', 'testing', name='connectionstatus')
    
    protocol_type.create(op.get_bind(), checkfirst=True)
    connection_status.create(op.get_bind(), checkfirst=True)
    
    # Drop old columns that are no longer needed
    op.drop_column('connections', 'source_device_id')
    op.drop_column('connections', 'target_device_id')
    op.drop_column('connections', 'project_id')
    op.drop_column('connections', 'protocol_version')
    op.drop_column('connections', 'qos_level')
    op.drop_column('connections', 'retain_messages')
    op.drop_column('connections', 'latency_ms')
    op.drop_column('connections', 'throughput_bps')
    op.drop_column('connections', 'packet_loss_rate')
    op.drop_column('connections', 'max_message_size')
    op.drop_column('connections', 'rate_limit_per_second')
    op.drop_column('connections', 'simulation_enabled')
    op.drop_column('connections', 'simulation_config')
    op.drop_column('connections', 'total_messages_sent')
    op.drop_column('connections', 'total_messages_received')
    op.drop_column('connections', 'total_bytes_sent')
    op.drop_column('connections', 'total_bytes_received')
    op.drop_column('connections', 'last_activity_at')
    op.drop_column('connections', 'connection_type')
    op.drop_column('connections', 'status')
    op.drop_column('connections', 'configuration')
    
    # Add new columns
    op.add_column('connections', sa.Column('protocol', protocol_type, nullable=False, server_default='mqtt'))
    op.add_column('connections', sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column('connections', sa.Column('test_status', connection_status, nullable=False, server_default='untested'))
    op.add_column('connections', sa.Column('last_tested', sa.DateTime(timezone=True), nullable=True))
    op.add_column('connections', sa.Column('test_message', sa.Text(), nullable=True))
    
    # Update name column length
    op.alter_column('connections', 'name', type_=sa.String(length=255), existing_type=sa.String(length=100))
    
    # Drop old indexes
    op.drop_index('ix_connection_project_type', table_name='connections')
    op.drop_index('ix_connection_project_status', table_name='connections')
    op.drop_index('ix_connection_devices', table_name='connections')
    op.drop_index('ix_connection_source_device', table_name='connections')
    op.drop_index('ix_connection_target_device', table_name='connections')
    op.drop_index('ix_connection_activity', table_name='connections')
    
    # Create new indexes
    op.create_index('ix_connection_protocol_active', 'connections', ['protocol', 'is_active'])
    op.create_index('ix_connection_test_status', 'connections', ['test_status'])
    op.create_index('ix_connections_name', 'connections', ['name'])


def downgrade() -> None:
    # Drop new indexes
    op.drop_index('ix_connection_test_status', table_name='connections')
    op.drop_index('ix_connection_protocol_active', table_name='connections')
    op.drop_index('ix_connections_name', table_name='connections')
    
    # Drop new columns
    op.drop_column('connections', 'test_message')
    op.drop_column('connections', 'last_tested')
    op.drop_column('connections', 'test_status')
    op.drop_column('connections', 'config')
    op.drop_column('connections', 'protocol')
    
    # Recreate old enum types
    old_connection_type = postgresql.ENUM('mqtt', 'http', 'websocket', 'tcp', 'udp', 'coap', 'custom', name='connectiontype')
    old_connection_status = postgresql.ENUM('active', 'inactive', 'error', 'pending', name='connectionstatus')
    
    old_connection_type.create(op.get_bind(), checkfirst=True)
    old_connection_status.create(op.get_bind(), checkfirst=True)
    
    # Add back old columns
    op.add_column('connections', sa.Column('connection_type', old_connection_type, nullable=False, server_default='mqtt'))
    op.add_column('connections', sa.Column('status', old_connection_status, nullable=False, server_default='inactive'))
    op.add_column('connections', sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column('connections', sa.Column('protocol_version', sa.String(length=20), nullable=True))
    op.add_column('connections', sa.Column('source_device_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('connections', sa.Column('target_device_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('connections', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('connections', sa.Column('qos_level', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('connections', sa.Column('retain_messages', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('connections', sa.Column('latency_ms', sa.Float(), nullable=True))
    op.add_column('connections', sa.Column('throughput_bps', sa.Integer(), nullable=True))
    op.add_column('connections', sa.Column('packet_loss_rate', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('connections', sa.Column('max_message_size', sa.Integer(), nullable=False, server_default='1024'))
    op.add_column('connections', sa.Column('rate_limit_per_second', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('connections', sa.Column('simulation_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('connections', sa.Column('simulation_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column('connections', sa.Column('total_messages_sent', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('connections', sa.Column('total_messages_received', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('connections', sa.Column('total_bytes_sent', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('connections', sa.Column('total_bytes_received', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('connections', sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True))
    
    # Restore name column length
    op.alter_column('connections', 'name', type_=sa.String(length=100), existing_type=sa.String(length=255))
    
    # Recreate old indexes
    op.create_index('ix_connection_project_type', 'connections', ['project_id', 'connection_type'])
    op.create_index('ix_connection_project_status', 'connections', ['project_id', 'status'])
    op.create_index('ix_connection_devices', 'connections', ['source_device_id', 'target_device_id'])
    op.create_index('ix_connection_source_device', 'connections', ['source_device_id'])
    op.create_index('ix_connection_target_device', 'connections', ['target_device_id'])
    op.create_index('ix_connection_activity', 'connections', ['last_activity_at'])
    
    # Drop new enum types
    protocol_type = postgresql.ENUM(name='protocoltype')
    connection_status = postgresql.ENUM(name='connectionstatus')
    
    protocol_type.drop(op.get_bind(), checkfirst=True)
    connection_status.drop(op.get_bind(), checkfirst=True)
