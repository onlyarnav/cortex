from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.routes import auth, documents, search, chat
from app.core.logging import logger
from app.core.logging import setup_logging

setup_logging()
app = FastAPI(title="Cortex", version="1.0.0")

app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(search.router)

@app.get("/")
def root():
    return {"message": "Cortex API Running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})