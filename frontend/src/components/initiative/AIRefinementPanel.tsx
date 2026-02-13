import { useState } from 'react';
import { Bot, Send, ChevronDown, ChevronUp, Sparkles, Check } from 'lucide-react';
import { api } from '@/api/client';
import { initiativesApi } from '@/api/initiatives';
import type { InitiativeOut } from '@/types/api';

interface RefineResponse {
  content: string;
  suggestions: string[];
  metadata: Record<string, unknown>;
  conversation_history: { role: string; content: string }[];
}

interface Props {
  initiative: InitiativeOut;
  onUpdated?: (updated: InitiativeOut) => void;
}

export function AIRefinementPanel({ initiative, onUpdated }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [conversationHistory, setConversationHistory] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const callRefine = async (userMessage: string) => {
    setLoading(true);
    setError('');
    try {
      const resp = await api.post<RefineResponse>(`/api/initiatives/${initiative.id}/refine`, {
        message: userMessage,
        conversation_history: conversationHistory,
      });

      // Add messages to the chat
      const newMessages = [...messages];
      if (userMessage) {
        newMessages.push({ role: 'user', content: userMessage });
      }
      newMessages.push({ role: 'assistant', content: resp.content });

      setMessages(newMessages);
      setConversationHistory(resp.conversation_history);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI refinement failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = () => {
    setExpanded(true);
    if (messages.length === 0) {
      callRefine('');
    }
  };

  const handleSend = () => {
    if (!input.trim() || loading) return;
    const msg = input.trim();
    setInput('');
    callRefine(msg);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const applyField = async (field: string, value: string) => {
    try {
      const updated = await initiativesApi.update(initiative.id, { [field]: value });
      onUpdated?.(updated);
    } catch {
      // silent fail — user can manually update
    }
  };

  if (!expanded) {
    return (
      <button onClick={handleStart}
        className="w-full card p-4 text-left hover:border-teal-500/30 transition-colors cursor-pointer group">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-teal-500/10 group-hover:bg-teal-500/20 transition-colors">
            <Sparkles size={16} className="text-teal-400" />
          </div>
          <div>
            <span className="text-sm font-semibold text-teal-400">Strengthen with AI</span>
            <p className="text-xs text-gray-400">Get AI-powered suggestions to improve your business case</p>
          </div>
          <ChevronDown size={16} className="text-surface-muted ml-auto" />
        </div>
      </button>
    );
  }

  return (
    <div className="card border-teal-500/20">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <Bot size={16} className="text-teal-400" />
          <span className="text-sm font-semibold text-teal-400">AI Refinement</span>
        </div>
        <button onClick={() => setExpanded(false)} className="p-1 rounded-md text-surface-muted hover:text-gray-100 hover:bg-surface-hover transition-colors">
          <ChevronUp size={16} />
        </button>
      </div>

      {/* Messages */}
      <div className="px-5 py-4 max-h-96 overflow-y-auto space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
              msg.role === 'user'
                ? 'bg-brand-500/20 text-gray-200'
                : 'bg-surface-bg text-gray-300'
            }`}>
              <div className="whitespace-pre-wrap">{msg.content}</div>

              {/* Suggestion buttons for AI messages */}
              {msg.role === 'assistant' && i === messages.length - 1 && (
                <SuggestionButtons content={msg.content} initiative={initiative} onApply={applyField} />
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-bg rounded-lg px-3 py-2">
              <div className="flex items-center gap-2 text-sm text-surface-muted">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
                  <div className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse [animation-delay:0.2s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse [animation-delay:0.4s]" />
                </div>
                Thinking...
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="px-3 py-2 rounded-md bg-red-500/10 border border-red-500/30 text-sm text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-5 py-3 border-t border-surface-border">
        <div className="flex items-center gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="input-field flex-1 h-10 resize-none py-2"
            placeholder="Answer questions or ask for suggestions..."
            disabled={loading}
          />
          <button onClick={handleSend} disabled={!input.trim() || loading}
            className="btn-primary btn-sm shrink-0">
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---- Suggestion Buttons ---- */

function SuggestionButtons({
  content,
  initiative,
  onApply,
}: {
  content: string;
  initiative: InitiativeOut;
  onApply: (field: string, value: string) => void;
}) {
  const [applied, setApplied] = useState<Set<string>>(new Set());

  // Simple heuristic: if the AI mentions specific field suggestions, offer quick-apply buttons
  const suggestions: { field: string; label: string; match: RegExp }[] = [
    { field: 'scope', label: 'Apply Scope Suggestion', match: /(?:scope|in.scope|out.of.scope)[:\s]*["']?([^"'\n]{20,})["']?/i },
    { field: 'business_case', label: 'Apply Business Case', match: /(?:business.case|business.impact)[:\s]*["']?([^"'\n]{20,})["']?/i },
  ];

  const applicableSuggestions = suggestions.filter((s) => {
    const match = content.match(s.match);
    // Only suggest if the field is currently empty on the initiative
    return match && !initiative[s.field as keyof InitiativeOut];
  });

  if (applicableSuggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-surface-border/50">
      {applicableSuggestions.map((s) => {
        const match = content.match(s.match);
        if (!match?.[1]) return null;
        const value = match[1].trim();
        const isApplied = applied.has(s.field);

        return (
          <button key={s.field}
            onClick={() => { onApply(s.field, value); setApplied(new Set([...applied, s.field])); }}
            disabled={isApplied}
            className={`text-[10px] px-2 py-1 rounded-full border transition-colors ${
              isApplied
                ? 'border-green-500/30 text-green-400 bg-green-500/10'
                : 'border-teal-500/30 text-teal-400 bg-teal-500/10 hover:bg-teal-500/20 cursor-pointer'
            }`}>
            {isApplied ? <Check size={10} className="inline mr-1" /> : null}
            {isApplied ? 'Applied' : s.label}
          </button>
        );
      })}
    </div>
  );
}
