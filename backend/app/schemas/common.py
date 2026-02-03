"""Common response / request schemas used across all endpoints."""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard envelope: ``{ request_id, code, message, data }``."""

    request_id: str = ""
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class ApiError(BaseModel):
    """Error envelope: ``{ request_id, code, message, details }``."""

    request_id: str = ""
    code: int = 1
    message: str = "error"
    details: Optional[Any] = None


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
