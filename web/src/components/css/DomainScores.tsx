/**
 * DomainScores component - displays CSS domain breakdown
 */

interface DomainScoresProps {
  domainScores: Record<string, number>;
}

const DOMAIN_INFO: Record<string, { label: string; maxScore: number }> = {
  evidence_strength: { label: 'Evidence', maxScore: 35 },
  branch_quality: { label: 'Branch', maxScore: 20 },
  symptom_specificity: { label: 'Symptom', maxScore: 15 },
  environment_specificity: { label: 'Environment', maxScore: 10 },
  timeline_changes: { label: 'Timeline', maxScore: 10 },
  constraints_risk: { label: 'Constraints', maxScore: 10 },
};

export function DomainScores({ domainScores }: DomainScoresProps) {
  const domains = Object.entries(DOMAIN_INFO);

  return (
    <div className="space-y-2">
      {domains.map(([key, { label, maxScore }]) => {
        const score = domainScores[key] ?? 0;
        const percentage = (score / maxScore) * 100;

        return (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-600 dark:text-slate-400">{label}</span>
              <span className="font-mono text-slate-500">
                {score}/{maxScore}
              </span>
            </div>
            <div className="h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 transition-all duration-300"
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
