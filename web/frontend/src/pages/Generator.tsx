import { useState, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Wand2,
  Loader2,
  Save,
  FolderOpen,
  Sparkles,
  Upload,
  Eye,
  Code,
  Trash2,
  CheckCircle2,
  AlertCircle,
  X,
} from 'lucide-react';
import {
  generateLibrary,
  saveDraft,
  listDrafts,
  deleteDraft,
  enrichContent,
  publishFromEditor,
} from '../api/client';
import type { Draft } from '../types';
import YamlEditor from '../components/YamlEditor';
import ValidationPanel from '../components/ValidationPanel';
import PreviewMode from '../components/PreviewMode';
import DiffView from '../components/DiffView';
import EmptyState from '../components/EmptyState';

type ViewMode = 'source' | 'preview';

interface ToastMessage {
  type: 'success' | 'error';
  text: string;
}

export default function Generator() {
  // Step 1: Source selection state
  const [repoPath, setRepoPath] = useState('');
  const [featureName, setFeatureName] = useState('');

  // Step 2: Editor state
  const [yamlContent, setYamlContent] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('source');

  // Draft management
  const [showDrafts, setShowDrafts] = useState(false);
  const [draftName, setDraftName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // Enrichment / diff state
  const [showDiff, setShowDiff] = useState(false);
  const [enrichedYaml, setEnrichedYaml] = useState('');
  const [enrichSuggestions, setEnrichSuggestions] = useState<string[]>([]);

  // Toast notifications
  const [toast, setToast] = useState<ToastMessage | null>(null);

  const queryClient = useQueryClient();

  // Show toast with auto-dismiss
  const showToast = useCallback((type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4000);
  }, []);

  // -----------------------------------------------------------------------
  // Step 1: Generate from repo
  // -----------------------------------------------------------------------
  const generateMutation = useMutation({
    mutationFn: () => generateLibrary(repoPath, featureName, true),
    onSuccess: (data) => {
      if (data.success && data.output_path) {
        showToast('success', `Library generated at ${data.output_path}`);
        // The API generates a file; we show a message to user
        // In a real scenario we might read the file content back
        setYamlContent(getDefaultTemplate(featureName));
      } else {
        showToast('error', data.message || 'Generation failed');
      }
    },
    onError: (err) => {
      showToast('error', err instanceof Error ? err.message : 'Generation failed');
      // Provide a template so user can still work
      setYamlContent(getDefaultTemplate(featureName));
    },
  });

  // -----------------------------------------------------------------------
  // Draft operations
  // -----------------------------------------------------------------------
  const draftsQuery = useQuery({
    queryKey: ['drafts'],
    queryFn: listDrafts,
    enabled: showDrafts,
  });

  const saveDraftMutation = useMutation({
    mutationFn: (params: { name: string; yaml: string }) =>
      saveDraft(params.name, params.yaml),
    onSuccess: () => {
      showToast('success', 'Draft saved successfully');
      setShowSaveDialog(false);
      setDraftName('');
      queryClient.invalidateQueries({ queryKey: ['drafts'] });
    },
    onError: (err) => {
      showToast('error', err instanceof Error ? err.message : 'Failed to save draft');
    },
  });

  const deleteDraftMutation = useMutation({
    mutationFn: (id: string) => deleteDraft(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drafts'] });
      showToast('success', 'Draft deleted');
    },
    onError: (err) => {
      showToast('error', err instanceof Error ? err.message : 'Failed to delete draft');
    },
  });

  // -----------------------------------------------------------------------
  // Enrich with AI
  // -----------------------------------------------------------------------
  const enrichMutation = useMutation({
    mutationFn: () => enrichContent(yamlContent),
    onSuccess: (data) => {
      setEnrichedYaml(data.enriched_yaml);
      setEnrichSuggestions(data.suggestions);
      setShowDiff(true);
    },
    onError: (err) => {
      showToast('error', err instanceof Error ? err.message : 'Enrichment failed');
    },
  });

  // -----------------------------------------------------------------------
  // Publish
  // -----------------------------------------------------------------------
  const publishMutation = useMutation({
    mutationFn: () => publishFromEditor(yamlContent, featureName || undefined),
    onSuccess: (entry) => {
      showToast('success', `Published "${entry.name}" v${entry.version} to registry`);
    },
    onError: (err) => {
      showToast('error', err instanceof Error ? err.message : 'Publish failed');
    },
  });

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------
  const handleLoadDraft = (draft: Draft) => {
    setYamlContent(draft.yaml_content);
    setFeatureName(draft.name);
    setShowDrafts(false);
    showToast('success', `Loaded draft "${draft.name}"`);
  };

  const handleAcceptEnrichment = () => {
    setYamlContent(enrichedYaml);
    setShowDiff(false);
    setEnrichedYaml('');
    setEnrichSuggestions([]);
    showToast('success', 'Enrichment changes accepted');
  };

  const handleRejectEnrichment = () => {
    setShowDiff(false);
    setEnrichedYaml('');
    setEnrichSuggestions([]);
  };

  const handleGenerate = () => {
    if (repoPath && featureName) {
      generateMutation.mutate();
    } else if (featureName) {
      // No repo path -- just create a template
      setYamlContent(getDefaultTemplate(featureName));
    }
  };

  return (
    <div>
      {/* Toast notification */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg border transition-all ${
            toast.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          {toast.type === 'success' ? (
            <CheckCircle2 size={16} className="text-emerald-600" />
          ) : (
            <AlertCircle size={16} className="text-red-600" />
          )}
          <span className="text-sm font-medium">{toast.text}</span>
          <button
            onClick={() => setToast(null)}
            className="ml-2 text-gray-400 hover:text-gray-600"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Wand2 size={24} className="text-indigo-600" />
          Library Generator
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Generate, edit, validate, and publish Agentic Library specifications
        </p>
      </div>

      {/* Step 1: Source Selection */}
      {!yamlContent && !showDiff && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Source Selection</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label
                htmlFor="gen-repo-path"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Repository Path
              </label>
              <input
                id="gen-repo-path"
                type="text"
                placeholder="/path/to/repository"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <div>
              <label
                htmlFor="gen-feature-name"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Feature / Library Name
              </label>
              <input
                id="gen-feature-name"
                type="text"
                placeholder="e.g. auth-middleware"
                value={featureName}
                onChange={(e) => setFeatureName(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerate}
              disabled={!featureName || generateMutation.isPending}
              className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generateMutation.isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Wand2 size={16} />
              )}
              Generate Draft
            </button>

            <span className="text-sm text-gray-400">or</span>

            <button
              onClick={() => setYamlContent(getDefaultTemplate(featureName || 'my-library'))}
              className="flex items-center gap-2 px-4 py-2.5 text-gray-700 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Code size={16} />
              Start from Template
            </button>

            <button
              onClick={() => setShowDrafts(true)}
              className="flex items-center gap-2 px-4 py-2.5 text-gray-700 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <FolderOpen size={16} />
              Load Draft
            </button>
          </div>

          {/* Generate error */}
          {generateMutation.error && !generateMutation.isPending && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
              <p className="text-sm text-red-700">
                {generateMutation.error instanceof Error
                  ? generateMutation.error.message
                  : 'An error occurred'}
              </p>
            </div>
          )}

          {/* Generate loading */}
          {generateMutation.isPending && (
            <div className="flex items-center gap-2 mt-4 text-sm text-gray-600">
              <Loader2 size={16} className="animate-spin text-indigo-600" />
              Analyzing repository and generating library...
            </div>
          )}
        </div>
      )}

      {/* Drafts modal */}
      {showDrafts && (
        <DraftsModal
          drafts={draftsQuery.data ?? []}
          isLoading={draftsQuery.isLoading}
          onSelect={handleLoadDraft}
          onDelete={(id) => deleteDraftMutation.mutate(id)}
          onClose={() => setShowDrafts(false)}
        />
      )}

      {/* Save draft dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl border border-gray-200 p-6 w-full max-w-md shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Save Draft</h3>
            <label
              htmlFor="draft-name-input"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Draft Name
            </label>
            <input
              id="draft-name-input"
              type="text"
              placeholder="e.g. my-library-draft"
              value={draftName}
              onChange={(e) => setDraftName(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowSaveDialog(false);
                  setDraftName('');
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  saveDraftMutation.mutate({
                    name: draftName || featureName || 'untitled',
                    yaml: yamlContent,
                  })
                }
                disabled={saveDraftMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {saveDraftMutation.isPending && (
                  <Loader2 size={14} className="animate-spin" />
                )}
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Editor + Validation (Steps 2-5) */}
      {yamlContent && !showDiff && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Editor/Preview (2 cols) */}
          <div className="lg:col-span-2 space-y-4">
            {/* Actions bar */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center justify-between flex-wrap gap-3">
                {/* View toggle */}
                <div className="flex items-center rounded-lg border border-gray-300 overflow-hidden">
                  <button
                    onClick={() => setViewMode('source')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === 'source'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Code size={14} />
                    Source
                  </button>
                  <button
                    onClick={() => setViewMode('preview')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors ${
                      viewMode === 'preview'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Eye size={14} />
                    Preview
                  </button>
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={() => {
                      setDraftName(featureName || '');
                      setShowSaveDialog(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <Save size={14} />
                    Save Draft
                  </button>

                  <button
                    onClick={() => setShowDrafts(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <FolderOpen size={14} />
                    Load Draft
                  </button>

                  <button
                    onClick={() => enrichMutation.mutate()}
                    disabled={enrichMutation.isPending || !yamlContent.trim()}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {enrichMutation.isPending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Sparkles size={14} />
                    )}
                    Enhance with AI
                  </button>

                  <button
                    onClick={() => publishMutation.mutate()}
                    disabled={publishMutation.isPending || !yamlContent.trim()}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {publishMutation.isPending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Upload size={14} />
                    )}
                    Publish to Registry
                  </button>

                  <button
                    onClick={() => {
                      setYamlContent('');
                      setViewMode('source');
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
                    title="Clear editor and start over"
                  >
                    <X size={14} />
                  </button>
                </div>
              </div>
            </div>

            {/* Editor or Preview */}
            {viewMode === 'source' ? (
              <YamlEditor
                value={yamlContent}
                onChange={setYamlContent}
              />
            ) : (
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
                <PreviewMode yamlContent={yamlContent} />
              </div>
            )}
          </div>

          {/* Right: Validation Panel (1 col) */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl border border-gray-200 p-4 sticky top-8">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Validation</h3>
              <ValidationPanel yamlContent={yamlContent} />
            </div>
          </div>
        </div>
      )}

      {/* Diff view for enrichment */}
      {showDiff && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={18} className="text-indigo-600" />
            <h2 className="text-lg font-semibold text-gray-900">AI Enhancement Preview</h2>
          </div>
          <DiffView
            original={yamlContent}
            enriched={enrichedYaml}
            suggestions={enrichSuggestions}
            onAccept={handleAcceptEnrichment}
            onReject={handleRejectEnrichment}
          />
        </div>
      )}

      {/* Empty state when no content and not generating */}
      {!yamlContent && !showDiff && !generateMutation.isPending && (
        <div className="mt-8">
          <EmptyState
            title="No library in editor"
            description="Generate a draft from a repository, start from a template, or load a saved draft to begin editing."
            icon={Wand2}
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Drafts modal sub-component
// ---------------------------------------------------------------------------

function DraftsModal({
  drafts,
  isLoading,
  onSelect,
  onDelete,
  onClose,
}: {
  drafts: Draft[];
  isLoading: boolean;
  onSelect: (draft: Draft) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl border border-gray-200 w-full max-w-lg shadow-xl max-h-[80vh] flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Saved Drafts</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 size={24} className="animate-spin text-indigo-600" />
            </div>
          )}

          {!isLoading && drafts.length === 0 && (
            <div className="text-center py-8">
              <p className="text-sm text-gray-500">No saved drafts yet</p>
            </div>
          )}

          {!isLoading && drafts.length > 0 && (
            <div className="space-y-2">
              {drafts.map((draft) => (
                <div
                  key={draft.id}
                  className="flex items-center justify-between px-4 py-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors group"
                >
                  <button
                    onClick={() => onSelect(draft)}
                    className="flex-1 text-left min-w-0"
                  >
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {draft.name}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {draft.updated_at
                        ? `Updated ${new Date(draft.updated_at).toLocaleDateString()} ${new Date(draft.updated_at).toLocaleTimeString()}`
                        : 'No date'}
                    </p>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(draft.id);
                    }}
                    className="ml-2 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-all"
                    title="Delete draft"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-gray-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Default template
// ---------------------------------------------------------------------------

function getDefaultTemplate(name: string): string {
  return `agentic_library:
  manifest:
    name: "${name}"
    version: "1.0.0"
    spec_version: "1.0"
    description: "A brief description of what this library does"
    complexity: simple
    tags:
      - utility
    language_agnostic: true

  overview: |
    Provide a high-level overview of the library's purpose
    and how an AI agent should approach implementing it.

  instructions:
    - step: 1
      title: "Set up the foundation"
      description: "Create the initial project structure and dependencies"
      code_sketch: |
        # Pseudocode for step 1
      notes: ""

    - step: 2
      title: "Implement core logic"
      description: "Build the main functionality"
      code_sketch: |
        # Pseudocode for step 2
      notes: ""

  guardrails:
    - rule: "Follow the target project's existing code style and conventions"
      severity: must
      rationale: "Consistency with existing code reduces maintenance burden"

    - rule: "Use the target project's existing dependencies where possible"
      severity: should
      rationale: "Minimizes additional dependency footprint"

    - rule: "Include error handling appropriate to the target project's patterns"
      severity: must
      rationale: "Robust error handling prevents runtime failures"

  validation:
    - description: "Feature works as described in the overview"
      test_approach: "Write a test that exercises the primary use case"
      expected_behavior: "Test passes without errors"

  capability_dependencies: []
`;
}
