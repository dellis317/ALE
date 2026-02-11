"""FastAPI application for the ALE (Agentic Library Extractor) web portal.

Provides REST API endpoints wrapping the ALE Python package for:
- Registry management (publish, search, list)
- Conformance validation (3-gate pipeline)
- Repository analysis and library generation
- Drift detection and provenance tracking
- Intermediate Representation (IR) parsing
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the ALE package is importable by adding the project root to sys.path.
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web.backend.app.routers import ai_query, analyze, auth, conformance, distribution, drift, generator, ir, llm, orgs, policies, registry, security

app = FastAPI(
    title="ALE API",
    description=(
        "REST API for the Agentic Library Extractor. "
        "Provides endpoints for registry management, conformance validation, "
        "repository analysis, drift detection, and IR parsing."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS middleware (allow all origins for development)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------
app.include_router(registry.router)
app.include_router(distribution.router)
app.include_router(conformance.router)
app.include_router(analyze.router)
app.include_router(drift.router)
app.include_router(ir.router)
app.include_router(generator.router)
app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(policies.router)
app.include_router(llm.router)
app.include_router(security.router)
app.include_router(ai_query.router)


# ---------------------------------------------------------------------------
# Root and health-check endpoints
# ---------------------------------------------------------------------------


@app.get("/", tags=["meta"])
async def root():
    """Return basic API information."""
    return {
        "name": "ALE API",
        "version": "0.1.0",
        "description": "Agentic Library Extractor REST API",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health", tags=["meta"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
