"""Schema validator — structural validation using JSON Schema.

This is gate 1 of 3 in the executable specification. It validates that
an Agentic Library file conforms to the required structure before any
semantic or runtime checks.
"""

from __future__ import annotations

from ale.spec.schema import get_schema


def validate_schema(data: dict) -> list[str]:
    """Validate a parsed Agentic Library dict against the JSON Schema.

    Args:
        data: The full parsed YAML/JSON dict (with top-level 'agentic_library' key).

    Returns:
        List of error messages. Empty list means valid.
    """
    issues: list[str] = []
    schema = get_schema()

    # Walk the schema manually since jsonschema may not be available.
    # This provides a pragmatic structural validator that covers the
    # critical required/type/enum checks without adding a dependency.
    _validate_node(data, schema, "", issues)

    return issues


def _validate_node(data, schema: dict, path: str, issues: list[str]):
    """Recursively validate data against a JSON Schema node."""
    schema_type = schema.get("type")

    # Type check
    if schema_type and not _type_matches(data, schema_type):
        issues.append(f"{path or '/'}: expected type '{schema_type}', got {type(data).__name__}")
        return  # Don't recurse into wrong types

    # Enum check
    if "enum" in schema:
        if data not in schema["enum"]:
            issues.append(f"{path or '/'}: value '{data}' not in allowed values {schema['enum']}")

    # minLength for strings
    if schema_type == "string" and isinstance(data, str):
        min_len = schema.get("minLength", 0)
        if len(data) < min_len:
            issues.append(f"{path or '/'}: string too short (min {min_len}, got {len(data)})")

    # Pattern for strings
    if schema_type == "string" and "pattern" in schema and isinstance(data, str):
        import re

        if not re.match(schema["pattern"], data):
            issues.append(f"{path or '/'}: string '{data}' does not match pattern '{schema['pattern']}'")

    # Required properties for objects
    if schema_type == "object" and isinstance(data, dict):
        for req in schema.get("required", []):
            if req not in data:
                issues.append(f"{path or '/'}: missing required property '{req}'")

        # Validate known properties
        props = schema.get("properties", {})
        for key, value in data.items():
            if key in props:
                _validate_node(value, props[key], f"{path}.{key}", issues)

    # Array items
    if schema_type == "array" and isinstance(data, list):
        min_items = schema.get("minItems", 0)
        if len(data) < min_items:
            issues.append(f"{path or '/'}: array too short (min {min_items}, got {len(data)})")

        items_schema = schema.get("items")
        if items_schema:
            # Handle oneOf in items
            if "oneOf" in items_schema:
                for i, item in enumerate(data):
                    matched = False
                    for option in items_schema["oneOf"]:
                        test_issues: list[str] = []
                        _validate_node(item, option, f"{path}[{i}]", test_issues)
                        if not test_issues:
                            matched = True
                            break
                    if not matched:
                        issues.append(
                            f"{path}[{i}]: item does not match any of the allowed schemas"
                        )
            else:
                for i, item in enumerate(data):
                    _validate_node(item, items_schema, f"{path}[{i}]", issues)


def _type_matches(data, schema_type: str) -> bool:
    """Check if data matches the expected JSON Schema type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }
    expected = type_map.get(schema_type)
    if expected is None:
        return True  # Unknown type, don't block
    # In YAML, booleans can be parsed as bool, but ints shouldn't match bool
    if schema_type == "integer" and isinstance(data, bool):
        return False
    return isinstance(data, expected)
