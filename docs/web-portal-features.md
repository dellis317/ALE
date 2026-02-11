# ALE Web Portal — Feature Summary

## 1. Registry Browser (Marketplace + Discovery)
The registry shouldn't force users to think in "which library do I want?" first. It should start with **what outcome they want**, then map that goal to **verified** libraries and a **stack-aware preview plan**. This is the 10x shift: discovery becomes a guided "get me to X safely" flow, not a browsing experience.

- **Library catalog** — paginated list of all published agentic libraries with sort/filter
- **Outcome-Based Discovery (goal → recommendation)** — a first-class entry point where users describe a goal (e.g., *"add rate limiting to FastAPI"*) and the portal:
  - asks for **stack constraints** (language/framework/runtime/policy constraints)
  - recommends **verified** libraries that can achieve the goal
  - generates a tailored **Outcome Preview Plan** (see library detail page) so users can evaluate fit without hunting through pages

### LLM Integration and Cost Management
The portal includes optional LLM-backed experiences (e.g., outcome preview refinement, editor "enrichment," and explanation/clarity improvements). Because this is a high-trust surface, the portal must have a **product-level stance** on **who supplies keys**, **who pays**, **how usage is limited**, and **how previews work without exposing sensitive code**.

- **API keys / token stance**
  - **Users bring their own API keys by default (BYOK)** for any LLM calls. Keys are configured per user/org and are not stored in libraries, policies, or registry artifacts.
  - The portal may support a **brokered-token mode (org-managed)** as an explicit admin configuration for centralized billing and governance. This is opt-in and surfaced clearly in UI ("LLM calls are billed to: You / Your org").

- **Cost controls (limits + predictability)**
  - **Hard limits** per org and per user (daily/monthly call caps) for any LLM-backed feature.
  - **Per-action budgeting**: each LLM-backed action shows an estimated request size category (small/medium/large) and enforces a max for that action to prevent surprise usage.
  - **Feature-level toggles**: admins can disable LLM features entirely, or allow only certain actions (e.g., allow "editor clarity suggestions," disallow "repo-context prompts").
  - **Strict "no silent calls" rule**: any LLM usage is user-initiated, visible, and recorded (see Security Posture → Audit logs).

- **Abuse prevention + rate limits**
  - **Rate limits** on LLM-triggering endpoints (per user/org) separate from general API rate limits to prevent credential burn and denial-of-wallet scenarios.
  - **Quotas + backoff**: when limits are hit, the portal degrades gracefully (non-LLM previews remain available) and provides explicit messaging on what was blocked and why.
  - **Prompt/content safety guardrails**: LLM calls operate on bounded inputs (see below), and outputs are treated as suggestions requiring human acceptance (diff-based) rather than auto-applied changes.

- **Preview without sharing sensitive code or API keys (privacy-preserving evaluation)**
  - **No-code-required preview path**: Outcome Preview Plans and consumer-ready previews can be generated from **library metadata** (manifest, capabilities, guardrails, compatibility matrix, validation criteria) plus **user-provided stack constraints**—without ingesting repo code.
  - **Sandbox-first evaluation**: users can run **Try in sandbox repo** to see diffs + hook results without connecting their real repo, keeping evaluation isolated from sensitive codebases.
  - **LLM prompts are minimized by default**: if LLM assistance is enabled, the portal prefers **derived artifacts** (IR summaries, dependency graphs, high-level constraints) over raw code, and provides an explicit "what will be sent" preview before any call.
  - **Key isolation**: users can use LLM-backed features without sharing keys with the publisher/registry; keys are supplied by the consumer org/user (BYOK) or by an explicitly configured org broker mode.

- **Search (goal-aware)** — full-text search plus faceted filtering by tags, capabilities, complexity, language, framework, verification status—**augmented with user goals** so results rank by *expected fit for the described outcome*, not just metadata relevance
- **Library detail page** — full spec view: manifest, overview, instructions (step-by-step), guardrails, validation criteria, abstraction boundary, compatibility matrix, migration history
  - **Outcome Preview Plan** *(new)* — when a user arrives with a goal (or enters one on the page), the portal generates a plan preview that answers: *"If I use this library to achieve my goal in my stack, what will happen?"*
    - **Inputs:** user goal (free text + capability selection), stack constraints (language/framework, repo characteristics where available), and any declared non-goals/constraints
    - **Output:** a concise, consumer-readable plan that:
      - maps the goal → the library's capabilities ("what this enables")
      - highlights which instructions/steps are likely to apply *as-is* vs need parameterization
      - calls out expected integration points (where in the app it will attach)
      - flags compatibility or policy risks *before* sandbox testing (e.g., mismatch with framework constraints)
    - **Purpose:** users can judge fit by outcome alignment first, then use **Preview mode** and **Sandbox Testing** to validate with evidence
- **Version history** — see all versions of a library, diff between versions, breaking change indicators
- **Executable Verification** — executable verification story that enables one-click independent replay of the 3 gates (schema, semantic, hooks) with captured inputs, deterministic runners, and an attestation artifact for local or CI verification.
- **Quality signals** — ratings, download count, maintainer info, last updated
- **Consumer-ready view** — a prominent "how to apply" summary that mirrors what appears in **Preview mode** (the consumer rendering of steps + guardrails), plus a clear path to **Sandbox Testing** so consumers can judge fit *by actually trying the output* before adopting

### Sandbox Testing
Preview mode tells you what the library *claims* it will do. Sandbox Testing answers: **"Can I test this library's output without touching my codebase?"** The portal should make **Try in sandbox repo** a first-class action on every library detail page.

- **Try in sandbox repo (ephemeral environment)**
  - From the library detail page (or Preview mode / Outcome Preview Plan), the user clicks **Try in sandbox repo**.
  - The portal provisions an **ephemeral sandbox workspace** (isolated from the user's real repo) specifically for evaluation.
  - The sandbox run is treated as *trial output*—it produces results and evidence without changing the user's existing codebase.

- **What happens in the sandbox**
  - **Generate output** — the portal applies the agentic library into the sandbox workspace (using the library's instructions/guardrails as the generation plan).
  - **Run hooks** — the portal executes the library's validation hooks inside the sandbox run, capturing:
    - pass/fail
    - stdout/stderr
    - durations
  - **Show diffs + results** — the portal presents:
    - a diff view of "what would change" (files added/modified in the sandbox)
    - the full hook results and gate evidence
    - any schema/semantic/hook failures as actionable feedback

- **What the user gets (without adopting yet)**
  - A concrete, reviewable "would-be PR" outcome: **diff + evidence** without any write-back to their repo.
  - A reliable way to compare shortlisted libraries beyond reading: run multiple sandbox trials and compare diffs/results side-by-side.

---

### Ecosystem model (who can publish + how discovery works at scale)
A registry browser implies an ecosystem, not just a list. The portal should make the "marketplace loop" explicit: **publish → verify → discover → adopt → earn trust → repeat**.

- **Who can publish**
  - **Org publishers** — teams inside an organization publish to an org-scoped registry (default for internal reuse).
  - **Third-party publishers** — external publishers can publish to broader registries *as long as libraries are verifiable via the same 3-gate conformance pipeline*.
  - **Individuals (optional)** — can publish under a personal identity, but discovery and trust emphasize verification + maintainer standing (see below).

- **Discovery at scale**
  - **Verified-first discovery** — default result ranking and filters bias toward libraries with strong conformance evidence (schema/semantic/hooks) and recent pass history.
  - **Capability-driven navigation — discovery centered on "what this enables"** (capabilities/tags), not just names.
  - **Outcome-based discovery** — users describe goals ("add rate limiting to FastAPI") and the portal routes them to verified options + a stack-aware Outcome Preview Plan, reducing the need to browse and interpret metadata manually.
  - **Compatibility-driven narrowing** — compatibility matrix becomes a first-class filter (language/framework/constraints) so users can quickly find "fits my stack" options.
  - **Trust-aware ranking signals** — beyond text relevance: verification status, conformance recency, adoption/usage signals, maintainer verification, and policy alignment indicators (where applicable).

### Curation models (featured / endorsed)
To keep quality legible as the registry grows, the portal supports curation layers that sit *on top of* the open publishing surface:

- **Featured libraries**
  - A curated set highlighted in search, category pages, and outcome-based recommendations.
  - Selection based on: consistent conformance pass history, clarity in Preview mode, strong compatibility coverage, and clear migration history.

- **Endorsed libraries**
  - A stronger signal than "featured," intended to represent libraries that are recommended for broad adoption.
  - Endorsement requires: verified maintainer(s), stable versioning discipline (breaking-change indicators + migration guidance), and reliable hooks execution.

- **Curator workflow**
  - A reviewer-facing flow to nominate, evaluate, and approve Featured/Endorsed status, with a visible "why endorsed" rationale on the detail page (keeping the signal explainable, not mysterious).

### Deprecation & lifecycle policy (how outdated libraries are managed)
A marketplace needs predictable lifecycle mechanics so users don't adopt dead patterns unknowingly.

- **Library status states**
  - **Active** — current, recommended for new adoption.
  - **Deprecated** — still available, but not recommended for new use; detail page and search/recommendation surfaces show a clear warning.
  - **Archived** — kept for provenance/history and existing consumers, but removed from default discovery views (still directly linkable).

- **Deprecation requirements**
  - Must include: reason for deprecation, recommended replacement (if any), and guidance on migration.
  - Deprecation is reflected in **search and outcome-based recommendation ranking** and library status state alongside conformance history.

- **Consumer communication**
  - Deprecation appears in: library detail page, version history, and registry notifications (so adopters can plan upgrades).
  - Drift/operate screens surface "deprecated in use" as an operational signal alongside version/validation drift.

### Maintainer verification (who is trusted to represent a library)
Because the registry is part of an ecosystem, "maintainer identity" becomes a trust primitive.

- **Maintainer profile**
  - Shows identity, publishing scope (org/team), and library portfolio.
  - Highlights conformance history across maintained libraries (a track record, not just a claim).

- **Verification process**
  - **Verified maintainer** status is granted when the maintainer can be tied to an accountable identity (e.g., org affiliation) and demonstrates adherence to ecosystem quality norms:
    - Libraries consistently pass the 3-gate pipeline
    - Clear versioning and migration notes for breaking changes
    - Responsive upkeep signals (e.g., recent updates where needed, clear deprecation practices)
  - Verified maintainer status becomes a filter/ranking signal and is displayed on library pages.

### Incentives for publishing (why contribute)
To make publishing worthwhile, the portal makes contributions visible and rewarded in ecosystem terms (not just "uploaded a file").

- **Reputation + adoption credit**
  - Maintainers accrue visible reputation via verified libraries, adoption counts, and conformance consistency.
  - Library pages and maintainer profiles make impact legible (who built the blueprint that many teams rely on).

- **Quality-linked visibility**
  - Better conformance posture and clearer consumer UX (Preview mode + Outcome Preview Plan clarity) leads to higher discovery placement and eligibility for Featured/Endorsed status.

- **Operational leverage**
  - Publishing a blueprint reduces repeated work across teams; the portal reflects this by treating high-quality libraries as reusable infrastructure with measurable downstream adoption.

---

## 2. Repo Analyzer
- **Repo input** — accept Git URL *or* connect to GitHub/GitLab orgs, with a security posture appropriate for a high-trust surface (see **Security Posture**)
- **Analysis dashboard** — run analysis at quick/standard/deep depth, show progress
- **Candidate list** — ranked table with overall score and 7-dimension breakdown
- **Candidate detail** — per-candidate view with radar chart of scoring dimensions, source file list, dependency graph, flags/warnings, top reasons
- **Side-by-side comparison** — compare two or more candidates
- **Extraction trigger** — select a candidate and kick off library generation from the UI

## 3. Library Generator / Editor
- **Generation wizard** — step through extraction: select candidate, review initial output, configure LLM enrichment options
- **Live editor** — edit the generated `.agentic.yaml` in-browser with syntax highlighting and real-time validation (schema + semantic errors shown inline)
- **LLM enrichment panel** — send the draft to LLM for feedback on security, robustness, clarity; show suggestions as diffs you accept/reject
- **Preview mode** — rendered view of the library as a consumer would see it (instructions as a step-by-step guide, guardrails as a checklist)
- **Publish flow** — validate and publish to registry directly from the editor

## Security Posture (First-Class, Gating for v0.2+)
The portal touches **source code**, **org connections**, **PR creation**, and (optionally) **LLM calls**. That makes it a **high-trust surface area**. For **v0.2+**, security posture is not "nice to have"—it is a **gating requirement** for shipping and for enabling features like GitHub/GitLab org connections, PR automation, and any LLM-backed flows.

This section is intentionally concrete: it defines (1) the **threats**, (2) the **data boundaries**, and (3) the **controls** required to safely operate a portal that can read many repos and (optionally) propose changes back via PRs.

### Threat model highlights (what we're protecting against)
- **Untrusted repo input** — accepting a Git URL means handling attacker-controlled content (and the knock-on effects of cloning, parsing, and analyzing it).
- **Supply-chain / ecosystem abuse** — a malicious or compromised publisher could try to distribute unsafe instructions; consumers need verifiable evidence rather than trust-by-claim.
- **Over-scoped org access** — connecting to GitHub/GitLab orgs risks granting broader access than needed (repos, teams, metadata).
- **PR creation as an actuator** — one-click PRs are a powerful control action; misuse or compromise can push unwanted changes across many repos.
- **Data exfiltration via logs/exports** — source code, metadata, or credentials leaking into logs, UI rendering, exports, or analytics.
- **LLM interaction risk (if enabled)** — prompts may include sensitive context; outputs may be unsafe or misleading without guardrails and review.

### Data boundaries (code in/out)
The portal must make boundaries explicit and enforceable so users can reason about "what leaves my repo" and "what can change my repo."

- **Code in (ingress)**
  - Ingests source code by cloning repos or reading via provider APIs.
  - Treats all repo content as **untrusted input** (even if it's "our org"), because a compromised repo is still a realistic threat case.

- **Code out (egress)**
  - Default posture: analyzed artifacts are **derived data** (scores, IR summaries, dependency graphs, extracted `.agentic.yaml` drafts), not raw repo dumps.
  - Any UI feature that shows code excerpts should be treated as a deliberate exposure surface (it must be bounded and auditable).

- **Write-back boundary (actuation)**
  - The only intended "write" back to repos is via **reviewable PRs** (and associated metadata), not direct pushes.
  - PR creation is treated as a privileged action constrained by policy and approvals (see "Permission scopes" and "Audit logs").

### Secrets handling (how credentials are treated)
- **No secrets in libraries or policies** — `.agentic.yaml`, policy files, and registry metadata must not carry secrets.
- **Credential isolation** — OAuth tokens / API keys are treated as sensitive; avoid leaking into logs, exports, or UI surfaces.
- **Explicit boundaries** — where the portal stores/uses credentials is clearly separated from user-editable artifacts (libraries, policies, instructions).
- **Prompt hygiene for LLM flows (if enabled)** — prompts should avoid including credentials and avoid including unnecessary raw code; any LLM enrichment is presented as suggestions requiring human acceptance (diff-based).

### Sandboxing (treat analysis as hostile)
Because repos are untrusted inputs, the analysis/generation "playground" must be isolated from where credentials and org repos live.

- **Safe-walled playground vs. app repos**
  - The portal runs analysis/extraction in a **sandboxed execution environment** that is separated from:
    - org tokens / provider credentials,
    - the registry write path,
    - and any systems that can create PRs.
  - The sandbox is treated as a containment zone: it may parse and transform code, but it should not have ambient authority to access other repos or write back.

- **Why this matters**
  - Even if the code is "just being parsed," the system is still handling attacker-controlled input. The architecture assumes compromise is possible in the analysis layer, and therefore **walls it off** from privileged actions and sensitive storage.

### Permission scopes (least privilege by default)
- **Minimal scopes for GitHub/GitLab** — request only what's necessary for the specific action (browse repos, read code, open PRs), and avoid "org-wide" permissions by default.
- **Role-based access is enforced everywhere** — RBAC applies to publishing, approvals, conformance runs, PR creation, and policy edits (not just UI visibility).
- **Policy-enforced blast radius** — automation (drift remediation, rollouts) is constrained by policy so the system cannot exceed declared boundaries.
- **Separation of duties (operationally)**
  - "Read and analyze" does not automatically imply "can publish" or "can open PRs."
  - Where policy demands **require_approval**, approvals are an explicit gate before write-back actions proceed.

### Audit logs (durable evidence, not vibes)
Security is inseparable from explainability. If the portal can touch many repos, it must always be able to answer: "who did what, using what authority, and what changed?"

- **Provenance is audit-grade** — who did what, when, against which repo/library version, with what evidence (gates + outcomes).
- **Security-relevant events are retained** — org connection changes, permission changes, approvals, PR creation, and rollback actions are captured alongside conformance and drift history.
- **Retention is part of "done"** — if an action can't be explained later, it isn't safe enough to automate at scale.

---

## 4. Conformance & Validation
- **Conformance runner** — upload or select a library, run the 3-gate pipeline, show results
- **Gate-by-gate breakdown** — schema results, semantic results (errors + warnings with paths), hook execution results (stdout/stderr, duration, pass/fail)
- **Conformance history** — track conformance runs over time per library
- **Batch validation** — validate all libraries in a registry at once, surface regressions

## Extensibility and Customization
If ALE is an ecosystem, the portal can't be a bottleneck. The web portal should be designed as a **platform surface**: teams keep the core model (schema → semantic → hooks), while tailoring validation, scoring, policy, and UI to their workflow.

### Extension model (what can be customized)
- **Custom validators (semantic extensions)**
  - Add org- or domain-specific semantic checks.
  - Treat these as additional validation units that run alongside built-in gates and produce explainable errors/warnings.

- **Custom gates (beyond the default 3)**
  - Allow teams to define extra gates required in their environment or registry scope.
  - Gate results are replayable and auditable: each gate emits structured evidence and can be verified locally or in CI.

- **Custom scoring dimensions (Analyzer extensions)**
  - Extend or adjust the 7-dimension scoring model with org-specific dimensions and weights (or additional risk flags).
  - Keep the UI explainable: show breakdown and reasons, even when dimensions are custom.

- **Custom policies (policy-as-code extensions)**
  - Support additional policy rule types or org-specific matchers/actions while preserving allow/deny/require_approval.
  - Policy simulation remains the truth surface that explains *why* a rule fired.

- **Custom views (portal UI extensions)**
  - Let orgs define dashboard slices and saved views without forking the portal.
  - Views should be backed by the same programmatic query surface so they can be replicated in internal tooling.

### How extensions plug in (mechanisms)
- **Plugins** — extension mechanism for validators, scoring dimensions, policy matchers/actions, and view definitions.
- **Webhooks-as-extensions** — trigger external systems that compute additional signals/evidence (attached back to library versions, conformance runs, or provenance).
- **Custom gates** — first-class concept so teams can add/require extra gates per org/registry/policy context.

The net effect: the portal stays the reference implementation of the ecosystem mechanics, while workflow evolution happens at the edges.

## 5. Drift Dashboard (Continuous Control, Not Just Reporting)
Drift isn't just an alerting surface—it's a **closed-loop control system** that keeps fleets of repos continuously aligned with verified libraries, with **guardrailed automation**.

- **Fleet view** — all repos with applied libraries, color-coded by drift status (clean, version drift, validation drift, implementation drift)
- **Per-repo detail** — which libraries are applied, what versions, when, current drift state
- **Per-library view** — across all repos, where is this library applied, which repos are up to date vs. drifted
- **Drift alerts** — configurable notifications when drift is detected

- **Automated remediation (guardrailed)**
  - **Staged rollouts** — remediate drift gradually across a selected cohort.
  - **Canaries** — start with a small subset to prove the upgrade path.
  - **Automatic revert on failure** — if conformance gates fail (or a post-apply validation run regresses), revert and record the outcome in provenance.
  - **Policy-driven blast-radius limits** — upgrades/remediations can only touch allowed scopes and only expand rollout when policy permits (and approvals, if required).

- **Upgrade proposals (one-click PR as the control action)**
  - **One-click to generate a PR** that upgrades a drifted repo to the latest library version.
  - PRs include evidence context: drift type, target version, conformance results (pre/post where applicable), and any policy approvals required.
  - When staged rollout/canary mode is enabled, PR creation is **sequenced** by cohort (canary first → expand).

## 6. Sync & Policy Management
- **Policy editor** — create/edit policy sets in YAML with a form-based UI, preview rule matching against test contexts
- **Policy simulation** — "what if I apply library X to repo Y?" — show which rules fire, whether it would be allowed/denied/require approval
- **Provenance timeline** — per-repo audit log of every library application: who, when, what version, validation evidence, commit SHA

- **Closed-loop drift control (operate, not just observe)**
  - **Continuous control posture** — sync detects drift and drives repos back toward a proven state with automation plus guardrails.
  - **Policy as the governor** — policies constrain remediation (what can change, who approves, rollout width).
  - **Evidence as feedback** — conformance results and hook outcomes determine whether to proceed, pause, or revert.

- **Rollback controls** — select a provenance entry and trigger rollback
- **Approval workflows** — when policy says "require approval," route to reviewers with context

## 7. IR Explorer
- **Code graph visualization** — interactive dependency graph of a repo's IR (modules as nodes, dependencies as edges)
- **Symbol browser** — browse functions/classes/constants, see visibility, parameters, return types, side effects, fan-in/fan-out
- **Isolation analysis** — highlight candidate boundaries on the graph, show what's inside vs. what crosses the boundary
- **Multi-language view** — as more parsers ship, show IR from different languages in a unified view

## 8. Organization / Multi-Repo
- **Org dashboard** — overview of all repos, all applied libraries, aggregate drift/compliance status
- **Pattern normalization** — identify the same pattern implemented differently across repos ("12 repos have a rate limiter, 4 different implementations")
- **Rollout planner** — plan a library rollout across N repos: select target repos, preview policy evaluation for each, batch-create PRs
- **Compliance reporting** — exportable reports showing which repos conform to which library versions, audit-ready

## 9. Auth & Access Control
- **User accounts** — login via GitHub/GitLab OAuth
- **Role-based access** — admin, publisher, reviewer, viewer
- **Org/team scoping** — registries and policies scoped to teams
- **API keys** — for CI/CD integration (run conformance checks in pipelines)

## 10. API Layer
- **REST API** — everything the portal does, available programmatically *including extension surfaces* (register/require custom gates, run conformance with org-specific validators, manage policies, publish/query registry data, query drift/provenance, and power custom views in internal tools)
- **Webhooks** — push notifications on: new library published, drift detected, conformance failure, approval needed
- **CI/CD integration** — GitHub Actions / GitLab CI templates that call the API for validation gates
- **CLI sync** — `ale` CLI talks to the same API so portal and CLI are interchangeable

---

## Consumer Journey

The portal becomes clearer when it's organized around the **golden path**: from "I need X" → "it's safely running in my repo with proof." Below are two end-to-end flows, with the **states**, **artifacts**, and **decision points** each screen must support.

### Flow A — Achieve an Outcome Using the Registry (the "consumer" path)

**Trigger:** "I need a rate limiter (or auth guard, cache, retry policy, etc.) in repo Y."

1. **Describe the outcome (goal-first discovery)**
   - **Screen(s):** *Registry Browser → Outcome-Based Discovery / goal-aware Search*
   - **State:** *Goal defined → constraints captured → shortlist formed*
   - **Artifacts:** goal statement, stack constraints, ranked recommendations
   - **Decision points:**
     - Are the recommendations **verified** (schema/semantic/hooks conformance history)?
     - Do they match my **language/framework** constraints?
     - Are they **active vs deprecated**?
     - Are any **featured/endorsed** (curation signals)?

2. **Evaluate (human-readable + outcome-aligned)**
   - **Screen(s):** *Library detail page* + **Outcome Preview Plan** + **Preview mode** + **Try in sandbox repo**
   - **State:** *Shortlist → selected candidate*
   - **Artifacts:** chosen library + version, Outcome Preview Plan, compatibility matrix, guardrails checklist, validation criteria
   - **Decision points:**
     - Does the **Outcome Preview Plan** match what we mean by the goal?
     - Do the **instructions** align with how we build things here?
     - Do the **guardrails** fit our constraints?
     - Can I **try it safely** via **Sandbox Testing** (diff + hook results)?
     - Is the **migration history** acceptable (breaking changes)?
     - Is the **maintainer** verified / credible?
     - If LLM-backed refinement is offered: **who is paying/which key is used**, and is the prompt boundary acceptable?

3. **Preflight in my repo (safe-to-try)**
   - **Screen(s):** *Sync & Policy Management → Policy simulation*
   - **State:** *Selected candidate → approved plan (or blocked)*
   - **Artifacts:** policy simulation report (allowed/denied/require approval + matching rules)
   - **Decision points:**
     - Allowed vs require approval vs denied
     - If approval required: who approves, and on what evidence?

4. **Apply + Prove**
   - **Screen(s):** *Conformance & Validation* + *Provenance timeline*
   - **State:** *Planned → applied → proven*
   - **Artifacts:** conformance results (3-gate breakdown), provenance entry (who/when/version/evidence/commit SHA)
   - **Decision points:**
     - Do all gates pass? If not, stop and iterate.

5. **Operate Over Time (closed-loop drift control)**
   - **Screen(s):** *Drift Dashboard* (+ alerts) + upgrade proposals + rollback/provenance views
   - **State:** *Running → monitored → remediated (staged/canary) → expanded or reverted*
   - **Artifacts:** drift status, one-click PR upgrade proposal, rollback action, recorded evidence in provenance
   - **Decision points:**
     - Drift detected: staged rollout/canary vs defer
     - Validation drift: treat as a release blocker until re-proven
     - Failure during remediation: automatic revert (or manual rollback) within policy blast-radius constraints
     - Deprecation flagged: migrate vs accept risk with explicit acknowledgement

**Definition of "done":** the library is in the repo **and** there is durable evidence: conformance gates + provenance record (audit-ready proof).

---

### Flow B — Turn Existing Code Into a Reusable Library, Then Consume It (the "producer-to-consumer" path)

**Trigger:** "We already implemented X in one repo; we want it reusable everywhere with proof."

1. **Find the best candidate**
   - **Screen(s):** *Repo Analyzer → Candidate list/detail*
   - **State:** *Repo selected → candidate chosen*
   - **Artifacts:** ranked candidate list, 7-dimension breakdown, dependency graph, warnings/flags
   - **Decision points:**
     - Is the boundary clean enough to extract?
     - Do flags (e.g., heavy coupling) make it a bad blueprint?

2. **Generate and refine the blueprint**
   - **Screen(s):** *Library Generator / Editor*
   - **State:** *Draft created → review-ready*
   - **Artifacts:** generated `.agentic.yaml`, inline schema+semantic feedback, accepted/rejected diffs
   - **Decision points:**
     - Fix validation errors until schema + semantic are clean
     - Confirm consumer clarity via Preview mode (steps + guardrails)
     - If LLM enrichment is enabled: ensure the org's key/cost posture is understood and prompts remain within allowed boundaries

3. **Verify (make trust executable)**
   - **Screen(s):** *Conformance & Validation*
   - **State:** *Review-ready → verified*
   - **Artifacts:** gate-by-gate evidence (schema/semantic/hooks), conformance history
   - **Decision points:**
     - Hooks runnable and passing? If not, it's not executable verification, it's just text.

4. **Publish**
   - **Screen(s):** *Publish flow* → *Registry Browser (detail page)*
   - **State:** *Verified → discoverable*
   - **Artifacts:** registry entry, version record, conformance history, executable verification replay bundle/attestation artifact
   - **Decision points:**
     - Publish as verified-only, or allow unverified versions (make the difference legible via replayable evidence)
     - Declare lifecycle intent: active by default, with responsible deprecation
     - Maintainer posture: who owns updates, and whether maintainer verification is in place (or pending)

5. **Consume via Flow A**
   - Once published, the next team follows **Describe outcome → Evaluate (Outcome Preview Plan + Preview + Sandbox) → Preflight (Policy) → Apply + Prove → Operate (drift control)**.

**Definition of "done":** the blueprint is discoverable, consumer-readable (Preview mode), **replayably verified**, and adopted with provenance-backed proof.

---

## Killer Demo (5 minutes)
A single 5-minute sequence should show end-to-end trust, not UI breadth. The demo is optimized around the build order: **API layer first**, then **registry + conformance**.

### Demo script (sequence)
1. **Start at the API (proves it's a platform, not a UI project)**
   - Show REST endpoints for:
     - **Registry list/search** (including goal-aware search inputs)
     - **Library detail**
     - **Conformance run** (trigger the 3 gates and retrieve results)
     - **Fetch verification artifact** (retrieve the captured inputs + deterministic runner metadata + attestation artifact)

2. **Describe an outcome in the Registry Browser**
   - Enter a concrete goal (e.g., "add rate limiting to FastAPI").
   - Provide minimal stack constraints.
   - Show the portal returning verified recommendations ranked by fit.

3. **Open a recommended library detail page (outcome-aligned evaluation)**
   - Show the **Outcome Preview Plan** for that goal/stack.
   - Scroll the consumer-ready view:
     - Instructions
     - Guardrails
     - Compatibility matrix
     - Migration history
   - Show the **Executable Verification** section: how to replay schema → semantic → hooks for this exact version.
   - If showing LLM-backed enhancements: explicitly show **key source (BYOK vs org broker)** and the portal's **usage limits** and "what will be sent" boundary.

4. **Run conformance live (the "proof" step)**
   - Trigger a conformance run for that version.
   - Show the gate-by-gate breakdown:
     - Schema results
     - Semantic results
     - Hook execution results (stdout/stderr, duration, pass/fail)

5. **Wow moment: independent replay**
   - The "wow" is that trust is **executable**:
     - A skeptical lead can one-click replay the same 3 gates with captured inputs and deterministic runners.
     - The system emits an **attestation artifact** that can be verified locally or in CI, without relying on UI signals.

6. **Close with the operational consequence**
   - Point to: conformance history + provenance timeline—evidence that can be replayed later, not a one-time claim.

---

## Potential for Standardization
ALE isn't just a portal for managing internal "agentic libraries"—it's close to a **shareable, interoperable standard** for agentic libraries.

The ingredients are already present across the product surface area:

- **Manifests** (library detail page / full spec view) make libraries addressable and portable across tools and organizations.
- **Validation gates** (schema → semantic → hooks) make correctness machine-checkable, not subjective.
- **Executable verification** makes trust reproducible: independent parties can replay the same gates with captured inputs and deterministic runners, and verify an attestation artifact locally or in CI.
- **Compatibility matrices** make libraries safely reusable across languages/frameworks/constraints, and make upgrade paths explicit.
- **Provenance** (who/when/what version/what evidence) makes adoption auditable, which matters when libraries are applied by agents across many repos.
- **Outcome-based discovery** (goal → verified recommendation → Outcome Preview Plan) makes the ecosystem usable at scale: users don't need to learn a catalog—they can describe what they want to achieve and get stack-aware, evidence-backed options.
- **LLM-backed UX (optional, governed)** can improve clarity and planning, but only with explicit stances on **keys, cost controls, rate limits, and privacy boundaries**—so "preview" and "enrichment" never become an uncontrolled data-exfiltration or denial-of-wallet risk.

Framed this way, the registry becomes a marketplace-like index of interoperable libraries, where:
- Third-party publishers can publish libraries that conform to the same manifest + gates, and
- Independent verifiers can replay conformance and attach results as durable artifacts, and
- Curation + lifecycle mechanics (featured/endorsed, deprecation/archival, maintainer verification) keep quality enforceable and legible as the ecosystem scales, and
- Incentives (reputation, adoption credit, visibility tied to quality) make it rational to invest in well-maintained libraries.

This perspective also raises the leverage of the portal itself: a reference implementation of ecosystem mechanics (publishing, conformance, executable verification, compatibility reporting, provenance, curation, lifecycle), rather than a single-team distribution tool.

---

## Build Order
The realistic build order: **API layer first** (FastAPI wrapping existing modules), then **registry browser + conformance runner** (highest immediate value and core of interoperability/executable verification—and the 5-minute demo), then **drift dashboard + analyzer UI**, then the rest incrementally.
