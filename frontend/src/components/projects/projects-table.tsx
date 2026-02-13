import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MoreHorizontal,
  Trash2,
  Archive,
  ArchiveRestore,
  Pencil,
  Radio,
  Pause,
  Cpu,
} from "lucide-react";
import type { ProjectSummary, TransmissionStatus } from "@/types/project";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface ProjectsTableProps {
  projects: ProjectSummary[];
  onEdit?: (project: ProjectSummary) => void;
  onDelete?: (id: string) => void;
  onArchive?: (id: string) => void;
  onUnarchive?: (id: string) => void;
  onBulkDelete?: (ids: string[]) => void;
  isLoading?: boolean;
}

export function ProjectsTable({
  projects,
  onEdit,
  onDelete,
  onArchive,
  onUnarchive,
  onBulkDelete,
  isLoading = false,
}: ProjectsTableProps) {
  const navigate = useNavigate();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(projects.map((p) => p.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    const next = new Set(selectedIds);
    if (checked) next.add(id);
    else next.delete(id);
    setSelectedIds(next);
  };

  const handleBulkDelete = () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    onBulkDelete?.(ids);
    setSelectedIds(new Set());
  };

  const getStatusBadge = (status: TransmissionStatus) => {
    const map: Record<
      TransmissionStatus,
      { variant: "default" | "secondary" | "outline"; label: string; icon?: React.ReactNode }
    > = {
      inactive: { variant: "secondary", label: "Inactive" },
      active: {
        variant: "default",
        label: "Active",
        icon: <Radio className="h-3 w-3 mr-1" />,
      },
      paused: {
        variant: "outline",
        label: "Paused",
        icon: <Pause className="h-3 w-3 mr-1" />,
      },
    };
    const cfg = map[status];
    return (
      <Badge variant={cfg.variant} className="gap-0">
        {cfg.icon}
        {cfg.label}
      </Badge>
    );
  };

  const allSelected = projects.length > 0 && selectedIds.size === projects.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < projects.length;

  return (
    <div className="space-y-4">
      {selectedIds.size > 0 && (
        <Alert>
          <AlertDescription className="flex items-center justify-between">
            <span className="font-medium">
              {selectedIds.size} project{selectedIds.size > 1 ? "s" : ""} selected
            </span>
            <Button size="sm" variant="destructive" onClick={handleBulkDelete}>
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={allSelected}
                  onCheckedChange={handleSelectAll}
                  aria-label="Select all"
                  className={someSelected ? "data-[state=checked]:bg-primary/50" : ""}
                />
              </TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Transmission</TableHead>
              <TableHead>Devices</TableHead>
              <TableHead>Tags</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  Loading projects...
                </TableCell>
              </TableRow>
            ) : projects.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No projects found
                </TableCell>
              </TableRow>
            ) : (
              projects.map((project) => (
                <TableRow key={project.id} className={project.is_archived ? "opacity-60" : ""}>
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(project.id)}
                      onCheckedChange={(checked) =>
                        handleSelectOne(project.id, checked as boolean)
                      }
                      aria-label={`Select ${project.name}`}
                    />
                  </TableCell>
                  <TableCell className="font-medium">
                    <div
                      className="flex flex-col cursor-pointer hover:text-primary transition-colors"
                      onClick={() => navigate(`/projects/${project.id}`)}
                    >
                      <div className="flex items-center gap-2">
                        <span>{project.name}</span>
                        {project.is_archived && (
                          <Badge variant="outline" className="text-xs">
                            <Archive className="h-3 w-3 mr-1" />
                            Archived
                          </Badge>
                        )}
                      </div>
                      {project.description && (
                        <span className="text-xs text-muted-foreground truncate max-w-[250px]">
                          {project.description}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(project.transmission_status)}</TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="gap-1">
                      <Cpu className="h-3 w-3" />
                      {project.device_count}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap max-w-[150px]">
                      {(project.tags || []).slice(0, 2).map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                      {(project.tags || []).length > 2 && (
                        <Badge variant="outline" className="text-xs">
                          +{project.tags.length - 2}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(project.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                          <span className="sr-only">Open menu</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => navigate(`/projects/${project.id}`)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          View / Edit
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        {project.is_archived ? (
                          <DropdownMenuItem onClick={() => onUnarchive?.(project.id)}>
                            <ArchiveRestore className="h-4 w-4 mr-2" />
                            Unarchive
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem onClick={() => onArchive?.(project.id)}>
                            <Archive className="h-4 w-4 mr-2" />
                            Archive
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => onDelete?.(project.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
