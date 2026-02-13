/**
 * Dataset Hooks
 * React Query hooks for dataset management
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
    DatasetFilters,
    DatasetCreateRequest,
    DatasetUpdateRequest,
    DatasetUploadRequest,
    DatasetGenerateRequest,
} from '@/types/dataset';
import { datasetService } from '@/services/dataset.service';

// ==================== Query Keys ====================

export const datasetKeys = {
    all: ['datasets'] as const,
    list: (filters: DatasetFilters) => [...datasetKeys.all, 'list', filters] as const,
    detail: (id: string) => [...datasetKeys.all, 'detail', id] as const,
    preview: (id: string, limit?: number) => [...datasetKeys.all, 'preview', id, limit] as const,
    generators: ['datasets', 'generators'] as const,
    statistics: ['datasets', 'statistics'] as const,
};

// ==================== Query Hooks ====================

/**
 * Hook to fetch datasets list with filtering and pagination
 */
export function useDatasets(filters: DatasetFilters = {}) {
    return useQuery({
        queryKey: datasetKeys.list(filters),
        queryFn: () => datasetService.list(filters),
        staleTime: 30_000, // 30 seconds
    });
}

/**
 * Hook to fetch a single dataset by ID
 */
export function useDataset(id: string) {
    return useQuery({
        queryKey: datasetKeys.detail(id),
        queryFn: () => datasetService.getById(id),
        enabled: !!id,
    });
}

/**
 * Hook to fetch dataset preview with sample data
 */
export function useDatasetPreview(id: string, limit: number = 50) {
    return useQuery({
        queryKey: datasetKeys.preview(id, limit),
        queryFn: () => datasetService.getPreview(id, limit),
        enabled: !!id,
        staleTime: 60_000, // 1 minute
    });
}

/**
 * Hook to fetch available generator types
 */
export function useGeneratorTypes() {
    return useQuery({
        queryKey: datasetKeys.generators,
        queryFn: () => datasetService.getGenerators(),
        staleTime: Infinity, // Generator types rarely change
    });
}

/**
 * Hook to fetch dataset statistics
 */
export function useDatasetStatistics() {
    return useQuery({
        queryKey: datasetKeys.statistics,
        queryFn: () => datasetService.getStatistics(),
        staleTime: 60_000, // 1 minute
    });
}

// ==================== Mutation Hooks ====================

/**
 * Hook to create a new dataset (manual creation)
 */
export function useCreateDataset() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: DatasetCreateRequest) => datasetService.create(payload),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: datasetKeys.all });
        },
    });
}

/**
 * Hook to update dataset metadata
 */
export function useUpdateDataset() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, payload }: { id: string; payload: DatasetUpdateRequest }) =>
            datasetService.update(id, payload),
        onSuccess: async (_data, variables) => {
            await queryClient.invalidateQueries({ queryKey: datasetKeys.all });
            await queryClient.invalidateQueries({ queryKey: datasetKeys.detail(variables.id) });
        },
    });
}

/**
 * Hook to delete a dataset
 */
export function useDeleteDataset() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, hardDelete }: { id: string; hardDelete?: boolean }) =>
            datasetService.delete(id, { hardDelete }),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: datasetKeys.all });
        },
    });
}

/**
 * Hook to upload a file and create a dataset
 */
export function useUploadDataset() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ file, metadata }: { file: File; metadata: DatasetUploadRequest }) =>
            datasetService.upload(file, metadata),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: datasetKeys.all });
        },
    });
}

/**
 * Hook to generate a synthetic dataset
 */
export function useGenerateDataset() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: DatasetGenerateRequest) => datasetService.generate(payload),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: datasetKeys.all });
        },
    });
}

/**
 * Hook to validate a dataset
 */
export function useValidateDataset() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => datasetService.validate(id),
        onSuccess: async (_data, id) => {
            await queryClient.invalidateQueries({ queryKey: datasetKeys.detail(id) });
            await queryClient.invalidateQueries({ queryKey: datasetKeys.all });
        },
    });
}

/**
 * Hook to download a dataset file
 */
export function useDownloadDataset() {
    return useMutation({
        mutationFn: async (id: string) => {
            const blob = await datasetService.download(id);
            return { id, blob };
        },
        onSuccess: ({ blob }, id) => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dataset-${id}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        },
    });
}
