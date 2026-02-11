interface ScoreBarProps {
  score: number;
  label: string;
  size?: 'sm' | 'md';
}

function getScoreColor(score: number): string {
  if (score < 0.3) return 'bg-red-500';
  if (score <= 0.6) return 'bg-amber-500';
  return 'bg-emerald-500';
}

function getScoreTrack(score: number): string {
  if (score < 0.3) return 'bg-red-100';
  if (score <= 0.6) return 'bg-amber-100';
  return 'bg-emerald-100';
}

export default function ScoreBar({ score, label, size = 'md' }: ScoreBarProps) {
  const percentage = Math.round(score * 100);
  const barHeight = size === 'sm' ? 'h-1.5' : 'h-2.5';

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        <span className={`font-medium text-gray-700 ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
          {label}
        </span>
        <span className={`font-semibold text-gray-900 ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
          {percentage}%
        </span>
      </div>
      <div className={`w-full ${barHeight} rounded-full ${getScoreTrack(score)}`}>
        <div
          className={`${barHeight} rounded-full ${getScoreColor(score)} transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
