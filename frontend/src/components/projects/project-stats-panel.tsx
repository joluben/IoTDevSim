import { BarChart3, CheckCircle, XCircle, Percent } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import type { ProjectStats } from '@/types/project';

interface ProjectStatsPanelProps {
  stats: ProjectStats | undefined;
  isLoading?: boolean;
}

export function ProjectStatsPanel({ stats, isLoading }: ProjectStatsPanelProps) {
  if (isLoading || !stats) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardContent className="flex items-center gap-4 p-4">
              <div className="h-10 w-10 rounded-lg bg-muted animate-pulse" />
              <div className="space-y-1">
                <div className="h-6 w-12 bg-muted animate-pulse rounded" />
                <div className="h-3 w-20 bg-muted animate-pulse rounded" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const items = [
    { label: 'Total Transmissions', value: stats.total_transmissions, icon: BarChart3, color: 'text-blue-500' },
    { label: 'Successful', value: stats.successful_transmissions, icon: CheckCircle, color: 'text-green-500' },
    { label: 'Failed', value: stats.failed_transmissions, icon: XCircle, color: 'text-red-500' },
    { label: 'Success Rate', value: `${stats.success_rate}%`, icon: Percent, color: 'text-purple-500' },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label}>
          <CardContent className="flex items-center gap-4 p-4">
            <div className={`rounded-lg bg-muted p-2.5 ${item.color}`}>
              <item.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{item.value}</p>
              <p className="text-xs text-muted-foreground">{item.label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
