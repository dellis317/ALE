# AI Query Interface for Analyzer Rows — Implementation Plan

## Overview

Add an inline GenAI query interface to each analyzer `CandidateRow`, allowing users to ask questions about a library/component when the auto-generated description is insufficient. Queries can be entered via text or voice (audio capture → Web Speech API transcription). All interactions are logged per library+component+user and moderated for security/profanity. Repeated violations lock the user's account.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React)                                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │ CandidateRow                                    │    │
│  │  ┌───────────────────────────────────────────┐  │    │
│  │  │ AIQueryPanel (new component)              │  │    │
│  │  │  - Text input + mic button                │  │    │
│  │  │  - Web Speech API transcription           │  │    │
│  │  │  - Response display                       │  │    │
│  │  │  - Past Q&A accordion (per component)     │  │    │
│  │  │  - Moderation error/warning banner        │  │    │
│  │  └───────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│                    POST /api/ai-query                     │
│                    GET  /api/ai-query/history             │
│                         │                                │
├─────────────────────────┼───────────────────────────────┤
│  Backend (FastAPI)      │                                │
│  ┌──────────────────────▼──────────────────────────┐    │
│  │ ai_query router                                  │    │
│  │  1. Auth middleware (get current user)            │    │
│  │  2. Check account lock status                    │    │
│  │  3. Content moderation (ContentModerator)        │    │
│  │  4. LLM call with candidate context              │    │
│  │  5. Log interaction (AIQueryStore)               │    │
│  │  6. Return response                              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ ContentModerator (ale/moderation/)               │   │
│  │  - Regex blocklist (injection patterns)          │   │
│  │  - Profanity word list check                     │   │
│  │  - Prompt injection detection                    │   │
│  │  - Violation tracking per user                   │   │
│  │  - Account lock on 2nd violation                 │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ AIQueryStore (ale/ai_query/)                     │   │
│  │  - JSONL file storage (~/.ale/ai_query_logs/)    │   │
│  │  - Indexed by library+component + repo_url       │   │
│  │  - Query by user, by component, by library       │   │
│  │  - Surface past Q&A for same component           │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: Backend — Content Moderation System

### File: `ale/moderation/__init__.py`
Empty package init.

### File: `ale/moderation/moderator.py`

**Class `ContentModerator`:**

- **Storage:** `~/.ale/moderation/violations.json` — tracks per-user violation history
- **`check_prompt(user_id: str, text: str) -> ModerationResult`**
  - Returns dataclass: `ModerationResult(allowed: bool, reason: str, violation_type: str)`
  - Checks in order:
    1. **Account lock check** — If user already has >= 2 violations, reject immediately with `reason="account_locked"`
    2. **Prompt injection detection** — Regex patterns for common injection attacks:
       - "ignore previous instructions", "system prompt", role-play jailbreak patterns
       - HTML/script tags, SQL-like patterns (`DROP`, `SELECT * FROM`, `'; --`)
       - Encoded payloads (base64-encoded suspicious strings)
    3. **Profanity / inappropriate content** — Word-list based check using a curated blocklist (slurs, explicit content, threats, hate speech). Use word-boundary matching to avoid false positives on substrings.
    4. **Security-sensitive content** — Patterns like API keys, credentials, PII (SSN, credit card numbers via regex)
  - On violation: increment user's violation count, record timestamp + violation_type
  - On 2nd violation: set `account_locked: true` in violations.json

- **`get_user_status(user_id: str) -> UserModerationStatus`**
  - Returns: `UserModerationStatus(violation_count: int, is_locked: bool, violations: list[ViolationRecord])`

- **`unlock_user(user_id: str)` (admin only)**
  - Resets violation count and lock status

### File: `ale/moderation/models.py`

```python
@dataclass
class ModerationResult:
    allowed: bool
    reason: str = ""          # human-readable explanation
    violation_type: str = ""  # "injection" | "profanity" | "security" | "account_locked" | ""

@dataclass
class ViolationRecord:
    timestamp: str
    violation_type: str
    prompt_snippet: str  # first 100 chars, redacted

@dataclass
class UserModerationStatus:
    user_id: str
    violation_count: int = 0
    is_locked: bool = False
    violations: list[ViolationRecord] = field(default_factory=list)
```

---

## Phase 2: Backend — AI Query Store (Interaction Log)

### File: `ale/ai_query/__init__.py`
Empty package init.

### File: `ale/ai_query/models.py`

```python
@dataclass
class AIQueryRecord:
    id: str                    # uuid
    user_id: str
    username: str
    repo_url: str              # repository URL or path
    library_name: str          # name of the library (if extracted) or repo name
    component_name: str        # candidate name from analyzer
    prompt: str
    response: str
    input_method: str          # "text" | "voice"
    model: str
    input_tokens: int
    output_tokens: int
    cost_estimate: float
    timestamp: str             # ISO 8601
```

### File: `ale/ai_query/store.py`

**Class `AIQueryStore`:**

- **Storage:** `~/.ale/ai_query_logs/` directory
  - File per library+component: `{library_name}__{component_name}.jsonl`
  - This makes per-component queries fast without scanning everything
- **`record_query(record: AIQueryRecord) -> AIQueryRecord`** — append to the correct file
- **`get_history(library_name: str, component_name: str, limit: int = 50) -> list[AIQueryRecord]`** — read component's JSONL, return newest-first
- **`get_history_by_user(user_id: str, limit: int = 50) -> list[AIQueryRecord]`** — scan all files, filter by user
- **`get_all_for_library(library_name: str, limit: int = 100) -> list[AIQueryRecord]`** — scan files matching `{library_name}__*.jsonl`
- **`get_insights(library_name: str, component_name: str) -> list[AIQueryRecord]`** — returns up to 10 most recent Q&A pairs for surfacing in the analyzer UI

---

## Phase 3: Backend — AI Query Router (API Endpoints)

### File: `web/backend/app/routers/ai_query.py`

**Router tag:** `"ai-query"`

### Endpoint: `POST /api/ai-query`

**Request model (`AIQueryRequest`):**
```python
class AIQueryRequest(BaseModel):
    repo_url: str              # repo path or URL
    library_name: str          # library being analyzed
    component_name: str        # candidate name
    prompt: str                # user's question
    input_method: str = "text" # "text" | "voice"
    # Context fields sent from frontend:
    candidate_description: str = ""
    candidate_tags: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)
    context_summary: str = ""
```

**Response model (`AIQueryResponse`):**
```python
class AIQueryResponse(BaseModel):
    id: str
    response: str
    model: str
    tokens_used: int = 0
    cost_estimate: float = 0.0
    timestamp: str = ""
```

**Flow:**
1. Extract user from auth middleware (Bearer token)
2. Call `ContentModerator.check_prompt(user_id, prompt)`
   - If `not allowed` and `violation_type == "account_locked"`: return **423 Locked** with error detail
   - If `not allowed` (first violation warning): return **422 Unprocessable Entity** with `reason` and `violation_type`
3. Build LLM prompt with context:
   - System prompt: "You are an expert code analyst. Answer questions about the following code component. Be specific, cite file paths and function names when possible."
   - User prompt includes: candidate name, description, tags, source files, context_summary, and the user's actual question
4. Call `LLMClient.complete()` (checks budget via UsageTracker)
5. Record via `AIQueryStore.record_query()`
6. Log to `AuditLogger` (action: `ai_query`, resource_type: `candidate`, resource_id: `component_name`)
7. Record LLM usage via `UsageTracker` (purpose: `ai_query`)
8. Return `AIQueryResponse`

### Endpoint: `GET /api/ai-query/history`

**Query params:** `library_name`, `component_name` (both required), `limit` (optional, default 50)

**Response:** `list[AIQueryHistoryEntry]` where:
```python
class AIQueryHistoryEntry(BaseModel):
    id: str
    user_id: str
    username: str
    prompt: str
    response: str
    input_method: str
    timestamp: str
```

Returns past Q&A for a specific component — used to show "Previously asked" in the UI.

### Endpoint: `GET /api/ai-query/insights/{library_name}/{component_name}`

Returns the top 10 most relevant/recent Q&A pairs for inline display in the analyzer row. Lightweight endpoint for populating the "Past insights" section.

### Endpoint: `GET /api/ai-query/user-status`

Returns the current user's moderation status (violation count, locked status). Used by frontend to show warnings proactively.

### Endpoint: `POST /api/ai-query/admin/unlock/{user_id}` (admin only)

Allows admins to unlock a user's account after review.

### Pydantic models location: `web/backend/app/models/api.py`

Add all request/response models to the existing API models file.

---

## Phase 4: Frontend — TypeScript Types

### File: `web/frontend/src/types/index.ts` (additions)

```typescript
// AI Query types
export interface AIQueryRequest {
  repo_url: string;
  library_name: string;
  component_name: string;
  prompt: string;
  input_method: 'text' | 'voice';
  candidate_description: string;
  candidate_tags: string[];
  source_files: string[];
  context_summary: string;
}

export interface AIQueryResponse {
  id: string;
  response: string;
  model: string;
  tokens_used: number;
  cost_estimate: number;
  timestamp: string;
}

export interface AIQueryHistoryEntry {
  id: string;
  user_id: string;
  username: string;
  prompt: string;
  response: string;
  input_method: string;
  timestamp: string;
}

export interface UserModerationStatus {
  user_id: string;
  violation_count: number;
  is_locked: boolean;
}

export interface ModerationError {
  reason: string;
  violation_type: string;
  is_locked: boolean;
}
```

---

## Phase 5: Frontend — API Client Functions

### File: `web/frontend/src/api/client.ts` (additions)

```typescript
export async function submitAIQuery(params: AIQueryRequest): Promise<AIQueryResponse>
export async function getAIQueryHistory(libraryName: string, componentName: string, limit?: number): Promise<AIQueryHistoryEntry[]>
export async function getAIQueryInsights(libraryName: string, componentName: string): Promise<AIQueryHistoryEntry[]>
export async function getUserModerationStatus(): Promise<UserModerationStatus>
export async function adminUnlockUser(userId: string): Promise<void>
```

---

## Phase 6: Frontend — AIQueryPanel Component

### File: `web/frontend/src/components/AIQueryPanel.tsx`

**Props:**
```typescript
interface AIQueryPanelProps {
  repoPath: string;
  libraryName: string;         // repo name or library name
  componentName: string;       // candidate.name
  candidateDescription: string;
  candidateTags: string[];
  sourceFiles: string[];
  contextSummary: string;
}
```

**UI Layout (within the expanded CandidateRow, below the existing details grid):**

```
┌─────────────────────────────────────────────────────────┐
│ 💬 Ask about this component                     [?]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─── Past Insights (collapsible, if any exist) ─────┐ │
│  │ Q: "What error handling patterns does this use?"   │ │
│  │ A: "The module uses try/except with custom..."     │ │
│  │ — asked by @jane 2d ago                            │ │
│  │                                                    │ │
│  │ Q: "Is this thread-safe?"                          │ │
│  │ A: "No, the shared state in _cache dict..."        │ │
│  │ — asked by @bob 5d ago                             │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌────────────────────────────────────────┐ ┌───┐ ┌──┐ │
│  │ Ask a question about this component... │ │ 🎤│ │➤ │ │
│  └────────────────────────────────────────┘ └───┘ └──┘ │
│                                                         │
│  ┌─── Response ──────────────────────────────────────┐  │
│  │ Based on the source files, this component...      │  │
│  │ ...                                               │  │
│  │                                    0.003 USD, 1.2k│  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ⚠️ Warning: Your message was flagged for [reason].     │
│     This is your first warning. A second violation      │
│     will lock your account.                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Key behaviors:**

1. **Text entry:** Standard text input with submit button (Enter key also submits)
2. **Voice input:** Mic button toggles Web Speech API (`SpeechRecognition`/`webkitSpeechRecognition`)
   - On start: button turns red, shows "Listening..."
   - On result: fills text input with transcript, user can review/edit before submitting
   - On error / no-support: hide mic button, text-only fallback
3. **Past insights:** Fetched via `getAIQueryInsights()` on component mount; collapsible accordion showing recent Q&A from any user for this component
4. **Loading state:** Spinner while LLM processes
5. **Error handling:**
   - 422 (moderation violation): Show warning banner with reason, clear input
   - 423 (account locked): Show persistent error banner, disable input
   - Budget exceeded (402): Show budget exceeded message
   - Network errors: Standard retry/error messaging
6. **Cost display:** Show token count and cost estimate on each response

---

## Phase 7: Frontend — Integration into Analyzer.tsx

### Modifications to `CandidateRow` in `web/frontend/src/pages/Analyzer.tsx`

1. Add `AIQueryPanel` import
2. Pass necessary props from candidate data and repoPath
3. Place `AIQueryPanel` inside the expanded section, after the existing details grid
4. Derive `libraryName` from repoPath (basename of the path)

The panel only renders when the row is expanded, keeping the collapsed view clean.

---

## Phase 8: Backend Registration

### File: `web/backend/app/main.py`

- Import and include `ai_query.router` alongside existing routers
- Mount at root like all other routers

---

## Implementation Order (14 files total)

| Step | File | Description |
|------|------|-------------|
| 1 | `ale/moderation/__init__.py` | Package init |
| 2 | `ale/moderation/models.py` | Moderation dataclasses |
| 3 | `ale/moderation/moderator.py` | ContentModerator with violation tracking |
| 4 | `ale/ai_query/__init__.py` | Package init |
| 5 | `ale/ai_query/models.py` | AIQueryRecord dataclass |
| 6 | `ale/ai_query/store.py` | AIQueryStore with JSONL persistence |
| 7 | `web/backend/app/models/api.py` | Add Pydantic request/response models |
| 8 | `web/backend/app/routers/ai_query.py` | FastAPI router with all endpoints |
| 9 | `web/backend/app/main.py` | Register new router |
| 10 | `web/frontend/src/types/index.ts` | Add TypeScript interfaces |
| 11 | `web/frontend/src/api/client.ts` | Add API client functions |
| 12 | `web/frontend/src/components/AIQueryPanel.tsx` | New component |
| 13 | `web/frontend/src/pages/Analyzer.tsx` | Integrate AIQueryPanel into CandidateRow |
| 14 | Tests (if test infra exists) | Unit tests for moderator + store |

---

## Security Considerations

- **Prompt injection:** The system prompt is fixed server-side; user input is always placed in the `user` message role, never in `system`. The moderator catches common injection patterns before the prompt reaches the LLM.
- **XSS:** All responses rendered via React's default escaping (no `dangerouslySetInnerHTML`).
- **Rate limiting:** The existing LLM budget system applies to AI queries (purpose: `ai_query`). This prevents cost abuse.
- **Data minimization:** Violation records store only a 100-char snippet of the flagged prompt, not the full text.
- **Account lock is reversible:** Admin can unlock via API, preventing permanent denial-of-service to legitimate users who triggered a false positive.
- **PII in prompts:** The moderator detects and blocks prompts containing patterns matching SSNs, credit card numbers, and similar PII.
- **Audit trail:** Every AI query and every moderation violation is logged in the audit system.
