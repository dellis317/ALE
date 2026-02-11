import { NavLink, Outlet } from 'react-router-dom';
import { Package, Search, ShieldCheck, Activity } from 'lucide-react';

const navItems = [
  { to: '/', label: 'Registry', icon: Package, end: true },
  { to: '/analyze', label: 'Analyzer', icon: Search },
  { to: '/conformance', label: 'Conformance', icon: ShieldCheck },
  { to: '/drift', label: 'Drift', icon: Activity },
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

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10">
          <p className="text-xs text-slate-500">ALE Web Portal v1.0</p>
        </div>
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
