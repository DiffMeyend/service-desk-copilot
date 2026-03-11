/**
 * NextActionPanel - surfaces Claude's next-action guidance above the snapshot card
 */

import { useStore } from '../store';
import { useNextAction } from '../hooks/useTickets';

const ACTION_BADGE: Record<string, { label: string; className: string }> = {
  run_test: { label: 'Run Test', className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  load_pack: { label: 'Load Pack', className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' },
  decide: { label: 'Decide', className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
  gather_evidence: { label: 'Gather Evidence', className: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300' },
};

export function NextActionPanel() {
  const { activeTicketId, setPendingCommandId } = useStore();
  const { data, isLoading } = useNextAction(activeTicketId);

  if (!activeTicketId) return null;

  if (isLoading) {
    return (
      <div className="card p-4 flex items-center gap-2 text-slate-400 text-xs">
        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        Loading next action...
      </div>
    );
  }

  if (!data || (data.action === 'unknown' && !data.suggestion)) return null;

  const badge = ACTION_BADGE[data.action];

  return (
    <div className="card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Next Action</h2>
        {badge && (
          <span className={`px-2 py-0.5 text-xs font-medium rounded ${badge.className}`}>
            {badge.label}
          </span>
        )}
      </div>

      {/* Suggestion */}
      {data.suggestion && (
        <div className="rounded-lg bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-700 p-3">
          <p className="text-sm text-slate-700 dark:text-slate-300">{data.suggestion}</p>
          {data.discriminating_test && (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 italic">
              Key test: {data.discriminating_test}
            </p>
          )}
        </div>
      )}

      {/* AI Reasoning — collapsible */}
      {data.ai_reasoning && (
        <details className="text-xs text-slate-600 dark:text-slate-400">
          <summary className="cursor-pointer select-none text-violet-600 dark:text-violet-400 hover:underline">
            Claude's reasoning
          </summary>
          <p className="mt-2 leading-relaxed whitespace-pre-wrap">{data.ai_reasoning}</p>
        </details>
      )}

      {/* Suggested command pills */}
      {data.ai_suggested_commands && data.ai_suggested_commands.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {data.ai_suggested_commands.map((cmd) => (
            <button
              key={cmd}
              onClick={() => setPendingCommandId(cmd)}
              className="font-mono text-xs bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-violet-100 dark:hover:bg-violet-900/30 hover:text-violet-700 dark:hover:text-violet-300 px-2 py-0.5 rounded transition-colors cursor-pointer"
            >
              {cmd}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
