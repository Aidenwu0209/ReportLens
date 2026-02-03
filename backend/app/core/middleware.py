"""Request-level middleware: request_id injection, CORS, audit logging."""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects ``X-Request-Id`` into every request/response for traceability."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        response.headers["X-Request-Id"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed:.4f}s"
        return response


def setup_middleware(app: FastAPI) -> None:
    """Register all middleware on the FastAPI app."""
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
