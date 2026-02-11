interface RadarChartProps {
  dimensions: { name: string; score: number }[];
  size?: number;
}

export default function RadarChart({ dimensions, size = 250 }: RadarChartProps) {
  if (dimensions.length < 3) return null;

  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 40;
  const angleStep = (2 * Math.PI) / dimensions.length;
  // Start from the top (-PI/2)
  const startAngle = -Math.PI / 2;

  function polarToCartesian(angle: number, r: number): [number, number] {
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  }

  // Build grid lines at 0.25, 0.5, 0.75, 1.0
  const gridLevels = [0.25, 0.5, 0.75, 1.0];

  // Build data polygon
  const dataPoints = dimensions.map((dim, i) => {
    const angle = startAngle + i * angleStep;
    const r = dim.score * radius;
    return polarToCartesian(angle, r);
  });

  const dataPath =
    dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0]} ${p[1]}`).join(' ') + ' Z';

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto">
      {/* Grid circles */}
      {gridLevels.map((level) => {
        const gridPoints = dimensions.map((_, i) => {
          const angle = startAngle + i * angleStep;
          return polarToCartesian(angle, level * radius);
        });
        const gridPath =
          gridPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0]} ${p[1]}`).join(' ') + ' Z';
        return (
          <path
            key={level}
            d={gridPath}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={1}
            strokeDasharray={level < 1 ? '2,2' : undefined}
          />
        );
      })}

      {/* Axis lines */}
      {dimensions.map((_, i) => {
        const angle = startAngle + i * angleStep;
        const [ex, ey] = polarToCartesian(angle, radius);
        return (
          <line
            key={`axis-${i}`}
            x1={cx}
            y1={cy}
            x2={ex}
            y2={ey}
            stroke="#d1d5db"
            strokeWidth={1}
          />
        );
      })}

      {/* Data polygon */}
      <path
        d={dataPath}
        fill="rgba(99, 102, 241, 0.2)"
        stroke="#6366f1"
        strokeWidth={2}
      />

      {/* Data points */}
      {dataPoints.map((p, i) => (
        <circle
          key={`point-${i}`}
          cx={p[0]}
          cy={p[1]}
          r={3}
          fill="#6366f1"
          stroke="white"
          strokeWidth={1}
        />
      ))}

      {/* Labels */}
      {dimensions.map((dim, i) => {
        const angle = startAngle + i * angleStep;
        const labelRadius = radius + 20;
        const [lx, ly] = polarToCartesian(angle, labelRadius);
        const textAnchor =
          Math.abs(lx - cx) < 5
            ? 'middle'
            : lx < cx
              ? 'end'
              : 'start';
        const dy = Math.abs(ly - cy) < 5 ? '0.35em' : ly < cy ? '0em' : '0.7em';

        return (
          <text
            key={`label-${i}`}
            x={lx}
            y={ly}
            textAnchor={textAnchor}
            dy={dy}
            className="text-[10px] fill-gray-600 font-medium"
          >
            {dim.name}
          </text>
        );
      })}
    </svg>
  );
}
