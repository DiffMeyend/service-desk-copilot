/**
 * MainWorkArea component - contains CP snapshot, hypotheses, log form, evidence
 */

import { useStore } from '../store';
import { CPSnapshotCard } from './snapshot/CPSnapshotCard';
import { HypothesesPanel } from './hypotheses/HypothesesPanel';
import { LogResultForm } from './evidence/LogResultForm';
import { EvidenceLog } from './evidence/EvidenceLog';
import { NextActionPanel } from './NextActionPanel';

interface MainWorkAreaProps {
  className?: string;
}

export function MainWorkArea({ className = '' }: MainWorkAreaProps) {
  const { contextPayload, activeTicketId, evidenceInterpretations, pendingCommandId } = useStore();

  if (!activeTicketId) {
    return (
      <main
        className={`flex items-center justify-center bg-slate-100 dark:bg-slate-800 ${className}`}
      >
        <div className="text-center">
          <h2 className="text-xl font-semibold text-slate-600 dark:text-slate-400 mb-2">
            Welcome to QF_Wiz
          </h2>
          <p className="text-slate-500">
            Select a ticket from the sidebar to begin troubleshooting
          </p>
        </div>
      </main>
    );
  }

  if (!contextPayload) {
    return (
      <main
        className={`flex items-center justify-center bg-slate-100 dark:bg-slate-800 ${className}`}
      >
        <div className="flex items-center gap-2 text-slate-500">
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
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
          Loading ticket...
        </div>
      </main>
    );
  }

  return (
    <main
      className={`overflow-y-auto bg-slate-100 dark:bg-slate-800 p-6 space-y-6 ${className}`}
    >
      {/* Next Action Panel */}
      <NextActionPanel />

      {/* CP Snapshot Card */}
      <CPSnapshotCard cp={contextPayload} />

      {/* Hypotheses Panel */}
      <HypothesesPanel
        ticketId={activeTicketId}
        hypotheses={contextPayload.branches.active_hypotheses}
        sourcePack={contextPayload.branches.source_pack}
        currentBestGuess={contextPayload.branches.current_best_guess}
      />

      {/* Log Result Form */}
      <LogResultForm
        ticketId={activeTicketId}
        hypotheses={contextPayload.branches.active_hypotheses}
        prefillCommandId={pendingCommandId ?? undefined}
      />

      {/* Evidence Log */}
      <EvidenceLog
        evidence={contextPayload.evidence}
        interpretations={evidenceInterpretations}
      />
    </main>
  );
}
