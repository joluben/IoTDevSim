import { Search, X } from "lucide-react";
import type { DeviceFilters, DeviceType, DeviceStatus } from "@/types/device";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface DevicesFiltersProps {
  value: DeviceFilters;
  onChange: (filters: DeviceFilters) => void;
}

export function DevicesFilters({ value, onChange }: DevicesFiltersProps) {
  const update = (partial: Partial<DeviceFilters>) =>
    onChange({ ...value, ...partial, skip: 0 });

  const hasActiveFilters =
    value.search ||
    value.device_type ||
    value.status ||
    value.is_active !== undefined ||
    value.transmission_enabled !== undefined ||
    value.has_dataset !== undefined;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[200px] max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search devices..."
          value={value.search || ""}
          onChange={(e) => update({ search: e.target.value || undefined })}
          className="pl-9"
        />
      </div>

      <Select
        value={value.device_type || "all"}
        onValueChange={(v) =>
          update({ device_type: v === "all" ? undefined : (v as DeviceType) })
        }
      >
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="Type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All types</SelectItem>
          <SelectItem value="sensor">Sensor</SelectItem>
          <SelectItem value="datalogger">Datalogger</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={value.status || "all"}
        onValueChange={(v) =>
          update({ status: v === "all" ? undefined : (v as DeviceStatus) })
        }
      >
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="idle">Idle</SelectItem>
          <SelectItem value="transmitting">Transmitting</SelectItem>
          <SelectItem value="error">Error</SelectItem>
          <SelectItem value="paused">Paused</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={
          value.transmission_enabled === undefined
            ? "all"
            : value.transmission_enabled
              ? "enabled"
              : "disabled"
        }
        onValueChange={(v) =>
          update({
            transmission_enabled:
              v === "all" ? undefined : v === "enabled",
          })
        }
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="Transmission" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="enabled">Transmitting</SelectItem>
          <SelectItem value="disabled">Not transmitting</SelectItem>
        </SelectContent>
      </Select>

      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            onChange({
              ...value,
              search: undefined,
              device_type: undefined,
              status: undefined,
              is_active: undefined,
              transmission_enabled: undefined,
              has_dataset: undefined,
              tags: undefined,
              skip: 0,
            })
          }
        >
          <X className="h-4 w-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}
