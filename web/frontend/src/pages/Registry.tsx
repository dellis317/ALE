import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Search, ShieldCheck, Star, Download, Package } from 'lucide-react';
import { searchRegistry, fetchRegistry } from '../api/client';
import type { LibraryEntry } from '../types';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';

function ComplexityBadge({ complexity }: { complexity: string }) {
  const variant =
    complexity === 'simple'
      ? 'success'
      : complexity === 'moderate'
        ? 'warning'
        : complexity === 'complex'
          ? 'error'
          : 'default';
  return <Badge label={complexity} variant={variant} />;
}

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={12}
          className={star <= rating ? 'text-amber-400 fill-amber-400' : 'text-gray-300'}
        />
      ))}
    </div>
  );
}

function LibraryCard({ entry, onClick }: { entry: LibraryEntry; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all duration-200 cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
            <Package size={18} className="text-indigo-600" />
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors truncate">
              {entry.name}
            </h3>
            <span className="text-xs text-gray-500">v{entry.version}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {entry.is_verified && (
            <span className="flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
              <ShieldCheck size={12} />
              Verified
            </span>
          )}
          <ComplexityBadge complexity={entry.complexity} />
        </div>
      </div>

      <p className="text-sm text-gray-600 mb-3 line-clamp-2">{entry.description}</p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {entry.tags.slice(0, 5).map((tag) => (
          <Badge key={tag} label={tag} variant="info" />
        ))}
        {entry.tags.length > 5 && (
          <Badge label={`+${entry.tags.length - 5}`} variant="default" />
        )}
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-500 pt-3 border-t border-gray-100">
        <div className="flex items-center gap-1">
          <StarRating rating={entry.quality.rating} />
          <span className="ml-1">({entry.quality.rating_count})</span>
        </div>
        <div className="flex items-center gap-1">
          <Download size={12} />
          <span>{entry.quality.download_count.toLocaleString()}</span>
        </div>
        {entry.quality.maintained && (
          <span className="text-emerald-600 font-medium">Maintained</span>
        )}
      </div>
    </button>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-lg bg-gray-200" />
        <div className="flex-1">
          <div className="h-4 bg-gray-200 rounded w-32 mb-1" />
          <div className="h-3 bg-gray-100 rounded w-16" />
        </div>
      </div>
      <div className="h-3 bg-gray-100 rounded w-full mb-2" />
      <div className="h-3 bg-gray-100 rounded w-3/4 mb-3" />
      <div className="flex gap-2 mb-3">
        <div className="h-5 bg-gray-100 rounded-full w-14" />
        <div className="h-5 bg-gray-100 rounded-full w-18" />
        <div className="h-5 bg-gray-100 rounded-full w-12" />
      </div>
      <div className="h-3 bg-gray-100 rounded w-48 pt-3 border-t border-gray-100" />
    </div>
  );
}

export default function Registry() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const {
    data: searchResult,
    isLoading: isSearching,
    error: searchError,
  } = useQuery({
    queryKey: ['registry', 'search', searchTerm, verifiedOnly, selectedTags],
    queryFn: () =>
      searchTerm || verifiedOnly || selectedTags.length > 0
        ? searchRegistry({ q: searchTerm, verified_only: verifiedOnly, tags: selectedTags })
        : fetchRegistry().then((entries) => ({ entries, total_count: entries.length })),
    staleTime: 30000,
  });

  const entries = searchResult?.entries ?? [];

  // Collect all unique tags from results
  const allTags = Array.from(
    new Set(entries.flatMap((e) => e.tags))
  ).sort();

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Library Registry</h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse and discover agentic libraries
        </p>
      </div>

      {/* Search bar */}
      <div className="mb-6">
        <div className="relative">
          <Search
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Search libraries by name, description, or tags..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow"
          />
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <button
          onClick={() => setVerifiedOnly(!verifiedOnly)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            verifiedOnly
              ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
              : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
          }`}
        >
          <ShieldCheck size={14} />
          Verified only
        </button>
        <div className="h-4 w-px bg-gray-300" />
        {allTags.slice(0, 10).map((tag) => (
          <button
            key={tag}
            onClick={() => toggleTag(tag)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              selectedTags.includes(tag)
                ? 'bg-indigo-50 text-indigo-700 border-indigo-300'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {tag}
          </button>
        ))}
      </div>

      {/* Results count */}
      {searchResult && (
        <p className="text-xs text-gray-500 mb-4">
          {searchResult.total_count} {searchResult.total_count === 1 ? 'library' : 'libraries'} found
        </p>
      )}

      {/* Error state */}
      {searchError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-red-700">
            Failed to load libraries: {searchError instanceof Error ? searchError.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Loading state */}
      {isSearching && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* Results grid */}
      {!isSearching && entries.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {entries.map((entry) => (
            <LibraryCard
              key={entry.qualified_id}
              entry={entry}
              onClick={() => navigate(`/library/${entry.name}/${entry.version}`)}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isSearching && !searchError && entries.length === 0 && (
        <EmptyState
          title="No libraries found"
          description={
            searchTerm
              ? `No libraries match "${searchTerm}". Try adjusting your search or filters.`
              : 'No libraries in the registry yet. Libraries will appear here once they are published.'
          }
          icon={Package}
        />
      )}
    </div>
  );
}
