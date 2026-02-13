import * as React from 'react';
import { AlertTriangle, Bug, Network, Lock, Clock, Info, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { Connection } from '@/types/connection';

interface ErrorCategory {
  id: string;
  name: string;
  icon: React.ElementType;
  color: string;
  description: string;
}

const errorCategories: ErrorCategory[] = [
  {
    id: 'network',
    name: 'Red',
    icon: Network,
    color: 'text-blue-600',
    description: 'Problemas de conectividad de red',
  },
  {
    id: 'authentication',
    name: 'Autenticación',
    icon: Lock,
    color: 'text-yellow-600',
    description: 'Errores de credenciales o permisos',
  },
  {
    id: 'timeout',
    name: 'Timeout',
    icon: Clock,
    color: 'text-orange-600',
    description: 'Tiempos de espera excedidos',
  },
  {
    id: 'configuration',
    name: 'Configuración',
    icon: Bug,
    color: 'text-purple-600',
    description: 'Errores en la configuración',
  },
];

interface ErrorSolution {
  problem: string;
  solution: string;
  steps: string[];
  documentation?: string;
}

const errorSolutions: Record<string, ErrorSolution[]> = {
  network: [
    {
      problem: 'No se puede conectar al servidor',
      solution: 'Verificar conectividad de red y configuración del firewall',
      steps: [
        'Verifica que la URL del servidor sea correcta',
        'Comprueba que el puerto esté abierto en el firewall',
        'Asegúrate de que el servidor esté en ejecución',
        'Prueba la conectividad con ping o telnet',
      ],
      documentation: 'https://docs.example.com/network-troubleshooting',
    },
    {
      problem: 'Conexión rechazada',
      solution: 'El servidor está rechazando la conexión',
      steps: [
        'Verifica que el servicio esté activo en el servidor',
        'Comprueba las reglas del firewall del servidor',
        'Revisa los logs del servidor para más detalles',
        'Verifica que no haya límites de conexiones activas',
      ],
    },
  ],
  authentication: [
    {
      problem: 'Credenciales inválidas',
      solution: 'Las credenciales proporcionadas son incorrectas',
      steps: [
        'Verifica que el usuario y contraseña sean correctos',
        'Comprueba que la cuenta no esté bloqueada',
        'Asegúrate de usar el método de autenticación correcto',
        'Revisa los permisos de la cuenta en el servidor',
      ],
    },
    {
      problem: 'Token expirado',
      solution: 'El token de autenticación ha caducado',
      steps: [
        'Genera un nuevo token de acceso',
        'Actualiza las credenciales en la configuración',
        'Verifica la fecha de expiración del token',
        'Considera usar tokens con mayor duración',
      ],
    },
  ],
  timeout: [
    {
      problem: 'Timeout de conexión',
      solution: 'La conexión tardó demasiado en establecerse',
      steps: [
        'Aumenta el valor de timeout en la configuración',
        'Verifica la latencia de red al servidor',
        'Comprueba que el servidor no esté sobrecargado',
        'Considera usar un servidor más cercano geográficamente',
      ],
    },
  ],
  configuration: [
    {
      problem: 'Configuración inválida',
      solution: 'Los parámetros de configuración son incorrectos',
      steps: [
        'Revisa todos los campos de configuración',
        'Verifica el formato de URLs y puertos',
        'Comprueba que los valores estén dentro de rangos válidos',
        'Consulta la documentación del protocolo',
      ],
    },
    {
      problem: 'Protocolo no soportado',
      solution: 'El servidor no soporta el protocolo configurado',
      steps: [
        'Verifica qué protocolos soporta el servidor',
        'Actualiza la configuración al protocolo correcto',
        'Comprueba la versión del protocolo',
        'Revisa la documentación del servidor',
      ],
    },
  ],
};

interface ConnectionErrorReportProps {
  connection: Connection;
  errorMessage?: string;
  errorDetails?: Record<string, any>;
}

export function ConnectionErrorReport({
  connection,
  errorMessage,
  errorDetails,
}: ConnectionErrorReportProps) {
  const [selectedCategory, setSelectedCategory] = React.useState<string>('network');

  const categorizeError = (message: string): string => {
    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.includes('timeout') || lowerMessage.includes('timed out')) {
      return 'timeout';
    }
    if (lowerMessage.includes('auth') || lowerMessage.includes('credential') || 
        lowerMessage.includes('permission') || lowerMessage.includes('unauthorized')) {
      return 'authentication';
    }
    if (lowerMessage.includes('config') || lowerMessage.includes('invalid') ||
        lowerMessage.includes('format')) {
      return 'configuration';
    }
    return 'network';
  };

  const detectedCategory = errorMessage ? categorizeError(errorMessage) : 'network';
  const currentCategory = errorCategories.find(c => c.id === selectedCategory) || errorCategories[0];
  const solutions = errorSolutions[selectedCategory] || [];

  return (
    <div className="space-y-6">
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Error de Conexión Detectado</AlertTitle>
        <AlertDescription>
          {errorMessage || 'La conexión ha fallado. Revisa los detalles a continuación.'}
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Categorías de Error</CardTitle>
          <CardDescription>
            Selecciona una categoría para ver soluciones específicas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {errorCategories.map((category) => {
              const Icon = category.icon;
              const isDetected = category.id === detectedCategory;
              const isSelected = category.id === selectedCategory;
              
              return (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`relative p-4 rounded-lg border-2 transition-all ${
                    isSelected
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  {isDetected && (
                    <Badge className="absolute -top-2 -right-2" variant="destructive">
                      Detectado
                    </Badge>
                  )}
                  <Icon className={`h-6 w-6 mx-auto mb-2 ${category.color}`} />
                  <div className="text-sm font-medium">{category.name}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {category.description}
                  </div>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            {React.createElement(currentCategory.icon, {
              className: `h-5 w-5 ${currentCategory.color}`,
            })}
            <CardTitle>Soluciones para {currentCategory.name}</CardTitle>
          </div>
          <CardDescription>{currentCategory.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-4">
              {solutions.length === 0 ? (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    No hay soluciones específicas disponibles para esta categoría.
                    Consulta la documentación general o contacta con soporte.
                  </AlertDescription>
                </Alert>
              ) : (
                solutions.map((solution, index) => (
                  <Card key={index}>
                    <CardHeader>
                      <CardTitle className="text-base">{solution.problem}</CardTitle>
                      <CardDescription>{solution.solution}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div>
                        <h4 className="text-sm font-medium mb-2">Pasos para resolver:</h4>
                        <ol className="space-y-2">
                          {solution.steps.map((step, stepIndex) => (
                            <li key={stepIndex} className="flex gap-2 text-sm">
                              <span className="flex-shrink-0 flex items-center justify-center h-5 w-5 rounded-full bg-primary/10 text-primary text-xs font-medium">
                                {stepIndex + 1}
                              </span>
                              <span className="flex-1">{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                      {solution.documentation && (
                        <Button variant="outline" size="sm" asChild>
                          <a
                            href={solution.documentation}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ExternalLink className="h-4 w-4 mr-2" />
                            Ver Documentación
                          </a>
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {errorDetails && Object.keys(errorDetails).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Detalles Técnicos</CardTitle>
            <CardDescription>
              Información adicional sobre el error
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="text-xs font-mono bg-muted p-4 rounded-lg overflow-auto">
              {JSON.stringify(errorDetails, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Información de la Conexión</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="font-medium text-muted-foreground">Nombre</dt>
              <dd className="mt-1">{connection.name}</dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Protocolo</dt>
              <dd className="mt-1">
                <Badge variant="outline">{connection.protocol.toUpperCase()}</Badge>
              </dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Estado</dt>
              <dd className="mt-1">
                <Badge variant={connection.is_active ? 'default' : 'secondary'}>
                  {connection.is_active ? 'Activa' : 'Inactiva'}
                </Badge>
              </dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Última Prueba</dt>
              <dd className="mt-1">
                {connection.last_tested
                  ? new Date(connection.last_tested).toLocaleString()
                  : 'Nunca'}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
