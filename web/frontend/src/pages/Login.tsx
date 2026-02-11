import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Github, Gitlab, Zap, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading: authLoading } = useAuth();
  const [error, setError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  async function handleDemoLogin() {
    setError('');
    setLoggingIn(true);
    try {
      await login();
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoggingIn(false);
    }
  }

  function handleGitHubLogin() {
    // In production, this would redirect to the GitHub OAuth URL.
    // In demo mode, we use the demo login flow instead.
    handleDemoLogin();
  }

  function handleGitLabLogin() {
    // Same as GitHub -- in demo mode, falls through to demo login.
    handleDemoLogin();
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f172a] flex flex-col items-center justify-center px-4">
      {/* Branding */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold text-white tracking-tight mb-2">ALE</h1>
        <p className="text-slate-400 text-sm">Agentic Library Extractor</p>
      </div>

      {/* Login card */}
      <div className="w-full max-w-sm">
        <div className="bg-[#1e293b] rounded-2xl border border-white/10 shadow-2xl p-8">
          <h2 className="text-xl font-semibold text-white text-center mb-1">Welcome back</h2>
          <p className="text-sm text-slate-400 text-center mb-8">
            Sign in to manage libraries and API keys
          </p>

          {/* Error message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3 mb-6">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* OAuth buttons */}
          <div className="space-y-3 mb-6">
            <button
              onClick={handleGitHubLogin}
              disabled={loggingIn}
              className="flex items-center justify-center gap-3 w-full px-4 py-3 bg-white text-gray-900 rounded-lg font-medium text-sm hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Github size={18} />
              Continue with GitHub
            </button>

            <button
              onClick={handleGitLabLogin}
              disabled={loggingIn}
              className="flex items-center justify-center gap-3 w-full px-4 py-3 bg-[#fc6d26] text-white rounded-lg font-medium text-sm hover:bg-[#e65a1a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Gitlab size={18} />
              Continue with GitLab
            </button>
          </div>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-white/10" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-3 bg-[#1e293b] text-slate-500">or</span>
            </div>
          </div>

          {/* Demo login */}
          <button
            onClick={handleDemoLogin}
            disabled={loggingIn}
            className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-indigo-600 text-white rounded-lg font-medium text-sm hover:bg-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Zap size={16} />
            {loggingIn ? 'Signing in...' : 'Demo Login'}
          </button>

          <p className="text-xs text-slate-500 text-center mt-3">
            Creates a local admin account for development
          </p>
        </div>

        {/* Features */}
        <div className="mt-8 grid grid-cols-2 gap-4">
          <div className="flex items-start gap-3 p-3">
            <Shield size={18} className="text-indigo-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-slate-300">Role-Based Access</p>
              <p className="text-xs text-slate-500 mt-0.5">Admin, publisher, reviewer, viewer</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3">
            <Zap size={18} className="text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-slate-300">API Keys</p>
              <p className="text-xs text-slate-500 mt-0.5">Programmatic access for CI/CD</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
