import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Search, ShieldCheck, Star, Download, Package, ArrowUpDown, ChevronLeft, ChevronRight as ChevronRightIcon, MessageSquareText, FolderTree, Calendar } from 'lucide-react';
import { searchRegistry, fetchRegistry, searchGeneratedLibraries } from '../api/client';
import type { LibraryEntry, GeneratedLibrary } from '../types';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';

const ITEMS_PER_PAGE = 12;

type SortField = 'name' | 'rating' | 'downloads' | 'last_updated';

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

function StatusBadge({ entry }: { entry: LibraryEntry }) {
  // Determine status based on quality signals
  if (!entry.quality.maintained) {
    return <Badge label="Deprecated" variant="warning" />;
  }
  if (entry.quality.download_count === 0 && entry.quality.rating_count === 0) {
    return <Badge label="Archived" variant="default" />;
  }
  return <Badge label="Active" variant="success" />;
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
        <StatusBadge entry={entry} />
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

function GeneratedLibraryCard({ library, onClick }: { library: GeneratedLibrary; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-xl border border-indigo-200 p-5 hover:shadow-md hover:border-indigo-300 transition-all duration-200 cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
            <FolderTree size={18} className="text-indigo-600" />
          </div>
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors truncate">
              {library.name}
            </h3>
            <span className="text-xs text-gray-500">
              {library.candidate_name === '__whole_codebase__' ? 'Full Codebase' : library.candidate_name}
            </span>
          </div>
        </div>
        <Badge label="Generated" variant="info" />
      </div>

      <p className="text-sm text-gray-600 mb-3 line-clamp-2">
        {library.source_repo_url || library.repo_path}
      </p>

      <div className="flex items-center gap-4 text-xs text-gray-500 pt-3 border-t border-gray-100">
        <div className="flex items-center gap-1">
          <Calendar size={12} />
          <span>{new Date(library.created_at).toLocaleDateString()}</span>
        </div>
        <Badge label="Your Library" variant="success" />
      </div>
    </button>
  );
}

function sortEntries(entries: LibraryEntry[], sortBy: SortField): LibraryEntry[] {
  return [...entries].sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return a.name.localeCompare(b.name);
      case 'rating':
        return b.quality.rating - a.quality.rating;
      case 'downloads':
        return b.quality.download_count - a.quality.download_count;
      case 'last_updated':
        return new Date(b.quality.last_updated).getTime() - new Date(a.quality.last_updated).getTime();
      default:
        return 0;
    }
  });
}

export default function Registry() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<SortField>('name');
  const [complexityFilter, setComplexityFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [goalDescription, setGoalDescription] = useState('');

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

  // Also search generated (saved) libraries so they appear in discovery
  const { data: generatedLibraries = [] } = useQuery({
    queryKey: ['generated-libraries-search', searchTerm],
    queryFn: () => searchGeneratedLibraries(searchTerm),
    staleTime: 30000,
  });

  const entries = searchResult?.entries ?? [];

  // Apply complexity filter and sorting
  const filteredAndSorted = useMemo(() => {
    let filtered = entries;
    if (complexityFilter) {
      filtered = filtered.filter((e) => e.complexity === complexityFilter);
    }
    return sortEntries(filtered, sortBy);
  }, [entries, complexityFilter, sortBy]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredAndSorted.length / ITEMS_PER_PAGE));
  const safePage = Math.min(currentPage, totalPages);
  const paginatedEntries = filteredAndSorted.slice(
    (safePage - 1) * ITEMS_PER_PAGE,
    safePage * ITEMS_PER_PAGE
  );

  // Collect all unique tags from results
  const allTags = Array.from(
    new Set(entries.flatMap((e) => e.tags))
  ).sort();

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
    setCurrentPage(1);
  };

  const handleGoalSearch = () => {
    if (goalDescription.trim()) {
      // Extract keywords from goal description
      const stopWords = new Set(['i', 'a', 'an', 'the', 'to', 'and', 'or', 'for', 'of', 'in', 'on', 'is', 'am', 'are', 'was', 'were', 'be', 'been', 'my', 'what', 'how', 'do', 'does', 'want', 'need', 'trying', 'that', 'this', 'with']);
      const keywords = goalDescription
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, '')
        .split(/\s+/)
        .filter((w) => w.length > 2 && !stopWords.has(w))
        .slice(0, 5)
        .join(' ');
      setSearchTerm(keywords || goalDescription.trim());
      setCurrentPage(1);
    }
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

      {/* Describe what you need */}
      <div className="mb-6">
        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <MessageSquareText size={20} className="text-indigo-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-indigo-900 mb-2">Describe what you need</h3>
              <textarea
                value={goalDescription}
                onChange={(e) => setGoalDescription(e.target.value)}
                placeholder="What are you trying to accomplish? Describe your goal..."
                rows={2}
                className="w-full px-3 py-2 text-sm bg-white border border-indigo-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              />
              <button
                onClick={handleGoalSearch}
                disabled={!goalDescription.trim()}
                className="mt-2 px-4 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Find Libraries
              </button>
            </div>
          </div>
        </div>
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
            onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-shadow"
          />
        </div>
      </div>

      {/* Filters and sort */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <button
          onClick={() => { setVerifiedOnly(!verifiedOnly); setCurrentPage(1); }}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            verifiedOnly
              ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
              : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
          }`}
        >
          <ShieldCheck size={14} />
          Verified only
        </button>

        {/* Complexity filter */}
        <div className="h-4 w-px bg-gray-300" />
        <div className="flex items-center gap-1.5">
          <select
            value={complexityFilter}
            onChange={(e) => { setComplexityFilter(e.target.value); setCurrentPage(1); }}
            className="text-xs font-medium bg-white border border-gray-300 rounded-full px-3 py-1.5 text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Complexities</option>
            <option value="simple">Simple</option>
            <option value="moderate">Moderate</option>
            <option value="complex">Complex</option>
          </select>
        </div>

        {/* Sort control */}
        <div className="h-4 w-px bg-gray-300" />
        <div className="flex items-center gap-1.5">
          <ArrowUpDown size={14} className="text-gray-400" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortField)}
            className="text-xs font-medium bg-white border border-gray-300 rounded-full px-3 py-1.5 text-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="name">Sort by Name</option>
            <option value="rating">Sort by Rating</option>
            <option value="downloads">Sort by Downloads</option>
            <option value="last_updated">Sort by Last Updated</option>
          </select>
        </div>

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
          {filteredAndSorted.length + generatedLibraries.length}{' '}
          {filteredAndSorted.length + generatedLibraries.length === 1 ? 'library' : 'libraries'} found
          {generatedLibraries.length > 0 && ` (${generatedLibraries.length} generated, ${filteredAndSorted.length} published)`}
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

      {/* Generated (saved) libraries */}
      {!isSearching && generatedLibraries.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Your Generated Libraries ({generatedLibraries.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {generatedLibraries.slice(0, 6).map((lib) => (
              <GeneratedLibraryCard
                key={lib.id}
                library={lib}
                onClick={() => navigate(`/libraries/${lib.id}`)}
              />
            ))}
          </div>
          {generatedLibraries.length > 6 && (
            <button
              onClick={() => navigate('/libraries')}
              className="mt-3 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View all {generatedLibraries.length} generated libraries...
            </button>
          )}
        </div>
      )}

      {/* Published registry results */}
      {!isSearching && paginatedEntries.length > 0 && (
        <>
          {generatedLibraries.length > 0 && (
            <h2 className="text-sm font-semibold text-gray-700 mb-3">
              Published Libraries ({filteredAndSorted.length})
            </h2>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paginatedEntries.map((entry) => (
              <LibraryCard
                key={entry.qualified_id}
                entry={entry}
                onClick={() => navigate(`/library/${entry.name}/${entry.version}`)}
              />
            ))}
          </div>
        </>
      )}

      {/* Pagination */}
      {!isSearching && filteredAndSorted.length > ITEMS_PER_PAGE && (
        <div className="flex items-center justify-center gap-4 mt-8">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={safePage <= 1}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft size={14} />
            Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {safePage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={safePage >= totalPages}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Next
            <ChevronRightIcon size={14} />
          </button>
        </div>
      )}

      {/* Empty state */}
      {!isSearching && !searchError && filteredAndSorted.length === 0 && generatedLibraries.length === 0 && (
        <EmptyState
          title="No libraries found"
          description={
            searchTerm
              ? `No libraries match "${searchTerm}". Try adjusting your search or filters.`
              : 'No libraries yet. Go to the Analyze tab to generate libraries from a repository, or publish libraries to the registry.'
          }
          icon={Package}
        />
      )}
    </div>
  );
}
