"""Reference runner for Agentic Library validation hooks.

This is gate 3 of 3 in the executable specification. The reference runner:
1. Loads an Agentic Library and validates it (schema + semantic)
2. Executes declared validation hooks
3. Reports standard pass/fail results

The goal is a stable baseline so independent tools align on the same contract.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ale.spec import SPEC_VERSION
from ale.spec.schema_validator import validate_schema
from ale.spec.semantic_validator import validate_semantics, Severity


@dataclass
class HookResult:
    """Result of executing a single validation hook."""

    description: str
    hook_type: str
    passed: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    error: str = ""


@dataclass
class RunnerResult:
    """Full result of a reference runner execution."""

    library_name: str
    library_version: str
    spec_version: str
    schema_passed: bool
    semantic_passed: bool
    schema_errors: list[str] = field(default_factory=list)
    semantic_errors: list[str] = field(default_factory=list)
    semantic_warnings: list[str] = field(default_factory=list)
    hook_results: list[HookResult] = field(default_factory=list)
    total_duration_ms: int = 0

    @property
    def all_passed(self) -> bool:
        """All three gates passed: schema, semantics, and hooks."""
        hooks_ok = all(h.passed for h in self.hook_results) if self.hook_results else True
        return self.schema_passed and self.semantic_passed and hooks_ok

    @property
    def hooks_passed(self) -> bool:
        if not self.hook_results:
            return True
        return all(h.passed for h in self.hook_results)

    def summary(self) -> str:
        lines = [
            f"Library: {self.library_name} v{self.library_version}",
            f"Spec Version: {self.spec_version}",
            f"Schema:    {'PASS' if self.schema_passed else 'FAIL'}",
            f"Semantics: {'PASS' if self.semantic_passed else 'FAIL'}",
        ]
        if self.hook_results:
            passed = sum(1 for h in self.hook_results if h.passed)
            total = len(self.hook_results)
            lines.append(f"Hooks:     {passed}/{total} passed")
        else:
            lines.append("Hooks:     (none declared)")
        lines.append(f"Overall:   {'PASS' if self.all_passed else 'FAIL'}")
        lines.append(f"Duration:  {self.total_duration_ms}ms")
        return "\n".join(lines)


class ReferenceRunner:
    """Executes the full validation pipeline for an Agentic Library."""

    def __init__(self, working_dir: str | Path | None = None):
        """Initialize the reference runner.

        Args:
            working_dir: Directory to execute hooks in (e.g., the target repo).
                         Defaults to current working directory.
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def run(self, library_path: str | Path) -> RunnerResult:
        """Execute the full validation pipeline.

        1. Parse the library file
        2. Validate schema (gate 1)
        3. Validate semantics (gate 2)
        4. Execute validation hooks (gate 3)
        """
        start = time.monotonic()
        path = Path(library_path)

        # Parse
        with open(path) as f:
            data = yaml.safe_load(f)

        lib = data.get("agentic_library", {})
        manifest = lib.get("manifest", {})

        result = RunnerResult(
            library_name=manifest.get("name", "unknown"),
            library_version=manifest.get("version", "0.0.0"),
            spec_version=manifest.get("spec_version", "unknown"),
        )

        # Gate 1: Schema
        schema_issues = validate_schema(data)
        result.schema_passed = len(schema_issues) == 0
        result.schema_errors = schema_issues

        if not result.schema_passed:
            result.total_duration_ms = int((time.monotonic() - start) * 1000)
            return result

        # Gate 2: Semantics
        sem_result = validate_semantics(data)
        result.semantic_passed = sem_result.passed
        result.semantic_errors = [i.message for i in sem_result.errors]
        result.semantic_warnings = [i.message for i in sem_result.warnings]

        if not result.semantic_passed:
            result.total_duration_ms = int((time.monotonic() - start) * 1000)
            return result

        # Gate 3: Hooks
        for validation in lib.get("validation", []):
            hook = validation.get("hook")
            if hook:
                hook_result = self._execute_hook(validation, hook)
                result.hook_results.append(hook_result)

        result.total_duration_ms = int((time.monotonic() - start) * 1000)
        return result

    def _execute_hook(self, validation: dict, hook: dict) -> HookResult:
        """Execute a single validation hook."""
        hook_type = hook.get("type", "unknown")
        description = validation.get("description", "unnamed validation")
        timeout = hook.get("timeout_seconds", 60)
        expected_exit = hook.get("expected_exit_code", 0)

        if hook_type == "command":
            return self._run_command_hook(description, hook, timeout, expected_exit)
        elif hook_type == "assertion":
            return self._run_assertion_hook(description, hook)
        else:
            return HookResult(
                description=description,
                hook_type=hook_type,
                passed=False,
                error=f"Unknown hook type: {hook_type}",
            )

    def _run_command_hook(
        self, description: str, hook: dict, timeout: int, expected_exit: int
    ) -> HookResult:
        """Execute a command-based validation hook."""
        command = hook.get("command", "")
        if not command:
            return HookResult(
                description=description,
                hook_type="command",
                passed=False,
                error="Hook has type 'command' but no 'command' field.",
            )

        start = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = int((time.monotonic() - start) * 1000)
            return HookResult(
                description=description,
                hook_type="command",
                passed=proc.returncode == expected_exit,
                exit_code=proc.returncode,
                stdout=proc.stdout[:5000],
                stderr=proc.stderr[:5000],
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            return HookResult(
                description=description,
                hook_type="command",
                passed=False,
                error=f"Hook timed out after {timeout}s.",
                duration_ms=timeout * 1000,
            )
        except Exception as e:
            return HookResult(
                description=description,
                hook_type="command",
                passed=False,
                error=str(e),
            )

    def _run_assertion_hook(self, description: str, hook: dict) -> HookResult:
        """Execute an assertion-based validation hook.

        Assertion hooks declare a condition as a command that should exit 0 if true.
        """
        command = hook.get("command", "")
        if not command:
            return HookResult(
                description=description,
                hook_type="assertion",
                passed=False,
                error="Assertion hook has no 'command' field.",
            )

        # Assertions are just commands with exit-code semantics
        return self._run_command_hook(description, hook, timeout=30, expected_exit=0)
