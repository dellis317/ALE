import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  BookOpen,
  Loader2,
  FolderTree,
  FileText,
  ChevronDown,
  ChevronRight,
  Calendar,
  GitBranch,
  Hash,
  Shield,
  ClipboardList,
  Settings2,
  History,
  Eye,
  Lock,
  Layers,
  LayoutList,
  Blocks,
} from 'lucide-react';
import { getGeneratedLibrary } from '../api/client';
import type { LibraryDocNode } from '../types';
import Badge from '../components/Badge';

/** Map section slugs to icons. */
function getSectionIcon(slug: string) {
  const last = slug.split('/').pop() || '';
  if (last.includes('overview')) return Eye;
  if (last.includes('architecture')) return Blocks;
  if (last.includes('instruction')) return LayoutList;
  if (last.includes('guardrail')) return Shield;
  if (last.includes('validation')) return ClipboardList;
  if (last.includes('dependenc')) return Layers;
  if (last.includes('version')) return History;
  if (last.includes('audit')) return GitBranch;
  if (last.includes('security')) return Lock;
  if (last.includes('variable')) return Settings2;
  if (last.includes('step')) return Hash;
  return FileText;
}

/** Recursive tree navigation component. */
function TreeNode({
  node,
  depth,
  selectedId,
  onSelect,
  expandedIds,
  onToggle,
}: {
  node: LibraryDocNode;
  depth: number;
  selectedId: string;
  onSelect: (node: LibraryDocNode) => void;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
}) {
  const isSelected = node.id === selectedId;
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedIds.has(node.id);
  const Icon = getSectionIcon(node.slug);

  return (
    <div>
      <button
        onClick={() => {
          onSelect(node);
          if (hasChildren) onToggle(node.id);
        }}
        className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
          isSelected
            ? 'bg-indigo-50 text-indigo-700 font-medium'
            : 'text-gray-700 hover:bg-gray-50'
        }`}
        style={{ paddingLeft: `${12 + depth * 16}px` }}
      >
        {hasChildren ? (
          <span className="text-gray-400 flex-shrink-0">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        ) : (
          <span className="w-3.5 flex-shrink-0" />
        )}
        <Icon size={14} className={isSelected ? 'text-indigo-500' : 'text-gray-400'} />
        <span className="truncate">{node.title}</span>
        {node.type === 'root' && (
          <Badge label="Root" variant="info" />
        )}
      </button>

      {hasChildren && isExpanded && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              expandedIds={expandedIds}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** Simple markdown-to-JSX renderer for the library content. */
function MarkdownContent({ content }: { content: string }) {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inTable = false;
  let tableRows: string[][] = [];
  let tableAligns: string[] = [];
  let inCode = false;
  let codeLines: string[] = [];

  const flushTable = () => {
    if (tableRows.length === 0) return;
    const header = tableRows[0];
    const body = tableRows.slice(1);

    elements.push(
      <div key={`table-${elements.length}`} className="overflow-x-auto my-4">
        <table className="min-w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
          <thead className="bg-gray-50">
            <tr>
              {header.map((cell, i) => (
                <th
                  key={i}
                  className="px-4 py-2 text-left text-xs font-semibold text-gray-600 border-b border-gray-200"
                >
                  {cell.trim()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className="px-4 py-2 text-gray-700 border-b border-gray-100"
                  >
                    {renderInline(cell.trim())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    tableRows = [];
    tableAligns = [];
  };

  const flushCode = () => {
    elements.push(
      <pre
        key={`code-${elements.length}`}
        className="bg-gray-900 text-gray-100 text-sm rounded-lg px-4 py-3 my-3 overflow-x-auto font-mono"
      >
        {codeLines.join('\n')}
      </pre>
    );
    codeLines = [];
  };

  /** Render inline formatting: bold, italic, code, links. */
  function renderInline(text: string): React.ReactNode {
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let idx = 0;

    while (remaining.length > 0) {
      // inline code
      const codeMatch = remaining.match(/^`([^`]+)`/);
      if (codeMatch) {
        parts.push(
          <code key={idx++} className="bg-gray-100 text-indigo-700 px-1.5 py-0.5 rounded text-xs font-mono">
            {codeMatch[1]}
          </code>
        );
        remaining = remaining.slice(codeMatch[0].length);
        continue;
      }

      // bold
      const boldMatch = remaining.match(/^\*\*([^*]+)\*\*/);
      if (boldMatch) {
        parts.push(<strong key={idx++} className="font-semibold">{boldMatch[1]}</strong>);
        remaining = remaining.slice(boldMatch[0].length);
        continue;
      }

      // italic
      const italicMatch = remaining.match(/^\*([^*]+)\*/);
      if (italicMatch) {
        parts.push(<em key={idx++}>{italicMatch[1]}</em>);
        remaining = remaining.slice(italicMatch[0].length);
        continue;
      }

      // link
      const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        parts.push(
          <a
            key={idx++}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 hover:underline"
          >
            {linkMatch[1]}
          </a>
        );
        remaining = remaining.slice(linkMatch[0].length);
        continue;
      }

      // plain character
      parts.push(remaining[0]);
      remaining = remaining.slice(1);
    }

    return parts.length === 1 ? parts[0] : <>{parts}</>;
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code blocks
    if (line.trimStart().startsWith('```')) {
      if (inCode) {
        flushCode();
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      continue;
    }

    // Tables
    if (line.includes('|') && line.trim().startsWith('|')) {
      const cells = line
        .split('|')
        .slice(1, -1)
        .map((c) => c.trim());

      // Check if separator row
      if (cells.every((c) => /^[-:]+$/.test(c))) {
        tableAligns = cells.map((c) => {
          if (c.startsWith(':') && c.endsWith(':')) return 'center';
          if (c.endsWith(':')) return 'right';
          return 'left';
        });
        inTable = true;
        continue;
      }

      tableRows.push(cells);
      inTable = true;
      continue;
    }

    if (inTable) {
      flushTable();
      inTable = false;
    }

    // Empty line
    if (!line.trim()) {
      elements.push(<div key={`br-${i}`} className="h-3" />);
      continue;
    }

    // Headings
    const h1 = line.match(/^# (.+)/);
    if (h1) {
      elements.push(
        <h1 key={i} className="text-2xl font-bold text-gray-900 mt-6 mb-3 first:mt-0">
          {renderInline(h1[1])}
        </h1>
      );
      continue;
    }
    const h2 = line.match(/^## (.+)/);
    if (h2) {
      elements.push(
        <h2 key={i} className="text-lg font-semibold text-gray-900 mt-5 mb-2">
          {renderInline(h2[1])}
        </h2>
      );
      continue;
    }
    const h3 = line.match(/^### (.+)/);
    if (h3) {
      elements.push(
        <h3 key={i} className="text-base font-semibold text-gray-800 mt-4 mb-1.5">
          {renderInline(h3[1])}
        </h3>
      );
      continue;
    }

    // Blockquote
    const bq = line.match(/^> (.+)/);
    if (bq) {
      elements.push(
        <blockquote
          key={i}
          className="border-l-4 border-indigo-300 pl-4 py-1 my-2 text-gray-600 italic"
        >
          {renderInline(bq[1])}
        </blockquote>
      );
      continue;
    }

    // List items (ordered)
    const ol = line.match(/^(\d+)\.\s+(.+)/);
    if (ol) {
      elements.push(
        <div key={i} className="flex gap-2 ml-4 text-sm text-gray-700 leading-relaxed">
          <span className="text-gray-400 flex-shrink-0 font-mono">{ol[1]}.</span>
          <span>{renderInline(ol[2])}</span>
        </div>
      );
      continue;
    }

    // List items (unordered)
    const ul = line.match(/^[-*]\s+(.+)/);
    if (ul) {
      elements.push(
        <div key={i} className="flex gap-2 ml-4 text-sm text-gray-700 leading-relaxed">
          <span className="text-indigo-400 flex-shrink-0 mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400" />
          <span>{renderInline(ul[1])}</span>
        </div>
      );
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={i} className="my-4 border-gray-200" />);
      continue;
    }

    // Paragraph
    elements.push(
      <p key={i} className="text-sm text-gray-700 leading-relaxed">
        {renderInline(line)}
      </p>
    );
  }

  // Flush any remaining table/code
  if (inTable) flushTable();
  if (inCode) flushCode();

  return <div className="space-y-0.5">{elements}</div>;
}

export default function LibraryViewer() {
  const { id } = useParams<{ id: string }>();

  const libraryQuery = useQuery({
    queryKey: ['generated-library', id],
    queryFn: () => getGeneratedLibrary(id!),
    enabled: !!id,
  });

  const library = libraryQuery.data;

  // Tree state
  const [selectedNode, setSelectedNode] = useState<LibraryDocNode | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // When library loads, auto-select root and expand it
  if (library && !selectedNode) {
    setSelectedNode(library.structure);
    setExpandedIds(new Set([library.structure.id]));
  }

  const handleToggle = (nodeId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const handleExpandAll = () => {
    if (!library) return;
    const ids = new Set<string>();
    const walk = (node: LibraryDocNode) => {
      ids.add(node.id);
      node.children.forEach(walk);
    };
    walk(library.structure);
    setExpandedIds(ids);
  };

  const handleCollapseAll = () => {
    if (!library) return;
    setExpandedIds(new Set([library.structure.id]));
  };

  // Breadcrumb trail to selected node
  const getBreadcrumb = (
    node: LibraryDocNode,
    target: string,
    path: LibraryDocNode[]
  ): LibraryDocNode[] | null => {
    if (node.id === target) return [...path, node];
    for (const child of node.children) {
      const found = getBreadcrumb(child, target, [...path, node]);
      if (found) return found;
    }
    return null;
  };

  const breadcrumb = library && selectedNode
    ? getBreadcrumb(library.structure, selectedNode.id, []) || []
    : [];

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/libraries"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600 transition-colors mb-3"
        >
          <ArrowLeft size={14} />
          Back to Libraries
        </Link>

        {library && (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
              <FolderTree size={20} className="text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{library.name}</h1>
              <div className="flex items-center gap-3 mt-0.5 text-sm text-gray-500">
                <span className="flex items-center gap-1">
                  <Calendar size={12} />
                  {new Date(library.created_at).toLocaleDateString()}
                </span>
                <span className="flex items-center gap-1">
                  <GitBranch size={12} />
                  {library.candidate_name === '__whole_codebase__'
                    ? 'Full Codebase'
                    : library.candidate_name}
                </span>
                {(library.source_repo_url || library.repo_path) && (
                  <span className="font-mono text-xs text-gray-400 truncate max-w-xs" title={library.source_repo_url || library.repo_path}>
                    {library.source_repo_url || library.repo_path}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Loading */}
      {libraryQuery.isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={40} className="animate-spin text-indigo-600" />
        </div>
      )}

      {/* Error */}
      {libraryQuery.error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <h3 className="text-red-800 font-semibold mb-1">Error</h3>
          <p className="text-sm text-red-700">
            {libraryQuery.error instanceof Error
              ? libraryQuery.error.message
              : 'Failed to load library'}
          </p>
        </div>
      )}

      {/* Content: Tree + Document viewer */}
      {library && (
        <div className="flex gap-6" style={{ minHeight: 'calc(100vh - 220px)' }}>
          {/* Left: Tree navigator */}
          <div className="w-72 flex-shrink-0">
            <div className="bg-white rounded-xl border border-gray-200 sticky top-8 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-1.5">
                  <BookOpen size={14} />
                  Structure
                </h3>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleExpandAll}
                    className="text-xs text-gray-400 hover:text-indigo-600 px-1.5 py-0.5 rounded transition-colors"
                    title="Expand all"
                  >
                    Expand
                  </button>
                  <span className="text-gray-300">|</span>
                  <button
                    onClick={handleCollapseAll}
                    className="text-xs text-gray-400 hover:text-indigo-600 px-1.5 py-0.5 rounded transition-colors"
                    title="Collapse all"
                  >
                    Collapse
                  </button>
                </div>
              </div>
              <div className="p-2 max-h-[70vh] overflow-y-auto">
                <TreeNode
                  node={library.structure}
                  depth={0}
                  selectedId={selectedNode?.id || ''}
                  onSelect={setSelectedNode}
                  expandedIds={expandedIds}
                  onToggle={handleToggle}
                />
              </div>
            </div>
          </div>

          {/* Right: Document viewer */}
          <div className="flex-1 min-w-0">
            {selectedNode ? (
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* Breadcrumb */}
                {breadcrumb.length > 1 && (
                  <div className="px-6 py-2.5 bg-gray-50 border-b border-gray-100 flex items-center gap-1.5 text-xs text-gray-500 overflow-x-auto">
                    {breadcrumb.map((node, i) => (
                      <span key={node.id} className="flex items-center gap-1.5 flex-shrink-0">
                        {i > 0 && <ChevronRight size={10} className="text-gray-300" />}
                        <button
                          onClick={() => setSelectedNode(node)}
                          className={`hover:text-indigo-600 transition-colors ${
                            node.id === selectedNode.id
                              ? 'text-indigo-600 font-medium'
                              : ''
                          }`}
                        >
                          {node.title}
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                {/* Document header */}
                <div className="px-6 py-4 border-b border-gray-100">
                  <div className="flex items-center gap-2">
                    <Badge
                      label={selectedNode.type}
                      variant={
                        selectedNode.type === 'root'
                          ? 'info'
                          : selectedNode.type === 'section'
                            ? 'success'
                            : 'default'
                      }
                    />
                    <span className="text-xs font-mono text-gray-400">
                      {selectedNode.slug}
                    </span>
                  </div>
                  {selectedNode.summary && (
                    <p className="text-sm text-gray-600 mt-2">{selectedNode.summary}</p>
                  )}
                </div>

                {/* Document content */}
                <div className="px-6 py-5">
                  <MarkdownContent content={selectedNode.content} />
                </div>

                {/* Child sections quick nav */}
                {selectedNode.children.length > 0 && (
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      Child Sections
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {selectedNode.children.map((child) => {
                        const Icon = getSectionIcon(child.slug);
                        return (
                          <button
                            key={child.id}
                            onClick={() => {
                              setSelectedNode(child);
                              setExpandedIds((prev) => new Set([...prev, selectedNode.id]));
                            }}
                            className="flex items-center gap-2.5 px-3 py-2.5 bg-white rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50/50 text-left transition-colors group"
                          >
                            <Icon
                              size={14}
                              className="text-gray-400 group-hover:text-indigo-500 flex-shrink-0"
                            />
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-gray-700 group-hover:text-indigo-700 truncate">
                                {child.title}
                              </p>
                              <p className="text-xs text-gray-500 truncate">
                                {child.summary}
                              </p>
                            </div>
                            <ChevronRight
                              size={12}
                              className="text-gray-300 group-hover:text-indigo-400 flex-shrink-0 ml-auto"
                            />
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <BookOpen size={40} className="text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">
                  Select a section from the tree to view its content
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
