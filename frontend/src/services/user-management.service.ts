import { z } from 'zod';

import { apiClient, type ApiError } from '@/services/api.client';
import type {
  ManagedUserCreateRequest,
  ManagedUserCreateResponse,
  ManagedUserDetail,
  ManagedUserFilters,
  ManagedUserListResponse,
  ManagedUserOperationResponse,
  ManagedUserStatusRequest,
  ManagedUserUpdateRequest,
} from '@/types/user-management';

const USERS_BASE_PATH = '/users';

const userGroupSchema = z.enum(['admin', 'user']);

const userListItemSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  full_name: z.string(),
  group: userGroupSchema,
  is_active: z.boolean(),
  is_verified: z.boolean(),
  permissions: z.array(z.string()),
  created_at: z.string(),
  last_login: z.string().nullable().optional(),
});

const userDetailSchema = userListItemSchema.extend({
  roles: z.array(z.string()),
  is_superuser: z.boolean(),
  avatar_url: z.string().nullable().optional(),
  bio: z.string().nullable().optional(),
  external_provider: z.string().nullable().optional(),
  external_subject: z.string().nullable().optional(),
});

const usersListResponseSchema = z.object({
  items: z.array(userListItemSchema),
  total: z.number(),
  skip: z.number(),
  limit: z.number(),
  has_next: z.boolean(),
  has_prev: z.boolean(),
});

const userCreateResponseSchema = z.object({
  user: userDetailSchema,
  message: z.string(),
});

const userCreateSchema = z.object({
  email: z.string().email(),
  full_name: z.string().min(2).max(100),
  group: userGroupSchema,
  permissions: z.array(z.string()),
});

const userUpdateSchema = z
  .object({
    full_name: z.string().min(2).max(100).optional(),
    group: userGroupSchema.optional(),
    permissions: z.array(z.string()).optional(),
    is_active: z.boolean().optional(),
  })
  .refine((data) => Object.keys(data).length > 0, {
    message: 'At least one field is required for update',
  });

const userStatusSchema = z.object({
  is_active: z.boolean(),
});

function buildQueryParams(filters: ManagedUserFilters): Record<string, string | number | boolean> {
  const params: Record<string, string | number | boolean> = {};

  if (filters.search) params.search = filters.search;
  if (filters.group) params.group = filters.group;
  if (filters.is_active !== undefined) params.is_active = filters.is_active;
  if (filters.skip !== undefined) params.skip = filters.skip;
  if (filters.limit !== undefined) params.limit = filters.limit;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.sort_order) params.sort_order = filters.sort_order;

  return params;
}

function parseApiError(error: unknown): Error {
  const apiError = error as ApiError;
  const message =
    typeof apiError?.message === 'string' && apiError.message.trim().length > 0
      ? apiError.message
      : 'Unexpected error';
  const enrichedError = new Error(message) as Error & {
    status?: number;
    code?: string;
    details?: unknown;
  };
  enrichedError.status = apiError?.status;
  enrichedError.code = apiError?.code;
  enrichedError.details = apiError?.details;
  return enrichedError;
}

class UserManagementService {
  async list(filters: ManagedUserFilters = {}): Promise<ManagedUserListResponse> {
    try {
      const data = await apiClient.get<unknown>(USERS_BASE_PATH, {
        params: buildQueryParams(filters),
      });
      return usersListResponseSchema.parse(data) as ManagedUserListResponse;
    } catch (error) {
      throw parseApiError(error);
    }
  }

  async restore(payload: ManagedUserCreateRequest): Promise<ManagedUserCreateResponse> {
    try {
      const validated = userCreateSchema.parse(payload);
      const data = await apiClient.post<unknown>(`${USERS_BASE_PATH}/restore`, validated);
      return userCreateResponseSchema.parse(data) as ManagedUserCreateResponse;
    } catch (error) {
      throw parseApiError(error);
    }
  }

  async getById(id: string): Promise<ManagedUserDetail> {
    try {
      const data = await apiClient.get<unknown>(`${USERS_BASE_PATH}/${id}`);
      return userDetailSchema.parse(data) as ManagedUserDetail;
    } catch (error) {
      throw parseApiError(error);
    }
  }

  async create(payload: ManagedUserCreateRequest): Promise<ManagedUserCreateResponse> {
    try {
      const validated = userCreateSchema.parse(payload);
      const data = await apiClient.post<unknown>(`${USERS_BASE_PATH}/`, validated);
      return userCreateResponseSchema.parse(data) as ManagedUserCreateResponse;
    } catch (error) {
      throw parseApiError(error);
    }
  }

  async update(id: string, payload: ManagedUserUpdateRequest): Promise<ManagedUserDetail> {
    try {
      const validated = userUpdateSchema.parse(payload);
      const data = await apiClient.patch<unknown>(`${USERS_BASE_PATH}/${id}`, validated);
      return userDetailSchema.parse(data) as ManagedUserDetail;
    } catch (error) {
      throw parseApiError(error);
    }
  }

  async updateStatus(id: string, payload: ManagedUserStatusRequest): Promise<ManagedUserDetail> {
    try {
      const validated = userStatusSchema.parse(payload);
      const data = await apiClient.patch<unknown>(`${USERS_BASE_PATH}/${id}/status`, validated);
      return userDetailSchema.parse(data) as ManagedUserDetail;
    } catch (error) {
      throw parseApiError(error);
    }
  }

  async delete(id: string): Promise<void> {
    try {
      await apiClient.delete(`${USERS_BASE_PATH}/${id}`);
    } catch (error) {
      throw parseApiError(error);
    }
  }

  async resetPassword(id: string): Promise<ManagedUserOperationResponse> {
    try {
      return await apiClient.post<ManagedUserOperationResponse>(`${USERS_BASE_PATH}/${id}/reset-password`);
    } catch (error) {
      throw parseApiError(error);
    }
  }
}

export const userManagementService = new UserManagementService();
