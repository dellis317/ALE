import { useMemo } from 'react';
import type { UsageRecord } from '../types';

interface UsageChartProps {
  records: UsageRecord[];
}

/**
 * Simple SVG bar chart showing daily token usage over the last 7 days.
 * No external chart library required.
 */
export default function UsageChart({ records }: UsageChartProps) {
  const dailyData = useMemo(() => {
    const now = new Date();
    const days: { label: string; date: string; tokens: number }[] = [];

    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().slice(0, 10);
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      days.push({
        label: dayNames[d.getDay()],
        date: dateStr,
        tokens: 0,
      });
    }

    for (const record of records) {
      const recordDate = record.timestamp.slice(0, 10);
      const day = days.find((d) => d.date === recordDate);
      if (day) {
        day.tokens += record.input_tokens + record.output_tokens;
      }
    }

    return days;
  }, [records]);

  const maxTokens = Math.max(...dailyData.map((d) => d.tokens), 1);

  const chartWidth = 420;
  const chartHeight = 180;
  const barWidth = 40;
  const gap = 16;
  const paddingTop = 20;
  const paddingBottom = 30;
  const usableHeight = chartHeight - paddingTop - paddingBottom;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Daily Token Usage (Last 7 Days)</h3>
      {maxTokens <= 1 && dailyData.every((d) => d.tokens === 0) ? (
        <div className="flex items-center justify-center h-[180px] text-gray-400 text-sm">
          No usage data for this period
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full"
          aria-label="Daily token usage bar chart"
        >
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
            const y = paddingTop + usableHeight * (1 - pct);
            return (
              <line
                key={pct}
                x1={0}
                y1={y}
                x2={chartWidth}
                y2={y}
                stroke="#f1f5f9"
                strokeWidth={1}
              />
            );
          })}

          {/* Bars */}
          {dailyData.map((day, i) => {
            const barHeight = day.tokens > 0 ? (day.tokens / maxTokens) * usableHeight : 0;
            const x = i * (barWidth + gap) + gap;
            const y = paddingTop + usableHeight - barHeight;

            return (
              <g key={day.date}>
                {/* Bar */}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barHeight}
                  rx={4}
                  fill="#6366f1"
                  className="transition-all duration-300"
                >
                  <title>
                    {day.label}: {day.tokens.toLocaleString()} tokens
                  </title>
                </rect>

                {/* Value label on top of bar */}
                {day.tokens > 0 && (
                  <text
                    x={x + barWidth / 2}
                    y={y - 4}
                    textAnchor="middle"
                    className="text-[9px] fill-gray-500"
                  >
                    {day.tokens >= 1000
                      ? `${(day.tokens / 1000).toFixed(1)}k`
                      : day.tokens}
                  </text>
                )}

                {/* Day label */}
                <text
                  x={x + barWidth / 2}
                  y={chartHeight - 8}
                  textAnchor="middle"
                  className="text-[11px] fill-gray-500 font-medium"
                >
                  {day.label}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
