import { Check, X } from 'lucide-react';

interface DiffViewProps {
  original: string;
  enriched: string;
  suggestions: string[];
  onAccept: () => void;
  onReject: () => void;
}

interface DiffLine {
  type: 'same' | 'added' | 'removed';
  content: string;
  lineNumber: { left?: number; right?: number };
}

function computeDiff(original: string, enriched: string): DiffLine[] {
  const origLines = original.split('\n');
  const enrichLines = enriched.split('\n');
  const result: DiffLine[] = [];

  // Simple line-by-line diff using longest common subsequence approach
  const lcs = computeLCS(origLines, enrichLines);
  let oi = 0;
  let ei = 0;
  let li = 0;

  while (li < lcs.length) {
    const [origIdx, enrichIdx] = lcs[li];

    // Lines removed from original (before the match)
    while (oi < origIdx) {
      result.push({
        type: 'removed',
        content: origLines[oi],
        lineNumber: { left: oi + 1 },
      });
      oi++;
    }

    // Lines added in enriched (before the match)
    while (ei < enrichIdx) {
      result.push({
        type: 'added',
        content: enrichLines[ei],
        lineNumber: { right: ei + 1 },
      });
      ei++;
    }

    // Matching line
    result.push({
      type: 'same',
      content: origLines[oi],
      lineNumber: { left: oi + 1, right: ei + 1 },
    });
    oi++;
    ei++;
    li++;
  }

  // Remaining removed lines
  while (oi < origLines.length) {
    result.push({
      type: 'removed',
      content: origLines[oi],
      lineNumber: { left: oi + 1 },
    });
    oi++;
  }

  // Remaining added lines
  while (ei < enrichLines.length) {
    result.push({
      type: 'added',
      content: enrichLines[ei],
      lineNumber: { right: ei + 1 },
    });
    ei++;
  }

  return result;
}

function computeLCS(a: string[], b: string[]): [number, number][] {
  const m = a.length;
  const n = b.length;

  // Build DP table
  const dp: number[][] = Array.from({ length: m + 1 }, () =>
    Array(n + 1).fill(0)
  );

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to find the actual LCS indices
  const result: [number, number][] = [];
  let i = m;
  let j = n;
  while (i > 0 && j > 0) {
    if (a[i - 1] === b[j - 1]) {
      result.unshift([i - 1, j - 1]);
      i--;
      j--;
    } else if (dp[i - 1][j] > dp[i][j - 1]) {
      i--;
    } else {
      j--;
    }
  }

  return result;
}

export default function DiffView({
  original,
  enriched,
  suggestions,
  onAccept,
  onReject,
}: DiffViewProps) {
  const diffLines = computeDiff(original, enriched);

  return (
    <div className="space-y-4">
      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-indigo-800 mb-2">AI Suggestions</h4>
          <ul className="space-y-1">
            {suggestions.map((suggestion, i) => (
              <li key={i} className="text-sm text-indigo-700 flex items-start gap-2">
                <span className="text-indigo-400 mt-0.5 flex-shrink-0">--</span>
                {suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Diff view */}
      <div className="border border-gray-300 rounded-lg overflow-hidden">
        <div className="bg-gray-100 border-b border-gray-300 px-4 py-2 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-600">Unified Diff View</span>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-red-100 border border-red-300" />
              Removed
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded bg-emerald-100 border border-emerald-300" />
              Added
            </span>
          </div>
        </div>

        <div className="overflow-auto max-h-[500px] bg-gray-950 font-mono text-xs">
          {diffLines.map((line, i) => (
            <div
              key={i}
              className={`flex ${
                line.type === 'added'
                  ? 'bg-emerald-950/40'
                  : line.type === 'removed'
                    ? 'bg-red-950/40'
                    : ''
              }`}
            >
              {/* Line numbers */}
              <div className="flex-shrink-0 w-10 text-right pr-2 text-gray-600 select-none py-0.5">
                {line.lineNumber.left ?? ''}
              </div>
              <div className="flex-shrink-0 w-10 text-right pr-2 text-gray-600 select-none py-0.5">
                {line.lineNumber.right ?? ''}
              </div>

              {/* Symbol */}
              <div className="flex-shrink-0 w-5 text-center py-0.5 select-none">
                {line.type === 'added' && (
                  <span className="text-emerald-400">+</span>
                )}
                {line.type === 'removed' && (
                  <span className="text-red-400">-</span>
                )}
                {line.type === 'same' && (
                  <span className="text-gray-600">&nbsp;</span>
                )}
              </div>

              {/* Content */}
              <div
                className={`flex-1 py-0.5 pr-4 whitespace-pre ${
                  line.type === 'added'
                    ? 'text-emerald-300'
                    : line.type === 'removed'
                      ? 'text-red-300'
                      : 'text-gray-300'
                }`}
              >
                {line.content}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-3 justify-end">
        <button
          onClick={onReject}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <X size={16} />
          Reject Changes
        </button>
        <button
          onClick={onAccept}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
        >
          <Check size={16} />
          Accept Changes
        </button>
      </div>
    </div>
  );
}
