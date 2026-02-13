import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useDeleteDevice } from "@/hooks/useDevices";
import { useUIStore } from "@/app/store/ui-store";
import type { DeviceSummary } from "@/types/device";

interface DeleteDeviceDialogProps {
  device: DeviceSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeleteDeviceDialog({
  device,
  open,
  onOpenChange,
}: DeleteDeviceDialogProps) {
  const [hardDelete, setHardDelete] = useState(false);
  const deleteMutation = useDeleteDevice();
  const addNotification = useUIStore((s) => s.addNotification);

  const handleDelete = async () => {
    if (!device) return;
    try {
      await deleteMutation.mutateAsync({ id: device.id, hardDelete });
      addNotification({
        type: "success",
        title: "Device deleted",
        message: `Device "${device.name}" has been ${hardDelete ? "permanently" : "soft"} deleted.`,
      });
      onOpenChange(false);
    } catch (error) {
      addNotification({
        type: "error",
        title: "Error deleting device",
        message: error instanceof Error ? error.message : "An unexpected error occurred.",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Delete Device
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete <strong>"{device?.name}"</strong>?
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {device?.transmission_enabled && (
            <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-3 text-sm">
              <p className="font-medium text-yellow-600 dark:text-yellow-400">
                Warning: This device has active transmission.
              </p>
              <p className="text-muted-foreground mt-1">
                Deleting it will stop all ongoing transmissions.
              </p>
            </div>
          )}

          <div className="flex items-center gap-3 rounded-lg border p-3">
            <Switch
              id="hard-delete"
              checked={hardDelete}
              onCheckedChange={setHardDelete}
            />
            <div>
              <Label htmlFor="hard-delete" className="font-medium">
                Permanent deletion
              </Label>
              <p className="text-xs text-muted-foreground">
                {hardDelete
                  ? "Device will be permanently removed and cannot be recovered."
                  : "Device will be soft-deleted and can be restored later."}
              </p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={deleteMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              "Delete"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
