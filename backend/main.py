from fastapi import FastAPI
from app.api.routes import auth

app = FastAPI(title="Cortex", version="1.0.0")

app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Cortex API Running"}

@app.get("/health")
def health():
    return {"status": "ok"}