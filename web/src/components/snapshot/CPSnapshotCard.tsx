/**
 * CPSnapshotCard - displays ticket/context summary
 */

import type { ContextPayload } from '../../types/contextPayload';

interface CPSnapshotCardProps {
  cp: ContextPayload;
}

export function CPSnapshotCard({ cp }: CPSnapshotCardProps) {
  const { ticket, problem, evidence, branches } = cp;

  const formatWorkStopped = (value: boolean | null) => {
    if (value === true) return 'Yes';
    if (value === false) return 'No';
    return 'Unknown';
  };

  const formatScope = () => {
    const parts = [];
    if (problem.scope.single_user) parts.push('single user');
    if (problem.scope.single_device) parts.push('single device');
    if (problem.scope.multi_user) parts.push('multi-user');
    if (problem.scope.service_wide) parts.push('service-wide');
    return parts.join(', ') || 'Unknown';
  };

  return (
    <div className="card p-4">
      <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4 flex items-center gap-2">
        <svg
          className="w-4 h-4 text-primary-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        CP Snapshot
      </h2>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        {/* Location */}
        <div>
          <dt className="text-slate-500 dark:text-slate-500">Location</dt>
          <dd className="text-slate-700 dark:text-slate-300">
            {ticket.company}
            {ticket.site && ` / ${ticket.site}`}
          </dd>
        </div>

        {/* Requester */}
        <div>
          <dt className="text-slate-500 dark:text-slate-500">Requester</dt>
          <dd className="text-slate-700 dark:text-slate-300">
            {ticket.requester.name || 'Unknown'}
          </dd>
        </div>

        {/* Issue Summary */}
        <div className="col-span-2">
          <dt className="text-slate-500 dark:text-slate-500">Issue</dt>
          <dd className="text-slate-700 dark:text-slate-300">
            {ticket.summary || 'No summary'}
          </dd>
        </div>

        {/* Symptoms */}
        {problem.symptoms.length > 0 && (
          <div className="col-span-2">
            <dt className="text-slate-500 dark:text-slate-500">Symptoms</dt>
            <dd className="text-slate-700 dark:text-slate-300">
              {problem.symptoms.join(', ')}
            </dd>
          </div>
        )}

        {/* Work Stopped */}
        <div>
          <dt className="text-slate-500 dark:text-slate-500">Work stopped</dt>
          <dd
            className={`font-medium ${
              problem.impact.work_stopped === true
                ? 'text-red-600'
                : 'text-slate-700 dark:text-slate-300'
            }`}
          >
            {formatWorkStopped(problem.impact.work_stopped)}
          </dd>
        </div>

        {/* Scope */}
        <div>
          <dt className="text-slate-500 dark:text-slate-500">Scope</dt>
          <dd className="text-slate-700 dark:text-slate-300">{formatScope()}</dd>
        </div>

        {/* Tests Run */}
        <div>
          <dt className="text-slate-500 dark:text-slate-500">Tests run</dt>
          <dd className="text-slate-700 dark:text-slate-300">
            {evidence.tests_run.length}
          </dd>
        </div>

        {/* Best Guess */}
        <div>
          <dt className="text-slate-500 dark:text-slate-500">Best guess</dt>
          <dd className="text-slate-700 dark:text-slate-300">
            {branches.current_best_guess || 'None'}
          </dd>
        </div>
      </dl>
    </div>
  );
}
