/**
 * Dataset Store
 * Zustand store for dataset UI state management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

import type { DatasetFilters, DatasetSource, DatasetStatus } from '@/types/dataset';

// ==================== State Interface ====================

export interface DatasetState {
    // View mode
    viewMode: 'grid' | 'table';

    // Filters
    filters: DatasetFilters;

    // Selection state
    selectedIds: string[];

    // Dialog states
    isCreateDialogOpen: boolean;
    isUploadDialogOpen: boolean;
    isGenerateDialogOpen: boolean;
    isPreviewDialogOpen: boolean;
    isDeleteDialogOpen: boolean;

    // Current dataset for dialogs
    currentDatasetId: string | null;

    // Upload progress
    uploadProgress: number;
    isUploading: boolean;
}

// ==================== Actions Interface ====================

export interface DatasetActions {
    // View mode
    setViewMode: (mode: 'grid' | 'table') => void;

    // Filters
    setFilters: (filters: Partial<DatasetFilters>) => void;
    resetFilters: () => void;
    setSearch: (search: string) => void;
    setSourceFilter: (source: DatasetSource | undefined) => void;
    setStatusFilter: (status: DatasetStatus | undefined) => void;
    setTagsFilter: (tags: string[]) => void;
    setPagination: (skip: number, limit: number) => void;
    setSorting: (sortBy: string, sortOrder: 'asc' | 'desc') => void;

    // Selection
    selectDataset: (id: string) => void;
    deselectDataset: (id: string) => void;
    selectAllDatasets: (ids: string[]) => void;
    clearSelection: () => void;
    toggleSelection: (id: string) => void;

    // Dialog controls
    openCreateDialog: () => void;
    closeCreateDialog: () => void;
    openUploadDialog: () => void;
    closeUploadDialog: () => void;
    openGenerateDialog: () => void;
    closeGenerateDialog: () => void;
    openPreviewDialog: (datasetId: string) => void;
    closePreviewDialog: () => void;
    openDeleteDialog: (datasetId: string) => void;
    closeDeleteDialog: () => void;
    closeAllDialogs: () => void;

    // Upload progress
    setUploadProgress: (progress: number) => void;
    setUploading: (uploading: boolean) => void;
    resetUploadState: () => void;

    // Reset store
    reset: () => void;
}

// Combined type
export type DatasetStore = DatasetState & DatasetActions;

// ==================== Default State ====================

const defaultFilters: DatasetFilters = {
    search: undefined,
    source: undefined,
    status: undefined,
    tags: undefined,
    file_format: undefined,
    min_rows: undefined,
    max_rows: undefined,
    skip: 0,
    limit: 20,
    sort_by: 'created_at',
    sort_order: 'desc',
};

const defaultState: DatasetState = {
    viewMode: 'grid',
    filters: defaultFilters,
    selectedIds: [],
    isCreateDialogOpen: false,
    isUploadDialogOpen: false,
    isGenerateDialogOpen: false,
    isPreviewDialogOpen: false,
    isDeleteDialogOpen: false,
    currentDatasetId: null,
    uploadProgress: 0,
    isUploading: false,
};

// ==================== Store Creation ====================

export const useDatasetStore = create<DatasetStore>()(
    devtools(
        persist(
            immer((set) => ({
                ...defaultState,

                // View mode
                setViewMode: (mode) => {
                    set((state) => {
                        state.viewMode = mode;
                    });
                },

                // Filters
                setFilters: (newFilters) => {
                    set((state) => {
                        state.filters = { ...state.filters, ...newFilters };
                    });
                },

                resetFilters: () => {
                    set((state) => {
                        state.filters = defaultFilters;
                    });
                },

                setSearch: (search) => {
                    set((state) => {
                        state.filters.search = search || undefined;
                        state.filters.skip = 0; // Reset pagination on search
                    });
                },

                setSourceFilter: (source) => {
                    set((state) => {
                        state.filters.source = source;
                        state.filters.skip = 0;
                    });
                },

                setStatusFilter: (status) => {
                    set((state) => {
                        state.filters.status = status;
                        state.filters.skip = 0;
                    });
                },

                setTagsFilter: (tags) => {
                    set((state) => {
                        state.filters.tags = tags.length > 0 ? tags : undefined;
                        state.filters.skip = 0;
                    });
                },

                setPagination: (skip, limit) => {
                    set((state) => {
                        state.filters.skip = skip;
                        state.filters.limit = limit;
                    });
                },

                setSorting: (sortBy, sortOrder) => {
                    set((state) => {
                        state.filters.sort_by = sortBy;
                        state.filters.sort_order = sortOrder;
                    });
                },

                // Selection
                selectDataset: (id) => {
                    set((state) => {
                        if (!state.selectedIds.includes(id)) {
                            state.selectedIds.push(id);
                        }
                    });
                },

                deselectDataset: (id) => {
                    set((state) => {
                        state.selectedIds = state.selectedIds.filter((i) => i !== id);
                    });
                },

                selectAllDatasets: (ids) => {
                    set((state) => {
                        state.selectedIds = ids;
                    });
                },

                clearSelection: () => {
                    set((state) => {
                        state.selectedIds = [];
                    });
                },

                toggleSelection: (id) => {
                    set((state) => {
                        if (state.selectedIds.includes(id)) {
                            state.selectedIds = state.selectedIds.filter((i) => i !== id);
                        } else {
                            state.selectedIds.push(id);
                        }
                    });
                },

                // Dialog controls
                openCreateDialog: () => {
                    set((state) => {
                        state.isCreateDialogOpen = true;
                    });
                },

                closeCreateDialog: () => {
                    set((state) => {
                        state.isCreateDialogOpen = false;
                    });
                },

                openUploadDialog: () => {
                    set((state) => {
                        state.isUploadDialogOpen = true;
                    });
                },

                closeUploadDialog: () => {
                    set((state) => {
                        state.isUploadDialogOpen = false;
                        state.uploadProgress = 0;
                        state.isUploading = false;
                    });
                },

                openGenerateDialog: () => {
                    set((state) => {
                        state.isGenerateDialogOpen = true;
                    });
                },

                closeGenerateDialog: () => {
                    set((state) => {
                        state.isGenerateDialogOpen = false;
                    });
                },

                openPreviewDialog: (datasetId) => {
                    set((state) => {
                        state.isPreviewDialogOpen = true;
                        state.currentDatasetId = datasetId;
                    });
                },

                closePreviewDialog: () => {
                    set((state) => {
                        state.isPreviewDialogOpen = false;
                        state.currentDatasetId = null;
                    });
                },

                openDeleteDialog: (datasetId) => {
                    set((state) => {
                        state.isDeleteDialogOpen = true;
                        state.currentDatasetId = datasetId;
                    });
                },

                closeDeleteDialog: () => {
                    set((state) => {
                        state.isDeleteDialogOpen = false;
                        state.currentDatasetId = null;
                    });
                },

                closeAllDialogs: () => {
                    set((state) => {
                        state.isCreateDialogOpen = false;
                        state.isUploadDialogOpen = false;
                        state.isGenerateDialogOpen = false;
                        state.isPreviewDialogOpen = false;
                        state.isDeleteDialogOpen = false;
                        state.currentDatasetId = null;
                    });
                },

                // Upload progress
                setUploadProgress: (progress) => {
                    set((state) => {
                        state.uploadProgress = progress;
                    });
                },

                setUploading: (uploading) => {
                    set((state) => {
                        state.isUploading = uploading;
                    });
                },

                resetUploadState: () => {
                    set((state) => {
                        state.uploadProgress = 0;
                        state.isUploading = false;
                    });
                },

                // Reset store
                reset: () => {
                    set(defaultState);
                },
            })),
            {
                name: 'dataset-store',
                partialize: (state) => ({
                    viewMode: state.viewMode,
                    filters: {
                        limit: state.filters.limit,
                        sort_by: state.filters.sort_by,
                        sort_order: state.filters.sort_order,
                    },
                }),
            }
        ),
        {
            name: 'dataset-store',
        }
    )
);
