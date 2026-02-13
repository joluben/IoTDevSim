/**
 * Dataset Preview Dialog Component
 * Displays a preview of the dataset data and statistics in a modal
 */

import * as React from 'react';
import {
    Eye,
    Table as TableIcon,
    BarChart3,
    Info,
    RefreshCw,
    Database,
    Binary,
    Hash,
    Type,
    Calendar,
} from 'lucide-react';

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { useDataset, useDatasetPreview } from '@/hooks/useDatasets';
import { useDatasetStore } from '@/app/store/dataset-store';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

export function DatasetPreviewDialog() {
    const isVisible = useDatasetStore((s) => s.isPreviewDialogOpen);
    const closeDialog = useDatasetStore((s) => s.closePreviewDialog);
    const datasetId = useDatasetStore((s) => s.currentDatasetId);

    const [limit, setLimit] = React.useState(20);
    const [activeTab, setActiveTab] = React.useState('data');

    // Queries
    const { data: dataset, isLoading: isLoadingDetail } = useDataset(datasetId || '');
    const { data: preview, isLoading: isLoadingPreview, refetch } = useDatasetPreview(datasetId || '', limit);

    const isLoading = isLoadingDetail || isLoadingPreview;

    if (!isVisible) return null;

    const columns = preview?.columns || [];
    const rows = preview?.data || [];

    const getDataTypeIcon = (type: string) => {
        const t = type.toLowerCase();
        if (t.includes('int') || t.includes('float') || t.includes('number')) return <Hash className="h-3 w-3" />;
        if (t.includes('date') || t.includes('time')) return <Calendar className="h-3 w-3" />;
        if (t.includes('bool')) return <Binary className="h-3 w-3" />;
        return <Type className="h-3 w-3" />;
    };

    return (
        <Dialog open={isVisible} onOpenChange={(open) => !open && closeDialog()}>
            <DialogContent className="max-w-7xl h-[90vh] flex flex-col p-0 gap-0 overflow-hidden">
                <DialogHeader className="p-6 pb-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                                <Eye className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                                <DialogTitle className="text-xl font-bold flex items-center gap-2">
                                    {isLoadingDetail ? <Skeleton className="h-6 w-48" /> : dataset?.name}
                                    {!isLoadingDetail && dataset?.status === 'ready' && (
                                        <Badge variant="secondary" className="bg-green-500/10 text-green-500 hover:bg-green-500/10 border-green-500/20">
                                            Listo
                                        </Badge>
                                    )}
                                </DialogTitle>
                                <DialogDescription className="text-sm line-clamp-1">
                                    {isLoadingDetail ? <Skeleton className="h-4 w-64 mt-1" /> : dataset?.description || 'Vista previa de los datos y estadísticas del dataset'}
                                </DialogDescription>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 mr-6">
                            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
                                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                                Actualizar
                            </Button>
                        </div>
                    </div>
                </DialogHeader>

                <div className="flex-1 overflow-hidden flex flex-col px-6">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
                        <div className="flex items-center justify-between border-b mb-4">
                            <TabsList className="bg-transparent h-12 w-auto justify-start gap-4 p-0">
                                <TabsTrigger
                                    value="data"
                                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-full px-4"
                                >
                                    <TableIcon className="h-4 w-4 mr-2" />
                                    Datos
                                </TabsTrigger>
                                <TabsTrigger
                                    value="stats"
                                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-full px-4"
                                >
                                    <BarChart3 className="h-4 w-4 mr-2" />
                                    Estadísticas
                                </TabsTrigger>
                                <TabsTrigger
                                    value="info"
                                    className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-full px-4"
                                >
                                    <Info className="h-4 w-4 mr-2" />
                                    Metadatos
                                </TabsTrigger>
                            </TabsList>

                            {activeTab === 'data' && (
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="text-xs text-muted-foreground mr-2">
                                        Viendo {rows.length} de {dataset?.row_count || '...'} filas
                                    </span>
                                </div>
                            )}
                        </div>

                        <TabsContent value="data" className="flex-1 overflow-hidden m-0 border rounded-xl bg-muted/20">
                            {isLoading ? (
                                <div className="p-4 space-y-4">
                                    <Skeleton className="h-10 w-full" />
                                    <Skeleton className="h-10 w-full" />
                                    <Skeleton className="h-10 w-full" />
                                    <Skeleton className="h-64 w-full" />
                                </div>
                            ) : rows.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center text-center p-12">
                                    <Database className="h-12 w-12 text-muted-foreground/30 mb-4" />
                                    <h3 className="text-lg font-medium">No hay datos disponibles</h3>
                                    <p className="text-muted-foreground max-w-xs mx-auto">
                                        Este dataset parece estar vacío o todavía se está procesando.
                                    </p>
                                </div>
                            ) : (
                                <ScrollArea className="h-full">
                                    <div className="min-w-full inline-block align-middle">
                                        <Table>
                                            <TableHeader className="bg-muted/50 sticky top-0 z-10 shadow-sm">
                                                <TableRow>
                                                    <TableHead className="w-12 text-center border-r">#</TableHead>
                                                    {columns.map((col) => (
                                                        <TableHead key={col.name} className="whitespace-nowrap px-4 py-3 border-r min-w-[150px]">
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-primary/70">{getDataTypeIcon(col.data_type)}</span>
                                                                <span className="font-semibold text-foreground">{col.name}</span>
                                                            </div>
                                                            <div className="text-[10px] text-muted-foreground uppercase font-medium mt-0.5">
                                                                {col.data_type}
                                                            </div>
                                                        </TableHead>
                                                    ))}
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {rows.map((row, idx) => (
                                                    <TableRow key={idx} className="hover:bg-primary/5 transition-colors border-b">
                                                        <TableCell className="text-center text-xs text-muted-foreground bg-muted/20 border-r py-2">
                                                            {idx + 1}
                                                        </TableCell>
                                                        {columns.map((col) => {
                                                            const value = row[col.name];
                                                            return (
                                                                <TableCell key={`${idx}-${col.name}`} className="px-4 py-2 border-r text-sm truncate max-w-[300px]">
                                                                    {value === null || value === undefined ? (
                                                                        <span className="text-muted-foreground/40 italic text-xs">null</span>
                                                                    ) : typeof value === 'boolean' ? (
                                                                        <Badge variant={value ? "default" : "secondary"} className="h-5 text-[10px] uppercase font-bold px-1.5">
                                                                            {value ? 'True' : 'False'}
                                                                        </Badge>
                                                                    ) : typeof value === 'object' ? (
                                                                        <span className="text-xs font-mono text-blue-500 bg-blue-500/5 px-1 rounded">{JSON.stringify(value)}</span>
                                                                    ) : (
                                                                        String(value)
                                                                    )}
                                                                </TableCell>
                                                            );
                                                        })}
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </div>
                                    <ScrollBar orientation="horizontal" />
                                    <ScrollBar orientation="vertical" />
                                </ScrollArea>
                            )}
                        </TabsContent>

                        <TabsContent value="stats" className="flex-1 overflow-hidden m-0 pt-0">
                            <ScrollArea className="h-full pr-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-6 mt-1">
                                    {isLoading ? (
                                        Array.from({ length: 6 }).map((_, i) => (
                                            <Skeleton key={i} className="h-40 w-full rounded-xl" />
                                        ))
                                    ) : (preview?.statistics || []).map((stat) => (
                                        <Card key={stat.name} className="overflow-hidden border-muted/60 shadow-sm hover:shadow-md transition-shadow">
                                            <CardHeader className="bg-muted/30 py-3 px-4 border-b">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-2">
                                                        {getDataTypeIcon(stat.data_type)}
                                                        <span className="font-bold text-sm truncate max-w-[150px]">{stat.name}</span>
                                                    </div>
                                                    <Badge variant="outline" className="text-[10px] uppercase font-bold py-0 h-4">
                                                        {stat.data_type}
                                                    </Badge>
                                                </div>
                                            </CardHeader>
                                            <CardContent className="p-4 space-y-3">
                                                <div className="grid grid-cols-2 gap-x-2 gap-y-3 text-xs">
                                                    <div>
                                                        <span className="text-muted-foreground block mb-0.5">Valores Únicos</span>
                                                        <span className="font-semibold text-foreground flex items-center gap-1.5">
                                                            {stat.unique_count}
                                                            <span className="text-[10px] text-muted-foreground font-normal">
                                                                ({((stat.unique_count / stat.total_count) * 100).toFixed(1)}%)
                                                            </span>
                                                        </span>
                                                    </div>
                                                    <div>
                                                        <span className="text-muted-foreground block mb-0.5">Nulos / Vacíos</span>
                                                        <span className={`font-semibold flex items-center gap-1.5 ${stat.null_count > 0 ? 'text-amber-500' : 'text-green-500'}`}>
                                                            {stat.null_count}
                                                            <span className="text-[10px] font-normal opacity-70">
                                                                ({((stat.null_count / stat.total_count) * 100).toFixed(1)}%)
                                                            </span>
                                                        </span>
                                                    </div>

                                                    {stat.min_value !== undefined && (
                                                        <div className="col-span-2 border-t pt-2 mt-1">
                                                            <div className="flex justify-between items-center mb-1">
                                                                <span className="text-muted-foreground">Min / Max</span>
                                                                <span className="font-mono text-[10px] font-bold">
                                                                    {String(stat.min_value)} / {String(stat.max_value)}
                                                                </span>
                                                            </div>
                                                            {typeof stat.mean_value === 'number' && (
                                                                <div className="flex justify-between items-center">
                                                                    <span className="text-muted-foreground">Media</span>
                                                                    <span className="font-bold text-primary">{stat.mean_value.toFixed(2)}</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            </ScrollArea>
                        </TabsContent>

                        <TabsContent value="info" className="flex-1 overflow-hidden m-0 pt-0">
                            <ScrollArea className="h-full">
                                <div className="space-y-6 pb-6 mt-1">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <Card className="border-muted/60">
                                            <CardHeader className="bg-muted/10 py-3 px-4 border-b">
                                                <h4 className="font-bold text-sm">Información General</h4>
                                            </CardHeader>
                                            <CardContent className="p-4">
                                                <dl className="space-y-4 text-sm">
                                                    <div className="flex justify-between border-b pb-2">
                                                        <dt className="text-muted-foreground">ID del Dataset</dt>
                                                        <dd className="font-mono text-xs">{dataset?.id}</dd>
                                                    </div>
                                                    <div className="flex justify-between border-b pb-2">
                                                        <dt className="text-muted-foreground">Origen</dt>
                                                        <dd className="capitalize">{dataset?.source}</dd>
                                                    </div>
                                                    <div className="flex justify-between border-b pb-2">
                                                        <dt className="text-muted-foreground">Formato</dt>
                                                        <dd className="uppercase">{dataset?.file_format || 'N/A'}</dd>
                                                    </div>
                                                    <div className="flex justify-between border-b pb-2">
                                                        <dt className="text-muted-foreground">Total de Filas</dt>
                                                        <dd className="font-bold">{dataset?.row_count?.toLocaleString() ?? 'N/A'}</dd>
                                                    </div>
                                                    <div className="flex justify-between border-b pb-2">
                                                        <dt className="text-muted-foreground">Total de Columnas</dt>
                                                        <dd className="font-bold">{dataset?.column_count}</dd>
                                                    </div>
                                                    <div className="flex justify-between border-b pb-2">
                                                        <dt className="text-muted-foreground">Fecha de Creación</dt>
                                                        <dd>{dataset ? new Date(dataset.created_at).toLocaleString() : '...'}</dd>
                                                    </div>
                                                </dl>
                                            </CardContent>
                                        </Card>

                                        <Card className="border-muted/60">
                                            <CardHeader className="bg-muted/10 py-3 px-4 border-b">
                                                <h4 className="font-bold text-sm">Etiquetas y Metadatos</h4>
                                            </CardHeader>
                                            <CardContent className="p-4 space-y-4">
                                                <div>
                                                    <span className="text-muted-foreground text-xs block mb-2 font-medium">Etiquetas</span>
                                                    <div className="flex flex-wrap gap-2">
                                                        {dataset?.tags.map(tag => (
                                                            <Badge key={tag} variant="secondary">{tag}</Badge>
                                                        ))}
                                                        {(!dataset?.tags || dataset.tags.length === 0) && (
                                                            <span className="text-xs text-muted-foreground italic">Sin etiquetas</span>
                                                        )}
                                                    </div>
                                                </div>

                                                <div className="border-t pt-4">
                                                    <span className="text-muted-foreground text-xs block mb-2 font-medium">Metadatos Personalizados</span>
                                                    <pre className="text-[10px] bg-muted p-3 rounded-lg overflow-auto max-h-[150px] font-mono leading-relaxed">
                                                        {dataset?.metadata ? JSON.stringify(dataset.metadata, null, 2) : '{}'}
                                                    </pre>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </div>
                                </div>
                            </ScrollArea>
                        </TabsContent>
                    </Tabs>
                </div>

                <div className="p-4 border-t bg-muted/20 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-muted-foreground">Límite de filas:</span>
                        {[20, 50, 100, 200].map(v => (
                            <Button
                                key={v}
                                size="sm"
                                variant={limit === v ? "default" : "outline"}
                                className="h-7 px-2.5 text-[10px]"
                                onClick={() => setLimit(v)}
                                disabled={isLoading}
                            >
                                {v}
                            </Button>
                        ))}
                    </div>
                    <Button variant="default" onClick={closeDialog}>
                        Cerrar Vista Previa
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
