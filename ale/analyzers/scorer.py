"""Scorer -- computes real 7-dimension scores from IR data.

Replaces hardcoded placeholder scores with actual metrics derived from
parsed symbols, dependencies, side effects, and call graph context.
"""

from __future__ import annotations

from ale.ir.models import IRModule, SideEffectKind, SymbolKind, Visibility
from ale.models.candidate import ExtractionCandidate, ScoreDimension, ScoringBreakdown


def score_candidate(candidate: ExtractionCandidate) -> None:
    """Compute real 7-dimension scores for a candidate and set them in place.

    Uses the IR-enriched data already on the candidate (symbols, deps,
    callers/callees) to derive meaningful scores.
    """
    dims = ScoringBreakdown.default_dimensions()
    dim_map = {d.name: d for d in dims}

    _score_isolation(candidate, dim_map["isolation"])
    _score_coupling(candidate, dim_map["coupling_risk"])
    _score_complexity(candidate, dim_map["complexity_risk"])
    _score_reuse(candidate, dim_map["reuse_potential"])
    _score_testability(candidate, dim_map["testability"])
    _score_portability(candidate, dim_map["portability"])
    _score_security(candidate, dim_map["security_sensitivity"])

    candidate.scoring = ScoringBreakdown(dimensions=dims)

    # Also set legacy scores for backward compat
    candidate.isolation_score = dim_map["isolation"].score
    candidate.reuse_score = dim_map["reuse_potential"].score
    candidate.complexity_score = dim_map["complexity_risk"].score
    candidate.clarity_score = dim_map["portability"].score


def _score_isolation(candidate: ExtractionCandidate, dim: ScoreDimension) -> None:
    """Isolation = how self-contained is this candidate?

    High score: few internal deps, few callers (loosely coupled).
    Low score: many internal deps and callers (deeply embedded).
    """
    internal_dep_count = len(candidate.dependencies_internal)
    caller_count = len(candidate.callers)
    callee_count = len(candidate.callees)

    # Start at 1.0 and deduct for coupling signals
    score = 1.0

    # Penalize for internal dependencies (each dep reduces isolation)
    if internal_dep_count > 0:
        score -= min(0.4, internal_dep_count * 0.08)
        dim.reasons.append(f"{internal_dep_count} internal dependencies")

    # Penalize for many callers (deeply embedded in codebase)
    if caller_count > 0:
        score -= min(0.3, caller_count * 0.06)
        dim.reasons.append(f"{caller_count} modules depend on this")

    if callee_count > 0:
        score -= min(0.2, callee_count * 0.04)

    if internal_dep_count == 0 and callee_count == 0:
        dim.reasons.append("No internal dependencies -- highly isolated")

    if caller_count == 0:
        dim.reasons.append("No callers -- can be extracted without breaking dependents")

    if internal_dep_count > 5:
        dim.flags.append("High internal coupling -- may need refactoring before extraction")

    dim.score = max(0.05, min(1.0, score))


def _score_coupling(candidate: ExtractionCandidate, dim: ScoreDimension) -> None:
    """Coupling risk = how entangled is this with the rest of the codebase?

    This is the *risk* dimension -- high score means LOW coupling (good).
    """
    callers = len(candidate.callers)
    callees = len(candidate.callees)
    internal_deps = len(candidate.dependencies_internal)
    total_coupling = callers + callees + internal_deps

    if total_coupling == 0:
        dim.score = 0.95
        dim.reasons.append("No coupling detected -- minimal entanglement risk")
        return

    # Start high, deduct based on coupling depth
    score = 1.0 - min(0.8, total_coupling * 0.05)

    if callers > 3:
        dim.flags.append(f"Many dependents ({callers}) -- extraction may break consumers")

    if internal_deps > 3:
        dim.reasons.append(f"{internal_deps} internal deps increase coupling risk")
    else:
        dim.reasons.append("Manageable internal dependency count")

    dim.score = max(0.05, min(1.0, score))


def _score_complexity(candidate: ExtractionCandidate, dim: ScoreDimension) -> None:
    """Complexity risk = how complex is this to extract?

    High score means LOW complexity risk (simpler, easier to extract).
    """
    symbols = candidate.symbols
    file_count = len(candidate.source_files)

    total_symbols = len(symbols)
    class_count = sum(1 for s in symbols if s.get("kind") == "class")
    func_count = sum(1 for s in symbols if s.get("kind") in ("function", "method"))

    # Baseline
    score = 0.8

    # Penalize for many symbols (more to extract)
    if total_symbols > 20:
        score -= 0.2
        dim.reasons.append(f"{total_symbols} symbols -- significant extraction scope")
    elif total_symbols > 10:
        score -= 0.1
        dim.reasons.append(f"{total_symbols} symbols -- moderate scope")
    else:
        dim.reasons.append(f"{total_symbols} symbols -- manageable scope")

    # Penalize for many files
    if file_count > 5:
        score -= 0.15
        dim.flags.append(f"Spans {file_count} files -- multi-file extraction")
    elif file_count > 2:
        score -= 0.05

    # Classes add complexity
    if class_count > 3:
        score -= 0.1
        dim.reasons.append(f"{class_count} classes with potential inheritance")

    # Many functions is manageable but adds scope
    if func_count > 15:
        score -= 0.1

    dim.score = max(0.05, min(1.0, score))


def _score_reuse(candidate: ExtractionCandidate, dim: ScoreDimension) -> None:
    """Reuse potential = how valuable is this as a reusable library?

    High score: clear API, documented, general-purpose.
    Low score: sparse API, no docs, highly specific.
    """
    symbols = candidate.symbols
    entry_points = candidate.entry_points

    public_funcs = [s for s in symbols if s.get("kind") in ("function", "class") and s.get("docstring")]
    undocumented = [s for s in symbols if s.get("kind") in ("function", "class") and not s.get("docstring")]
    total_public = len(entry_points)

    score = 0.5  # Neutral baseline

    # Reward for having a clear public API
    if total_public > 0:
        score += min(0.2, total_public * 0.04)
        dim.reasons.append(f"{total_public} public entry points")
    else:
        score -= 0.15
        dim.reasons.append("No public entry points detected")

    # Reward for documentation coverage
    doc_count = len(public_funcs)
    if doc_count > 0:
        doc_ratio = doc_count / max(1, doc_count + len(undocumented))
        if doc_ratio > 0.5:
            score += 0.15
            dim.reasons.append(f"{doc_ratio:.0%} documentation coverage")
        else:
            score += 0.05
    else:
        dim.reasons.append("No docstrings found -- low discoverability")

    # Reward for having external deps (uses established patterns)
    ext_deps = len(candidate.dependencies_external)
    if 0 < ext_deps <= 3:
        score += 0.05
        dim.reasons.append("Uses well-known external packages")
    elif ext_deps > 5:
        score -= 0.05
        dim.flags.append(f"Many external deps ({ext_deps}) -- heavier dependency footprint")

    # Reward for being tagged as utility/common/shared
    utility_tags = {"utility", "helpers", "common", "shared", "tools", "core", "lib"}
    if utility_tags & set(candidate.tags):
        score += 0.1
        dim.reasons.append("Located in utility/common directory -- likely reusable")

    dim.score = max(0.05, min(1.0, score))


def _score_testability(candidate: ExtractionCandidate, dim: ScoreDimension) -> None:
    """Testability = how easy is it to test this in isolation?

    High score: pure functions, no side effects.
    Low score: many side effects, hard to mock.
    """
    symbols = candidate.symbols

    # Count functions with side effects via their signatures
    side_effect_funcs = 0
    pure_funcs = 0
    for sym in symbols:
        if sym.get("kind") in ("function", "method"):
            sig = sym.get("signature", "")
            # Heuristic: look for common side-effect patterns in names
            name = sym.get("name", "")
            if any(kw in name.lower() for kw in ("write", "send", "delete", "remove", "upload", "post")):
                side_effect_funcs += 1
            else:
                pure_funcs += 1

    total = side_effect_funcs + pure_funcs
    if total == 0:
        dim.score = 0.5
        dim.reasons.append("No functions to evaluate")
        return

    pure_ratio = pure_funcs / total
    score = 0.3 + (pure_ratio * 0.6)

    if pure_ratio > 0.8:
        dim.reasons.append(f"{pure_ratio:.0%} of functions appear side-effect-free")
    elif pure_ratio > 0.5:
        dim.reasons.append(f"{pure_ratio:.0%} pure function ratio")
    else:
        dim.flags.append("Many functions with potential side effects -- harder to test")
        dim.reasons.append(f"Only {pure_ratio:.0%} pure function ratio")

    # Penalize for no entry points (harder to test)
    if not candidate.entry_points:
        score -= 0.1
        dim.reasons.append("No clear entry points for testing")

    dim.score = max(0.05, min(1.0, score))


def _score_portability(candidate: ExtractionCandidate, dim: ScoreDimension) -> None:
    """Portability = how easily can this be reproduced in another project/language?

    High score: clear boundaries, few platform deps.
    Low score: deep framework coupling, platform-specific.
    """
    ext_deps = candidate.dependencies_external
    symbols = candidate.symbols

    score = 0.7  # Neutral-good baseline

    # Heavy framework deps reduce portability
    framework_deps = {"django", "flask", "fastapi", "sqlalchemy", "celery", "tornado"}
    found_frameworks = [d for d in ext_deps if d.lower() in framework_deps]
    if found_frameworks:
        score -= len(found_frameworks) * 0.1
        dim.flags.append(f"Framework dependencies: {', '.join(found_frameworks)}")
        dim.reasons.append("Framework coupling reduces portability")
    else:
        dim.reasons.append("No heavy framework dependencies")

    # Minimal external deps = more portable
    if len(ext_deps) == 0:
        score += 0.15
        dim.reasons.append("Zero external dependencies -- highly portable")
    elif len(ext_deps) <= 2:
        score += 0.05
        dim.reasons.append("Minimal external dependencies")
    elif len(ext_deps) > 6:
        score -= 0.1

    # Well-documented API = clearer abstraction boundary
    documented = sum(1 for s in symbols if s.get("docstring"))
    if documented > 0:
        score += 0.05
        dim.reasons.append("Documented API aids cross-project adoption")

    dim.score = max(0.05, min(1.0, score))


def _score_security(candidate: ExtractionCandidate, dim: ScoreDimension) -> None:
    """Security sensitivity = does this touch sensitive operations?

    High score means LOW security sensitivity (safer to extract).
    """
    symbols = candidate.symbols
    ext_deps = candidate.dependencies_external

    score = 0.9  # Default: low sensitivity

    # Check for network/IO patterns in function names
    sensitive_patterns = {"auth", "crypt", "secret", "password", "token", "credential", "key", "cert"}
    io_patterns = {"file", "write", "upload", "download", "request", "http", "socket"}

    sensitive_names = []
    io_names = []
    for sym in symbols:
        name = sym.get("name", "").lower()
        if any(p in name for p in sensitive_patterns):
            sensitive_names.append(sym.get("name", ""))
        if any(p in name for p in io_patterns):
            io_names.append(sym.get("name", ""))

    if sensitive_names:
        score -= min(0.4, len(sensitive_names) * 0.1)
        dim.flags.append(f"Security-sensitive symbols: {', '.join(sensitive_names[:3])}")
        dim.reasons.append("Contains security-sensitive operations")

    if io_names:
        score -= min(0.2, len(io_names) * 0.05)
        dim.reasons.append(f"{len(io_names)} I/O operations detected")

    # Check for security-related external deps
    security_deps = {"cryptography", "pyjwt", "passlib", "bcrypt", "paramiko"}
    found_sec = [d for d in ext_deps if d.lower() in security_deps]
    if found_sec:
        score -= 0.15
        dim.flags.append(f"Security-related dependencies: {', '.join(found_sec)}")

    if not sensitive_names and not io_names and not found_sec:
        dim.reasons.append("No security-sensitive operations detected")

    dim.score = max(0.05, min(1.0, score))
