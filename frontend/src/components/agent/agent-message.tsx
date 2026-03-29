/**
 * Agent Message
 * Individual chat message with Markdown rendering and tool execution display
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AgentToolDisplay } from './agent-tool-display';
import type { AgentMessage as AgentMessageType } from '@/types/agent';

interface AgentMessageProps {
  message: AgentMessageType;
}

export function AgentMessage({ message }: AgentMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 px-4 py-3',
        isUser ? 'flex-row-reverse' : 'flex-row',
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground',
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message content */}
      <div
        className={cn(
          'flex max-w-[85%] flex-col gap-1',
          isUser ? 'items-end' : 'items-start',
        )}
      >
        <div
          className={cn(
            'rounded-xl px-3.5 py-2.5 text-sm leading-relaxed',
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground',
          )}
        >
          {/* Tool executions (before text for assistant) */}
          {!isUser && message.toolExecutions && message.toolExecutions.length > 0 && (
            <AgentToolDisplay executions={message.toolExecutions} />
          )}

          {/* Markdown content */}
          {message.content ? (
            <div className="prose prose-sm dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Render code blocks with syntax highlighting style
                  code({ className, children, ...props }) {
                    const isInline = !className;
                    return isInline ? (
                      <code
                        className="rounded bg-black/10 px-1 py-0.5 text-xs dark:bg-white/10"
                        {...props}
                      >
                        {children}
                      </code>
                    ) : (
                      <code
                        className={cn('block overflow-x-auto rounded-md bg-black/5 p-2 text-xs dark:bg-white/5', className)}
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  },
                  // Tables
                  table({ children }) {
                    return (
                      <div className="my-2 overflow-x-auto">
                        <table className="min-w-full text-xs">{children}</table>
                      </div>
                    );
                  },
                  // Links open in new tab
                  a({ href, children }) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline"
                      >
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          ) : message.isStreaming ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span className="text-xs">Pensando…</span>
            </div>
          ) : null}
        </div>

        {/* Timestamp */}
        <span className="px-1 text-[10px] text-muted-foreground">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </div>
  );
}
