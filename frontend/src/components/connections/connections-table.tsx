import { useState } from "react";
import { MoreHorizontal, Trash2, Power, PowerOff, TestTube, CheckCircle2 } from "lucide-react";
import { Connection, ConnectionStatus } from "@/types/connection";
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
import { ConnectionTestDialog } from "./connection-test-dialog";
import { useUpdateConnection } from "@/hooks/useConnections";

interface ConnectionsTableProps {
  connections: Connection[];
  onDelete?: (id: string) => void;
  onBulkDelete?: (ids: string[]) => void;
  onBulkActivate?: (ids: string[]) => void;
  onBulkDeactivate?: (ids: string[]) => void;
  onBulkTest?: (ids: string[]) => void;
  onEdit?: (connection: Connection) => void;
  isLoading?: boolean;
}

export function ConnectionsTable({
  connections,
  onDelete,
  onBulkDelete,
  onBulkActivate,
  onBulkDeactivate,
  onBulkTest,
  onEdit,
  isLoading = false,
}: ConnectionsTableProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [testingConnection, setTestingConnection] = useState<{ id: string; name: string } | null>(null);
  const updateMutation = useUpdateConnection();

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(connections.map((c) => c.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    const newSelected = new Set(selectedIds);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedIds(newSelected);
  };

  const handleToggleConnection = (connection: Connection) => {
    updateMutation.mutate({
      id: connection.id,
      payload: { is_active: !connection.is_active }
    });
  };

  const handleBulkAction = (action: "delete" | "activate" | "deactivate" | "test") => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;

    switch (action) {
      case "delete":
        onBulkDelete?.(ids);
        break;
      case "activate":
        onBulkActivate?.(ids);
        break;
      case "deactivate":
        onBulkDeactivate?.(ids);
        break;
      case "test":
        onBulkTest?.(ids);
        break;
    }

    setSelectedIds(new Set());
  };

  const getStatusBadge = (status: ConnectionStatus) => {
    const variants: Record<ConnectionStatus, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
      untested: { variant: "secondary", label: "Untested" },
      success: { variant: "default", label: "Success" },
      failed: { variant: "destructive", label: "Failed" },
      testing: { variant: "outline", label: "Testing" },
    };

    const config = variants[status];
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const allSelected = connections.length > 0 && selectedIds.size === connections.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < connections.length;

  return (
    <div className="space-y-4">
      {selectedIds.size > 0 && (
        <Alert>
          <AlertDescription className="flex items-center justify-between">
            <span className="font-medium">
              {selectedIds.size} connection{selectedIds.size > 1 ? "s" : ""} selected
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleBulkAction("activate")}
              >
                <Power className="h-4 w-4 mr-2" />
                Activate
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleBulkAction("deactivate")}
              >
                <PowerOff className="h-4 w-4 mr-2" />
                Deactivate
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleBulkAction("test")}
              >
                <TestTube className="h-4 w-4 mr-2" />
                Test
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => handleBulkAction("delete")}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            </div>
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
              <TableHead>Protocol</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Test Status</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  Loading connections...
                </TableCell>
              </TableRow>
            ) : connections.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No connections found
                </TableCell>
              </TableRow>
            ) : (
              connections.map((connection) => (
                <TableRow key={connection.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.has(connection.id)}
                      onCheckedChange={(checked) =>
                        handleSelectOne(connection.id, checked as boolean)
                      }
                      aria-label={`Select ${connection.name}`}
                    />
                  </TableCell>
                  <TableCell className="font-medium">{connection.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{connection.protocol}</Badge>
                  </TableCell>
                  <TableCell className="max-w-xs truncate">
                    {connection.description || "-"}
                  </TableCell>
                  <TableCell>
                    {connection.is_active ? (
                      <Badge variant="default" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Active
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell>{getStatusBadge(connection.test_status)}</TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                          <span className="sr-only">Open menu</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => onEdit?.(connection)}>
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setTestingConnection({ id: connection.id, name: connection.name })}>
                          <TestTube className="h-4 w-4 mr-2" />
                          Test Connection
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleToggleConnection(connection)}>
                          <Power className="h-4 w-4 mr-2" />
                          {connection.is_active ? 'Disable' : 'Enable'}
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => onDelete?.(connection.id)}
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

      {testingConnection && (
        <ConnectionTestDialog
          connectionId={testingConnection.id}
          connectionName={testingConnection.name}
          open={!!testingConnection}
          onOpenChange={(open) => !open && setTestingConnection(null)}
        />
      )}
    </div>
  );
}
