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
import { Textarea } from "@/components/ui/textarea";
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
import { X } from "lucide-react";
import type { DeviceFormValues } from "@/types/device";

interface DeviceBasicInfoSectionProps {
  form: UseFormReturn<DeviceFormValues>;
  isEditing: boolean;
}

export function DeviceBasicInfoSection({ form, isEditing }: DeviceBasicInfoSectionProps) {
  const tagsValue = form.watch("tags") || "";
  const tagsArray = tagsValue
    .split(",")
    .map((t: string) => t.trim())
    .filter(Boolean);

  const removeTag = (tagToRemove: string) => {
    const newTags = tagsArray.filter((t: string) => t !== tagToRemove).join(", ");
    form.setValue("tags", newTags, { shouldDirty: true });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Device Identity</CardTitle>
          <CardDescription>
            Basic identification for the device. Name and type are required.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="Temperature Sensor 1" {...field} />
                  </FormControl>
                  <FormDescription>2–100 characters</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="device_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Reference</FormLabel>
                  <FormControl>
                    <Input
                      placeholder={isEditing ? "" : "Auto-generated"}
                      maxLength={8}
                      className="font-mono uppercase"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    8-character alphanumeric ID.{" "}
                    {!isEditing && "Leave blank to auto-generate."}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
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
                      <SelectItem value="sensor">
                        <div className="flex flex-col">
                          <span>Sensor</span>
                          <span className="text-xs text-muted-foreground">
                            Single dataset, 1 row per transmission
                          </span>
                        </div>
                      </SelectItem>
                      <SelectItem value="datalogger">
                        <div className="flex flex-col">
                          <span>Datalogger</span>
                          <span className="text-xs text-muted-foreground">
                            Multiple datasets, batch transmission
                          </span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-col justify-end">
                  <div className="flex items-center gap-3 rounded-lg border p-3">
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <div className="space-y-0.5">
                      <FormLabel className="!mt-0">Active</FormLabel>
                      <FormDescription className="text-xs">
                        Inactive devices cannot transmit data.
                      </FormDescription>
                    </div>
                  </div>
                </FormItem>
              )}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
          <CardDescription>
            Optional description and tags for organization.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Description</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="Describe the purpose of this device..."
                    rows={3}
                    {...field}
                  />
                </FormControl>
                <FormDescription>Max 500 characters</FormDescription>
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
                  <Input
                    placeholder="Type tags separated by commas..."
                    {...field}
                  />
                </FormControl>
                {tagsArray.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {tagsArray.map((tag: string) => (
                      <Badge
                        key={tag}
                        variant="secondary"
                        className="gap-1 pr-1"
                      >
                        {tag}
                        <button
                          type="button"
                          onClick={() => removeTag(tag)}
                          className="ml-0.5 rounded-full hover:bg-muted p-0.5"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                )}
                <FormMessage />
              </FormItem>
            )}
          />
        </CardContent>
      </Card>
    </div>
  );
}
