import { useState } from "react";
import { UseFormReturn } from "react-hook-form";
import {
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Play,
  Pause,
  Square,
  Database,
  X,
  Radio,
  Clock,
  RotateCcw,
  RefreshCw,
} from "lucide-react";
import { useLinkDataset, useUnlinkDataset, useDeviceDatasets } from "@/hooks/useDevices";
import { useUIStore } from "@/app/store/ui-store";
import type { DeviceFormValues } from "@/types/device";

interface Connection {
  id: string;
  name: string;
  protocol_type: string;
}

interface Dataset {
  id: string;
  name: string;
  row_count: number;
  status?: string;
}

interface DeviceCommunicationSectionProps {
  form: UseFormReturn<DeviceFormValues>;
  deviceId?: string;
  connections: Connection[];
  datasets: Dataset[];
  isEditing: boolean;
  onTransmissionAction?: (action: "play" | "pause" | "stop") => void;
  transmissionStatus?: "idle" | "transmitting" | "paused" | "stopped" | "error";
  lastTransmissionAt?: string | null;
  currentRowIndex?: number;
  onRefresh?: () => void | Promise<void>;
}

export function DeviceCommunicationSection({
  form,
  deviceId,
  connections,
  datasets,
  isEditing,
  onTransmissionAction,
  transmissionStatus = "idle",
  lastTransmissionAt,
  currentRowIndex = 0,
  onRefresh,
}: DeviceCommunicationSectionProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const linkMutation = useLinkDataset();
  const unlinkMutation = useUnlinkDataset();
  const addNotification = useUIStore((s) => s.addNotification);

  const deviceDatasetsQuery = useDeviceDatasets(deviceId ?? "");
  const linkedDatasets = deviceDatasetsQuery.data?.datasets ?? [];
  const linkedDatasetIds = new Set(linkedDatasets.map((d: { dataset_id: string }) => d.dataset_id));
  const availableDatasets = datasets.filter((d) => !linkedDatasetIds.has(d.id));

  const deviceType = form.watch("device_type");
  const transmissionEnabled = form.watch("transmission_enabled");
  const connectionId = form.watch("connection_id");
  const isSensor = deviceType === "sensor";
  const canLinkMore = !isSensor || linkedDatasets.length === 0;
  const hasDataset = linkedDatasets.length > 0;
  const hasConnection = !!connectionId && connectionId !== "" && connectionId !== "__none__";
  const canEnableTransmission = hasDataset && hasConnection;

  const handleLink = async () => {
    if (!deviceId || !selectedDatasetId) return;
    try {
      await linkMutation.mutateAsync({
        deviceId,
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
    if (!deviceId) return;
    try {
      await unlinkMutation.mutateAsync({ deviceId, datasetId });
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case "transmitting":
        return "text-green-500";
      case "paused":
        return "text-yellow-500";
      case "stopped":
        return "text-muted-foreground";
      case "error":
        return "text-red-500";
      default:
        return "text-muted-foreground";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "transmitting":
        return "Transmitting";
      case "paused":
        return "Paused";
      case "stopped":
        return "Stopped";
      case "error":
        return "Error";
      default:
        return "Idle";
    }
  };

  return (
    <div className="space-y-6">
      {/* Datasets */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Datasets
          </CardTitle>
          <CardDescription>
            {isSensor
              ? "Sensors support a single dataset. Data is transmitted row by row."
              : "Dataloggers support multiple datasets. Each represents a different sensor/measurement source."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isEditing && deviceId ? (
            <>
              {linkedDatasets.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Linked Datasets</p>
                  <div className="flex flex-wrap gap-2">
                    {linkedDatasets.map((link: { dataset_id: string }) => (
                      <Badge key={link.dataset_id} variant="secondary" className="gap-1 pr-1 py-1">
                        <Database className="h-3 w-3" />
                        {getDatasetName(link.dataset_id)}
                        <button
                          type="button"
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

              {canLinkMore && (
                <div className="flex gap-2">
                  <Select value={selectedDatasetId} onValueChange={setSelectedDatasetId}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select a dataset..." />
                    </SelectTrigger>
                    <SelectContent>
                      {availableDatasets.length === 0 ? (
                        <SelectItem value="__empty__" disabled>
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
                    type="button"
                    onClick={handleLink}
                    disabled={!selectedDatasetId || linkMutation.isPending}
                    size="sm"
                  >
                    {linkMutation.isPending ? "Linking..." : "Link"}
                  </Button>
                </div>
              )}

              {isSensor && linkedDatasets.length >= 1 && (
                <p className="text-xs text-muted-foreground">
                  Sensors only support 1 dataset. Unlink the current one to link a different dataset.
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Save the device first, then you can link datasets.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Connection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Radio className="h-5 w-5" />
            Connection
          </CardTitle>
          <CardDescription>
            Assign a connection endpoint for data transmission (MQTT, HTTP, Kafka).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FormField
            control={form.control}
            name="connection_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Connection</FormLabel>
                <Select
                  onValueChange={(v) => field.onChange(v === "__none__" ? "" : v)}
                  value={field.value || "__none__"}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="No connection" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="__none__">None</SelectItem>
                    {connections.map((conn) => (
                      <SelectItem key={conn.id} value={conn.id}>
                        {conn.name} ({conn.protocol_type})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </CardContent>
      </Card>

      {/* Transmission Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Transmission
          </CardTitle>
          <CardDescription>
            Configure how and when data is sent from this device.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isEditing && !canEnableTransmission && (
            <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-3 text-sm text-muted-foreground">
              {!hasDataset && !hasConnection
                ? "Link a dataset and assign a connection before enabling transmission."
                : !hasDataset
                  ? "Link a dataset before enabling transmission."
                  : "Assign a connection before enabling transmission."}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="transmission_enabled"
              render={({ field }) => (
                <FormItem className="flex flex-col justify-center">
                  <div className="flex items-center gap-3 rounded-lg border p-3">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={(checked) => {
                          if (checked && isEditing && !canEnableTransmission) return;
                          field.onChange(checked);
                        }}
                        disabled={isEditing && !canEnableTransmission && !field.value}
                      />
                    </FormControl>
                    <div className="space-y-0.5">
                      <FormLabel className="!mt-0">Enable transmission</FormLabel>
                      <FormDescription className="text-xs">
                        Device must have a dataset and connection.
                      </FormDescription>
                    </div>
                  </div>
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="transmission_frequency"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Frequency (seconds)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={172800}
                      placeholder="10"
                      value={field.value ?? ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        field.onChange(val === "" ? undefined : Number(val));
                      }}
                      onBlur={field.onBlur}
                      name={field.name}
                      ref={field.ref}
                    />
                  </FormControl>
                  <FormDescription>1 second to 48 hours (172800s)</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <Separator />

          {/* Payload options */}
          <div className="space-y-3">
            <p className="text-sm font-medium">Payload Options</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="include_device_id"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 rounded-lg border p-3 space-y-0">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <div>
                      <FormLabel className="!mt-0">Include device_id</FormLabel>
                      <FormDescription className="text-xs">
                        Add device reference to payload
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="include_timestamp"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 rounded-lg border p-3 space-y-0">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <div>
                      <FormLabel className="!mt-0">Include timestamp</FormLabel>
                      <FormDescription className="text-xs">
                        Add timestamp to each payload
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="auto_reset"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 rounded-lg border p-3 space-y-0">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <div>
                      <FormLabel className="!mt-0 flex items-center gap-1.5">
                        <RotateCcw className="h-3.5 w-3.5" />
                        Auto-reset
                      </FormLabel>
                      <FormDescription className="text-xs">
                        Restart from row 0 at dataset end
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />

              {!isSensor && (
                <FormField
                  control={form.control}
                  name="batch_size"
                  render={({ field }) => (
                    <FormItem className="flex flex-col justify-center rounded-lg border p-3">
                      <FormLabel>Batch size</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={1}
                          placeholder="1"
                          value={field.value ?? ""}
                          onChange={(e) => {
                            const val = e.target.value;
                            field.onChange(val === "" ? undefined : Number(val));
                          }}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          className="h-8"
                        />
                      </FormControl>
                      <FormDescription className="text-xs">
                        Rows per transmission (Datalogger only)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
            </div>
          </div>

          {/* Transmission Controls — only in edit mode */}
          {isEditing && (
            <>
              <Separator />
              <div className="space-y-3">
                <p className="text-sm font-medium">Transmission Controls</p>
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    variant={transmissionStatus === "transmitting" ? "secondary" : "default"}
                    size="sm"
                    onClick={() => onTransmissionAction?.("play")}
                    disabled={!transmissionEnabled || transmissionStatus === "transmitting"}
                    className="gap-1.5"
                  >
                    <Play className="h-4 w-4" />
                    Play
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => onTransmissionAction?.("pause")}
                    disabled={transmissionStatus !== "transmitting"}
                    className="gap-1.5"
                  >
                    <Pause className="h-4 w-4" />
                    Pause
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => onTransmissionAction?.("stop")}
                    disabled={transmissionStatus === "idle" || transmissionStatus === "stopped"}
                    className="gap-1.5"
                  >
                    <Square className="h-4 w-4" />
                    Stop
                  </Button>

                  <div className="ml-auto flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1.5">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          transmissionStatus === "transmitting"
                            ? "bg-green-500 animate-pulse"
                            : transmissionStatus === "paused"
                              ? "bg-yellow-500"
                              : transmissionStatus === "error"
                                ? "bg-red-500"
                                : "bg-muted-foreground/40"
                        }`}
                      />
                      <span className={getStatusColor(transmissionStatus)}>
                        {getStatusLabel(transmissionStatus)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-6 text-xs text-muted-foreground">
                  {lastTransmissionAt && (
                    <span>
                      Last: {new Date(lastTransmissionAt).toLocaleString()}
                    </span>
                  )}
                  <span>Row index: {currentRowIndex}</span>
                  {onRefresh && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-6 gap-1 px-2 text-xs"
                      onClick={async () => {
                        setIsRefreshing(true);
                        try {
                          await onRefresh();
                        } finally {
                          setIsRefreshing(false);
                        }
                      }}
                      disabled={isRefreshing}
                    >
                      <RefreshCw className={`h-3 w-3 ${isRefreshing ? "animate-spin" : ""}`} />
                      Refresh
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
