/**
 * Datasets Table Component
 * Displays datasets in a sortable table view
 */

import * as React from 'react';
import {
    Database,
    FileSpreadsheet,
    Cpu,
    Cloud,
    Eye,
    Download,
    Trash2,
    CheckCircle,
    AlertCircle,
    Clock,
    Loader2,
    MoreHorizontal,
    ArrowUpDown,
} from 'lucide-react';

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { DatasetSummary } from '@/types/dataset';

interface DatasetsTableProps {
    datasets: DatasetSummary[];
    onPreview?: (id: string) => void;
    onDownload?: (id: string) => void;
    onDelete?: (id: string) => void;
}

// Source icons mapping
const sourceIcons: Record<string, React.ElementType> = {
    upload: FileSpreadsheet,
    generated: Cpu,
    manual: Database,
    template: Cloud,
};

const sourceLabels: Record<string, string> = {
    upload: 'Subido',
    generated: 'Generado',
    manual: 'Manual',
    template: 'Plantilla',
};

// Status config
const statusConfig: Record<string, { color: string; icon: React.ElementType; label: string }> = {
    draft: { color: 'text-gray-500', icon: Clock, label: 'Borrador' },
    processing: { color: 'text-blue-500', icon: Loader2, label: 'Procesando' },
    ready: { color: 'text-green-500', icon: CheckCircle, label: 'Listo' },
    error: { color: 'text-red-500', icon: AlertCircle, label: 'Error' },
};

function formatNumber(num: number): string {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
}

function formatRelativeTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 30) return date.toLocaleDateString();
    if (diffDays > 0) return `hace ${diffDays} día${diffDays > 1 ? 's' : ''}`;
    if (diffHours > 0) return `hace ${diffHours} hora${diffHours > 1 ? 's' : ''}`;
    if (diffMins > 0) return `hace ${diffMins} minuto${diffMins > 1 ? 's' : ''}`;
    return 'hace un momento';
}

type SortKey = 'name' | 'source' | 'status' | 'row_count' | 'column_count' | 'created_at';
type SortDir = 'asc' | 'desc';

export function DatasetsTable({ datasets, onPreview, onDownload, onDelete }: DatasetsTableProps) {
    const [sortKey, setSortKey] = React.useState<SortKey>('created_at');
    const [sortDir, setSortDir] = React.useState<SortDir>('desc');

    const toggleSort = (key: SortKey) => {
        if (sortKey === key) {
            setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
        } else {
            setSortKey(key);
            setSortDir('asc');
        }
    };

    const sorted = React.useMemo(() => {
        return [...datasets].sort((a, b) => {
            let cmp = 0;
            switch (sortKey) {
                case 'name':
                    cmp = a.name.localeCompare(b.name);
                    break;
                case 'source':
                    cmp = a.source.localeCompare(b.source);
                    break;
                case 'status':
                    cmp = a.status.localeCompare(b.status);
                    break;
                case 'row_count':
                    cmp = a.row_count - b.row_count;
                    break;
                case 'column_count':
                    cmp = a.column_count - b.column_count;
                    break;
                case 'created_at':
                    cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
                    break;
            }
            return sortDir === 'asc' ? cmp : -cmp;
        });
    }, [datasets, sortKey, sortDir]);

    const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
        <Button
            variant="ghost"
            size="sm"
            className="-ml-3 h-8 font-medium"
            onClick={() => toggleSort(field)}
        >
            {label}
            <ArrowUpDown className="ml-1 h-3 w-3 text-muted-foreground" />
        </Button>
    );

    return (
        <div className="rounded-lg border bg-card">
            <Table>
                <TableHeader>
                    <TableRow className="hover:bg-transparent">
                        <TableHead className="w-[280px]">
                            <SortHeader label="Nombre" field="name" />
                        </TableHead>
                        <TableHead className="w-[100px]">
                            <SortHeader label="Origen" field="source" />
                        </TableHead>
                        <TableHead className="w-[100px]">
                            <SortHeader label="Estado" field="status" />
                        </TableHead>
                        <TableHead className="w-[80px] text-right">
                            <SortHeader label="Filas" field="row_count" />
                        </TableHead>
                        <TableHead className="w-[80px] text-right">
                            <SortHeader label="Cols" field="column_count" />
                        </TableHead>
                        <TableHead>Tags</TableHead>
                        <TableHead className="w-[130px]">
                            <SortHeader label="Creado" field="created_at" />
                        </TableHead>
                        <TableHead className="w-[50px]" />
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {sorted.map((dataset) => {
                        const SourceIcon = sourceIcons[dataset.source] || Database;
                        const info = statusConfig[dataset.status] || statusConfig.draft;
                        const StatusIcon = info.icon;

                        return (
                            <TableRow
                                key={dataset.id}
                                className="cursor-pointer"
                                onClick={() => onPreview?.(dataset.id)}
                            >
                                <TableCell>
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
                                            <SourceIcon className="h-4 w-4 text-primary" />
                                        </div>
                                        <div className="min-w-0">
                                            <div className="font-medium truncate">{dataset.name}</div>
                                            {dataset.description && (
                                                <div className="text-xs text-muted-foreground truncate max-w-[220px]">
                                                    {dataset.description}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </TableCell>
                                <TableCell>
                                    <span className="text-xs text-muted-foreground">
                                        {sourceLabels[dataset.source] || dataset.source}
                                    </span>
                                </TableCell>
                                <TableCell>
                                    <div className={`flex items-center gap-1.5 text-xs ${info.color}`}>
                                        <StatusIcon className={`h-3.5 w-3.5 ${dataset.status === 'processing' ? 'animate-spin' : ''}`} />
                                        {info.label}
                                    </div>
                                </TableCell>
                                <TableCell className="text-right tabular-nums">
                                    {formatNumber(dataset.row_count)}
                                </TableCell>
                                <TableCell className="text-right tabular-nums">
                                    {dataset.column_count}
                                </TableCell>
                                <TableCell>
                                    <div className="flex flex-wrap gap-1">
                                        {dataset.tags.slice(0, 3).map((tag) => (
                                            <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">
                                                {tag}
                                            </Badge>
                                        ))}
                                        {dataset.tags.length > 3 && (
                                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                                                +{dataset.tags.length - 3}
                                            </Badge>
                                        )}
                                    </div>
                                </TableCell>
                                <TableCell className="text-xs text-muted-foreground">
                                    {formatRelativeTime(dataset.created_at)}
                                </TableCell>
                                <TableCell>
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                <MoreHorizontal className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            {onPreview && (
                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onPreview(dataset.id); }}>
                                                    <Eye className="mr-2 h-4 w-4" />
                                                    Vista previa
                                                </DropdownMenuItem>
                                            )}
                                            {onDownload && (
                                                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onDownload(dataset.id); }}>
                                                    <Download className="mr-2 h-4 w-4" />
                                                    Descargar
                                                </DropdownMenuItem>
                                            )}
                                            {(onPreview || onDownload) && onDelete && <DropdownMenuSeparator />}
                                            {onDelete && (
                                                <DropdownMenuItem
                                                    className="text-destructive"
                                                    onClick={(e) => { e.stopPropagation(); onDelete(dataset.id); }}
                                                >
                                                    <Trash2 className="mr-2 h-4 w-4" />
                                                    Eliminar
                                                </DropdownMenuItem>
                                            )}
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                            </TableRow>
                        );
                    })}
                </TableBody>
            </Table>
        </div>
    );
}
