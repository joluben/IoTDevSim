"""
Connection Schemas
Request/response models for connection management
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum

from app.schemas.base import (
    BaseSchema,
    BaseCreateSchema,
    BaseUpdateSchema,
    BaseResponseSchema,
    PaginatedResponse
)


class ProtocolType(str, Enum):
    """Protocol type enumeration"""
    MQTT = "mqtt"
    HTTP = "http"
    HTTPS = "https"
    KAFKA = "kafka"


class ConnectionStatus(str, Enum):
    """Connection test status"""
    UNTESTED = "untested"
    SUCCESS = "success"
    FAILED = "failed"
    TESTING = "testing"


# MQTT Configuration Schemas
class MQTTConfig(BaseModel):
    """MQTT protocol configuration"""
    broker_url: str = Field(..., description="MQTT broker URL (e.g., mqtt://broker.example.com or ws://broker.example.com)")
    port: int = Field(1883, ge=1, le=65535, description="MQTT broker port")
    topic: str = Field(..., description="MQTT topic to publish to")
    username: Optional[str] = Field(None, description="MQTT username")
    password: Optional[str] = Field(None, description="MQTT password")
    client_id: Optional[str] = Field(None, description="MQTT client ID")
    qos: int = Field(0, ge=0, le=2, description="Quality of Service level (0, 1, or 2)")
    retain: bool = Field(False, description="Retain messages flag")
    clean_session: bool = Field(True, description="Clean session flag")
    keepalive: int = Field(60, ge=1, description="Keepalive interval in seconds")
    use_tls: bool = Field(False, description="Use TLS/SSL encryption")
    ca_cert: Optional[str] = Field(None, description="CA certificate for TLS")
    client_cert: Optional[str] = Field(None, description="Client certificate for TLS")
    client_key: Optional[str] = Field(None, description="Client key for TLS")
    ws_path: Optional[str] = Field(None, description="WebSocket path (e.g., /mqtt). Only used with ws:// or wss:// transport")
    
    @field_validator('broker_url')
    @classmethod
    def validate_broker_url(cls, v: str) -> str:
        """Validate MQTT broker URL format"""
        if not v:
            raise ValueError("Broker URL cannot be empty")
        valid_schemes = ('mqtt://', 'mqtts://', 'tcp://', 'ws://', 'wss://')
        if not any(v.startswith(s) for s in valid_schemes):
            raise ValueError("Broker URL must start with mqtt://, mqtts://, tcp://, ws://, or wss://")
        return v.strip()
    
    @property
    def is_websocket(self) -> bool:
        """Check if the connection uses WebSocket transport"""
        return self.broker_url.startswith('ws://') or self.broker_url.startswith('wss://')
    
    @property
    def is_secure(self) -> bool:
        """Check if the connection uses TLS (mqtts://, wss://, or explicit use_tls)"""
        return self.use_tls or self.broker_url.startswith('mqtts://') or self.broker_url.startswith('wss://')
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate MQTT topic"""
        if not v or not v.strip():
            raise ValueError("Topic cannot be empty")
        if '#' in v or '+' in v:
            raise ValueError("Topic cannot contain wildcards (# or +) for publishing")
        return v.strip()


# HTTP/HTTPS Configuration Schemas
class HTTPMethod(str, Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class HTTPAuthType(str, Enum):
    """HTTP authentication types"""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"


class HTTPConfig(BaseModel):
    """HTTP/HTTPS protocol configuration"""
    endpoint_url: str = Field(..., description="HTTP endpoint URL")
    method: HTTPMethod = Field(HTTPMethod.POST, description="HTTP method")
    auth_type: HTTPAuthType = Field(HTTPAuthType.NONE, description="Authentication type")
    username: Optional[str] = Field(None, description="Username for basic auth")
    password: Optional[str] = Field(None, description="Password for basic auth")
    bearer_token: Optional[str] = Field(None, description="Bearer token for bearer auth")
    api_key_header: Optional[str] = Field(None, description="API key header name")
    api_key_value: Optional[str] = Field(None, description="API key value")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional HTTP headers")
    timeout: int = Field(30, ge=1, le=300, description="Request timeout in seconds")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    
    @field_validator('endpoint_url')
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        """Validate HTTP endpoint URL"""
        if not v:
            raise ValueError("Endpoint URL cannot be empty")
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Endpoint URL must start with http:// or https://")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_auth_fields(self):
        """Validate authentication fields based on auth type"""
        if self.auth_type == HTTPAuthType.BASIC:
            if not self.username or not self.password:
                raise ValueError("Username and password required for basic authentication")
        elif self.auth_type == HTTPAuthType.BEARER:
            if not self.bearer_token:
                raise ValueError("Bearer token required for bearer authentication")
        elif self.auth_type == HTTPAuthType.API_KEY:
            if not self.api_key_header or not self.api_key_value:
                raise ValueError("API key header and value required for API key authentication")
        return self


# Kafka Configuration Schemas
class KafkaConfig(BaseModel):
    """Kafka protocol configuration"""
    bootstrap_servers: List[str] = Field(..., min_length=1, description="Kafka bootstrap servers")
    topic: str = Field(..., description="Kafka topic to produce to")
    username: Optional[str] = Field(None, description="SASL username")
    password: Optional[str] = Field(None, description="SASL password")
    security_protocol: str = Field("PLAINTEXT", description="Security protocol (PLAINTEXT, SSL, SASL_PLAINTEXT, SASL_SSL)")
    sasl_mechanism: Optional[str] = Field(None, description="SASL mechanism (PLAIN, SCRAM-SHA-256, SCRAM-SHA-512)")
    ssl_ca_cert: Optional[str] = Field(None, description="SSL CA certificate")
    ssl_client_cert: Optional[str] = Field(None, description="SSL client certificate")
    ssl_client_key: Optional[str] = Field(None, description="SSL client key")
    compression_type: str = Field("none", description="Compression type (none, gzip, snappy, lz4, zstd)")
    acks: str = Field("1", description="Acknowledgment mode (0, 1, all)")
    retries: int = Field(3, ge=0, description="Number of retries")
    batch_size: int = Field(16384, ge=1, description="Batch size in bytes")
    linger_ms: int = Field(0, ge=0, description="Linger time in milliseconds")
    
    @field_validator('bootstrap_servers')
    @classmethod
    def validate_bootstrap_servers(cls, v: List[str]) -> List[str]:
        """Validate Kafka bootstrap servers"""
        if not v:
            raise ValueError("At least one bootstrap server is required")
        validated = []
        for server in v:
            server = server.strip()
            if not server:
                continue
            if ':' not in server:
                raise ValueError(f"Bootstrap server must include port: {server}")
            validated.append(server)
        if not validated:
            raise ValueError("At least one valid bootstrap server is required")
        return validated
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate Kafka topic"""
        if not v or not v.strip():
            raise ValueError("Topic cannot be empty")
        return v.strip()
    
    @field_validator('security_protocol')
    @classmethod
    def validate_security_protocol(cls, v: str) -> str:
        """Validate security protocol"""
        allowed = ["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"]
        if v.upper() not in allowed:
            raise ValueError(f"Security protocol must be one of: {', '.join(allowed)}")
        return v.upper()
    
    @model_validator(mode='after')
    def validate_sasl_fields(self):
        """Validate SASL fields when using SASL"""
        if 'SASL' in self.security_protocol:
            if not self.username or not self.password:
                raise ValueError("Username and password required for SASL authentication")
            if not self.sasl_mechanism:
                raise ValueError("SASL mechanism required for SASL authentication")
        return self


# Connection Request Schemas
class ConnectionCreate(BaseCreateSchema):
    """Schema for creating a connection"""
    name: str = Field(..., min_length=1, max_length=255, description="Connection name")
    description: Optional[str] = Field(None, description="Connection description")
    protocol: ProtocolType = Field(..., description="Protocol type")
    config: Dict[str, Any] = Field(..., description="Protocol-specific configuration")
    is_active: bool = Field(True, description="Whether connection is active")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate connection name"""
        if not v or not v.strip():
            raise ValueError("Connection name cannot be empty")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_config(self):
        """Validate protocol-specific configuration"""
        try:
            if self.protocol == ProtocolType.MQTT:
                MQTTConfig(**self.config)
            elif self.protocol in [ProtocolType.HTTP, ProtocolType.HTTPS]:
                HTTPConfig(**self.config)
            elif self.protocol == ProtocolType.KAFKA:
                KafkaConfig(**self.config)
        except Exception as e:
            raise ValueError(f"Invalid {self.protocol.value} configuration: {str(e)}")
        return self


class ConnectionUpdate(BaseUpdateSchema):
    """Schema for updating a connection"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Connection name")
    description: Optional[str] = Field(None, description="Connection description")
    protocol: Optional[ProtocolType] = Field(None, description="Protocol type")
    config: Optional[Dict[str, Any]] = Field(None, description="Protocol-specific configuration")
    is_active: Optional[bool] = Field(None, description="Whether connection is active")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate connection name"""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Connection name cannot be empty")
        return v.strip() if v else v
    
    @model_validator(mode='after')
    def validate_config(self):
        """Validate protocol-specific configuration if both protocol and config are provided"""
        if self.protocol and self.config:
            try:
                if self.protocol == ProtocolType.MQTT:
                    MQTTConfig(**self.config)
                elif self.protocol in [ProtocolType.HTTP, ProtocolType.HTTPS]:
                    HTTPConfig(**self.config)
                elif self.protocol == ProtocolType.KAFKA:
                    KafkaConfig(**self.config)
            except Exception as e:
                raise ValueError(f"Invalid {self.protocol.value} configuration: {str(e)}")
        return self


# Connection Response Schemas
class ConnectionResponse(BaseResponseSchema):
    """Schema for connection response"""
    name: str = Field(..., description="Connection name")
    description: Optional[str] = Field(None, description="Connection description")
    protocol: ProtocolType = Field(..., description="Protocol type")
    config: Dict[str, Any] = Field(..., description="Protocol-specific configuration (sensitive data masked)")
    is_active: bool = Field(..., description="Whether connection is active")
    test_status: ConnectionStatus = Field(..., description="Connection test status")
    last_tested: Optional[datetime] = Field(None, description="Last test timestamp")
    test_message: Optional[str] = Field(None, description="Test result message")


class ConnectionListResponse(BaseModel):
    """Schema for paginated connection list"""
    items: List[ConnectionResponse] = Field(..., description="List of connections")
    total: int = Field(..., description="Total number of connections")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")
    has_next: bool = Field(..., description="Whether there are more items")
    has_prev: bool = Field(..., description="Whether there are previous items")


# Connection Test Schemas
class ConnectionTestRequest(BaseModel):
    """Schema for connection test request"""
    timeout: int = Field(10, ge=1, le=60, description="Test timeout in seconds")


class ConnectionTestResponse(BaseModel):
    """Schema for connection test response"""
    success: bool = Field(..., description="Whether test was successful")
    message: str = Field(..., description="Test result message")
    duration_ms: float = Field(..., description="Test duration in milliseconds")
    timestamp: datetime = Field(..., description="Test timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional test details")


# Connection Filter Schemas
class ConnectionFilterParams(BaseModel):
    """Schema for connection filtering parameters"""
    search: Optional[str] = Field(None, description="Search in name and description")
    protocol: Optional[ProtocolType] = Field(None, description="Filter by protocol type")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    test_status: Optional[ConnectionStatus] = Field(None, description="Filter by test status")
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of items to return")
    sort_by: Optional[str] = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc or desc)")


# Bulk Operations Schemas
class BulkOperationType(str, Enum):
    """Types of bulk operations"""
    DELETE = "delete"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    TEST = "test"


class BulkOperationRequest(BaseModel):
    """Request schema for bulk operations"""
    operation: BulkOperationType = Field(..., description="Type of operation")
    connection_ids: List[UUID] = Field(..., min_length=1, description="List of connection IDs")


class BulkOperationResponse(BaseModel):
    """Response schema for bulk operations"""
    success: bool = Field(..., description="Overall success status")
    success_count: int = Field(..., description="Number of successful operations")
    failure_count: int = Field(..., description="Number of failed operations")
    results: Dict[str, Any] = Field(..., description="Detailed results by connection ID")
    message: str = Field(..., description="Summary message")


# Import/Export Schemas
class ExportFormat(str, Enum):
    """Export file formats"""
    JSON = "json"


class ExportOption(str, Enum):
    """Export options for sensitive data"""
    ENCRYPTED = "encrypted"  # Keep existing encryption (system-specific)
    MASKED = "masked"        # Mask sensitive data (safe for sharing, not restorable)
    # PLAIN = "plain"        # Decrypt (dangerous, require specific permission/flag)


class ConnectionExportRequest(BaseModel):
    """Request schema for connection export"""
    connection_ids: Optional[List[UUID]] = Field(None, description="List of connection IDs to export. If None, export all.")
    format: ExportFormat = Field(ExportFormat.JSON, description="Export format")
    export_option: ExportOption = Field(ExportOption.ENCRYPTED, description="How to handle sensitive data")


class ConnectionImportStrategy(str, Enum):
    """Strategy for handling existing connections during import"""
    SKIP = "skip"         # Skip if name exists
    OVERWRITE = "overwrite"  # Overwrite if name exists
    RENAME = "rename"     # Auto-rename (append counter)


class ConnectionImportRequest(BaseModel):
    """Request schema for connection import"""
    content: str = Field(..., description="Raw content to import (JSON string)")
    strategy: ConnectionImportStrategy = Field(ConnectionImportStrategy.SKIP, description="Import strategy")


class ConnectionTemplate(BaseModel):
    """Schema for connection configuration template"""
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    protocol: ProtocolType = Field(..., description="Protocol type")
    config: Dict[str, Any] = Field(..., description="Default configuration")
