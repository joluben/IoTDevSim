/**
 * Dataset Service
 * API client for dataset management operations
 */

import { z } from 'zod';

import { apiClient } from '@/services/api.client';
import type {
    Dataset,
    DatasetSummary,
    DatasetCreateRequest,
    DatasetUpdateRequest,
    DatasetUploadRequest,
    DatasetGenerateRequest,
    DatasetListResponse,
    DatasetPreview,
    DatasetValidationResult,
    DatasetFilters,
    GeneratorInfo,
    DatasetStatistics,
} from '@/types/dataset';

const DATASETS_BASE_PATH = '/datasets';

// ==================== Zod Schemas ====================

const datasetColumnSchema = z.object({
    name: z.string(),
    data_type: z.string(),
    position: z.number(),
    nullable: z.boolean(),
    unique_count: z.number().nullable().optional(),
    null_count: z.number().nullable().optional(),
    min_value: z.string().nullable().optional(),
    max_value: z.string().nullable().optional(),
    mean_value: z.number().nullable().optional(),
    sample_values: z.array(z.unknown()),
});

const datasetSchema = z.object({
    id: z.string().uuid(),
    name: z.string(),
    description: z.string().nullable().optional(),
    source: z.enum(['upload', 'generated', 'manual', 'template']),
    status: z.enum(['draft', 'processing', 'ready', 'error']),
    file_format: z.string().nullable().optional(),
    file_size: z.number().nullable().optional(),
    row_count: z.number(),
    column_count: z.number(),
    tags: z.array(z.string()),
    metadata: z.record(z.string(), z.unknown()).optional(),
    completeness_score: z.number().nullable().optional(),
    validation_status: z.string(),
    generator_type: z.string().nullable().optional(),
    columns: z.array(datasetColumnSchema),
    created_at: z.string(),
    updated_at: z.string(),
});

const datasetSummarySchema = z.object({
    id: z.string().uuid(),
    name: z.string(),
    description: z.string().nullable().optional(),
    source: z.enum(['upload', 'generated', 'manual', 'template']),
    status: z.enum(['draft', 'processing', 'ready', 'error']),
    file_format: z.string().nullable().optional(),
    row_count: z.number(),
    column_count: z.number(),
    tags: z.array(z.string()),
    completeness_score: z.number().nullable().optional(),
    created_at: z.string(),
    updated_at: z.string(),
});

const datasetListResponseSchema = z.object({
    items: z.array(datasetSummarySchema),
    total: z.number(),
    skip: z.number(),
    limit: z.number(),
    has_next: z.boolean(),
    has_prev: z.boolean(),
});

const datasetCreateSchema = z.object({
    name: z.string().min(1).max(255),
    description: z.string().max(2000).optional(),
    source: z.enum(['upload', 'generated', 'manual', 'template']),
    tags: z.array(z.string()).optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
    columns: z.array(z.object({
        name: z.string(),
        data_type: z.string(),
        position: z.number(),
        nullable: z.boolean().optional(),
    })).optional(),
});

const datasetUpdateSchema = z.object({
    name: z.string().min(1).max(255).optional(),
    description: z.string().max(2000).nullable().optional(),
    tags: z.array(z.string()).optional(),
    metadata: z.record(z.string(), z.unknown()).optional(),
});

const datasetGenerateSchema = z.object({
    name: z.string().min(1).max(255),
    description: z.string().max(2000).optional(),
    generator_type: z.enum(['temperature', 'equipment', 'environmental', 'fleet', 'custom']),
    generator_config: z.record(z.string(), z.unknown()),
    tags: z.array(z.string()).optional(),
});

const datasetPreviewSchema = z.object({
    columns: z.array(datasetColumnSchema),
    data: z.array(z.record(z.string(), z.unknown())),
    total_rows: z.number(),
    preview_rows: z.number(),
    statistics: z.array(z.object({
        name: z.string(),
        data_type: z.string(),
        total_count: z.number(),
        null_count: z.number(),
        unique_count: z.number(),
        min_value: z.unknown().optional(),
        max_value: z.unknown().optional(),
        mean_value: z.number().nullable().optional(),
        median_value: z.number().nullable().optional(),
        std_value: z.number().nullable().optional(),
    })),
});

const datasetValidationResultSchema = z.object({
    is_valid: z.boolean(),
    completeness_score: z.number(),
    error_count: z.number(),
    warning_count: z.number(),
    errors: z.array(z.record(z.string(), z.unknown())),
    warnings: z.array(z.record(z.string(), z.unknown())),
});

const generatorInfoSchema = z.object({
    id: z.string(),
    name: z.string(),
    description: z.string(),
    config_schema: z.record(z.string(), z.unknown()),
    example_config: z.record(z.string(), z.unknown()),
    output_columns: z.array(z.string()),
});

const datasetStatisticsSchema = z.object({
    total: z.number(),
    by_source: z.record(z.string(), z.number()),
    by_status: z.record(z.string(), z.number()),
    total_rows: z.number(),
    total_size_bytes: z.number(),
});

// ==================== Helper Functions ====================

function buildQueryParams(filters: DatasetFilters): Record<string, string | number | boolean> {
    const params: Record<string, string | number | boolean> = {};

    if (filters.search) params.search = filters.search;
    if (filters.source) params.source = filters.source;
    if (filters.status) params.status = filters.status;
    if (filters.tags && filters.tags.length > 0) params.tags = filters.tags.join(',');
    if (filters.file_format) params.file_format = filters.file_format;
    if (filters.min_rows !== undefined) params.min_rows = filters.min_rows;
    if (filters.max_rows !== undefined) params.max_rows = filters.max_rows;
    if (filters.created_after) params.created_after = filters.created_after;
    if (filters.created_before) params.created_before = filters.created_before;
    if (filters.skip !== undefined) params.skip = filters.skip;
    if (filters.limit !== undefined) params.limit = filters.limit;
    if (filters.sort_by) params.sort_by = filters.sort_by;
    if (filters.sort_order) params.sort_order = filters.sort_order;

    return params;
}

// ==================== Dataset Service Class ====================

class DatasetService {
    /**
     * List datasets with filtering and pagination
     */
    async list(filters: DatasetFilters = {}): Promise<DatasetListResponse> {
        const data = await apiClient.get<unknown>(DATASETS_BASE_PATH, {
            params: buildQueryParams(filters),
        });

        return datasetListResponseSchema.parse(data) as DatasetListResponse;
    }

    /**
     * Get dataset by ID
     */
    async getById(id: string): Promise<Dataset> {
        const data = await apiClient.get<unknown>(`${DATASETS_BASE_PATH}/${id}`);
        return datasetSchema.parse(data) as Dataset;
    }

    /**
     * Create a new dataset (manual creation)
     */
    async create(payload: DatasetCreateRequest): Promise<Dataset> {
        const validated = datasetCreateSchema.parse(payload);
        const data = await apiClient.post<unknown>(DATASETS_BASE_PATH, validated);
        return datasetSchema.parse(data) as Dataset;
    }

    /**
     * Update dataset metadata
     */
    async update(id: string, payload: DatasetUpdateRequest): Promise<Dataset> {
        const validated = datasetUpdateSchema.parse(payload);
        const data = await apiClient.put<unknown>(`${DATASETS_BASE_PATH}/${id}`, validated);
        return datasetSchema.parse(data) as Dataset;
    }

    /**
     * Delete dataset
     */
    async delete(id: string, options?: { hardDelete?: boolean }): Promise<{ message: string }> {
        const hardDelete = options?.hardDelete ?? false;
        const data = await apiClient.delete<unknown>(`${DATASETS_BASE_PATH}/${id}`, {
            params: { hard_delete: hardDelete },
        });
        return data as { message: string };
    }

    /**
     * Upload file to create dataset
     */
    async upload(file: File, metadata: DatasetUploadRequest): Promise<Dataset> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('name', metadata.name);
        if (metadata.description) formData.append('description', metadata.description);
        formData.append('tags', JSON.stringify(metadata.tags || []));
        formData.append('has_header', String(metadata.has_header ?? true));
        formData.append('delimiter', metadata.delimiter || ',');
        formData.append('encoding', metadata.encoding || 'utf-8');

        const data = await apiClient.post<unknown>(`${DATASETS_BASE_PATH}/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });

        return datasetSchema.parse(data) as Dataset;
    }

    /**
     * Generate synthetic dataset
     */
    async generate(payload: DatasetGenerateRequest): Promise<Dataset> {
        const validated = datasetGenerateSchema.parse(payload);
        const data = await apiClient.post<unknown>(`${DATASETS_BASE_PATH}/generate`, validated);
        return datasetSchema.parse(data) as Dataset;
    }

    /**
     * Get dataset preview with sample data
     */
    async getPreview(id: string, limit: number = 50): Promise<DatasetPreview> {
        const data = await apiClient.get<unknown>(`${DATASETS_BASE_PATH}/${id}/preview`, {
            params: { limit },
        });
        return datasetPreviewSchema.parse(data) as DatasetPreview;
    }

    /**
     * Validate dataset
     */
    async validate(id: string): Promise<DatasetValidationResult> {
        const data = await apiClient.post<unknown>(`${DATASETS_BASE_PATH}/${id}/validate`);
        return datasetValidationResultSchema.parse(data) as DatasetValidationResult;
    }

    /**
     * Download dataset file
     */
    async download(id: string): Promise<Blob> {
        const response = await apiClient.get<Blob>(`${DATASETS_BASE_PATH}/${id}/download`, {
            responseType: 'blob',
        });
        return response;
    }

    /**
     * Get available generator types
     */
    async getGenerators(): Promise<GeneratorInfo[]> {
        const data = await apiClient.get<unknown>(`${DATASETS_BASE_PATH}/generators`);
        return z.array(generatorInfoSchema).parse(data) as GeneratorInfo[];
    }

    /**
     * Get dataset statistics
     */
    async getStatistics(): Promise<DatasetStatistics> {
        const data = await apiClient.get<unknown>(`${DATASETS_BASE_PATH}/statistics`);
        return datasetStatisticsSchema.parse(data) as DatasetStatistics;
    }
}

export const datasetService = new DatasetService();

// Export schemas for external use
export {
    datasetSchema,
    datasetSummarySchema,
    datasetListResponseSchema,
    datasetCreateSchema,
    datasetUpdateSchema,
    datasetGenerateSchema,
    datasetPreviewSchema,
    datasetValidationResultSchema,
    generatorInfoSchema,
};
