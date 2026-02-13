import * as React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Save, Loader2 } from "lucide-react";

import { PageContainer } from "@/components/layout/page-container";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Form } from "@/components/ui/form";
import { DeviceBasicInfoSection } from "@/components/devices/device-basic-info-section";
import { DeviceMetadataSection } from "@/components/devices/device-metadata-section";
import { DeviceCommunicationSection } from "@/components/devices/device-communication-section";
import {
  useDevice,
  useCreateDevice,
  useUpdateDevice,
  usePatchDevice,
} from "@/hooks/useDevices";
import { useConnections } from "@/hooks/useConnections";
import { useDatasets } from "@/hooks/useDatasets";
import { useUIStore } from "@/app/store/ui-store";
import { deviceFormSchema } from "@/types/device";
import type { DeviceFormValues } from "@/types/device";

export default function DeviceFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = !!id;
  const addNotification = useUIStore((s) => s.addNotification);

  const [activeTab, setActiveTab] = React.useState("basic");
  const [localTransmissionStatus, setLocalTransmissionStatus] = React.useState<string | null>(null);
  const [localRowIndex, setLocalRowIndex] = React.useState<number | null>(null);
  const [localLastTransmission, setLocalLastTransmission] = React.useState<string | null>(null);

  // Queries
  const deviceQuery = useDevice(id ?? "");
  const connectionsQuery = useConnections({ skip: 0, limit: 100 });
  const datasetsQuery = useDatasets({ skip: 0, limit: 100 });

  // Mutations
  const createMutation = useCreateDevice();
  const updateMutation = useUpdateDevice();
  const patchMutation = usePatchDevice();

  const connections = (connectionsQuery.data?.items ?? []).map((c: any) => ({
    id: c.id,
    name: c.name,
    protocol_type: c.protocol_type,
  }));

  const datasets = (datasetsQuery.data?.items ?? []).map((d: any) => ({
    id: d.id,
    name: d.name,
    row_count: d.row_count ?? 0,
    status: d.status,
  }));

  const form = useForm<DeviceFormValues>({
    resolver: zodResolver(deviceFormSchema),
    defaultValues: {
      name: "",
      device_id: "",
      device_type: "sensor",
      description: "",
      tags: "",
      is_active: true,
      connection_id: "",
      transmission_enabled: false,
      transmission_frequency: undefined,
      include_device_id: true,
      include_timestamp: true,
      auto_reset: true,
      batch_size: undefined,
      manufacturer: null,
      model: null,
      firmware_version: null,
      ip_address: null,
      mac_address: null,
      port: null,
      capabilities: [],
      custom_metadata: {},
    },
  });

  // Populate form when device data loads
  React.useEffect(() => {
    if (!deviceQuery.data || !isEditing) return;
    const d = deviceQuery.data;
    form.reset({
      name: d.name,
      device_id: d.device_id ?? "",
      device_type: d.device_type,
      description: d.description ?? "",
      tags: (d.tags || []).join(", "),
      is_active: d.is_active,
      connection_id: d.connection_id ?? "",
      transmission_enabled: d.transmission_enabled,
      transmission_frequency: d.transmission_frequency ?? undefined,
      include_device_id: d.transmission_config?.include_device_id !== false,
      include_timestamp: d.transmission_config?.include_timestamp !== false,
      auto_reset: d.transmission_config?.auto_reset !== false,
      batch_size: d.transmission_config?.batch_size ?? undefined,
      manufacturer: d.manufacturer ?? null,
      model: d.model ?? null,
      firmware_version: d.firmware_version ?? null,
      ip_address: d.ip_address ?? null,
      mac_address: d.mac_address ?? null,
      port: d.port ?? null,
      capabilities: d.capabilities ?? [],
      custom_metadata: (d.device_metadata as Record<string, unknown>) ?? {},
    });
  }, [deviceQuery.data, isEditing, form]);

  const onSubmit = async (values: DeviceFormValues) => {
    try {
      const tags = values.tags
        ? values.tags.split(",").map((t: string) => t.trim()).filter(Boolean)
        : [];

      const transmissionConfig: Record<string, unknown> = {
        auto_reset: values.auto_reset,
        include_device_id: values.include_device_id,
        include_timestamp: values.include_timestamp,
      };
      if (values.batch_size) transmissionConfig.batch_size = values.batch_size;

      const metadata: Record<string, unknown> = {};
      if (values.manufacturer) metadata.manufacturer = values.manufacturer;
      if (values.model) metadata.model = values.model;
      if (values.firmware_version) metadata.firmware_version = values.firmware_version;
      if (values.ip_address) metadata.ip_address = values.ip_address;
      if (values.mac_address) metadata.mac_address = values.mac_address;
      if (values.port) metadata.port = values.port;
      if (values.capabilities?.length) metadata.capabilities = values.capabilities;
      if (values.custom_metadata && Object.keys(values.custom_metadata).length > 0) {
        metadata.custom_metadata = values.custom_metadata;
      }

      if (isEditing && id) {
        const payload: Record<string, unknown> = {
          name: values.name,
          device_type: values.device_type,
          description: values.description || null,
          tags,
          is_active: values.is_active,
          connection_id: values.connection_id || null,
          transmission_enabled: values.transmission_enabled,
          transmission_config: transmissionConfig,
        };
        if (values.transmission_frequency) {
          payload.transmission_frequency = values.transmission_frequency;
        }

        await updateMutation.mutateAsync({ id, payload: payload as any });

        // Update metadata separately if any fields are set
        if (Object.keys(metadata).length > 0) {
          await patchMutation.mutateAsync({ id, payload: metadata as any });
        }

        addNotification({
          type: "success",
          title: "Device updated",
          message: `Device "${values.name}" updated successfully.`,
        });
      } else {
        const payload: Record<string, unknown> = {
          name: values.name,
          device_type: values.device_type,
          transmission_enabled: values.transmission_enabled,
          tags,
          is_active: values.is_active,
          transmission_config: transmissionConfig,
        };
        if (values.description) payload.description = values.description;
        if (values.device_id) payload.device_id = values.device_id;
        if (values.connection_id) payload.connection_id = values.connection_id;
        if (values.transmission_frequency) {
          payload.transmission_frequency = values.transmission_frequency;
        }
        if (Object.keys(metadata).length > 0) payload.metadata = metadata;

        const created = await createMutation.mutateAsync(payload as any);

        addNotification({
          type: "success",
          title: "Device created",
          message: `Device "${values.name}" created successfully.`,
        });

        // Navigate to edit mode so user can link datasets
        navigate(`/devices/${created.id}/edit`, { replace: true });
        return;
      }
    } catch (error) {
      addNotification({
        type: "error",
        title: isEditing ? "Error updating device" : "Error creating device",
        message: error instanceof Error ? error.message : "An unexpected error occurred.",
      });
    }
  };

  const handleTransmissionAction = async (action: "play" | "pause" | "stop") => {
    if (!id) return;
    try {
      switch (action) {
        case "play":
          await patchMutation.mutateAsync({
            id,
            payload: { transmission_enabled: true } as any,
          });
          form.setValue("transmission_enabled", true);
          setLocalTransmissionStatus("transmitting");
          addNotification({ type: "success", title: "Transmission started", message: "" });
          break;
        case "pause":
          await patchMutation.mutateAsync({
            id,
            payload: { transmission_enabled: false } as any,
          });
          form.setValue("transmission_enabled", false);
          setLocalTransmissionStatus("paused");
          addNotification({ type: "success", title: "Transmission paused", message: "" });
          break;
        case "stop":
          await patchMutation.mutateAsync({
            id,
            payload: { transmission_enabled: false, current_row_index: 0 } as any,
          });
          form.setValue("transmission_enabled", false);
          setLocalTransmissionStatus("stopped");
          setLocalRowIndex(0);
          addNotification({ type: "success", title: "Transmission stopped", message: "Row index reset to 0." });
          break;
      }
    } catch (error) {
      addNotification({
        type: "error",
        title: "Transmission error",
        message: error instanceof Error ? error.message : "Failed to update transmission.",
      });
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const isLoading = isEditing && deviceQuery.isLoading;

  if (isLoading) {
    return (
      <PageContainer title="Loading device..." showBackButton backButtonHref="/devices">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={isEditing ? `Edit: ${deviceQuery.data?.name ?? "Device"}` : "New Device"}
      description={
        isEditing
          ? "Update device settings, metadata, and communication configuration."
          : "Create a new IoT device. Configure its identity, metadata, and communication."
      }
      showBackButton
      backButtonHref="/devices"
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="basic">Basic Info</TabsTrigger>
                <TabsTrigger value="metadata">Metadata</TabsTrigger>
                <TabsTrigger value="communication">Communication</TabsTrigger>
              </TabsList>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/devices")}
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
                <Button type="submit" disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      {isEditing ? "Save Changes" : "Create Device"}
                    </>
                  )}
                </Button>
              </div>
            </div>

            <TabsContent value="basic" className="mt-0">
              <DeviceBasicInfoSection form={form} isEditing={isEditing} />
            </TabsContent>

            <TabsContent value="metadata" className="mt-0">
              <DeviceMetadataSection form={form} />
            </TabsContent>

            <TabsContent value="communication" className="mt-0">
              <DeviceCommunicationSection
                form={form}
                deviceId={id}
                connections={connections}
                datasets={datasets}
                isEditing={isEditing}
                onTransmissionAction={handleTransmissionAction}
                transmissionStatus={(localTransmissionStatus ?? deviceQuery.data?.status ?? "idle") as any}
                lastTransmissionAt={localLastTransmission ?? deviceQuery.data?.last_transmission_at}
                currentRowIndex={localRowIndex ?? deviceQuery.data?.current_row_index ?? 0}
                onRefresh={async () => {
                  const result = await deviceQuery.refetch();
                  if (result.data) {
                    setLocalTransmissionStatus(result.data.status ?? "idle");
                    setLocalRowIndex(result.data.current_row_index ?? 0);
                    setLocalLastTransmission(result.data.last_transmission_at ?? null);
                  }
                }}
              />
            </TabsContent>
          </Tabs>
        </form>
      </Form>
    </PageContainer>
  );
}
