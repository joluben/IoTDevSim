import { useState } from 'react';
import { Download, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { TransmissionHistoryEntry, TransmissionHistoryFilters, ProjectDevice } from '@/types/project';

interface TransmissionHistoryTableProps {
  entries: TransmissionHistoryEntry[];
  total: number;
  filters: TransmissionHistoryFilters;
  onFiltersChange: (filters: TransmissionHistoryFilters) => void;
  devices: ProjectDevice[];
  onExport?: () => void;
  isLoading?: boolean;
  hasNext?: boolean;
  hasPrev?: boolean;
}

export function TransmissionHistoryTable({
  entries,
  total,
  filters,
  onFiltersChange,
  devices,
  onExport,
  isLoading,
  hasNext,
  hasPrev,
}: TransmissionHistoryTableProps) {
  const skip = filters.skip ?? 0;
  const limit = filters.limit ?? 50;

  const update = (partial: Partial<TransmissionHistoryFilters>) =>
    onFiltersChange({ ...filters, ...partial, skip: 0 });

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Transmission History</CardTitle>
          {onExport && (
            <Button size="sm" variant="outline" onClick={onExport}>
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <Select
            value={filters.device_id || 'all'}
            onValueChange={(v) => update({ device_id: v === 'all' ? undefined : v })}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All devices" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All devices</SelectItem>
              {devices.map((d) => (
                <SelectItem key={d.id} value={d.id}>
                  {d.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={filters.status || 'all'}
            onValueChange={(v) => update({ status: v === 'all' ? undefined : v })}
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="error">Error</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Table */}
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Device</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Protocol</TableHead>
                <TableHead>Topic</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Latency</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    Loading history...
                  </TableCell>
                </TableRow>
              ) : entries.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No transmission history
                  </TableCell>
                </TableRow>
              ) : (
                entries.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="text-sm font-medium">{entry.device_name}</span>
                        {entry.device_ref && (
                          <code className="text-xs text-muted-foreground font-mono">
                            {entry.device_ref}
                          </code>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={entry.status === 'success' ? 'default' : 'destructive'}
                        className="text-xs"
                      >
                        {entry.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs uppercase">
                        {entry.protocol}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[150px] truncate">
                      {entry.topic || '-'}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {entry.payload_size} B
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {entry.latency_ms != null ? `${entry.latency_ms} ms` : '-'}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {total > 0 && (
          <div className="flex items-center justify-between pt-1">
            <span className="text-sm text-muted-foreground">
              {skip + 1}–{Math.min(skip + limit, total)} of {total}
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                disabled={!hasPrev}
                onClick={() =>
                  onFiltersChange({ ...filters, skip: Math.max(0, skip - limit) })
                }
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                disabled={!hasNext}
                onClick={() =>
                  onFiltersChange({ ...filters, skip: skip + limit })
                }
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
