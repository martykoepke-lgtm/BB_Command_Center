import { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, User, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import { useUIStore } from '@/stores/uiStore';
import { useAIStore, type ChatMessage } from '@/stores/aiStore';
import { aiApi } from '@/api/ai';

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  return (
    <div className={clsx('flex gap-2 mb-4', isUser && 'flex-row-reverse')}>
      <div
        className={clsx(
          'w-7 h-7 rounded-full flex items-center justify-center shrink-0',
          isUser ? 'bg-brand-500' : 'bg-teal-600',
        )}
      >
        {isUser ? <User size={14} className="text-white" /> : <Bot size={14} className="text-white" />}
      </div>
      <div
        className={clsx(
          'max-w-[80%] px-3 py-2 rounded-lg text-sm',
          isUser
            ? 'bg-brand-500/20 text-gray-100'
            : 'bg-surface-hover text-gray-200',
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.agent && (
          <span className="block mt-1 text-[10px] text-surface-muted font-mono">{message.agent}</span>
        )}
      </div>
    </div>
  );
}

export function AIPanel() {
  const { aiPanelOpen, setAIPanelOpen } = useUIStore();
  const { messages, isStreaming, addMessage, setStreaming } = useAIStore();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    setInput('');
    addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    });

    setStreaming(true);
    try {
      const response = await aiApi.chat(text, {
        initiative_id: useAIStore.getState().contextInitiativeId ?? undefined,
        phase: useAIStore.getState().contextPhase ?? undefined,
      });

      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        agent: response.agent,
      });
    } catch {
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      });
    } finally {
      setStreaming(false);
    }
  };

  if (!aiPanelOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-screen w-96 bg-surface-card border-l border-surface-border flex flex-col z-40 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between h-14 px-4 border-b border-surface-border shrink-0">
        <div className="flex items-center gap-2">
          <Bot size={18} className="text-teal-400" />
          <span className="text-sm font-semibold text-gray-100">AI Assistant</span>
        </div>
        <button
          onClick={() => setAIPanelOpen(false)}
          className="p-1 rounded-md text-surface-muted hover:text-gray-100 hover:bg-surface-hover"
        >
          <X size={18} />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="text-center text-surface-muted text-sm mt-8">
            <Bot size={32} className="mx-auto mb-3 text-teal-400/50" />
            <p>Ask me anything about your initiatives, data analysis, or methodology.</p>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}
        {isStreaming && (
          <div className="flex items-center gap-2 text-sm text-surface-muted">
            <Loader2 size={14} className="animate-spin" />
            Thinking...
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-surface-border">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask the AI assistant..."
            className="input-field text-sm"
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="btn-primary btn-sm shrink-0"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
