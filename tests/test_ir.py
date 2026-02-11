"""Tests for the canonical IR (Intermediate Representation)."""

import tempfile
from pathlib import Path

from ale.ir.models import (
    DependencyKind,
    IRDependency,
    IRGraph,
    IRModule,
    IRParameter,
    IRSymbol,
    SideEffectKind,
    SymbolKind,
    Visibility,
)
from ale.ir.python_parser import parse_python_file


# --- IR Model Tests ---


def test_ir_symbol_basic():
    sym = IRSymbol(
        name="process",
        kind=SymbolKind.FUNCTION,
        source_file="utils/process.py",
        line_start=10,
        line_end=25,
        parameters=[
            IRParameter(name="data", type_hint="dict"),
            IRParameter(name="verbose", type_hint="bool", default_value="False", required=False),
        ],
        return_type="list[str]",
    )
    assert sym.qualified_name == "utils/process.py:process"
    assert sym.line_count == 16
    assert len(sym.parameters) == 2


def test_ir_module():
    module = IRModule(
        path="utils/helpers.py",
        language="python",
        symbols=[
            IRSymbol(name="public_fn", kind=SymbolKind.FUNCTION, source_file="utils/helpers.py"),
            IRSymbol(
                name="_private_fn",
                kind=SymbolKind.FUNCTION,
                source_file="utils/helpers.py",
                visibility=Visibility.PRIVATE,
            ),
            IRSymbol(name="MyClass", kind=SymbolKind.CLASS, source_file="utils/helpers.py"),
        ],
    )
    assert len(module.public_symbols) == 2
    assert len(module.functions) == 2
    assert len(module.classes) == 1


def test_ir_graph_fan_in_out():
    graph = IRGraph(
        dependencies=[
            IRDependency(source="a:fn1", target="b:fn2", kind=DependencyKind.CALL),
            IRDependency(source="a:fn1", target="c:fn3", kind=DependencyKind.CALL),
            IRDependency(source="d:fn4", target="b:fn2", kind=DependencyKind.CALL),
        ]
    )
    assert graph.dependency_fan_out("a:fn1") == 2
    assert graph.dependency_fan_in("b:fn2") == 2
    assert graph.dependency_fan_out("d:fn4") == 1


def test_ir_graph_subgraph():
    graph = IRGraph(
        modules=[
            IRModule(
                path="a.py",
                language="python",
                symbols=[
                    IRSymbol(name="fn1", kind=SymbolKind.FUNCTION, source_file="a.py"),
                    IRSymbol(name="fn2", kind=SymbolKind.FUNCTION, source_file="a.py"),
                ],
            ),
        ],
        dependencies=[
            IRDependency(source="a.py:fn1", target="a.py:fn2", kind=DependencyKind.CALL),
            IRDependency(source="a.py:fn1", target="ext:lib", kind=DependencyKind.IMPORT),
        ],
    )
    sub = graph.subgraph({"a.py:fn1"})
    assert len(sub.dependencies) == 2  # Both deps involve fn1
    assert len(sub.modules) == 1


def test_ir_graph_external_deps():
    graph = IRGraph(
        dependencies=[
            IRDependency(source="a:fn", target="b:fn", kind=DependencyKind.CALL, is_external=False),
            IRDependency(
                source="a:fn", target="requests:get", kind=DependencyKind.CALL, is_external=True
            ),
        ]
    )
    assert len(graph.external_dependencies) == 1
    assert len(graph.internal_dependencies) == 1


# --- Python Parser Tests ---


def test_parse_simple_function():
    code = '''
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        module = parse_python_file(f.name, repo_root=Path(f.name).parent)

    assert len(module.functions) == 1
    fn = module.functions[0]
    assert fn.name == "greet"
    assert fn.return_type == "str"
    assert len(fn.parameters) == 1
    assert fn.parameters[0].name == "name"
    assert fn.parameters[0].type_hint == "str"
    assert fn.docstring == "Say hello."
    assert fn.visibility == Visibility.PUBLIC


def test_parse_private_function():
    code = "def _internal(): pass\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        module = parse_python_file(f.name, repo_root=Path(f.name).parent)

    assert module.functions[0].visibility == Visibility.PRIVATE


def test_parse_class():
    code = '''
class Parser:
    """A parser class."""
    def parse(self, data: str) -> dict:
        pass
    def _validate(self):
        pass
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        module = parse_python_file(f.name, repo_root=Path(f.name).parent)

    assert len(module.classes) == 1
    cls = module.classes[0]
    assert cls.name == "Parser"
    assert cls.docstring == "A parser class."
    assert len(cls.members) == 2
    assert cls.members[0].name == "parse"
    assert cls.members[0].kind == SymbolKind.METHOD


def test_parse_imports():
    code = """
import os
import json
from pathlib import Path
from .utils import helper
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        module = parse_python_file(f.name, repo_root=Path(f.name).parent)

    assert len(module.imports) == 4
    # os and json are external
    external = [i for i in module.imports if i.is_external]
    internal = [i for i in module.imports if not i.is_external]
    assert len(external) == 3  # os, json, pathlib.Path
    assert len(internal) == 1  # .utils.helper


def test_parse_side_effects():
    code = """
def do_io():
    with open("file.txt") as f:
        data = f.read()
    print(data)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        module = parse_python_file(f.name, repo_root=Path(f.name).parent)

    fn = module.functions[0]
    assert SideEffectKind.FILE_IO in fn.side_effects
    assert SideEffectKind.STDOUT in fn.side_effects


def test_parse_async_function():
    code = """
async def fetch(url: str) -> bytes:
    pass
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        module = parse_python_file(f.name, repo_root=Path(f.name).parent)

    assert module.functions[0].is_async is True


def test_parse_constants():
    code = """
MAX_RETRIES = 5
DEFAULT_TIMEOUT = 30
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        module = parse_python_file(f.name, repo_root=Path(f.name).parent)

    constants = [s for s in module.symbols if s.kind == SymbolKind.CONSTANT]
    assert len(constants) == 2
    names = {c.name for c in constants}
    assert "MAX_RETRIES" in names
    assert "DEFAULT_TIMEOUT" in names


def test_parse_syntax_error():
    code = "def broken(\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        module = parse_python_file(f.name, repo_root=Path(f.name).parent)

    # Should return an empty module, not crash
    assert module.language == "python"
    assert module.symbols == []
