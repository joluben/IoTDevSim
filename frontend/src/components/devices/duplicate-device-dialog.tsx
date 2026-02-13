import { useState, useEffect } from "react";
import { Copy, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { useDuplicateDevice, usePreviewDuplicate } from "@/hooks/useDevices";
import { useUIStore } from "@/app/store/ui-store";
import type { DeviceSummary } from "@/types/device";

interface DuplicateDeviceDialogProps {
  device: DeviceSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DuplicateDeviceDialog({
  device,
  open,
  onOpenChange,
}: DuplicateDeviceDialogProps) {
  const [count, setCount] = useState(1);
  const [namePrefix, setNamePrefix] = useState("");
  const [previewNames, setPreviewNames] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);

  const duplicateMutation = useDuplicateDevice();
  const previewMutation = usePreviewDuplicate();
  const addNotification = useUIStore((s) => s.addNotification);

  useEffect(() => {
    if (device && open) {
      setCount(1);
      setNamePrefix(device.name);
      setPreviewNames([]);
      setProgress(0);
    }
  }, [device, open]);

  const handlePreview = async () => {
    if (!device) return;
    try {
      const result = await previewMutation.mutateAsync({
        id: device.id,
        payload: { count, name_prefix: namePrefix || undefined },
      });
      setPreviewNames(result.names);
    } catch (error) {
      addNotification({
        type: "error",
        title: "Preview failed",
        message: error instanceof Error ? error.message : "Could not generate preview.",
      });
    }
  };

  const handleDuplicate = async () => {
    if (!device) return;
    try {
      setProgress(10);
      const result = await duplicateMutation.mutateAsync({
        id: device.id,
        payload: { count, name_prefix: namePrefix || undefined },
      });
      setProgress(100);

      addNotification({
        type: "success",
        title: "Devices duplicated",
        message: `${result.created_count} device(s) created successfully.`,
      });

      setTimeout(() => {
        onOpenChange(false);
      }, 500);
    } catch (error) {
      setProgress(0);
      addNotification({
        type: "error",
        title: "Duplication failed",
        message: error instanceof Error ? error.message : "An unexpected error occurred.",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Copy className="h-5 w-5" />
            Duplicate Device
          </DialogTitle>
          <DialogDescription>
            Create copies of "{device?.name}". Each copy gets a unique reference and incremental name.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="count">Number of copies</Label>
              <Input
                id="count"
                type="number"
                min={1}
                max={50}
                value={count}
                onChange={(e) => setCount(Math.min(50, Math.max(1, Number(e.target.value) || 1)))}
              />
              <p className="text-xs text-muted-foreground">1–50 copies</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="prefix">Name prefix</Label>
              <Input
                id="prefix"
                value={namePrefix}
                onChange={(e) => setNamePrefix(e.target.value)}
                placeholder={device?.name ?? "Device"}
              />
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handlePreview}
            disabled={previewMutation.isPending}
          >
            {previewMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : null}
            Preview names
          </Button>

          {previewNames.length > 0 && (
            <div className="space-y-2">
              <Label>Generated names</Label>
              <ScrollArea className="h-[120px] rounded-md border p-3">
                <div className="space-y-1">
                  {previewNames.map((name, i) => (
                    <div key={i} className="text-sm font-mono">
                      {name}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {duplicateMutation.isPending && (
            <div className="space-y-2">
              <Progress value={progress} className="h-2" />
              <p className="text-xs text-muted-foreground text-center">
                Creating {count} device(s)...
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={duplicateMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleDuplicate}
            disabled={duplicateMutation.isPending || count < 1}
          >
            {duplicateMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Duplicating...
              </>
            ) : (
              <>
                <Copy className="h-4 w-4 mr-2" />
                Duplicate ({count})
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
