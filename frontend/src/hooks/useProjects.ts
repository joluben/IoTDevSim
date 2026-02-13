import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  ProjectFilters,
  ProjectCreateRequest,
  ProjectUpdateRequest,
  ProjectDeviceAssignRequest,
  ProjectTransmissionRequest,
  TransmissionHistoryFilters,
} from '@/types/project';
import { projectService } from '@/services/project.service';

const projectKeys = {
  all: ['projects'] as const,
  list: (filters: ProjectFilters) => [...projectKeys.all, 'list', filters] as const,
  detail: (id: string) => [...projectKeys.all, 'detail', id] as const,
  devices: (id: string) => [...projectKeys.all, 'devices', id] as const,
  unassigned: (params?: { search?: string; skip?: number; limit?: number }) =>
    [...projectKeys.all, 'unassigned', params] as const,
  stats: (id: string) => [...projectKeys.all, 'stats', id] as const,
  history: (id: string, filters: TransmissionHistoryFilters) =>
    [...projectKeys.all, 'history', id, filters] as const,
};

// ==================== CRUD ====================

export function useProjects(filters: ProjectFilters) {
  return useQuery({
    queryKey: projectKeys.list(filters),
    queryFn: () => projectService.list(filters),
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => projectService.getById(id),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProjectCreateRequest) => projectService.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ProjectUpdateRequest }) =>
      projectService.update(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function usePatchProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ProjectUpdateRequest }) =>
      projectService.patch(id, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => projectService.delete(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

// ==================== Archive ====================

export function useArchiveProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => projectService.archive(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useUnarchiveProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => projectService.unarchive(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

// ==================== Device Assignment ====================

export function useProjectDevices(projectId: string) {
  return useQuery({
    queryKey: projectKeys.devices(projectId),
    queryFn: () => projectService.getDevices(projectId),
    enabled: !!projectId,
  });
}

export function useUnassignedDevices(params?: { search?: string; skip?: number; limit?: number }) {
  return useQuery({
    queryKey: projectKeys.unassigned(params),
    queryFn: () => projectService.getUnassignedDevices(params),
  });
}

export function useAssignDevices() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, payload }: { projectId: string; payload: ProjectDeviceAssignRequest }) =>
      projectService.assignDevices(projectId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useUnassignDevice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, deviceId }: { projectId: string; deviceId: string }) =>
      projectService.unassignDevice(projectId, deviceId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

// ==================== Transmission Control ====================

export function useStartTransmissions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, payload }: { projectId: string; payload?: ProjectTransmissionRequest }) =>
      projectService.startTransmissions(projectId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function usePauseTransmissions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => projectService.pauseTransmissions(projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useResumeTransmissions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => projectService.resumeTransmissions(projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

export function useStopTransmissions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => projectService.stopTransmissions(projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
    },
  });
}

// ==================== Stats & History ====================

export function useProjectStats(projectId: string) {
  return useQuery({
    queryKey: projectKeys.stats(projectId),
    queryFn: () => projectService.getStats(projectId),
    enabled: !!projectId,
    refetchInterval: 5000, // Poll every 5 seconds for real-time updates
    refetchIntervalInBackground: false,
  });
}

export function useProjectHistory(projectId: string, filters: TransmissionHistoryFilters = {}, enabled: boolean = true) {
  return useQuery({
    queryKey: projectKeys.history(projectId, filters),
    queryFn: () => projectService.getHistory(projectId, filters),
    enabled: !!projectId && enabled,
    refetchInterval: 5000, // Poll every 5 seconds for real-time updates
    refetchIntervalInBackground: false,
  });
}

export function useExportHistory() {
  return useMutation({
    mutationFn: ({ projectId, filters }: { projectId: string; filters?: { device_id?: string; status?: string } }) =>
      projectService.exportHistory(projectId, filters),
  });
}

export function useClearProjectLogs() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => projectService.clearLogs(projectId),
    onSuccess: async (_, projectId) => {
      // Invalidate history and stats queries after clearing logs
      await queryClient.invalidateQueries({ queryKey: projectKeys.history(projectId, {}) });
      await queryClient.invalidateQueries({ queryKey: projectKeys.stats(projectId) });
    },
  });
}

export { projectKeys };
