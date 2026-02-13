import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MoreHorizontal,
  Trash2,
  Copy,
  Power,
  Radio,
  Pencil,
} from "lucide-react";
import type { DeviceSummary, DeviceStatus } from "@/types/device";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DuplicateDeviceDialog } from "@/components/devices/duplicate-device-dialog";
import { DeleteDeviceDialog } from "@/components/devices/delete-device-dialog";

interface DevicesTableProps {
  devices: DeviceSummary[];
  onEdit?: (device: DeviceSummary) => void;
  onDelete?: (id: string) => void;
  onDuplicate?: (device: DeviceSummary) => void;
  onLinkDataset?: (device: DeviceSummary) => void;
  onViewMetadata?: (device: DeviceSummary) => void;
  onToggleActive?: (device: DeviceSummary) => void;
  onBulkDelete?: (ids: string[]) => void;
  isLoading?: boolean;
}

export function DevicesTable({
  devices,
  onEdit,
  onDelete,
  onDuplicate,
  onLinkDataset,
  onViewMetadata,
  onToggleActive,
  onBulkDelete,
  isLoading = false,
}: DevicesTableProps) {
  const navigate = useNavigate();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [duplicateDevice, setDuplicateDevice] = useState<DeviceSummary | null>(null);
  const [duplicateOpen, setDuplicateOpen] = useState(false);
  const [deleteDevice, setDeleteDevice] = useState<DeviceSummary | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(devices.map((d) => d.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    const newSelected = new Set(selectedIds);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedIds(newSelected);
  };

  const handleBulkDelete = () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    onBulkDelete?.(ids);
    setSelectedIds(new Set());
  };

  const getStatusBadge = (status: DeviceStatus) => {
    const variants: Record<
      DeviceStatus,
      { variant: "default" | "secondary" | "destructive" | "outline"; label: string }
    > = {
      idle: { variant: "secondary", label: "Idle" },
      transmitting: { variant: "default", label: "Transmitting" },
      error: { variant: "destructive", label: "Error" },
      paused: { variant: "outline", label: "Paused" },
    };
    const config = variants[status];
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const getTypeBadge = (type: string) => {
    return (
      <Badge variant="outline" className="capitalize">
        {type === "datalogger" ? "Datalogger" : "Sensor"}
      </Badge>
    );
  };

  const allSelected = devices.length > 0 && selectedIds.size === devices.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < devices.length;

  return (
    <div className="space-y-4">
      {selectedIds.size > 0 && (
        <Alert>
          <AlertDescription className="flex items-center justify-between">
            <span className="font-medium">
              {selectedIds.size} device{selectedIds.size > 1 ? "s" : ""} selected
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="destructive"
                onClick={handleBulkDelete}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={allSelected}
                  onCheckedChange={handleSelectAll}
                  aria-label="Select all"
                  className={someSelected ? "data-[state=checked]:bg-primary/50" : ""}
                />
              </TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Reference</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Transmission</TableHead>
              <TableHead>Datasets</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                  Loading devices...
                </TableCell>
              </TableRow>
            ) : devices.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                  No devices found
                </TableCell>
              </TableRow>
            ) : (
              devices.map((device) => (
                <TableRow key={device.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(device.id)}
                      onCheckedChange={(checked) =>
                        handleSelectOne(device.id, checked as boolean)
                      }
                      aria-label={`Select ${device.name}`}
                    />
                  </TableCell>
                  <TableCell className="font-medium">
                    <div
                      className="flex flex-col cursor-pointer hover:text-primary transition-colors"
                      onClick={() => navigate(`/devices/${device.id}/edit`)}
                    >
                      <span>{device.name}</span>
                      {device.description && (
                        <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                          {device.description}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">
                      {device.device_id}
                    </code>
                  </TableCell>
                  <TableCell>{getTypeBadge(device.device_type)}</TableCell>
                  <TableCell>{getStatusBadge(device.status)}</TableCell>
                  <TableCell>
                    {device.transmission_enabled ? (
                      <Badge variant="default" className="gap-1">
                        <Radio className="h-3 w-3" />
                        Active
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Off</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={device.has_dataset ? "default" : "secondary"}>
                      {device.dataset_count}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap max-w-[150px]">
                      {(device.tags || []).slice(0, 2).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                      {(device.tags || []).length > 2 && (
                        <Badge variant="outline" className="text-xs">
                          +{device.tags.length - 2}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                          <span className="sr-only">Open menu</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => onEdit?.(device)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => {
                            if (onDuplicate) {
                              onDuplicate(device);
                            } else {
                              setDuplicateDevice(device);
                              setDuplicateOpen(true);
                            }
                          }}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onToggleActive?.(device)}>
                          <Power className="h-4 w-4 mr-2" />
                          {device.is_active ? "Disable" : "Enable"}
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => {
                            if (onDelete) {
                              onDelete(device.id);
                            } else {
                              setDeleteDevice(device);
                              setDeleteOpen(true);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <DuplicateDeviceDialog
        device={duplicateDevice}
        open={duplicateOpen}
        onOpenChange={setDuplicateOpen}
      />

      <DeleteDeviceDialog
        device={deleteDevice}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
      />
    </div>
  );
}
