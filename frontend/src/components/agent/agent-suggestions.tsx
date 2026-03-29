/**
 * Agent Suggestions
 * Contextual suggestion chips that change based on the current page
 */

import React from 'react';
import { Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentSuggestion } from '@/types/agent';

interface AgentSuggestionsProps {
  suggestions: AgentSuggestion[];
  onSelect: (prompt: string) => void;
  className?: string;
}

export function AgentSuggestions({
  suggestions,
  onSelect,
  className,
}: AgentSuggestionsProps) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className={cn('flex flex-wrap gap-2 px-4 py-2', className)}>
      {suggestions.map((suggestion, idx) => (
        <button
          key={`${suggestion.label}-${idx}`}
          type="button"
          onClick={() => onSelect(suggestion.prompt)}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full border border-border',
            'bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground',
            'transition-colors hover:bg-accent hover:text-accent-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          )}
        >
          <Sparkles className="h-3 w-3" />
          {suggestion.label}
        </button>
      ))}
    </div>
  );
}
