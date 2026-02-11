"""Python IR parser — builds IR from Python source files using AST.

This is the first language parser for the IR layer. It uses Python's built-in
ast module (no tree-sitter needed for Python) to extract normalized symbols
and dependencies.
"""

from __future__ import annotations

import ast
from pathlib import Path

from ale.ir.models import (
    DependencyKind,
    IRDependency,
    IRModule,
    IRParameter,
    IRSymbol,
    SideEffectKind,
    SymbolKind,
    Visibility,
)


# Known side-effect-producing calls
SIDE_EFFECT_CALLS = {
    "open": SideEffectKind.FILE_IO,
    "print": SideEffectKind.STDOUT,
    "write": SideEffectKind.FILE_IO,
    "read": SideEffectKind.FILE_IO,
    "requests.get": SideEffectKind.NETWORK,
    "requests.post": SideEffectKind.NETWORK,
    "urllib": SideEffectKind.NETWORK,
    "subprocess": SideEffectKind.FILE_IO,
    "os.environ": SideEffectKind.ENVIRONMENT,
    "getenv": SideEffectKind.ENVIRONMENT,
}


def parse_python_file(file_path: str | Path, repo_root: str | Path = "") -> IRModule:
    """Parse a Python file into an IR module.

    Args:
        file_path: Absolute or relative path to the .py file.
        repo_root: Root of the repo, used to compute relative paths.
    """
    file_path = Path(file_path)
    repo_root = Path(repo_root) if repo_root else file_path.parent

    source = file_path.read_text(errors="replace")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return IRModule(path=str(file_path.relative_to(repo_root)), language="python")

    relative_path = str(file_path.relative_to(repo_root))
    module = IRModule(path=relative_path, language="python")

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            module.symbols.append(_parse_function(node, relative_path))
        elif isinstance(node, ast.ClassDef):
            module.symbols.append(_parse_class(node, relative_path))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module.imports.extend(_parse_import(node, relative_path))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    module.symbols.append(
                        IRSymbol(
                            name=target.id,
                            kind=SymbolKind.CONSTANT,
                            source_file=relative_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                        )
                    )

    return module


def _parse_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, source_file: str
) -> IRSymbol:
    """Parse a function definition into an IR symbol."""
    params = []
    for arg in node.args.args:
        if arg.arg == "self":
            continue
        type_hint = ""
        if arg.annotation:
            type_hint = ast.unparse(arg.annotation)
        params.append(IRParameter(name=arg.arg, type_hint=type_hint))

    return_type = ""
    if node.returns:
        return_type = ast.unparse(node.returns)

    visibility = Visibility.PRIVATE if node.name.startswith("_") else Visibility.PUBLIC

    side_effects = _detect_side_effects(node)

    docstring = ast.get_docstring(node) or ""

    return IRSymbol(
        name=node.name,
        kind=SymbolKind.FUNCTION,
        source_file=source_file,
        line_start=node.lineno,
        line_end=node.end_lineno or node.lineno,
        visibility=visibility,
        parameters=params,
        return_type=return_type,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        side_effects=side_effects,
        docstring=docstring,
    )


def _parse_class(node: ast.ClassDef, source_file: str) -> IRSymbol:
    """Parse a class definition into an IR symbol."""
    base_classes = [ast.unparse(base) for base in node.bases]
    visibility = Visibility.PRIVATE if node.name.startswith("_") else Visibility.PUBLIC
    docstring = ast.get_docstring(node) or ""

    members = []
    for item in node.body:
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            member = _parse_function(item, source_file)
            member.kind = SymbolKind.METHOD
            members.append(member)

    return IRSymbol(
        name=node.name,
        kind=SymbolKind.CLASS,
        source_file=source_file,
        line_start=node.lineno,
        line_end=node.end_lineno or node.lineno,
        visibility=visibility,
        base_classes=base_classes,
        members=members,
        docstring=docstring,
    )


def _parse_import(
    node: ast.Import | ast.ImportFrom, source_file: str
) -> list[IRDependency]:
    """Parse import statements into IR dependencies."""
    deps = []
    source_name = f"{source_file}:<module>"

    if isinstance(node, ast.Import):
        for alias in node.names:
            deps.append(
                IRDependency(
                    source=source_name,
                    target=alias.name,
                    kind=DependencyKind.IMPORT,
                    is_external=not alias.name.startswith("."),
                )
            )
    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        is_relative = (node.level or 0) > 0
        for alias in node.names:
            target = f"{module}.{alias.name}" if module else alias.name
            deps.append(
                IRDependency(
                    source=source_name,
                    target=target,
                    kind=DependencyKind.IMPORT,
                    is_external=not is_relative,
                )
            )

    return deps


def _detect_side_effects(node: ast.AST) -> list[SideEffectKind]:
    """Detect potential side effects in a function body."""
    effects = set()

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            call_name = _get_call_name(child)
            for pattern, effect in SIDE_EFFECT_CALLS.items():
                if pattern in call_name:
                    effects.add(effect)

    return list(effects)


def _get_call_name(node: ast.Call) -> str:
    """Extract the name of a function call."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""
