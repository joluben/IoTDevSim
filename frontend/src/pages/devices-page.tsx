import * as React from 'react';
import { useNavigate } from 'react-router-dom';

import { LayoutGrid, Table as TableIcon, Plus, ChevronLeft, ChevronRight } from 'lucide-react';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';

import { PageContainer } from '@/components/layout/page-container';
import { DevicesTable } from '@/components/devices/devices-table';
import { DevicesFilters } from '@/components/devices/devices-filters';
import { DevicesStats } from '@/components/devices/devices-stats';
import { Button } from '@/components/ui/button';
import { useDevices, useDeleteDevice, usePatchDevice } from '@/hooks/useDevices';
import type { DeviceFilters, DeviceSummary } from '@/types/device';
import { useUIStore } from '@/app/store/ui-store';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const DEFAULT_FILTERS: DeviceFilters = {
  search: undefined,
  device_type: undefined,
  status: undefined,
  is_active: undefined,
  transmission_enabled: undefined,
  has_dataset: undefined,
  skip: 0,
  limit: 20,
  sort_by: 'created_at',
  sort_order: 'desc',
};

export default function DevicesPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = React.useState<DeviceFilters>(DEFAULT_FILTERS);
  const [viewMode, setViewMode] = React.useState<'grid' | 'table'>('table');
  const addNotification = useUIStore((s) => s.addNotification);
  const listQuery = useDevices(filters);
  const deleteMutation = useDeleteDevice();
  const patchMutation = usePatchDevice();

  const [deletingDeviceId, setDeletingDeviceId] = React.useState<string | null>(null);

  const devices = listQuery.data?.items ?? [];

  React.useEffect(() => {
    if (!listQuery.isError) return;
    addNotification({
      type: 'error',
      title: 'Failed to load devices',
      message:
        listQuery.error instanceof Error
          ? listQuery.error.message
          : 'An unexpected error occurred.',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listQuery.isError]);

  const handleDelete = (id: string) => {
    setDeletingDeviceId(id);
  };

  const confirmDelete = () => {
    if (!deletingDeviceId) return;
    deleteMutation.mutate(
      { id: deletingDeviceId },
      {
        onSuccess: () => {
          addNotification({ type: 'success', title: 'Device deleted', message: '' });
          setDeletingDeviceId(null);
        },
        onError: (error) => {
          addNotification({
            type: 'error',
            title: 'Failed to delete device',
            message: error instanceof Error ? error.message : 'Unexpected error',
          });
          setDeletingDeviceId(null);
        },
      }
    );
  };

  const handleBulkDelete = (ids: string[]) => {
    ids.forEach((id) => deleteMutation.mutate({ id }));
  };

  const handleToggleActive = (device: DeviceSummary) => {
    patchMutation.mutate({
      id: device.id,
      payload: { is_active: !device.is_active },
    });
  };

  const handleEdit = (device: DeviceSummary) => {
    navigate(`/devices/${device.id}/edit`);
  };

  const handleLinkDataset = (device: DeviceSummary) => {
    navigate(`/devices/${device.id}/edit`);
  };

  return (
    <PageContainer
      title="Devices"
      description="Manage your IoT devices"
      header={
        <div className="flex items-center justify-between gap-4">
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'grid' | 'table')}>
            <TabsList>
              <TabsTrigger value="table">
                <TableIcon className="h-4 w-4 mr-2" />
                Table
              </TabsTrigger>
              <TabsTrigger value="grid">
                <LayoutGrid className="h-4 w-4 mr-2" />
                Cards
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <Button onClick={() => navigate('/devices/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Device
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        <DevicesStats devices={devices} />

        <DevicesFilters value={filters} onChange={setFilters} />

        {devices.length === 0 && !listQuery.isLoading ? (
          <div className="rounded-lg border bg-card p-10 text-center">
            <div className="mx-auto max-w-md space-y-3">
              <div className="text-lg font-semibold">No devices yet</div>
              <div className="text-sm text-muted-foreground">
                Create your first device to start transmitting data.
              </div>
              <div className="flex justify-center">
                <Button onClick={() => navigate('/devices/new')}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Device
                </Button>
              </div>
            </div>
          </div>
        ) : viewMode === 'table' ? (
          <DevicesTable
            devices={devices}
            onDelete={handleDelete}
            onBulkDelete={handleBulkDelete}
            onToggleActive={handleToggleActive}
            onEdit={handleEdit}
            onLinkDataset={handleLinkDataset}
            isLoading={listQuery.isLoading}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {devices.map((device) => (
              <div
                key={device.id}
                className="rounded-xl border bg-card p-5 space-y-3 cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => navigate(`/devices/${device.id}/edit`)}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold">{device.name}</h3>
                    <code className="text-xs text-muted-foreground font-mono">
                      {device.device_id}
                    </code>
                  </div>
                  <span className="text-xs capitalize rounded-full bg-muted px-2 py-0.5">
                    {device.device_type}
                  </span>
                </div>
                {device.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {device.description}
                  </p>
                )}
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>Status: {device.status}</span>
                  <span>·</span>
                  <span>{device.dataset_count} dataset(s)</span>
                </div>
              </div>
            ))}

            <div
              className="flex min-h-[140px] items-center justify-center rounded-xl border border-dashed bg-card p-6 cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => navigate('/devices/new')}
            >
              <div className="space-y-3 text-center">
                <div className="text-sm text-muted-foreground">New device</div>
                <Button variant="outline" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Create
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Pagination */}
        {(listQuery.data?.total ?? 0) > 0 && (
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>
                {(filters.skip ?? 0) + 1}–{Math.min((filters.skip ?? 0) + (filters.limit ?? 20), listQuery.data?.total ?? 0)}{' '}
                of {listQuery.data?.total ?? 0}
              </span>
              <Select
                value={String(filters.limit ?? 20)}
                onValueChange={(v) => setFilters({ ...filters, limit: Number(v), skip: 0 })}
              >
                <SelectTrigger className="h-8 w-[70px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
              <span>per page</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                disabled={!listQuery.data?.has_prev}
                onClick={() =>
                  setFilters({
                    ...filters,
                    skip: Math.max(0, (filters.skip ?? 0) - (filters.limit ?? 20)),
                  })
                }
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                disabled={!listQuery.data?.has_next}
                onClick={() =>
                  setFilters({
                    ...filters,
                    skip: (filters.skip ?? 0) + (filters.limit ?? 20),
                  })
                }
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deletingDeviceId}
        onOpenChange={(open) => { if (!open) setDeletingDeviceId(null); }}
        title="Delete device"
        description="Are you sure you want to delete this device? Active transmissions will be stopped and the device configuration will be lost."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={confirmDelete}
      />
    </PageContainer>
  );
}
