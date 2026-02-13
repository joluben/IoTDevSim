import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  DeviceFilters,
  DeviceCreateRequest,
  DeviceUpdateRequest,
  DeviceDuplicateRequest,
  DeviceDatasetLinkRequest,
  DeviceMetadata,
  DeviceExportRequest,
  DeviceImportRequest,
  DeviceBulkLinkRequest,
} from '@/types/device';
import { deviceService } from '@/services/device.service';

const deviceKeys = {
  all: ['devices'] as const,
  list: (filters: DeviceFilters) => [...deviceKeys.all, 'list', filters] as const,
  detail: (id: string) => [...deviceKeys.all, 'detail', id] as const,
  datasets: (id: string) => [...deviceKeys.all, 'datasets', id] as const,
  metadata: (id: string) => [...deviceKeys.all, 'metadata', id] as const,
};

export function useDevices(filters: DeviceFilters) {
  return useQuery({
    queryKey: deviceKeys.list(filters),
    queryFn: () => deviceService.list(filters),
  });
}

export function useDevice(id: string) {
  return useQuery({
    queryKey: deviceKeys.detail(id),
    queryFn: () => deviceService.getById(id),
    enabled: !!id,
  });
}

export function useCreateDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: DeviceCreateRequest) => deviceService.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function useUpdateDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DeviceUpdateRequest }) =>
      deviceService.update(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function usePatchDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DeviceUpdateRequest }) =>
      deviceService.patch(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function useDeleteDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, hardDelete }: { id: string; hardDelete?: boolean }) =>
      deviceService.delete(id, { hardDelete }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function useDuplicateDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DeviceDuplicateRequest }) =>
      deviceService.duplicate(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function usePreviewDuplicate() {
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DeviceDuplicateRequest }) =>
      deviceService.previewDuplicate(id, payload),
  });
}

// ==================== Dataset Linking ====================

export function useDeviceDatasets(deviceId: string) {
  return useQuery({
    queryKey: deviceKeys.datasets(deviceId),
    queryFn: () => deviceService.getDatasets(deviceId),
    enabled: !!deviceId,
  });
}

export function useLinkDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deviceId, payload }: { deviceId: string; payload: DeviceDatasetLinkRequest }) =>
      deviceService.linkDataset(deviceId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function useUnlinkDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deviceId, datasetId }: { deviceId: string; datasetId: string }) =>
      deviceService.unlinkDataset(deviceId, datasetId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function useBulkLinkDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: DeviceBulkLinkRequest) => deviceService.bulkLinkDataset(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

// ==================== Metadata ====================

export function useDeviceMetadata(deviceId: string) {
  return useQuery({
    queryKey: deviceKeys.metadata(deviceId),
    queryFn: () => deviceService.getMetadata(deviceId),
    enabled: !!deviceId,
  });
}

export function useUpdateDeviceMetadata() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: DeviceMetadata }) =>
      deviceService.updateMetadata(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

export function usePatchDeviceMetadata() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<DeviceMetadata> }) =>
      deviceService.patchMetadata(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}

// ==================== Export / Import ====================

export function useExportDevices() {
  return useMutation({
    mutationFn: (payload: DeviceExportRequest) => deviceService.export(payload),
  });
}

export function useImportDevices() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: DeviceImportRequest) => deviceService.import(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: deviceKeys.all });
    },
  });
}
