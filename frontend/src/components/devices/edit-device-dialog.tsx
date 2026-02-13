import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useUpdateDevice } from "@/hooks/useDevices";
import { useUIStore } from "@/app/store/ui-store";
import type { DeviceSummary } from "@/types/device";

const editDeviceSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().max(500).optional().or(z.literal("")),
  device_type: z.enum(["sensor", "datalogger"]),
  tags: z.string().optional(),
  connection_id: z.string().optional().or(z.literal("")),
  transmission_enabled: z.boolean(),
  transmission_frequency: z.number().int().min(1).optional(),
});

type EditDeviceFormValues = z.infer<typeof editDeviceSchema>;

interface Connection {
  id: string;
  name: string;
  protocol_type: string;
}

interface EditDeviceDialogProps {
  device: DeviceSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connections?: Connection[];
}

export function EditDeviceDialog({
  device,
  open,
  onOpenChange,
  connections = [],
}: EditDeviceDialogProps) {
  const updateMutation = useUpdateDevice();
  const addNotification = useUIStore((s) => s.addNotification);

  const form = useForm<EditDeviceFormValues, unknown, EditDeviceFormValues>({
    resolver: zodResolver(editDeviceSchema),
    defaultValues: {
      name: "",
      description: "",
      device_type: "sensor",
      tags: "",
      connection_id: "",
      transmission_enabled: false,
      transmission_frequency: undefined,
    },
  });

  useEffect(() => {
    if (device && open) {
      form.reset({
        name: device.name,
        description: device.description ?? "",
        device_type: device.device_type,
        tags: (device.tags || []).join(", "),
        connection_id: device.connection_id ?? "",
        transmission_enabled: device.transmission_enabled,
        transmission_frequency: undefined,
      });
    }
  }, [device, open, form]);

  const onSubmit = async (values: EditDeviceFormValues) => {
    if (!device) return;
    try {
      const payload: Record<string, unknown> = {
        name: values.name,
        device_type: values.device_type,
        transmission_enabled: values.transmission_enabled,
      };

      payload.description = values.description || null;
      if (values.connection_id) payload.connection_id = values.connection_id;
      else payload.connection_id = null;
      if (values.transmission_frequency)
        payload.transmission_frequency = values.transmission_frequency;
      if (values.tags) {
        payload.tags = values.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean);
      } else {
        payload.tags = [];
      }

      await updateMutation.mutateAsync({
        id: device.id,
        payload: payload as any,
      });

      addNotification({
        type: "success",
        title: "Device updated",
        message: `Device "${values.name}" updated successfully.`,
      });

      onOpenChange(false);
    } catch (error) {
      addNotification({
        type: "error",
        title: "Error updating device",
        message:
          error instanceof Error ? error.message : "An unexpected error occurred.",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Edit Device</DialogTitle>
          <DialogDescription>
            Update device settings, connection, and transmission configuration.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="Device name" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="device_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Type *</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="sensor">Sensor</SelectItem>
                      <SelectItem value="datalogger">Datalogger</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Optional description..." rows={2} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="tags"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tags</FormLabel>
                  <FormControl>
                    <Input placeholder="tag1, tag2, tag3" {...field} />
                  </FormControl>
                  <FormDescription>Comma-separated tags.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="connection_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Connection (MQTT)</FormLabel>
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
                  <FormDescription>
                    Assign an MQTT connection for data transmission.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex items-center gap-6">
              <FormField
                control={form.control}
                name="transmission_enabled"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-2 space-y-0">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="!mt-0">Enable transmission</FormLabel>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="transmission_frequency"
                render={({ field }) => (
                  <FormItem className="flex-1">
                    <FormLabel>Frequency (s)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={1}
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
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
