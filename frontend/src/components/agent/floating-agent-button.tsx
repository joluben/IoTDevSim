/**
 * Floating Agent Button
 * FAB (Floating Action Button) in bottom-right corner.
 * Only visible when the agent-service is available.
 */

import React from 'react';
import { Bot, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAgentContext } from '@/contexts/agent-context';

export function FloatingAgentButton() {
  const { isAvailable, isOpen, togglePanel } = useAgentContext();

  if (!isAvailable) return null;

  return (
    <button
      type="button"
      onClick={togglePanel}
      className={cn(
        'fixed bottom-20 right-6 z-50 flex h-12 w-12 items-center justify-center',
        'rounded-full shadow-lg transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        isOpen
          ? 'bg-muted text-muted-foreground hover:bg-muted/80'
          : 'bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105',
      )}
      title={isOpen ? 'Cerrar asistente' : 'Abrir asistente IA'}
      aria-label={isOpen ? 'Cerrar asistente' : 'Abrir asistente IA'}
    >
      {isOpen ? (
        <X className="h-5 w-5" />
      ) : (
        <Bot className="h-5 w-5" />
      )}
    </button>
  );
}
