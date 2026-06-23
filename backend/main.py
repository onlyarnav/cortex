from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging, logger
from app.core.config import settings
from app.api.routes import auth, documents, search, chat

setup_logging()

app = FastAPI(
    title="Cortex",
    description="Semantic second-brain RAG platform",
    version="1.0.0",
)

ALLOWED_ORIGINS = (
    ["*"] if settings.ENVIRONMENT == "development"
    else ["https://your-frontend-domain.vercel.app"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def root():
    return {"message": "Cortex API Running"}


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}