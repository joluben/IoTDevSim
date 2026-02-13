import * as React from 'react';
import { TrendingUp, TrendingDown, Activity, Clock, Zap, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import type { Connection } from '@/types/connection';

interface PerformanceMetric {
  label: string;
  value: number;
  unit: string;
  trend?: 'up' | 'down' | 'stable';
  status: 'good' | 'warning' | 'critical';
  threshold: {
    good: number;
    warning: number;
  };
}

interface ConnectionPerformanceMetricsProps {
  connection: Connection;
  historicalData?: {
    timestamp: string;
    response_time: number;
    success: boolean;
  }[];
}

export function ConnectionPerformanceMetrics({
  connection,
  historicalData = [],
}: ConnectionPerformanceMetricsProps) {
  const calculateMetrics = (): PerformanceMetric[] => {
    const recentTests = historicalData.slice(-10);
    const avgResponseTime = recentTests.length > 0
      ? recentTests.reduce((sum, test) => sum + test.response_time, 0) / recentTests.length
      : 0;

    const successRate = recentTests.length > 0
      ? (recentTests.filter(t => t.success).length / recentTests.length) * 100
      : 0;

    const lastTest = recentTests[recentTests.length - 1];
    const previousTest = recentTests[recentTests.length - 2];
    
    let responseTrend: 'up' | 'down' | 'stable' = 'stable';
    if (lastTest && previousTest) {
      if (lastTest.response_time > previousTest.response_time * 1.1) {
        responseTrend = 'up';
      } else if (lastTest.response_time < previousTest.response_time * 0.9) {
        responseTrend = 'down';
      }
    }

    const getResponseTimeStatus = (time: number): 'good' | 'warning' | 'critical' => {
      if (time < 100) return 'good';
      if (time < 500) return 'warning';
      return 'critical';
    };

    const getSuccessRateStatus = (rate: number): 'good' | 'warning' | 'critical' => {
      if (rate >= 95) return 'good';
      if (rate >= 80) return 'warning';
      return 'critical';
    };

    return [
      {
        label: 'Tiempo de Respuesta Promedio',
        value: avgResponseTime,
        unit: 'ms',
        trend: responseTrend,
        status: getResponseTimeStatus(avgResponseTime),
        threshold: { good: 100, warning: 500 },
      },
      {
        label: 'Tasa de Éxito',
        value: successRate,
        unit: '%',
        status: getSuccessRateStatus(successRate),
        threshold: { good: 95, warning: 80 },
      },
      {
        label: 'Latencia Actual',
        value: lastTest?.response_time || 0,
        unit: 'ms',
        status: getResponseTimeStatus(lastTest?.response_time || 0),
        threshold: { good: 100, warning: 500 },
      },
      {
        label: 'Pruebas Realizadas',
        value: recentTests.length,
        unit: 'tests',
        status: 'good',
        threshold: { good: 0, warning: 0 },
      },
    ];
  };

  const metrics = calculateMetrics();

  const getStatusColor = (status: 'good' | 'warning' | 'critical') => {
    switch (status) {
      case 'good':
        return 'text-green-600 dark:text-green-400';
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'critical':
        return 'text-destructive';
    }
  };

  const getStatusBadge = (status: 'good' | 'warning' | 'critical') => {
    switch (status) {
      case 'good':
        return <Badge variant="default">Óptimo</Badge>;
      case 'warning':
        return <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-700 dark:text-yellow-400">Advertencia</Badge>;
      case 'critical':
        return <Badge variant="destructive">Crítico</Badge>;
    }
  };

  const getTrendIcon = (trend?: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-destructive" />;
      case 'down':
        return <TrendingDown className="h-4 w-4 text-green-600" />;
      default:
        return <Activity className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getMetricIcon = (label: string) => {
    if (label.includes('Tiempo') || label.includes('Latencia')) {
      return <Clock className="h-4 w-4" />;
    }
    if (label.includes('Tasa')) {
      return <Zap className="h-4 w-4" />;
    }
    return <Activity className="h-4 w-4" />;
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{metric.label}</CardTitle>
              {getMetricIcon(metric.label)}
            </CardHeader>
            <CardContent>
              <div className="flex items-baseline gap-2">
                <div className={`text-2xl font-bold ${getStatusColor(metric.status)}`}>
                  {metric.value.toFixed(metric.unit === '%' ? 1 : 0)}
                </div>
                <span className="text-sm text-muted-foreground">{metric.unit}</span>
                {metric.trend && getTrendIcon(metric.trend)}
              </div>
              <div className="mt-2">
                {getStatusBadge(metric.status)}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Análisis de Rendimiento</CardTitle>
          <CardDescription>
            Métricas detalladas y umbrales de rendimiento
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {metrics.map((metric, index) => (
            <div key={index} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{metric.label}</span>
                  {metric.status === 'critical' && (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${getStatusColor(metric.status)}`}>
                    {metric.value.toFixed(metric.unit === '%' ? 1 : 0)} {metric.unit}
                  </span>
                  {metric.trend && getTrendIcon(metric.trend)}
                </div>
              </div>

              {metric.threshold.good > 0 && (
                <>
                  <Progress
                    value={Math.min((metric.value / metric.threshold.warning) * 100, 100)}
                    className="h-2"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Óptimo: &lt; {metric.threshold.good}{metric.unit}</span>
                    <span>Advertencia: &lt; {metric.threshold.warning}{metric.unit}</span>
                  </div>
                </>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      {historicalData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Historial de Pruebas</CardTitle>
            <CardDescription>
              Últimas {Math.min(historicalData.length, 10)} pruebas realizadas
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {historicalData.slice(-10).reverse().map((test, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <div className={`h-2 w-2 rounded-full ${
                      test.success ? 'bg-green-500' : 'bg-destructive'
                    }`} />
                    <span className="text-sm text-muted-foreground">
                      {new Date(test.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={test.success ? 'default' : 'destructive'}>
                      {test.success ? 'Exitosa' : 'Fallida'}
                    </Badge>
                    <span className="text-sm font-medium">
                      {test.response_time}ms
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recomendaciones</CardTitle>
          <CardDescription>
            Sugerencias para mejorar el rendimiento
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {metrics.some(m => m.status === 'critical') && (
              <li className="flex gap-2 text-sm">
                <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
                <span>
                  Se detectaron métricas críticas. Revisa la configuración de la conexión y
                  verifica el estado del servidor.
                </span>
              </li>
            )}
            {metrics.some(m => m.status === 'warning') && (
              <li className="flex gap-2 text-sm">
                <AlertCircle className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                <span>
                  El rendimiento está por debajo del óptimo. Considera aumentar el timeout o
                  revisar la latencia de red.
                </span>
              </li>
            )}
            {metrics.every(m => m.status === 'good') && (
              <li className="flex gap-2 text-sm">
                <Zap className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span>
                  Todas las métricas están en rangos óptimos. La conexión funciona correctamente.
                </span>
              </li>
            )}
            <li className="flex gap-2 text-sm text-muted-foreground">
              <Activity className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>
                Realiza pruebas periódicas para mantener un historial actualizado de rendimiento.
              </span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
