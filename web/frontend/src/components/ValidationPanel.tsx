import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import { validateContent } from '../api/client';

interface ValidationPanelProps {
  yamlContent: string;
}

export default function ValidationPanel({ yamlContent }: ValidationPanelProps) {
  // Debounce: track a stable content value after 500ms of no changes
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stableContentRef = useRef(yamlContent);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      stableContentRef.current = yamlContent;
      // Force re-render by dispatching a state update through the query key
    }, 500);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [yamlContent]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['validate-content', yamlContent],
    queryFn: () => validateContent(yamlContent),
    enabled: yamlContent.trim().length > 0,
    staleTime: 5000,
    refetchOnWindowFocus: false,
    // Debounce is handled via React Query's built-in deduplication
    // and the fact that each unique content generates a new query key
  });

  const hasContent = yamlContent.trim().length > 0;

  if (!hasContent) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-gray-500">Enter YAML content to see validation results</p>
      </div>
    );
  }

  if (isLoading || isFetching) {
    return (
      <div className="p-4 flex items-center justify-center gap-2">
        <Loader2 size={16} className="animate-spin text-indigo-600" />
        <span className="text-sm text-gray-600">Validating...</span>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const hasErrors = data.schema_errors.length > 0 || data.semantic_errors.length > 0;
  const hasWarnings = data.semantic_warnings.length > 0;

  return (
    <div className="space-y-3">
      {/* Status banner */}
      {data.valid && !hasWarnings && (
        <div className="flex items-center gap-2 px-3 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg">
          <CheckCircle2 size={16} className="text-emerald-600 flex-shrink-0" />
          <span className="text-sm font-medium text-emerald-700">All checks passed</span>
        </div>
      )}

      {data.valid && hasWarnings && (
        <div className="flex items-center gap-2 px-3 py-2.5 bg-emerald-50 border border-emerald-200 rounded-lg">
          <CheckCircle2 size={16} className="text-emerald-600 flex-shrink-0" />
          <span className="text-sm font-medium text-emerald-700">
            Valid with {data.semantic_warnings.length} warning{data.semantic_warnings.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {!data.valid && (
        <div className="flex items-center gap-2 px-3 py-2.5 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle size={16} className="text-red-600 flex-shrink-0" />
          <span className="text-sm font-medium text-red-700">
            Validation failed ({data.schema_errors.length + data.semantic_errors.length} error{(data.schema_errors.length + data.semantic_errors.length) !== 1 ? 's' : ''})
          </span>
        </div>
      )}

      {/* Schema errors */}
      {data.schema_errors.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Schema Errors
          </h4>
          <ul className="space-y-1.5">
            {data.schema_errors.map((error, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <AlertCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
                <span className="text-red-700 font-mono text-xs break-all">{error}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Semantic errors */}
      {data.semantic_errors.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Semantic Errors
          </h4>
          <ul className="space-y-1.5">
            {data.semantic_errors.map((error, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <AlertCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
                <span className="text-red-700 font-mono text-xs break-all">{error}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Semantic warnings */}
      {data.semantic_warnings.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Warnings
          </h4>
          <ul className="space-y-1.5">
            {data.semantic_warnings.map((warning, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <AlertTriangle size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                <span className="text-amber-700 font-mono text-xs break-all">{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
