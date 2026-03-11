/**
 * HypothesesPanel - displays active hypotheses with actions
 */

import { useState } from 'react';
import type { Hypothesis } from '../../types/contextPayload';
import { HypothesisCard } from './HypothesisCard';
import { PackSelector } from './PackSelector';
import { useStore } from '../../store';

interface HypothesesPanelProps {
  ticketId: string;
  hypotheses: Hypothesis[];
  sourcePack: string[];
  currentBestGuess: string;
}

export function HypothesesPanel({
  ticketId,
  hypotheses,
  sourcePack,
  currentBestGuess,
}: HypothesesPanelProps) {
  const [showPackSelector, setShowPackSelector] = useState(false);
  const hypothesisAssessments = useStore((s) => s.hypothesisAssessments);

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
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
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          Hypotheses
          {sourcePack.length > 0 && (
            <span className="text-xs font-normal text-slate-500 ml-2">
              from: {sourcePack.join(', ')}
            </span>
          )}
        </h2>

        <button
          onClick={() => setShowPackSelector(!showPackSelector)}
          className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400"
        >
          {showPackSelector ? 'Cancel' : 'Load Pack'}
        </button>
      </div>

      {/* Pack selector */}
      {showPackSelector && (
        <div className="mb-4">
          <PackSelector
            ticketId={ticketId}
            onSelect={() => setShowPackSelector(false)}
          />
        </div>
      )}

      {/* Hypotheses list */}
      {hypotheses.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-4">
          No active hypotheses. Load a branch pack to start.
        </p>
      ) : (
        <div className="space-y-3">
          {hypotheses.map((hypothesis, index) => (
            <HypothesisCard
              key={hypothesis.id}
              hypothesis={hypothesis}
              index={index + 1}
              isBestGuess={hypothesis.id === currentBestGuess}
              claudeAssessment={hypothesisAssessments[hypothesis.id]}
            />
          ))}
        </div>
      )}
    </div>
  );
}
