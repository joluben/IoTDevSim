-- IoTDevSim Database Initialization
-- PostgreSQL optimization for IoT workloads

-- Create database if it doesn't exist (handled by Docker)
-- CREATE DATABASE iot_devsim;

-- Connect to the database
\c iot_devsim;

-- Create extensions for better performance and functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Set timezone
SET timezone = 'UTC';

-- Optimize PostgreSQL settings for IoT workloads
-- These settings are optimized for write-heavy IoT data ingestion

-- Memory settings
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- WAL settings for high write throughput
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET wal_compression = 'on';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';
ALTER SYSTEM SET checkpoint_timeout = '15min';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

-- Connection and performance settings
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET max_parallel_workers = 4;
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
ALTER SYSTEM SET max_parallel_maintenance_workers = 2;

-- Logging settings for monitoring
ALTER SYSTEM SET log_statement = 'mod';
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_checkpoints = 'on';
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';

-- Reload configuration
SELECT pg_reload_conf();

-- Create custom functions for IoT data processing

-- Function to generate device IDs
CREATE OR REPLACE FUNCTION generate_device_id(prefix TEXT DEFAULT 'DEV')
RETURNS TEXT AS $$
BEGIN
    RETURN prefix || '-' || UPPER(SUBSTRING(uuid_generate_v4()::TEXT FROM 1 FOR 8));
END;
$$ LANGUAGE plpgsql;

-- Function to calculate message hash
CREATE OR REPLACE FUNCTION calculate_message_hash(content JSONB)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(digest(content::TEXT, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Function to clean old transmission logs (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_transmission_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM transmission_logs 
    WHERE timestamp < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create indexes that will be used across tables
-- These will be created by Alembic migrations, but we define them here for reference

-- Notification for successful initialization
DO $$
BEGIN
    RAISE NOTICE 'database initialized successfully';
    RAISE NOTICE 'Extensions created: uuid-ossp, pg_stat_statements, pg_trgm, btree_gin, btree_gist';
    RAISE NOTICE 'Custom functions created: generate_device_id, calculate_message_hash, cleanup_old_transmission_logs';
END $$;
