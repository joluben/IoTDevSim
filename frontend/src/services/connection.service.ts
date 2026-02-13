import { z } from 'zod';

import { apiClient } from '@/services/api.client';
import type {
  Connection,
  ConnectionCreateRequest,
  ConnectionFilters,
  ConnectionListResponse,
  ConnectionTestRequest,
  ConnectionTestResponse,
  ConnectionUpdateRequest,
} from '@/types/connection';
import {
  connectionCreateSchema,
  connectionListResponseSchema,
  connectionSchema,
  connectionUpdateSchema,
} from '@/features/connections/validation/connection.schemas';

const CONNECTIONS_BASE_PATH = '/connections';

const connectionTestRequestSchema = z
  .object({
    timeout: z.number().int().min(1).max(60).optional(),
  })
  .strict();

const connectionTestResponseSchema = z
  .object({
    success: z.boolean(),
    message: z.string(),
    duration_ms: z.number(),
    timestamp: z.string(),
    details: z.record(z.string(), z.unknown()).optional(),
  })
  .strict();

function buildQueryParams(filters: ConnectionFilters): Record<string, string | number | boolean> {
  const params: Record<string, string | number | boolean> = {};

  if (filters.search) params.search = filters.search;
  if (filters.protocol) params.protocol = filters.protocol;
  if (filters.is_active !== undefined) params.is_active = filters.is_active;
  if (filters.test_status) params.test_status = filters.test_status;
  if (filters.skip !== undefined) params.skip = filters.skip;
  if (filters.limit !== undefined) params.limit = filters.limit;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.sort_order) params.sort_order = filters.sort_order;

  return params;
}

class ConnectionService {
  async list(filters: ConnectionFilters): Promise<ConnectionListResponse> {
    const data = await apiClient.get<unknown>(CONNECTIONS_BASE_PATH, {
      params: buildQueryParams(filters),
    });

    return connectionListResponseSchema.parse(data) as ConnectionListResponse;
  }

  async getById(id: string): Promise<Connection> {
    const data = await apiClient.get<unknown>(`${CONNECTIONS_BASE_PATH}/${id}`);
    return connectionSchema.parse(data) as Connection;
  }

  async create(payload: ConnectionCreateRequest): Promise<Connection> {
    const validated = connectionCreateSchema.parse(payload);
    const data = await apiClient.post<unknown>(CONNECTIONS_BASE_PATH, validated);
    return connectionSchema.parse(data) as Connection;
  }

  async update(id: string, payload: ConnectionUpdateRequest): Promise<Connection> {
    const validated = connectionUpdateSchema.parse(payload);
    const data = await apiClient.put<unknown>(`${CONNECTIONS_BASE_PATH}/${id}`, validated);
    return connectionSchema.parse(data) as Connection;
  }

  async delete(id: string, options?: { hardDelete?: boolean }): Promise<{ message: string } | unknown> {
    const hardDelete = options?.hardDelete ?? false;
    return apiClient.delete<unknown>(`${CONNECTIONS_BASE_PATH}/${id}`, {
      params: { hard_delete: hardDelete },
    });
  }

  async test(id: string, payload?: ConnectionTestRequest): Promise<ConnectionTestResponse> {
    const validated = connectionTestRequestSchema.parse(payload ?? {});
    const data = await apiClient.post<unknown>(`${CONNECTIONS_BASE_PATH}/${id}/test`, validated);
    return connectionTestResponseSchema.parse(data) as ConnectionTestResponse;
  }

  async bulk(payload: import('@/types/connection').BulkOperationRequest): Promise<import('@/types/connection').BulkOperationResponse> {
    const data = await apiClient.post<unknown>(`${CONNECTIONS_BASE_PATH}/bulk`, payload);
    return data as import('@/types/connection').BulkOperationResponse;
  }

  async export(payload: import('@/types/connection').ConnectionExportRequest): Promise<unknown> {
    const data = await apiClient.post<unknown>(`${CONNECTIONS_BASE_PATH}/export`, payload);
    return data;
  }

  async import(payload: import('@/types/connection').ConnectionImportRequest): Promise<import('@/types/connection').BulkOperationResponse> {
    const data = await apiClient.post<unknown>(`${CONNECTIONS_BASE_PATH}/import`, payload);
    return data as import('@/types/connection').BulkOperationResponse;
  }

  async getTemplates(): Promise<import('@/types/connection').ConnectionTemplate[]> {
    const data = await apiClient.get<unknown>(`${CONNECTIONS_BASE_PATH}/templates`);
    return data as import('@/types/connection').ConnectionTemplate[];
  }
}

export const connectionService = new ConnectionService();
