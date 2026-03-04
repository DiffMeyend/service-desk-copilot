/**
 * GuardrailsChecklist component - displays basic troubleshooting checklist
 */

import type { GuardrailChecks } from '../../types/contextPayload';

interface GuardrailsChecklistProps {
  checks: GuardrailChecks;
}

interface CheckItem {
  key: keyof GuardrailChecks;
  label: string;
}

const CHECK_ITEMS: CheckItem[] = [
  { key: 'scope_confirmed', label: 'Scope confirmed' },
  { key: 'error_message_confirmed', label: 'Error text captured' },
  { key: 'repro_confirmed', label: 'Repro steps verified' },
  { key: 'connectivity_confirmed', label: 'Connectivity checked' },
  { key: 'authentication_confirmed', label: 'Auth verified' },
  { key: 'service_availability_confirmed', label: 'Service available' },
];

export function GuardrailsChecklist({ checks }: GuardrailsChecklistProps) {
  const completedCount = CHECK_ITEMS.filter(
    (item) => checks[item.key] === true
  ).length;
  const totalCount = CHECK_ITEMS.length;

  return (
    <div>
      {/* Progress indicator */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-slate-500">
          {completedCount}/{totalCount} complete
        </span>
        {checks.confirmed && (
          <span className="text-xs text-green-600 dark:text-green-400 font-medium">
            Verified
          </span>
        )}
      </div>

      {/* Checklist */}
      <ul className="space-y-1.5">
        {CHECK_ITEMS.map((item) => {
          const isChecked = checks[item.key] === true;
          return (
            <li key={item.key} className="flex items-center gap-2">
              <div
                className={`w-4 h-4 rounded flex items-center justify-center ${
                  isChecked
                    ? 'bg-green-500 text-white'
                    : 'border border-slate-300 dark:border-slate-600'
                }`}
              >
                {isChecked && (
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </div>
              <span
                className={`text-xs ${
                  isChecked
                    ? 'text-slate-600 dark:text-slate-400'
                    : 'text-slate-500 dark:text-slate-500'
                }`}
              >
                {item.label}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
