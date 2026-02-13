import * as React from 'react';
import { CheckCircle2, Info, AlertTriangle, XCircle, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/app/store/ui-store';

const iconByType = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
} as const;

const colorByType = {
  success: 'text-green-600',
  error: 'text-destructive',
  warning: 'text-amber-600',
  info: 'text-blue-600',
} as const;

type NotificationType = keyof typeof iconByType;

export function NotificationsToaster() {
  const notifications = useUIStore((s) => s.notifications);
  const removeNotification = useUIStore((s) => s.removeNotification);

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-[360px] flex-col gap-2">
      {notifications
        .slice()
        .sort((a, b) => b.timestamp - a.timestamp)
        .map((n) => {
          const type = n.type as NotificationType;
          const Icon = iconByType[type] ?? Info;

          return (
            <div
              key={n.id}
              className="rounded-lg border bg-background p-4 shadow-lg"
              role="status"
              aria-live="polite"
            >
              <div className="flex items-start gap-3">
                <Icon className={cn('mt-0.5 h-5 w-5', colorByType[type] ?? 'text-muted-foreground')} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">{n.title}</div>
                      {n.message ? (
                        <div className="mt-0.5 text-sm text-muted-foreground">{n.message}</div>
                      ) : null}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => removeNotification(n.id)}
                      aria-label="Cerrar notificación"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
    </div>
  );
}
