import { useState } from 'react';
import {
  Plus,
  Trash2,
  Cpu,
  Radio,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
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
import type { ProjectDevice } from '@/types/project';
import { useUnassignedDevices, useAssignDevices, useUnassignDevice } from '@/hooks/useProjects';

interface ProjectDevicesPanelProps {
  projectId: string;
  devices: ProjectDevice[];
  isLoading?: boolean;
  onRefresh?: () => void;
}

export function ProjectDevicesPanel({
  projectId,
  devices,
  isLoading,
  onRefresh,
}: ProjectDevicesPanelProps) {
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [selectorSearch, setSelectorSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const unassignedQuery = useUnassignedDevices(
    selectorOpen ? { search: selectorSearch || undefined, limit: 50 } : undefined
  );
  const assignMutation = useAssignDevices();
  const unassignMutation = useUnassignDevice();

  const handleAssign = () => {
    if (selectedIds.size === 0) return;
    assignMutation.mutate(
      { projectId, payload: { device_ids: Array.from(selectedIds) } },
      {
        onSuccess: () => {
          setSelectorOpen(false);
          setSelectedIds(new Set());
          onRefresh?.();
        },
      }
    );
  };

  const handleUnassign = (deviceId: string) => {
    unassignMutation.mutate(
      { projectId, deviceId },
      { onSuccess: () => onRefresh?.() }
    );
  };

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  return (
    <>
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">
              Devices ({devices.length})
            </CardTitle>
            <Button size="sm" onClick={() => setSelectorOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Devices
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {devices.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-6">
              No devices assigned yet. Click "Add Devices" to get started.
            </p>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Dataset</TableHead>
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {devices.map((device) => (
                    <TableRow key={device.id}>
                      <TableCell className="font-medium">
                        <div className="flex flex-col">
                          <span>{device.name}</span>
                          <code className="text-xs text-muted-foreground font-mono">
                            {device.device_id}
                          </code>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize text-xs">
                          {device.device_type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {device.transmission_enabled ? (
                          <Badge variant="default" className="gap-1 text-xs">
                            <Radio className="h-3 w-3" />
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">
                            {device.status}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={device.has_dataset ? 'default' : 'secondary'} className="text-xs">
                          {device.dataset_count}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive"
                          onClick={() => handleUnassign(device.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Device Selector Dialog */}
      <Dialog open={selectorOpen} onOpenChange={setSelectorOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Add Devices to Project</DialogTitle>
            <DialogDescription>
              Select unassigned devices to add to this project.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search devices..."
                value={selectorSearch}
                onChange={(e) => setSelectorSearch(e.target.value)}
                className="pl-9"
              />
            </div>

            <div className="max-h-[300px] overflow-y-auto rounded-md border">
              {unassignedQuery.isLoading ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  Loading...
                </div>
              ) : (unassignedQuery.data?.items ?? []).length === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  No unassigned devices found
                </div>
              ) : (
                <div className="divide-y">
                  {(unassignedQuery.data?.items ?? []).map((device) => (
                    <label
                      key={device.id}
                      className="flex items-center gap-3 p-3 hover:bg-muted/50 cursor-pointer"
                    >
                      <Checkbox
                        checked={selectedIds.has(device.id)}
                        onCheckedChange={() => toggleSelect(device.id)}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Cpu className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span className="font-medium text-sm truncate">{device.name}</span>
                          <Badge variant="outline" className="text-xs capitalize flex-shrink-0">
                            {device.device_type}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground ml-6">
                          {device.device_id} · {device.dataset_count} dataset(s)
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {selectedIds.size > 0 && (
              <p className="text-sm text-muted-foreground">
                {selectedIds.size} device{selectedIds.size > 1 ? 's' : ''} selected
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectorOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAssign}
              disabled={selectedIds.size === 0 || assignMutation.isPending}
            >
              {assignMutation.isPending ? 'Adding...' : `Add ${selectedIds.size} Device${selectedIds.size !== 1 ? 's' : ''}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
