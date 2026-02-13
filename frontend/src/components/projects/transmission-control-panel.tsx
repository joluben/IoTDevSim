import { Play, Pause, Square, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { TransmissionStatus, ProjectTransmissionResult } from '@/types/project';

interface TransmissionControlPanelProps {
  transmissionStatus: TransmissionStatus;
  deviceCount: number;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onClearLogs?: () => void;
  isLoading?: boolean;
  lastResult?: ProjectTransmissionResult | null;
}

export function TransmissionControlPanel({
  transmissionStatus,
  deviceCount,
  onStart,
  onPause,
  onResume,
  onStop,
  onClearLogs,
  isLoading = false,
  lastResult,
}: TransmissionControlPanelProps) {
  const getStatusDisplay = () => {
    const map: Record<TransmissionStatus, { label: string; color: string; variant: 'default' | 'secondary' | 'outline' }> = {
      inactive: { label: 'Inactive', color: 'text-muted-foreground', variant: 'secondary' },
      active: { label: 'Active', color: 'text-green-600', variant: 'default' },
      paused: { label: 'Paused', color: 'text-yellow-600', variant: 'outline' },
    };
    return map[transmissionStatus];
  };

  const status = getStatusDisplay();

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Transmission Control</CardTitle>
          <Badge variant={status.variant} className={status.color}>
            {status.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          {transmissionStatus === 'inactive' && (
            <Button onClick={onStart} disabled={isLoading || deviceCount === 0} className="gap-2">
              <Play className="h-4 w-4" />
              Start All
            </Button>
          )}

          {transmissionStatus === 'active' && (
            <>
              <Button onClick={onPause} disabled={isLoading} variant="outline" className="gap-2">
                <Pause className="h-4 w-4" />
                Pause
              </Button>
              <Button onClick={onStop} disabled={isLoading} variant="destructive" className="gap-2">
                <Square className="h-4 w-4" />
                Stop
              </Button>
            </>
          )}

          {transmissionStatus === 'paused' && (
            <>
              <Button onClick={onResume} disabled={isLoading} className="gap-2">
                <RefreshCw className="h-4 w-4" />
                Resume
              </Button>
              <Button onClick={onStop} disabled={isLoading} variant="destructive" className="gap-2">
                <Square className="h-4 w-4" />
                Stop
              </Button>
            </>
          )}
        </div>

        {deviceCount === 0 && transmissionStatus === 'inactive' && (
          <p className="text-sm text-muted-foreground">
            Assign devices to this project before starting transmissions.
          </p>
        )}

        {lastResult && (
          <div className="rounded-md border p-3 text-sm space-y-1">
            <div className="font-medium">
              Last operation: <span className="capitalize">{lastResult.operation}</span>
            </div>
            <div className="text-muted-foreground">
              {lastResult.success_count} succeeded, {lastResult.failure_count} failed
              {' '}of {lastResult.total_devices} devices
            </div>
            {lastResult.results
              .filter((r) => !r.success)
              .map((r) => (
                <div key={r.device_id} className="text-destructive text-xs">
                  {r.device_name}: {r.message}
                </div>
              ))}
          </div>
        )}

        {onClearLogs && (
          <Button
            onClick={onClearLogs}
            disabled={isLoading}
            variant="outline"
            size="sm"
            className="gap-2 w-full"
          >
            <Trash2 className="h-4 w-4" />
            Clear Logs
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
