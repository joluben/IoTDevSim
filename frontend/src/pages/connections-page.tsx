import * as React from 'react';

import { Plus, LayoutGrid, Table as TableIcon } from 'lucide-react';

import { PageContainer } from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import { ConnectionCard } from '@/components/connections/connection-card';
import { ConnectionsFilters } from '@/components/connections/connections-filters';
import { ConnectionsStats } from '@/components/connections/connections-stats';
import { CreateConnectionDialog } from '@/components/connections/create-connection-dialog';
import { CreateConnectionWizardDialog } from '@/components/connections/create-connection-wizard-dialog';
import { ConnectionsTable } from '@/components/connections/connections-table';
import { EditConnectionDialog } from '@/components/connections/edit-connection-dialog';
import { ConnectionImportDialog } from '@/components/connections/connection-import-dialog';
import { ConnectionExportDialog } from '@/components/connections/connection-export-dialog';
import {
  useConnections,
  useDeleteConnection,
  useTestConnection,
  useBulkOperations,
} from '@/hooks/useConnections';
import type { ConnectionFilters, Connection } from '@/types/connection';
import { useUIStore } from '@/app/store/ui-store';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const DEFAULT_FILTERS: ConnectionFilters = {
  search: '',
  protocol: undefined,
  test_status: undefined,
  is_active: undefined,
  skip: 0,
  limit: 50,
  sort_by: 'created_at',
  sort_order: 'desc',
};

export default function ConnectionsPage() {
  const [filters, setFilters] = React.useState<ConnectionFilters>(DEFAULT_FILTERS);
  const [viewMode, setViewMode] = React.useState<'grid' | 'table'>('table');
  const [editingConnection, setEditingConnection] = React.useState<Connection | null>(null);
  const addNotification = useUIStore((s) => s.addNotification);
  const listQuery = useConnections(filters);
  const testMutation = useTestConnection();
  const deleteMutation = useDeleteConnection();
  const bulkMutation = useBulkOperations();

  const connections = listQuery.data?.items ?? [];

  React.useEffect(() => {
    if (!listQuery.isError) return;

    addNotification({
      type: 'error',
      title: 'No se pudieron cargar las conexiones',
      message:
        listQuery.error instanceof Error
          ? listQuery.error.message
          : 'Ocurrió un error inesperado.',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listQuery.isError]);

  const handleTest = (id: string) => {
    testMutation.mutate({ id });
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate({ id });
  };

  const handleBulkDelete = (ids: string[]) => {
    bulkMutation.mutate({ operation: 'delete', connection_ids: ids });
  };

  const handleBulkActivate = (ids: string[]) => {
    bulkMutation.mutate({ operation: 'activate', connection_ids: ids });
  };

  const handleBulkDeactivate = (ids: string[]) => {
    bulkMutation.mutate({ operation: 'deactivate', connection_ids: ids });
  };

  const handleBulkTest = (ids: string[]) => {
    bulkMutation.mutate({ operation: 'test', connection_ids: ids });
  };

  const handleEdit = (connection: Connection) => {
    setEditingConnection(connection);
  };

  return (
    <PageContainer
      title="Conexiones"
      description="Gestiona tus conexiones IoT"
      header={
        <div className="flex items-center justify-between gap-4">
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'grid' | 'table')}>
            <TabsList>
              <TabsTrigger value="table">
                <TableIcon className="h-4 w-4 mr-2" />
                Tabla
              </TabsTrigger>
              <TabsTrigger value="grid">
                <LayoutGrid className="h-4 w-4 mr-2" />
                Tarjetas
              </TabsTrigger>
            </TabsList>
          </Tabs>
          
          <div className="flex items-center gap-2">
            <ConnectionImportDialog />
            <ConnectionExportDialog selectedIds={[]} />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Nueva conexión
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <CreateConnectionDialog triggerLabel="Formulario rápido" triggerVariant="ghost" />
                <CreateConnectionWizardDialog triggerLabel="Asistente guiado" triggerVariant="ghost" />
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        <ConnectionsStats connections={connections} />

        <ConnectionsFilters value={filters} onChange={setFilters} />

        {connections.length === 0 && !listQuery.isLoading ? (
          <div className="rounded-lg border bg-card p-10 text-center">
            <div className="mx-auto max-w-md space-y-3">
              <div className="text-lg font-semibold">No hay conexiones</div>
              <div className="text-sm text-muted-foreground">
                Crea tu primera conexión para empezar a enviar datos.
              </div>
              <div className="flex justify-center">
                <CreateConnectionDialog triggerLabel="Crear conexión" />
              </div>
            </div>
          </div>
        ) : viewMode === 'table' ? (
          <ConnectionsTable
            connections={connections}
            onDelete={handleDelete}
            onBulkDelete={handleBulkDelete}
            onBulkActivate={handleBulkActivate}
            onBulkDeactivate={handleBulkDeactivate}
            onBulkTest={handleBulkTest}
            onEdit={handleEdit}
            isLoading={listQuery.isLoading}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {connections.map((connection) => (
              <ConnectionCard
                key={connection.id}
                connection={connection}
                onTest={handleTest}
                onDelete={handleDelete}
                isTesting={testMutation.isPending}
                isDeleting={deleteMutation.isPending}
              />
            ))}

            <div className="flex min-h-[180px] items-center justify-center rounded-xl border border-dashed bg-card p-6">
              <div className="space-y-3 text-center">
                <div className="text-sm text-muted-foreground">Nueva conexión</div>
                <CreateConnectionDialog
                  triggerLabel="Crear"
                  triggerVariant="outline"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <EditConnectionDialog
        connection={editingConnection}
        open={!!editingConnection}
        onOpenChange={(open) => {
          if (!open) setEditingConnection(null);
        }}
      />
    </PageContainer>
  );
}
