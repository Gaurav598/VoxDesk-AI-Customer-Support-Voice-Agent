from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

from voice_agent.domain import CallMode, CallSession
from voice_agent.knowledge import InMemoryKnowledgeBase, KnowledgeDocument
from voice_agent.llm import RuleBasedFallbackLLM
from voice_agent.orchestrator import ConversationOrchestrator
from voice_agent.tickets import InMemoryTicketStore


class KnowledgeRequest(BaseModel):
    organization_id: str
    text: str


class TurnRequest(BaseModel):
    organization_id: str
    caller_phone: str
    text: str
    mode: CallMode = CallMode.SUPPORT


def create_app() -> FastAPI:
    app = FastAPI(title="VoxDesk")
    knowledge = InMemoryKnowledgeBase()
    tickets = InMemoryTicketStore()
    orchestrator = ConversationOrchestrator(
        knowledge_base=knowledge,
        llm_client=RuleBasedFallbackLLM(),
        ticket_store=tickets,
    )

    @app.post("/knowledge")
    def add_knowledge(request: KnowledgeRequest) -> dict:
        knowledge.add_document(
            KnowledgeDocument(
                id=f"DOC-{uuid4().hex[:8].upper()}",
                organization_id=request.organization_id,
                text=request.text,
            )
        )
        return {"status": "stored"}

    @app.post("/simulate/turn")
    def simulate_turn(request: TurnRequest) -> dict:
        session = CallSession(
            id=f"CALL-{uuid4().hex[:8].upper()}",
            organization_id=request.organization_id,
            caller_phone=request.caller_phone,
            mode=request.mode,
        )
        result = orchestrator.handle_user_text(session, request.text)
        return {
            "reply": result.decision.reply,
            "language": result.decision.language,
            "intent": result.decision.intent,
            "status": result.decision.status,
            "actions": [action.value for action in result.actions_executed],
            "ticket_id": result.ticket.id if result.ticket else None,
            "transcript": session.transcript,
        }

    @app.get("/tickets")
    def list_tickets() -> list[dict]:
        return [ticket.__dict__ for ticket in tickets.list_tickets()]

    return app


app = create_app()
