import * as React from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import type { z } from 'zod';

import type { Connection, ConnectionUpdateRequest } from '@/types/connection';
import { connectionFormFields, type ConnectionFormValues } from '@/features/connections/config/connection-form.config';
import {
  connectionCreateSchema,
  type ConnectionCreateValues,
} from '@/features/connections/validation/connection.schemas';
import { DynamicForm } from '@/components/forms/dynamic-form';
import type { DynamicFormFieldConfig } from '@/components/forms/dynamic-form';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useUpdateConnection } from '@/hooks/useConnections';
import { useUIStore } from '@/app/store/ui-store';

const MASK_VALUE = '********';

function stripMaskedValues(config: Record<string, unknown> | undefined): Record<string, unknown> | undefined {
  if (!config) return config;

  const next: Record<string, unknown> = { ...config };
  for (const [key, value] of Object.entries(next)) {
    if (value === MASK_VALUE) {
      delete next[key];
    }
  }
  return next;
}

export interface EditConnectionDialogProps {
  connection: Connection | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditConnectionDialog({ connection, open, onOpenChange }: EditConnectionDialogProps) {
  const updateMutation = useUpdateConnection();
  const addNotification = useUIStore((s) => s.addNotification);

  const form = useForm<ConnectionFormValues>({
    resolver: zodResolver(connectionCreateSchema),
    defaultValues: undefined,
    mode: 'onBlur',
  });

  React.useEffect(() => {
    if (!open || !connection) return;

    const defaultValues = {
      name: connection.name,
      description: connection.description ?? undefined,
      protocol: connection.protocol,
      is_active: connection.is_active,
      config: (connection.config ?? {}) as ConnectionFormValues['config'],
    } as ConnectionFormValues;

    form.reset(defaultValues);
  }, [open, connection, form]);

  React.useEffect(() => {
    if (!updateMutation.isError) return;

    addNotification({
      type: 'error',
      title: 'No se pudo actualizar la conexión',
      message:
        updateMutation.error instanceof Error
          ? updateMutation.error.message
          : 'Ocurrió un error inesperado.',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updateMutation.isError]);

  const fields = React.useMemo(() => {
    return connectionFormFields.map((f) => ({
      ...f,
      name: f.name as unknown as never,
    })) as unknown as Array<DynamicFormFieldConfig<ConnectionCreateValues>>;
  }, []);

  const handleSubmit = async (values: ConnectionCreateValues) => {
    if (!connection) return;

    const payload: ConnectionUpdateRequest = {
      ...values,
      config: stripMaskedValues(values.config as Record<string, unknown> | undefined),
    };

    await updateMutation.mutateAsync({ id: connection.id, payload });

    addNotification({
      type: 'success',
      title: 'Conexión actualizada',
      message: 'Los cambios se han guardado correctamente.',
    });

    onOpenChange(false);
  };

  const handleClose = () => {
    updateMutation.reset();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Editar conexión</DialogTitle>
          <DialogDescription>Actualiza la configuración de la conexión.</DialogDescription>
        </DialogHeader>

        <DynamicForm
          form={form}
          fields={fields}
          onSubmit={handleSubmit}
          submitLabel={updateMutation.isPending ? 'Guardando…' : 'Guardar'}
          isSubmitting={updateMutation.isPending}
          className="space-y-0"
          footer={
            <div className="mt-6 flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={updateMutation.isPending}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Guardando…' : 'Guardar'}
              </Button>
            </div>
          }
        />
      </DialogContent>
    </Dialog>
  );
}
