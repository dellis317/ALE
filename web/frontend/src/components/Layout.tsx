import { NavLink, Outlet } from 'react-router-dom';
import { Package, Search, ShieldCheck, Activity, Network, Wand2, Settings, Building2, Sparkles, Shield, ClipboardCheck } from 'lucide-react';
import UserMenu from './UserMenu';

const navItems = [
  { to: '/', label: 'Registry', icon: Package, end: true },
  { to: '/analyze', label: 'Analyzer', icon: Search },
  { to: '/generate', label: 'Generator', icon: Wand2 },
  { to: '/conformance', label: 'Conformance', icon: ShieldCheck },
  { to: '/drift', label: 'Drift', icon: Activity },
  { to: '/ir', label: 'IR Explorer', icon: Network },
  { to: '/settings/api-keys', label: 'Settings', icon: Settings },
  { to: '/orgs', label: 'Organizations', icon: Building2 },
  { to: '/llm', label: 'LLM', icon: Sparkles },
  { to: '/policies', label: 'Policies', icon: Shield },
  { to: '/approvals', label: 'Approvals', icon: ClipboardCheck },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-[#0f172a] text-white flex flex-col">
        {/* Logo */}
        <div className="px-6 py-6 border-b border-white/10">
          <h1 className="text-2xl font-bold tracking-tight">ALE</h1>
          <p className="text-xs text-slate-400 mt-1">Agentic Library Extractor</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-300 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User menu / Footer */}
        <UserMenu />
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
