"""IR router -- parse Python files into the Intermediate Representation."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ale.ir.python_parser import parse_python_file

from web.backend.app.models.api import (
    IRDependencyResponse,
    IRModuleResponse,
    IRParameterResponse,
    IRParseRequest,
    IRSymbolResponse,
)

router = APIRouter(tags=["ir"])


def _symbol_to_response(symbol) -> IRSymbolResponse:
    """Convert an IRSymbol dataclass to a Pydantic response."""
    return IRSymbolResponse(
        name=symbol.name,
        kind=symbol.kind.value,
        source_file=symbol.source_file,
        line_start=symbol.line_start,
        line_end=symbol.line_end,
        line_count=symbol.line_count,
        visibility=symbol.visibility.value,
        parameters=[
            IRParameterResponse(
                name=p.name,
                type_hint=p.type_hint,
                default_value=p.default_value,
                required=p.required,
            )
            for p in symbol.parameters
        ],
        return_type=symbol.return_type,
        is_async=symbol.is_async,
        side_effects=[e.value for e in symbol.side_effects],
        docstring=symbol.docstring,
        base_classes=symbol.base_classes,
        interfaces=symbol.interfaces,
        members=[_symbol_to_response(m) for m in symbol.members],
        qualified_name=symbol.qualified_name,
    )


def _dependency_to_response(dep) -> IRDependencyResponse:
    """Convert an IRDependency dataclass to a Pydantic response."""
    return IRDependencyResponse(
        source=dep.source,
        target=dep.target,
        kind=dep.kind.value,
        is_external=dep.is_external,
    )


@router.post(
    "/api/ir/parse",
    response_model=IRModuleResponse,
    summary="Parse a Python file into IR",
)
async def parse_file(request: IRParseRequest):
    """Parse a Python source file and return its Intermediate Representation.

    The IR includes all symbols (functions, classes, constants), their
    parameters, return types, visibility, side effects, and import
    dependencies.
    """
    file_path = Path(request.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {request.file_path}",
        )

    if not file_path.suffix == ".py":
        raise HTTPException(
            status_code=400,
            detail="Only Python (.py) files are supported",
        )

    try:
        module = parse_python_file(
            file_path=request.file_path,
            repo_root=request.repo_root or "",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return IRModuleResponse(
        path=module.path,
        language=module.language,
        symbols=[_symbol_to_response(s) for s in module.symbols],
        imports=[_dependency_to_response(d) for d in module.imports],
    )
