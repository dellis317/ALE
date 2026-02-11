import { useState } from 'react';
import { Box, Code2, Minus, Hash, ChevronDown, ChevronRight, Zap } from 'lucide-react';
import type { IRSymbol } from '../types';

interface SymbolTreeProps {
  symbols: IRSymbol[];
  onSelect: (symbol: IRSymbol) => void;
  selectedSymbol?: string;
}

const kindIcons: Record<string, typeof Box> = {
  class: Box,
  function: Code2,
  method: Minus,
  constant: Hash,
};

function VisibilityDot({ visibility }: { visibility: string }) {
  const color =
    visibility === 'public'
      ? 'bg-emerald-500'
      : visibility === 'private'
        ? 'bg-red-500'
        : 'bg-amber-500';

  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${color} flex-shrink-0`}
      title={visibility}
    />
  );
}

function SideEffectBadge({ effect }: { effect: string }) {
  return (
    <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200 px-1.5 py-0 text-[10px] font-medium">
      <Zap size={8} />
      {effect}
    </span>
  );
}

function TreeNode({
  symbol,
  onSelect,
  selectedSymbol,
  depth,
}: {
  symbol: IRSymbol;
  onSelect: (symbol: IRSymbol) => void;
  selectedSymbol?: string;
  depth: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasChildren = symbol.members && symbol.members.length > 0;
  const isSelected = selectedSymbol === symbol.qualified_name;

  const Icon = kindIcons[symbol.kind] || Code2;

  const handleClick = () => {
    onSelect(symbol);
  };

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={`w-full text-left flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-colors group cursor-pointer ${
          isSelected
            ? 'bg-indigo-50 text-indigo-900'
            : 'hover:bg-gray-100 text-gray-700'
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {/* Expand/collapse toggle */}
        {hasChildren ? (
          <span
            onClick={handleToggle}
            className="flex-shrink-0 text-gray-400 hover:text-gray-600"
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}

        {/* Kind icon */}
        <Icon
          size={14}
          className={`flex-shrink-0 ${
            isSelected ? 'text-indigo-600' : 'text-gray-400 group-hover:text-gray-600'
          }`}
        />

        {/* Visibility dot */}
        <VisibilityDot visibility={symbol.visibility} />

        {/* Name */}
        <span
          className={`truncate font-medium ${
            isSelected ? 'text-indigo-900' : 'text-gray-900'
          }`}
        >
          {symbol.name}
        </span>

        {/* Async badge */}
        {symbol.is_async && (
          <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200 px-1.5 py-0 text-[10px] font-medium flex-shrink-0">
            async
          </span>
        )}

        {/* Side effects badges */}
        {symbol.side_effects && symbol.side_effects.length > 0 && (
          <div className="flex items-center gap-1 flex-shrink-0">
            {symbol.side_effects.slice(0, 2).map((effect) => (
              <SideEffectBadge key={effect} effect={effect} />
            ))}
            {symbol.side_effects.length > 2 && (
              <span className="text-[10px] text-gray-400">
                +{symbol.side_effects.length - 2}
              </span>
            )}
          </div>
        )}
      </button>

      {/* Children */}
      {hasChildren && expanded && (
        <div>
          {symbol.members.map((member) => (
            <TreeNode
              key={member.qualified_name || `${symbol.qualified_name}.${member.name}`}
              symbol={member}
              onSelect={onSelect}
              selectedSymbol={selectedSymbol}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function SymbolTree({ symbols, onSelect, selectedSymbol }: SymbolTreeProps) {
  if (!symbols || symbols.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-gray-500">
        No symbols found
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {symbols.map((symbol) => (
        <TreeNode
          key={symbol.qualified_name || symbol.name}
          symbol={symbol}
          onSelect={onSelect}
          selectedSymbol={selectedSymbol}
          depth={0}
        />
      ))}
    </div>
  );
}
