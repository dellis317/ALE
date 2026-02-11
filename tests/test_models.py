"""Tests for ALE data models."""

from ale.models.agentic_library import (
    AgenticLibrary,
    Complexity,
    Guardrail,
    InstructionStep,
    ValidationCriterion,
)
from ale.models.candidate import ExtractionCandidate


def test_agentic_library_creation():
    lib = AgenticLibrary(
        name="test-lib",
        description="A test library",
        complexity=Complexity.SIMPLE,
    )
    assert lib.name == "test-lib"
    assert lib.version == "1.0.0"
    assert lib.complexity == Complexity.SIMPLE
    assert lib.language_agnostic is True
    assert lib.instructions == []
    assert lib.guardrails == []


def test_agentic_library_with_full_spec():
    lib = AgenticLibrary(
        name="full-lib",
        description="Fully specified library",
        instructions=[
            InstructionStep(order=1, title="Step 1", description="Do the thing"),
            InstructionStep(order=2, title="Step 2", description="Do the other thing"),
        ],
        guardrails=[
            Guardrail(rule="Must be safe", severity="must"),
        ],
        validation=[
            ValidationCriterion(
                description="It works",
                test_approach="Run it",
                expected_behavior="No errors",
            ),
        ],
    )
    assert len(lib.instructions) == 2
    assert len(lib.guardrails) == 1
    assert len(lib.validation) == 1


def test_candidate_scoring():
    candidate = ExtractionCandidate(
        name="test-util",
        description="A test utility",
        source_files=["utils/test.py"],
        entry_points=["test"],
        isolation_score=0.8,
        reuse_score=0.6,
        complexity_score=0.7,
        clarity_score=0.5,
    )
    # Weighted: 0.8*0.3 + 0.6*0.3 + 0.7*0.2 + 0.5*0.2 = 0.24 + 0.18 + 0.14 + 0.10 = 0.66
    assert abs(candidate.overall_score - 0.66) < 0.01


def test_candidate_summary():
    candidate = ExtractionCandidate(
        name="parser",
        description="JSON parser utility",
        source_files=["utils/parser.py", "utils/parser_helpers.py"],
        entry_points=["parse"],
        isolation_score=0.9,
        reuse_score=0.8,
        complexity_score=0.7,
        clarity_score=0.6,
    )
    summary = candidate.summary()
    assert "parser" in summary
    assert "2 files" in summary


def test_candidate_zero_scores():
    candidate = ExtractionCandidate(
        name="empty",
        description="No scores",
        source_files=[],
        entry_points=[],
    )
    assert candidate.overall_score == 0.0
