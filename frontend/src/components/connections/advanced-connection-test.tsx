import * as React from 'react';
import { CheckCircle, XCircle, Loader2, AlertTriangle, Terminal, Clock, Zap, Activity } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { ConnectionTestResponse, Connection } from '@/types/connection';
import { useTestConnection } from '@/hooks/useConnections';

const testOptionsSchema = z.object({
  timeout: z.coerce.number().min(1).max(300),
  retries: z.coerce.number().min(0).max(5),
  verify_ssl: z.boolean(),
  detailed_logs: z.boolean(),
});

type TestOptions = z.infer<typeof testOptionsSchema>;

interface AdvancedConnectionTestProps {
  connection: Connection;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface TestLog {
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

export function AdvancedConnectionTest({
  connection,
  open,
  onOpenChange,
}: AdvancedConnectionTestProps) {
  const [result, setResult] = React.useState<ConnectionTestResponse | null>(null);
  const [logs, setLogs] = React.useState<TestLog[]>([]);
  const [progress, setProgress] = React.useState(0);
  const testMutation = useTestConnection();

  const form = useForm({
    resolver: zodResolver(testOptionsSchema),
    defaultValues: {
      timeout: 30,
      retries: 3,
      verify_ssl: true,
      detailed_logs: false,
    },
  });

  const addLog = (level: TestLog['level'], message: string) => {
    setLogs((prev) => [
      ...prev,
      {
        timestamp: new Date().toISOString(),
        level,
        message,
      },
    ]);
  };

  const simulateProgress = () => {
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return prev;
        }
        return prev + 10;
      });
    }, 200);
    return interval;
  };

  const handleTest = (data: any) => {
    setResult(null);
    setLogs([]);
    
    addLog('info', `Iniciando prueba de conexión: ${connection.name}`);
    addLog('info', `Protocolo: ${connection.protocol.toUpperCase()}`);
    addLog('info', `Timeout configurado: ${data.timeout}s`);
    
    const progressInterval = simulateProgress();

    testMutation.mutate(
      { id: connection.id },
      {
        onSuccess: (testResult) => {
          clearInterval(progressInterval);
          setProgress(100);
          setResult(testResult);
          
          if (testResult.success) {
            addLog('success', `✓ Conexión exitosa en ${testResult.duration_ms}ms`);
            addLog('info', testResult.message);
          } else {
            addLog('error', `✗ Conexión fallida: ${testResult.message}`);
          }

          if (data.detailed_logs && testResult.details) {
            Object.entries(testResult.details).forEach(([key, value]) => {
              addLog('info', `${key}: ${JSON.stringify(value)}`);
            });
          }
        },
        onError: (error) => {
          clearInterval(progressInterval);
          setProgress(0);
          addLog('error', `Error: ${error instanceof Error ? error.message : 'Error desconocido'}`);
        },
      }
    );
  };

  React.useEffect(() => {
    if (open) {
      setResult(null);
      setLogs([]);
      setProgress(0);
    }
  }, [open]);

  const getProtocolSpecificOptions = () => {
    switch (connection.protocol) {
      case 'mqtt':
        return (
          <div className="space-y-4">
            <FormField
              control={form.control}
              name="timeout"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Timeout de Conexión (segundos)</FormLabel>
                  <FormControl>
                    <Input 
                      type="number" 
                      value={field.value as number}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      onBlur={field.onBlur}
                      name={field.name}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="retries"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Número de Reintentos</FormLabel>
                  <FormControl>
                    <Input 
                      type="number" 
                      value={field.value as number}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                      onBlur={field.onBlur}
                      name={field.name}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        );
      case 'http':
      case 'https':
        return (
          <div className="space-y-4">
            <FormField
              control={form.control}
              name="timeout"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Timeout de Petición (segundos)</FormLabel>
                  <FormControl>
                    <Input type="number" value={field.value as string} onChange={(e) => field.onChange(Number(e.target.value))} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="verify_ssl"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Verificar Certificado SSL</FormLabel>
                    <p className="text-sm text-muted-foreground">
                      Valida el certificado SSL del servidor
                    </p>
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />
          </div>
        );
      case 'kafka':
        return (
          <div className="space-y-4">
            <FormField
              control={form.control}
              name="timeout"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Timeout de Conexión (segundos)</FormLabel>
                  <FormControl>
                    <Input type="number" value={field.value as string} onChange={(e) => field.onChange(Number(e.target.value))} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>Prueba Avanzada de Conexión</DialogTitle>
          <DialogDescription>
            {connection.name} - {connection.protocol.toUpperCase()}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="test" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="test">Prueba</TabsTrigger>
            <TabsTrigger value="logs">Logs</TabsTrigger>
            <TabsTrigger value="metrics">Métricas</TabsTrigger>
          </TabsList>

          <TabsContent value="test" className="space-y-4">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(handleTest)} className="space-y-4">
                {getProtocolSpecificOptions()}

                <FormField
                  control={form.control}
                  name="detailed_logs"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base">Logs Detallados</FormLabel>
                        <p className="text-sm text-muted-foreground">
                          Incluye información técnica adicional
                        </p>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {testMutation.isPending && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Progreso de la prueba</span>
                      <span className="font-medium">{progress}%</span>
                    </div>
                    <Progress value={progress} className="h-2" />
                  </div>
                )}

                {result && (
                  <Alert variant={result.success ? 'default' : 'destructive'}>
                    {result.success ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : (
                      <XCircle className="h-4 w-4" />
                    )}
                    <AlertTitle>
                      {result.success ? 'Conexión Exitosa' : 'Conexión Fallida'}
                    </AlertTitle>
                    <AlertDescription>
                      {result.message}
                      <div className="mt-2 flex gap-4 text-xs">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {result.duration_ms}ms
                        </span>
                        {result.details?.latency && typeof result.details.latency === 'number' ? (
                          <span className="flex items-center gap-1">
                            <Zap className="h-3 w-3" />
                            Latency: {result.details.latency}ms
                          </span>
                        ) : null}
                      </div>
                    </AlertDescription>
                  </Alert>
                )}

                <div className="flex gap-2">
                  <Button
                    type="submit"
                    disabled={testMutation.isPending}
                    className="flex-1"
                  >
                    {testMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Probando...
                      </>
                    ) : (
                      <>
                        <Activity className="mr-2 h-4 w-4" />
                        Ejecutar Prueba
                      </>
                    )}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                    Cerrar
                  </Button>
                </div>
              </form>
            </Form>
          </TabsContent>

          <TabsContent value="logs" className="space-y-4">
            <ScrollArea className="h-[400px] w-full rounded-lg border">
              <div className="p-4 space-y-2 font-mono text-xs">
                {logs.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    No hay logs disponibles. Ejecuta una prueba para ver los logs.
                  </p>
                ) : (
                  logs.map((log, index) => (
                    <div
                      key={index}
                      className={`flex gap-2 p-2 rounded ${
                        log.level === 'error'
                          ? 'bg-destructive/10 text-destructive'
                          : log.level === 'success'
                          ? 'bg-green-500/10 text-green-700 dark:text-green-400'
                          : log.level === 'warning'
                          ? 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400'
                          : 'bg-muted/50'
                      }`}
                    >
                      <span className="text-muted-foreground">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      <span className="flex-1">{log.message}</span>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="metrics" className="space-y-4">
            {result ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Tiempo de Respuesta</div>
                    <div className="text-2xl font-bold">{result.duration_ms}ms</div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Estado</div>
                    <div className="text-2xl font-bold">
                      {result.success ? (
                        <Badge variant="default">Exitoso</Badge>
                      ) : (
                        <Badge variant="destructive">Fallido</Badge>
                      )}
                    </div>
                  </div>
                </div>

                {result.details && (
                  <div className="rounded-lg border">
                    <div className="px-4 py-2 border-b bg-muted/50">
                      <span className="text-sm font-medium">Detalles Técnicos</span>
                    </div>
                    <div className="p-4 overflow-x-auto">
                      <pre className="text-xs font-mono whitespace-pre-wrap break-all">
                        {JSON.stringify(result.details, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                No hay métricas disponibles. Ejecuta una prueba para ver las métricas.
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
