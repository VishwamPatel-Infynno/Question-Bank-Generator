from fastapi import APIRouter

from app.api.v1.ai import router as ai_router
from app.api.v1.batches import router as batches_router
from app.api.v1.config import router as config_router
from app.api.v1.generation import router as generation_router
from app.api.v1.health import router as health_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.passages import router as passages_router
from app.api.v1.questions import router as questions_router
from app.api.v1.taxonomy import router as taxonomy_router

v1_router = APIRouter()
v1_router.include_router(ai_router)
v1_router.include_router(generation_router)
v1_router.include_router(questions_router)
v1_router.include_router(passages_router)
v1_router.include_router(batches_router)
v1_router.include_router(config_router)
v1_router.include_router(health_router)
v1_router.include_router(taxonomy_router)
v1_router.include_router(metrics_router)

__all__ = ["v1_router"]
