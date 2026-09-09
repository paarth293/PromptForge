# PromptForge — Architecture Decisions

This document records the core architectural and technical stack decisions for PromptForge, fulfilling Step 2 of Phase 0.

---

## 1. Backend Framework: Python (FastAPI)
* **Decision:** FastAPI with Uvicorn and Pydantic v2.
* **Rationale:** Asynchronous concurrency (`asyncio`) is mandatory for running concurrent Red Team attack sessions (concurrency 8–10) and streaming real-time verdicts via Server-Sent Events (SSE). Python provides the deepest ecosystem for LLM SDKs, JSON-schema validation, and embeddings math.

## 2. Frontend Framework: Next.js (React) + TailwindCSS
* **Decision:** Next.js (App Router / React) styled with TailwindCSS and Lucide icons.
* **Rationale:** Next.js supports seamless Server-Sent Events (SSE) subscriptions, reactive UI rendering for live-streaming attacks, interactive cards for Stage 0 Spec Confirmation, and responsive layout for the two-surface (Ask vs. Deploy) product model.

## 3. Database & Storage: SQLite with async driver (aiosqlite)
* **Decision:** SQLite with async support for development, architected with repository abstractions for pluggable PostgreSQL support.
* **Rationale:** SQLite requires zero infrastructure setup overhead on local environments while providing reliable ACID transactions, relational integrity, and fast file-based persistence for `AgentBlueprint`, `RedTeamReport`, and `AdversarialPlaybookEntry`.

## 4. Vector Store & Embeddings Engine
* **Decision:** Lightweight Python-based vector cosine similarity engine with pluggable model embeddings (SentenceTransformers / OpenAI embeddings / fast local hash embeddings fallback).
* **Rationale:** Needed for duplicate-attack filtering in the Red Team quality gate and fact comparison in structure-aware consistency evaluation. A standalone Python embedding/similarity layer avoids heavy external vector database or C++ compilation dependencies.

## 5. Multi-Provider LLM Abstraction Layer
* **Decision:** Unified provider client (`LLMClient`) supporting:
  - OpenAI (GPT-4o, GPT-4o-mini)
  - Anthropic (Claude 3.5 Sonnet)
  - Google Gemini (Gemini 1.5/2.0 Flash/Pro)
  - Ollama (Local open-weight models like Llama 3)
  - Deterministic Mock / Simulation Provider (for hermetic testing and offline CI/CD)
* **Rationale:** Fulfills the 3-axis diversity requirement where the Red Team generator, target agent, and evaluator judge are deliberately different models or personas.

## 6. Cryptographic Spine & Tamper-Evident Ledger
* **Decision:** SHA-256 hash chaining implemented in pure Python.
* **Rationale:** Every lifecycle event (spec creation, blueprint assembly, attack verdicts, hardening diffs, verification scorecards, and deployment) is cryptographically linked to the prior event hash. This produces a verifiable, tamper-evident Birth Certificate and Agent Dossier.

## 7. Hosting & Deployment Target
* **Decision:** Containerized service (Docker) ready for unified deployment on Render/Railway/Fly.io or self-hosted execution.
* **Rationale:** Clean separation of concerns allows running backend and frontend either unified or as decoupled microservices.
