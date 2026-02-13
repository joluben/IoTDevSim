import { Cpu, Radio, AlertTriangle, Database } from "lucide-react";
import type { DeviceSummary } from "@/types/device";
import { Card, CardContent } from "@/components/ui/card";

interface DevicesStatsProps {
  devices: DeviceSummary[];
}

export function DevicesStats({ devices }: DevicesStatsProps) {
  const total = devices.length;
  const transmitting = devices.filter((d) => d.transmission_enabled).length;
  const errors = devices.filter((d) => d.status === "error").length;
  const withDataset = devices.filter((d) => d.has_dataset).length;

  const stats = [
    {
      label: "Total Devices",
      value: total,
      icon: Cpu,
      color: "text-blue-500",
    },
    {
      label: "Transmitting",
      value: transmitting,
      icon: Radio,
      color: "text-green-500",
    },
    {
      label: "Errors",
      value: errors,
      icon: AlertTriangle,
      color: "text-red-500",
    },
    {
      label: "With Dataset",
      value: withDataset,
      icon: Database,
      color: "text-purple-500",
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.label}>
          <CardContent className="flex items-center gap-4 p-4">
            <div className={`rounded-lg bg-muted p-2.5 ${stat.color}`}>
              <stat.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stat.value}</p>
              <p className="text-xs text-muted-foreground">{stat.label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
