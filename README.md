# PromptForge

> **The Self-Hardening Forge for AI Agents — The Operating System for AI Agents, Built Entirely Through Prompts.**

PromptForge takes a natural-language description of an AI agent (or an imported third-party agent) and generates, red-teams, hardens, empirically verifies, shields, and deploys it — entirely through orchestrated prompt chains and a deterministic verification spine.

---

## Architecture Overview

* **Backend:** Python 3.11 with FastAPI, Uvicorn, and Pydantic v2.
* **Frontend:** Next.js 14 App Router, React 18, Tailwind CSS, Lucide icons.
* **Database:** SQLite with `aiosqlite` async migrations engine.
* **LLM Abstraction:** Multi-provider client supporting OpenAI, Anthropic, Gemini, Ollama, and deterministic Mock/Simulation modes.
* **Spine:** SHA-256 hash chaining, deterministic middleware, and structure-aware scoring.

---

## Local Development Quickstart

### 1. Prerequisites
* Python 3.11+
* Node.js v20+ / v24+
* npm or pnpm

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Run migrations and tests
python -m pytest backend/tests/

# Start FastAPI development server
uvicorn backend.app.main:app --reload --port 8000
```
Backend API will be accessible at: `http://localhost:8000` (Health endpoint: `http://localhost:8000/health`).

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend will be accessible at: `http://localhost:3000`.

---

## Milestones
* ⭐ `milestone-scaffold`: Phase 0 scaffold complete (Backend, Frontend, Database, Multi-Provider LLM Client, Pre-commit hooks).
