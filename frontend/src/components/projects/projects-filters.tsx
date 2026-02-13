import { Search, X } from "lucide-react";
import type { ProjectFilters, TransmissionStatus } from "@/types/project";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ProjectsFiltersProps {
  value: ProjectFilters;
  onChange: (filters: ProjectFilters) => void;
}

export function ProjectsFilters({ value, onChange }: ProjectsFiltersProps) {
  const update = (partial: Partial<ProjectFilters>) =>
    onChange({ ...value, ...partial, skip: 0 });

  const hasActiveFilters =
    value.search ||
    value.transmission_status ||
    value.is_active !== undefined ||
    value.is_archived !== undefined;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[200px] max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search projects..."
          value={value.search || ""}
          onChange={(e) => update({ search: e.target.value || undefined })}
          className="pl-9"
        />
      </div>

      <Select
        value={value.transmission_status || "all"}
        onValueChange={(v) =>
          update({
            transmission_status:
              v === "all" ? undefined : (v as TransmissionStatus),
          })
        }
      >
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="Transmission" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="inactive">Inactive</SelectItem>
          <SelectItem value="active">Active</SelectItem>
          <SelectItem value="paused">Paused</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={
          value.is_archived === undefined
            ? "all"
            : value.is_archived
              ? "archived"
              : "not_archived"
        }
        onValueChange={(v) =>
          update({
            is_archived:
              v === "all" ? undefined : v === "archived",
          })
        }
      >
        <SelectTrigger className="w-[150px]">
          <SelectValue placeholder="Archive" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="not_archived">Active</SelectItem>
          <SelectItem value="archived">Archived</SelectItem>
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
              transmission_status: undefined,
              is_active: undefined,
              is_archived: undefined,
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
