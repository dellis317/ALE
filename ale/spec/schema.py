"""JSON Schema for the Agentic Library specification.

This is the normative structural definition: it defines required sections,
their types/shapes, and basic cross-field constraints. This schema is the
first gate in the executable spec — if a library doesn't pass schema
validation, it's rejected before any semantic analysis.
"""

from ale.spec import SPEC_VERSION

# The canonical JSON Schema for an Agentic Library YAML file.
# Tools can export this and use it with any JSON Schema validator.
AGENTIC_LIBRARY_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": f"https://ale.dev/schema/agentic-library/v{SPEC_VERSION}",
    "title": "Agentic Library Specification",
    "description": (
        "Schema for an Agentic Library — a portable blueprint that AI agents "
        "follow to implement features natively in any target project."
    ),
    "type": "object",
    "required": ["agentic_library"],
    "additionalProperties": False,
    "properties": {
        "agentic_library": {
            "type": "object",
            "required": ["manifest", "instructions", "guardrails", "validation"],
            "additionalProperties": False,
            "properties": {
                # --- Manifest ---
                "manifest": {
                    "type": "object",
                    "required": ["name", "version", "description", "spec_version"],
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "type": "string",
                            "pattern": "^[a-z][a-z0-9-]*$",
                            "description": "Kebab-case identifier for the library.",
                        },
                        "version": {
                            "type": "string",
                            "pattern": r"^\d+\.\d+\.\d+",
                            "description": "Semantic version of this library.",
                        },
                        "spec_version": {
                            "type": "string",
                            "description": "Version of the ALE spec this library targets.",
                        },
                        "description": {
                            "type": "string",
                            "minLength": 10,
                            "description": "Human-readable description of what this library does.",
                        },
                        "source_repo": {
                            "type": "string",
                            "description": "Git URL of the repo this was extracted from.",
                        },
                        "complexity": {
                            "type": "string",
                            "enum": ["trivial", "simple", "moderate", "complex"],
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "language_agnostic": {
                            "type": "boolean",
                            "default": True,
                        },
                        "target_languages": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                # --- Overview ---
                "overview": {
                    "type": "string",
                    "minLength": 20,
                    "description": "High-level explanation of what this does and why.",
                },
                # --- Instructions ---
                "instructions": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["step", "title", "description"],
                        "additionalProperties": False,
                        "properties": {
                            "step": {
                                "type": "integer",
                                "minimum": 1,
                            },
                            "title": {
                                "type": "string",
                                "minLength": 3,
                            },
                            "description": {
                                "type": "string",
                                "minLength": 10,
                            },
                            "code_sketch": {
                                "type": "string",
                                "description": "Pseudocode or language-agnostic sketch.",
                            },
                            "notes": {"type": "string"},
                            "preconditions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "What must be true before this step runs.",
                            },
                            "touched_surfaces": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Files, modules, or integration points this step affects."
                                ),
                            },
                            "capabilities_used": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Capability dependencies this step relies on.",
                            },
                        },
                    },
                },
                # --- Guardrails ---
                "guardrails": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["rule", "severity"],
                        "additionalProperties": False,
                        "properties": {
                            "rule": {
                                "type": "string",
                                "minLength": 5,
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["must", "should", "may"],
                            },
                            "rationale": {"type": "string"},
                            "enforcement": {
                                "type": "string",
                                "enum": ["machine", "review", "advisory"],
                                "description": (
                                    "How enforceable this guardrail is: "
                                    "'machine' = can be checked automatically, "
                                    "'review' = requires human review, "
                                    "'advisory' = guidance only."
                                ),
                            },
                            "check_command": {
                                "type": "string",
                                "description": (
                                    "Shell command to verify this guardrail (for machine-enforceable)."
                                ),
                            },
                        },
                    },
                },
                # --- Validation ---
                "validation": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["description", "test_approach", "expected_behavior"],
                        "additionalProperties": False,
                        "properties": {
                            "description": {
                                "type": "string",
                                "minLength": 5,
                            },
                            "test_approach": {
                                "type": "string",
                            },
                            "expected_behavior": {
                                "type": "string",
                            },
                            "hook": {
                                "type": "object",
                                "description": "Runnable validation hook for the reference runner.",
                                "required": ["type"],
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["command", "script", "assertion"],
                                    },
                                    "command": {"type": "string"},
                                    "timeout_seconds": {
                                        "type": "integer",
                                        "default": 60,
                                    },
                                    "expected_exit_code": {
                                        "type": "integer",
                                        "default": 0,
                                    },
                                },
                            },
                        },
                    },
                },
                # --- Capability Dependencies ---
                "capability_dependencies": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "required": ["capability", "required"],
                                "properties": {
                                    "capability": {"type": "string"},
                                    "required": {"type": "boolean"},
                                    "description": {"type": "string"},
                                },
                            },
                        ]
                    },
                },
                # --- Abstraction Boundary ---
                "abstraction_boundary": {
                    "type": "object",
                    "description": "Explicit declaration of what this library assumes and touches.",
                    "properties": {
                        "scope": {
                            "type": "string",
                            "description": "What parts of the target project this modifies.",
                        },
                        "assumptions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What must be true about the target project.",
                        },
                        "integration_points": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Where this library connects to existing code.",
                        },
                        "does_not_touch": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Explicit exclusions — what this library will NOT modify.",
                        },
                    },
                },
                # --- Compatibility Matrix ---
                "compatibility": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["target_id", "target_type", "status"],
                        "properties": {
                            "target_id": {"type": "string"},
                            "target_type": {
                                "type": "string",
                                "enum": ["language", "framework", "runtime"],
                            },
                            "target_version": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["supported", "experimental", "deprecated"],
                            },
                            "notes": {"type": "string"},
                        },
                    },
                },
                # --- Framework Hints ---
                "framework_hints": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                # --- Migration ---
                "migration": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["from_version", "to_version", "summary"],
                        "properties": {
                            "from_version": {"type": "string"},
                            "to_version": {"type": "string"},
                            "summary": {"type": "string"},
                            "breaking": {"type": "boolean", "default": False},
                            "steps": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "rollback_guidance": {"type": "string"},
                        },
                    },
                },
                # --- Examples ---
                "examples": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["target", "description"],
                        "properties": {
                            "target": {"type": "string"},
                            "description": {"type": "string"},
                            "code": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


def get_schema() -> dict:
    """Return the canonical JSON Schema for Agentic Library files."""
    return AGENTIC_LIBRARY_SCHEMA
