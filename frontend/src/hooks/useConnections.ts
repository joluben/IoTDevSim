import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  ConnectionFilters,
  ConnectionCreateRequest,
  ConnectionUpdateRequest,
  ConnectionTestRequest,
  BulkOperationRequest,
  ConnectionExportRequest,
  ConnectionImportRequest,
} from '@/types/connection';
import { connectionService } from '@/services/connection.service';

const connectionKeys = {
  all: ['connections'] as const,
  list: (filters: ConnectionFilters) => [...connectionKeys.all, 'list', filters] as const,
  templates: ['connections', 'templates'] as const,
};

export function useConnections(filters: ConnectionFilters) {
  return useQuery({
    queryKey: connectionKeys.list(filters),
    queryFn: () => connectionService.list(filters),
  });
}

export function useConnectionTemplates() {
  return useQuery({
    queryKey: connectionKeys.templates,
    queryFn: () => connectionService.getTemplates(),
    staleTime: Infinity, // Templates rarely change
  });
}

export function useCreateConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ConnectionCreateRequest) => connectionService.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectionKeys.all });
    },
  });
}

export function useUpdateConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ConnectionUpdateRequest }) =>
      connectionService.update(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectionKeys.all });
    },
  });
}

export function useDeleteConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, hardDelete }: { id: string; hardDelete?: boolean }) =>
      connectionService.delete(id, { hardDelete }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectionKeys.all });
    },
  });
}

export function useTestConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload?: ConnectionTestRequest }) =>
      connectionService.test(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectionKeys.all });
    },
  });
}

export function useBulkOperations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: BulkOperationRequest) => connectionService.bulk(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectionKeys.all });
    },
  });
}

export function useImportConnections() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ConnectionImportRequest) => connectionService.import(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: connectionKeys.all });
    },
  });
}

export function useExportConnections() {
  return useMutation({
    mutationFn: (payload: ConnectionExportRequest) => connectionService.export(payload),
  });
}
