/**
 * HypothesisCard - displays a single hypothesis with tests and actions
 */

import { useState } from 'react';
import type { Hypothesis } from '../../types/contextPayload';

interface HypothesisCardProps {
  hypothesis: Hypothesis;
  index: number;
  isBestGuess: boolean;
  claudeAssessment?: 'confirmed' | 'falsified' | 'unchanged';
}

export function HypothesisCard({
  hypothesis,
  index,
  isBestGuess,
  claudeAssessment,
}: HypothesisCardProps) {
  const [expanded, setExpanded] = useState(false);

  const confidencePercent = Math.round(hypothesis.confidence_hint * 100);

  const getConfidenceColor = () => {
    if (confidencePercent >= 70) return 'text-green-600 dark:text-green-400';
    if (confidencePercent >= 40) return 'text-amber-600 dark:text-amber-400';
    return 'text-slate-500';
  };

  return (
    <div
      className={`border rounded-lg p-3 ${
        isBestGuess
          ? 'border-primary-300 bg-primary-50 dark:border-primary-700 dark:bg-primary-900/20'
          : 'border-slate-200 dark:border-slate-700'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <span className="text-xs font-medium text-slate-400 dark:text-slate-500 mt-0.5">
            {index}.
          </span>
          <div>
            <p className="text-sm text-slate-700 dark:text-slate-300">
              {hypothesis.hypothesis}
            </p>
            <div className="flex flex-wrap gap-1 mt-1">
              {isBestGuess && (
                <span className="text-xs bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300 px-1.5 py-0.5 rounded">
                  Best Guess
                </span>
              )}
              {claudeAssessment === 'confirmed' && (
                <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300 px-1.5 py-0.5 rounded">
                  Claude: confirmed
                </span>
              )}
              {claudeAssessment === 'falsified' && (
                <span className="text-xs bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 px-1.5 py-0.5 rounded">
                  Claude: falsified
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Confidence */}
        <span
          className={`text-xs font-mono flex-shrink-0 ${getConfidenceColor()}`}
        >
          [{confidencePercent}%]
        </span>
      </div>

      {/* Discriminating question */}
      {hypothesis.discriminating_question && (
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 italic">
          Q: {hypothesis.discriminating_question}
        </p>
      )}

      {/* Expand/collapse tests */}
      {hypothesis.discriminating_tests.length > 0 && (
        <div className="mt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400"
          >
            <svg
              className={`w-3 h-3 transition-transform ${
                expanded ? 'rotate-90' : ''
              }`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                clipRule="evenodd"
              />
            </svg>
            {hypothesis.discriminating_tests.length} test
            {hypothesis.discriminating_tests.length !== 1 ? 's' : ''}
          </button>

          {expanded && (
            <ul className="mt-2 space-y-1 pl-4 border-l-2 border-slate-200 dark:border-slate-700">
              {hypothesis.discriminating_tests.map((test, i) => (
                <li
                  key={i}
                  className="text-xs text-slate-600 dark:text-slate-400 font-mono"
                >
                  {test}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
