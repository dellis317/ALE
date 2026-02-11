"""Prompt templates for ALE LLM integration.

Each template uses ``{placeholder}`` syntax for variable substitution via
``str.format()`` or ``str.format_map()``.
"""

# ---------------------------------------------------------------------------
# Library enrichment
# ---------------------------------------------------------------------------

LIBRARY_ENRICHMENT_PROMPT = """\
You are an expert software architect specializing in agentic library design.

Given the following agentic library YAML specification, enrich it by:
1. Improving descriptions to be clearer and more actionable for AI agents.
2. Adding missing guardrails if the library lacks safety constraints.
3. Suggesting additional tags that accurately describe the library's capabilities.
4. Enhancing hook descriptions with concrete expected-behavior notes.
5. Ensuring the specification follows best practices for agent consumption.

Return ONLY the enriched YAML content (no markdown fences, no commentary).
Preserve the existing structure and all fields; only add or improve content.

---
Library YAML:
{yaml_content}
"""

# ---------------------------------------------------------------------------
# Repository analysis
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT = """\
You are a senior code analyst. Analyze the following repository structure and \
source code summaries to identify high-value patterns that could be extracted \
as reusable agentic libraries.

For each candidate you identify, provide:
- A concise name (snake_case)
- A one-sentence description of what the pattern does
- The key source files involved
- An isolation score (0-1) indicating how self-contained the pattern is
- A reuse score (0-1) indicating how broadly useful this pattern would be
- Suggested tags

Repository information:
{repo_summary}

Source file summaries:
{file_summaries}

Return your analysis as a JSON array of candidate objects.
"""

# ---------------------------------------------------------------------------
# Description generation
# ---------------------------------------------------------------------------

DESCRIPTION_PROMPT = """\
You are a technical writer for developer tools. Given the following agentic \
library YAML specification, generate a clear, concise, and informative \
description (2-4 sentences) that explains:
1. What the library does
2. When an AI agent should use it
3. What makes it valuable

Return ONLY the description text, with no extra formatting.

Library YAML:
{yaml_content}
"""

# ---------------------------------------------------------------------------
# Guardrail suggestions
# ---------------------------------------------------------------------------

GUARDRAIL_PROMPT = """\
You are a safety-focused software architect. Given the following agentic \
library specification, suggest guardrails that should be added to ensure \
safe and predictable agent behavior.

For each guardrail, provide:
- "type": one of "pre_check", "post_check", "invariant", "rate_limit", "scope_limit"
- "description": what the guardrail enforces
- "severity": "error" | "warning" | "info"
- "condition": a human-readable condition statement
- "rationale": why this guardrail matters

Return your suggestions as a JSON array of guardrail objects.

Library YAML:
{yaml_content}
"""

# ---------------------------------------------------------------------------
# Human-friendly preview
# ---------------------------------------------------------------------------

PREVIEW_PROMPT = """\
You are a documentation specialist. Given the following agentic library YAML \
specification, generate a human-friendly {format} preview that includes:

1. **Title and version** prominently displayed
2. **Overview** - a clear summary of what the library does
3. **Capabilities** - bulleted list of what the library can do
4. **Guardrails** - safety constraints in plain language
5. **Hooks** - what lifecycle hooks are available and what they do
6. **Usage notes** - when and how an agent should use this library

Make the preview informative and easy to scan. Use proper {format} formatting.

Library YAML:
{yaml_content}
"""
