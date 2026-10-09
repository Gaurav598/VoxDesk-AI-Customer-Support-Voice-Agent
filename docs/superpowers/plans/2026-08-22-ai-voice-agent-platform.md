# AI Voice Agent Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first AI voice support/sales platform MVP with local LLM, local STT boundary, knowledge search, tickets, and telephony/WhatsApp adapters.

**Architecture:** Core agent logic is isolated from external providers. Local services are verified with deterministic tests; Exotel, WhatsApp, STT, and TTS sit behind adapters so they can be wired when credentials and models are available.

**Tech Stack:** Python, FastAPI, Ollama, faster-whisper, Piper, Postgres, Redis, Chroma-ready knowledge boundary, unittest.

---

### Task 1: Core Domain and Knowledge

**Files:**
- Create: `backend/src/voice_agent/domain.py`
- Create: `backend/src/voice_agent/knowledge.py`
- Test: `backend/tests/test_knowledge.py`

- [x] **Step 1: Write failing knowledge test**
- [x] **Step 2: Implement domain objects and in-memory knowledge search**
- [x] **Step 3: Run `PYTHONPATH=src python3 -m unittest tests.test_knowledge -v`**

### Task 2: LLM and Orchestration

**Files:**
- Create: `backend/src/voice_agent/llm.py`
- Create: `backend/src/voice_agent/orchestrator.py`
- Create: `backend/src/voice_agent/tickets.py`
- Test: `backend/tests/test_orchestrator.py`
- Test: `backend/tests/test_ollama_payload.py`

- [x] **Step 1: Write failing orchestrator and Ollama payload tests**
- [x] **Step 2: Implement ticket store, Ollama payload builder, fallback LLM, and conversation orchestrator**
- [x] **Step 3: Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`**

### Task 3: Provider Boundaries

**Files:**
- Create: `backend/src/voice_agent/stt.py`
- Create: `backend/src/voice_agent/tts.py`
- Create: `backend/src/voice_agent/telephony.py`
- Create: `backend/src/voice_agent/whatsapp.py`

- [x] **Step 1: Add local STT, local TTS, telephony, and WhatsApp dry-run adapters**
- [x] **Step 2: Keep provider credentials out of source through `.env.example`**

### Task 4: API Shell

**Files:**
- Create: `backend/src/voice_agent/api.py`
- Create: `backend/pyproject.toml`

- [x] **Step 1: Add FastAPI app factory**
- [x] **Step 2: Add local simulation endpoints for knowledge, turn processing, and tickets**

### Task 5: Local Dev Setup and Docs

**Files:**
- Create: `README.md`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `docs/technical-design.md`

- [x] **Step 1: Document local-first architecture**
- [x] **Step 2: Add Postgres and Redis compose file**
- [x] **Step 3: List user-provided credentials required for real calling**
