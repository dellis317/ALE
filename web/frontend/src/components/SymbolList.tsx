import { Code2, Box, Variable } from 'lucide-react';
import type { CandidateSymbol } from '../types';

function SymbolIcon({ kind }: { kind: string }) {
  switch (kind) {
    case 'function':
    case 'method':
      return <Code2 size={14} className="text-indigo-500 flex-shrink-0" />;
    case 'class':
      return <Box size={14} className="text-amber-500 flex-shrink-0" />;
    default:
      return <Variable size={14} className="text-gray-400 flex-shrink-0" />;
  }
}

interface SymbolListProps {
  symbols: CandidateSymbol[];
  maxItems?: number;
}

export default function SymbolList({ symbols, maxItems = 10 }: SymbolListProps) {
  const displayed = symbols.slice(0, maxItems);

  if (displayed.length === 0) {
    return (
      <p className="text-xs text-gray-400 italic">No symbols extracted</p>
    );
  }

  return (
    <div className="space-y-2">
      {displayed.map((sym, i) => (
        <div
          key={`${sym.name}-${i}`}
          className="flex items-start gap-2 px-2 py-1.5 rounded bg-gray-50 border border-gray-100"
        >
          <SymbolIcon kind={sym.kind} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-gray-900">{sym.name}</span>
              <span className="text-[10px] font-medium text-gray-400 uppercase">{sym.kind}</span>
            </div>
            {sym.signature && (
              <code className="text-xs font-mono text-indigo-700 block mt-0.5 truncate">
                {sym.signature}
              </code>
            )}
            {sym.docstring && (
              <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{sym.docstring}</p>
            )}
          </div>
        </div>
      ))}
      {symbols.length > maxItems && (
        <p className="text-xs text-gray-400 text-center">
          +{symbols.length - maxItems} more symbols
        </p>
      )}
    </div>
  );
}
