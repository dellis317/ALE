import { useState } from 'react';
import {
  X,
  Key,
  Server,
  Shield,
  Terminal,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  ExternalLink,
} from 'lucide-react';

const DEPLOY_GUIDE_KEY = 'ale_deploy_guide_dismissed';

export function hasSeenDeployGuide(): boolean {
  return localStorage.getItem(DEPLOY_GUIDE_KEY) === 'true';
}

export function dismissDeployGuide(): void {
  localStorage.setItem(DEPLOY_GUIDE_KEY, 'true');
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 rounded-md bg-white/10 hover:bg-white/20 text-slate-400 hover:text-white transition-colors"
      title="Copy to clipboard"
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
    </button>
  );
}

function CollapsibleSection({
  title,
  icon: Icon,
  children,
  defaultOpen = false,
  badge,
}: {
  title: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: { text: string; color: string };
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        {open ? (
          <ChevronDown size={16} className="text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronRight size={16} className="text-gray-400 flex-shrink-0" />
        )}
        <Icon size={16} className="text-indigo-600 flex-shrink-0" />
        <span className="text-sm font-semibold text-gray-900 flex-1">{title}</span>
        {badge && (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badge.color}`}>
            {badge.text}
          </span>
        )}
      </button>
      {open && <div className="px-4 py-4 border-t border-gray-200">{children}</div>}
    </div>
  );
}

export default function DeploymentConfigGuide({ onClose }: { onClose: () => void }) {
  const handleDismiss = () => {
    dismissDeployGuide();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-100 flex items-center justify-center">
              <Server size={18} className="text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Deployment Configuration</h2>
              <p className="text-xs text-gray-500">First-time setup &mdash; configure your environment</p>
            </div>
          </div>
          <button
            onClick={handleDismiss}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {/* Intro */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
            <AlertTriangle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-amber-800 font-medium">
                ALE works in demo mode by default.
              </p>
              <p className="text-sm text-amber-700 mt-1">
                Set the environment variables below to enable OAuth login, LLM-powered features,
                and custom registry storage. Everything below is optional &mdash; the app runs
                without them using demo/stub behavior.
              </p>
            </div>
          </div>

          {/* Section 1: LLM / Anthropic API Key */}
          <CollapsibleSection
            title="Anthropic API Key (LLM Features)"
            icon={Key}
            defaultOpen={true}
            badge={{ text: 'Recommended', color: 'bg-indigo-100 text-indigo-700' }}
          >
            <p className="text-sm text-gray-600 mb-3">
              Required for AI-powered enrichment, guardrail suggestions, library descriptions,
              and preview generation. Without this key, LLM features return placeholder responses.
            </p>
            <div className="relative">
              <pre className="bg-slate-900 text-slate-100 text-xs font-mono rounded-lg p-4 pr-10 overflow-x-auto">
{`export ANTHROPIC_API_KEY="sk-ant-api03-..."
`}
              </pre>
              <CopyButton text='export ANTHROPIC_API_KEY="sk-ant-api03-..."' />
            </div>
            <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
              Get your key from
              <span className="inline-flex items-center gap-1 text-indigo-600 font-medium">
                console.anthropic.com
                <ExternalLink size={10} />
              </span>
            </p>
            <div className="mt-3 bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-600">
                <strong>Endpoints affected:</strong>{' '}
                <code className="bg-gray-200 px-1 rounded text-xs">POST /api/llm/enrich</code>{' '}
                <code className="bg-gray-200 px-1 rounded text-xs">POST /api/llm/preview</code>{' '}
                <code className="bg-gray-200 px-1 rounded text-xs">POST /api/llm/suggest-guardrails</code>{' '}
                <code className="bg-gray-200 px-1 rounded text-xs">POST /api/llm/describe</code>
              </p>
            </div>
          </CollapsibleSection>

          {/* Section 2: OAuth */}
          <CollapsibleSection
            title="GitHub / GitLab OAuth"
            icon={Shield}
            badge={{ text: 'Optional', color: 'bg-gray-100 text-gray-600' }}
          >
            <p className="text-sm text-gray-600 mb-3">
              Enable real OAuth login instead of the demo account. Without these, ALE uses
              a local demo admin user automatically.
            </p>
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1.5">GitHub OAuth</p>
                <div className="relative">
                  <pre className="bg-slate-900 text-slate-100 text-xs font-mono rounded-lg p-4 pr-10 overflow-x-auto">
{`export GITHUB_CLIENT_ID="your_github_client_id"
export GITHUB_CLIENT_SECRET="your_github_client_secret"`}
                  </pre>
                  <CopyButton text={`export GITHUB_CLIENT_ID="your_github_client_id"\nexport GITHUB_CLIENT_SECRET="your_github_client_secret"`} />
                </div>
                <p className="text-xs text-gray-500 mt-1.5">
                  Create an OAuth App at GitHub &rarr; Settings &rarr; Developer settings &rarr; OAuth Apps.
                  Set callback URL to <code className="bg-gray-100 px-1 rounded">http://&lt;host&gt;/api/auth/callback/github</code>
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1.5">GitLab OAuth</p>
                <div className="relative">
                  <pre className="bg-slate-900 text-slate-100 text-xs font-mono rounded-lg p-4 pr-10 overflow-x-auto">
{`export GITLAB_CLIENT_ID="your_gitlab_client_id"
export GITLAB_CLIENT_SECRET="your_gitlab_client_secret"`}
                  </pre>
                  <CopyButton text={`export GITLAB_CLIENT_ID="your_gitlab_client_id"\nexport GITLAB_CLIENT_SECRET="your_gitlab_client_secret"`} />
                </div>
                <p className="text-xs text-gray-500 mt-1.5">
                  Create an Application in your GitLab instance.
                  Set redirect URL to <code className="bg-gray-100 px-1 rounded">http://&lt;host&gt;/api/auth/callback/gitlab</code>
                </p>
              </div>
            </div>
          </CollapsibleSection>

          {/* Section 3: Registry */}
          <CollapsibleSection
            title="Registry Storage"
            icon={Server}
            badge={{ text: 'Optional', color: 'bg-gray-100 text-gray-600' }}
          >
            <p className="text-sm text-gray-600 mb-3">
              Controls where published agentic library entries are stored on disk.
              Defaults to <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">.ale_registry/</code> in
              the project root.
            </p>
            <div className="relative">
              <pre className="bg-slate-900 text-slate-100 text-xs font-mono rounded-lg p-4 pr-10 overflow-x-auto">
{`export ALE_REGISTRY_DIR="/path/to/registry"`}
              </pre>
              <CopyButton text='export ALE_REGISTRY_DIR="/path/to/registry"' />
            </div>
          </CollapsibleSection>

          {/* Section 4: Starting the services */}
          <CollapsibleSection
            title="Starting the Services"
            icon={Terminal}
          >
            <p className="text-sm text-gray-600 mb-3">
              ALE has a FastAPI backend and a Vite/React frontend. Both need to be running.
            </p>
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1.5">Backend (FastAPI)</p>
                <div className="relative">
                  <pre className="bg-slate-900 text-slate-100 text-xs font-mono rounded-lg p-4 pr-10 overflow-x-auto">
{`pip install -r web/backend/requirements.txt
pip install -e .
uvicorn web.backend.app.main:app --reload --port 8000`}
                  </pre>
                  <CopyButton text={`pip install -r web/backend/requirements.txt\npip install -e .\nuvicorn web.backend.app.main:app --reload --port 8000`} />
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1.5">Frontend (Vite + React)</p>
                <div className="relative">
                  <pre className="bg-slate-900 text-slate-100 text-xs font-mono rounded-lg p-4 pr-10 overflow-x-auto">
{`cd web/frontend
npm install
npm run dev`}
                  </pre>
                  <CopyButton text={`cd web/frontend\nnpm install\nnpm run dev`} />
                </div>
              </div>
            </div>
            <div className="mt-3 bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-600">
                <strong>Data storage:</strong> User accounts, sessions, API keys, drafts, and LLM usage
                are stored under <code className="bg-gray-200 px-1 rounded">~/.ale/</code> and
                are created automatically on first use.
              </p>
            </div>
          </CollapsibleSection>

          {/* Quick .env reference */}
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-4 py-3 bg-gray-50">
              <p className="text-sm font-semibold text-gray-900">
                Quick Reference &mdash; All Environment Variables
              </p>
            </div>
            <div className="relative">
              <pre className="bg-slate-900 text-slate-100 text-xs font-mono p-4 pr-10 overflow-x-auto">
{`# Required for LLM features (enrichment, descriptions, guardrails)
ANTHROPIC_API_KEY=sk-ant-api03-...

# GitHub OAuth (optional — enables real login)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# GitLab OAuth (optional)
GITLAB_CLIENT_ID=
GITLAB_CLIENT_SECRET=

# Custom registry storage path (optional)
ALE_REGISTRY_DIR=/path/to/registry`}
              </pre>
              <CopyButton
                text={`# Required for LLM features (enrichment, descriptions, guardrails)\nANTHROPIC_API_KEY=sk-ant-api03-...\n\n# GitHub OAuth (optional — enables real login)\nGITHUB_CLIENT_ID=\nGITHUB_CLIENT_SECRET=\n\n# GitLab OAuth (optional)\nGITLAB_CLIENT_ID=\nGITLAB_CLIENT_SECRET=\n\n# Custom registry storage path (optional)\nALE_REGISTRY_DIR=/path/to/registry`}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-2xl flex-shrink-0">
          <p className="text-xs text-gray-500">
            You can run without any configuration &mdash; demo mode is fully functional.
          </p>
          <button
            onClick={handleDismiss}
            className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
