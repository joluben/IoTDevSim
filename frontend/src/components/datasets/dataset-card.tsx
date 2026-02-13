/**
 * Dataset Card Component
 * Displays dataset information in a card format for grid view
 */

import * as React from 'react';
import { Database, FileSpreadsheet, Cpu, Cloud, MoreVertical, Eye, Download, Trash2, CheckCircle, AlertCircle, Clock, Loader2 } from 'lucide-react';

import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Progress } from '@/components/ui/progress';
import type { DatasetSummary } from '@/types/dataset';

// Simple relative time formatter
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

interface DatasetCardProps {
    dataset: DatasetSummary;
    onPreview?: (id: string) => void;
    onDownload?: (id: string) => void;
    onDelete?: (id: string) => void;
    onEdit?: (id: string) => void;
    isSelected?: boolean;
    onSelect?: (id: string) => void;
}

// Source icons mapping
const sourceIcons: Record<string, React.ElementType> = {
    upload: FileSpreadsheet,
    generated: Cpu,
    manual: Database,
    template: Cloud,
};

// Status colors and icons
const statusConfig: Record<string, { color: string; icon: React.ElementType; label: string }> = {
    draft: { color: 'bg-gray-500', icon: Clock, label: 'Borrador' },
    processing: { color: 'bg-blue-500', icon: Loader2, label: 'Procesando' },
    ready: { color: 'bg-green-500', icon: CheckCircle, label: 'Listo' },
    error: { color: 'bg-red-500', icon: AlertCircle, label: 'Error' },
};

function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatNumber(num: number): string {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
}

export function DatasetCard({
    dataset,
    onPreview,
    onDownload,
    onDelete,
    onEdit,
    isSelected,
    onSelect,
}: DatasetCardProps) {
    const SourceIcon = sourceIcons[dataset.source] || Database;
    const statusInfo = statusConfig[dataset.status] || statusConfig.draft;
    const StatusIcon = statusInfo.icon;

    const sourceLabels: Record<string, string> = {
        upload: 'Subido',
        generated: 'Generado',
        manual: 'Manual',
        template: 'Plantilla',
    };

    return (
        <Card
            className={`group relative transition-all hover:shadow-md ${isSelected ? 'ring-2 ring-primary' : ''
                }`}
        >
            {/* Selection checkbox */}
            {onSelect && (
                <div className="absolute left-3 top-3 z-10">
                    <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onSelect(dataset.id)}
                        className="h-4 w-4 rounded border-gray-300"
                    />
                </div>
            )}

            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <SourceIcon className="h-5 w-5 text-primary" />
                        </div>
                        <div className="space-y-1">
                            <h3 className="font-semibold leading-none tracking-tight line-clamp-1">
                                {dataset.name}
                            </h3>
                            <p className="text-xs text-muted-foreground">
                                {sourceLabels[dataset.source] || dataset.source}
                            </p>
                        </div>
                    </div>

                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                                <MoreVertical className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            {onPreview && (
                                <DropdownMenuItem onClick={() => onPreview(dataset.id)}>
                                    <Eye className="mr-2 h-4 w-4" />
                                    Vista previa
                                </DropdownMenuItem>
                            )}
                            {onEdit && (
                                <DropdownMenuItem onClick={() => onEdit(dataset.id)}>
                                    <Database className="mr-2 h-4 w-4" />
                                    Editar
                                </DropdownMenuItem>
                            )}
                            {onDownload && dataset.source === 'upload' && (
                                <DropdownMenuItem onClick={() => onDownload(dataset.id)}>
                                    <Download className="mr-2 h-4 w-4" />
                                    Descargar
                                </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            {onDelete && (
                                <DropdownMenuItem
                                    onClick={() => onDelete(dataset.id)}
                                    className="text-destructive focus:text-destructive"
                                >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Eliminar
                                </DropdownMenuItem>
                            )}
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </CardHeader>

            <CardContent className="pb-3">
                {dataset.description && (
                    <p className="mb-3 text-sm text-muted-foreground line-clamp-2">
                        {dataset.description}
                    </p>
                )}

                {/* Data metrics */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-muted-foreground">Filas</span>
                        <p className="font-medium">{formatNumber(dataset.row_count)}</p>
                    </div>
                    <div>
                        <span className="text-muted-foreground">Columnas</span>
                        <p className="font-medium">{dataset.column_count}</p>
                    </div>
                </div>

                {/* Completeness indicator */}
                {dataset.completeness_score !== null && dataset.completeness_score !== undefined && (
                    <div className="mt-3">
                        <div className="flex items-center justify-between text-xs mb-1">
                            <span className="text-muted-foreground">Completitud</span>
                            <span className="font-medium">{dataset.completeness_score.toFixed(0)}%</span>
                        </div>
                        <Progress value={dataset.completeness_score} className="h-1.5" />
                    </div>
                )}

                {/* Tags */}
                {dataset.tags && dataset.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                        {dataset.tags.slice(0, 3).map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                            </Badge>
                        ))}
                        {dataset.tags.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                                +{dataset.tags.length - 3}
                            </Badge>
                        )}
                    </div>
                )}
            </CardContent>

            <CardFooter className="border-t pt-3">
                <div className="flex w-full items-center justify-between">
                    {/* Status badge */}
                    <Badge
                        variant="outline"
                        className={`${statusInfo.color} text-white border-0`}
                    >
                        <StatusIcon className={`mr-1 h-3 w-3 ${dataset.status === 'processing' ? 'animate-spin' : ''}`} />
                        {statusInfo.label}
                    </Badge>

                    {/* Time */}
                    <span className="text-xs text-muted-foreground">
                        {formatRelativeTime(dataset.created_at)}
                    </span>
                </div>
            </CardFooter>
        </Card>
    );
}
