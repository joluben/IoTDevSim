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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, X, Trash2 } from "lucide-react";
import type { DeviceFormValues } from "@/types/device";

interface DeviceMetadataSectionProps {
  form: UseFormReturn<DeviceFormValues>;
}

export function DeviceMetadataSection({ form }: DeviceMetadataSectionProps) {
  const [newCapability, setNewCapability] = useState("");
  const [newMetaKey, setNewMetaKey] = useState("");
  const [newMetaValue, setNewMetaValue] = useState("");

  const capabilities = form.watch("capabilities") || [];
  const customMetadata = form.watch("custom_metadata") || {};

  const addCapability = () => {
    const trimmed = newCapability.trim();
    if (!trimmed || capabilities.includes(trimmed)) return;
    form.setValue("capabilities", [...capabilities, trimmed], { shouldDirty: true });
    setNewCapability("");
  };

  const removeCapability = (cap: string) => {
    form.setValue(
      "capabilities",
      capabilities.filter((c: string) => c !== cap),
      { shouldDirty: true }
    );
  };

  const addCustomMeta = () => {
    const key = newMetaKey.trim();
    const value = newMetaValue.trim();
    if (!key) return;
    form.setValue("custom_metadata", { ...customMetadata, [key]: value }, { shouldDirty: true });
    setNewMetaKey("");
    setNewMetaValue("");
  };

  const removeCustomMeta = (key: string) => {
    const next = { ...customMetadata };
    delete next[key];
    form.setValue("custom_metadata", next, { shouldDirty: true });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Hardware Information</CardTitle>
          <CardDescription>
            Optional static data about the physical device being simulated.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="manufacturer"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Manufacturer</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. Bosch, Siemens" {...field} value={field.value ?? ""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Model</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. BME280" {...field} value={field.value ?? ""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="firmware_version"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Firmware Version</FormLabel>
                <FormControl>
                  <Input placeholder="e.g. 1.2.3" {...field} value={field.value ?? ""} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Network</CardTitle>
          <CardDescription>
            Network addressing information for the simulated device.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="ip_address"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>IP Address</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g. 192.168.1.100"
                      {...field}
                      value={field.value ?? ""}
                    />
                  </FormControl>
                  <FormDescription>IPv4 or IPv6</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="mac_address"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>MAC Address</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g. AA:BB:CC:DD:EE:FF"
                      maxLength={17}
                      {...field}
                      value={field.value ?? ""}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="port"
            render={({ field }) => (
              <FormItem className="max-w-[200px]">
                <FormLabel>Port</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={1}
                    max={65535}
                    placeholder="e.g. 8883"
                    value={field.value ?? ""}
                    onChange={(e) => {
                      const val = e.target.value;
                      field.onChange(val === "" ? null : Number(val));
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Capabilities</CardTitle>
          <CardDescription>
            List of supported operations or measurement types.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="e.g. temperature, humidity"
              value={newCapability}
              onChange={(e) => setNewCapability(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCapability();
                }
              }}
              className="flex-1"
            />
            <Button type="button" variant="outline" size="icon" onClick={addCapability}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          {capabilities.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {capabilities.map((cap: string) => (
                <Badge key={cap} variant="secondary" className="gap-1 pr-1">
                  {cap}
                  <button
                    type="button"
                    onClick={() => removeCapability(cap)}
                    className="ml-0.5 rounded-full hover:bg-muted p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Custom Metadata</CardTitle>
          <CardDescription>
            Free-form key-value pairs for additional device information.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="Key"
              value={newMetaKey}
              onChange={(e) => setNewMetaKey(e.target.value)}
              className="flex-1"
            />
            <Input
              placeholder="Value"
              value={newMetaValue}
              onChange={(e) => setNewMetaValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustomMeta();
                }
              }}
              className="flex-1"
            />
            <Button type="button" variant="outline" size="icon" onClick={addCustomMeta}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          {Object.keys(customMetadata).length > 0 && (
            <div className="rounded-md border">
              {Object.entries(customMetadata).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between px-3 py-2 border-b last:border-b-0"
                >
                  <div className="flex items-center gap-3 text-sm">
                    <span className="font-mono font-medium">{key}</span>
                    <span className="text-muted-foreground">{String(value)}</span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => removeCustomMeta(key)}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
