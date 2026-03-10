/**
 * RightPanel component - displays CSS gauge, domain scores, blockers, guardrails, decision gate
 */

import { useStore } from '../../store';
import { AIInsightsPanel } from '../AIInsightsPanel';
import { CSSGauge } from '../css/CSSGauge';
import { DomainScores } from '../css/DomainScores';
import { BlockersList } from '../css/BlockersList';
import { GuardrailsChecklist } from '../guardrails/GuardrailsChecklist';
import { DecisionGate } from '../decision/DecisionGate';

interface RightPanelProps {
  className?: string;
  triage?: { routing_suggestion?: string; triage_reasoning?: string } | null;
}

export function RightPanel({ className = '', triage }: RightPanelProps) {
  const { contextPayload, activeTicketId } = useStore();

  if (!activeTicketId || !contextPayload) {
    return (
      <aside
        className={`flex items-center justify-center bg-slate-50 dark:bg-slate-900 ${className}`}
      >
        <p className="text-slate-500 text-sm">Select a ticket to view details</p>
      </aside>
    );
  }

  const { css, guardrails, decision } = contextPayload;

  return (
    <aside
      className={`flex flex-col bg-slate-50 dark:bg-slate-900 overflow-y-auto ${className}`}
    >
      {/* CSS Gauge */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <CSSGauge score={css.score} target={css.target} />
      </div>

      {/* Domain Scores */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
          Domain Scores
        </h3>
        <DomainScores domainScores={css.domain_scores} />
      </div>

      {/* Blockers */}
      {css.missing_fields && css.missing_fields.length > 0 && (
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
            Blockers
          </h3>
          <BlockersList blockers={css.missing_fields} />
        </div>
      )}

      {/* Guardrails Checklist */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
          Guardrails
        </h3>
        <GuardrailsChecklist checks={guardrails.basic_troubleshooting} />
      </div>

      {/* Decision Gate */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-700">
        <DecisionGate
          ticketId={activeTicketId}
          status={decision.status}
          cssScore={css.score}
          cssTarget={css.target}
          bestGuess={contextPayload.branches.current_best_guess}
        />
      </div>

      {/* AI Insights Panel */}
      <div className="p-4">
        <AIInsightsPanel ticketId={activeTicketId} triage={triage} />
      </div>
    </aside>
  );
}
