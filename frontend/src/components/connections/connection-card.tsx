import * as React from 'react';
import { MoreVertical, Play, Trash2 } from 'lucide-react';

import type { Connection } from '@/types/connection';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

function formatProtocol(protocol: Connection['protocol']) {
  switch (protocol) {
    case 'mqtt':
      return 'MQTT';
    case 'http':
      return 'HTTP';
    case 'https':
      return 'HTTPS';
    case 'kafka':
      return 'Kafka';
    default:
      return protocol;
  }
}

function getStatusBadgeVariant(status: Connection['test_status']): {
  variant: 'default' | 'secondary' | 'destructive' | 'outline';
  className?: string;
  label: string;
} {
  switch (status) {
    case 'success':
      return { variant: 'secondary', label: 'OK' };
    case 'failed':
      return { variant: 'destructive', label: 'Falló' };
    case 'testing':
      return { variant: 'outline', label: 'Probando…', className: 'text-muted-foreground' };
    case 'untested':
    default:
      return { variant: 'outline', label: 'Sin test', className: 'text-muted-foreground' };
  }
}

export interface ConnectionCardProps {
  connection: Connection;
  onTest: (id: string) => void;
  onDelete: (id: string) => void;
  isTesting?: boolean;
  isDeleting?: boolean;
}

export function ConnectionCard({
  connection,
  onTest,
  onDelete,
  isTesting = false,
  isDeleting = false,
}: ConnectionCardProps) {
  const statusBadge = getStatusBadgeVariant(connection.test_status);

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="truncate">{connection.name}</CardTitle>
            <CardDescription className="truncate">
              {connection.description || 'Sin descripción'}
            </CardDescription>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Actions" disabled={isDeleting}>
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => onTest(connection.id)}
                disabled={isTesting || isDeleting}
              >
                <Play className="h-4 w-4" />
                Probar
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onSelect={() => onDelete(connection.id)}
                disabled={isDeleting || isTesting}
              >
                <Trash2 className="h-4 w-4" />
                Eliminar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{formatProtocol(connection.protocol)}</Badge>
          <Badge variant={statusBadge.variant} className={statusBadge.className}>
            {statusBadge.label}
          </Badge>
          <Badge variant={connection.is_active ? 'default' : 'outline'}>
            {connection.is_active ? 'Activa' : 'Inactiva'}
          </Badge>
        </div>

        <div className="text-sm text-muted-foreground">
          {connection.last_tested ? (
            <span>Último test: {new Date(connection.last_tested).toLocaleString()}</span>
          ) : (
            <span>Último test: —</span>
          )}
        </div>

        {connection.test_message ? (
          <div className="text-sm">{connection.test_message}</div>
        ) : null}
      </CardContent>
    </Card>
  );
}
