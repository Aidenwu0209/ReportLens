"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.middleware import setup_middleware

app = FastAPI(
    title="年报智能解析平台 API",
    description="Annual Report Intelligent Parsing Platform – B2B FinTech",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
setup_middleware(app)

# Routes
app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
