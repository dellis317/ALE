import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Network,
  Loader2,
  Plus,
  Trash2,
  Play,
  FileCode2,
  GitBranch,
} from 'lucide-react';
import { parseFile } from '../api/client';
import type { IRSymbol, IRModule } from '../types';
import SymbolTree from '../components/SymbolTree';
import SymbolDetail from '../components/SymbolDetail';
import DependencyGraph from '../components/DependencyGraph';
import EmptyState from '../components/EmptyState';

type ActiveTab = 'symbols' | 'dependencies';

export default function IRExplorer() {
  const [filePaths, setFilePaths] = useState<string[]>(['']);
  const [repoRoot, setRepoRoot] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState<IRSymbol | null>(null);
  const [parsedModules, setParsedModules] = useState<IRModule[]>([]);
  const [activeTab, setActiveTab] = useState<ActiveTab>('symbols');

  const mutation = useMutation({
    mutationFn: async () => {
      const validPaths = filePaths.filter((p) => p.trim() !== '');
      if (validPaths.length === 0) throw new Error('No file paths provided');

      const results = await Promise.all(
        validPaths.map((path) => parseFile(path.trim(), repoRoot.trim() || undefined))
      );
      return results;
    },
    onSuccess: (data) => {
      setParsedModules(data);
      setSelectedSymbol(null);
    },
  });

  const addFilePath = () => {
    setFilePaths([...filePaths, '']);
  };

  const removeFilePath = (index: number) => {
    if (filePaths.length === 1) return;
    setFilePaths(filePaths.filter((_, i) => i !== index));
  };

  const updateFilePath = (index: number, value: string) => {
    const updated = [...filePaths];
    updated[index] = value;
    setFilePaths(updated);
  };

  const handleParse = () => {
    mutation.mutate();
  };

  const hasValidPaths = filePaths.some((p) => p.trim() !== '');
  const allSymbols = parsedModules.flatMap((m) => m.symbols);
  const allImports = parsedModules.flatMap((m) => m.imports);
  const primaryModulePath = parsedModules.length > 0 ? parsedModules[0].path : '';

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Network size={24} className="text-indigo-600" />
          IR Explorer
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Parse source files to explore their intermediate representation, symbols, and dependencies
        </p>
      </div>

      {/* Input Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <div className="space-y-4">
          {/* File paths */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              File Paths
            </label>
            <div className="space-y-2">
              {filePaths.map((path, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div className="flex-1">
                    <div className="relative">
                      <FileCode2
                        size={16}
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                      />
                      <input
                        type="text"
                        placeholder="/path/to/source/file.py"
                        value={path}
                        onChange={(e) => updateFilePath(index, e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && hasValidPaths && !mutation.isPending) {
                            handleParse();
                          }
                        }}
                        className="w-full pl-10 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono"
                      />
                    </div>
                  </div>
                  {filePaths.length > 1 && (
                    <button
                      onClick={() => removeFilePath(index)}
                      className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                      title="Remove file path"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              onClick={addFilePath}
              className="mt-2 flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-700 font-medium transition-colors"
            >
              <Plus size={14} />
              Add another file
            </button>
          </div>

          {/* Repo root */}
          <div>
            <label
              htmlFor="repo-root"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Repository Root
              <span className="text-gray-400 font-normal ml-1">(optional)</span>
            </label>
            <div className="relative max-w-lg">
              <GitBranch
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                id="repo-root"
                type="text"
                placeholder="Defaults to file's directory"
                value={repoRoot}
                onChange={(e) => setRepoRoot(e.target.value)}
                className="w-full pl-10 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono"
              />
            </div>
          </div>
        </div>

        {/* Parse button */}
        <div className="mt-5">
          <button
            onClick={handleParse}
            disabled={!hasValidPaths || mutation.isPending}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Play size={16} />
            )}
            Parse
          </button>
        </div>
      </div>

      {/* Loading */}
      {mutation.isPending && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Loader2 size={40} className="animate-spin text-indigo-600 mx-auto mb-4" />
            <p className="text-sm text-gray-600 font-medium">Parsing files...</p>
            <p className="text-xs text-gray-400 mt-1">
              Analyzing {filePaths.filter((p) => p.trim() !== '').length} file(s)
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {mutation.error && !mutation.isPending && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
          <h3 className="text-red-800 font-semibold mb-1">Parse Error</h3>
          <p className="text-sm text-red-700">
            {mutation.error instanceof Error
              ? mutation.error.message
              : 'An unknown error occurred'}
          </p>
        </div>
      )}

      {/* Results */}
      {parsedModules.length > 0 && !mutation.isPending && (
        <div>
          {/* Module summary */}
          <div className="flex items-center gap-4 mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Results
            </h2>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>
                {parsedModules.length} module(s)
              </span>
              <span className="text-gray-300">|</span>
              <span>
                {allSymbols.length} symbol(s)
              </span>
              <span className="text-gray-300">|</span>
              <span>
                {allImports.length} import(s)
              </span>
              {parsedModules[0]?.language && (
                <>
                  <span className="text-gray-300">|</span>
                  <span className="inline-flex items-center rounded-full bg-indigo-50 text-indigo-700 ring-1 ring-inset ring-indigo-200 px-2 py-0.5 text-xs font-medium">
                    {parsedModules[0].language}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-4 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('symbols')}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'symbols'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Symbols
            </button>
            <button
              onClick={() => setActiveTab('dependencies')}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'dependencies'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Dependencies ({allImports.length})
            </button>
          </div>

          {/* Symbols tab */}
          {activeTab === 'symbols' && (
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Symbol tree (left, ~40%) */}
              <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                  <h3 className="text-sm font-semibold text-gray-700">Symbol Browser</h3>
                </div>
                <div className="p-3 max-h-[600px] overflow-y-auto">
                  {parsedModules.map((mod) => (
                    <div key={mod.path}>
                      {parsedModules.length > 1 && (
                        <div className="px-2 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-100 mb-1">
                          {mod.path}
                        </div>
                      )}
                      <SymbolTree
                        symbols={mod.symbols}
                        onSelect={setSelectedSymbol}
                        selectedSymbol={selectedSymbol?.qualified_name}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Symbol detail (right, ~60%) */}
              <div className="lg:col-span-3 bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                  <h3 className="text-sm font-semibold text-gray-700">Symbol Detail</h3>
                </div>
                <div className="p-5 max-h-[600px] overflow-y-auto">
                  <SymbolDetail symbol={selectedSymbol} />
                </div>
              </div>
            </div>
          )}

          {/* Dependencies tab */}
          {activeTab === 'dependencies' && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <h3 className="text-sm font-semibold text-gray-700">Dependency Graph</h3>
              </div>
              <div className="p-5">
                {allImports.length > 0 ? (
                  <DependencyGraph
                    imports={allImports}
                    modulePath={primaryModulePath}
                  />
                ) : (
                  <EmptyState
                    title="No dependencies"
                    description="This module has no import dependencies to visualize."
                    icon={Network}
                  />
                )}
              </div>

              {/* Import table */}
              {allImports.length > 0 && (
                <div className="border-t border-gray-200">
                  <div className="px-4 py-3 bg-gray-50">
                    <h4 className="text-sm font-semibold text-gray-700">Import Details</h4>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500">
                            Source
                          </th>
                          <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500">
                            Target
                          </th>
                          <th className="text-left px-4 py-2 text-xs font-semibold text-gray-500">
                            Kind
                          </th>
                          <th className="text-center px-4 py-2 text-xs font-semibold text-gray-500">
                            External
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {allImports.map((imp, i) => (
                          <tr
                            key={i}
                            className={`border-b border-gray-100 ${
                              i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
                            }`}
                          >
                            <td className="px-4 py-2 font-mono text-gray-900">
                              {imp.source}
                            </td>
                            <td className="px-4 py-2 font-mono text-gray-700">
                              {imp.target}
                            </td>
                            <td className="px-4 py-2">
                              <span className="inline-flex items-center rounded-full bg-gray-100 text-gray-700 ring-1 ring-inset ring-gray-200 px-2 py-0.5 text-xs font-medium">
                                {imp.kind}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-center">
                              {imp.is_external ? (
                                <span className="inline-flex items-center rounded-full bg-orange-50 text-orange-700 ring-1 ring-inset ring-orange-200 px-2 py-0.5 text-xs font-medium">
                                  external
                                </span>
                              ) : (
                                <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-200 px-2 py-0.5 text-xs font-medium">
                                  internal
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Initial empty state */}
      {parsedModules.length === 0 && !mutation.isPending && !mutation.error && (
        <EmptyState
          title="No files parsed yet"
          description="Enter a file path above and click Parse to explore its intermediate representation."
          icon={Network}
        />
      )}
    </div>
  );
}
