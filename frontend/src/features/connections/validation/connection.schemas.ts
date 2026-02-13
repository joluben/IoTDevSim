import { z } from 'zod';

const protocolTypeSchema = z.enum(['mqtt', 'http', 'https', 'kafka']);

const connectionStatusSchema = z.enum(['untested', 'success', 'failed', 'testing']);

const mqttConfigSchema = z
  .object({
    broker_url: z
      .string()
      .min(1, 'Broker URL is required')
      .refine(
        (v) =>
          v.startsWith('mqtt://') ||
          v.startsWith('mqtts://') ||
          v.startsWith('tcp://') ||
          v.startsWith('ws://') ||
          v.startsWith('wss://'),
        {
          message: 'Broker URL must start with mqtt://, mqtts://, tcp://, ws://, or wss://',
        },
      ),
    port: z.number().int().min(1).max(65535).optional(),
    topic: z
      .string()
      .min(1, 'Topic is required')
      .refine((v) => !v.includes('#') && !v.includes('+'), {
        message: 'Topic cannot contain wildcards (# or +) for publishing',
      }),
    username: z.string().optional(),
    password: z.string().optional(),
    client_id: z.string().optional(),
    qos: z.union([z.literal(0), z.literal(1), z.literal(2)]).optional(),
    retain: z.boolean().optional(),
    clean_session: z.boolean().optional(),
    keepalive: z.number().int().min(1).optional(),
    use_tls: z.boolean().optional(),
    ca_cert: z.string().optional(),
    client_cert: z.string().optional(),
    client_key: z.string().optional(),
    ws_path: z.string().optional(),
  })
  .strict();

const httpMethodSchema = z.enum(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']);

const httpAuthTypeSchema = z.enum(['none', 'basic', 'bearer', 'api_key']);

const httpConfigSchemaBase = z
  .object({
    endpoint_url: z
      .string()
      .min(1, 'Endpoint URL is required')
      .refine((v) => v.startsWith('http://') || v.startsWith('https://'), {
        message: 'Endpoint URL must start with http:// or https://',
      }),
    method: httpMethodSchema.optional(),
    auth_type: httpAuthTypeSchema.optional(),
    username: z.string().min(1).optional(),
    password: z.string().min(1).optional(),
    bearer_token: z.string().min(1).optional(),
    api_key_header: z.string().min(1).optional(),
    api_key_value: z.string().min(1).optional(),
    headers: z.record(z.string(), z.string()).optional(),
    timeout: z.number().int().min(1).max(300).optional(),
    verify_ssl: z.boolean().optional(),
  })
  .strict();

const httpConfigSchema = httpConfigSchemaBase.superRefine((values, ctx) => {
  const authType = values.auth_type ?? 'none';

  if (authType === 'basic') {
    if (!values.username) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['username'],
        message: 'Username is required for basic authentication',
      });
    }
    if (!values.password) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['password'],
        message: 'Password is required for basic authentication',
      });
    }
  }

  if (authType === 'bearer' && !values.bearer_token) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['bearer_token'],
      message: 'Bearer token is required for bearer authentication',
    });
  }

  if (authType === 'api_key') {
    if (!values.api_key_header) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['api_key_header'],
        message: 'API key header is required for API key authentication',
      });
    }
    if (!values.api_key_value) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['api_key_value'],
        message: 'API key value is required for API key authentication',
      });
    }
  }
});

const kafkaSecurityProtocolSchema = z.enum(['PLAINTEXT', 'SSL', 'SASL_PLAINTEXT', 'SASL_SSL']);
const kafkaCompressionTypeSchema = z.enum(['none', 'gzip', 'snappy', 'lz4', 'zstd']);
const kafkaAcksSchema = z.enum(['0', '1', 'all']);

const kafkaConfigSchemaBase = z
  .object({
    bootstrap_servers: z
      .array(z.string().min(1))
      .min(1, 'At least one bootstrap server is required')
      .refine((servers) => servers.every((s) => s.includes(':')), {
        message: 'Each bootstrap server must include port (host:port)',
      }),
    topic: z.string().min(1, 'Topic is required'),
    username: z.string().min(1).optional(),
    password: z.string().min(1).optional(),
    security_protocol: kafkaSecurityProtocolSchema.optional(),
    sasl_mechanism: z.string().min(1).optional(),
    ssl_ca_cert: z.string().min(1).optional(),
    ssl_client_cert: z.string().min(1).optional(),
    ssl_client_key: z.string().min(1).optional(),
    compression_type: kafkaCompressionTypeSchema.optional(),
    acks: kafkaAcksSchema.optional(),
    retries: z.number().int().min(0).optional(),
    batch_size: z.number().int().min(1).optional(),
    linger_ms: z.number().int().min(0).optional(),
  })
  .strict();

const kafkaConfigSchema = kafkaConfigSchemaBase.superRefine((values, ctx) => {
  const securityProtocol = values.security_protocol ?? 'PLAINTEXT';

  if (securityProtocol.includes('SASL')) {
    if (!values.username) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['username'],
        message: 'Username is required for SASL authentication',
      });
    }
    if (!values.password) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['password'],
        message: 'Password is required for SASL authentication',
      });
    }
    if (!values.sasl_mechanism) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['sasl_mechanism'],
        message: 'SASL mechanism is required for SASL authentication',
      });
    }
  }
});

const connectionBaseSchema = z.object({
  name: z.string().min(1, 'Connection name is required').max(255),
  description: z.string().max(2000).optional(),
  is_active: z.boolean().optional(),
});

const connectionCreateSchema = z.discriminatedUnion('protocol', [
  connectionBaseSchema.extend({
    protocol: z.literal('mqtt'),
    config: mqttConfigSchema,
  }),
  connectionBaseSchema.extend({
    protocol: z.literal('http'),
    config: httpConfigSchema,
  }),
  connectionBaseSchema.extend({
    protocol: z.literal('https'),
    config: httpConfigSchema,
  }),
  connectionBaseSchema.extend({
    protocol: z.literal('kafka'),
    config: kafkaConfigSchema,
  }),
]);

const connectionUpdateSchema = z
  .object({
    name: z.string().min(1).max(255).optional(),
    description: z.string().max(2000).nullable().optional(),
    protocol: protocolTypeSchema.optional(),
    config: z.record(z.string(), z.unknown()).optional(),
    is_active: z.boolean().optional(),
  })
  .strict();

const connectionSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    description: z.string().nullable().optional(),
    protocol: protocolTypeSchema,
    config: z.record(z.string(), z.unknown()),
    is_active: z.boolean(),
    test_status: connectionStatusSchema,
    last_tested: z.string().nullable().optional(),
    test_message: z.string().nullable().optional(),
    created_at: z.string().optional(),
    updated_at: z.string().optional(),
  })
  .strict();

const connectionListResponseSchema = z
  .object({
    items: z.array(connectionSchema),
    total: z.number(),
    skip: z.number(),
    limit: z.number(),
    has_next: z.boolean(),
    has_prev: z.boolean(),
  })
  .strict();

export {
  protocolTypeSchema,
  connectionStatusSchema,
  mqttConfigSchema,
  httpConfigSchema,
  kafkaConfigSchema,
  connectionCreateSchema,
  connectionUpdateSchema,
  connectionSchema,
  connectionListResponseSchema,
};

export type ConnectionCreateValues = z.infer<typeof connectionCreateSchema>;
export type ConnectionUpdateValues = z.infer<typeof connectionUpdateSchema>;
export type ConnectionValues = z.infer<typeof connectionSchema>;
export type ConnectionListResponseValues = z.infer<typeof connectionListResponseSchema>;
