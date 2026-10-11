from pathlib import Path
from uuid import uuid4

from voice_agent.domain import ActionType, CallMode, CallSession
from voice_agent.llm import LLMClient, create_llm_client
from voice_agent.storage import SQLiteStore


class PlatformService:
    def __init__(self, store: SQLiteStore, llm_client: LLMClient) -> None:
        self.store = store
        self.llm_client = llm_client
        self.store.migrate()

    @classmethod
    def local(cls, store: SQLiteStore | None = None, llm_client: LLMClient | None = None) -> "PlatformService":
        default_store = store or SQLiteStore(Path("data") / "voice_agent.db")
        return cls(store=default_store, llm_client=llm_client or create_llm_client())

    def add_knowledge(self, organization_id: str, text: str) -> dict:
        document_id = self.store.add_knowledge(organization_id, text)
        return {"status": "stored", "document_id": document_id}

    def handle_support_turn(
        self,
        organization_id: str,
        caller_phone: str,
        text: str,
        language: str = "unknown",
    ) -> dict:
        session = CallSession(
            id=f"CALL-{uuid4().hex[:8].upper()}",
            organization_id=organization_id,
            caller_phone=caller_phone,
            mode=CallMode.SUPPORT,
            language=language,
        )
        self.store.save_call_session(session)
        self.store.append_call_turn(session.id, "customer", text)
        knowledge = self.store.search_knowledge(organization_id, text)
        decision = self.llm_client.decide(session, text, knowledge)
        self.store.append_call_turn(session.id, "agent", decision.reply)

        ticket = None
        actions_executed: list[ActionType] = [ActionType.REPLY]
        if ActionType.CREATE_TICKET in decision.actions:
            ticket = self.store.create_ticket(
                organization_id=organization_id,
                caller_phone=caller_phone,
                call_id=session.id,
                title=decision.ticket_title or "Support ticket from AI call",
                description=decision.ticket_description or text,
            )
            actions_executed.append(ActionType.CREATE_TICKET)

        for action in decision.actions:
            if action not in actions_executed:
                actions_executed.append(action)

        return {
            "call_id": session.id,
            "reply": decision.reply,
            "language": decision.language,
            "intent": decision.intent,
            "status": decision.status,
            "actions": [action.value for action in actions_executed],
            "ticket_id": ticket.id if ticket else None,
        }

    def list_tickets(self) -> list[dict]:
        return [ticket.__dict__ for ticket in self.store.list_tickets()]

    def list_knowledge(self, organization_id: str | None = None) -> list[dict]:
        return self.store.list_knowledge(organization_id)

    def list_calls(self, organization_id: str | None = None) -> list[dict]:
        return self.store.list_calls(organization_id)

    def get_call_transcript(self, call_id: str) -> list[str]:
        return self.store.get_call_transcript(call_id)

