/**
 * Dataset Types
 * TypeScript interfaces for dataset management
 */

// ==================== Enums ====================

export type DatasetStatus = 'draft' | 'processing' | 'ready' | 'error';

export type DatasetSource = 'upload' | 'generated' | 'manual' | 'template';

export type GeneratorType = 'temperature' | 'equipment' | 'environmental' | 'fleet' | 'custom';

// ==================== Column Types ====================

export interface DatasetColumn {
    name: string;
    data_type: string;
    position: number;
    nullable: boolean;
    unique_count?: number | null;
    null_count?: number | null;
    min_value?: string | null;
    max_value?: string | null;
    mean_value?: number | null;
    sample_values: unknown[];
}

export interface DatasetColumnCreate {
    name: string;
    data_type: string;
    position: number;
    nullable?: boolean;
}

// ==================== Dataset Types ====================

export interface Dataset {
    id: string;
    name: string;
    description?: string | null;
    source: DatasetSource;
    status: DatasetStatus;
    file_format?: string | null;
    file_size?: number | null;
    row_count: number;
    column_count: number;
    tags: string[];
    metadata?: Record<string, unknown>;
    completeness_score?: number | null;
    validation_status: string;
    generator_type?: string | null;
    columns: DatasetColumn[];
    created_at: string;
    updated_at: string;
}

export interface DatasetSummary {
    id: string;
    name: string;
    description?: string | null;
    source: DatasetSource;
    status: DatasetStatus;
    file_format?: string | null;
    row_count: number;
    column_count: number;
    tags: string[];
    completeness_score?: number | null;
    created_at: string;
    updated_at: string;
}

// ==================== Request Types ====================

export interface DatasetCreateRequest {
    name: string;
    description?: string;
    source: DatasetSource;
    tags?: string[];
    metadata?: Record<string, unknown>;
    columns?: DatasetColumnCreate[];
}

export interface DatasetUpdateRequest {
    name?: string;
    description?: string | null;
    tags?: string[];
    metadata?: Record<string, unknown>;
}

export interface DatasetUploadRequest {
    name: string;
    description?: string;
    tags?: string[];
    has_header?: boolean;
    delimiter?: string;
    encoding?: string;
}

export interface DatasetGenerateRequest {
    name: string;
    description?: string;
    generator_type: GeneratorType;
    generator_config: Record<string, unknown>;
    tags?: string[];
}

// ==================== Generator Config Types ====================

export interface TemperatureGeneratorConfig {
    sensor_count: number;
    duration_days: number;
    base_temperature?: number;
    variation_range?: number;
    seasonal_pattern?: boolean;
    noise_level?: number;
    sampling_interval?: number;
}

export interface EquipmentGeneratorConfig {
    equipment_types: string[];
    equipment_count: number;
    operational_hours?: number;
    maintenance_cycles?: number;
    failure_probability?: number;
    performance_degradation?: boolean;
}

export interface EnvironmentalGeneratorConfig {
    location_count: number;
    parameters: string[];
    measurement_frequency?: number;
    weather_correlation?: boolean;
    pollution_events?: boolean;
    seasonal_effects?: boolean;
}

export interface FleetGeneratorConfig {
    vehicle_count: number;
    route_complexity?: 'simple' | 'moderate' | 'complex';
    tracking_interval?: number;
    fuel_efficiency_variation?: number;
    maintenance_tracking?: boolean;
    driver_behavior_patterns?: boolean;
}

// ==================== Response Types ====================

export interface DatasetListResponse {
    items: DatasetSummary[];
    total: number;
    skip: number;
    limit: number;
    has_next: boolean;
    has_prev: boolean;
}

// ==================== Preview Types ====================

export interface ColumnStatistics {
    name: string;
    data_type: string;
    total_count: number;
    null_count: number;
    unique_count: number;
    min_value?: unknown;
    max_value?: unknown;
    mean_value?: number | null;
    median_value?: number | null;
    std_value?: number | null;
}

export interface DatasetPreview {
    columns: DatasetColumn[];
    data: Record<string, unknown>[];
    total_rows: number;
    preview_rows: number;
    statistics: ColumnStatistics[];
}

// ==================== Validation Types ====================

export interface DatasetValidationResult {
    is_valid: boolean;
    completeness_score: number;
    error_count: number;
    warning_count: number;
    errors: Record<string, unknown>[];
    warnings: Record<string, unknown>[];
}

// ==================== Generator Info Types ====================

export interface GeneratorInfo {
    id: string;
    name: string;
    description: string;
    config_schema: Record<string, unknown>;
    example_config: Record<string, unknown>;
    output_columns: string[];
}

// ==================== Filter Types ====================

export interface DatasetFilters {
    search?: string;
    source?: DatasetSource;
    status?: DatasetStatus;
    tags?: string[];
    file_format?: string;
    min_rows?: number;
    max_rows?: number;
    created_after?: string;
    created_before?: string;
    skip?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
}

// ==================== Statistics Types ====================

export interface DatasetStatistics {
    total: number;
    by_source: Record<string, number>;
    by_status: Record<string, number>;
    total_rows: number;
    total_size_bytes: number;
}
