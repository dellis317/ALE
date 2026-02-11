import { useState, useRef, useEffect, useCallback } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  MessageSquare,
  Mic,
  MicOff,
  Send,
  Loader2,
  AlertTriangle,
  Lock,
  ChevronDown,
  ChevronRight,
  Clock,
  User,
} from 'lucide-react';
import { submitAIQuery, getAIQueryInsights } from '../api/client';
import type { AIQueryResponse, AIQueryHistoryEntry, ModerationErrorDetail } from '../types';

interface AIQueryPanelProps {
  repoPath: string;
  libraryName: string;
  componentName: string;
  candidateDescription: string;
  candidateTags: string[];
  sourceFiles: string[];
  contextSummary: string;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// Web Speech API type augmentation
interface SpeechRecognitionEvent extends Event {
  results: { [index: number]: { [index: number]: { transcript: string } } };
}

export default function AIQueryPanel({
  repoPath,
  libraryName,
  componentName,
  candidateDescription,
  candidateTags,
  sourceFiles,
  contextSummary,
}: AIQueryPanelProps) {
  const [prompt, setPrompt] = useState('');
  const [inputMethod, setInputMethod] = useState<'text' | 'voice'>('text');
  const [isListening, setIsListening] = useState(false);
  const [lastResponse, setLastResponse] = useState<AIQueryResponse | null>(null);
  const [moderationError, setModerationError] = useState<ModerationErrorDetail | null>(null);
  const [insightsExpanded, setInsightsExpanded] = useState(false);
  const recognitionRef = useRef<ReturnType<typeof createRecognition> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Check for Web Speech API support
  const speechSupported = typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);

  // Fetch past insights for this component
  const insightsQuery = useQuery({
    queryKey: ['ai-query-insights', libraryName, componentName],
    queryFn: () => getAIQueryInsights(libraryName, componentName, 10),
    staleTime: 30_000,
  });

  const insights: AIQueryHistoryEntry[] = insightsQuery.data ?? [];

  // Submit query mutation
  const queryMutation = useMutation({
    mutationFn: () =>
      submitAIQuery({
        repo_url: repoPath,
        library_name: libraryName,
        component_name: componentName,
        prompt,
        input_method: inputMethod,
        candidate_description: candidateDescription,
        candidate_tags: candidateTags,
        source_files: sourceFiles,
        context_summary: contextSummary,
      }),
    onSuccess: (data) => {
      setLastResponse(data);
      setModerationError(null);
      setPrompt('');
      // Refresh insights after successful query
      insightsQuery.refetch();
    },
    onError: (error: unknown) => {
      // Parse moderation errors from 422/423 responses
      if (error && typeof error === 'object' && 'status' in error) {
        const apiErr = error as { status: number; message: string };
        if (apiErr.status === 422 || apiErr.status === 423) {
          try {
            const detail = JSON.parse(apiErr.message);
            setModerationError({
              reason: detail.reason,
              violation_type: detail.violation_type,
              is_locked: detail.is_locked ?? apiErr.status === 423,
            });
          } catch {
            setModerationError({
              reason: apiErr.message,
              violation_type: 'unknown',
              is_locked: apiErr.status === 423,
            });
          }
          return;
        }
      }
      setModerationError(null);
    },
  });

  const handleSubmit = useCallback(() => {
    if (!prompt.trim() || queryMutation.isPending) return;
    setModerationError(null);
    queryMutation.mutate();
  }, [prompt, queryMutation]);

  // Speech recognition helpers
  function createRecognition() {
    const SR = (window as unknown as Record<string, unknown>).SpeechRecognition ||
      (window as unknown as Record<string, unknown>).webkitSpeechRecognition;
    if (!SR) return null;
    const recognition = new (SR as new () => EventTarget & {
      continuous: boolean;
      interimResults: boolean;
      lang: string;
      start: () => void;
      stop: () => void;
      onresult: ((e: SpeechRecognitionEvent) => void) | null;
      onerror: ((e: Event) => void) | null;
      onend: (() => void) | null;
    })();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    return recognition;
  }

  const toggleListening = useCallback(() => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const recognition = createRecognition();
    if (!recognition) return;

    recognitionRef.current = recognition;

    recognition.onresult = (e: SpeechRecognitionEvent) => {
      const transcript = e.results[0][0].transcript;
      setPrompt(transcript);
      setInputMethod('voice');
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
    setIsListening(true);
    setInputMethod('voice');
  }, [isListening]);

  // Cleanup recognition on unmount
  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  const isLocked = moderationError?.is_locked ?? false;

  return (
    <div className="mt-4 border-t border-gray-100 pt-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare size={16} className="text-indigo-600" />
        <h4 className="text-sm font-semibold text-gray-700">
          Ask about this component
        </h4>
      </div>

      {/* Past Insights accordion */}
      {insights.length > 0 && (
        <div className="mb-3">
          <button
            onClick={() => setInsightsExpanded(!insightsExpanded)}
            className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors cursor-pointer"
          >
            {insightsExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <Clock size={12} />
            Past insights ({insights.length})
          </button>

          {insightsExpanded && (
            <div className="mt-2 space-y-2 max-h-64 overflow-y-auto">
              {insights.map((entry) => (
                <div
                  key={entry.id}
                  className="bg-gray-50 rounded-lg px-3 py-2 text-xs"
                >
                  <div className="font-medium text-gray-700 mb-1">
                    Q: {entry.prompt}
                  </div>
                  <div className="text-gray-600 mb-1 line-clamp-3">
                    A: {entry.response}
                  </div>
                  <div className="flex items-center gap-2 text-gray-400">
                    <User size={10} />
                    <span>@{entry.username}</span>
                    <span>{timeAgo(entry.timestamp)}</span>
                    {entry.input_method === 'voice' && (
                      <span className="flex items-center gap-0.5">
                        <Mic size={10} /> voice
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Account locked banner */}
      {isLocked && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 mb-3">
          <Lock size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-red-700">
            <span className="font-semibold">Account locked.</span>{' '}
            {moderationError?.reason || 'Your account has been locked due to repeated policy violations. Contact an administrator.'}
          </div>
        </div>
      )}

      {/* Input row */}
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          placeholder={
            isLocked
              ? 'Your account is locked'
              : isListening
                ? 'Listening...'
                : 'Ask a question about this component...'
          }
          value={prompt}
          onChange={(e) => {
            setPrompt(e.target.value);
            setInputMethod('text');
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          disabled={isLocked || queryMutation.isPending}
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
        />

        {/* Mic button */}
        {speechSupported && (
          <button
            onClick={toggleListening}
            disabled={isLocked || queryMutation.isPending}
            className={`p-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              isListening
                ? 'bg-red-100 text-red-600 hover:bg-red-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
            title={isListening ? 'Stop listening' : 'Voice input'}
          >
            {isListening ? <MicOff size={16} /> : <Mic size={16} />}
          </button>
        )}

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={!prompt.trim() || isLocked || queryMutation.isPending}
          className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Submit question"
        >
          {queryMutation.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Send size={16} />
          )}
        </button>
      </div>

      {/* Moderation warning (non-locked) */}
      {moderationError && !isLocked && (
        <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5 mt-2">
          <AlertTriangle size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-700">
            <span className="font-semibold">Warning:</span>{' '}
            {moderationError.reason}{' '}
            <span className="text-amber-500">
              This is your first warning. A second violation will lock your account.
            </span>
          </div>
        </div>
      )}

      {/* Non-moderation errors */}
      {queryMutation.error && !moderationError && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 mt-2">
          <p className="text-sm text-red-700">
            {queryMutation.error instanceof Error
              ? queryMutation.error.message
              : 'An error occurred while processing your query.'}
          </p>
        </div>
      )}

      {/* Response display */}
      {lastResponse && (
        <div className="mt-3 bg-indigo-50/50 border border-indigo-100 rounded-lg px-4 py-3">
          <div className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
            {lastResponse.response}
          </div>
          <div className="flex items-center gap-3 mt-2 pt-2 border-t border-indigo-100 text-xs text-gray-400">
            <span>{lastResponse.model}</span>
            <span>{lastResponse.tokens_used.toLocaleString()} tokens</span>
            <span>${lastResponse.cost_estimate.toFixed(4)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
