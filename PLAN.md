# Multi-Agent Build Plan: ALE Web Portal — Full Feature Set

## Current State

**Built (MVP):** Registry Browser, Library Detail, Conformance Runner, Repo Analyzer, Drift Dashboard
**Backend APIs without UI:** `/api/generate`, `/api/ir/parse`
**Remaining:** ~40+ features across 12 feature areas from `docs/web-portal-features.md`

---

## Agent Architecture

8 parallel workstreams organized into 3 phases. Each agent owns a vertical slice (backend + frontend) to minimize merge conflicts and maximize parallelism.

```
Phase 1 (Foundation)          Phase 2 (Core Features)         Phase 3 (Platform)
─────────────────────         ───────────────────────         ──────────────────
Agent 1: Auth & RBAC    ──┬──▶ Agent 5: Org & Multi-Repo  ──▶ Agent 8: Extensibility
Agent 2: Library Editor   │    Agent 6: Policy Management       & Webhooks
Agent 3: IR Explorer      │    Agent 7: LLM Integration
Agent 4: Enhance Existing ┘         & Cost Controls
         Pages
```

---

## Phase 1 — Foundation (all 4 agents run in parallel)

### Agent 1: Auth & Access Control

**Why first:** Nearly every Phase 2/3 feature needs user identity, roles, and org scoping. Without this, approval workflows, publishing controls, maintainer profiles, and org dashboards have no user model to build on.

**Scope:**

Backend:
- New router: `web/backend/app/routers/auth.py`
- New models: User, Org, Team, Role, APIKey, Session
- OAuth flow endpoints (GitHub/GitLab callback stubs — actual OAuth integration with provider)
- Session/token middleware (JWT or session-based)
- RBAC decorator/dependency: `require_role("publisher")` for use on existing and new endpoints
- API key CRUD endpoints for CI/CD integration
- New core module: `ale/auth/` (user store, role definitions, permission checks)

Frontend:
- New page: `LoginPage.tsx` at `/login`
- Auth context provider wrapping the app (current user, roles, org)
- Protected route wrapper component
- User menu in Layout sidebar (avatar, logout, role indicator)
- API key management page at `/settings/api-keys`

Files created:
```
ale/auth/__init__.py
ale/auth/models.py              # User, Org, Team, Role, Session dataclasses
ale/auth/store.py               # UserStore (file-based initially, DB-ready interface)
ale/auth/permissions.py         # RBAC logic, role hierarchy
ale/auth/oauth.py               # GitHub/GitLab OAuth helpers
web/backend/app/routers/auth.py
web/backend/app/middleware/auth.py  # JWT/session middleware
web/frontend/src/contexts/AuthContext.tsx
web/frontend/src/pages/Login.tsx
web/frontend/src/pages/Settings.tsx
web/frontend/src/components/ProtectedRoute.tsx
web/frontend/src/components/UserMenu.tsx
```

API endpoints:
```
GET    /api/auth/login/github      → Redirect to GitHub OAuth
GET    /api/auth/callback/github   → Handle OAuth callback, return JWT
GET    /api/auth/login/gitlab      → Redirect to GitLab OAuth
GET    /api/auth/callback/gitlab   → Handle OAuth callback, return JWT
POST   /api/auth/logout            → Invalidate session
GET    /api/auth/me                → Current user + roles
GET    /api/auth/users             → List users (admin only)
PUT    /api/auth/users/{id}/role   → Update user role (admin only)
POST   /api/auth/api-keys          → Create API key
GET    /api/auth/api-keys          → List user's API keys
DELETE /api/auth/api-keys/{id}     → Revoke API key
```

Roles: `admin`, `publisher`, `reviewer`, `viewer`

---

### Agent 2: Library Generator / Editor

**Why first:** This is explicitly next in the documented build order. It completes the "producer path" (Flow B) — analyze repo → generate library → edit → validate → publish.

**Scope:**

Backend:
- Wire up existing `/api/generate` endpoint to frontend (already exists, just needs UI connection)
- New endpoints for editor workflow: save draft, publish from editor
- LLM enrichment endpoint (wraps existing `LibraryGenerator` with `enrich=True`)

Frontend:
- New page: `Generator.tsx` at `/generate`
  - Step 1: Select candidate from analyzer results (or enter repo path + feature name)
  - Step 2: Review generated `.agentic.yaml` draft
  - Step 3: Live editor with syntax highlighting
  - Step 4: Real-time validation panel (schema + semantic errors inline)
  - Step 5: Preview mode (rendered consumer view: instructions as steps, guardrails as checklist)
  - Step 6: Publish to registry button
- Code editor component (use a lightweight editor — `textarea` with monospace + line numbers, or integrate a simple code mirror)
- Validation sidebar that auto-runs on edit (debounced)
- Preview panel toggling between YAML source and rendered consumer view
- LLM enrichment button: "Enhance with AI" → shows diff of suggestions → accept/reject

Files created:
```
web/frontend/src/pages/Generator.tsx
web/frontend/src/components/YamlEditor.tsx       # Editor with line numbers + syntax hints
web/frontend/src/components/ValidationPanel.tsx   # Live schema/semantic error display
web/frontend/src/components/PreviewMode.tsx       # Consumer-facing rendered view
web/frontend/src/components/DiffView.tsx          # Accept/reject LLM suggestions
web/backend/app/routers/generator.py              # New router for editor workflow
```

API endpoints (new):
```
POST   /api/generate                → Generate library from candidate (exists, wire up)
POST   /api/generate/enrich         → LLM enrichment on draft YAML
POST   /api/generate/save-draft     → Save work-in-progress draft
GET    /api/generate/drafts         → List saved drafts
DELETE /api/generate/drafts/{id}    → Delete draft
POST   /api/generate/publish        → Validate + publish from editor content
```

Nav: Add "Generator" to sidebar (Wand icon from lucide-react)

---

### Agent 3: IR Explorer

**Why first:** Backend API already exists (`POST /api/ir/parse`). This is purely a frontend page + visualization, no backend work needed. Independent of all other agents.

**Scope:**

Frontend:
- New page: `IRExplorer.tsx` at `/ir`
  - File input (path to Python file or repo directory)
  - Parse button
  - Symbol browser: tree view of modules → classes → methods/functions
    - Each symbol shows: name, kind (icon), visibility, parameters, return type, side effects, docstring
    - Click to expand/collapse class members
  - Dependency graph: visualization of import relationships
    - Nodes = symbols/modules, edges = dependencies
    - Color-coded by dependency kind (import, call, inherit, etc.)
    - External vs internal dependency distinction
  - Isolation analysis overlay: highlight candidate boundaries on the graph
  - Multi-file support: parse multiple files, show unified view

Frontend components:
```
web/frontend/src/pages/IRExplorer.tsx
web/frontend/src/components/SymbolTree.tsx        # Hierarchical symbol browser
web/frontend/src/components/DependencyGraph.tsx   # SVG/Canvas graph visualization
web/frontend/src/components/SymbolDetail.tsx      # Symbol info panel
```

May need new dependency: A lightweight graph layout library (e.g., `dagre` for DAG layout, or hand-rolled SVG with force-directed positioning).

Nav: Add "IR Explorer" to sidebar (Network icon from lucide-react)

API endpoints: Uses existing `POST /api/ir/parse` — no backend changes needed.

---

### Agent 4: Enhance Existing Pages

**Why now:** The 5 existing pages are functional but missing key features documented in the spec. This agent upgrades them without creating new pages, reducing conflict with other agents.

**Scope:**

#### Registry Browser enhancements:
- Sort controls (by name, rating, downloads, last updated)
- Pagination (current loads all at once)
- Complexity filter dropdown
- Language/framework filter
- Deprecation badges (Active/Deprecated/Archived status)
- Featured/Endorsed visual indicators (star/badge on cards)
- "Describe what you need" input field (goal-based discovery entry point — initially routes to search with extracted keywords; full LLM-backed version comes in Phase 2)

#### Library Detail enhancements:
- Version history section: list all versions, diff between versions, breaking change indicators
- Instructions display: render `instructions` as numbered step-by-step guide
- Guardrails checklist: render `guardrails` as enforceable checklist with severity badges
- Validation criteria: show `validation` hooks and expected behaviors
- Migration guidance section (if version has breaking changes)
- Maintainer info section (name + link placeholder for auth-backed profiles)
- "Try in Sandbox" button (placeholder, wired up in Phase 2)

#### Conformance Runner enhancements:
- Conformance history: store and display past runs per library (new backend endpoint)
- Batch validation: "Validate All" button that runs conformance across all registry libraries
- Evidence download: export conformance results as JSON attestation artifact

#### Repo Analyzer enhancements (critical — current analyzer is a stub):

**Problem:** The analyzer's Phase 2 (AST analysis) and Phase 3 (LLM-assisted) are TODO stubs. Candidate descriptions are hardcoded as `"Utility module: {name}"`. No actual code understanding happens — candidates are discovered purely by directory naming heuristics (utils/, helpers/, lib/, etc.). Entry points are file stems, not real symbols. Dependency lists aren't populated.

**Implement Phase 2 — AST-based code understanding:**
- Wire up the existing IR parser (`ale.ir.python_parser.parse_python_file`) into the analyzer pipeline
- For each candidate's source files, parse to IR and extract:
  - **Real symbols**: function names, class names, method signatures, docstrings
  - **Real entry points**: public functions/classes (not file stems)
  - **Dependency graph**: what this module imports, what imports this module (fan-in/fan-out)
  - **Side effects**: file I/O, network, database calls detected per symbol
- Generate a **rich description** from the parsed IR:
  - Module purpose (derived from top-level docstring + dominant symbol kinds)
  - Key functions/classes with their signatures and one-line docstring summaries
  - Internal vs external dependency summary
  - Call pattern: "called by N modules" / "calls into N modules" (app context)
- Populate `dependencies_external` and `dependencies_internal` lists (currently empty)
- Populate `entry_points` with actual `module.ClassName` / `module.function_name` symbols

**New fields on ExtractionCandidate model:**
- `context_summary: str` — human-readable paragraph: what this code does, its role in the app, why it's extractable
- `symbols: list[dict]` — key symbols with name, kind, signature, docstring
- `callers: list[str]` — which other modules in the repo import/call this candidate
- `callees: list[str]` — which other modules this candidate depends on

**UI enhancements:**
- Expanded candidate card shows rich description (multi-line, not truncated)
- Symbol list with signatures and docstrings
- "Used by" / "Depends on" sections showing app context
- "Generate Library" button on each candidate card → navigates to Generator page with pre-filled params
- Side-by-side comparison: select 2+ candidates, show radar chart comparison
- Improved candidate detail: radar/spider chart for scoring dimensions (replace linear bars)

#### Drift Dashboard enhancements:
- Summary stats bar at top (total repos, clean count, drifted count, by drift type)
- Per-library cross-repo view: "Where is library X applied?" table
- Color-coded drift severity indicators
- Exportable drift report (JSON/CSV download)

Backend additions:
```
# New endpoints
GET  /api/conformance/history?library_name=...   → Past conformance runs
POST /api/conformance/batch                      → Run conformance on all registry libs
GET  /api/registry/{name}/versions               → All versions of a library
GET  /api/drift/summary?repo_path=...            → Aggregate drift stats
```

New core modules:
```
ale/spec/conformance_history.py          # Store/retrieve past conformance runs
ale/analyzers/code_analyzer.py           # Phase 2: AST/IR-based code understanding
ale/analyzers/context_builder.py         # Build call graph context (who calls what)
```

Files modified:
```
ale/models/candidate.py                    # Add context_summary, symbols, callers, callees fields
ale/analyzers/repo_analyzer.py             # Wire Phase 2 into analysis pipeline
web/frontend/src/pages/Registry.tsx        # Sort, pagination, filters, badges
web/frontend/src/pages/LibraryDetail.tsx   # Version history, instructions, guardrails
web/frontend/src/pages/Conformance.tsx     # History, batch, export
web/frontend/src/pages/Analyzer.tsx        # Rich descriptions, symbols, context, comparison, radar chart
web/frontend/src/pages/Drift.tsx           # Summary stats, per-library view, export
web/frontend/src/components/RadarChart.tsx  # New: spider/radar chart component
web/frontend/src/components/SymbolList.tsx  # New: symbol signatures + docstrings display
web/frontend/src/components/StepList.tsx    # New: instruction step renderer
web/frontend/src/components/GuardrailList.tsx # New: guardrail checklist renderer
web/frontend/src/types/index.ts            # Extended types (candidate context fields)
web/frontend/src/api/client.ts             # New API functions
web/backend/app/routers/conformance.py     # History + batch endpoints
web/backend/app/routers/registry.py        # Version list endpoint
web/backend/app/routers/analyze.py         # Extended CandidateResponse with new fields
web/backend/app/routers/drift.py           # Summary endpoint
web/backend/app/models/api.py              # New/extended response models
```

---

## Phase 2 — Core Features (3 agents, run in parallel after Phase 1)

### Agent 5: Organization & Multi-Repo

**Depends on:** Agent 1 (Auth) for user/org model

**Scope:**

Backend:
- New router: `web/backend/app/routers/org.py`
- Org dashboard data aggregation (scan multiple repos, aggregate drift/conformance status)
- Pattern normalization engine (find same-intent libraries across repos)
- Rollout planner (select repos + library → preview policy evaluation per repo → batch PR plan)
- Compliance report generator (JSON/PDF export of conformance + drift status across org)

Frontend:
- New page: `OrgDashboard.tsx` at `/org`
  - Org-level metrics: total repos, total libraries, conformance rate, drift rate
  - Repo list with status indicators (compliant/drifted/unchecked)
  - Library adoption heatmap (which libraries are used where)
  - Pattern normalization view: "These 4 repos implement rate-limiting differently"
- New page: `RolloutPlanner.tsx` at `/org/rollout`
  - Select library + version
  - Select target repos (checkbox list with current version shown)
  - Preview policy evaluation per repo
  - "Create PRs" batch action button
- Compliance report page at `/org/compliance`
  - Filterable report table
  - Export buttons (JSON, CSV)

Files created:
```
ale/org/__init__.py
ale/org/aggregator.py            # Cross-repo status aggregation
ale/org/pattern_detector.py      # Find similar implementations across repos
ale/org/rollout.py               # Rollout planning logic
ale/org/compliance.py            # Report generation
web/backend/app/routers/org.py
web/frontend/src/pages/OrgDashboard.tsx
web/frontend/src/pages/RolloutPlanner.tsx
web/frontend/src/pages/ComplianceReport.tsx
web/frontend/src/components/RepoStatusTable.tsx
web/frontend/src/components/AdoptionHeatmap.tsx
```

API endpoints:
```
GET    /api/org/dashboard               → Aggregate org stats
GET    /api/org/repos                   → List repos with status
GET    /api/org/patterns                → Detected pattern duplications
POST   /api/org/rollout/preview         → Preview rollout plan (policy eval per repo)
POST   /api/org/rollout/execute         → Execute rollout (batch PR creation)
GET    /api/org/compliance              → Compliance report data
GET    /api/org/compliance/export       → Download report (JSON/CSV)
```

---

### Agent 6: Policy Management & Approval Workflows

**Depends on:** Agent 1 (Auth) for roles/approvals

**Scope:**

Backend:
- New router: `web/backend/app/routers/policy.py`
- Wraps existing `ale/sync/policy.py` (which exists but isn't exposed via API yet)
- Policy CRUD (create, update, delete policy sets)
- Policy simulation engine: "What if library X is applied to repo Y?" → which rules fire, allow/deny/require_approval
- Approval workflow engine: route require_approval decisions to reviewers, track approval state
- Policy history/audit trail

Frontend:
- New page: `PolicyEditor.tsx` at `/policies`
  - List all policy sets
  - Form-based YAML editor for policy rules
  - Rule builder: add allow/deny/require_approval rules with conditions
  - Test panel: enter a context (library + repo), see which rules match
- New page: `PolicySimulation.tsx` at `/policies/simulate`
  - Input: library name/version + target repo
  - Output: rule-by-rule evaluation results
  - Color-coded: green (allow), red (deny), amber (require approval)
- Approval queue page at `/approvals`
  - List pending approvals
  - Approve/reject buttons with context display
  - Approval history

Files created:
```
ale/sync/approval.py                # Approval state machine
ale/sync/policy_simulator.py        # Simulation engine
web/backend/app/routers/policy.py
web/backend/app/routers/approvals.py
web/frontend/src/pages/PolicyEditor.tsx
web/frontend/src/pages/PolicySimulation.tsx
web/frontend/src/pages/Approvals.tsx
web/frontend/src/components/RuleBuilder.tsx
web/frontend/src/components/SimulationResult.tsx
```

API endpoints:
```
GET    /api/policies                     → List policy sets
POST   /api/policies                     → Create policy set
PUT    /api/policies/{id}                → Update policy set
DELETE /api/policies/{id}                → Delete policy set
POST   /api/policies/simulate            → Run simulation
GET    /api/approvals                    → List pending approvals
POST   /api/approvals/{id}/approve       → Approve
POST   /api/approvals/{id}/reject        → Reject
GET    /api/approvals/history            → Approval history
```

---

### Agent 7: LLM Integration & Cost Controls

**Depends on:** Agent 2 (Generator) for enrichment surface, Agent 1 (Auth) for per-user key management, Agent 4 (Phase 2 analyzer) for IR-based candidate data to enrich

**Scope:**

Backend:
- New router: `web/backend/app/routers/llm.py`
- LLM provider abstraction (wraps `anthropic` SDK, supports BYOK)
- Key management: per-user/org API key storage (encrypted at rest)
- Cost tracking: log every LLM call with token counts, estimated cost
- Rate limiting: per-user/org daily/monthly caps
- Feature toggles: admin can enable/disable specific LLM features
- Outcome-based discovery: LLM-powered goal → library recommendation mapping
- Enrichment pipeline: improve library clarity, security, robustness suggestions
- **Analyzer Phase 3 — LLM-powered candidate enrichment** (implements the `deep` depth mode):
  - Takes Phase 2 IR output (symbols, dependency graph, call context) as structured input
  - Generates human-readable `context_summary`: what the module does, what problem it solves, why it's a good extraction candidate, how it fits in the app architecture
  - Generates `description` upgrade: replaces the generic "Utility module: X" with a real explanation
  - Suggests tags and capability labels derived from semantic understanding
  - Flags architectural concerns the heuristic scorer can't detect (e.g., "this module has hidden coupling to the database layer via a global config object")
  - All LLM calls use **IR summaries and symbol signatures, not raw source code** (privacy-preserving by default)
  - Shows "What will be sent" preview before any LLM call

Frontend:
- LLM settings page at `/settings/llm`
  - BYOK key entry (encrypted, show masked)
  - Org-managed vs BYOK toggle
  - Usage dashboard: calls today/month, estimated cost, limit progress bar
  - Feature toggles (admin view)
  - Rate limit status display
- Outcome-based discovery integration in Registry:
  - "Describe what you need" natural language input
  - LLM processes goal → extracts capabilities/tags → searches registry
  - Shows "Outcome Preview Plan" for top results
- Enrichment integration in Generator:
  - "Enhance with AI" button shows diff preview
  - "What will be sent" transparency panel before any LLM call
  - Accept/reject individual suggestions
- **Analyzer `deep` mode integration:**
  - When user selects "deep" analysis depth, results include LLM-enriched descriptions
  - Each candidate card shows an "AI-enriched" badge when description was LLM-generated
  - "Enrich" button on individual candidates (for quick/standard results) to selectively upgrade descriptions via LLM

Files created:
```
ale/llm/__init__.py
ale/llm/provider.py              # LLM abstraction (Claude API wrapper)
ale/llm/cost_tracker.py          # Usage logging + cost estimation
ale/llm/rate_limiter.py          # Per-user/org rate limits
ale/llm/enrichment.py            # Library enrichment pipeline
ale/llm/outcome_discovery.py     # Goal → recommendation mapping
ale/llm/candidate_enrichment.py  # Analyzer Phase 3: IR → LLM → rich descriptions
web/backend/app/routers/llm.py
web/frontend/src/pages/LLMSettings.tsx
web/frontend/src/components/OutcomeDiscovery.tsx   # Goal input + results
web/frontend/src/components/EnrichmentPanel.tsx    # Diff-based suggestions
web/frontend/src/components/UsageDashboard.tsx     # Cost/rate display
web/frontend/src/components/TransparencyPanel.tsx  # "What will be sent" preview
```

API endpoints:
```
POST   /api/llm/discover              → Outcome-based discovery (goal → recommendations)
POST   /api/llm/enrich                → Enrich library draft
POST   /api/llm/enrich-candidate      → Enrich single analyzer candidate with LLM context
POST   /api/llm/preview-plan          → Generate Outcome Preview Plan
GET    /api/llm/usage                 → Current usage stats
PUT    /api/llm/settings              → Update LLM settings (keys, toggles)
GET    /api/llm/settings              → Get current LLM settings
POST   /api/llm/check-prompt          → Preview what would be sent to LLM
```

---

## Phase 3 — Platform Hardening (1 agent, after Phase 2)

### Agent 8: Security Posture, Extensibility & Webhooks

**Depends on:** Agent 1 (Auth), Agent 6 (Policy), Agent 7 (LLM) — this agent hardens everything built in Phase 1 & 2

**Scope:**

Security Posture:
- Audit log system: durable, append-only log of all security-relevant events
  - Org connection changes, permission changes, approvals, PR creation, rollback actions
  - Every conformance run, drift check, library publish, LLM call
- Sandbox isolation for repo analysis (subprocess isolation, temp directories, no ambient authority)
- Data boundary enforcement (code ingress/egress controls)
- Secrets detection (prevent credentials in libraries/policies)
- Request logging middleware (all API calls logged with user, timestamp, action)

Extensibility:
- Plugin registration system: register custom validators, gates, scoring dimensions
- Custom gate definitions: define extra gates beyond schema/semantic/hooks
- Webhook system: push notifications on events (library published, drift detected, conformance failure, approval needed)
- CI/CD integration templates: GitHub Actions / GitLab CI YAML templates that call the API

Backend:
```
ale/security/__init__.py
ale/security/audit_log.py         # Append-only audit log
ale/security/sandbox.py           # Subprocess isolation for analysis
ale/security/secrets_scanner.py   # Detect credentials in content
ale/extensions/__init__.py
ale/extensions/plugin_registry.py # Register/discover plugins
ale/extensions/custom_gates.py    # Custom gate definitions
ale/extensions/webhooks.py        # Webhook dispatch
web/backend/app/routers/audit.py
web/backend/app/routers/extensions.py
web/backend/app/routers/webhooks.py
web/backend/app/middleware/audit_logging.py  # Request-level audit middleware
```

Frontend:
```
web/frontend/src/pages/AuditLog.tsx           # Searchable audit trail
web/frontend/src/pages/WebhookSettings.tsx    # Configure webhook endpoints
web/frontend/src/pages/ExtensionManager.tsx   # View/register plugins
```

API endpoints:
```
GET    /api/audit                         → Query audit log (filterable)
GET    /api/audit/export                  → Export audit log
GET    /api/extensions                    → List registered extensions
POST   /api/extensions/validators         → Register custom validator
POST   /api/extensions/gates              → Register custom gate
POST   /api/extensions/scoring            → Register custom scoring dimension
GET    /api/webhooks                      → List configured webhooks
POST   /api/webhooks                      → Create webhook
PUT    /api/webhooks/{id}                 → Update webhook
DELETE /api/webhooks/{id}                 → Delete webhook
POST   /api/webhooks/{id}/test            → Test fire webhook
```

---

## Dependency Graph

```
                    ┌──────────────────┐
                    │  Phase 1 (parallel) │
                    └──────────────────┘
        ┌───────────┬──────────┬───────────┐
        ▼           ▼          ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
   │ Agent 1  │ │ Agent 2  │ │Agent 3 │ │ Agent 4  │
   │  Auth &  │ │ Library  │ │  IR    │ │ Enhance  │
   │  RBAC    │ │Generator │ │Explorer│ │ Existing │
   └────┬─────┘ └────┬─────┘ └────────┘ └──────────┘
        │             │           (done)      (done)
        │             │
        ▼             ▼
   ┌──────────────────────────────────┐
   │      Phase 2 (parallel)          │
   └──────────────────────────────────┘
   ┌───────────┬──────────┬───────────┐
   ▼           ▼          ▼           │
┌─────────┐ ┌─────────┐ ┌─────────┐  │
│ Agent 5  │ │ Agent 6  │ │ Agent 7 │  │
│ Org &    │ │ Policy & │ │  LLM &  │  │
│Multi-Repo│ │Approvals │ │  Cost   │  │
└────┬─────┘ └────┬─────┘ └────┬────┘  │
     │             │            │       │
     └─────────────┴────────────┘       │
                   │                    │
                   ▼                    │
          ┌──────────────────┐          │
          │  Phase 3          │          │
          └──────────────────┘          │
                   │                    │
                   ▼                    │
            ┌─────────────┐             │
            │   Agent 8    │◀───────────┘
            │  Security,   │
            │Extensibility,│
            │  Webhooks    │
            └──────────────┘
```

---

## Conflict Avoidance Strategy

Each agent owns specific files. Shared files are coordinated:

| Shared File | Coordination Rule |
|---|---|
| `App.tsx` (routes) | Each agent adds their own routes. Use unique route prefixes. Merge at end of each phase. |
| `Layout.tsx` (nav) | Agent 4 refactors navItems into a config array. Other agents append to it. |
| `types/index.ts` | Each agent appends new interfaces at the end. No modification of existing types. |
| `api/client.ts` | Each agent appends new functions at the end. No modification of existing functions. |
| `models/api.py` | Each agent appends new Pydantic models at the end. |
| `main.py` | Each agent adds one `include_router()` line. |

**Rule:** Agents must NOT modify existing functions/types/components created by other agents. Only append new code or create new files.

---

## Estimated Scope Per Agent

| Agent | New Backend Files | New Frontend Files | New Endpoints | Complexity |
|---|---|---|---|---|
| 1: Auth | 5 | 5 | 11 | High |
| 2: Generator | 2 | 5 | 6 | High |
| 3: IR Explorer | 0 | 4 | 0 | Medium |
| 4: Enhance Pages | 3 | 3 + 5 modified | 4 | Medium-High |
| 5: Org/Multi-Repo | 5 | 5 | 7 | High |
| 6: Policy/Approvals | 3 | 5 | 9 | High |
| 7: LLM/Cost | 5 | 5 | 7 | High |
| 8: Security/Ext | 7 | 3 | 12 | Very High |
| **Total** | **30** | **35+** | **56** | |

---

## Navigation Structure (Final)

```
Sidebar:
├── Registry          /                     (existing, enhanced)
├── Analyzer          /analyze              (existing, enhanced)
├── Generator         /generate             (new — Agent 2)
├── IR Explorer       /ir                   (new — Agent 3)
├── Conformance       /conformance          (existing, enhanced)
├── Drift             /drift                (existing, enhanced)
├── Policies          /policies             (new — Agent 6)
├── Approvals         /approvals            (new — Agent 6)
├── Organization      /org                  (new — Agent 5)
│   ├── Dashboard     /org
│   ├── Rollout       /org/rollout
│   └── Compliance    /org/compliance
├── Audit Log         /audit                (new — Agent 8)
└── Settings          /settings             (new — Agent 1 + 7)
    ├── API Keys      /settings/api-keys
    ├── LLM           /settings/llm
    ├── Webhooks      /settings/webhooks
    └── Extensions    /settings/extensions
```

---

## Agent Work Instructions Template

Each agent receives:
1. This plan document (for context)
2. The feature spec (`docs/web-portal-features.md`)
3. Architecture conventions (from the audit above):
   - Backend pattern: FastAPI router → Pydantic models → core ALE module
   - Frontend pattern: Page component → React Query (useQuery/useMutation) → api/client.ts → types/index.ts
   - Styling: Tailwind CSS with existing color scheme (indigo primary, gray neutral, emerald/amber/red status)
   - Components: Extend existing Badge, ScoreBar, GateResult, EmptyState patterns
   - Error handling: HTTPException (backend), ApiError (frontend), error/loading/empty states on every page
4. Their specific scope from this plan
5. File ownership boundaries (which files they create, which shared files they can append to)

---

## Execution Order Summary

```
Week 1:  Launch Agents 1, 2, 3, 4 in parallel
         ├── Agent 3 (IR Explorer) finishes first (smallest scope, no backend)
         ├── Agent 4 (Enhance Pages) finishes second
         ├── Agent 2 (Generator) finishes third
         └── Agent 1 (Auth) finishes last (most foundational)

Week 2:  Merge Phase 1 → Launch Agents 5, 6, 7 in parallel
         ├── All three have similar complexity
         └── Can run concurrently due to separate file ownership

Week 3:  Merge Phase 2 → Launch Agent 8
         └── Hardens everything, adds cross-cutting concerns

Week 4:  Integration testing, polish, final merge
```
