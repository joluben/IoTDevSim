import * as React from 'react';
import { Upload, AlertTriangle, FileJson, CheckCircle } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useImportConnections } from '@/hooks/useConnections';
import type { ConnectionImportStrategy } from '@/types/connection';

const importSchema = z.object({
  content: z.string().min(1, 'El contenido JSON es requerido'),
  strategy: z.enum(['skip', 'overwrite', 'rename'] as const),
});

type ImportFormValues = z.infer<typeof importSchema>;

export function ConnectionImportDialog() {
  const [open, setOpen] = React.useState(false);
  const [result, setResult] = React.useState<{
    success: boolean;
    message: string;
    details?: { success: number; failed: number };
  } | null>(null);

  const importMutation = useImportConnections();

  const form = useForm<ImportFormValues>({
    resolver: zodResolver(importSchema),
    defaultValues: {
      content: '',
      strategy: 'skip',
    },
  });

  const onSubmit = async (values: ImportFormValues) => {
    setResult(null);
    try {
      const response = await importMutation.mutateAsync({
        content: values.content,
        strategy: values.strategy as ConnectionImportStrategy,
      });

      setResult({
        success: response.success,
        message: response.message,
        details: {
          success: response.success_count,
          failed: response.failure_count,
        },
      });

      if (response.success && response.failure_count === 0) {
        // Close after a short delay if completely successful
        setTimeout(() => {
          setOpen(false);
          form.reset();
          setResult(null);
        }, 2000);
      }
    } catch (error) {
      setResult({
        success: false,
        message: error instanceof Error ? error.message : 'Error al importar conexiones',
      });
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      form.reset();
      setResult(null);
      importMutation.reset();
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        form.setValue('content', text);
      };
      reader.readAsText(file);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Upload className="mr-2 h-4 w-4" />
          Importar
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Importar Conexiones</DialogTitle>
          <DialogDescription>
            Carga un archivo JSON o pega el contenido para importar conexiones.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid w-full max-w-sm items-center gap-1.5">
              <FormLabel htmlFor="file-upload">Cargar archivo</FormLabel>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="w-full"
                  onClick={() => document.getElementById('file-upload')?.click()}
                >
                  <FileJson className="mr-2 h-4 w-4" />
                  Seleccionar archivo JSON
                </Button>
                <input
                  id="file-upload"
                  type="file"
                  accept=".json"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </div>
            </div>

            <FormField
              control={form.control}
              name="content"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Contenido JSON</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder='{ "connections": [...] }'
                      className="min-h-[200px] font-mono text-xs"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="strategy"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Estrategia de conflicto</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona una estrategia" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="skip">Saltar existentes</SelectItem>
                      <SelectItem value="overwrite">Sobrescribir existentes</SelectItem>
                      <SelectItem value="rename">Renombrar (crear copia)</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Define qué hacer si una conexión con el mismo nombre ya existe.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {result && (
              <Alert variant={result.success ? 'default' : 'destructive'}>
                {result.success ? (
                  <CheckCircle className="h-4 w-4" />
                ) : (
                  <AlertTriangle className="h-4 w-4" />
                )}
                <AlertTitle>{result.success ? 'Importación completada' : 'Error'}</AlertTitle>
                <AlertDescription>
                  {result.message}
                  {result.details && (
                    <div className="mt-1 text-xs">
                      Exitosos: {result.details.success}, Fallidos: {result.details.failed}
                    </div>
                  )}
                </AlertDescription>
              </Alert>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={importMutation.isPending}>
                {importMutation.isPending ? 'Importando...' : 'Importar Conexiones'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
