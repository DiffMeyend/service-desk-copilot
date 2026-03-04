/**
 * CSSGauge component - circular progress visualization for CSS score
 */

import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface CSSGaugeProps {
  score: number;
  target: number;
}

export function CSSGauge({ score, target }: CSSGaugeProps) {
  const percentage = Math.min(100, Math.max(0, (score / target) * 100));

  const getColor = () => {
    if (score >= target) return '#39ff14'; // neon green
    if (score >= 70) return '#ffff00'; // neon yellow
    return '#ff3131'; // neon red
  };

  const getStatusText = () => {
    if (score >= target) return 'Ready to Decide';
    if (score >= 70) return 'Converging';
    return 'Gathering Evidence';
  };

  // Data for pie chart (filled vs empty)
  const data = [
    { name: 'score', value: percentage },
    { name: 'remaining', value: 100 - percentage },
  ];

  return (
    <div className="flex flex-col items-center">
      {/* Gauge */}
      <div className="relative w-32 h-32">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={55}
              startAngle={90}
              endAngle={-270}
              paddingAngle={0}
              dataKey="value"
            >
              <Cell fill={getColor()} />
              <Cell fill="#303030" /> {/* dark gray */}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-2xl font-bold"
            style={{ color: getColor() }}
          >
            {score}
          </span>
          <span className="text-xs text-slate-500">/ {target}</span>
        </div>
      </div>

      {/* Status text */}
      <p className="mt-2 text-sm font-medium text-slate-600 dark:text-slate-400">
        {getStatusText()}
      </p>
    </div>
  );
}
