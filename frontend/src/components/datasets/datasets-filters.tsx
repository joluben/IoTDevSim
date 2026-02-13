/**
 * Dataset Filters Component
 * Filter controls for dataset list
 */

import * as React from 'react';
import { Search, X, SlidersHorizontal } from 'lucide-react';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Label } from '@/components/ui/label';
import type { DatasetFilters, DatasetSource, DatasetStatus } from '@/types/dataset';

interface DatasetFiltersProps {
    value: DatasetFilters;
    onChange: (filters: DatasetFilters) => void;
}

const sourceOptions: { value: DatasetSource; label: string }[] = [
    { value: 'upload', label: 'Subido' },
    { value: 'generated', label: 'Generado' },
    { value: 'manual', label: 'Manual' },
    { value: 'template', label: 'Plantilla' },
];

const statusOptions: { value: DatasetStatus; label: string }[] = [
    { value: 'draft', label: 'Borrador' },
    { value: 'processing', label: 'Procesando' },
    { value: 'ready', label: 'Listo' },
    { value: 'error', label: 'Error' },
];

const sortOptions = [
    { value: 'created_at', label: 'Fecha de creación' },
    { value: 'updated_at', label: 'Última modificación' },
    { value: 'name', label: 'Nombre' },
    { value: 'row_count', label: 'Número de filas' },
];

export function DatasetFilters({ value, onChange }: DatasetFiltersProps) {
    const [searchValue, setSearchValue] = React.useState(value.search || '');

    // Debounced search
    React.useEffect(() => {
        const timer = setTimeout(() => {
            if (searchValue !== value.search) {
                onChange({ ...value, search: searchValue || undefined, skip: 0 });
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [searchValue, value, onChange]);

    const handleSourceChange = (source: string) => {
        onChange({
            ...value,
            source: source === 'all' ? undefined : (source as DatasetSource),
            skip: 0,
        });
    };

    const handleStatusChange = (status: string) => {
        onChange({
            ...value,
            status: status === 'all' ? undefined : (status as DatasetStatus),
            skip: 0,
        });
    };

    const handleSortChange = (sortBy: string) => {
        onChange({ ...value, sort_by: sortBy });
    };

    const handleSortOrderToggle = () => {
        onChange({
            ...value,
            sort_order: value.sort_order === 'asc' ? 'desc' : 'asc',
        });
    };

    const handleClearFilters = () => {
        setSearchValue('');
        onChange({
            skip: 0,
            limit: value.limit || 20,
            sort_by: 'created_at',
            sort_order: 'desc',
        });
    };

    const activeFilterCount = [
        value.source,
        value.status,
        value.min_rows,
        value.max_rows,
        value.file_format,
        value.tags?.length,
    ].filter(Boolean).length;

    return (
        <div className="space-y-4">
            {/* Main filters row */}
            <div className="flex flex-wrap items-center gap-3">
                {/* Search input */}
                <div className="relative flex-1 min-w-[200px] max-w-sm">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        placeholder="Buscar datasets..."
                        value={searchValue}
                        onChange={(e) => setSearchValue(e.target.value)}
                        className="pl-9 pr-9"
                    />
                    {searchValue && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
                            onClick={() => setSearchValue('')}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    )}
                </div>

                {/* Source filter */}
                <Select value={value.source || 'all'} onValueChange={handleSourceChange}>
                    <SelectTrigger className="w-[140px]">
                        <SelectValue placeholder="Origen" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Todos los orígenes</SelectItem>
                        {sourceOptions.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                {/* Status filter */}
                <Select value={value.status || 'all'} onValueChange={handleStatusChange}>
                    <SelectTrigger className="w-[140px]">
                        <SelectValue placeholder="Estado" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">Todos los estados</SelectItem>
                        {statusOptions.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                {/* Sort */}
                <div className="flex items-center gap-1">
                    <Select value={value.sort_by || 'created_at'} onValueChange={handleSortChange}>
                        <SelectTrigger className="w-[160px]">
                            <SelectValue placeholder="Ordenar por" />
                        </SelectTrigger>
                        <SelectContent>
                            {sortOptions.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                    {opt.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Button
                        variant="outline"
                        size="icon"
                        onClick={handleSortOrderToggle}
                        className="shrink-0"
                    >
                        {value.sort_order === 'asc' ? '↑' : '↓'}
                    </Button>
                </div>

                {/* Advanced filters dropdown */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" className="relative">
                            <SlidersHorizontal className="mr-2 h-4 w-4" />
                            Filtros
                            {activeFilterCount > 0 && (
                                <Badge
                                    variant="secondary"
                                    className="ml-2 h-5 w-5 rounded-full p-0 flex items-center justify-center"
                                >
                                    {activeFilterCount}
                                </Badge>
                            )}
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-64 p-4" align="end">
                        <DropdownMenuLabel>Filtros avanzados</DropdownMenuLabel>
                        <DropdownMenuSeparator />

                        {/* File format filter */}
                        <div className="space-y-2 py-2">
                            <Label>Formato de archivo</Label>
                            <Select
                                value={value.file_format || 'all'}
                                onValueChange={(v) =>
                                    onChange({ ...value, file_format: v === 'all' ? undefined : v, skip: 0 })
                                }
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Todos los formatos" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">Todos los formatos</SelectItem>
                                    <SelectItem value="csv">CSV</SelectItem>
                                    <SelectItem value="xlsx">Excel</SelectItem>
                                    <SelectItem value="json">JSON</SelectItem>
                                    <SelectItem value="tsv">TSV</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Row count range */}
                        <div className="space-y-2 py-2">
                            <Label>Rango de filas</Label>
                            <div className="flex items-center gap-2">
                                <Input
                                    type="number"
                                    placeholder="Mín"
                                    value={value.min_rows || ''}
                                    onChange={(e) => {
                                        const val = e.target.value ? parseInt(e.target.value, 10) : undefined;
                                        onChange({ ...value, min_rows: val, skip: 0 });
                                    }}
                                    className="w-20"
                                />
                                <span className="text-muted-foreground">—</span>
                                <Input
                                    type="number"
                                    placeholder="Máx"
                                    value={value.max_rows || ''}
                                    onChange={(e) => {
                                        const val = e.target.value ? parseInt(e.target.value, 10) : undefined;
                                        onChange({ ...value, max_rows: val, skip: 0 });
                                    }}
                                    className="w-20"
                                />
                            </div>
                        </div>
                    </DropdownMenuContent>
                </DropdownMenu>

                {/* Clear filters */}
                {(value.search || activeFilterCount > 0) && (
                    <Button variant="ghost" size="sm" onClick={handleClearFilters}>
                        <X className="mr-1 h-4 w-4" />
                        Limpiar
                    </Button>
                )}
            </div>
        </div>
    );
}
