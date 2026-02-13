import * as React from 'react';
import { CheckCircle, XCircle, Loader2, Terminal } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import type { ConnectionTestResponse } from '@/types/connection';
import { useTestConnection } from '@/hooks/useConnections';
import { useUIStore } from '@/app/store/ui-store';

interface ConnectionTestDialogProps {
  connectionId: string | null;
  connectionName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConnectionTestDialog({
  connectionId,
  connectionName,
  open,
  onOpenChange,
}: ConnectionTestDialogProps) {
  const [result, setResult] = React.useState<ConnectionTestResponse | null>(null);
  const testMutation = useTestConnection();
  const addNotification = useUIStore((s) => s.addNotification);

  // Reset state when dialog opens/closes or connection changes
  React.useEffect(() => {
    if (open && connectionId) {
      setResult(null);
      testMutation.mutate(
        { id: connectionId },
        {
          onSuccess: (data) => {
            setResult(data);
          },
        }
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, connectionId]);

  React.useEffect(() => {
    if (!testMutation.isError) return;
    addNotification({
      type: 'error',
      title: 'No se pudo ejecutar el test',
      message:
        testMutation.error instanceof Error
          ? testMutation.error.message
          : 'Ocurrió un error inesperado.',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [testMutation.isError]);

  React.useEffect(() => {
    if (!result) return;
    addNotification({
      type: result.success ? 'success' : 'error',
      title: result.success ? 'Test OK' : 'Test fallido',
      message: result.message,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result?.success, result?.message]);

  const handleClose = () => {
    onOpenChange(false);
  };

  const handleRetry = () => {
    if (connectionId) {
      setResult(null);
      testMutation.mutate(
        { id: connectionId },
        {
          onSuccess: (data) => {
            setResult(data);
          },
        }
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Probando conexión: {connectionName}</DialogTitle>
          <DialogDescription>
            Verificando conectividad y configuración del protocolo.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {testMutation.isPending && (
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Ejecutando pruebas de conexión...</p>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-4 rounded-lg border bg-card">
                {result.success ? (
                  <CheckCircle className="h-6 w-6 text-green-500" />
                ) : (
                  <XCircle className="h-6 w-6 text-destructive" />
                )}
                <div className="flex-1">
                  <div className="font-medium">
                    {result.success ? 'Conexión Exitosa' : 'Conexión Fallida'}
                  </div>
                  <div className="text-sm text-muted-foreground">{result.message}</div>
                </div>
                <Badge variant={result.success ? 'secondary' : 'destructive'}>
                  {result.duration_ms} ms
                </Badge>
              </div>

              {result.details && Object.keys(result.details).length > 0 && (
                <div className="rounded-lg border bg-muted/50">
                  <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/50">
                    <Terminal className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Detalles Técnicos</span>
                  </div>
                  <ScrollArea className="h-[200px] w-full rounded-b-lg">
                    <div className="p-4 font-mono text-xs">
                      <pre>{JSON.stringify(result.details, null, 2)}</pre>
                    </div>
                  </ScrollArea>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cerrar
          </Button>
          {!testMutation.isPending && (
            <Button onClick={handleRetry} disabled={testMutation.isPending}>
              {testMutation.isPending ? 'Probando...' : 'Reintentar'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
