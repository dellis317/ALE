# Agentic Library Specification v0.1

## What is an Agentic Library?

An Agentic Library is a **blueprint** — a structured set of instructions that an AI coding agent
can follow to implement a feature **natively** in any target project, in any language and framework.

Unlike traditional libraries (which ship compiled code + dependencies), an Agentic Library ships
**knowledge**: what to build, how to build it, what to watch out for, and how to verify it works.

## File Format

Agentic Libraries are stored as YAML files with the `.agentic.yaml` extension.

## Structure

### 1. Manifest

```yaml
agentic_library:
  manifest:
    name: "rate-limiter"                    # Required. Kebab-case identifier.
    version: "1.0.0"                        # Required. SemVer.
    description: "Token bucket rate limiter with sliding window support"  # Required.
    source_repo: "https://github.com/..."   # Optional. Where this was extracted from.
    complexity: "moderate"                   # trivial | simple | moderate | complex
    tags: ["networking", "security"]         # Freeform tags for discovery.
    language_agnostic: true                  # Can be implemented in any language?
    target_languages: []                     # If not agnostic, which languages?
```

### 2. Overview

A human-readable explanation of what the feature does, why it's useful, and the core concepts.

```yaml
  overview: |
    A token bucket rate limiter that controls request throughput. Supports
    per-key limits (e.g., per user, per IP) with configurable burst allowance
    and sliding window tracking...
```

### 3. Instructions

Step-by-step implementation guide. Each step should be clear enough that an AI agent can
follow it without seeing the original source code.

```yaml
  instructions:
    - step: 1
      title: "Create the token bucket data structure"
      description: |
        Implement a TokenBucket class/struct that tracks:
        - Maximum tokens (capacity)
        - Current token count
        - Refill rate (tokens per second)
        - Last refill timestamp
      code_sketch: |
        class TokenBucket:
            capacity: int
            tokens: float
            refill_rate: float
            last_refill: timestamp
      notes: "Use monotonic clock for timestamps to avoid clock drift issues"
```

### 4. Guardrails

Constraints the implementation MUST, SHOULD, or MAY follow.

```yaml
  guardrails:
    - rule: "Must be thread-safe / concurrency-safe"
      severity: "must"
      rationale: "Rate limiters are typically accessed from multiple threads/requests"
    - rule: "Should use atomic operations where possible instead of locks"
      severity: "should"
      rationale: "Performance in hot paths"
```

### 5. Validation

Testable criteria to verify the implementation is correct.

```yaml
  validation:
    - description: "Requests within limit are allowed"
      test_approach: "Send N requests where N <= limit, all should succeed"
      expected_behavior: "All requests return allow=true"
    - description: "Requests exceeding limit are rejected"
      test_approach: "Send N+1 requests where N = limit"
      expected_behavior: "Last request returns allow=false"
```

### 6. Capability Dependencies

Abstract capabilities the target project needs (NOT specific library names).

```yaml
  capability_dependencies:
    - "caching"        # Needs some form of key-value storage
    - "logging"        # Should be able to log rate limit events
```

### 7. Framework Hints (Optional)

Implementation notes for specific frameworks.

```yaml
  framework_hints:
    express: "Implement as Express middleware"
    django: "Implement as Django middleware class"
    fastapi: "Implement as FastAPI dependency"
```

## Design Principles

1. **Language-Agnostic First**: Instructions should describe *what* to build, not *how* in a
   specific language. Use pseudocode in code sketches.

2. **Self-Contained**: An agent should be able to implement the feature using ONLY the agentic
   library file — no need to reference the original source.

3. **Native Integration**: The result should look like it was hand-written for the target project,
   not like a foreign transplant.

4. **Security by Default**: Guardrails should encode security best practices relevant to the
   feature.

5. **Verifiable**: Every library must include validation criteria that can be turned into tests.
