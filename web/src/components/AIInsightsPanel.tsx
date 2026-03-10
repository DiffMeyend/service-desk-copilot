/**
 * AIInsightsPanel — surfaces Claude output in the right panel.
 *
 * Slots:
 *  - Triage banner (routing suggestion + reasoning on ticket load)
 *  - Chat input + response thread
 */

import { useState, useRef, useEffect } from 'react';
import { useChatMutation } from '../hooks/useTickets';
import type { TriageInfo, ChatResponse } from '../types/contextPayload';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  suggestedCommands?: string[];
}

interface AIInsightsPanelProps {
  ticketId: string;
  triage?: TriageInfo | null;
}

export function AIInsightsPanel({ ticketId, triage }: AIInsightsPanelProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const chatMutation = useChatMutation(ticketId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || chatMutation.isPending) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');

    chatMutation.mutate(
      { message: text },
      {
        onSuccess: (data: ChatResponse) => {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: data.response,
              suggestedCommands: data.suggested_commands,
            },
          ]);
        },
        onError: () => {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: 'Chat failed — check API connection.',
            },
          ]);
        },
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasTriage =
    triage && (triage.routing_suggestion || triage.triage_reasoning);

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
        <svg
          className="w-4 h-4 text-violet-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>
        Claude AI
      </h3>

      {/* Triage suggestion banner */}
      {hasTriage && (
        <div className="rounded-lg bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-700 p-3 text-xs space-y-1">
          {triage.routing_suggestion && (
            <p className="font-medium text-violet-700 dark:text-violet-300">
              Suggested routing:{' '}
              <span className="font-mono">{triage.routing_suggestion}</span>
            </p>
          )}
          {triage.triage_reasoning && (
            <p className="text-slate-600 dark:text-slate-400 leading-relaxed">
              {triage.triage_reasoning}
            </p>
          )}
        </div>
      )}

      {/* Chat thread */}
      {messages.length > 0 && (
        <div className="max-h-48 overflow-y-auto space-y-2 text-xs">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`rounded-lg p-2 ${
                msg.role === 'user'
                  ? 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 ml-4'
                  : 'bg-violet-50 dark:bg-violet-900/20 text-slate-700 dark:text-slate-300 mr-4'
              }`}
            >
              <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.suggestedCommands && msg.suggestedCommands.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {msg.suggestedCommands.map((cmd) => (
                    <span
                      key={cmd}
                      className="font-mono bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-1 rounded"
                    >
                      {cmd}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2 items-end">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Claude about this ticket..."
          rows={2}
          className="flex-1 text-xs rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-violet-500"
          disabled={chatMutation.isPending}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || chatMutation.isPending}
          className="flex-shrink-0 rounded-lg bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-3 py-2 text-xs font-medium transition-colors"
        >
          {chatMutation.isPending ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
}
