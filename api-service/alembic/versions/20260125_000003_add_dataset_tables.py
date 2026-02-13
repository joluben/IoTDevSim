"""
Add dataset management tables

Revision ID: 000003_datasets
Revises: 000002_iot_protocols
Create Date: 2026-01-25 17:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000003_datasets'
down_revision = '000002_iot_protocols'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create dataset enums
    dataset_status = postgresql.ENUM('draft', 'processing', 'ready', 'error', name='datasetstatus')
    dataset_source = postgresql.ENUM('upload', 'generated', 'manual', 'template', name='datasetsource')
    
    dataset_status.create(op.get_bind(), checkfirst=True)
    dataset_source.create(op.get_bind(), checkfirst=True)
    
    # Create datasets table
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        
        # Basic information
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Data source and characteristics
        sa.Column('source', dataset_source, nullable=False),
        sa.Column('status', dataset_status, nullable=False, server_default='draft'),
        
        # File information
        sa.Column('file_path', sa.String(512), nullable=True),
        sa.Column('file_format', sa.String(20), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        
        # Data metrics
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('column_count', sa.Integer(), nullable=False, server_default='0'),
        
        # Schema and metadata (JSONB for PostgreSQL)
        sa.Column('schema_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        
        # Quality metrics
        sa.Column('completeness_score', sa.Float(), nullable=True),
        sa.Column('validation_status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        
        # Generator configuration
        sa.Column('generator_type', sa.String(50), nullable=True),
        sa.Column('generator_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    
    # Create indexes for datasets
    op.create_index('ix_datasets_name', 'datasets', ['name'])
    op.create_index('ix_datasets_source', 'datasets', ['source'])
    op.create_index('ix_datasets_status', 'datasets', ['status'])
    op.create_index('ix_datasets_created_at', 'datasets', ['created_at'])
    op.create_index('ix_datasets_updated_at', 'datasets', ['updated_at'])
    op.create_index('ix_datasets_deleted_at', 'datasets', ['deleted_at'])
    op.create_index('ix_datasets_is_deleted', 'datasets', ['is_deleted'])
    op.create_index('ix_dataset_source_status', 'datasets', ['source', 'status'])
    op.create_index('ix_dataset_status_active', 'datasets', ['status', 'is_deleted'])
    op.create_index('ix_dataset_name_search', 'datasets', ['name'])
    
    # Create dataset_versions table
    op.create_table(
        'dataset_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        
        # Reference to parent dataset
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        
        # Version information
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('change_description', sa.Text(), nullable=True),
        
        # File snapshot
        sa.Column('file_path', sa.String(512), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        
        # Data metrics snapshot
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('column_count', sa.Integer(), nullable=False, server_default='0'),
        
        # Schema snapshot
        sa.Column('schema_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    
    # Create indexes for dataset_versions
    op.create_index('ix_dataset_versions_dataset_id', 'dataset_versions', ['dataset_id'])
    op.create_index('ix_dataset_versions_version_number', 'dataset_versions', ['version_number'])
    op.create_index('ix_dataset_versions_created_at', 'dataset_versions', ['created_at'])
    op.create_index('ix_dataset_version_unique', 'dataset_versions', ['dataset_id', 'version_number'], unique=True)
    
    # Create dataset_columns table
    op.create_table(
        'dataset_columns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        
        # Reference to parent dataset
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        
        # Column information
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        
        # Constraints
        sa.Column('nullable', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        
        # Statistics
        sa.Column('unique_count', sa.Integer(), nullable=True),
        sa.Column('null_count', sa.Integer(), nullable=True),
        sa.Column('min_value', sa.String(255), nullable=True),
        sa.Column('max_value', sa.String(255), nullable=True),
        sa.Column('mean_value', sa.Float(), nullable=True),
        
        # Sample values
        sa.Column('sample_values', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    
    # Create indexes for dataset_columns
    op.create_index('ix_dataset_columns_dataset_id', 'dataset_columns', ['dataset_id'])
    op.create_index('ix_dataset_column_position', 'dataset_columns', ['dataset_id', 'position'])


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_table('dataset_columns')
    op.drop_table('dataset_versions')
    op.drop_table('datasets')
    
    # Drop enum types
    dataset_status = postgresql.ENUM(name='datasetstatus')
    dataset_source = postgresql.ENUM(name='datasetsource')
    
    dataset_status.drop(op.get_bind(), checkfirst=True)
    dataset_source.drop(op.get_bind(), checkfirst=True)
