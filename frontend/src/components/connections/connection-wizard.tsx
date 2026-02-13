import * as React from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Form } from '@/components/ui/form';
import { FormWizard, WizardStep } from '@/components/forms/form-wizard';
import { FormSection } from '@/components/forms/form-section';
import { ValidatedField } from '@/components/forms/validated-field';
import { ArrayField } from '@/components/forms/array-field';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useCreateConnection } from '@/hooks/useConnections';
import type { ConnectionCreateValues } from '@/features/connections/validation/connection.schemas';
import type { ProtocolType } from '@/types/connection';

const wizardSteps: WizardStep[] = [
  {
    id: 'basic',
    title: 'Información Básica',
    description: 'Nombre y descripción',
  },
  {
    id: 'protocol',
    title: 'Protocolo',
    description: 'Selecciona el protocolo',
  },
  {
    id: 'configuration',
    title: 'Configuración',
    description: 'Detalles del protocolo',
  },
  {
    id: 'advanced',
    title: 'Avanzado',
    description: 'Opciones adicionales',
    optional: true,
  },
];

const basicSchema = z.object({
  name: z.string().min(1, 'El nombre es requerido').max(100, 'Máximo 100 caracteres'),
  description: z.string().max(500, 'Máximo 500 caracteres').optional(),
  is_active: z.boolean().default(true),
});

const protocolSchema = z.object({
  protocol: z.enum(['mqtt', 'http', 'https', 'kafka']),
});

const mqttConfigSchema = z.object({
  broker_url: z.string().min(1, 'La URL del broker es requerida'),
  port: z.number().min(1).max(65535).optional(),
  topic: z.string().min(1, 'El topic es requerido'),
  username: z.string().optional(),
  password: z.string().optional(),
  client_id: z.string().optional(),
  qos: z.enum(['0', '1', '2']).optional(),
  use_tls: z.boolean().optional(),
});

const httpConfigSchema = z.object({
  endpoint_url: z.string().url('Debe ser una URL válida'),
  method: z.enum(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']).optional(),
  auth_type: z.enum(['none', 'basic', 'bearer', 'api_key']).optional(),
  username: z.string().optional(),
  password: z.string().optional(),
  bearer_token: z.string().optional(),
  timeout: z.number().min(1).max(300).optional(),
  verify_ssl: z.boolean().optional(),
});

const kafkaConfigSchema = z.object({
  bootstrap_servers: z.array(z.string()).min(1, 'Al menos un servidor es requerido'),
  topic: z.string().min(1, 'El topic es requerido'),
  username: z.string().optional(),
  password: z.string().optional(),
});

interface ConnectionWizardProps {
  onComplete: () => void;
  onCancel: () => void;
}

export function ConnectionWizard({ onComplete, onCancel }: ConnectionWizardProps) {
  const [currentStep, setCurrentStep] = React.useState(0);
  const createMutation = useCreateConnection();

  const form = useForm<any>({
    resolver: zodResolver(
      z.object({
        name: z.string().min(1),
        description: z.string().optional(),
        protocol: z.enum(['mqtt', 'http', 'https', 'kafka']),
        is_active: z.boolean(),
        config: z.any(),
      })
    ),
    defaultValues: {
      name: '',
      description: '',
      protocol: 'mqtt' as ProtocolType,
      is_active: true,
      config: {},
    },
    mode: 'onBlur',
  });

  const protocol = form.watch('protocol');

  const validateCurrentStep = async (): Promise<boolean> => {
    const values = form.getValues();

    try {
      switch (currentStep) {
        case 0:
          await basicSchema.parseAsync({
            name: values.name,
            description: values.description,
            is_active: values.is_active,
          });
          return true;
        case 1:
          await protocolSchema.parseAsync({ protocol: values.protocol });
          return true;
        case 2:
          if (protocol === 'mqtt') {
            await mqttConfigSchema.parseAsync(values.config);
          } else if (protocol === 'http' || protocol === 'https') {
            await httpConfigSchema.parseAsync(values.config);
          } else if (protocol === 'kafka') {
            await kafkaConfigSchema.parseAsync(values.config);
          }
          return true;
        case 3:
          return true;
        default:
          return false;
      }
    } catch (error) {
      return false;
    }
  };

  const handleStepChange = async (newStep: number) => {
    if (newStep > currentStep) {
      const isValid = await validateCurrentStep();
      if (!isValid) {
        form.trigger();
        return;
      }
    }
    setCurrentStep(newStep);
  };

  const handleComplete = async () => {
    const isValid = await form.trigger();
    if (!isValid) return;

    const values = form.getValues();
    await createMutation.mutateAsync(values as ConnectionCreateValues);
    onComplete();
  };

  const canGoNext = React.useMemo(() => {
    const values = form.getValues();
    switch (currentStep) {
      case 0:
        return !!values.name;
      case 1:
        return !!values.protocol;
      case 2:
        if (protocol === 'mqtt') {
          return !!values.config?.broker_url && !!values.config?.topic;
        } else if (protocol === 'http' || protocol === 'https') {
          return !!values.config?.endpoint_url;
        } else if (protocol === 'kafka') {
          return !!values.config?.bootstrap_servers?.length && !!values.config?.topic;
        }
        return false;
      case 3:
        return true;
      default:
        return false;
    }
  }, [currentStep, protocol, form.watch()]);

  return (
    <Form {...form}>
      <form className="space-y-6">
        {createMutation.error && (
          <Alert variant="destructive">
            <AlertDescription>
              {createMutation.error instanceof Error
                ? createMutation.error.message
                : 'No se pudo crear la conexión'}
            </AlertDescription>
          </Alert>
        )}

        <FormWizard
          steps={wizardSteps}
          currentStep={currentStep}
          onStepChange={handleStepChange}
          onComplete={handleComplete}
          onCancel={onCancel}
          canGoNext={canGoNext}
          isSubmitting={createMutation.isPending}
        >
          {currentStep === 0 && <BasicInfoStep control={form.control} />}
          {currentStep === 1 && <ProtocolStep control={form.control} />}
          {currentStep === 2 && <ConfigurationStep control={form.control} protocol={protocol} />}
          {currentStep === 3 && <AdvancedStep control={form.control} protocol={protocol} />}
        </FormWizard>
      </form>
    </Form>
  );
}

function BasicInfoStep({ control }: { control: any }) {
  return (
    <div className="space-y-6">
      <FormSection
        title="Información General"
        description="Proporciona un nombre y descripción para tu conexión"
        collapsible={false}
        required
      >
        <ValidatedField
          control={control}
          name="name"
          label="Nombre"
          placeholder="Mi Conexión IoT"
          required
          helpText="Usa un nombre descriptivo que identifique fácilmente esta conexión"
          successMessage="Nombre válido"
          errorRecovery="El nombre debe tener entre 1 y 100 caracteres"
        />

        <ValidatedField
          control={control}
          name="description"
          label="Descripción"
          type="textarea"
          placeholder="Describe el propósito de esta conexión..."
          helpText="Opcional: Agrega detalles sobre el uso de esta conexión"
        />

        <ValidatedField
          control={control}
          name="is_active"
          label="Estado"
          type="select"
          options={[
            { value: 'true', label: 'Activa' },
            { value: 'false', label: 'Inactiva' },
          ]}
          description="Las conexiones activas pueden ser usadas inmediatamente"
        />
      </FormSection>
    </div>
  );
}

function ProtocolStep({ control }: { control: any }) {
  return (
    <div className="space-y-6">
      <FormSection
        title="Selección de Protocolo"
        description="Elige el protocolo de comunicación para tu dispositivo IoT"
        collapsible={false}
        required
      >
        <ValidatedField
          control={control}
          name="protocol"
          label="Protocolo"
          type="select"
          required
          options={[
            { value: 'mqtt', label: 'MQTT - Message Queue Telemetry Transport' },
            { value: 'http', label: 'HTTP - HyperText Transfer Protocol' },
            { value: 'https', label: 'HTTPS - HTTP Secure' },
            { value: 'kafka', label: 'Apache Kafka' },
          ]}
          helpText="MQTT es ideal para dispositivos con recursos limitados. HTTP/HTTPS para APIs REST. Kafka para streaming de datos a gran escala."
          successMessage="Protocolo seleccionado"
        />
      </FormSection>
    </div>
  );
}

function ConfigurationStep({ control, protocol }: { control: any; protocol: ProtocolType }) {
  return (
    <div className="space-y-6">
      {protocol === 'mqtt' && <MQTTConfiguration control={control} />}
      {(protocol === 'http' || protocol === 'https') && <HTTPConfiguration control={control} />}
      {protocol === 'kafka' && <KafkaConfiguration control={control} />}
    </div>
  );
}

function MQTTConfiguration({ control }: { control: any }) {
  return (
    <>
      <FormSection
        title="Configuración del Broker MQTT"
        description="Detalles de conexión al broker MQTT"
        required
        helpText="El broker MQTT es el servidor que gestiona la comunicación entre dispositivos"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <ValidatedField
            control={control}
            name="config.broker_url"
            label="URL del Broker"
            placeholder="mqtt://broker.example.com"
            required
            helpText="Formato: mqtt://host o mqtts://host para conexión segura"
            errorRecovery="Verifica que la URL comience con mqtt:// o mqtts://"
          />

          <ValidatedField
            control={control}
            name="config.port"
            label="Puerto"
            type="number"
            placeholder="1883"
            helpText="Puerto estándar: 1883 (MQTT) o 8883 (MQTTS)"
          />
        </div>

        <ValidatedField
          control={control}
          name="config.topic"
          label="Topic"
          placeholder="sensors/temperature"
          required
          helpText="El topic define el canal de comunicación. Usa / para jerarquías"
          errorRecovery="Los topics no deben contener espacios ni caracteres especiales"
        />
      </FormSection>

      <FormSection
        title="Autenticación"
        description="Credenciales para acceder al broker"
        defaultOpen={false}
        helpText="Deja en blanco si el broker no requiere autenticación"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <ValidatedField
            control={control}
            name="config.username"
            label="Usuario"
            placeholder="usuario"
          />

          <ValidatedField
            control={control}
            name="config.password"
            label="Contraseña"
            type="password"
            placeholder="••••••••"
          />
        </div>
      </FormSection>
    </>
  );
}

function HTTPConfiguration({ control }: { control: any }) {
  return (
    <>
      <FormSection
        title="Configuración HTTP/HTTPS"
        description="Detalles del endpoint HTTP"
        required
      >
        <ValidatedField
          control={control}
          name="config.endpoint_url"
          label="URL del Endpoint"
          type="url"
          placeholder="https://api.example.com/data"
          required
          helpText="URL completa del endpoint incluyendo protocolo (http:// o https://)"
          errorRecovery="Asegúrate de incluir el protocolo (http:// o https://)"
        />
      </FormSection>

      <FormSection
        title="Autenticación HTTP"
        description="Método de autenticación para el endpoint"
        defaultOpen={false}
      >
        <div className="grid gap-4 md:grid-cols-2">
          <ValidatedField
            control={control}
            name="config.auth_type"
            label="Tipo de Autenticación"
            type="select"
            options={[
              { value: 'none', label: 'Sin autenticación' },
              { value: 'basic', label: 'Basic Auth' },
              { value: 'bearer', label: 'Bearer Token' },
              { value: 'api_key', label: 'API Key' },
            ]}
          />

          <ValidatedField
            control={control}
            name="config.method"
            label="Método HTTP"
            type="select"
            options={[
              { value: 'GET', label: 'GET' },
              { value: 'POST', label: 'POST' },
              { value: 'PUT', label: 'PUT' },
              { value: 'PATCH', label: 'PATCH' },
              { value: 'DELETE', label: 'DELETE' },
            ]}
            helpText="POST es el más común para enviar datos de sensores"
          />
        </div>
      </FormSection>
    </>
  );
}

function KafkaConfiguration({ control }: { control: any }) {
  return (
    <>
      <FormSection
        title="Configuración de Kafka"
        description="Detalles de conexión al cluster de Kafka"
        required
      >
        <ArrayField
          control={control}
          name="config.bootstrap_servers"
          label="Bootstrap Servers"
          description="Lista de servidores Kafka para la conexión inicial"
          fields={[
            {
              name: 'server',
              label: 'Servidor',
              placeholder: 'localhost:9092',
            },
          ]}
          defaultItem={{ server: '' }}
          minItems={1}
          maxItems={5}
          addButtonLabel="Agregar Servidor"
        />

        <ValidatedField
          control={control}
          name="config.topic"
          label="Topic"
          placeholder="iot-data"
          required
          helpText="Nombre del topic de Kafka donde se enviarán los datos"
        />
      </FormSection>
    </>
  );
}

function AdvancedStep({ control, protocol }: { control: any; protocol: ProtocolType }) {
  return (
    <div className="space-y-6">
      {protocol === 'mqtt' && (
        <FormSection
          title="Opciones Avanzadas MQTT"
          description="Configuración adicional para MQTT"
          defaultOpen={false}
        >
          <ValidatedField
            control={control}
            name="config.client_id"
            label="Client ID"
            placeholder="iot-device-001"
            helpText="Identificador único del cliente. Se genera automáticamente si se deja vacío"
          />

          <ValidatedField
            control={control}
            name="config.qos"
            label="Quality of Service (QoS)"
            type="select"
            options={[
              { value: '0', label: '0 - At most once' },
              { value: '1', label: '1 - At least once' },
              { value: '2', label: '2 - Exactly once' },
            ]}
            helpText="QoS 0 es más rápido, QoS 2 garantiza entrega única pero es más lento"
          />

          <ValidatedField
            control={control}
            name="config.use_tls"
            label="Usar TLS/SSL"
            type="select"
            options={[
              { value: 'true', label: 'Sí' },
              { value: 'false', label: 'No' },
            ]}
            helpText="Habilita cifrado TLS para conexiones seguras"
          />
        </FormSection>
      )}

      {(protocol === 'http' || protocol === 'https') && (
        <FormSection
          title="Opciones Avanzadas HTTP"
          description="Configuración adicional para HTTP/HTTPS"
          defaultOpen={false}
        >
          <ArrayField
            control={control}
            name="config.headers"
            label="Headers Personalizados"
            description="Headers HTTP adicionales para la petición"
            fields={[
              {
                name: 'key',
                label: 'Nombre',
                placeholder: 'Content-Type',
              },
              {
                name: 'value',
                label: 'Valor',
                placeholder: 'application/json',
              },
            ]}
            defaultItem={{ key: '', value: '' }}
            maxItems={10}
            addButtonLabel="Agregar Header"
          />

          <ValidatedField
            control={control}
            name="config.timeout"
            label="Timeout (segundos)"
            type="number"
            placeholder="30"
            helpText="Tiempo máximo de espera para la respuesta del servidor"
          />

          <ValidatedField
            control={control}
            name="config.verify_ssl"
            label="Verificar Certificado SSL"
            type="select"
            options={[
              { value: 'true', label: 'Sí' },
              { value: 'false', label: 'No' },
            ]}
            helpText="Desactiva solo para desarrollo. En producción siempre debe estar activo"
          />
        </FormSection>
      )}
    </div>
  );
}
