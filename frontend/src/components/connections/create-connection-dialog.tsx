import * as React from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import type { z } from 'zod';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { DynamicForm } from '@/components/forms/dynamic-form';
import { connectionFormFields, type ConnectionFormValues } from '@/features/connections/config/connection-form.config';
import {
  connectionCreateSchema,
  type ConnectionCreateValues,
} from '@/features/connections/validation/connection.schemas';
import { useFormAutoSave } from '@/hooks/useFormAutoSave';
import { useCreateConnection } from '@/hooks/useConnections';
import { useUIStore } from '@/app/store/ui-store';
import type { ProtocolType } from '@/types/connection';

type ConnectionVariantByProtocol<T extends ProtocolType> = Extract<
  ConnectionCreateValues,
  { protocol: T }
>;

type ConfigByProtocol<T extends ProtocolType> = ConnectionVariantByProtocol<T>['config'];

const PROTOCOL_DEFAULTS = {
  mqtt: {
    broker_url: '',
    port: 1883,
    topic: '',
    username: '',
    password: '',
    client_id: '',
    qos: 0,
    retain: false,
    clean_session: true,
    keepalive: 60,
    use_tls: false,
  },
  http: {
    endpoint_url: '',
    method: 'POST',
    auth_type: 'none',
    timeout: 30,
    verify_ssl: true,
    headers: {},
  },
  https: {
    endpoint_url: '',
    method: 'POST',
    auth_type: 'none',
    timeout: 30,
    verify_ssl: true,
    headers: {},
  },
  kafka: {
    bootstrap_servers: [],
    topic: '',
    security_protocol: 'PLAINTEXT',
    compression_type: 'none',
    acks: '1',
  },
} satisfies { [K in ProtocolType]: ConfigByProtocol<K> };

const getProtocolDefaultConfig = <T extends ProtocolType>(protocol: T): ConfigByProtocol<T> => {
  return PROTOCOL_DEFAULTS[protocol] as ConfigByProtocol<T>;
};

const DEFAULT_VALUES = {
  name: '',
  description: '',
  protocol: 'mqtt' as const,
  is_active: true,
  config: PROTOCOL_DEFAULTS.mqtt,
} as ConnectionFormValues;

export interface CreateConnectionDialogProps {
  triggerLabel?: string;
  triggerVariant?: 'default' | 'outline' | 'secondary' | 'ghost' | 'destructive';
  onCreated?: () => void;
}

export function CreateConnectionDialog({
  triggerLabel = 'Nueva conexión',
  triggerVariant = 'default',
  onCreated,
}: CreateConnectionDialogProps) {
  const [open, setOpen] = React.useState(false);
  const createMutation = useCreateConnection();
  const addNotification = useUIStore((s) => s.addNotification);

  const form = useForm<ConnectionFormValues>({
    resolver: zodResolver(connectionCreateSchema),
    defaultValues: DEFAULT_VALUES,
    mode: 'onBlur',
  });
  const protocol = form.watch('protocol');

  const { clearSavedDraft } = useFormAutoSave(form, {
    enabled: open,
    storageKey: 'connection-create-draft',
  });

  React.useEffect(() => {
    if (!createMutation.isError) return;

    addNotification({
      type: 'error',
      title: 'No se pudo crear la conexión',
      message:
        createMutation.error instanceof Error
          ? createMutation.error.message
          : 'Ocurrió un error inesperado.',
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createMutation.isError]);

  React.useEffect(() => {
    form.setValue('config', getProtocolDefaultConfig(protocol));
  }, [protocol, form]);

  const handleSubmit = async (values: ConnectionCreateValues) => {
    await createMutation.mutateAsync(values);
    addNotification({
      type: 'success',
      title: 'Conexión creada',
      message: 'La conexión se creó correctamente.',
    });
    clearSavedDraft();
    form.reset(DEFAULT_VALUES);
    setOpen(false);
    onCreated?.();
  };

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (!next) {
      createMutation.reset();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant={triggerVariant}>{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Nueva conexión</DialogTitle>
          <DialogDescription>Crea una conexión para tu sistema IoT.</DialogDescription>
        </DialogHeader>

        <DynamicForm
          form={form}
          fields={connectionFormFields}
          onSubmit={handleSubmit}
          submitLabel={createMutation.isPending ? 'Creando…' : 'Crear'}
          isSubmitting={createMutation.isPending}
          className="space-y-0"
          footer={
            <div className="mt-6 flex justify-end gap-2">
              <Button
                variant="outline"
                type="button"
                onClick={() => setOpen(false)}
                disabled={createMutation.isPending}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creando…' : 'Crear'}
              </Button>
            </div>
          }
        />
      </DialogContent>
    </Dialog>
  );
}
