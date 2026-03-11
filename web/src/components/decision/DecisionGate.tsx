/**
 * DecisionGate component - shows decision status and DECIDE button
 */

import { useState } from 'react';
import { useDecide } from '../../hooks/useTickets';
import type { DecisionStatus } from '../../types/contextPayload';

interface DecisionGateProps {
  ticketId: string;
  status: DecisionStatus;
  cssScore: number;
  cssTarget: number;
  bestGuess: string;
  reasoning?: string[];
}

export function DecisionGate({
  ticketId,
  status,
  cssScore,
  cssTarget,
  bestGuess,
  reasoning,
}: DecisionGateProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const decideMutation = useDecide(ticketId);
  const canDecide = cssScore >= cssTarget;
  const isDecided = ['resolved', 'escalated_time', 'escalated_skill', 'decide'].includes(status);

  const getStatusBadge = () => {
    switch (status) {
      case 'resolved':
        return { text: 'Resolved', className: 'bg-green-100 text-green-700' };
      case 'escalated_time':
        return { text: 'Escalated (Time)', className: 'bg-amber-100 text-amber-700' };
      case 'escalated_skill':
        return { text: 'Escalated (Skill)', className: 'bg-amber-100 text-amber-700' };
      case 'decide':
        return { text: 'Decision Made', className: 'bg-blue-100 text-blue-700' };
      case 'converging':
        return { text: 'Converging', className: 'bg-purple-100 text-purple-700' };
      case 'testing':
        return { text: 'Testing', className: 'bg-cyan-100 text-cyan-700' };
      default:
        return { text: 'Triage', className: 'bg-slate-100 text-slate-700' };
    }
  };

  const statusBadge = getStatusBadge();

  const handleDecide = async () => {
    try {
      await decideMutation.mutateAsync({});
      setShowConfirm(false);
    } catch (error) {
      console.error('Decision failed:', error);
    }
  };

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
        Decision Gate
      </h3>

      {/* Status badge */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-slate-500">Status:</span>
        <span
          className={`px-2 py-0.5 text-xs font-medium rounded ${statusBadge.className}`}
        >
          {statusBadge.text}
        </span>
      </div>

      {/* Best guess */}
      {bestGuess && (
        <div className="mb-4">
          <span className="text-xs text-slate-500">Best Guess:</span>
          <p className="text-sm text-slate-700 dark:text-slate-300 mt-1">
            {bestGuess}
          </p>
        </div>
      )}

      {/* Reasoning list */}
      {reasoning && reasoning.length > 0 && (
        <div className="mb-4">
          <span className="text-xs text-slate-500">Reasoning:</span>
          <ol className="mt-1 space-y-1 list-decimal list-inside">
            {reasoning.map((r, i) => (
              <li key={i} className="text-xs text-slate-600 dark:text-slate-400">
                {r}
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Decision button or confirmation */}
      {!isDecided && (
        <>
          {showConfirm ? (
            <div className="space-y-2">
              <p className="text-xs text-slate-600 dark:text-slate-400">
                {canDecide
                  ? 'Ready to commit to diagnosis?'
                  : `CSS is ${cssScore}/${cssTarget}. Decision may be premature.`}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleDecide}
                  disabled={decideMutation.isPending}
                  className={`flex-1 btn ${
                    canDecide ? 'btn-primary' : 'bg-amber-500 text-white hover:bg-amber-600'
                  }`}
                >
                  {decideMutation.isPending ? 'Deciding...' : 'Confirm'}
                </button>
                <button
                  onClick={() => setShowConfirm(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowConfirm(true)}
              disabled={!canDecide && cssScore < 50}
              className={`w-full btn ${
                canDecide
                  ? 'btn-primary'
                  : 'bg-slate-300 text-slate-600 cursor-not-allowed dark:bg-slate-700 dark:text-slate-400'
              }`}
            >
              {canDecide ? 'DECIDE' : `CSS ${cssScore}/${cssTarget}`}
            </button>
          )}
        </>
      )}

      {/* Show decision result */}
      {decideMutation.data?.warning && (
        <p className="mt-2 text-xs text-amber-600">{decideMutation.data.warning}</p>
      )}
    </div>
  );
}
