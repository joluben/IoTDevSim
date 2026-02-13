import * as React from 'react';
import { Activity, CheckCircle2, Link2, XCircle } from 'lucide-react';

import type { Connection } from '@/types/connection';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface StatCardProps {
  label: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
}

function StatCard({ label, value, icon: Icon }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}

export interface ConnectionsStatsProps {
  connections: Connection[];
}

export function ConnectionsStats({ connections }: ConnectionsStatsProps) {
  const total = connections.length;
  const active = connections.filter((c) => c.is_active).length;
  const ok = connections.filter((c) => c.test_status === 'success').length;
  const failed = connections.filter((c) => c.test_status === 'failed').length;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard label="Total" value={total} icon={Link2} />
      <StatCard label="Activas" value={active} icon={Activity} />
      <StatCard label="OK" value={ok} icon={CheckCircle2} />
      <StatCard label="Fallidas" value={failed} icon={XCircle} />
    </div>
  );
}
