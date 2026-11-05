from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_api_access
from app.api.v1 import v1_router

api_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_access)])
api_router.include_router(v1_router)

__all__ = ["api_router"]
