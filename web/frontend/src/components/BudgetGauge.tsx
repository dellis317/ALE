interface BudgetGaugeProps {
  percentUsed: number;
  currentCost: number;
  monthlyLimit: number;
}

/**
 * Circular SVG gauge showing budget usage percentage.
 * Color transitions: green (<60%), amber (60-80%), red (>80%).
 */
export default function BudgetGauge({ percentUsed, currentCost, monthlyLimit }: BudgetGaugeProps) {
  const clampedPercent = Math.min(Math.max(percentUsed, 0), 100);

  // SVG arc parameters
  const size = 160;
  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (clampedPercent / 100) * circumference;

  // Color based on percentage
  let strokeColor = '#10b981'; // emerald-500
  let bgRingColor = '#d1fae5'; // emerald-100
  let textColor = 'text-emerald-600';

  if (clampedPercent >= 80) {
    strokeColor = '#ef4444'; // red-500
    bgRingColor = '#fee2e2'; // red-100
    textColor = 'text-red-600';
  } else if (clampedPercent >= 60) {
    strokeColor = '#f59e0b'; // amber-500
    bgRingColor = '#fef3c7'; // amber-100
    textColor = 'text-amber-600';
  }

  const formatCost = (value: number) => `$${value.toFixed(2)}`;

  return (
    <div className="flex flex-col items-center">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="transform -rotate-90"
        aria-label={`Budget usage: ${clampedPercent.toFixed(0)}%`}
      >
        {/* Background ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={bgRingColor}
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      {/* Center text overlay */}
      <div
        className="absolute flex flex-col items-center justify-center"
        style={{ width: size, height: size }}
      >
        <span className={`text-2xl font-bold ${textColor}`}>
          {clampedPercent.toFixed(0)}%
        </span>
        <span className="text-xs text-gray-500">used</span>
      </div>
      {/* Cost summary below */}
      <div className="mt-3 text-center">
        <p className="text-sm text-gray-600">
          <span className="font-semibold">{formatCost(currentCost)}</span>
          {' / '}
          <span className="text-gray-400">{formatCost(monthlyLimit)}</span>
        </p>
      </div>
    </div>
  );
}
