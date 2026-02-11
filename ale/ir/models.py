"""IR data models — cross-language normalized code representation.

These models are the canonical intermediate form that the extractor builds
from language-specific parse trees and that the generator reads to produce
Agentic Library instructions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Visibility(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    INTERNAL = "internal"


class SymbolKind(Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    TYPE = "type"
    INTERFACE = "interface"


class DependencyKind(Enum):
    IMPORT = "import"  # Static import/require
    CALL = "call"  # Function/method call
    INHERIT = "inherit"  # Class inheritance
    IMPLEMENT = "implement"  # Interface implementation
    TYPE_REF = "type_ref"  # Type reference
    INSTANTIATE = "instantiate"  # Object creation


class SideEffectKind(Enum):
    NONE = "none"
    FILE_IO = "file_io"
    NETWORK = "network"
    DATABASE = "database"
    STDOUT = "stdout"
    MUTATION = "mutation"  # Mutates external state
    ENVIRONMENT = "environment"  # Reads/writes env vars


# --- Core IR Nodes ---


@dataclass
class IRParameter:
    """A parameter to a function/method."""

    name: str
    type_hint: str = ""
    default_value: str = ""
    required: bool = True


@dataclass
class IRSymbol:
    """A normalized code symbol (function, class, variable, etc.)."""

    name: str
    kind: SymbolKind
    source_file: str
    line_start: int = 0
    line_end: int = 0
    visibility: Visibility = Visibility.PUBLIC

    # For functions/methods
    parameters: list[IRParameter] = field(default_factory=list)
    return_type: str = ""
    is_async: bool = False

    # Behavioral contract
    side_effects: list[SideEffectKind] = field(default_factory=list)
    docstring: str = ""

    # For classes
    base_classes: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    members: list[IRSymbol] = field(default_factory=list)

    @property
    def qualified_name(self) -> str:
        return f"{self.source_file}:{self.name}"

    @property
    def line_count(self) -> int:
        if self.line_end and self.line_start:
            return self.line_end - self.line_start + 1
        return 0


@dataclass
class IRDependency:
    """A dependency edge between symbols."""

    source: str  # Qualified name of the dependent
    target: str  # Qualified name of the dependency
    kind: DependencyKind
    is_external: bool = False  # True if target is outside the analyzed scope


@dataclass
class IRModule:
    """A normalized module/file containing symbols."""

    path: str  # File path relative to repo root
    language: str
    symbols: list[IRSymbol] = field(default_factory=list)
    imports: list[IRDependency] = field(default_factory=list)

    @property
    def public_symbols(self) -> list[IRSymbol]:
        return [s for s in self.symbols if s.visibility == Visibility.PUBLIC]

    @property
    def functions(self) -> list[IRSymbol]:
        return [s for s in self.symbols if s.kind == SymbolKind.FUNCTION]

    @property
    def classes(self) -> list[IRSymbol]:
        return [s for s in self.symbols if s.kind == SymbolKind.CLASS]


@dataclass
class IRGraph:
    """The complete IR graph for an analyzed codebase (or subset).

    This is the primary data structure the extractor builds and the
    generator reads. It contains all normalized modules, symbols, and
    their dependency relationships.
    """

    modules: list[IRModule] = field(default_factory=list)
    dependencies: list[IRDependency] = field(default_factory=list)

    @property
    def all_symbols(self) -> list[IRSymbol]:
        return [s for m in self.modules for s in m.symbols]

    @property
    def external_dependencies(self) -> list[IRDependency]:
        return [d for d in self.dependencies if d.is_external]

    @property
    def internal_dependencies(self) -> list[IRDependency]:
        return [d for d in self.dependencies if not d.is_external]

    def symbols_for_file(self, path: str) -> list[IRSymbol]:
        for m in self.modules:
            if m.path == path:
                return m.symbols
        return []

    def dependency_fan_out(self, symbol_name: str) -> int:
        """How many things does this symbol depend on?"""
        return sum(1 for d in self.dependencies if d.source == symbol_name)

    def dependency_fan_in(self, symbol_name: str) -> int:
        """How many things depend on this symbol?"""
        return sum(1 for d in self.dependencies if d.target == symbol_name)

    def subgraph(self, symbol_names: set[str]) -> IRGraph:
        """Extract a subgraph containing only the specified symbols and their modules."""
        relevant_modules = []
        for module in self.modules:
            relevant_symbols = [s for s in module.symbols if s.qualified_name in symbol_names]
            if relevant_symbols:
                relevant_modules.append(
                    IRModule(
                        path=module.path,
                        language=module.language,
                        symbols=relevant_symbols,
                        imports=[
                            i
                            for i in module.imports
                            if i.source in symbol_names or i.target in symbol_names
                        ],
                    )
                )

        relevant_deps = [
            d
            for d in self.dependencies
            if d.source in symbol_names or d.target in symbol_names
        ]

        return IRGraph(modules=relevant_modules, dependencies=relevant_deps)
