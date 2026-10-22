"""FastAPI application entry point.

Run from the repository root:
    uvicorn backend.app.main:app --reload
"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from contextlib import asynccontextmanager

from backend.app.api.v1 import health
from backend.app.api.v1.router import router as api_v1_router
from backend.app.core.config import get_settings
from backend.app.core.errors import DomainError, error_payload
from backend.app.core.logging import configure_logging, request_id_ctx

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("food_optimizer.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_directories()
    logger.info(
        "backend_started",
        extra={"stage": "startup"},
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend for the Autonomous Context-Aware Food Waste Optimization System. "
        "All records and outcomes are synthetic; no live VIT kitchen action is executed."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_ctx.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    finally:
        request_id_ctx.reset(token)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    logger.warning(
        "domain_error",
        extra={"path": request.url.path, "status_code": exc.status_code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            exc.code,
            exc.message,
            exc.details,
            request_id=request_id_ctx.get(),
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "type": error.get("type"),
            "loc": [str(item) for item in error.get("loc", [])],
            "msg": error.get("msg"),
            "input": str(error.get("input"))[:500],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_payload(
            "VALIDATION_ERROR",
            "Request validation failed",
            details,
            request_id=request_id_ctx.get(),
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            codes.get(exc.status_code, "HTTP_ERROR"),
            str(exc.detail),
            None,
            request_id=request_id_ctx.get(),
        ),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content=error_payload(
            "INTERNAL_ERROR",
            "An unexpected server error occurred.",
            None,
            request_id=request_id_ctx.get(),
        ),
    )


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_v1_prefix,
        "synthetic_only": True,
    }


app.include_router(health.router)
app.include_router(health.router, prefix=settings.api_v1_prefix, include_in_schema=False)
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
