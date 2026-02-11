import type {
  LibraryEntry,
  SearchResult,
  ConformanceResult,
  Candidate,
  DriftReport,
  ProvenanceRecord,
  IRModule,
  Draft,
  ValidationResult,
  EnrichmentResult,
  User,
  APIKeyEntry,
  LoginResult,
  ConformanceHistoryEntry,
  BatchConformanceResult,
  DriftSummary,
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

// IR Explorer API
export async function parseFile(filePath: string, repoRoot?: string): Promise<IRModule> {
  return request<IRModule>('/api/ir/parse', {
    method: 'POST',
    body: JSON.stringify({ file_path: filePath, repo_root: repoRoot || '' }),
  });
}

// Generator / Editor API
export async function generateLibrary(
  repoPath: string,
  featureName: string,
  enrich?: boolean
): Promise<{ success: boolean; output_path?: string; message: string }> {
  return request<{ success: boolean; output_path?: string; message: string }>('/api/generate', {
    method: 'POST',
    body: JSON.stringify({ repo_path: repoPath, feature_name: featureName, enrich: enrich ?? true }),
  });
}

export async function validateContent(yamlContent: string): Promise<ValidationResult> {
  return request<ValidationResult>('/api/generate/validate', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

export async function enrichContent(yamlContent: string): Promise<EnrichmentResult> {
  return request<EnrichmentResult>('/api/generate/enrich', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

export async function saveDraft(name: string, yamlContent: string): Promise<Draft> {
  return request<Draft>('/api/generate/save-draft', {
    method: 'POST',
    body: JSON.stringify({ name, yaml_content: yamlContent }),
  });
}

export async function listDrafts(): Promise<Draft[]> {
  return request<Draft[]>('/api/generate/drafts');
}

export async function getDraft(id: string): Promise<Draft> {
  return request<Draft>(`/api/generate/drafts/${id}`);
}

export async function deleteDraft(id: string): Promise<void> {
  await request<void>(`/api/generate/drafts/${id}`, { method: 'DELETE' });
}

export async function publishFromEditor(yamlContent: string, name?: string): Promise<LibraryEntry> {
  return request<LibraryEntry>('/api/generate/publish', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent, name: name || '' }),
  });
}

// Auth API
export async function loginDemo(): Promise<LoginResult> {
  return request<LoginResult>('/api/auth/login/github');
}

export async function logout(token: string): Promise<void> {
  await request<void>('/api/auth/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getCurrentUser(token: string): Promise<User> {
  return request<User>('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function listUsers(token: string): Promise<User[]> {
  return request<User[]>('/api/auth/users', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateUserRole(token: string, userId: string, role: string): Promise<User> {
  return request<User>(`/api/auth/users/${userId}/role`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ role }),
  });
}

export async function createAPIKey(token: string, name: string): Promise<{ key: APIKeyEntry; raw_key: string }> {
  return request<{ key: APIKeyEntry; raw_key: string }>('/api/auth/api-keys', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name }),
  });
}

export async function listAPIKeys(token: string): Promise<APIKeyEntry[]> {
  return request<APIKeyEntry[]>('/api/auth/api-keys', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function deleteAPIKey(token: string, keyId: string): Promise<void> {
  await request<void>(`/api/auth/api-keys/${keyId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// Enhanced endpoints

export async function getLibraryVersions(name: string): Promise<LibraryEntry[]> {
  return request<LibraryEntry[]>(`/api/registry/${encodeURIComponent(name)}/versions`);
}

export async function getConformanceHistory(libraryName: string): Promise<ConformanceHistoryEntry[]> {
  return request<ConformanceHistoryEntry[]>(`/api/conformance/history?library_name=${encodeURIComponent(libraryName)}`);
}

export async function runBatchConformance(): Promise<BatchConformanceResult> {
  return request<BatchConformanceResult>('/api/conformance/batch', { method: 'POST' });
}

export async function getDriftSummary(repoPath: string): Promise<DriftSummary> {
  const params = new URLSearchParams({ repo_path: repoPath });
  return request<DriftSummary>(`/api/drift/summary?${params.toString()}`);
}
