/**
 * Agent Tool Display
 * Inline visualization of tool executions (loading → result)
 */

import React from 'react';
import { Loader2, CheckCircle2, XCircle, Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolExecution } from '@/types/agent';

const TOOL_LABELS: Record<string, string> = {
  list_connections: 'Listando conexiones…',
  create_connection: 'Creando conexión…',
  test_connection: 'Probando conexión…',
  list_datasets: 'Listando datasets…',
  create_dataset: 'Generando dataset…',
  preview_dataset: 'Previsualizando dataset…',
  get_available_generators: 'Consultando generadores…',
  list_devices: 'Listando dispositivos…',
  create_device: 'Creando dispositivo…',
  get_device_status: 'Consultando estado…',
  link_dataset_to_device: 'Vinculando dataset…',
  list_projects: 'Listando proyectos…',
  create_project: 'Creando proyecto…',
  get_project_details: 'Consultando proyecto…',
  start_transmission: 'Iniciando transmisión…',
  stop_transmission: 'Deteniendo transmisión…',
  get_project_stats: 'Obteniendo estadísticas…',
  query_transmission_logs: 'Consultando logs…',
  get_recent_errors: 'Buscando errores…',
  get_performance_summary: 'Analizando rendimiento…',
  analyze_transmission_trends: 'Analizando tendencias…',
  create_dataset_with_ai: 'Generando dataset con IA…',
};

interface AgentToolDisplayProps {
  executions: ToolExecution[];
}

export function AgentToolDisplay({ executions }: AgentToolDisplayProps) {
  if (!executions || executions.length === 0) return null;

  return (
    <div className="my-2 space-y-1.5">
      {executions.map((exec, idx) => (
        <div
          key={`${exec.tool_name}-${idx}`}
          className={cn(
            'flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs',
            exec.status === 'running' && 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300',
            exec.status === 'completed' && 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300',
            exec.status === 'error' && 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300',
          )}
        >
          {exec.status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
          {exec.status === 'completed' && <CheckCircle2 className="h-3 w-3" />}
          {exec.status === 'error' && <XCircle className="h-3 w-3" />}
          <Wrench className="h-3 w-3 opacity-50" />
          <span className="font-medium">
            {TOOL_LABELS[exec.tool_name] || exec.tool_name}
          </span>
        </div>
      ))}
    </div>
  );
}
