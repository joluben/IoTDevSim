import * as React from 'react';
import { useNavigate } from 'react-router-dom';

import { LayoutGrid, Table as TableIcon, Plus, ChevronLeft, ChevronRight } from 'lucide-react';

import { PageContainer } from '@/components/layout/page-container';
import { ProjectsTable } from '@/components/projects/projects-table';
import { ProjectsFilters } from '@/components/projects/projects-filters';
import { ProjectsStats } from '@/components/projects/projects-stats';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  useProjects,
  useDeleteProject,
  useArchiveProject,
  useUnarchiveProject,
} from '@/hooks/useProjects';
import type { ProjectFilters, ProjectSummary, TransmissionStatus } from '@/types/project';
import { useUIStore } from '@/app/store/ui-store';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const DEFAULT_FILTERS: ProjectFilters = {
  search: undefined,
  transmission_status: undefined,
  is_active: undefined,
  is_archived: false,
  skip: 0,
  limit: 20,
  sort_by: 'created_at',
  sort_order: 'desc',
};

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = React.useState<ProjectFilters>(DEFAULT_FILTERS);
  const [viewMode, setViewMode] = React.useState<'grid' | 'table'>('table');
  const addNotification = useUIStore((s) => s.addNotification);
  const listQuery = useProjects(filters);
  const deleteMutation = useDeleteProject();
  const archiveMutation = useArchiveProject();
  const unarchiveMutation = useUnarchiveProject();

  const projects = listQuery.data?.items ?? [];

  React.useEffect(() => {
    if (!listQuery.isError) return;
    addNotification({
      type: 'error',
      title: 'Failed to load projects',
      message:
        listQuery.error instanceof Error
          ? listQuery.error.message
          : 'An unexpected error occurred.',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listQuery.isError]);

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () =>
        addNotification({ type: 'success', title: 'Project deleted', message: '' }),
    });
  };

  const handleBulkDelete = (ids: string[]) => {
    ids.forEach((id) => deleteMutation.mutate(id));
  };

  const handleArchive = (id: string) => {
    archiveMutation.mutate(id, {
      onSuccess: () =>
        addNotification({ type: 'success', title: 'Project archived', message: '' }),
    });
  };

  const handleUnarchive = (id: string) => {
    unarchiveMutation.mutate(id, {
      onSuccess: () =>
        addNotification({ type: 'success', title: 'Project unarchived', message: '' }),
    });
  };

  const getStatusColor = (status: TransmissionStatus) => {
    const map: Record<TransmissionStatus, string> = {
      active: 'bg-green-500/10 text-green-600 border-green-500/20',
      paused: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
      inactive: 'bg-muted text-muted-foreground',
    };
    return map[status];
  };

  return (
    <PageContainer
      title="Projects"
      description="Manage IoT device groups and control transmissions"
      header={
        <div className="flex items-center justify-between gap-4">
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'grid' | 'table')}>
            <TabsList>
              <TabsTrigger value="table">
                <TableIcon className="h-4 w-4 mr-2" />
                Table
              </TabsTrigger>
              <TabsTrigger value="grid">
                <LayoutGrid className="h-4 w-4 mr-2" />
                Cards
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <Button onClick={() => navigate('/projects/new')}>
            <Plus className="h-4 w-4 mr-2" />
            New Project
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        <ProjectsStats projects={projects} />

        <ProjectsFilters value={filters} onChange={setFilters} />

        {projects.length === 0 && !listQuery.isLoading ? (
          <div className="rounded-lg border bg-card p-10 text-center">
            <div className="mx-auto max-w-md space-y-3">
              <div className="text-lg font-semibold">No projects yet</div>
              <div className="text-sm text-muted-foreground">
                Create your first project to group devices and control transmissions.
              </div>
              <div className="flex justify-center">
                <Button onClick={() => navigate('/projects/new')}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Project
                </Button>
              </div>
            </div>
          </div>
        ) : viewMode === 'table' ? (
          <ProjectsTable
            projects={projects}
            onDelete={handleDelete}
            onBulkDelete={handleBulkDelete}
            onArchive={handleArchive}
            onUnarchive={handleUnarchive}
            isLoading={listQuery.isLoading}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <div
                key={project.id}
                className={`rounded-xl border bg-card p-5 space-y-3 cursor-pointer hover:border-primary/50 transition-colors ${
                  project.is_archived ? 'opacity-60' : ''
                }`}
                onClick={() => navigate(`/projects/${project.id}`)}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold">{project.name}</h3>
                    <span className="text-xs text-muted-foreground">
                      {project.device_count} device{project.device_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <Badge
                    variant="outline"
                    className={`capitalize text-xs ${getStatusColor(project.transmission_status)}`}
                  >
                    {project.transmission_status}
                  </Badge>
                </div>
                {project.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {project.description}
                  </p>
                )}
                {project.tags.length > 0 && (
                  <div className="flex gap-1 flex-wrap">
                    {project.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                    {project.tags.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{project.tags.length - 3}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            ))}

            <div
              className="flex min-h-[140px] items-center justify-center rounded-xl border border-dashed bg-card p-6 cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => navigate('/projects/new')}
            >
              <div className="space-y-3 text-center">
                <div className="text-sm text-muted-foreground">New project</div>
                <Button variant="outline" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Create
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Pagination */}
        {(listQuery.data?.total ?? 0) > 0 && (
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>
                {(filters.skip ?? 0) + 1}–
                {Math.min(
                  (filters.skip ?? 0) + (filters.limit ?? 20),
                  listQuery.data?.total ?? 0
                )}{' '}
                of {listQuery.data?.total ?? 0}
              </span>
              <Select
                value={String(filters.limit ?? 20)}
                onValueChange={(v) => setFilters({ ...filters, limit: Number(v), skip: 0 })}
              >
                <SelectTrigger className="h-8 w-[70px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
              <span>per page</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                disabled={!listQuery.data?.has_prev}
                onClick={() =>
                  setFilters({
                    ...filters,
                    skip: Math.max(0, (filters.skip ?? 0) - (filters.limit ?? 20)),
                  })
                }
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                disabled={!listQuery.data?.has_next}
                onClick={() =>
                  setFilters({
                    ...filters,
                    skip: (filters.skip ?? 0) + (filters.limit ?? 20),
                  })
                }
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </PageContainer>
  );
}
