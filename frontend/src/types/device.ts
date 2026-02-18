import { z } from 'zod';

export type DeviceType = 'sensor' | 'datalogger';

export type DeviceStatus = 'idle' | 'transmitting' | 'error' | 'paused';

export interface TransmissionConfig {
  batch_size?: number;
  auto_reset?: boolean;
  jitter_ms?: number;
  retry_on_error?: boolean;
  max_retries?: number;
  include_device_id?: boolean;
  include_timestamp?: boolean;
}

export interface DeviceMetadata {
  manufacturer?: string | null;
  model?: string | null;
  firmware_version?: string | null;
  ip_address?: string | null;
  mac_address?: string | null;
  port?: number | null;
  capabilities?: string[];
  custom_metadata?: Record<string, unknown>;
}

export interface Device {
  id: string;
  name: string;
  device_id: string;
  description?: string | null;
  device_type: DeviceType;
  is_active: boolean;
  status: DeviceStatus;
  tags: string[];
  connection_id?: string | null;
  project_id?: string | null;
  transmission_enabled: boolean;
  transmission_frequency?: number | null;
  transmission_config: TransmissionConfig;
  current_row_index: number;
  last_transmission_at?: string | null;
  manufacturer?: string | null;
  model?: string | null;
  firmware_version?: string | null;
  ip_address?: string | null;
  mac_address?: string | null;
  port?: number | null;
  capabilities?: string[];
  device_metadata?: Record<string, unknown>;
  dataset_count: number;
  has_dataset: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeviceSummary {
  id: string;
  name: string;
  device_id: string;
  description?: string | null;
  device_type: DeviceType;
  is_active: boolean;
  status: DeviceStatus;
  tags: string[];
  connection_id?: string | null;
  project_id?: string | null;
  transmission_enabled: boolean;
  dataset_count: number;
  has_dataset: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeviceCreateRequest {
  name: string;
  description?: string;
  device_type: DeviceType;
  device_id?: string;
  tags?: string[];
  connection_id?: string;
  project_id?: string;
  transmission_enabled?: boolean;
  transmission_frequency?: number;
  transmission_config?: TransmissionConfig;
  metadata?: DeviceMetadata;
}

export interface DeviceUpdateRequest {
  name?: string;
  description?: string | null;
  device_id?: string;
  device_type?: DeviceType;
  is_active?: boolean;
  tags?: string[];
  connection_id?: string | null;
  project_id?: string | null;
  transmission_enabled?: boolean;
  transmission_frequency?: number | null;
  transmission_config?: TransmissionConfig;
}

export interface DeviceListResponse {
  items: DeviceSummary[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface DeviceFilters {
  search?: string;
  device_type?: DeviceType;
  is_active?: boolean;
  transmission_enabled?: boolean;
  has_dataset?: boolean;
  tags?: string[];
  connection_id?: string;
  project_id?: string;
  status?: DeviceStatus;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface DeviceDuplicateRequest {
  count: number;
  name_prefix?: string;
}

export interface DeviceDuplicatePreview {
  names: string[];
  count: number;
}

export interface DeviceDuplicateResponse {
  created_count: number;
  devices: DeviceSummary[];
}

export interface DeviceDatasetLinkRequest {
  dataset_id: string;
  config?: Record<string, unknown>;
}

export interface DeviceDatasetLink {
  device_id: string;
  dataset_id: string;
  linked_at: string;
  config: Record<string, unknown>;
}

export interface DeviceMetadataResponse {
  device_id: string;
  device_name: string;
  manufacturer?: string | null;
  model?: string | null;
  firmware_version?: string | null;
  ip_address?: string | null;
  mac_address?: string | null;
  port?: number | null;
  capabilities: string[];
  custom_metadata: Record<string, unknown>;
}

export interface DeviceExportRequest {
  device_ids?: string[];
  include_metadata?: boolean;
  include_transmission_config?: boolean;
}

export type DeviceImportStrategy = 'skip' | 'overwrite' | 'rename';

export interface DeviceImportRequest {
  content: string;
  strategy: DeviceImportStrategy;
}

export interface DeviceImportResponse {
  imported_count: number;
  skipped_count: number;
  error_count: number;
  errors: Array<{ name: string; error: string }>;
}

export interface DeviceBulkLinkRequest {
  device_ids: string[];
  dataset_id: string;
  config?: Record<string, unknown>;
}

// ==================== Device Form Schema & Values ====================

export const deviceFormSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(100, "Name must be at most 100 characters"),
  device_id: z
    .string()
    .length(8, "Must be exactly 8 characters")
    .regex(/^[A-Za-z0-9]+$/, "Only alphanumeric characters")
    .optional()
    .or(z.literal("")),
  device_type: z.enum(["sensor", "datalogger"]),
  description: z.string().max(500, "Max 500 characters").optional().or(z.literal("")),
  tags: z.string().optional(),
  is_active: z.boolean(),
  connection_id: z.string().optional().or(z.literal("")),
  transmission_enabled: z.boolean(),
  transmission_frequency: z.number().int().min(1, "Frequency must be at least 1 second").max(172800, "Frequency must be at most 48 hours (172800 seconds)").optional(),
  include_device_id: z.boolean(),
  include_timestamp: z.boolean(),
  auto_reset: z.boolean(),
  batch_size: z.number().int().min(1).optional(),
  manufacturer: z.string().max(100).nullable().optional(),
  model: z.string().max(100).nullable().optional(),
  firmware_version: z.string().max(50).nullable().optional(),
  ip_address: z.string().max(45).nullable().optional(),
  mac_address: z.string().max(17).nullable().optional(),
  port: z.number().int().min(1).max(65535).nullable().optional(),
  capabilities: z.array(z.string()).optional(),
  custom_metadata: z.record(z.string(), z.unknown()).optional(),
}).refine(
  (data) => {
    if (data.transmission_enabled) {
      return data.transmission_frequency !== undefined && data.transmission_frequency !== null && data.transmission_frequency >= 1;
    }
    return true;
  },
  {
    message: "Transmission frequency is required when transmission is enabled",
    path: ["transmission_frequency"],
  }
);

export type DeviceFormValues = z.infer<typeof deviceFormSchema>;
