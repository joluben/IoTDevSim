export type UserGroup = 'admin' | 'user';

export type UserSortOrder = 'asc' | 'desc';

export interface ManagedUserListItem {
  id: string;
  email: string;
  full_name: string;
  group: UserGroup;
  is_active: boolean;
  is_verified: boolean;
  permissions: string[];
  created_at: string;
  last_login?: string | null;
}

export interface ManagedUserDetail extends ManagedUserListItem {
  roles: string[];
  is_superuser: boolean;
  avatar_url?: string | null;
  bio?: string | null;
  external_provider?: string | null;
  external_subject?: string | null;
}

export interface ManagedUserListResponse {
  items: ManagedUserListItem[];
  total: number;
  skip: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ManagedUserFilters {
  search?: string;
  group?: UserGroup;
  is_active?: boolean;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: UserSortOrder;
}

export interface ManagedUserCreateRequest {
  email: string;
  full_name: string;
  group: UserGroup;
  permissions: string[];
}

export interface ManagedUserUpdateRequest {
  full_name?: string;
  group?: UserGroup;
  permissions?: string[];
  is_active?: boolean;
}

export interface ManagedUserStatusRequest {
  is_active: boolean;
}

export interface ManagedUserCreateResponse {
  user: ManagedUserDetail;
  message: string;
}

export interface ManagedUserOperationResponse {
  message: string;
  data?: Record<string, unknown> | null;
  timestamp?: string;
}

export const MANAGED_USER_PERMISSIONS = [
  'connections:read',
  'connections:write',
  'datasets:read',
  'datasets:write',
  'devices:read',
  'devices:write',
  'projects:read',
  'projects:write',
  'users:read',
  'users:write',
] as const;

export type ManagedPermission = (typeof MANAGED_USER_PERMISSIONS)[number];

export type ResourcePermissionMatrix = {
  resource: 'connections' | 'datasets' | 'devices' | 'projects';
  read: boolean;
  write: boolean;
};
