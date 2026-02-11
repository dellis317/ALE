import { useState } from 'react';
import { CheckCircle2, XCircle, ChevronDown, ChevronRight } from 'lucide-react';

interface GateResultProps {
  name: string;
  passed: boolean;
  errors?: string[];
  details?: string;
}

export default function GateResult({ name, passed, errors, details }: GateResultProps) {
  const [expanded, setExpanded] = useState(!passed);
  const hasContent = (errors && errors.length > 0) || details;

  return (
    <div
      className={`rounded-lg border ${
        passed ? 'border-emerald-200 bg-emerald-50/50' : 'border-red-200 bg-red-50/50'
      }`}
    >
      <button
        onClick={() => hasContent && setExpanded(!expanded)}
        className={`w-full flex items-center gap-3 px-4 py-3 text-left ${
          hasContent ? 'cursor-pointer' : 'cursor-default'
        }`}
      >
        {passed ? (
          <CheckCircle2 size={20} className="text-emerald-600 flex-shrink-0" />
        ) : (
          <XCircle size={20} className="text-red-600 flex-shrink-0" />
        )}
        <span
          className={`font-semibold text-sm ${passed ? 'text-emerald-800' : 'text-red-800'}`}
        >
          {name}
        </span>
        <span
          className={`ml-auto text-xs font-medium px-2 py-0.5 rounded-full ${
            passed
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-red-100 text-red-700'
          }`}
        >
          {passed ? 'PASSED' : 'FAILED'}
        </span>
        {hasContent && (
          <span className="text-gray-400">
            {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </span>
        )}
      </button>

      {expanded && hasContent && (
        <div className="px-4 pb-3 pt-0 border-t border-gray-200/50">
          {details && <p className="text-sm text-gray-600 mt-2">{details}</p>}
          {errors && errors.length > 0 && (
            <ul className="mt-2 space-y-1">
              {errors.map((err, i) => (
                <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                  <span className="text-red-400 mt-0.5 flex-shrink-0">--</span>
                  <span className="font-mono text-xs break-all">{err}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
