/**
 * Agent Service Types
 * TypeScript interfaces for agent chat communication
 */

export interface AgentChatRequest {
  message: string;
  session_id?: string;
  context?: string;
}

export interface AgentSuggestion {
  label: string;
  prompt: string;
  icon?: string;
}

export interface AgentSuggestionsResponse {
  suggestions: AgentSuggestion[];
  context: string;
}

export type MessageRole = 'user' | 'assistant';

export interface ToolExecution {
  tool_name: string;
  status: 'running' | 'completed' | 'error';
  result?: string;
}

export interface AgentMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  toolExecutions?: ToolExecution[];
}

export interface SSEEvent {
  event: string;
  data: string;
}

export interface AgentHealthResponse {
  status: string;
  service: string;
  llm_provider?: {
    status: string;
    provider: string;
    model: string;
  };
}
