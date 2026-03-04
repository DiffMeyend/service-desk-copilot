/**
 * BlockersList component - displays CSS blockers/missing items
 */

interface BlockersListProps {
  blockers: string[];
}

export function BlockersList({ blockers }: BlockersListProps) {
  if (blockers.length === 0) {
    return (
      <p className="text-sm text-green-600 dark:text-green-400">
        No blockers - all requirements met!
      </p>
    );
  }

  return (
    <ul className="space-y-1">
      {blockers.slice(0, 5).map((blocker, index) => (
        <li
          key={index}
          className="flex items-start gap-2 text-xs text-amber-700 dark:text-amber-400"
        >
          <svg
            className="w-4 h-4 flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span>{blocker}</span>
        </li>
      ))}
      {blockers.length > 5 && (
        <li className="text-xs text-slate-500 pl-6">
          +{blockers.length - 5} more...
        </li>
      )}
    </ul>
  );
}
