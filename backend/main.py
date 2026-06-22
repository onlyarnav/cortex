import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import auth, chat, documents, search
from app.core.logging import logger, setup_logging


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

setup_logging()


# ---------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Cortex API")

    try:
        # Future startup tasks:
        # - Database connection checks
        # - Redis connection checks
        # - Qdrant connection checks
        # - Load ML models
        # - Warm caches
        yield

    finally:
        logger.info("Shutting down Cortex API")


# ---------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------

app = FastAPI(
    title="Cortex API",
    description="Production-grade RAG & Agent Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ---------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["Chat"],
)

app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["Documents"],
)

app.include_router(
    search.router,
    prefix="/api/v1/search",
    tags=["Search"],
)


# ---------------------------------------------------------------------
# Root Endpoints
# ---------------------------------------------------------------------

@app.get("/", tags=["System"])
async def root():
    return {
        "name": "Cortex API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health", tags=["System"])
async def health():
    """
    Liveness probe.
    Used by Docker/Kubernetes.
    """
    return {
        "status": "healthy",
    }


@app.get("/ready", tags=["System"])
async def readiness():
    """
    Readiness probe.

    Future:
    - PostgreSQL ping
    - Redis ping
    - Qdrant ping
    """

    return {
        "status": "ready",
        "services": {
            "database": "ok",
            "redis": "ok",
            "qdrant": "ok",
        },
    }


# ---------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    logger.warning(
        f"HTTP {exc.status_code} - {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    logger.warning(
        f"Validation error on {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        f"Unhandled exception on {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
        },
    )


# ---------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    duration = round(
        time.perf_counter() - start,
        4,
    )

    logger.info(
        f"{request.method} "
        f"{request.url.path} "
        f"{response.status_code} "
        f"{duration}s"
    )

    return response