import type { DynamicFormFieldConfig } from '@/components/forms/dynamic-form';
import { connectionCreateSchema, type ConnectionCreateValues } from '@/features/connections/validation/connection.schemas';
import type { z } from 'zod';

export type ConnectionFormValues = z.infer<typeof connectionCreateSchema>;

export const connectionFormFields: DynamicFormFieldConfig<z.infer<typeof connectionCreateSchema>>[] = [
  {
    name: 'name',
    label: 'Nombre',
    type: 'text',
    placeholder: 'Producción',
  },
  {
    name: 'description',
    label: 'Descripción',
    type: 'textarea',
    placeholder: 'Describe esta conexión',
  },
  {
    name: 'protocol',
    label: 'Protocolo',
    type: 'select',
    options: [
      { value: 'mqtt', label: 'MQTT' },
      { value: 'http', label: 'HTTP' },
      { value: 'https', label: 'HTTPS' },
      { value: 'kafka', label: 'Kafka' }
    ],
  },

  // MQTT
  {
    name: 'config.broker_url',
    label: 'Broker URL',
    type: 'text',
    placeholder: 'mqtt://broker.example.com',
    description: 'Protocolos: mqtt://, mqtts://, tcp://, ws://, wss://',
    layout: 'half',
    visibleWhen: [{ field: 'protocol', equals: 'mqtt' }],
  },
  {
    name: 'config.port',
    label: 'Puerto',
    type: 'number',
    placeholder: '1883',
    layout: 'half',
    visibleWhen: [{ field: 'protocol', equals: 'mqtt' }],
  },
  {
    name: 'config.topic',
    label: 'Topic',
    type: 'text',
    placeholder: '/factory/line/1',
    visibleWhen: [{ field: 'protocol', equals: 'mqtt' }],
  },
  {
    name: 'config.username',
    label: 'Usuario',
    type: 'text',
    layout: 'half',
    visibleWhen: [{ field: 'protocol', equals: 'mqtt' }],
  },
  {
    name: 'config.password',
    label: 'Password',
    type: 'password',
    layout: 'half',
    visibleWhen: [{ field: 'protocol', equals: 'mqtt' }],
  },
  {
    name: 'config.ws_path',
    label: 'WebSocket Path',
    type: 'text',
    placeholder: '/mqtt',
    description: 'Ruta WebSocket del broker (por defecto /mqtt)',
    layout: 'half',
    visibleWhen: [
      { field: 'protocol', equals: 'mqtt' },
      { field: 'config.broker_url', includes: 'ws://' },
    ],
  },
  {
    name: 'config.ws_path',
    label: 'WebSocket Path',
    type: 'text',
    placeholder: '/mqtt',
    description: 'Ruta WebSocket del broker (por defecto /mqtt)',
    layout: 'half',
    visibleWhen: [
      { field: 'protocol', equals: 'mqtt' },
      { field: 'config.broker_url', includes: 'wss://' },
    ],
  },

  // HTTP/HTTPS
  {
    name: 'config.endpoint_url',
    label: 'Endpoint URL',
    type: 'text',
    placeholder: 'https://example.com/webhook',
    visibleWhen: [{ field: 'protocol', equals: 'http' }],
  },
  {
    name: 'config.endpoint_url',
    label: 'Endpoint URL',
    type: 'text',
    placeholder: 'https://example.com/webhook',
    visibleWhen: [{ field: 'protocol', equals: 'https' }],
  },
  {
    name: 'config.auth_type',
    label: 'Auth',
    type: 'select',
    options: [
      { label: 'None', value: 'none' },
      { label: 'Basic', value: 'basic' },
      { label: 'Bearer', value: 'bearer' },
      { label: 'API Key', value: 'api_key' },
    ],
    layout: 'half',
    visibleWhen: [{ field: 'protocol', equals: 'http' }],
  },
  {
    name: 'config.auth_type',
    label: 'Auth',
    type: 'select',
    options: [
      { label: 'None', value: 'none' },
      { label: 'Basic', value: 'basic' },
      { label: 'Bearer', value: 'bearer' },
      { label: 'API Key', value: 'api_key' },
    ],
    layout: 'half',
    visibleWhen: [{ field: 'protocol', equals: 'https' }],
  },
  {
    name: 'config.method',
    label: 'Método',
    type: 'select',
    options: [
      { label: 'GET', value: 'GET' },
      { label: 'POST', value: 'POST' },
      { label: 'PUT', value: 'PUT' },
      { label: 'PATCH', value: 'PATCH' },
      { label: 'DELETE', value: 'DELETE' },
    ],
    layout: 'half',
    visibleWhen: [{ field: 'protocol', equals: 'http' }],
  },
  {
    name: 'config.method',
    label: 'Método',
    type: 'select',
    options: [
      { label: 'GET', value: 'GET' },
      { label: 'POST', value: 'POST' },
      { label: 'PUT', value: 'PUT' },
      { label: 'PATCH', value: 'PATCH' },
      { label: 'DELETE', value: 'DELETE' },
    ],
    layout: 'half',
    visibleWhen: [{ field: 'protocol', equals: 'https' }],
  },
  {
    name: 'config.username',
    label: 'Usuario',
    type: 'text',
    visibleWhen: [
      { field: 'protocol', equals: 'http' },
      { field: 'config.auth_type', equals: 'basic' },
    ],
  },
  {
    name: 'config.password',
    label: 'Password',
    type: 'password',
    visibleWhen: [
      { field: 'protocol', equals: 'http' },
      { field: 'config.auth_type', equals: 'basic' },
    ],
  },
  {
    name: 'config.username',
    label: 'Usuario',
    type: 'text',
    visibleWhen: [
      { field: 'protocol', equals: 'https' },
      { field: 'config.auth_type', equals: 'basic' },
    ],
  },
  {
    name: 'config.password',
    label: 'Password',
    type: 'password',
    visibleWhen: [
      { field: 'protocol', equals: 'https' },
      { field: 'config.auth_type', equals: 'basic' },
    ],
  },
  {
    name: 'config.bearer_token',
    label: 'Bearer token',
    type: 'password',
    visibleWhen: [
      { field: 'protocol', equals: 'http' },
      { field: 'config.auth_type', equals: 'bearer' },
    ],
  },
  {
    name: 'config.bearer_token',
    label: 'Bearer token',
    type: 'password',
    visibleWhen: [
      { field: 'protocol', equals: 'https' },
      { field: 'config.auth_type', equals: 'bearer' },
    ],
  },
  {
    name: 'config.api_key_header',
    label: 'API Key header',
    type: 'text',
    placeholder: 'X-API-Key',
    visibleWhen: [
      { field: 'protocol', equals: 'http' },
      { field: 'config.auth_type', equals: 'api_key' },
    ],
  },
  {
    name: 'config.api_key_value',
    label: 'API Key value',
    type: 'password',
    visibleWhen: [
      { field: 'protocol', equals: 'http' },
      { field: 'config.auth_type', equals: 'api_key' },
    ],
  },
  {
    name: 'config.api_key_header',
    label: 'API Key header',
    type: 'text',
    placeholder: 'X-API-Key',
    visibleWhen: [
      { field: 'protocol', equals: 'https' },
      { field: 'config.auth_type', equals: 'api_key' },
    ],
  },
  {
    name: 'config.api_key_value',
    label: 'API Key value',
    type: 'password',
    visibleWhen: [
      { field: 'protocol', equals: 'https' },
      { field: 'config.auth_type', equals: 'api_key' },
    ],
  },
  {
    name: 'config.timeout',
    label: 'Timeout (s)',
    type: 'number',
    placeholder: '30',
    visibleWhen: [{ field: 'protocol', equals: 'http' }],
  },
  {
    name: 'config.timeout',
    label: 'Timeout (s)',
    type: 'number',
    placeholder: '30',
    visibleWhen: [{ field: 'protocol', equals: 'https' }],
  },
  {
    name: 'config.verify_ssl',
    label: 'Verificar SSL',
    type: 'switch',
    visibleWhen: [{ field: 'protocol', equals: 'https' }],
  },

  // Kafka
  {
    name: 'config.bootstrap_servers',
    label: 'Bootstrap servers',
    type: 'text_array',
    placeholder: 'localhost:9092, kafka:9092',
    description: 'Lista separada por comas (host:port)',
    visibleWhen: [{ field: 'protocol', equals: 'kafka' }],
  },
  {
    name: 'config.topic',
    label: 'Topic',
    type: 'text',
    placeholder: 'events',
    visibleWhen: [{ field: 'protocol', equals: 'kafka' }],
  },
  {
    name: 'config.security_protocol',
    label: 'Security protocol',
    type: 'select',
    options: [
      { label: 'PLAINTEXT', value: 'PLAINTEXT' },
      { label: 'SSL', value: 'SSL' },
      { label: 'SASL_PLAINTEXT', value: 'SASL_PLAINTEXT' },
      { label: 'SASL_SSL', value: 'SASL_SSL' },
    ],
    visibleWhen: [{ field: 'protocol', equals: 'kafka' }],
  },
  {
    name: 'config.sasl_mechanism',
    label: 'SASL mechanism',
    type: 'text',
    placeholder: 'PLAIN',
    visibleWhen: [
      { field: 'protocol', equals: 'kafka' },
      { field: 'config.security_protocol', includes: 'SASL' },
    ],
  },
  {
    name: 'config.username',
    label: 'Usuario',
    type: 'text',
    visibleWhen: [
      { field: 'protocol', equals: 'kafka' },
      { field: 'config.security_protocol', includes: 'SASL' },
    ],
  },
  {
    name: 'config.password',
    label: 'Password',
    type: 'password',
    visibleWhen: [
      { field: 'protocol', equals: 'kafka' },
      { field: 'config.security_protocol', includes: 'SASL' },
    ],
  },
];
