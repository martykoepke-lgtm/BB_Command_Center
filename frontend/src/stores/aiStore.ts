import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  agent?: string;
  isStreaming?: boolean;
}

interface AIState {
  messages: ChatMessage[];
  isStreaming: boolean;
  activeAgent: string | null;
  contextInitiativeId: string | null;
  contextPhase: string | null;

  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  setStreaming: (streaming: boolean) => void;
  setActiveAgent: (agent: string | null) => void;
  setContext: (initiativeId: string | null, phase?: string | null) => void;
  clearMessages: () => void;
}

export const useAIStore = create<AIState>((set) => ({
  messages: [],
  isStreaming: false,
  activeAgent: null,
  contextInitiativeId: null,
  contextPhase: null,

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateLastMessage: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length > 0) {
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content };
      }
      return { messages: msgs };
    }),

  setStreaming: (streaming) => set({ isStreaming: streaming }),
  setActiveAgent: (agent) => set({ activeAgent: agent }),
  setContext: (initiativeId, phase = null) =>
    set({ contextInitiativeId: initiativeId, contextPhase: phase }),
  clearMessages: () => set({ messages: [] }),
}));
