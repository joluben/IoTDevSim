/**
 * Agent Context
 * Global state provider for the AI agent chat panel
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { useLocation } from 'react-router-dom';
import { agentService } from '@/services/agent.service';
import { AGENT_CONFIG } from '@/app/config/constants';
import type { AgentMessage, AgentSuggestion, ToolExecution } from '@/types/agent';

interface AgentContextValue {
  /** Whether the agent-service is reachable */
  isAvailable: boolean;
  /** Whether the chat panel is open */
  isOpen: boolean;
  /** Toggle the chat panel */
  togglePanel: () => void;
  /** Open the chat panel */
  openPanel: () => void;
  /** Close the chat panel */
  closePanel: () => void;
  /** Chat message history */
  messages: AgentMessage[];
  /** Whether the agent is currently streaming a response */
  isStreaming: boolean;
  /** Send a new message to the agent */
  sendMessage: (text: string) => void;
  /** Contextual suggestion chips */
  suggestions: AgentSuggestion[];
  /** Clear the chat history and session */
  clearChat: () => void;
  /** Current page path for contextual suggestions */
  currentPage: string;
}

const AgentContext = createContext<AgentContextValue | null>(null);

let messageIdCounter = 0;
function nextMessageId(): string {
  return `msg_${Date.now()}_${++messageIdCounter}`;
}

export function AgentProvider({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const currentPage = location.pathname;

  const [isAvailable, setIsAvailable] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState<AgentSuggestion[]>([]);

  const abortControllerRef = useRef<AbortController | null>(null);
  const healthIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Health check on mount + periodic
  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      const healthy = await agentService.checkHealth();
      if (mounted) setIsAvailable(healthy);
    };

    checkHealth();
    healthIntervalRef.current = setInterval(checkHealth, AGENT_CONFIG.healthCheckInterval);

    return () => {
      mounted = false;
      if (healthIntervalRef.current) clearInterval(healthIntervalRef.current);
    };
  }, []);

  // Fetch suggestions when page changes or panel opens
  useEffect(() => {
    if (!isAvailable) return;

    const fetchSuggestions = async () => {
      const result = await agentService.getSuggestions(currentPage);
      setSuggestions(result);
    };

    fetchSuggestions();
  }, [currentPage, isAvailable, isOpen]);

  const togglePanel = useCallback(() => setIsOpen((prev) => !prev), []);
  const openPanel = useCallback(() => setIsOpen(true), []);
  const closePanel = useCallback(() => {
    setIsOpen(false);
    // Abort any in-flight stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim() || isStreaming) return;

      // Add user message
      const userMsg: AgentMessage = {
        id: nextMessageId(),
        role: 'user',
        content: text.trim(),
        timestamp: new Date(),
      };

      // Create placeholder for assistant response
      const assistantMsg: AgentMessage = {
        id: nextMessageId(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
        toolExecutions: [],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      const assistantId = assistantMsg.id;
      const sessionId = agentService.getOrCreateSessionId();

      // Abort previous request if any
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      agentService.sendMessage(
        {
          message: text.trim(),
          session_id: sessionId,
          context: currentPage,
        },
        {
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + token }
                  : m,
              ),
            );
          },
          onToolCall: (toolName, status, result) => {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== assistantId) return m;
                const existing = m.toolExecutions || [];
                const idx = existing.findIndex((t) => t.tool_name === toolName);
                const toolExec: ToolExecution = { tool_name: toolName, status: status as ToolExecution['status'], result };
                const updated =
                  idx >= 0
                    ? existing.map((t, i) => (i === idx ? toolExec : t))
                    : [...existing, toolExec];
                return { ...m, toolExecutions: updated };
              }),
            );
          },
          onComplete: () => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, isStreaming: false } : m,
              ),
            );
            setIsStreaming(false);
            abortControllerRef.current = null;
          },
          onError: (error) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content:
                        m.content ||
                        `Error: ${error.message}`,
                      isStreaming: false,
                    }
                  : m,
              ),
            );
            setIsStreaming(false);
            abortControllerRef.current = null;
          },
        },
        controller.signal,
      );
    },
    [isStreaming, currentPage],
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    agentService.clearSession();
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  return (
    <AgentContext.Provider
      value={{
        isAvailable,
        isOpen,
        togglePanel,
        openPanel,
        closePanel,
        messages,
        isStreaming,
        sendMessage,
        suggestions,
        clearChat,
        currentPage,
      }}
    >
      {children}
    </AgentContext.Provider>
  );
}

export function useAgentContext(): AgentContextValue {
  const ctx = useContext(AgentContext);
  if (!ctx) {
    throw new Error('useAgentContext must be used within an AgentProvider');
  }
  return ctx;
}
