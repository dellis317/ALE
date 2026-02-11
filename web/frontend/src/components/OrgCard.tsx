import { Link } from 'react-router-dom';
import { Building2, Users, GitBranch, ArrowRight } from 'lucide-react';
import type { Organization } from '../types';

interface OrgCardProps {
  org: Organization;
}

export default function OrgCard({ org }: OrgCardProps) {
  return (
    <Link
      to={`/orgs/${org.slug}`}
      className="block bg-white rounded-xl border border-gray-200 p-6 hover:border-indigo-300 hover:shadow-md transition-all group"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
            <Building2 size={20} className="text-indigo-600" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors">
              {org.name}
            </h3>
            <p className="text-xs text-gray-400 font-mono">/{org.slug}</p>
          </div>
        </div>
        <ArrowRight
          size={16}
          className="text-gray-300 group-hover:text-indigo-500 transition-colors mt-1"
        />
      </div>

      {org.description && (
        <p className="text-sm text-gray-500 mt-3 line-clamp-2">{org.description}</p>
      )}

      <div className="flex items-center gap-5 mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center gap-1.5 text-sm text-gray-500">
          <Users size={14} className="text-gray-400" />
          <span>
            {org.member_count} {org.member_count === 1 ? 'member' : 'members'}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-sm text-gray-500">
          <GitBranch size={14} className="text-gray-400" />
          <span>
            {org.repo_count} {org.repo_count === 1 ? 'repo' : 'repos'}
          </span>
        </div>
      </div>
    </Link>
  );
}
