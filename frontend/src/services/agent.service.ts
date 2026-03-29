/**
 * Agent Service
 * SSE streaming client for the AI agent chat endpoint
 */

import { AGENT_CONFIG } from '@/app/config/constants';
import { TokenStorage } from './auth.service';
import type {
  AgentChatRequest,
  AgentSuggestion,
  AgentSuggestionsResponse,
  AgentHealthResponse,
} from '@/types/agent';

class AgentService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = AGENT_CONFIG.baseUrl;
  }

  private getAuthHeaders(): Record<string, string> {
    const token = TokenStorage.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  /**
   * Check if the agent service is available
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) return false;
      const data: AgentHealthResponse = await response.json();
      return data.status === 'healthy';
    } catch {
      return false;
    }
  }

  /**
   * Send a chat message and receive SSE streamed response.
   * Calls onToken for each text chunk, onToolCall for tool executions,
   * onComplete when the stream ends, and onError on failures.
   */
  async sendMessage(
    request: AgentChatRequest,
    callbacks: {
      onToken: (token: string) => void;
      onToolCall?: (toolName: string, status: string, result?: string) => void;
      onComplete?: () => void;
      onError?: (error: Error) => void;
    },
    abortSignal?: AbortSignal,
  ): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/agent/chat`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(request),
        signal: abortSignal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Agent error (${response.status}): ${errorText}`);
      }

      if (!response.body) {
        throw new Error('No response body received');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            if (data === '[DONE]') {
              callbacks.onComplete?.();
              return;
            }

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === 'token' || parsed.type === 'text' || parsed.type === 'content') {
                callbacks.onToken(parsed.content || parsed.text || '');
              } else if (parsed.type === 'tool_call') {
                callbacks.onToolCall?.(
                  parsed.tool_name || parsed.name || 'unknown',
                  parsed.status || 'running',
                  parsed.result,
                );
              } else if (parsed.type === 'error') {
                callbacks.onError?.(new Error(parsed.message || parsed.content || 'Agent error'));
                return;
              } else if (parsed.type === 'complete') {
                callbacks.onComplete?.();
                return;
              } else if (parsed.type === 'session') {
                // Session acknowledgment from backend — store session_id if provided
                if (parsed.session_id) {
                  sessionStorage.setItem(
                    AGENT_CONFIG.sessionStorageKey,
                    parsed.session_id,
                  );
                }
              }
            } catch {
              // Plain text token (not JSON)
              callbacks.onToken(data);
            }
          }
        }
      }

      callbacks.onComplete?.();
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        callbacks.onComplete?.();
        return;
      }
      callbacks.onError?.(error instanceof Error ? error : new Error(String(error)));
    }
  }

  /**
   * Get contextual suggestions for the current page
   */
  async getSuggestions(context: string): Promise<AgentSuggestion[]> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/v1/agent/suggestions?context=${encodeURIComponent(context)}`,
        {
          method: 'GET',
          headers: this.getAuthHeaders(),
          signal: AbortSignal.timeout(5000),
        },
      );

      if (!response.ok) return [];

      const data: AgentSuggestionsResponse = await response.json();
      return data.suggestions || [];
    } catch {
      return [];
    }
  }

  /**
   * Generate a unique session ID and persist it in sessionStorage
   */
  getOrCreateSessionId(): string {
    const stored = sessionStorage.getItem(AGENT_CONFIG.sessionStorageKey);
    if (stored) return stored;

    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    sessionStorage.setItem(AGENT_CONFIG.sessionStorageKey, sessionId);
    return sessionId;
  }

  /**
   * Clear the current session
   */
  clearSession(): void {
    sessionStorage.removeItem(AGENT_CONFIG.sessionStorageKey);
  }
}

export const agentService = new AgentService();
