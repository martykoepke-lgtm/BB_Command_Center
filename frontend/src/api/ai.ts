import { api } from './client';

export interface AIMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AIChatResponse {
  response: string;
  agent: string;
  suggested_actions?: string[];
}

export const aiApi = {
  chat: (message: string, context?: { initiative_id?: string; phase?: string; agent?: string }) =>
    api.post<AIChatResponse>('/api/ai/chat', { message, ...context }),

  invoke: (agent: string, message: string, context?: Record<string, unknown>) =>
    api.post<AIChatResponse>('/api/ai/invoke', { agent, message, context }),

  agents: () =>
    api.get<{ agents: string[] }>('/api/ai/agents'),

  streamChat: async function* (
    message: string,
    context?: { initiative_id?: string; phase?: string; agent?: string },
  ): AsyncGenerator<string> {
    const token = localStorage.getItem('bb_token');
    const response = await fetch('/api/ai/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, ...context }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`Stream failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          yield data;
        }
      }
    }
  },
};
