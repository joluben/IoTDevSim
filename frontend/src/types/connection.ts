export type ProtocolType = 'mqtt' | 'http' | 'https' | 'kafka';

export type ConnectionStatus = 'untested' | 'success' | 'failed' | 'testing';

export interface MQTTConfig {
  broker_url: string;
  port?: number;
  topic: string;
  username?: string;
  password?: string;
  client_id?: string;
  qos?: 0 | 1 | 2;
  retain?: boolean;
  clean_session?: boolean;
  keepalive?: number;
  use_tls?: boolean;
  ca_cert?: string;
  client_cert?: string;
  client_key?: string;
  ws_path?: string;
}

export type HTTPMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export type HTTPAuthType = 'none' | 'basic' | 'bearer' | 'api_key';

export interface HTTPConfig {
  endpoint_url: string;
  method?: HTTPMethod;
  auth_type?: HTTPAuthType;
  username?: string;
  password?: string;
  bearer_token?: string;
  api_key_header?: string;
  api_key_value?: string;
  headers?: Record<string, string>;
  timeout?: number;
  verify_ssl?: boolean;
}

export type KafkaSecurityProtocol = 'PLAINTEXT' | 'SSL' | 'SASL_PLAINTEXT' | 'SASL_SSL';

export type KafkaCompressionType = 'none' | 'gzip' | 'snappy' | 'lz4' | 'zstd';

export type KafkaAcks = '0' | '1' | 'all';

export interface KafkaConfig {
  bootstrap_servers: string[];
  topic: string;
  username?: string;
  password?: string;
  security_protocol?: KafkaSecurityProtocol;
  sasl_mechanism?: string;
  ssl_ca_cert?: string;
  ssl_client_cert?: string;
  ssl_client_key?: string;
  compression_type?: KafkaCompressionType;
  acks?: KafkaAcks;
  retries?: number;
  batch_size?: number;
  linger_ms?: number;
}

export type ConnectionConfig = MQTTConfig | HTTPConfig | KafkaConfig | Record<string, unknown>;

export interface Connection {
  id: string;
  name: string;
  description?: string | null;
  protocol: ProtocolType;
  config: Record<string, unknown>;
  is_active: boolean;
  test_status: ConnectionStatus;
  last_tested?: string | null;
  test_message?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ConnectionCreateRequest {
  name: string;
  description?: string;
  protocol: ProtocolType;
  config: ConnectionConfig;
  is_active?: boolean;
}

export interface ConnectionUpdateRequest {
  name?: string;
  description?: string | null;
  protocol?: ProtocolType;
  config?: ConnectionConfig;
  is_active?: boolean;
}

export interface ConnectionListResponse {
  items: Connection[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ConnectionTestRequest {
  timeout?: number;
}

export interface ConnectionTestResponse {
  success: boolean;
  message: string;
  duration_ms: number;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface ConnectionFilters {
  search?: string;
  protocol?: ProtocolType;
  is_active?: boolean;
  test_status?: ConnectionStatus;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export type BulkOperationType = 'delete' | 'activate' | 'deactivate' | 'test';

export interface BulkOperationRequest {
  operation: BulkOperationType;
  connection_ids: string[];
}

export interface BulkOperationResponse {
  success: boolean;
  success_count: number;
  failure_count: number;
  results: Record<string, unknown>;
  message: string;
}

export type ExportFormat = 'json';

export type ExportOption = 'encrypted' | 'masked';

export interface ConnectionExportRequest {
  connection_ids?: string[];
  format: ExportFormat;
  export_option: ExportOption;
}

export type ConnectionImportStrategy = 'skip' | 'overwrite' | 'rename';

export interface ConnectionImportRequest {
  content: string;
  strategy: ConnectionImportStrategy;
}

export interface ConnectionTemplate {
  name: string;
  description: string;
  protocol: ProtocolType;
  config: ConnectionConfig;
}
