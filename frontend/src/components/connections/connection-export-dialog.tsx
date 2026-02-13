import * as React from 'react';
import { Download, CheckCircle, AlertTriangle, Copy } from 'lucide-react';
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
import { useExportConnections } from '@/hooks/useConnections';
import type { ExportFormat, ExportOption } from '@/types/connection';

const exportSchema = z.object({
  format: z.enum(['json'] as const),
  export_option: z.enum(['encrypted', 'masked'] as const),
});

type ExportFormValues = z.infer<typeof exportSchema>;

interface ConnectionExportDialogProps {
  selectedIds?: string[];
}

export function ConnectionExportDialog({ selectedIds = [] }: ConnectionExportDialogProps) {
  const [open, setOpen] = React.useState(false);
  const [exportData, setExportData] = React.useState<string | null>(null);
  const exportMutation = useExportConnections();

  const form = useForm<ExportFormValues>({
    resolver: zodResolver(exportSchema),
    defaultValues: {
      format: 'json',
      export_option: 'encrypted',
    },
  });

  const onSubmit = async (values: ExportFormValues) => {
    setExportData(null);
    try {
      const response = await exportMutation.mutateAsync({
        connection_ids: selectedIds.length > 0 ? selectedIds : undefined,
        format: values.format as ExportFormat,
        export_option: values.export_option as ExportOption,
      });

      // Format JSON for display
      setExportData(JSON.stringify(response, null, 2));
    } catch (error) {
      console.error('Export error:', error);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      form.reset();
      setExportData(null);
      exportMutation.reset();
    }
  };

  const handleCopy = () => {
    if (exportData) {
      navigator.clipboard.writeText(exportData);
    }
  };

  const handleDownload = () => {
    if (exportData) {
      const blob = new Blob([exportData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `connections-export-${new Date().toISOString()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Exportar
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Exportar Conexiones</DialogTitle>
          <DialogDescription>
            Descarga tus conexiones en formato JSON. Puedes elegir incluir credenciales cifradas para backup.
          </DialogDescription>
        </DialogHeader>

        {!exportData ? (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              {selectedIds.length > 0 && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertTitle>Selección activa</AlertTitle>
                  <AlertDescription>
                    Se exportarán {selectedIds.length} conexiones seleccionadas.
                  </AlertDescription>
                </Alert>
              )}

              <FormField
                control={form.control}
                name="export_option"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Manejo de datos sensibles</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecciona una opción" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="encrypted">Cifrado (Backup/Restauración)</SelectItem>
                        <SelectItem value="masked">Enmascarado (Seguro para compartir)</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      'Cifrado' mantiene las contraseñas cifradas (solo restaurable en el mismo sistema).
                      'Enmascarado' oculta las contraseñas con asteriscos.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {exportMutation.isError && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>
                    {exportMutation.error instanceof Error
                      ? exportMutation.error.message
                      : 'Error al exportar conexiones'}
                  </AlertDescription>
                </Alert>
              )}

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={exportMutation.isPending}>
                  {exportMutation.isPending ? 'Generando...' : 'Generar Exportación'}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        ) : (
          <div className="space-y-4">
            <div className="rounded-md border p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Vista previa</span>
                <Button variant="ghost" size="sm" onClick={handleCopy}>
                  <Copy className="h-4 w-4 mr-2" />
                  Copiar
                </Button>
              </div>
              <Textarea
                readOnly
                value={exportData}
                className="font-mono text-xs h-[300px]"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setExportData(null)}>
                Volver
              </Button>
              <Button onClick={handleDownload}>
                <Download className="mr-2 h-4 w-4" />
                Descargar Archivo
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
