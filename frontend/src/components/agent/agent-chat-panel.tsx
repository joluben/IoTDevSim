/**
 * Agent Chat Panel
 * Slide-over panel from the right side with full chat functionality
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  X,
  Send,
  Trash2,
  Bot,
  Loader2,
  Minimize2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAgentContext } from '@/contexts/agent-context';
import { AgentMessage } from './agent-message';
import { AgentSuggestions } from './agent-suggestions';

export function AgentChatPanel() {
  const {
    isOpen,
    closePanel,
    messages,
    isStreaming,
    sendMessage,
    suggestions,
    clearChat,
  } = useAgentContext();

  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  const handleSend = useCallback(() => {
    if (!inputValue.trim() || isStreaming) return;
    sendMessage(inputValue);
    setInputValue('');
  }, [inputValue, isStreaming, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleSuggestionSelect = useCallback(
    (prompt: string) => {
      if (isStreaming) return;
      sendMessage(prompt);
    },
    [isStreaming, sendMessage],
  );

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm transition-opacity lg:hidden"
          onClick={closePanel}
          aria-hidden="true"
        />
      )}

      {/* Panel */}
      <div
        className={cn(
          'fixed right-0 top-0 z-50 flex h-full w-full flex-col border-l border-border bg-background shadow-xl transition-transform duration-300 ease-in-out sm:w-[420px]',
          isOpen ? 'translate-x-0' : 'translate-x-full',
        )}
        role="dialog"
        aria-label="Asistente IA"
        aria-hidden={!isOpen}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h2 className="text-sm font-semibold">Asistente IoTDevSim</h2>
              <p className="text-[10px] text-muted-foreground">
                {isStreaming ? 'Escribiendo…' : 'En línea'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={clearChat}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title="Limpiar chat"
              disabled={messages.length === 0}
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={closePanel}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title="Cerrar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
                <Bot className="h-7 w-7 text-primary" />
              </div>
              <h3 className="mb-1 text-sm font-semibold">
                ¡Hola! Soy tu asistente IoT
              </h3>
              <p className="mb-6 text-xs text-muted-foreground">
                Puedo ayudarte a gestionar conexiones, datasets, dispositivos y
                proyectos de simulación.
              </p>

              {/* Suggestions when chat is empty */}
              <AgentSuggestions
                suggestions={suggestions}
                onSelect={handleSuggestionSelect}
                className="justify-center"
              />
            </div>
          ) : (
            <div className="py-2">
              {messages.map((msg) => (
                <AgentMessage key={msg.id} message={msg} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Suggestions when there are messages */}
        {messages.length > 0 && !isStreaming && suggestions.length > 0 && (
          <AgentSuggestions
            suggestions={suggestions}
            onSelect={handleSuggestionSelect}
          />
        )}

        {/* Input area */}
        <div className="border-t border-border p-3">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe tu mensaje…"
              rows={1}
              className={cn(
                'flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm',
                'placeholder:text-muted-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                'max-h-32 min-h-[36px]',
              )}
              disabled={isStreaming}
              style={{
                height: 'auto',
                minHeight: '36px',
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = `${Math.min(target.scrollHeight, 128)}px`;
              }}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!inputValue.trim() || isStreaming}
              className={cn(
                'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors',
                'bg-primary text-primary-foreground hover:bg-primary/90',
                'disabled:cursor-not-allowed disabled:opacity-50',
              )}
              title="Enviar mensaje"
            >
              {isStreaming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
          <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
            El asistente puede cometer errores. Verifica la información
            importante.
          </p>
        </div>
      </div>
    </>
  );
}
