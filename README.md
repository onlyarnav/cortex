# Cortex — Personal Semantic Second-Brain (RAG Platform)

Cortex is a self-hosted, single-user Retrieval-Augmented Generation (RAG) platform. Upload your documents (PDF, Markdown, TXT, DOCX), and Cortex extracts, chunks, and embeds them so you can semantically search and chat with your own knowledge base — with citation-aware answers grounded in your actual content.

This is a personal project, built and used by one person. It is not designed or intended for multi-tenant public use.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [API Reference](#api-reference)
- [How Document Processing Works](#how-document-processing-works)
- [How Search & Chat Work](#how-search--chat-work)
- [Testing](#testing)
- [Security Notes](#security-notes)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Overview

Cortex solves a simple problem: you accumulate notes, PDFs, and documents, but finding the right piece of information later — or asking a question across all of them at once — is hard. Cortex lets you:

1. Upload a document
2. Have it automatically extracted, chunked, and embedded in the background
3. Run semantic search across everything you've uploaded
4. Chat with an LLM that answers using only your own documents as context, citing exactly which chunks it used

Authentication (signup/login via JWT) is included even though this is single-user, primarily to prevent anonymous public access if/when the app is deployed to a public URL.

---

## Architecture

```
                    ┌─────────────┐
   Upload Request   │   FastAPI   │
   ───────────────► │   Backend   │
                    └──────┬──────┘
                           │ saves file, creates Document + Job rows
                           │ dispatches async task
                           ▼
                    ┌─────────────┐        ┌──────────┐
                    │    Redis    │◄──────►│  Celery  │
                    │  (broker)   │        │  Worker  │
                    └─────────────┘        └────┬─────┘
                                                 │
                          ┌──────────────────────┼──────────────────────┐
                          ▼                      ▼                      ▼
                  1. Extract text       2. Chunk text          3. Generate
                  (pypdf/docx/txt)      (500 words,            embeddings
                                         50-word overlap)      (batched)
                                                                       │
                                                                       ▼
                                                              ┌─────────────┐
                                                              │   Qdrant    │
                                                              │ (vectors)   │
                                                              └─────────────┘
                                                                       ▲
                    ┌─────────────┐    embed query, search    │
   Search/Chat      │   FastAPI   │ ───────────────────────────┘
   Request   ──────►│   Backend   │
                    └──────┬──────┘
                           │ retrieved chunks → prompt
                           ▼
                    ┌─────────────┐
                    │  Groq LLM   │
                    │ (llama-3.1) │
                    └─────────────┘
                           │
                           ▼
                  Answer + cited sources
```

**Relational data** (users, documents, chunks, jobs, conversations, messages) lives in PostgreSQL. **Vector data** (embeddings) lives in Qdrant. **Task queueing** runs through Redis + Celery so slow operations (text extraction, embedding generation) never block an HTTP request.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| Relational DB | PostgreSQL (via SQLAlchemy 2.0, Alembic migrations) |
| Vector DB | Qdrant |
| Task queue | Celery + Redis |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (384-dim) |
| LLM | Groq (`llama-3.1-8b-instant`) via LangChain |
| Auth | JWT (`python-jose`) + bcrypt (`passlib`) |
| Rate limiting | `slowapi` |
| File storage | Local disk (Phase 1) → Cloudinary (planned, for cross-container persistence) |
| Testing | `pytest` + `TestClient` |
| Containerization | Docker + Docker Compose |
| Deployment target | Railway (backend, Postgres, Redis) + Qdrant Cloud |

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/         # auth, documents, search, chat
│   │   └── dependencies/   # auth dependency (get_current_user)
│   ├── ai/
│   │   ├── embeddings.py   # sentence-transformers model + batch encoding
│   │   ├── vector_store.py # Qdrant client, upsert/search/delete
│   │   └── llm.py          # Groq/LangChain answer generation
│   ├── core/
│   │   ├── config.py       # Settings (env-driven)
│   │   ├── celery_app.py   # Celery app config
│   │   ├── logging.py      # structured logging setup
│   │   └── limiter.py      # slowapi rate limiter
│   ├── db/
│   │   ├── models/         # User, Document, Chunk, Job, Conversation, Message
│   │   └── session.py      # SQLAlchemy session, get_db dependency
│   ├── schemas/             # Pydantic request/response models
│   ├── workers/
│   │   └── document_worker.py  # Celery task: extract → chunk → embed → store
│   └── rag/                 # (Phase 2) BM25 index, RRF fusion, reranking
├── alembic/                  # DB migrations
├── tests/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- Docker Desktop
- Python 3.12 (for running things outside Docker, e.g. Alembic commands)
- A Groq API key (free tier available at [console.groq.com](https://console.groq.com))

### Clone & Configure

```cmd
git clone <your-repo-url>
cd cortex\backend
copy .env.example .env
```

Fill in `.env` (see [Environment Variables](#environment-variables) below).

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@postgres:5432/cortex` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `QDRANT_URL` | Qdrant connection string | `http://qdrant:6333` |
| `GROQ_API_KEY` | API key for Groq LLM | `gsk_...` |
| `JWT_SECRET_KEY` | Secret for signing JWTs | (generate a long random string) |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry | `60` |
| `MAX_FILE_SIZE_MB` | Upload size cap | `25` |

> **Note:** `postgresql://` scheme is required — `postgres://` (used by some hosts) will break SQLAlchemy 2.0 and must be rewritten.

---

## Running the Project

### Full stack via Docker Compose

```cmd
docker compose up -d
```

This starts `postgres`, `redis`, `qdrant`, and `backend`, with healthchecks gating startup order.

### Local development (backend outside Docker, infra inside)

```cmd
docker compose up -d postgres redis qdrant
alembic upgrade head
uvicorn main:app --reload --reload-dir app
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

> **Windows note:** `--pool=solo` is required for Celery on Windows — the default `prefork` pool fails with `PermissionError` due to how `billiard` handles process forking on Windows.

### Clean-slate reset (for testing reproducibility)

```cmd
docker compose down -v
docker compose up -d postgres redis qdrant
alembic upgrade head
```

This wipes all data (Postgres + Qdrant volumes) and rebuilds the schema from migrations.

---

## API Reference

All endpoints except `/auth/signup` and `/auth/login` require a Bearer JWT.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/signup` | Create an account |
| `POST` | `/auth/login` | Get a JWT access token |
| `POST` | `/documents/upload` | Upload a document (PDF/MD/TXT/DOCX), triggers async processing |
| `GET` | `/documents/` | List your uploaded documents |
| `GET` | `/documents/{id}` | Get a single document's status |
| `DELETE` | `/documents/{id}` | Delete a document (removes file, DB rows, and Qdrant vectors) |
| `POST` | `/search/` | Semantic search across your documents |
| `POST` | `/chat/` | Ask a question, get a grounded answer with citations |

Full interactive docs available at `/docs` (Swagger UI) once the server is running.

---

## How Document Processing Works

1. **Upload** — file is validated (type + size), saved to disk with a UUID-prefixed name, and a `Document` (status: `pending`) + `Job` row are created. The HTTP request returns immediately.
2. **Celery picks up the task** in the background:
   - **Extract text** — `pypdf` for PDFs, `python-docx` for Word files, plain read for `.md`/`.txt`
   - **Chunk** — splits into 500-word segments with 50-word overlap (overlap preserves context across chunk boundaries)
   - **Embed** — all chunks for a document are embedded in a single batched call (much faster than one-by-one)
   - **Store** — chunks go into Postgres, vectors go into Qdrant
3. **Status updates** — `Document.upload_status` and `Job.status` move from `pending` → `processing` → `done` (or `failed`, with the error message saved)

---

## How Search & Chat Work

**Search (`POST /search/`)**: your query is embedded with the same model used for documents, then Qdrant returns the top-k most similar chunks, filtered to only your own documents.

**Chat (`POST /chat/`)**: same retrieval step, then the retrieved chunks are inserted into a prompt that explicitly instructs the LLM to answer *only* from the given context. The response includes a `sources` array (document name, chunk ID, similarity score) so every answer is traceable back to the exact chunks that produced it. Conversations persist across turns via `conversation_id`.

---

## Testing

```cmd
cd backend
pytest -v
```

Covers: duplicate signup rejection, wrong-password login rejection, invalid file type rejection, unauthenticated access rejection. Tests run against a fresh database — no manual seeding required.

---

## Security Notes

- Every Qdrant vector is tagged with `user_id` at write time, and every search/chat query filters by it — even though this is currently a single-user project, this prevents any document from being retrievable outside the account that owns it if Cortex is ever deployed with a public-facing login.
- Passwords are hashed with bcrypt, never stored in plaintext.
- JWT tokens are timezone-aware with a configurable expiry.
- CORS is currently permissive for local development and must be locked to a specific origin before any public deployment.

---

## Known Limitations

- **File storage is local disk**, not object storage. On most cloud hosts this is ephemeral — uploaded files may not survive a container restart. This is acceptable because only the *original file* needs disk access (at processing time); the durable data — chunks in Postgres, vectors in Qdrant — persists independently. Cloudinary integration is planned to remove this limitation entirely.
- **No frontend** — current interface is the Swagger UI (`/docs`).
- **Single `.env` file** — fine for one developer/one environment; not a secrets-management setup.
- **BM25 index (Phase 2) is in-memory per rebuild**, cached in Redis with a TTL — very large personal libraries (tens of thousands of chunks) may see rebuild latency; not a concern at personal-archive scale.

---

## Roadmap

- [x] **Phase 1** — Core RAG pipeline: upload, extraction, chunking, embeddings, vector storage, semantic search, citation-aware chat, auth, async processing
- [ ] **Phase 2** — Advanced retrieval: hybrid search (BM25 + vector + RRF fusion), cross-encoder reranking, metadata filtering, query rewriting, semantic caching, parent-child retrieval
- [ ] **Phase 3** — Production infrastructure: streaming responses, WebSockets, deeper observability, multi-file batch upload
- [ ] **Phase 4** — Agentic layer: summarization, comparison, study-plan generation, internet search tool use (LangGraph)
- [ ] **Phase 5** — Multi-agent orchestration (retriever / research / citation / memory / evaluator / planner agents)
- [ ] **Phase 6** — Evaluation framework: RAGAS/DeepEval, hallucination & retrieval scoring
- [ ] **Phase 7** — Knowledge graph: entity extraction, relationship mapping, concept maps
- [ ] **Phase 8** — Deployment hardening: CI/CD, HTTPS, full production rollout

**Current focus:** Phase 2, starting with hybrid search.
