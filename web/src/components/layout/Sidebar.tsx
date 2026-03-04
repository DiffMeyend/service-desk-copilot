/**
 * Sidebar component - displays ticket list for navigation
 */

import { useTickets } from '../../hooks/useTickets';
import { useStore } from '../../store';
import type { TicketSummary } from '../../types/contextPayload';

interface SidebarProps {
  className?: string;
}

function TicketItem({
  ticket,
  isActive,
  onClick,
}: {
  ticket: TicketSummary;
  isActive: boolean;
  onClick: () => void;
}) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'resolved':
        return 'bg-green-500';
      case 'escalated_time':
      case 'escalated_skill':
        return 'bg-amber-500';
      case 'decide':
        return 'bg-blue-500';
      default:
        return 'bg-slate-400';
    }
  };

  const getCSSScoreClass = (score: number) => {
    if (score >= 90) return 'css-score-high';
    if (score >= 70) return 'css-score-medium';
    return 'css-score-low';
  };

  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg transition-colors ${
        isActive
          ? 'bg-primary-100 dark:bg-primary-900/30 border-l-4 border-primary-500'
          : 'hover:bg-slate-100 dark:hover:bg-slate-700'
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-mono text-sm font-medium text-slate-900 dark:text-slate-100">
          {ticket.id}
        </span>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${getStatusColor(ticket.status)}`}
            title={ticket.status}
          />
          <span
            className={`px-1.5 py-0.5 text-xs font-medium rounded ${getCSSScoreClass(
              ticket.css_score
            )}`}
          >
            {ticket.css_score}
          </span>
        </div>
      </div>

      <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
        {ticket.hostname || 'No hostname'}
      </p>

      <p className="text-xs text-slate-600 dark:text-slate-300 truncate mt-1">
        {ticket.summary}
      </p>
    </button>
  );
}

export function Sidebar({ className = '' }: SidebarProps) {
  const { data: tickets, isLoading, error } = useTickets();
  const { activeTicketId, setActiveTicket } = useStore();

  return (
    <aside
      className={`flex flex-col bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
          Tickets
        </h2>
      </div>

      {/* Ticket list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoading && (
          <div className="flex items-center justify-center p-4 text-slate-500">
            <svg
              className="w-5 h-5 animate-spin mr-2"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Loading...
          </div>
        )}

        {error && (
          <div className="p-4 text-red-500 text-sm">
            Failed to load tickets
          </div>
        )}

        {tickets?.length === 0 && !isLoading && (
          <div className="p-4 text-slate-500 text-sm text-center">
            No tickets found
          </div>
        )}

        {tickets?.map((ticket) => (
          <TicketItem
            key={ticket.id}
            ticket={ticket}
            isActive={ticket.id === activeTicketId}
            onClick={() => setActiveTicket(ticket.id)}
          />
        ))}
      </div>
    </aside>
  );
}
