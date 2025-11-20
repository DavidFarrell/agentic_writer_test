"""Routes for Agentic Writer application."""

from .projects import router as projects_router
from .resources import router as resources_router
from .artefacts import router as artefacts_router
from .agents import router as agents_router

__all__ = [
    "projects_router",
    "resources_router",
    "artefacts_router",
    "agents_router",
]
