import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { LogOut, Settings, User as UserIcon, ChevronUp } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-red-500/20 text-red-300',
  publisher: 'bg-amber-500/20 text-amber-300',
  reviewer: 'bg-blue-500/20 text-blue-300',
  viewer: 'bg-slate-500/20 text-slate-300',
};

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [open]);

  if (!user) {
    return (
      <div className="px-6 py-4 border-t border-white/10">
        <Link
          to="/login"
          className="flex items-center gap-2 text-sm text-slate-300 hover:text-white transition-colors"
        >
          <UserIcon size={16} />
          Sign in
        </Link>
      </div>
    );
  }

  const roleColor = ROLE_COLORS[user.role] ?? ROLE_COLORS.viewer;
  const initials = (user.display_name || user.username || '?')
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <div ref={menuRef} className="relative px-3 py-3 border-t border-white/10">
      {/* Dropdown menu (appears above the trigger) */}
      {open && (
        <div className="absolute bottom-full left-3 right-3 mb-2 bg-[#1e293b] border border-white/10 rounded-lg shadow-xl overflow-hidden z-50">
          {/* User info */}
          <div className="px-4 py-3 border-b border-white/10">
            <p className="text-sm font-medium text-white truncate">
              {user.display_name || user.username}
            </p>
            <p className="text-xs text-slate-400 truncate">{user.email}</p>
            <span
              className={`inline-block mt-1.5 px-2 py-0.5 rounded text-xs font-medium ${roleColor}`}
            >
              {user.role}
            </span>
          </div>

          {/* Menu items */}
          <div className="py-1">
            <Link
              to="/settings/api-keys"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
            >
              <Settings size={15} />
              Settings
            </Link>
            <button
              onClick={() => {
                setOpen(false);
                logout();
              }}
              className="flex items-center gap-2.5 w-full px-4 py-2 text-sm text-slate-300 hover:bg-white/5 hover:text-white transition-colors"
            >
              <LogOut size={15} />
              Sign out
            </button>
          </div>
        </div>
      )}

      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-3 w-full px-3 py-2 rounded-lg hover:bg-white/5 transition-colors group"
      >
        {/* Avatar */}
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt={user.display_name}
            className="w-8 h-8 rounded-full flex-shrink-0"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0 text-xs font-medium text-white">
            {initials}
          </div>
        )}

        {/* Name + role */}
        <div className="flex-1 min-w-0 text-left">
          <p className="text-sm font-medium text-slate-200 truncate">
            {user.display_name || user.username}
          </p>
          <p className="text-xs text-slate-500 truncate">{user.role}</p>
        </div>

        <ChevronUp
          size={16}
          className={`text-slate-500 transition-transform ${open ? '' : 'rotate-180'}`}
        />
      </button>
    </div>
  );
}
