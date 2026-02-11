"""Tests for ALE data models."""

from ale.models.agentic_library import (
    AbstractionBoundary,
    AgenticLibrary,
    CapabilityDep,
    CompatibilityEntry,
    CompatibilityStatus,
    Complexity,
    Guardrail,
    GuardrailEnforcement,
    InstructionStep,
    MigrationGuide,
    ProvenanceRecord,
    ValidationCriterion,
    ValidationHook,
)
from ale.models.candidate import ExtractionCandidate, ScoreDimension, ScoringBreakdown
from ale.spec import SPEC_VERSION


def test_agentic_library_creation():
    lib = AgenticLibrary(
        name="test-lib",
        description="A test library",
        complexity=Complexity.SIMPLE,
    )
    assert lib.name == "test-lib"
    assert lib.version == "1.0.0"
    assert lib.spec_version == SPEC_VERSION
    assert lib.complexity == Complexity.SIMPLE
    assert lib.language_agnostic is True
    assert lib.instructions == []
    assert lib.guardrails == []
    assert lib.abstraction_boundary is None
    assert lib.compatibility == []
    assert lib.migrations == []


def test_agentic_library_with_full_spec():
    lib = AgenticLibrary(
        name="full-lib",
        description="Fully specified library",
        instructions=[
            InstructionStep(
                order=1,
                title="Step 1",
                description="Do the thing",
                preconditions=["Project exists"],
                touched_surfaces=["src/main.py"],
                capabilities_used=["logging"],
            ),
            InstructionStep(order=2, title="Step 2", description="Do the other thing"),
        ],
        guardrails=[
            Guardrail(
                rule="Must be safe",
                severity="must",
                enforcement=GuardrailEnforcement.MACHINE,
                check_command="pytest tests/",
            ),
        ],
        validation=[
            ValidationCriterion(
                description="It works",
                test_approach="Run it",
                expected_behavior="No errors",
                hook=ValidationHook(type="command", command="pytest"),
            ),
        ],
        capability_deps=[
            CapabilityDep(capability="logging", required=True),
        ],
        abstraction_boundary=AbstractionBoundary(
            scope="Application logging layer",
            assumptions=["Project has a main entry point"],
            integration_points=["app initialization"],
        ),
        compatibility=[
            CompatibilityEntry(
                target_id="python",
                target_type="language",
                status=CompatibilityStatus.SUPPORTED,
            ),
        ],
        migrations=[
            MigrationGuide(
                from_version="0.9.0",
                to_version="1.0.0",
                summary="Initial stable release",
                breaking=True,
                steps=["Update import paths"],
            ),
        ],
    )
    assert len(lib.instructions) == 2
    assert lib.instructions[0].capabilities_used == ["logging"]
    assert len(lib.guardrails) == 1
    assert lib.guardrails[0].enforcement == GuardrailEnforcement.MACHINE
    assert len(lib.validation) == 1
    assert lib.validation[0].hook.type == "command"
    assert len(lib.capability_deps) == 1
    assert lib.abstraction_boundary.scope == "Application logging layer"
    assert len(lib.compatibility) == 1
    assert lib.compatibility[0].status == CompatibilityStatus.SUPPORTED
    assert len(lib.migrations) == 1
    assert lib.migrations[0].breaking is True


def test_provenance_record():
    record = ProvenanceRecord(
        library_name="rate-limiter",
        library_version="1.0.0",
        applied_by="ale-runner/0.2.0",
        validation_passed=True,
    )
    assert record.library_name == "rate-limiter"
    assert record.applied_at == ""  # Not set until recorded


# --- Candidate / Scoring ---


def test_candidate_legacy_scoring():
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


def test_candidate_7dim_scoring():
    dims = [
        ScoreDimension(name="isolation", score=0.9, weight=0.20, reasons=["Well-isolated module"]),
        ScoreDimension(name="coupling_risk", score=0.8, weight=0.15),
        ScoreDimension(name="complexity_risk", score=0.7, weight=0.10),
        ScoreDimension(name="reuse_potential", score=0.85, weight=0.20, reasons=["Common pattern"]),
        ScoreDimension(name="testability", score=0.6, weight=0.15),
        ScoreDimension(name="portability", score=0.75, weight=0.15),
        ScoreDimension(name="security_sensitivity", score=0.9, weight=0.05),
    ]
    candidate = ExtractionCandidate(
        name="scored-util",
        description="A scored utility",
        source_files=["utils/scored.py"],
        entry_points=["score"],
        scoring=ScoringBreakdown(dimensions=dims),
    )
    # 7-dim score should take precedence over legacy
    assert candidate.overall_score > 0.0
    assert candidate.overall_score != candidate.isolation_score  # Not using legacy


def test_scoring_breakdown_defaults():
    dims = ScoringBreakdown.default_dimensions()
    assert len(dims) == 7
    total_weight = sum(d.weight for d in dims)
    assert abs(total_weight - 1.0) < 0.001


def test_scoring_breakdown_top_reasons():
    breakdown = ScoringBreakdown(
        dimensions=[
            ScoreDimension(
                name="isolation",
                score=0.9,
                weight=0.3,
                reasons=["Self-contained", "No imports"],
            ),
            ScoreDimension(
                name="reuse",
                score=0.5,
                weight=0.2,
                reasons=["Moderate reuse potential"],
            ),
        ]
    )
    reasons = breakdown.top_reasons
    assert len(reasons) == 3
    assert "[isolation]" in reasons[0]


def test_scoring_flags():
    breakdown = ScoringBreakdown(
        dimensions=[
            ScoreDimension(
                name="security",
                score=0.2,
                weight=0.05,
                flags=["Handles credentials", "Uses eval()"],
            ),
        ]
    )
    assert len(breakdown.all_flags) == 2
    assert "eval()" in breakdown.all_flags[1]


def test_candidate_detailed_report():
    candidate = ExtractionCandidate(
        name="parser",
        description="JSON parser utility",
        source_files=["utils/parser.py"],
        entry_points=["parse"],
        scoring=ScoringBreakdown(
            dimensions=[
                ScoreDimension(name="isolation", score=0.9, weight=0.2, reasons=["Clean boundary"]),
            ]
        ),
    )
    report = candidate.detailed_report()
    assert "parser" in report
    assert "isolation" in report
    assert "Clean boundary" in report


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
