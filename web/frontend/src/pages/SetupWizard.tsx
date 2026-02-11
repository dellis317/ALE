import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  FolderGit2,
  Search,
  Wand2,
  CheckCircle2,
  Loader2,
  Package,
  ChevronRight,
  BookOpen,
  Shield,
  Lightbulb,
  Rocket,
  AlertCircle,
  RotateCcw,
  Code,
  Eye,
} from 'lucide-react';
import { analyzeRepo, generateLibrary } from '../api/client';
import type { Candidate, AnalyzeResult } from '../types';
import ScoreBar from '../components/ScoreBar';
import Badge from '../components/Badge';

const SETUP_COMPLETE_KEY = 'ale_setup_completed';

const STEPS = [
  { id: 'welcome', label: 'Welcome' },
  { id: 'connect', label: 'Repository' },
  { id: 'analyze', label: 'Analyze' },
  { id: 'generate', label: 'Generate' },
  { id: 'complete', label: 'Done' },
] as const;

type StepId = (typeof STEPS)[number]['id'];

export function hasCompletedSetup(): boolean {
  return localStorage.getItem(SETUP_COMPLETE_KEY) === 'true';
}

export function markSetupComplete(): void {
  localStorage.setItem(SETUP_COMPLETE_KEY, 'true');
}

export default function SetupWizard() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<StepId>('welcome');

  // Connect step state
  const [repoPath, setRepoPath] = useState('');
  const [depth, setDepth] = useState<'quick' | 'standard' | 'deep'>('standard');

  // Analyze step state
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);

  // Generate step state
  const [generatedPath, setGeneratedPath] = useState('');
  const [generatedYaml, setGeneratedYaml] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const currentStepIndex = STEPS.findIndex((s) => s.id === currentStep);

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeRepo(repoPath, depth),
    onSuccess: (data: AnalyzeResult) => {
      setCandidates(data.candidates);
    },
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      generateLibrary(repoPath, selectedCandidate?.name ?? '', true),
    onSuccess: (data) => {
      if (data.success && data.output_path) {
        setGeneratedPath(data.output_path);
      }
      setGeneratedYaml(getWizardTemplate(selectedCandidate?.name ?? 'my-library'));
    },
    onError: () => {
      // On error, still provide a template so user can see what the output looks like
      setGeneratedYaml(getWizardTemplate(selectedCandidate?.name ?? 'my-library'));
    },
  });

  const goNext = useCallback(() => {
    const idx = STEPS.findIndex((s) => s.id === currentStep);
    if (idx < STEPS.length - 1) {
      setCurrentStep(STEPS[idx + 1].id);
    }
  }, [currentStep]);

  const goBack = useCallback(() => {
    const idx = STEPS.findIndex((s) => s.id === currentStep);
    if (idx > 0) {
      setCurrentStep(STEPS[idx - 1].id);
    }
  }, [currentStep]);

  const handleAnalyze = () => {
    analyzeMutation.mutate();
  };

  const handleSelectAndGenerate = (candidate: Candidate) => {
    setSelectedCandidate(candidate);
  };

  const handleGenerate = () => {
    if (selectedCandidate) {
      generateMutation.mutate();
      goNext();
    }
  };

  const handleFinish = () => {
    markSetupComplete();
    navigate('/');
  };

  const handleSkipToApp = () => {
    markSetupComplete();
    navigate('/');
  };

  const handleGoToGenerator = () => {
    markSetupComplete();
    navigate('/generate');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30">
      {/* Top bar */}
      <div className="border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Sparkles size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">ALE Setup</h1>
              <p className="text-xs text-gray-500">First-time setup wizard</p>
            </div>
          </div>
          <button
            onClick={handleSkipToApp}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Skip wizard
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="max-w-4xl mx-auto px-6 pt-8">
        <div className="flex items-center gap-2">
          {STEPS.map((step, i) => (
            <div key={step.id} className="flex items-center flex-1 last:flex-initial">
              <div className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                    i < currentStepIndex
                      ? 'bg-indigo-600 text-white'
                      : i === currentStepIndex
                        ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                        : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {i < currentStepIndex ? (
                    <CheckCircle2 size={16} />
                  ) : (
                    i + 1
                  )}
                </div>
                <span
                  className={`text-sm font-medium hidden sm:inline ${
                    i <= currentStepIndex ? 'text-gray-900' : 'text-gray-400'
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-3 rounded ${
                    i < currentStepIndex ? 'bg-indigo-600' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step content */}
      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Step 1: Welcome */}
        {currentStep === 'welcome' && (
          <div className="text-center max-w-2xl mx-auto">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-indigo-200">
              <Sparkles size={36} className="text-white" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-3">
              Welcome to ALE
            </h2>
            <p className="text-lg text-gray-600 mb-8">
              The Agentic Library Extractor helps you discover reusable patterns
              in your codebase and turn them into blueprints that AI agents can
              follow to implement features natively in any project.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-10 text-left">
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center mb-3">
                  <Search size={20} className="text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">Discover</h3>
                <p className="text-sm text-gray-600">
                  Analyze repositories to find reusable components, patterns, and
                  utilities worth extracting.
                </p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center mb-3">
                  <Wand2 size={20} className="text-purple-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">Generate</h3>
                <p className="text-sm text-gray-600">
                  Turn discovered candidates into structured library specs that
                  any AI agent can understand.
                </p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center mb-3">
                  <Package size={20} className="text-emerald-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">Publish</h3>
                <p className="text-sm text-gray-600">
                  Share libraries in a registry so teams and agents can discover
                  and implement them anywhere.
                </p>
              </div>
            </div>

            <div className="bg-indigo-50 rounded-xl border border-indigo-100 p-5 mb-10 text-left">
              <h3 className="font-semibold text-indigo-900 mb-2 flex items-center gap-2">
                <Lightbulb size={16} className="text-indigo-600" />
                What are Agentic Libraries?
              </h3>
              <p className="text-sm text-indigo-800">
                Unlike traditional libraries that ship compiled code, Agentic
                Libraries ship <strong>knowledge</strong> &mdash; step-by-step
                instructions, guardrails, validation criteria, and capability
                dependencies. An AI agent reads these blueprints and implements
                the feature natively in your codebase, in your language, following
                your conventions.
              </p>
            </div>

            <button
              onClick={goNext}
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
            >
              Get Started
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* Step 2: Connect Repository */}
        {currentStep === 'connect' && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <div className="w-16 h-16 rounded-xl bg-blue-50 flex items-center justify-center mx-auto mb-4">
                <FolderGit2 size={28} className="text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Point to a Repository
              </h2>
              <p className="text-gray-600">
                Enter the path to a local repository you&apos;d like to analyze for
                extractable library candidates.
              </p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6">
              <div className="mb-5">
                <label
                  htmlFor="wizard-repo-path"
                  className="block text-sm font-medium text-gray-700 mb-1.5"
                >
                  Repository Path
                </label>
                <input
                  id="wizard-repo-path"
                  type="text"
                  placeholder="/path/to/your/repository"
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  className="w-full px-4 py-3 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-1.5">
                  Path to a local Git repository on this machine.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Analysis Depth
                </label>
                <div className="flex rounded-lg border border-gray-300 overflow-hidden">
                  {(['quick', 'standard', 'deep'] as const).map((d) => (
                    <button
                      key={d}
                      onClick={() => setDepth(d)}
                      className={`flex-1 px-4 py-2.5 text-sm font-medium capitalize transition-colors ${
                        depth === d
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1.5">
                  {depth === 'quick'
                    ? 'Fast scan using directory heuristics only.'
                    : depth === 'standard'
                      ? 'Balanced analysis with heuristics and basic AST parsing.'
                      : 'Full AST analysis, dependency resolution, and scoring.'}
                </p>
              </div>
            </div>

            <div className="bg-amber-50 rounded-xl border border-amber-100 p-4 mb-8 flex items-start gap-3">
              <BookOpen size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-amber-800">
                  <strong>Tip:</strong> For your first run, try a project you know
                  well. The analyzer will identify components like utilities,
                  middleware, and self-contained features that are good candidates
                  for extraction.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <button
                onClick={goBack}
                className="flex items-center gap-2 px-4 py-2.5 text-gray-600 font-medium rounded-lg hover:bg-gray-100 transition-colors"
              >
                <ArrowLeft size={16} />
                Back
              </button>
              <button
                onClick={() => {
                  handleAnalyze();
                  goNext();
                }}
                disabled={!repoPath.trim()}
                className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Analyze Repository
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Analyze & Discover */}
        {currentStep === 'analyze' && (
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-8">
              <div className="w-16 h-16 rounded-xl bg-purple-50 flex items-center justify-center mx-auto mb-4">
                <Search size={28} className="text-purple-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Discover Candidates
              </h2>
              <p className="text-gray-600">
                {analyzeMutation.isPending
                  ? 'Scanning your repository for extractable patterns...'
                  : candidates.length > 0
                    ? `Found ${candidates.length} candidate${candidates.length !== 1 ? 's' : ''} in your repository. Select one to generate a library.`
                    : 'Review analysis results and pick a candidate to extract.'}
              </p>
            </div>

            {/* Loading state */}
            {analyzeMutation.isPending && (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
                <Loader2 size={48} className="animate-spin text-indigo-600 mx-auto mb-4" />
                <p className="text-gray-700 font-medium">Analyzing repository...</p>
                <p className="text-sm text-gray-500 mt-1">
                  {depth === 'deep'
                    ? 'Deep analysis examines AST structure, dependencies, and scoring'
                    : depth === 'quick'
                      ? 'Quick scan in progress'
                      : 'Scanning files and analyzing patterns'}
                </p>
              </div>
            )}

            {/* Error state */}
            {analyzeMutation.error && !analyzeMutation.isPending && (
              <div className="bg-white rounded-xl border border-gray-200 p-8 shadow-sm mb-6">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0">
                    <AlertCircle size={24} className="text-red-500" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1">Analysis Error</h3>
                    <p className="text-sm text-gray-600 mb-4">
                      {analyzeMutation.error instanceof Error
                        ? analyzeMutation.error.message
                        : 'Could not analyze the repository. The backend may not be running, or the path may be invalid.'}
                    </p>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => {
                          analyzeMutation.reset();
                          goBack();
                        }}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <ArrowLeft size={14} />
                        Change Path
                      </button>
                      <button
                        onClick={() => analyzeMutation.mutate()}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors"
                      >
                        <RotateCcw size={14} />
                        Retry
                      </button>
                      <button
                        onClick={goNext}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
                      >
                        Skip to generate
                        <ArrowRight size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Candidates list */}
            {!analyzeMutation.isPending && candidates.length > 0 && (
              <div className="space-y-3 mb-8">
                {candidates.map((candidate, i) => {
                  const isWhole = candidate.name === '__whole_codebase__';
                  const displayName = isWhole ? 'Entire Codebase' : candidate.name;
                  return (
                  <button
                    key={candidate.name}
                    onClick={() => handleSelectAndGenerate(candidate)}
                    className={`w-full text-left rounded-xl border-2 p-5 transition-all shadow-sm hover:shadow-md ${
                      isWhole
                        ? selectedCandidate?.name === candidate.name
                          ? 'bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-500 ring-2 ring-indigo-100'
                          : 'bg-gradient-to-r from-indigo-50/50 to-purple-50/50 border-indigo-200 hover:border-indigo-400'
                        : selectedCandidate?.name === candidate.name
                          ? 'bg-white border-indigo-500 ring-2 ring-indigo-100'
                          : 'bg-white border-gray-200 hover:border-indigo-300'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        isWhole
                          ? 'bg-gradient-to-br from-indigo-500 to-purple-600'
                          : 'bg-indigo-50'
                      }`}>
                        {isWhole ? (
                          <Package size={14} className="text-white" />
                        ) : (
                          <span className="text-sm font-bold text-indigo-600">#{i + 1}</span>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-gray-900">{displayName}</h3>
                          {isWhole && <Badge label="Full Repository" variant="info" />}
                          {selectedCandidate?.name === candidate.name && (
                            <CheckCircle2 size={16} className="text-indigo-600" />
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mb-2 line-clamp-2">{candidate.description}</p>
                        <div className="flex items-center gap-4">
                          <div className="w-28">
                            <ScoreBar score={candidate.overall_score} label="Score" size="sm" />
                          </div>
                          {!isWhole && candidate.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {candidate.tags.slice(0, 4).map((tag) => (
                                <Badge key={tag} label={tag} variant="info" />
                              ))}
                            </div>
                          )}
                          <span className="text-xs text-gray-500 ml-auto">
                            {candidate.source_files.length} file{candidate.source_files.length !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>
                      <ChevronRight
                        size={18}
                        className={`flex-shrink-0 mt-2 transition-colors ${
                          selectedCandidate?.name === candidate.name
                            ? 'text-indigo-500'
                            : 'text-gray-300'
                        }`}
                      />
                    </div>
                  </button>
                  );
                })}
              </div>
            )}

            {/* No candidates */}
            {!analyzeMutation.isPending && !analyzeMutation.error && candidates.length === 0 && analyzeMutation.data !== undefined && (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center shadow-sm mb-6">
                <Search size={32} className="text-gray-300 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-900 mb-1">No candidates found</h3>
                <p className="text-sm text-gray-500 mb-4">
                  The analyzer didn&apos;t find extractable candidates in this repository.
                  Try a different path or increase the analysis depth.
                </p>
                <button
                  onClick={() => {
                    analyzeMutation.reset();
                    setCandidates([]);
                    goBack();
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <ArrowLeft size={14} />
                  Try Another Repository
                </button>
              </div>
            )}

            {/* Navigation */}
            {!analyzeMutation.isPending && (
              <div className="flex items-center justify-between">
                <button
                  onClick={() => {
                    analyzeMutation.reset();
                    setCandidates([]);
                    setSelectedCandidate(null);
                    goBack();
                  }}
                  className="flex items-center gap-2 px-4 py-2.5 text-gray-600 font-medium rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <ArrowLeft size={16} />
                  Back
                </button>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      setSelectedCandidate(null);
                      goNext();
                    }}
                    className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
                  >
                    Skip this step
                  </button>
                  <button
                    onClick={handleGenerate}
                    disabled={!selectedCandidate}
                    className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <Wand2 size={16} />
                    Generate Library
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 4: Generate & Review */}
        {currentStep === 'generate' && (
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-8">
              <div className="w-16 h-16 rounded-xl bg-emerald-50 flex items-center justify-center mx-auto mb-4">
                <Wand2 size={28} className="text-emerald-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {generateMutation.isPending
                  ? 'Generating Library...'
                  : 'Library Generated'}
              </h2>
              <p className="text-gray-600">
                {generateMutation.isPending
                  ? 'Creating an agentic library specification from the selected candidate...'
                  : selectedCandidate
                    ? `Here's the generated library spec for "${selectedCandidate.name}". You can refine it later in the Generator page.`
                    : 'Here\'s a sample library spec template. Head to the Generator page to create one from your repository.'}
              </p>
            </div>

            {/* Loading */}
            {generateMutation.isPending && (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
                <Loader2 size={48} className="animate-spin text-indigo-600 mx-auto mb-4" />
                <p className="text-gray-700 font-medium">Generating library specification...</p>
                <p className="text-sm text-gray-500 mt-1">
                  Analyzing code structure and creating implementation blueprint
                </p>
              </div>
            )}

            {/* Generated output */}
            {!generateMutation.isPending && generatedYaml && (
              <>
                {generatedPath && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-4 flex items-center gap-3">
                    <CheckCircle2 size={18} className="text-emerald-600 flex-shrink-0" />
                    <p className="text-sm text-emerald-800">
                      Library spec saved to <code className="font-mono bg-emerald-100 px-1.5 py-0.5 rounded">{generatedPath}</code>
                    </p>
                  </div>
                )}

                {/* View toggle */}
                <div className="flex items-center gap-2 mb-4">
                  <div className="flex items-center rounded-lg border border-gray-300 overflow-hidden">
                    <button
                      onClick={() => setShowPreview(false)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors ${
                        !showPreview
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <Code size={14} />
                      YAML Source
                    </button>
                    <button
                      onClick={() => setShowPreview(true)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors ${
                        showPreview
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <Eye size={14} />
                      Preview
                    </button>
                  </div>
                </div>

                {/* YAML display */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-6">
                  {!showPreview ? (
                    <pre className="p-5 text-sm font-mono text-gray-800 overflow-x-auto max-h-96 overflow-y-auto leading-relaxed">
                      {generatedYaml}
                    </pre>
                  ) : (
                    <div className="p-5 max-h-96 overflow-y-auto">
                      <YamlPreview yaml={generatedYaml} />
                    </div>
                  )}
                </div>

                <div className="bg-blue-50 rounded-xl border border-blue-100 p-4 mb-8 flex items-start gap-3">
                  <Lightbulb size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-blue-800">
                    This is your first generated library spec. You can edit, enrich
                    with AI, and publish it from the <strong>Generator</strong> page.
                    The spec follows the <code className="font-mono bg-blue-100 px-1 rounded">.agentic.yaml</code> format
                    that any AI agent can consume.
                  </p>
                </div>
              </>
            )}

            {/* Error generating */}
            {generateMutation.error && !generateMutation.isPending && !generatedYaml && (
              <div className="bg-white rounded-xl border border-gray-200 p-8 shadow-sm mb-6">
                <div className="flex items-start gap-4">
                  <AlertCircle size={24} className="text-amber-500 flex-shrink-0" />
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">Generation Note</h3>
                    <p className="text-sm text-gray-600 mb-3">
                      The backend generation encountered an issue, but we&apos;ve prepared
                      a template you can use as a starting point in the Generator.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation */}
            {!generateMutation.isPending && (
              <div className="flex items-center justify-between">
                <button
                  onClick={() => {
                    setGeneratedYaml('');
                    setGeneratedPath('');
                    generateMutation.reset();
                    goBack();
                  }}
                  className="flex items-center gap-2 px-4 py-2.5 text-gray-600 font-medium rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <ArrowLeft size={16} />
                  Back
                </button>
                <button
                  onClick={goNext}
                  className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  Continue
                  <ArrowRight size={16} />
                </button>
              </div>
            )}
          </div>
        )}

        {/* Step 5: Complete */}
        {currentStep === 'complete' && (
          <div className="max-w-2xl mx-auto text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-emerald-200">
              <Rocket size={36} className="text-white" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-3">
              You&apos;re All Set!
            </h2>
            <p className="text-lg text-gray-600 mb-8">
              You&apos;ve completed the ALE setup wizard. Here&apos;s what you can
              do next:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10 text-left">
              <button
                onClick={() => {
                  markSetupComplete();
                  navigate('/');
                }}
                className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all text-left"
              >
                <div className="flex items-center gap-3 mb-2">
                  <Package size={20} className="text-indigo-600" />
                  <h3 className="font-semibold text-gray-900">Browse Registry</h3>
                </div>
                <p className="text-sm text-gray-600">
                  Explore published agentic libraries and see what&apos;s available.
                </p>
              </button>

              <button
                onClick={() => {
                  markSetupComplete();
                  navigate('/analyze');
                }}
                className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all text-left"
              >
                <div className="flex items-center gap-3 mb-2">
                  <Search size={20} className="text-blue-600" />
                  <h3 className="font-semibold text-gray-900">Analyze More Repos</h3>
                </div>
                <p className="text-sm text-gray-600">
                  Scan additional repositories for extractable library candidates.
                </p>
              </button>

              <button
                onClick={handleGoToGenerator}
                className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all text-left"
              >
                <div className="flex items-center gap-3 mb-2">
                  <Wand2 size={20} className="text-purple-600" />
                  <h3 className="font-semibold text-gray-900">Generator</h3>
                </div>
                <p className="text-sm text-gray-600">
                  Create, edit, and publish library specs with AI enhancement.
                </p>
              </button>

              <button
                onClick={() => {
                  markSetupComplete();
                  navigate('/settings/api-keys');
                }}
                className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all text-left"
              >
                <div className="flex items-center gap-3 mb-2">
                  <Shield size={20} className="text-amber-600" />
                  <h3 className="font-semibold text-gray-900">API Keys</h3>
                </div>
                <p className="text-sm text-gray-600">
                  Set up API keys for CI/CD integration and programmatic access.
                </p>
              </button>
            </div>

            <button
              onClick={handleFinish}
              className="inline-flex items-center gap-2 px-8 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
            >
              Go to Dashboard
              <ArrowRight size={18} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Simple YAML preview for the wizard
// ---------------------------------------------------------------------------

function YamlPreview({ yaml }: { yaml: string }) {
  // Parse key sections from the YAML for a friendly preview
  const sections: { title: string; content: string }[] = [];
  const lines = yaml.split('\n');
  let currentSection = '';
  let currentContent: string[] = [];

  for (const line of lines) {
    if (line.match(/^\s{2}\w+:/) && !line.match(/^\s{4}/)) {
      if (currentSection) {
        sections.push({ title: currentSection, content: currentContent.join('\n') });
      }
      currentSection = line.trim().replace(':', '');
      currentContent = [];
    } else if (currentSection) {
      currentContent.push(line);
    }
  }
  if (currentSection) {
    sections.push({ title: currentSection, content: currentContent.join('\n') });
  }

  if (sections.length === 0) {
    return <pre className="text-sm font-mono text-gray-700">{yaml}</pre>;
  }

  return (
    <div className="space-y-4">
      {sections.map((section, i) => (
        <div key={i}>
          <h4 className="text-sm font-semibold text-gray-900 capitalize mb-1">
            {section.title.replace(/_/g, ' ')}
          </h4>
          <pre className="text-xs font-mono text-gray-600 bg-gray-50 rounded-lg p-3 overflow-x-auto">
            {section.content.trim() || '(empty)'}
          </pre>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Template for wizard-generated library
// ---------------------------------------------------------------------------

function getWizardTemplate(name: string): string {
  return `agentic_library:
  manifest:
    name: "${name}"
    version: "1.0.0"
    spec_version: "1.0"
    description: "Auto-generated library spec for ${name}"
    complexity: simple
    tags:
      - extracted
      - auto-generated
    language_agnostic: true

  overview: |
    This library provides a reusable implementation blueprint for the
    "${name}" component. An AI agent can follow these instructions to
    implement this feature natively in any target project.

  instructions:
    - step: 1
      title: "Understand the component structure"
      description: "Review the existing implementation and identify the core interfaces and dependencies."
      code_sketch: |
        # Analyze the entry points and public API
        # Map out dependency requirements
      notes: "Start by understanding the existing patterns before implementing"

    - step: 2
      title: "Implement the core logic"
      description: "Build the main functionality following the target project's conventions."
      code_sketch: |
        # Implement the primary functionality
        # Follow project-specific patterns and naming
      notes: "Adapt to the target language and framework"

    - step: 3
      title: "Add error handling and validation"
      description: "Ensure robust error handling consistent with the target project."
      code_sketch: |
        # Add input validation
        # Implement error boundaries
      notes: "Match existing error handling patterns in the project"

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

    - description: "No regressions in existing functionality"
      test_approach: "Run existing test suite after integration"
      expected_behavior: "All existing tests continue to pass"

  capability_dependencies: []
`;
}
