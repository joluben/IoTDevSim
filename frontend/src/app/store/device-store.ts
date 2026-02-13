/**
 * Device Store
 * Zustand store for device UI state management
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

import type { DeviceFilters, DeviceType, DeviceStatus } from '@/types/device';

// ==================== State Interface ====================

export interface DeviceState {
    // View mode
    viewMode: 'grid' | 'table';

    // Filters
    filters: DeviceFilters;

    // Selection state
    selectedIds: string[];

    // Dialog states
    isCreateDialogOpen: boolean;
    isEditDialogOpen: boolean;
    isDuplicateDialogOpen: boolean;
    isDeleteDialogOpen: boolean;
    isLinkDatasetDialogOpen: boolean;
    isMetadataDialogOpen: boolean;
    isExportDialogOpen: boolean;
    isImportDialogOpen: boolean;

    // Current device for dialogs
    currentDeviceId: string | null;
}

// ==================== Actions Interface ====================

export interface DeviceActions {
    // View mode
    setViewMode: (mode: 'grid' | 'table') => void;

    // Filters
    setFilters: (filters: Partial<DeviceFilters>) => void;
    resetFilters: () => void;
    setSearch: (search: string) => void;
    setDeviceTypeFilter: (deviceType: DeviceType | undefined) => void;
    setStatusFilter: (status: DeviceStatus | undefined) => void;
    setActiveFilter: (isActive: boolean | undefined) => void;
    setTransmissionFilter: (enabled: boolean | undefined) => void;
    setDatasetFilter: (hasDataset: boolean | undefined) => void;
    setTagsFilter: (tags: string[]) => void;
    setProjectFilter: (projectId: string | undefined) => void;
    setConnectionFilter: (connectionId: string | undefined) => void;
    setPagination: (skip: number, limit: number) => void;
    setSorting: (sortBy: string, sortOrder: 'asc' | 'desc') => void;

    // Selection
    selectDevice: (id: string) => void;
    deselectDevice: (id: string) => void;
    selectAllDevices: (ids: string[]) => void;
    clearSelection: () => void;
    toggleSelection: (id: string) => void;

    // Dialog controls
    openCreateDialog: () => void;
    closeCreateDialog: () => void;
    openEditDialog: (deviceId: string) => void;
    closeEditDialog: () => void;
    openDuplicateDialog: (deviceId: string) => void;
    closeDuplicateDialog: () => void;
    openDeleteDialog: (deviceId: string) => void;
    closeDeleteDialog: () => void;
    openLinkDatasetDialog: (deviceId: string) => void;
    closeLinkDatasetDialog: () => void;
    openMetadataDialog: (deviceId: string) => void;
    closeMetadataDialog: () => void;
    openExportDialog: () => void;
    closeExportDialog: () => void;
    openImportDialog: () => void;
    closeImportDialog: () => void;
    closeAllDialogs: () => void;

    // Reset store
    reset: () => void;
}

// Combined type
export type DeviceStore = DeviceState & DeviceActions;

// ==================== Default State ====================

const defaultFilters: DeviceFilters = {
    search: undefined,
    device_type: undefined,
    is_active: undefined,
    transmission_enabled: undefined,
    has_dataset: undefined,
    tags: undefined,
    connection_id: undefined,
    project_id: undefined,
    status: undefined,
    skip: 0,
    limit: 20,
    sort_by: 'created_at',
    sort_order: 'desc',
};

const defaultState: DeviceState = {
    viewMode: 'table',
    filters: defaultFilters,
    selectedIds: [],
    isCreateDialogOpen: false,
    isEditDialogOpen: false,
    isDuplicateDialogOpen: false,
    isDeleteDialogOpen: false,
    isLinkDatasetDialogOpen: false,
    isMetadataDialogOpen: false,
    isExportDialogOpen: false,
    isImportDialogOpen: false,
    currentDeviceId: null,
};

// ==================== Store Creation ====================

export const useDeviceStore = create<DeviceStore>()(
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
                        state.filters.skip = 0;
                    });
                },

                setDeviceTypeFilter: (deviceType) => {
                    set((state) => {
                        state.filters.device_type = deviceType;
                        state.filters.skip = 0;
                    });
                },

                setStatusFilter: (status) => {
                    set((state) => {
                        state.filters.status = status;
                        state.filters.skip = 0;
                    });
                },

                setActiveFilter: (isActive) => {
                    set((state) => {
                        state.filters.is_active = isActive;
                        state.filters.skip = 0;
                    });
                },

                setTransmissionFilter: (enabled) => {
                    set((state) => {
                        state.filters.transmission_enabled = enabled;
                        state.filters.skip = 0;
                    });
                },

                setDatasetFilter: (hasDataset) => {
                    set((state) => {
                        state.filters.has_dataset = hasDataset;
                        state.filters.skip = 0;
                    });
                },

                setTagsFilter: (tags) => {
                    set((state) => {
                        state.filters.tags = tags.length > 0 ? tags : undefined;
                        state.filters.skip = 0;
                    });
                },

                setProjectFilter: (projectId) => {
                    set((state) => {
                        state.filters.project_id = projectId;
                        state.filters.skip = 0;
                    });
                },

                setConnectionFilter: (connectionId) => {
                    set((state) => {
                        state.filters.connection_id = connectionId;
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
                selectDevice: (id) => {
                    set((state) => {
                        if (!state.selectedIds.includes(id)) {
                            state.selectedIds.push(id);
                        }
                    });
                },

                deselectDevice: (id) => {
                    set((state) => {
                        state.selectedIds = state.selectedIds.filter((i) => i !== id);
                    });
                },

                selectAllDevices: (ids) => {
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

                openEditDialog: (deviceId) => {
                    set((state) => {
                        state.isEditDialogOpen = true;
                        state.currentDeviceId = deviceId;
                    });
                },

                closeEditDialog: () => {
                    set((state) => {
                        state.isEditDialogOpen = false;
                        state.currentDeviceId = null;
                    });
                },

                openDuplicateDialog: (deviceId) => {
                    set((state) => {
                        state.isDuplicateDialogOpen = true;
                        state.currentDeviceId = deviceId;
                    });
                },

                closeDuplicateDialog: () => {
                    set((state) => {
                        state.isDuplicateDialogOpen = false;
                        state.currentDeviceId = null;
                    });
                },

                openDeleteDialog: (deviceId) => {
                    set((state) => {
                        state.isDeleteDialogOpen = true;
                        state.currentDeviceId = deviceId;
                    });
                },

                closeDeleteDialog: () => {
                    set((state) => {
                        state.isDeleteDialogOpen = false;
                        state.currentDeviceId = null;
                    });
                },

                openLinkDatasetDialog: (deviceId) => {
                    set((state) => {
                        state.isLinkDatasetDialogOpen = true;
                        state.currentDeviceId = deviceId;
                    });
                },

                closeLinkDatasetDialog: () => {
                    set((state) => {
                        state.isLinkDatasetDialogOpen = false;
                        state.currentDeviceId = null;
                    });
                },

                openMetadataDialog: (deviceId) => {
                    set((state) => {
                        state.isMetadataDialogOpen = true;
                        state.currentDeviceId = deviceId;
                    });
                },

                closeMetadataDialog: () => {
                    set((state) => {
                        state.isMetadataDialogOpen = false;
                        state.currentDeviceId = null;
                    });
                },

                openExportDialog: () => {
                    set((state) => {
                        state.isExportDialogOpen = true;
                    });
                },

                closeExportDialog: () => {
                    set((state) => {
                        state.isExportDialogOpen = false;
                    });
                },

                openImportDialog: () => {
                    set((state) => {
                        state.isImportDialogOpen = true;
                    });
                },

                closeImportDialog: () => {
                    set((state) => {
                        state.isImportDialogOpen = false;
                    });
                },

                closeAllDialogs: () => {
                    set((state) => {
                        state.isCreateDialogOpen = false;
                        state.isEditDialogOpen = false;
                        state.isDuplicateDialogOpen = false;
                        state.isDeleteDialogOpen = false;
                        state.isLinkDatasetDialogOpen = false;
                        state.isMetadataDialogOpen = false;
                        state.isExportDialogOpen = false;
                        state.isImportDialogOpen = false;
                        state.currentDeviceId = null;
                    });
                },

                // Reset store
                reset: () => {
                    set(defaultState);
                },
            })),
            {
                name: 'device-store',
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
            name: 'device-store',
        }
    )
);
