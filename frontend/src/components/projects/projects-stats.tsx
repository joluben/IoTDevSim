import { FolderOpen, Radio, Pause, Archive } from "lucide-react";
import type { ProjectSummary } from "@/types/project";
import { Card, CardContent } from "@/components/ui/card";

interface ProjectsStatsProps {
  projects: ProjectSummary[];
}

export function ProjectsStats({ projects }: ProjectsStatsProps) {
  const total = projects.length;
  const active = projects.filter((p) => p.transmission_status === "active").length;
  const paused = projects.filter((p) => p.transmission_status === "paused").length;
  const archived = projects.filter((p) => p.is_archived).length;

  const stats = [
    { label: "Total Projects", value: total, icon: FolderOpen, color: "text-blue-500" },
    { label: "Transmitting", value: active, icon: Radio, color: "text-green-500" },
    { label: "Paused", value: paused, icon: Pause, color: "text-yellow-500" },
    { label: "Archived", value: archived, icon: Archive, color: "text-muted-foreground" },
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
