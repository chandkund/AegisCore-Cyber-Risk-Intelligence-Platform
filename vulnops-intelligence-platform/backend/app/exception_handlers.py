from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorResponse

logger = logging.getLogger("vulnops.api")


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        rid = _rid(request)
        body = ErrorResponse(
            detail=str(exc.detail) if isinstance(exc.detail, str) else "HTTP error",
            code=f"http_{exc.status_code}",
            request_id=rid,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(exclude_none=True),
            headers=getattr(exc, "headers", None) or {},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        rid = _rid(request)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                detail="Validation error",
                code="validation_error",
                request_id=rid,
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        rid = _rid(request) or str(uuid.uuid4())
        logger.exception("unhandled_error request_id=%s", rid, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail="Internal server error",
                code="internal_error",
                request_id=rid,
            ).model_dump(exclude_none=True),
        )
