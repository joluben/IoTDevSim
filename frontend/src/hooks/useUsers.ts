import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { userManagementService } from '@/services/user-management.service';
import type {
  ManagedUserCreateRequest,
  ManagedUserFilters,
  ManagedUserStatusRequest,
  ManagedUserUpdateRequest,
} from '@/types/user-management';

export const userKeys = {
  all: ['users'] as const,
  list: (filters: ManagedUserFilters) => [...userKeys.all, 'list', filters] as const,
  detail: (id: string) => [...userKeys.all, 'detail', id] as const,
};

export function useUsersList(filters: ManagedUserFilters) {
  return useQuery({
    queryKey: userKeys.list(filters),
    queryFn: () => userManagementService.list(filters),
  });
}

export function useRestoreUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ManagedUserCreateRequest) => userManagementService.restore(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}

export function useResetUserPassword() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => userManagementService.resetPassword(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}

export function useUserDetail(id: string) {
  return useQuery({
    queryKey: userKeys.detail(id),
    queryFn: () => userManagementService.getById(id),
    enabled: !!id,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ManagedUserCreateRequest) => userManagementService.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ManagedUserUpdateRequest }) =>
      userManagementService.update(id, payload),
    onSuccess: async (_, vars) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: userKeys.all }),
        queryClient.invalidateQueries({ queryKey: userKeys.detail(vars.id) }),
      ]);
    },
  });
}

export function useToggleUserStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ManagedUserStatusRequest }) =>
      userManagementService.updateStatus(id, payload),
    onSuccess: async (_, vars) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: userKeys.all }),
        queryClient.invalidateQueries({ queryKey: userKeys.detail(vars.id) }),
      ]);
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => userManagementService.delete(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: userKeys.all });
    },
  });
}
