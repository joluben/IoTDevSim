import * as React from 'react';
import { Activity, AlertCircle, CheckCircle, Clock, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useConnections } from '@/hooks/useConnections';
import type { Connection, ConnectionStatus } from '@/types/connection';

interface ConnectionHealthDashboardProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function ConnectionHealthDashboard({
  autoRefresh = true,
  refreshInterval = 30000,
}: ConnectionHealthDashboardProps) {
  const { data, isLoading, refetch } = useConnections({});
  const [lastRefresh, setLastRefresh] = React.useState<Date>(new Date());

  const connections = data?.items ?? [];

  React.useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      refetch();
      setLastRefresh(new Date());
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, refetch]);

  const handleManualRefresh = () => {
    refetch();
    setLastRefresh(new Date());
  };

  const stats = React.useMemo(() => {
    const total = connections.length;
    const active = connections.filter((c) => c.is_active).length;
    const inactive = total - active;
    const tested = connections.filter((c) => c.test_status !== 'untested').length;
    const successful = connections.filter((c) => c.test_status === 'success').length;
    const failed = connections.filter((c) => c.test_status === 'failed').length;
    const untested = connections.filter((c) => c.test_status === 'untested').length;

    const successRate = tested > 0 ? (successful / tested) * 100 : 0;
    const activeRate = total > 0 ? (active / total) * 100 : 0;

    return {
      total,
      active,
      inactive,
      tested,
      successful,
      failed,
      untested,
      successRate,
      activeRate,
    };
  }, [connections]);

  const getStatusColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'success':
        return 'text-green-600 dark:text-green-400';
      case 'failed':
        return 'text-destructive';
      case 'testing':
        return 'text-blue-600 dark:text-blue-400';
      case 'untested':
      default:
        return 'text-muted-foreground';
    }
  };

  const getHealthStatus = () => {
    if (stats.successRate >= 90) return { label: 'Excelente', color: 'text-green-600', icon: CheckCircle };
    if (stats.successRate >= 70) return { label: 'Bueno', color: 'text-blue-600', icon: TrendingUp };
    if (stats.successRate >= 50) return { label: 'Regular', color: 'text-yellow-600', icon: Activity };
    return { label: 'Crítico', color: 'text-destructive', icon: AlertCircle };
  };

  const healthStatus = getHealthStatus();
  const HealthIcon = healthStatus.icon;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Monitor de Salud de Conexiones</h2>
          <p className="text-sm text-muted-foreground">
            Última actualización: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleManualRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Actualizar
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Conexiones</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">
              {stats.active} activas, {stats.inactive} inactivas
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Estado de Salud</CardTitle>
            <HealthIcon className={`h-4 w-4 ${healthStatus.color}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${healthStatus.color}`}>
              {healthStatus.label}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.successRate.toFixed(1)}% tasa de éxito
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pruebas Exitosas</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.successful}</div>
            <p className="text-xs text-muted-foreground">
              de {stats.tested} probadas
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pruebas Fallidas</CardTitle>
            <AlertCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{stats.failed}</div>
            <p className="text-xs text-muted-foreground">
              {stats.untested} sin probar
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Tasa de Activación</CardTitle>
            <CardDescription>
              Porcentaje de conexiones activas
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Progress value={stats.activeRate} className="h-2" />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">
                {stats.active} de {stats.total} conexiones
              </span>
              <span className="font-medium">{stats.activeRate.toFixed(1)}%</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tasa de Éxito en Pruebas</CardTitle>
            <CardDescription>
              Porcentaje de pruebas exitosas
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Progress 
              value={stats.successRate} 
              className="h-2"
            />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">
                {stats.successful} de {stats.tested} pruebas
              </span>
              <span className="font-medium">{stats.successRate.toFixed(1)}%</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Estado de Conexiones</CardTitle>
          <CardDescription>
            Vista detallada del estado de cada conexión
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {connections.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                No hay conexiones disponibles
              </p>
            ) : (
              connections.map((connection) => (
                <div
                  key={connection.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <div className={`h-2 w-2 rounded-full ${
                      connection.is_active ? 'bg-green-500' : 'bg-gray-400'
                    }`} />
                    <div className="flex-1">
                      <div className="font-medium">{connection.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {connection.protocol.toUpperCase()}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge variant={connection.is_active ? 'default' : 'secondary'}>
                      {connection.is_active ? 'Activa' : 'Inactiva'}
                    </Badge>
                    <Badge 
                      variant={
                        connection.test_status === 'success' ? 'default' :
                        connection.test_status === 'failed' ? 'destructive' :
                        'secondary'
                      }
                      className={getStatusColor(connection.test_status)}
                    >
                      {connection.test_status === 'success' && <CheckCircle className="h-3 w-3 mr-1" />}
                      {connection.test_status === 'failed' && <AlertCircle className="h-3 w-3 mr-1" />}
                      {connection.test_status === 'testing' && <Clock className="h-3 w-3 mr-1" />}
                      {connection.test_status === 'untested' ? 'Sin probar' :
                       connection.test_status === 'success' ? 'Exitosa' :
                       connection.test_status === 'failed' ? 'Fallida' :
                       'Probando'}
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
