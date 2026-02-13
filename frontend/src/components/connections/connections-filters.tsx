import * as React from 'react';

import type { ConnectionFilters, ConnectionStatus, ProtocolType } from '@/types/connection';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';

interface MenuOption<TValue extends string> {
  label: string;
  value?: TValue;
}

const protocolOptions: Array<MenuOption<ProtocolType>> = [
  { label: 'Todos' },
  { label: 'MQTT', value: 'mqtt' },
  { label: 'HTTP', value: 'http' },
  { label: 'HTTPS', value: 'https' },
  { label: 'Kafka', value: 'kafka' },
];

const statusOptions: Array<MenuOption<ConnectionStatus>> = [
  { label: 'Todos' },
  { label: 'Sin test', value: 'untested' },
  { label: 'OK', value: 'success' },
  { label: 'Falló', value: 'failed' },
  { label: 'Probando…', value: 'testing' },
];

export interface ConnectionsFiltersProps {
  value: ConnectionFilters;
  onChange: (next: ConnectionFilters) => void;
}

function renderValueLabel<TValue extends string>(
  options: Array<MenuOption<TValue>>,
  value: TValue | undefined
) {
  if (!value) return options[0]?.label ?? 'Todos';
  return options.find((o) => o.value === value)?.label ?? String(value);
}

export function ConnectionsFilters({ value, onChange }: ConnectionsFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex-1">
        <Input
          placeholder="Buscar conexiones…"
          value={value.search ?? ''}
          onChange={(e) => onChange({ ...value, search: e.target.value, skip: 0 })}
        />
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" type="button" className="w-full sm:w-auto justify-between">
              {renderValueLabel(protocolOptions, value.protocol)}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            {protocolOptions.map((opt) => (
              <DropdownMenuItem
                key={opt.label}
                onSelect={() => onChange({ ...value, protocol: opt.value, skip: 0 })}
              >
                {opt.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" type="button" className="w-full sm:w-auto justify-between">
              {renderValueLabel(statusOptions, value.test_status)}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            {statusOptions.map((opt) => (
              <DropdownMenuItem
                key={opt.label}
                onSelect={() => onChange({ ...value, test_status: opt.value, skip: 0 })}
              >
                {opt.label}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => onChange({ ...value, test_status: undefined, skip: 0 })}>
              Limpiar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" type="button" className="w-full sm:w-auto justify-between">
              {value.is_active === undefined
                ? 'Todos'
                : value.is_active
                  ? 'Activas'
                  : 'Inactivas'}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onSelect={() => onChange({ ...value, is_active: undefined, skip: 0 })}>
              Todos
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => onChange({ ...value, is_active: true, skip: 0 })}>
              Activas
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => onChange({ ...value, is_active: false, skip: 0 })}>
              Inactivas
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
