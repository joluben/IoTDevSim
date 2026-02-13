import { useState } from "react";
import { Plus } from "lucide-react";
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
  DialogTrigger,
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
import { useCreateDevice } from "@/hooks/useDevices";
import { useUIStore } from "@/app/store/ui-store";

const createDeviceSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  description: z.string().max(500).optional(),
  device_type: z.enum(["sensor", "datalogger"]),
  device_id: z
    .string()
    .length(8, "Must be exactly 8 characters")
    .regex(/^[A-Za-z0-9]+$/, "Only alphanumeric characters")
    .optional()
    .or(z.literal("")),
  tags: z.string().optional(),
  transmission_enabled: z.boolean().optional(),
  transmission_frequency: z.number().int().min(1).optional(),
});

type CreateDeviceFormValues = z.infer<typeof createDeviceSchema>;

interface CreateDeviceDialogProps {
  triggerLabel?: string;
  triggerVariant?: "default" | "outline" | "ghost" | "secondary";
}

export function CreateDeviceDialog({
  triggerLabel = "New Device",
  triggerVariant = "default",
}: CreateDeviceDialogProps) {
  const [open, setOpen] = useState(false);
  const createMutation = useCreateDevice();
  const addNotification = useUIStore((s) => s.addNotification);

  const form = useForm<CreateDeviceFormValues, unknown, CreateDeviceFormValues>({
    resolver: zodResolver(createDeviceSchema),
    defaultValues: {
      name: "",
      description: "",
      device_type: "sensor",
      device_id: "",
      tags: "",
      transmission_enabled: false,
      transmission_frequency: undefined,
    },
  });

  const onSubmit = async (values: CreateDeviceFormValues) => {
    try {
      const payload: Record<string, unknown> = {
        name: values.name,
        device_type: values.device_type,
        transmission_enabled: values.transmission_enabled ?? false,
      };

      if (values.description) payload.description = values.description;
      if (values.device_id) payload.device_id = values.device_id;
      if (values.transmission_frequency)
        payload.transmission_frequency = values.transmission_frequency;
      if (values.tags) {
        payload.tags = values.tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean);
      }

      await createMutation.mutateAsync(payload as any);

      addNotification({
        type: "success",
        title: "Device created",
        message: `Device "${values.name}" created successfully.`,
      });

      form.reset();
      setOpen(false);
    } catch (error) {
      addNotification({
        type: "error",
        title: "Error creating device",
        message:
          error instanceof Error ? error.message : "An unexpected error occurred.",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant={triggerVariant}>
          <Plus className="h-4 w-4 mr-2" />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create Device</DialogTitle>
          <DialogDescription>
            Add a new IoT device. A unique 8-character reference will be
            auto-generated if not provided.
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
                    <Input placeholder="Temperature Sensor 1" {...field} />
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
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                  <FormDescription>
                    Sensors support 1 dataset. Dataloggers support multiple.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="device_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Device Reference</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Auto-generated"
                      maxLength={8}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Optional 8-character alphanumeric ID. Leave blank to auto-generate.
                  </FormDescription>
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
                    <Textarea
                      placeholder="Optional description..."
                      rows={2}
                      {...field}
                    />
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
                onClick={() => setOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Device"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
