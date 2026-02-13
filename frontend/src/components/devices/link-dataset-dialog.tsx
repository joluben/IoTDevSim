import { useState } from "react";
import { Database, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useLinkDataset, useUnlinkDataset, useDeviceDatasets } from "@/hooks/useDevices";
import { useUIStore } from "@/app/store/ui-store";
import type { DeviceSummary } from "@/types/device";

interface Dataset {
  id: string;
  name: string;
  row_count: number;
}

interface LinkDatasetDialogProps {
  device: DeviceSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  datasets?: Dataset[];
}

export function LinkDatasetDialog({
  device,
  open,
  onOpenChange,
  datasets = [],
}: LinkDatasetDialogProps) {
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const linkMutation = useLinkDataset();
  const unlinkMutation = useUnlinkDataset();
  const addNotification = useUIStore((s) => s.addNotification);

  const deviceDatasetsQuery = useDeviceDatasets(device?.id ?? "");
  const linkedDatasets = deviceDatasetsQuery.data?.datasets ?? [];

  const linkedDatasetIds = new Set(linkedDatasets.map((d) => d.dataset_id));
  const availableDatasets = datasets.filter((d) => !linkedDatasetIds.has(d.id));

  const handleLink = async () => {
    if (!device || !selectedDatasetId) return;
    try {
      await linkMutation.mutateAsync({
        deviceId: device.id,
        payload: { dataset_id: selectedDatasetId },
      });
      addNotification({
        type: "success",
        title: "Dataset linked",
        message: "Dataset linked to device successfully.",
      });
      setSelectedDatasetId("");
    } catch (error) {
      addNotification({
        type: "error",
        title: "Error linking dataset",
        message: error instanceof Error ? error.message : "An unexpected error occurred.",
      });
    }
  };

  const handleUnlink = async (datasetId: string) => {
    if (!device) return;
    try {
      await unlinkMutation.mutateAsync({
        deviceId: device.id,
        datasetId,
      });
      addNotification({
        type: "success",
        title: "Dataset unlinked",
        message: "Dataset removed from device.",
      });
    } catch (error) {
      addNotification({
        type: "error",
        title: "Error unlinking dataset",
        message: error instanceof Error ? error.message : "An unexpected error occurred.",
      });
    }
  };

  const getDatasetName = (datasetId: string) => {
    const ds = datasets.find((d) => d.id === datasetId);
    return ds?.name ?? datasetId.slice(0, 8);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>Manage Datasets</DialogTitle>
          <DialogDescription>
            Link or unlink datasets for {device?.name ?? "this device"}.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {linkedDatasets.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Linked Datasets</p>
              <div className="flex flex-wrap gap-2">
                {linkedDatasets.map((link) => (
                  <Badge key={link.dataset_id} variant="secondary" className="gap-1 pr-1">
                    <Database className="h-3 w-3" />
                    {getDatasetName(link.dataset_id)}
                    <button
                      onClick={() => handleUnlink(link.dataset_id)}
                      className="ml-1 rounded-full hover:bg-muted p-0.5"
                      disabled={unlinkMutation.isPending}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {linkedDatasets.length === 0 && (
            <p className="text-sm text-muted-foreground">No datasets linked yet.</p>
          )}

          <div className="flex gap-2">
            <Select value={selectedDatasetId} onValueChange={setSelectedDatasetId}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Select a dataset..." />
              </SelectTrigger>
              <SelectContent>
                {availableDatasets.length === 0 ? (
                  <SelectItem value="" disabled>
                    No datasets available
                  </SelectItem>
                ) : (
                  availableDatasets.map((ds) => (
                    <SelectItem key={ds.id} value={ds.id}>
                      {ds.name} ({ds.row_count} rows)
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
            <Button
              onClick={handleLink}
              disabled={!selectedDatasetId || linkMutation.isPending}
              size="sm"
            >
              {linkMutation.isPending ? "Linking..." : "Link"}
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
