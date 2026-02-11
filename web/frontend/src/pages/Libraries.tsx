import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  Loader2,
  Trash2,
  FolderTree,
  Calendar,
  GitBranch,
  FileText,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import {
  listGeneratedLibraries,
  deleteGeneratedLibrary,
  checkLibraryUpdates,
  updateLibrary,
  createLibraryFromLatest,
} from '../api/client';
import type { GeneratedLibrary, UpdateCheckResult } from '../types';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';
import UpdateCheckModal from '../components/UpdateCheckModal';

export default function Libraries() {
  const queryClient = useQueryClient();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [updateCheckResult, setUpdateCheckResult] = useState<UpdateCheckResult | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  const librariesQuery = useQuery({
    queryKey: ['generated-libraries'],
    queryFn: listGeneratedLibraries,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteGeneratedLibrary(id),
    onSuccess: () => {
      setDeletingId(null);
      queryClient.invalidateQueries({ queryKey: ['generated-libraries'] });
    },
    onError: () => {
      setDeletingId(null);
    },
  });

  const checkUpdatesMutation = useMutation({
    mutationFn: (id: string) => checkLibraryUpdates(id),
    onSuccess: (data) => {
      setCheckingId(null);
      setUpdateCheckResult(data);
      setCheckError(null);
    },
    onError: (err) => {
      setCheckingId(null);
      setCheckError(err instanceof Error ? err.message : 'Failed to check for updates');
    },
  });

  const updateMutation = useMutation({
    mutationFn: (id: string) => updateLibrary(id),
    onSuccess: () => {
      setUpdateCheckResult(null);
      queryClient.invalidateQueries({ queryKey: ['generated-libraries'] });
    },
  });

  const createFromLatestMutation = useMutation({
    mutationFn: ({ id, newName }: { id: string; newName: string }) =>
      createLibraryFromLatest(id, newName),
    onSuccess: () => {
      setUpdateCheckResult(null);
      queryClient.invalidateQueries({ queryKey: ['generated-libraries'] });
    },
  });

  const libraries = librariesQuery.data ?? [];

  const countSections = (lib: GeneratedLibrary): number => {
    let count = 0;
    const walk = (children: GeneratedLibrary['structure']['children']) => {
      for (const child of children) {
        count++;
        if (child.children) walk(child.children);
      }
    };
    walk(lib.structure.children);
    return count;
  };

  const handleCheckUpdates = (e: React.MouseEvent, libId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setCheckingId(libId);
    setCheckError(null);
    checkUpdatesMutation.mutate(libId);
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <BookOpen size={24} className="text-indigo-600" />
          Generated Libraries
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse and review hierarchical agentic library documents generated from analysis
        </p>
      </div>

      {/* Check error toast */}
      {checkError && (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm shadow-lg">
          <span>{checkError}</span>
          <button onClick={() => setCheckError(null)} className="text-red-400 hover:text-red-600 ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Loading */}
      {librariesQuery.isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={40} className="animate-spin text-indigo-600" />
        </div>
      )}

      {/* Error */}
      {librariesQuery.error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
          <h3 className="text-red-800 font-semibold mb-1">Error Loading Libraries</h3>
          <p className="text-sm text-red-700">
            {librariesQuery.error instanceof Error
              ? librariesQuery.error.message
              : 'An unknown error occurred'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!librariesQuery.isLoading && libraries.length === 0 && (
        <EmptyState
          title="No generated libraries yet"
          description="Use the Analyzer to analyze a repository, then click 'Generate Library' on any candidate to create a hierarchical library document."
          icon={BookOpen}
        />
      )}

      {/* Library cards */}
      {libraries.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {libraries.map((lib) => (
            <div
              key={lib.id}
              className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow group"
            >
              <Link to={`/libraries/${lib.id}`} className="block p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                      <FolderTree size={18} className="text-indigo-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">
                        {lib.name}
                      </h3>
                      <p className="text-xs text-gray-500">{lib.root_doc}</p>
                    </div>
                  </div>
                  <ChevronRight
                    size={16}
                    className="text-gray-400 group-hover:text-indigo-500 transition-colors mt-1"
                  />
                </div>

                <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                  {lib.structure.summary}
                </p>

                <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <FileText size={12} />
                    {countSections(lib)} sections
                  </span>
                  <span className="flex items-center gap-1">
                    <GitBranch size={12} />
                    {lib.candidate_name === '__whole_codebase__'
                      ? 'Full Codebase'
                      : lib.candidate_name}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar size={12} />
                    {new Date(lib.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div className="mt-3">
                  <Badge
                    label={
                      lib.candidate_name === '__whole_codebase__'
                        ? 'Codebase'
                        : 'Component'
                    }
                    variant={
                      lib.candidate_name === '__whole_codebase__'
                        ? 'info'
                        : 'success'
                    }
                  />
                </div>
              </Link>

              {/* Actions bar */}
              <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
                <button
                  onClick={(e) => handleCheckUpdates(e, lib.id)}
                  disabled={checkingId === lib.id}
                  className="flex items-center gap-1.5 text-xs text-indigo-500 hover:text-indigo-700 transition-colors disabled:opacity-50"
                  title="Check source repo for updates"
                >
                  {checkingId === lib.id ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <RefreshCw size={12} />
                  )}
                  Check for Updates
                </button>

                <button
                  onClick={() => {
                    setDeletingId(lib.id);
                    deleteMutation.mutate(lib.id);
                  }}
                  disabled={deletingId === lib.id}
                  className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50"
                  title="Delete library"
                >
                  {deletingId === lib.id ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <Trash2 size={12} />
                  )}
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Update Check Modal */}
      {updateCheckResult && (
        <UpdateCheckModal
          result={updateCheckResult}
          onClose={() => setUpdateCheckResult(null)}
          onUpdate={() => {
            if (updateCheckResult.library_id) {
              updateMutation.mutate(updateCheckResult.library_id);
            }
          }}
          onCreateFromLatest={(newName) => {
            if (updateCheckResult.library_id) {
              createFromLatestMutation.mutate({
                id: updateCheckResult.library_id,
                newName,
              });
            }
          }}
          isUpdating={updateMutation.isPending}
          isCreating={createFromLatestMutation.isPending}
        />
      )}
    </div>
  );
}
