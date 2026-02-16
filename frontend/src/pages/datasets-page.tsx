/**
 * Datasets Page
 * Main page for dataset management
 */

import * as React from 'react';
import { Plus, LayoutGrid, Table as TableIcon, Upload, Cpu } from 'lucide-react';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';

import { PageContainer } from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { DatasetCard } from '@/components/datasets/dataset-card';
import { DatasetFilters } from '@/components/datasets/datasets-filters';
import { DatasetsStats } from '@/components/datasets/datasets-stats';
import { DatasetsTable } from '@/components/datasets/datasets-table';
import { UploadDatasetDialog } from '@/components/datasets/upload-dataset-dialog';
import { DatasetPreviewDialog } from '@/components/datasets/dataset-preview-dialog';
import { GenerateDatasetDialog } from '@/components/datasets/generate-dataset-dialog';
import {
    useDatasets,
    useDatasetStatistics,
    useDeleteDataset,
    useDownloadDataset,
} from '@/hooks/useDatasets';
import { useDatasetStore } from '@/app/store/dataset-store';
import { useUIStore } from '@/app/store/ui-store';
import type { DatasetFilters as DatasetFiltersType } from '@/types/dataset';
import { Skeleton } from '@/components/ui/skeleton';

export default function DatasetsPage() {
    const viewMode = useDatasetStore((s) => s.viewMode);
    const setViewMode = useDatasetStore((s) => s.setViewMode);
    const filters = useDatasetStore((s) => s.filters);
    const setFilters = useDatasetStore((s) => s.setFilters);
    const openPreviewDialog = useDatasetStore((s) => s.openPreviewDialog);
    const addNotification = useUIStore((s) => s.addNotification);

    // Dialog states
    const [isUploadOpen, setIsUploadOpen] = React.useState(false);
    const [isGenerateOpen, setIsGenerateOpen] = React.useState(false);
    const [deletingDatasetId, setDeletingDatasetId] = React.useState<string | null>(null);

    // Queries
    const listQuery = useDatasets(filters);
    const statsQuery = useDatasetStatistics();
    const deleteMutation = useDeleteDataset();
    const downloadMutation = useDownloadDataset();

    const datasets = listQuery.data?.items ?? [];

    // Error handling
    React.useEffect(() => {
        if (!listQuery.isError) return;
        addNotification({
            type: 'error',
            title: 'Error al cargar datasets',
            message:
                listQuery.error instanceof Error
                    ? listQuery.error.message
                    : 'Ocurrió un error inesperado.',
        });
    }, [listQuery.isError, listQuery.error, addNotification]);

    const handleFiltersChange = (newFilters: DatasetFiltersType) => {
        setFilters(newFilters);
    };

    const handlePreview = (id: string) => {
        openPreviewDialog(id);
    };

    const handleDownload = (id: string) => {
        downloadMutation.mutate(id, {
            onSuccess: () => {
                addNotification({
                    type: 'success',
                    title: 'Descarga iniciada',
                    message: 'El archivo se está descargando.',
                });
            },
            onError: (error) => {
                addNotification({
                    type: 'error',
                    title: 'Error en la descarga',
                    message: error instanceof Error ? error.message : 'No se pudo descargar el archivo.',
                });
            },
        });
    };

    const handleDelete = (id: string) => {
        setDeletingDatasetId(id);
    };

    const confirmDelete = () => {
        if (!deletingDatasetId) return;
        deleteMutation.mutate(
            { id: deletingDatasetId },
            {
                onSuccess: () => {
                    addNotification({
                        type: 'success',
                        title: 'Dataset eliminado',
                        message: 'El dataset se ha eliminado correctamente.',
                    });
                    setDeletingDatasetId(null);
                },
                onError: (error) => {
                    addNotification({
                        type: 'error',
                        title: 'Error al eliminar',
                        message: error instanceof Error ? error.message : 'No se pudo eliminar el dataset.',
                    });
                    setDeletingDatasetId(null);
                },
            }
        );
    };

    return (
        <PageContainer
            title="Datasets"
            description="Gestiona tus conjuntos de datos para simulación IoT"
            header={
                <div className="flex items-center justify-between gap-4">
                    <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'grid' | 'table')}>
                        <TabsList>
                            <TabsTrigger value="grid">
                                <LayoutGrid className="h-4 w-4 mr-2" />
                                Tarjetas
                            </TabsTrigger>
                            <TabsTrigger value="table">
                                <TableIcon className="h-4 w-4 mr-2" />
                                Tabla
                            </TabsTrigger>
                        </TabsList>
                    </Tabs>

                    <div className="flex items-center gap-2">
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button>
                                    <Plus className="h-4 w-4 mr-2" />
                                    Nuevo Dataset
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => setIsUploadOpen(true)}>
                                    <Upload className="mr-2 h-4 w-4" />
                                    Subir archivo
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => setIsGenerateOpen(true)}>
                                    <Cpu className="mr-2 h-4 w-4" />
                                    Generar datos sintéticos
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </div>
            }
        >
            <div className="space-y-6">
                {/* Statistics */}
                <DatasetsStats statistics={statsQuery.data} isLoading={statsQuery.isLoading} />

                {/* Filters */}
                <DatasetFilters value={filters} onChange={handleFiltersChange} />

                {/* Content */}
                {listQuery.isLoading ? (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {[1, 2, 3, 4, 5, 6].map((i) => (
                            <Skeleton key={i} className="h-[250px] rounded-xl" />
                        ))}
                    </div>
                ) : datasets.length === 0 ? (
                    <div className="rounded-lg border bg-card p-10 text-center">
                        <div className="mx-auto max-w-md space-y-3">
                            <div className="text-lg font-semibold">No hay datasets</div>
                            <div className="text-sm text-muted-foreground">
                                Sube un archivo o genera datos sintéticos para empezar.
                            </div>
                            <div className="flex justify-center gap-2">
                                <Button onClick={() => setIsUploadOpen(true)}>
                                    <Upload className="h-4 w-4 mr-2" />
                                    Subir archivo
                                </Button>
                            </div>
                        </div>
                    </div>
                ) : viewMode === 'grid' ? (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {datasets.map((dataset) => (
                            <DatasetCard
                                key={dataset.id}
                                dataset={dataset}
                                onPreview={handlePreview}
                                onDownload={handleDownload}
                                onDelete={handleDelete}
                            />
                        ))}

                        {/* Add new card */}
                        <div
                            onClick={() => setIsUploadOpen(true)}
                            className="flex min-h-[180px] cursor-pointer items-center justify-center rounded-xl border border-dashed bg-card p-6 transition-colors hover:border-primary/50 hover:bg-accent/50"
                        >
                            <div className="space-y-3 text-center">
                                <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
                                <div className="text-sm text-muted-foreground">Nuevo dataset</div>
                            </div>
                        </div>
                    </div>
                ) : (
                    <DatasetsTable
                        datasets={datasets}
                        onPreview={handlePreview}
                        onDownload={handleDownload}
                        onDelete={handleDelete}
                    />
                )}

                {/* Pagination info */}
                {listQuery.data && listQuery.data.total > 0 && (
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                        <span>
                            Mostrando {datasets.length} de {listQuery.data.total} datasets
                        </span>
                        {listQuery.data.has_next && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                    setFilters({
                                        ...filters,
                                        skip: (filters.skip || 0) + (filters.limit || 20),
                                    })
                                }
                            >
                                Cargar más
                            </Button>
                        )}
                    </div>
                )}
            </div>

            {/* Dialogs */}
            <UploadDatasetDialog open={isUploadOpen} onOpenChange={setIsUploadOpen} />
            <DatasetPreviewDialog />
            <GenerateDatasetDialog open={isGenerateOpen} onOpenChange={setIsGenerateOpen} />

            <ConfirmDialog
                open={!!deletingDatasetId}
                onOpenChange={(open) => { if (!open) setDeletingDatasetId(null); }}
                title="Eliminar dataset"
                description="¿Estás seguro de que deseas eliminar este dataset? Esta acción no se puede deshacer y los dispositivos vinculados perderán acceso a estos datos."
                confirmLabel="Eliminar"
                cancelLabel="Cancelar"
                variant="destructive"
                isLoading={deleteMutation.isPending}
                onConfirm={confirmDelete}
            />
        </PageContainer>
    );
}
