# Technical Design

## Goal

Build a local-first AI voice agent platform for organizations. The MVP handles inbound support calls, understands customer issues, searches organization knowledge, replies by voice, creates tickets, and sends WhatsApp summaries when provider credentials are available.

## Architecture

The product is split into adapters and core services. Core services run locally and are testable without telecom credentials. External systems are isolated behind provider interfaces.

## Local-first services

- `ConversationOrchestrator`: owns call state and action execution.
- `LLMClient`: produces structured decisions. Ollama is the real local provider; rule-based fallback is used for deterministic tests.
- `SQLiteStore`: local durable store for knowledge, call sessions, transcript turns, and tickets.
- `PlatformService`: local product service for adding knowledge, processing support turns, and reading tickets/transcripts.
- `JsonRouter`: dependency-free HTTP route layer for local end-to-end testing before FastAPI deployment.
- `FasterWhisperTranscriber`: local speech-to-text adapter.
- `PiperSynthesizer`: local text-to-speech adapter.
- `ExotelAdapter`: parses telephony webhook payloads.
- `DryRunWhatsAppClient`: records WhatsApp messages until live API credentials are provided.

## MVP requirements

- One organization can load support knowledge.
- One inbound support call can be represented as a call session.
- Customer speech text can be processed into an agent decision.
- Payment/order issues create tickets.
- Conversation transcript is recorded.
- WhatsApp is dry-run until credentials exist.
- Ollama payload uses local `/api/generate` JSON mode.
- Local HTTP API supports `/health`, `/knowledge`, `/calls/turn`, and `/tickets`.

## Current end-to-end status

Local end-to-end is implemented for text-based support turns:

1. Add organization knowledge through HTTP.
2. Submit a customer support message through HTTP.
3. Agent decides the response.
4. Ticket is created when needed.
5. Transcript and ticket are stored in SQLite.
6. Tickets can be fetched through HTTP.

Real voice end-to-end is intentionally blocked until provider credentials and local audio models exist.

## External requirements

Real calls require an Indian telephony provider such as Exotel or Plivo. Real WhatsApp requires Meta Cloud API or Exotel WhatsApp credentials. These are intentionally outside local verification.
