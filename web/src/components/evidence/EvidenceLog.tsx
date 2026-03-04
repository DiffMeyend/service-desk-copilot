/**
 * EvidenceLog - displays logged test results
 */

import { useState } from 'react';
import type { Evidence, TestResult } from '../../types/contextPayload';

interface EvidenceLogProps {
  evidence: Evidence;
}

function EvidenceItem({ result }: { result: TestResult }) {
  const [expanded, setExpanded] = useState(false);

  const formatTime = (timestamp: string) => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return timestamp;
    }
  };

  const truncatedOutput =
    result.output.length > 100
      ? result.output.substring(0, 100) + '...'
      : result.output;

  return (
    <div className="border-l-2 border-slate-300 dark:border-slate-600 pl-3 py-1">
      <div className="flex items-center justify-between">
        <span className="text-sm font-mono font-medium text-slate-700 dark:text-slate-300">
          {result.command_id}
        </span>
        <span className="text-xs text-slate-400">
          {formatTime(result.captured_at)}
        </span>
      </div>

      <div className="mt-1">
        {result.output.length > 100 ? (
          <>
            <p className="text-xs text-slate-600 dark:text-slate-400 font-mono whitespace-pre-wrap">
              {expanded ? result.output : truncatedOutput}
            </p>
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400 mt-1"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          </>
        ) : (
          <p className="text-xs text-slate-600 dark:text-slate-400 font-mono whitespace-pre-wrap">
            {result.output}
          </p>
        )}
      </div>
    </div>
  );
}

export function EvidenceLog({ evidence }: EvidenceLogProps) {
  const { results, tests_run, observations } = evidence;

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
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        Evidence Log
        <span className="text-xs font-normal text-slate-500">
          ({tests_run.length} tests)
        </span>
      </h2>

      {results.length === 0 && observations.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-4">
          No evidence logged yet. Run tests and log results to build your case.
        </p>
      ) : (
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {/* Test results */}
          {results.map((result, index) => (
            <EvidenceItem key={`${result.command_id}-${index}`} result={result} />
          ))}

          {/* Observations */}
          {observations.length > 0 && (
            <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
              <h3 className="text-xs font-medium text-slate-500 mb-2">
                Observations
              </h3>
              <ul className="space-y-1">
                {observations.map((obs, index) => (
                  <li
                    key={index}
                    className="text-xs text-slate-600 dark:text-slate-400"
                  >
                    • {obs}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
