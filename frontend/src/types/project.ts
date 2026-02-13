import { z } from 'zod';

export type TransmissionStatus = 'inactive' | 'active' | 'paused';

export interface Project {
  id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  transmission_status: TransmissionStatus;
  tags: string[];
  auto_reset_counter: boolean;
  max_devices: number;
  device_count: number;
  is_archived: boolean;
  archived_at?: string | null;
  connection_id?: string | null;
  owner_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  transmission_status: TransmissionStatus;
  tags: string[];
  device_count: number;
  is_archived: boolean;
  connection_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateRequest {
  name: string;
  description?: string;
  tags?: string[];
  connection_id?: string;
  auto_reset_counter?: boolean;
  max_devices?: number;
}

export interface ProjectUpdateRequest {
  name?: string;
  description?: string | null;
  is_active?: boolean;
  tags?: string[];
  connection_id?: string | null;
  auto_reset_counter?: boolean;
  max_devices?: number;
}

export interface ProjectListResponse {
  items: ProjectSummary[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ProjectFilters {
  search?: string;
  is_active?: boolean;
  transmission_status?: TransmissionStatus;
  is_archived?: boolean;
  tags?: string[];
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ProjectDevice {
  id: string;
  name: string;
  device_id: string;
  device_type: string;
  is_active: boolean;
  status: string;
  transmission_enabled: boolean;
  dataset_count: number;
  has_dataset: boolean;
  connection_id?: string | null;
}

export interface ProjectDevicesResponse {
  project_id: string;
  devices: ProjectDevice[];
  count: number;
}

export interface ProjectDeviceAssignRequest {
  device_ids: string[];
}

export interface ProjectTransmissionRequest {
  connection_id?: string;
  auto_reset_counter?: boolean;
}

export interface TransmissionDeviceResult {
  device_id: string;
  device_name: string;
  success: boolean;
  message: string;
}

export interface ProjectTransmissionResult {
  project_id: string;
  operation: string;
  transmission_status: string;
  total_devices: number;
  success_count: number;
  failure_count: number;
  results: TransmissionDeviceResult[];
}

export interface ProjectStats {
  project_id: string;
  total_devices: number;
  total_transmissions: number;
  successful_transmissions: number;
  failed_transmissions: number;
  success_rate: number;
}

export interface TransmissionHistoryEntry {
  id: string;
  device_id: string;
  device_name?: string | null;
  device_ref?: string | null;
  connection_id?: string | null;
  status: string;
  message_type: string;
  protocol: string;
  topic?: string | null;
  payload_size: number;
  error_message?: string | null;
  latency_ms?: number | null;
  timestamp: string;
}

export interface TransmissionHistoryResponse {
  items: TransmissionHistoryEntry[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface TransmissionHistoryFilters {
  device_id?: string;
  status?: string;
  skip?: number;
  limit?: number;
}

// ==================== Form Schema ====================

export const projectFormSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters').max(255, 'Max 255 characters'),
  description: z.string().max(500, 'Max 500 characters').optional().or(z.literal('')),
  tags: z.string().optional(),
  connection_id: z.string().optional().or(z.literal('')),
  auto_reset_counter: z.boolean(),
  max_devices: z.number().int().min(1).max(10000),
});

export type ProjectFormValues = z.infer<typeof projectFormSchema>;
