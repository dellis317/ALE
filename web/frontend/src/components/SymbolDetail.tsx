import {
  Box,
  Code2,
  Minus,
  Hash,
  FileCode2,
  Eye,
  EyeOff,
  Zap,
  ArrowRight,
  List,
} from 'lucide-react';
import type { IRSymbol } from '../types';
import Badge from './Badge';

interface SymbolDetailProps {
  symbol: IRSymbol | null;
}

const kindIcons: Record<string, typeof Box> = {
  class: Box,
  function: Code2,
  method: Minus,
  constant: Hash,
};

const kindColors: Record<string, string> = {
  class: 'bg-purple-50 text-purple-700 ring-purple-200',
  function: 'bg-blue-50 text-blue-700 ring-blue-200',
  method: 'bg-cyan-50 text-cyan-700 ring-cyan-200',
  constant: 'bg-gray-100 text-gray-700 ring-gray-200',
};

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
      {children}
    </h4>
  );
}

export default function SymbolDetail({ symbol }: SymbolDetailProps) {
  if (!symbol) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-16 text-center">
        <div className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center mb-3">
          <Code2 size={24} className="text-gray-400" />
        </div>
        <p className="text-sm text-gray-500 font-medium">Select a symbol</p>
        <p className="text-xs text-gray-400 mt-1">
          Click a symbol in the tree to view its details
        </p>
      </div>
    );
  }

  const Icon = kindIcons[symbol.kind] || Code2;
  const kindStyle = kindColors[symbol.kind] || kindColors.constant;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <Icon size={18} className="text-indigo-600 flex-shrink-0" />
          <h3 className="text-lg font-bold text-gray-900">{symbol.name}</h3>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${kindStyle}`}
          >
            {symbol.kind}
          </span>
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
              symbol.visibility === 'public'
                ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                : symbol.visibility === 'private'
                  ? 'bg-red-50 text-red-700 ring-red-200'
                  : 'bg-amber-50 text-amber-700 ring-amber-200'
            }`}
          >
            {symbol.visibility === 'public' ? (
              <Eye size={10} />
            ) : (
              <EyeOff size={10} />
            )}
            {symbol.visibility}
          </span>
          {symbol.is_async && <Badge label="async" variant="info" />}
        </div>

        {/* Source location */}
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <FileCode2 size={12} />
          <span className="font-mono">
            {symbol.source_file}:{symbol.line_start}-{symbol.line_end}
          </span>
          <span className="text-gray-400">({symbol.line_count} lines)</span>
        </div>
      </div>

      {/* Docstring */}
      {symbol.docstring && (
        <div>
          <SectionTitle>Docstring</SectionTitle>
          <pre className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap font-mono border border-gray-200 max-h-48 overflow-y-auto">
            {symbol.docstring}
          </pre>
        </div>
      )}

      {/* Parameters */}
      {symbol.parameters && symbol.parameters.length > 0 && (
        <div>
          <SectionTitle>Parameters</SectionTitle>
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500">
                    Name
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500">
                    Type
                  </th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-gray-500">
                    Default
                  </th>
                  <th className="text-center px-3 py-2 text-xs font-semibold text-gray-500">
                    Required
                  </th>
                </tr>
              </thead>
              <tbody>
                {symbol.parameters.map((param, i) => (
                  <tr
                    key={param.name}
                    className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}
                  >
                    <td className="px-3 py-2 font-mono font-medium text-gray-900">
                      {param.name}
                    </td>
                    <td className="px-3 py-2 font-mono text-indigo-600">
                      {param.type_hint || '--'}
                    </td>
                    <td className="px-3 py-2 font-mono text-gray-600">
                      {param.default_value || '--'}
                    </td>
                    <td className="px-3 py-2 text-center">
                      {param.required ? (
                        <span className="inline-block w-2 h-2 rounded-full bg-red-500" title="Required" />
                      ) : (
                        <span className="inline-block w-2 h-2 rounded-full bg-gray-300" title="Optional" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Return type */}
      {symbol.return_type && (
        <div>
          <SectionTitle>Return Type</SectionTitle>
          <div className="flex items-center gap-2">
            <ArrowRight size={14} className="text-gray-400" />
            <code className="text-sm font-mono text-indigo-700 bg-indigo-50 px-2 py-1 rounded">
              {symbol.return_type}
            </code>
          </div>
        </div>
      )}

      {/* Side effects */}
      {symbol.side_effects && symbol.side_effects.length > 0 && (
        <div>
          <SectionTitle>Side Effects</SectionTitle>
          <div className="flex flex-wrap gap-1.5">
            {symbol.side_effects.map((effect) => (
              <span
                key={effect}
                className="inline-flex items-center gap-1 rounded-full bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200 px-2.5 py-0.5 text-xs font-medium"
              >
                <Zap size={10} />
                {effect}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Base classes */}
      {symbol.base_classes && symbol.base_classes.length > 0 && (
        <div>
          <SectionTitle>Base Classes</SectionTitle>
          <div className="flex flex-wrap gap-1.5">
            {symbol.base_classes.map((base) => (
              <Badge key={base} label={base} variant="info" />
            ))}
          </div>
        </div>
      )}

      {/* Interfaces */}
      {symbol.interfaces && symbol.interfaces.length > 0 && (
        <div>
          <SectionTitle>Interfaces</SectionTitle>
          <div className="flex flex-wrap gap-1.5">
            {symbol.interfaces.map((iface) => (
              <Badge key={iface} label={iface} variant="default" />
            ))}
          </div>
        </div>
      )}

      {/* Members count */}
      {symbol.members && symbol.members.length > 0 && (
        <div>
          <SectionTitle>Members</SectionTitle>
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <List size={14} className="text-gray-400" />
            <span>
              {symbol.members.length} member{symbol.members.length !== 1 ? 's' : ''}
            </span>
            <span className="text-gray-400">|</span>
            <span className="text-gray-500">
              {symbol.members.filter((m) => m.kind === 'method').length} methods,{' '}
              {symbol.members.filter((m) => m.kind !== 'method').length} other
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
