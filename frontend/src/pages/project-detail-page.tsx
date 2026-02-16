import * as React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Pencil,
  Archive,
  ArchiveRestore,
  Trash2,
  Settings,
  Cpu,
  BarChart3,
  CheckCircle,
  XCircle,
  Percent,
} from 'lucide-react';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';

import { PageContainer } from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TransmissionControlPanel } from '@/components/projects/transmission-control-panel';
import { ProjectDevicesPanel } from '@/components/projects/project-devices-panel';
import { RealtimeTransmissionLog } from '@/components/projects/realtime-transmission-log';
import {
  useProject,
  useProjectDevices,
  useProjectStats,
  useProjectHistory,
  useStartTransmissions,
  usePauseTransmissions,
  useResumeTransmissions,
  useStopTransmissions,
  useDeleteProject,
  useArchiveProject,
  useUnarchiveProject,
  useClearProjectLogs,
} from '@/hooks/useProjects';
import type {
  TransmissionStatus,
  TransmissionHistoryFilters,
  ProjectTransmissionResult,
} from '@/types/project';
import { useUIStore } from '@/app/store/ui-store';

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const addNotification = useUIStore((s) => s.addNotification);

  const projectQuery = useProject(id!);
  const devicesQuery = useProjectDevices(id!);
  const statsQuery = useProjectStats(id!);

  const [historyFilters, setHistoryFilters] = React.useState<TransmissionHistoryFilters>({
    skip: 0,
    limit: 100,
  });
  const historyQuery = useProjectHistory(id!, historyFilters);

  const [lastResult, setLastResult] = React.useState<ProjectTransmissionResult | null>(null);
  const [deleteOpen, setDeleteOpen] = React.useState(false);

  const startMutation = useStartTransmissions();
  const pauseMutation = usePauseTransmissions();
  const resumeMutation = useResumeTransmissions();
  const stopMutation = useStopTransmissions();
  const deleteMutation = useDeleteProject();
  const archiveMutation = useArchiveProject();
  const unarchiveMutation = useUnarchiveProject();
  const clearLogsMutation = useClearProjectLogs();

  const project = projectQuery.data;
  const devices = devicesQuery.data?.devices ?? [];

  const handleTransmissionResult = (result: ProjectTransmissionResult) => {
    setLastResult(result);
    projectQuery.refetch();
    devicesQuery.refetch();
    statsQuery.refetch();
    historyQuery.refetch();
  };

  const handleStart = () => {
    startMutation.mutate(
      { projectId: id! },
      {
        onSuccess: (result) => {
          addNotification({ type: 'success', title: 'Transmissions started', message: '' });
          handleTransmissionResult(result);
        },
        onError: () =>
          addNotification({ type: 'error', title: 'Failed to start transmissions', message: '' }),
      }
    );
  };

  const handlePause = () => {
    pauseMutation.mutate(id!, {
      onSuccess: (result) => {
        addNotification({ type: 'success', title: 'Transmissions paused', message: '' });
        handleTransmissionResult(result);
      },
    });
  };

  const handleResume = () => {
    resumeMutation.mutate(id!, {
      onSuccess: (result) => {
        addNotification({ type: 'success', title: 'Transmissions resumed', message: '' });
        handleTransmissionResult(result);
      },
    });
  };

  const handleStop = () => {
    stopMutation.mutate(id!, {
      onSuccess: (result) => {
        addNotification({ type: 'success', title: 'Transmissions stopped', message: '' });
        handleTransmissionResult(result);
      },
    });
  };

  const handleDelete = () => {
    setDeleteOpen(true);
  };

  const confirmDelete = () => {
    deleteMutation.mutate(id!, {
      onSuccess: () => {
        addNotification({ type: 'success', title: 'Project deleted', message: '' });
        setDeleteOpen(false);
        navigate('/projects');
      },
      onError: (error) => {
        addNotification({
          type: 'error',
          title: 'Failed to delete project',
          message: error instanceof Error ? error.message : 'Unexpected error',
        });
        setDeleteOpen(false);
      },
    });
  };

  const handleArchive = () => {
    archiveMutation.mutate(id!, {
      onSuccess: () => {
        addNotification({ type: 'success', title: 'Project archived', message: '' });
        projectQuery.refetch();
      },
    });
  };

  const handleUnarchive = () => {
    unarchiveMutation.mutate(id!, {
      onSuccess: () => {
        addNotification({ type: 'success', title: 'Project unarchived', message: '' });
        projectQuery.refetch();
      },
    });
  };

  const isTransmissionLoading =
    startMutation.isPending ||
    pauseMutation.isPending ||
    resumeMutation.isPending ||
    stopMutation.isPending;

  if (projectQuery.isLoading) {
    return (
      <PageContainer title="Loading..." description="">
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </PageContainer>
    );
  }

  if (!project) {
    return (
      <PageContainer title="Not Found" description="">
        <div className="text-center py-20">
          <p className="text-muted-foreground">Project not found.</p>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/projects')}>
            Back to Projects
          </Button>
        </div>
      </PageContainer>
    );
  }

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
      title={project.name}
      description={project.description || 'No description'}
      header={
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="ghost" size="sm" onClick={() => navigate('/projects')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>

          <Badge
            variant="outline"
            className={`capitalize ${getStatusColor(project.transmission_status as TransmissionStatus)}`}
          >
            {project.transmission_status}
          </Badge>

          {project.is_archived && (
            <Badge variant="outline" className="text-xs">
              <Archive className="h-3 w-3 mr-1" />
              Archived
            </Badge>
          )}

          <div className="flex-1" />

          <Button variant="outline" size="sm" onClick={() => navigate(`/projects/${id}/edit`)}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>

          {project.is_archived ? (
            <Button variant="outline" size="sm" onClick={handleUnarchive}>
              <ArchiveRestore className="h-4 w-4 mr-2" />
              Unarchive
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={handleArchive}>
              <Archive className="h-4 w-4 mr-2" />
              Archive
            </Button>
          )}

          <Button variant="destructive" size="sm" onClick={handleDelete}>
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Project Info Summary */}
        <div className="flex flex-wrap gap-4">
          {project.tags.length > 0 && (
            <div className="flex gap-1 flex-wrap items-center">
              <span className="text-sm text-muted-foreground mr-1">Tags:</span>
              {project.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
          <div className="text-sm text-muted-foreground">
            Auto Reset: {project.auto_reset_counter ? 'On' : 'Off'}
          </div>
          <div className="text-sm text-muted-foreground">
            Max Devices: {project.max_devices}
          </div>
        </div>

        <Tabs defaultValue="devices" className="space-y-4">
          <TabsList>
            <TabsTrigger value="devices" className="gap-2">
              <Cpu className="h-4 w-4" />
              Devices
            </TabsTrigger>
            <TabsTrigger value="transmission" className="gap-2">
              <Settings className="h-4 w-4" />
              Transmission
            </TabsTrigger>
          </TabsList>

          <TabsContent value="devices" className="space-y-4">
            <ProjectDevicesPanel
              projectId={id!}
              devices={devices}
              isLoading={devicesQuery.isLoading}
              onRefresh={() => {
                devicesQuery.refetch();
                projectQuery.refetch();
              }}
            />
          </TabsContent>

          <TabsContent value="transmission" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
              {/* Left Column - Controls (1/4) */}
              <div className="lg:col-span-1">
                <TransmissionControlPanel
                  transmissionStatus={project.transmission_status as TransmissionStatus}
                  deviceCount={project.device_count}
                  onStart={handleStart}
                  onPause={handlePause}
                  onResume={handleResume}
                  onStop={handleStop}
                  onClearLogs={() => {
                    clearLogsMutation.mutate(id!, {
                      onSuccess: (result) => {
                        addNotification({
                          type: 'success',
                          title: 'Logs cleared',
                          message: `Cleared ${result.data.deleted_count} transmission logs`,
                        });
                      },
                      onError: () => {
                        addNotification({
                          type: 'error',
                          title: 'Failed to clear logs',
                          message: '',
                        });
                      },
                    });
                  }}
                  isLoading={isTransmissionLoading || clearLogsMutation.isPending}
                  lastResult={lastResult}
                />
              </div>
              
              {/* Right Column - Stats + Logs (3/4) */}
              <div className="lg:col-span-3 space-y-4">
                {/* Statistics Cards */}
                <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
                  <StatCard 
                    label="Total Transmissions" 
                    value={statsQuery.data?.total_transmissions ?? 0} 
                    icon={BarChart3} 
                    color="text-blue-500"
                    isLoading={statsQuery.isLoading}
                  />
                  <StatCard 
                    label="Successful" 
                    value={statsQuery.data?.successful_transmissions ?? 0} 
                    icon={CheckCircle} 
                    color="text-green-500"
                    isLoading={statsQuery.isLoading}
                  />
                  <StatCard 
                    label="Failed" 
                    value={statsQuery.data?.failed_transmissions ?? 0} 
                    icon={XCircle} 
                    color="text-red-500"
                    isLoading={statsQuery.isLoading}
                  />
                  <StatCard 
                    label="Success Rate" 
                    value={`${statsQuery.data?.success_rate ?? 0}%`} 
                    icon={Percent} 
                    color="text-purple-500"
                    isLoading={statsQuery.isLoading}
                  />
                </div>
                
                {/* Real-time Log */}
                <RealtimeTransmissionLog 
                  entries={historyQuery.data?.items ?? []}
                  isLoading={historyQuery.isLoading}
                  maxEntries={100}
                />
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete project"
        description={
          <>
            Are you sure you want to delete <strong>{project.name}</strong>?
            <br />
            <span className="text-xs text-muted-foreground mt-1 block">
              All associated device assignments and transmission history will be permanently lost.
            </span>
          </>
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={confirmDelete}
      />
    </PageContainer>
  );
}

// Inline StatCard component for statistics display
interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  isLoading?: boolean;
}

function StatCard({ label, value, icon: Icon, color, isLoading }: StatCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-4 p-4">
          <div className="h-10 w-10 rounded-lg bg-muted animate-pulse" />
          <div className="space-y-1">
            <div className="h-6 w-12 bg-muted animate-pulse rounded" />
            <div className="h-3 w-20 bg-muted animate-pulse rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className={`rounded-lg bg-muted p-2.5 ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}
