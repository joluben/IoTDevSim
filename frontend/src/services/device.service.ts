/**
 * Device Service
 * API client for device management operations
 */

import { z } from 'zod';

import { apiClient } from '@/services/api.client';
import type {
  Device,
  DeviceSummary,
  DeviceCreateRequest,
  DeviceUpdateRequest,
  DeviceListResponse,
  DeviceFilters,
  DeviceDuplicateRequest,
  DeviceDuplicatePreview,
  DeviceDuplicateResponse,
  DeviceDatasetLinkRequest,
  DeviceDatasetLink,
  DeviceMetadata,
  DeviceMetadataResponse,
  DeviceExportRequest,
  DeviceImportRequest,
  DeviceImportResponse,
  DeviceBulkLinkRequest,
} from '@/types/device';

const DEVICES_BASE_PATH = '/devices';

// ==================== Zod Schemas ====================

const transmissionConfigSchema = z.object({
  batch_size: z.number().optional(),
  auto_reset: z.boolean().optional(),
  jitter_ms: z.number().optional(),
  retry_on_error: z.boolean().optional(),
  max_retries: z.number().optional(),
}).passthrough();

const deviceSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  device_id: z.string(),
  description: z.string().nullable().optional(),
  device_type: z.enum(['sensor', 'datalogger']),
  is_active: z.boolean(),
  status: z.enum(['idle', 'transmitting', 'error', 'paused']),
  tags: z.array(z.string()),
  connection_id: z.string().uuid().nullable().optional(),
  project_id: z.string().uuid().nullable().optional(),
  transmission_enabled: z.boolean(),
  transmission_frequency: z.number().nullable().optional(),
  transmission_config: transmissionConfigSchema,
  current_row_index: z.number(),
  last_transmission_at: z.string().nullable().optional(),
  manufacturer: z.string().nullable().optional(),
  model: z.string().nullable().optional(),
  firmware_version: z.string().nullable().optional(),
  ip_address: z.string().nullable().optional(),
  mac_address: z.string().nullable().optional(),
  port: z.number().nullable().optional(),
  capabilities: z.array(z.string()).optional(),
  device_metadata: z.record(z.string(), z.unknown()).optional(),
  dataset_count: z.number(),
  has_dataset: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

const deviceSummarySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  device_id: z.string(),
  description: z.string().nullable().optional(),
  device_type: z.enum(['sensor', 'datalogger']),
  is_active: z.boolean(),
  status: z.enum(['idle', 'transmitting', 'error', 'paused']),
  tags: z.array(z.string()),
  connection_id: z.string().uuid().nullable().optional(),
  project_id: z.string().uuid().nullable().optional(),
  transmission_enabled: z.boolean(),
  dataset_count: z.number(),
  has_dataset: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

const deviceListResponseSchema = z.object({
  items: z.array(deviceSummarySchema),
  total: z.number(),
  skip: z.number(),
  limit: z.number(),
  has_next: z.boolean(),
  has_prev: z.boolean(),
});

const deviceCreateSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  device_type: z.enum(['sensor', 'datalogger']),
  device_id: z.string().length(8).regex(/^[A-Za-z0-9]+$/).optional(),
  tags: z.array(z.string()).optional(),
  connection_id: z.string().uuid().optional(),
  project_id: z.string().uuid().optional(),
  transmission_enabled: z.boolean().optional(),
  transmission_frequency: z.number().int().min(1).optional(),
  transmission_config: transmissionConfigSchema.optional(),
  metadata: z.object({
    manufacturer: z.string().nullable().optional(),
    model: z.string().nullable().optional(),
    firmware_version: z.string().nullable().optional(),
    ip_address: z.string().nullable().optional(),
    mac_address: z.string().nullable().optional(),
    port: z.number().nullable().optional(),
    capabilities: z.array(z.string()).optional(),
    custom_metadata: z.record(z.string(), z.unknown()).optional(),
  }).optional(),
});

const deviceUpdateSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: z.string().max(500).nullable().optional(),
  device_id: z.string().length(8).regex(/^[A-Za-z0-9]+$/).optional(),
  device_type: z.enum(['sensor', 'datalogger']).optional(),
  is_active: z.boolean().optional(),
  tags: z.array(z.string()).optional(),
  connection_id: z.string().uuid().nullable().optional(),
  project_id: z.string().uuid().nullable().optional(),
  transmission_enabled: z.boolean().optional(),
  transmission_frequency: z.number().int().min(1).nullable().optional(),
  transmission_config: transmissionConfigSchema.optional(),
});

const duplicatePreviewSchema = z.object({
  names: z.array(z.string()),
  count: z.number(),
});

const duplicateResponseSchema = z.object({
  created_count: z.number(),
  devices: z.array(deviceSummarySchema),
});

const datasetLinkSchema = z.object({
  device_id: z.string(),
  dataset_id: z.string(),
  linked_at: z.string(),
  config: z.record(z.string(), z.unknown()),
});

const metadataResponseSchema = z.object({
  device_id: z.string(),
  device_name: z.string(),
  manufacturer: z.string().nullable().optional(),
  model: z.string().nullable().optional(),
  firmware_version: z.string().nullable().optional(),
  ip_address: z.string().nullable().optional(),
  mac_address: z.string().nullable().optional(),
  port: z.number().nullable().optional(),
  capabilities: z.array(z.string()),
  custom_metadata: z.record(z.string(), z.unknown()),
});

const importResponseSchema = z.object({
  imported_count: z.number(),
  skipped_count: z.number(),
  error_count: z.number(),
  errors: z.array(z.object({ name: z.string(), error: z.string() })),
});

// ==================== Helper Functions ====================

function buildQueryParams(filters: DeviceFilters): Record<string, string | number | boolean> {
  const params: Record<string, string | number | boolean> = {};

  if (filters.search) params.search = filters.search;
  if (filters.device_type) params.device_type = filters.device_type;
  if (filters.is_active !== undefined) params.is_active = filters.is_active;
  if (filters.transmission_enabled !== undefined) params.transmission_enabled = filters.transmission_enabled;
  if (filters.has_dataset !== undefined) params.has_dataset = filters.has_dataset;
  if (filters.tags && filters.tags.length > 0) params.tags = filters.tags.join(',');
  if (filters.connection_id) params.connection_id = filters.connection_id;
  if (filters.project_id) params.project_id = filters.project_id;
  if (filters.status) params.status = filters.status;
  if (filters.skip !== undefined) params.skip = filters.skip;
  if (filters.limit !== undefined) params.limit = filters.limit;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.sort_order) params.sort_order = filters.sort_order;

  return params;
}

// ==================== Device Service Class ====================

class DeviceService {
  /**
   * List devices with filtering and pagination
   */
  async list(filters: DeviceFilters = {}): Promise<DeviceListResponse> {
    const data = await apiClient.get<unknown>(DEVICES_BASE_PATH, {
      params: buildQueryParams(filters),
    });
    return deviceListResponseSchema.parse(data) as DeviceListResponse;
  }

  /**
   * Get device by UUID
   */
  async getById(id: string): Promise<Device> {
    const data = await apiClient.get<unknown>(`${DEVICES_BASE_PATH}/${id}`);
    return deviceSchema.parse(data) as Device;
  }

  /**
   * Create a new device
   */
  async create(payload: DeviceCreateRequest): Promise<Device> {
    const validated = deviceCreateSchema.parse(payload);
    const data = await apiClient.post<unknown>(DEVICES_BASE_PATH, validated);
    return deviceSchema.parse(data) as Device;
  }

  /**
   * Update a device
   */
  async update(id: string, payload: DeviceUpdateRequest): Promise<Device> {
    const validated = deviceUpdateSchema.parse(payload);
    const data = await apiClient.put<unknown>(`${DEVICES_BASE_PATH}/${id}`, validated);
    return deviceSchema.parse(data) as Device;
  }

  /**
   * Partial update a device
   */
  async patch(id: string, payload: DeviceUpdateRequest): Promise<Device> {
    const validated = deviceUpdateSchema.parse(payload);
    const data = await apiClient.patch<unknown>(`${DEVICES_BASE_PATH}/${id}`, validated);
    return deviceSchema.parse(data) as Device;
  }

  /**
   * Delete a device
   */
  async delete(id: string, options?: { hardDelete?: boolean }): Promise<{ message: string }> {
    const hardDelete = options?.hardDelete ?? false;
    const data = await apiClient.delete<unknown>(`${DEVICES_BASE_PATH}/${id}`, {
      params: { hard_delete: hardDelete },
    });
    return data as { message: string };
  }

  // ==================== Duplication ====================

  /**
   * Preview duplication names
   */
  async previewDuplicate(id: string, payload: DeviceDuplicateRequest): Promise<DeviceDuplicatePreview> {
    const data = await apiClient.post<unknown>(`${DEVICES_BASE_PATH}/${id}/duplicate/preview`, payload);
    return duplicatePreviewSchema.parse(data) as DeviceDuplicatePreview;
  }

  /**
   * Duplicate a device
   */
  async duplicate(id: string, payload: DeviceDuplicateRequest): Promise<DeviceDuplicateResponse> {
    const data = await apiClient.post<unknown>(`${DEVICES_BASE_PATH}/${id}/duplicate`, payload);
    return duplicateResponseSchema.parse(data) as DeviceDuplicateResponse;
  }

  // ==================== Dataset Linking ====================

  /**
   * Get datasets linked to a device
   */
  async getDatasets(id: string): Promise<{ device_id: string; datasets: DeviceDatasetLink[] }> {
    const data = await apiClient.get<unknown>(`${DEVICES_BASE_PATH}/${id}/datasets`);
    return data as { device_id: string; datasets: DeviceDatasetLink[] };
  }

  /**
   * Link a dataset to a device
   */
  async linkDataset(id: string, payload: DeviceDatasetLinkRequest): Promise<unknown> {
    return apiClient.post<unknown>(`${DEVICES_BASE_PATH}/${id}/datasets`, payload);
  }

  /**
   * Unlink a dataset from a device
   */
  async unlinkDataset(deviceId: string, datasetId: string): Promise<unknown> {
    return apiClient.delete<unknown>(`${DEVICES_BASE_PATH}/${deviceId}/datasets/${datasetId}`);
  }

  /**
   * Bulk link a dataset to multiple devices
   */
  async bulkLinkDataset(payload: DeviceBulkLinkRequest): Promise<unknown> {
    return apiClient.post<unknown>(`${DEVICES_BASE_PATH}/bulk-link-dataset`, payload);
  }

  // ==================== Metadata ====================

  /**
   * Get device metadata
   */
  async getMetadata(id: string): Promise<DeviceMetadataResponse> {
    const data = await apiClient.get<unknown>(`${DEVICES_BASE_PATH}/${id}/metadata`);
    return metadataResponseSchema.parse(data) as DeviceMetadataResponse;
  }

  /**
   * Full update of device metadata
   */
  async updateMetadata(id: string, payload: DeviceMetadata): Promise<DeviceMetadataResponse> {
    const data = await apiClient.put<unknown>(`${DEVICES_BASE_PATH}/${id}/metadata`, payload);
    return metadataResponseSchema.parse(data) as DeviceMetadataResponse;
  }

  /**
   * Partial update of device metadata
   */
  async patchMetadata(id: string, payload: Partial<DeviceMetadata>): Promise<DeviceMetadataResponse> {
    const data = await apiClient.patch<unknown>(`${DEVICES_BASE_PATH}/${id}/metadata`, payload);
    return metadataResponseSchema.parse(data) as DeviceMetadataResponse;
  }

  // ==================== Export / Import ====================

  /**
   * Export devices to JSON
   */
  async export(payload: DeviceExportRequest): Promise<unknown> {
    return apiClient.post<unknown>(`${DEVICES_BASE_PATH}/export`, payload);
  }

  /**
   * Import devices from JSON
   */
  async import(payload: DeviceImportRequest): Promise<DeviceImportResponse> {
    const data = await apiClient.post<unknown>(`${DEVICES_BASE_PATH}/import`, payload);
    return importResponseSchema.parse(data) as DeviceImportResponse;
  }
}

export const deviceService = new DeviceService();

// Export schemas for external use
export {
  deviceSchema,
  deviceSummarySchema,
  deviceListResponseSchema,
  deviceCreateSchema,
  deviceUpdateSchema,
  duplicatePreviewSchema,
  duplicateResponseSchema,
  metadataResponseSchema,
};
