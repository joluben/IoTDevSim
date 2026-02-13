/**
 * Dataset Statistics Component
 * Shows summary statistics for datasets
 */

import * as React from 'react';
import { Database, FileSpreadsheet, Cpu, CheckCircle, AlertCircle, HardDrive } from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';
import type { DatasetStatistics } from '@/types/dataset';

interface DatasetsStatsProps {
    statistics?: DatasetStatistics | null;
    isLoading?: boolean;
}

function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatNumber(num: number): string {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
}

export function DatasetsStats({ statistics, isLoading }: DatasetsStatsProps) {
    if (isLoading) {
        return (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[1, 2, 3, 4].map((i) => (
                    <Card key={i}>
                        <CardContent className="p-4">
                            <div className="animate-pulse space-y-2">
                                <div className="h-4 w-20 rounded bg-muted" />
                                <div className="h-8 w-16 rounded bg-muted" />
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        );
    }

    const stats = [
        {
            label: 'Total Datasets',
            value: statistics?.total ?? 0,
            icon: Database,
            color: 'text-blue-500',
            bgColor: 'bg-blue-500/10',
        },
        {
            label: 'Listos',
            value: statistics?.by_status?.ready ?? 0,
            icon: CheckCircle,
            color: 'text-green-500',
            bgColor: 'bg-green-500/10',
        },
        {
            label: 'Total Filas',
            value: formatNumber(statistics?.total_rows ?? 0),
            icon: FileSpreadsheet,
            color: 'text-purple-500',
            bgColor: 'bg-purple-500/10',
        },
        {
            label: 'Almacenamiento',
            value: formatBytes(statistics?.total_size_bytes ?? 0),
            icon: HardDrive,
            color: 'text-orange-500',
            bgColor: 'bg-orange-500/10',
        },
    ];

    return (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
                <Card key={stat.label}>
                    <CardContent className="p-4">
                        <div className="flex items-center gap-3">
                            <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${stat.bgColor}`}>
                                <stat.icon className={`h-5 w-5 ${stat.color}`} />
                            </div>
                            <div>
                                <p className="text-sm text-muted-foreground">{stat.label}</p>
                                <p className="text-2xl font-bold">{stat.value}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
