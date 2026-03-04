/**
 * Header component - displays ticket info, priority, and session timer
 */

import { useStore } from '../../store';

interface HeaderProps {
  className?: string;
}

export function Header({ className = '' }: HeaderProps) {
  const { contextPayload, isConnected } = useStore();
  const ticket = contextPayload?.ticket;
  const hostname = contextPayload?.environment?.target_device?.hostname || 'No device';

  const getPriorityBadgeClass = (priority: string) => {
    switch (priority?.toUpperCase()) {
      case 'P1':
      case 'HIGH':
        return 'priority-p1';
      case 'P2':
      case 'MEDIUM':
        return 'priority-p2';
      case 'P3':
      case 'LOW':
        return 'priority-p3';
      default:
        return 'priority-unknown';
    }
  };

  return (
    <header
      className={`flex items-center justify-between px-6 py-3 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Logo and title */}
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold uppercase tracking-wider" style={{ color: '#39ff14', textShadow: '0 0 10px #39ff14, 0 0 20px #39ff14' }}>
          QF_Wiz
        </h1>

        {ticket && (
          <>
            <span className="text-slate-400">|</span>
            <span className="font-mono text-sm text-slate-600 dark:text-slate-400">
              {ticket.id}
            </span>
          </>
        )}
      </div>

      {/* Ticket info */}
      {ticket && (
        <div className="flex items-center gap-4">
          {/* Priority badge */}
          <span
            className={`px-2 py-1 text-xs font-medium rounded ${getPriorityBadgeClass(
              ticket.priority
            )}`}
          >
            {ticket.priority}
          </span>

          {/* Hostname */}
          <span className="text-sm font-mono text-slate-600 dark:text-slate-400">
            {hostname}
          </span>

          {/* Company */}
          <span className="text-sm text-slate-500 dark:text-slate-500">
            {ticket.company}
          </span>

          {/* Connection status indicator */}
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor: isConnected ? '#39ff14' : '#606060',
                boxShadow: isConnected ? '0 0 8px #39ff14' : 'none',
              }}
              title={isConnected ? 'Connected' : 'Disconnected'}
            />
            <span className="text-xs" style={{ color: isConnected ? '#39ff14' : '#606060' }}>
              {isConnected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Theme toggle placeholder */}
        <button
          className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
          title="Toggle theme"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
            />
          </svg>
        </button>
      </div>
    </header>
  );
}
