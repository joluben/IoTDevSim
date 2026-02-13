import * as React from 'react';
import { Circle, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { Connection, ConnectionStatus } from '@/types/connection';
import { useTestConnection } from '@/hooks/useConnections';

interface ConnectionStatusIndicatorProps {
  connection: Connection;
  autoRefresh?: boolean;
  refreshInterval?: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  onStatusChange?: (status: ConnectionStatus) => void;
}

export function ConnectionStatusIndicator({
  connection,
  autoRefresh = false,
  refreshInterval = 60000,
  showLabel = true,
  size = 'md',
  onStatusChange,
}: ConnectionStatusIndicatorProps) {
  const [lastChecked, setLastChecked] = React.useState<Date | null>(
    connection.last_tested ? new Date(connection.last_tested) : null
  );
  const testMutation = useTestConnection();

  React.useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      testMutation.mutate(
        { id: connection.id },
        {
          onSuccess: (data) => {
            setLastChecked(new Date());
            if (onStatusChange && data.success) {
              onStatusChange('success');
            } else if (onStatusChange && !data.success) {
              onStatusChange('failed');
            }
          },
        }
      );
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, connection.id, testMutation, onStatusChange]);

  const handleManualRefresh = () => {
    testMutation.mutate(
      { id: connection.id },
      {
        onSuccess: () => {
          setLastChecked(new Date());
        },
      }
    );
  };

  const getStatusConfig = () => {
    switch (connection.test_status) {
      case 'success':
        return {
          color: 'bg-green-500',
          label: 'Conectado',
          icon: Wifi,
          variant: 'default' as const,
        };
      case 'failed':
        return {
          color: 'bg-destructive',
          label: 'Desconectado',
          icon: WifiOff,
          variant: 'destructive' as const,
        };
      case 'testing':
        return {
          color: 'bg-blue-500',
          label: 'Probando',
          icon: RefreshCw,
          variant: 'secondary' as const,
        };
      case 'untested':
      default:
        return {
          color: 'bg-muted-foreground',
          label: 'Sin probar',
          icon: Circle,
          variant: 'secondary' as const,
        };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  const sizeClasses = {
    sm: 'h-2 w-2',
    md: 'h-3 w-3',
    lg: 'h-4 w-4',
  };

  const iconSizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5',
  };

  if (!showLabel) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  'rounded-full',
                  sizeClasses[size],
                  statusConfig.color,
                  connection.test_status === 'testing' && 'animate-pulse'
                )}
              />
              {autoRefresh && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={handleManualRefresh}
                  disabled={testMutation.isPending}
                >
                  <RefreshCw
                    className={cn(
                      'h-3 w-3',
                      testMutation.isPending && 'animate-spin'
                    )}
                  />
                </Button>
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1">
              <p className="font-medium">{statusConfig.label}</p>
              {lastChecked && (
                <p className="text-xs text-muted-foreground">
                  Última verificación: {lastChecked.toLocaleTimeString()}
                </p>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant={statusConfig.variant} className="gap-1.5">
        <StatusIcon
          className={cn(
            iconSizeClasses[size],
            connection.test_status === 'testing' && 'animate-spin'
          )}
        />
        {statusConfig.label}
      </Badge>
      {lastChecked && (
        <span className="text-xs text-muted-foreground">
          {lastChecked.toLocaleTimeString()}
        </span>
      )}
      {autoRefresh && (
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={handleManualRefresh}
          disabled={testMutation.isPending}
        >
          <RefreshCw
            className={cn(
              'h-3 w-3',
              testMutation.isPending && 'animate-spin'
            )}
          />
        </Button>
      )}
    </div>
  );
}
