import type {
  LibraryEntry,
  SearchResult,
  ConformanceResult,
  Candidate,
  DriftReport,
  ProvenanceRecord,
} from '../types';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) {
        message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignore parse errors
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export async function fetchRegistry(): Promise<LibraryEntry[]> {
  return request<LibraryEntry[]>('/api/registry');
}

export async function searchRegistry(params: {
  q?: string;
  tags?: string[];
  verified_only?: boolean;
  limit?: number;
  offset?: number;
}): Promise<SearchResult> {
  const searchParams = new URLSearchParams();
  if (params.q) searchParams.set('q', params.q);
  if (params.tags) {
    params.tags.forEach((tag) => searchParams.append('tags', tag));
  }
  if (params.verified_only) searchParams.set('verified_only', 'true');
  if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params.offset !== undefined) searchParams.set('offset', String(params.offset));

  return request<SearchResult>(`/api/registry/search?${searchParams.toString()}`);
}

export async function getLibrary(name: string, version?: string): Promise<LibraryEntry> {
  const path = version ? `/api/registry/${name}/${version}` : `/api/registry/${name}`;
  return request<LibraryEntry>(path);
}

export async function runConformance(
  libraryPath: string,
  workingDir?: string
): Promise<ConformanceResult> {
  return request<ConformanceResult>('/api/conformance/run', {
    method: 'POST',
    body: JSON.stringify({
      library_path: libraryPath,
      working_dir: workingDir || '.',
    }),
  });
}

export async function validateLibrary(libraryPath: string): Promise<ConformanceResult> {
  return request<ConformanceResult>('/api/conformance/validate', {
    method: 'POST',
    body: JSON.stringify({
      library_path: libraryPath,
    }),
  });
}

export async function getSchema(): Promise<unknown> {
  return request<unknown>('/api/schema');
}

export async function analyzeRepo(
  repoPath: string,
  depth?: string
): Promise<Candidate[]> {
  return request<Candidate[]>('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({
      repo_path: repoPath,
      depth: depth || 'standard',
    }),
  });
}

export async function checkDrift(
  repoPath: string,
  libraryName?: string
): Promise<DriftReport[]> {
  if (libraryName) {
    return request<DriftReport[]>('/api/drift/check', {
      method: 'POST',
      body: JSON.stringify({
        repo_path: repoPath,
        library_name: libraryName,
      }),
    });
  }
  return request<DriftReport[]>('/api/drift/check-all', {
    method: 'POST',
    body: JSON.stringify({
      repo_path: repoPath,
    }),
  });
}

export async function getProvenance(
  repoPath: string,
  libraryName?: string
): Promise<ProvenanceRecord[]> {
  const params = new URLSearchParams({ repo_path: repoPath });
  if (libraryName) params.set('library_name', libraryName);
  return request<ProvenanceRecord[]>(`/api/provenance?${params.toString()}`);
}
