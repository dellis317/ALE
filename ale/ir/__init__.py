"""Canonical Intermediate Representation (IR) for cross-language normalization.

The IR normalizes what the extractor and generator operate on, providing a
cross-language semantic substrate that sits between language-specific parse
trees (e.g., from Tree-sitter) and the language-agnostic Agentic Library output.

The IR normalizes:
- Code structure (modules, classes, functions, methods)
- Dependencies (imports, calls, references)
- Behavioral contracts (inputs, outputs, side effects)
"""
