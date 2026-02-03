"""API v1 router – assembles all sub-routers under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, auth, chat, documents, exports, jobs, results

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(results.router)
api_router.include_router(exports.router)
api_router.include_router(chat.router)
api_router.include_router(admin.router)
