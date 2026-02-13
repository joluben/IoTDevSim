/**
 * Project Service
 * API client for project management operations
 */

import { z } from 'zod';

import { apiClient } from '@/services/api.client';
import type {
  Project,
  ProjectSummary,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  ProjectListResponse,
  ProjectFilters,
  ProjectDevicesResponse,
  ProjectDeviceAssignRequest,
  ProjectTransmissionRequest,
  ProjectTransmissionResult,
  ProjectStats,
  TransmissionHistoryResponse,
  TransmissionHistoryFilters,
  ProjectDevice,
} from '@/types/project';

const PROJECTS_BASE_PATH = '/projects';

// ==================== Zod Schemas ====================

const projectSummarySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable().optional(),
  is_active: z.boolean(),
  transmission_status: z.enum(['inactive', 'active', 'paused']),
  tags: z.array(z.string()),
  device_count: z.number(),
  is_archived: z.boolean(),
  connection_id: z.string().uuid().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

const projectSchema = projectSummarySchema.extend({
  auto_reset_counter: z.boolean(),
  max_devices: z.number(),
  archived_at: z.string().nullable().optional(),
  owner_id: z.string().uuid().nullable().optional(),
});

const projectListResponseSchema = z.object({
  items: z.array(projectSummarySchema),
  total: z.number(),
  skip: z.number(),
  limit: z.number(),
  has_next: z.boolean(),
  has_prev: z.boolean(),
});

const transmissionResultSchema = z.object({
  project_id: z.string(),
  operation: z.string(),
  transmission_status: z.string(),
  total_devices: z.number(),
  success_count: z.number(),
  failure_count: z.number(),
  results: z.array(z.object({
    device_id: z.string(),
    device_name: z.string(),
    success: z.boolean(),
    message: z.string(),
  })),
});

const projectStatsSchema = z.object({
  project_id: z.string(),
  total_devices: z.number(),
  total_transmissions: z.number(),
  successful_transmissions: z.number(),
  failed_transmissions: z.number(),
  success_rate: z.number(),
});

// ==================== Helper ====================

function buildQueryParams(filters: ProjectFilters): Record<string, string | number | boolean> {
  const params: Record<string, string | number | boolean> = {};

  if (filters.search) params.search = filters.search;
  if (filters.is_active !== undefined) params.is_active = filters.is_active;
  if (filters.transmission_status) params.transmission_status = filters.transmission_status;
  if (filters.is_archived !== undefined) params.is_archived = filters.is_archived;
  if (filters.tags && filters.tags.length > 0) params.tags = filters.tags.join(',');
  if (filters.skip !== undefined) params.skip = filters.skip;
  if (filters.limit !== undefined) params.limit = filters.limit;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.sort_order) params.sort_order = filters.sort_order;

  return params;
}

// ==================== Service Class ====================

class ProjectService {
  // ── CRUD ──

  async list(filters: ProjectFilters = {}): Promise<ProjectListResponse> {
    const data = await apiClient.get<unknown>(PROJECTS_BASE_PATH, {
      params: buildQueryParams(filters),
    });
    return projectListResponseSchema.parse(data) as ProjectListResponse;
  }

  async getById(id: string): Promise<Project> {
    const data = await apiClient.get<unknown>(`${PROJECTS_BASE_PATH}/${id}`);
    return projectSchema.parse(data) as Project;
  }

  async create(payload: ProjectCreateRequest): Promise<Project> {
    const data = await apiClient.post<unknown>(PROJECTS_BASE_PATH, payload);
    return projectSchema.parse(data) as Project;
  }

  async update(id: string, payload: ProjectUpdateRequest): Promise<Project> {
    const data = await apiClient.put<unknown>(`${PROJECTS_BASE_PATH}/${id}`, payload);
    return projectSchema.parse(data) as Project;
  }

  async patch(id: string, payload: ProjectUpdateRequest): Promise<Project> {
    const data = await apiClient.patch<unknown>(`${PROJECTS_BASE_PATH}/${id}`, payload);
    return projectSchema.parse(data) as Project;
  }

  async delete(id: string): Promise<{ message: string }> {
    const data = await apiClient.delete<unknown>(`${PROJECTS_BASE_PATH}/${id}`);
    return data as { message: string };
  }

  // ── Archive ──

  async archive(id: string): Promise<Project> {
    const data = await apiClient.post<unknown>(`${PROJECTS_BASE_PATH}/${id}/archive`);
    return projectSchema.parse(data) as Project;
  }

  async unarchive(id: string): Promise<Project> {
    const data = await apiClient.post<unknown>(`${PROJECTS_BASE_PATH}/${id}/unarchive`);
    return projectSchema.parse(data) as Project;
  }

  // ── Device Assignment ──

  async getDevices(projectId: string): Promise<ProjectDevicesResponse> {
    const data = await apiClient.get<unknown>(`${PROJECTS_BASE_PATH}/${projectId}/devices`);
    return data as ProjectDevicesResponse;
  }

  async assignDevices(projectId: string, payload: ProjectDeviceAssignRequest): Promise<unknown> {
    return apiClient.post<unknown>(`${PROJECTS_BASE_PATH}/${projectId}/devices`, payload);
  }

  async unassignDevice(projectId: string, deviceId: string): Promise<unknown> {
    return apiClient.delete<unknown>(`${PROJECTS_BASE_PATH}/${projectId}/devices/${deviceId}`);
  }

  async getUnassignedDevices(params?: { search?: string; skip?: number; limit?: number }) {
    const data = await apiClient.get<unknown>(`${PROJECTS_BASE_PATH}/unassigned-devices`, {
      params: params ?? {},
    });
    return data as { items: ProjectDevice[]; total: number; skip: number; limit: number; has_next: boolean; has_prev: boolean };
  }

  // ── Transmission Control ──

  async startTransmissions(projectId: string, payload?: ProjectTransmissionRequest): Promise<ProjectTransmissionResult> {
    const data = await apiClient.post<unknown>(
      `${PROJECTS_BASE_PATH}/${projectId}/transmissions/start`,
      payload ?? {},
    );
    return transmissionResultSchema.parse(data) as ProjectTransmissionResult;
  }

  async pauseTransmissions(projectId: string): Promise<ProjectTransmissionResult> {
    const data = await apiClient.post<unknown>(
      `${PROJECTS_BASE_PATH}/${projectId}/transmissions/pause`,
    );
    return transmissionResultSchema.parse(data) as ProjectTransmissionResult;
  }

  async resumeTransmissions(projectId: string): Promise<ProjectTransmissionResult> {
    const data = await apiClient.post<unknown>(
      `${PROJECTS_BASE_PATH}/${projectId}/transmissions/resume`,
    );
    return transmissionResultSchema.parse(data) as ProjectTransmissionResult;
  }

  async stopTransmissions(projectId: string): Promise<ProjectTransmissionResult> {
    const data = await apiClient.post<unknown>(
      `${PROJECTS_BASE_PATH}/${projectId}/transmissions/stop`,
    );
    return transmissionResultSchema.parse(data) as ProjectTransmissionResult;
  }

  // ── Stats & History ──

  async getStats(projectId: string): Promise<ProjectStats> {
    const data = await apiClient.get<unknown>(`${PROJECTS_BASE_PATH}/${projectId}/stats`);
    return projectStatsSchema.parse(data) as ProjectStats;
  }

  async getHistory(projectId: string, filters: TransmissionHistoryFilters = {}): Promise<TransmissionHistoryResponse> {
    const params: Record<string, string | number> = {};
    if (filters.device_id) params.device_id = filters.device_id;
    if (filters.status) params.status = filters.status;
    if (filters.skip !== undefined) params.skip = filters.skip;
    if (filters.limit !== undefined) params.limit = filters.limit;

    const data = await apiClient.get<unknown>(`${PROJECTS_BASE_PATH}/${projectId}/history`, { params });
    return data as TransmissionHistoryResponse;
  }

  async exportHistory(projectId: string, filters?: { device_id?: string; status?: string }): Promise<Blob> {
    const params: Record<string, string> = {};
    if (filters?.device_id) params.device_id = filters.device_id;
    if (filters?.status) params.status = filters.status;

    const data = await apiClient.get<Blob>(`${PROJECTS_BASE_PATH}/${projectId}/history/export`, {
      params,
      responseType: 'blob',
    } as any);
    return data;
  }

  async clearLogs(projectId: string): Promise<{ success: boolean; message: string; data: { deleted_count: number } }> {
    const data = await apiClient.delete<unknown>(`${PROJECTS_BASE_PATH}/${projectId}/logs`);
    return data as { success: boolean; message: string; data: { deleted_count: number } };
  }
}

export const projectService = new ProjectService();

export {
  projectSchema,
  projectSummarySchema,
  projectListResponseSchema,
  transmissionResultSchema,
  projectStatsSchema,
};
