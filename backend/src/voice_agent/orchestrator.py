from dataclasses import dataclass

from voice_agent.domain import ActionType, AgentDecision, CallSession, Ticket
from voice_agent.knowledge import InMemoryKnowledgeBase
from voice_agent.llm import LLMClient
from voice_agent.tickets import InMemoryTicketStore


@dataclass(frozen=True)
class TurnResult:
    decision: AgentDecision
    ticket: Ticket | None
    actions_executed: list[ActionType]


class ConversationOrchestrator:
    def __init__(
        self,
        knowledge_base: InMemoryKnowledgeBase,
        llm_client: LLMClient,
        ticket_store: InMemoryTicketStore,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.llm_client = llm_client
        self.ticket_store = ticket_store

    def handle_user_text(self, session: CallSession, user_text: str) -> TurnResult:
        session.transcript.append(f"customer: {user_text}")
        knowledge = self.knowledge_base.search(session.organization_id, user_text)
        decision = self.llm_client.decide(session, user_text, knowledge)
        session.language = decision.language
        session.transcript.append(f"agent: {decision.reply}")

        ticket = None
        actions_executed: list[ActionType] = [ActionType.REPLY]
        if ActionType.CREATE_TICKET in decision.actions:
            ticket = self.ticket_store.create_ticket(
                organization_id=session.organization_id,
                caller_phone=session.caller_phone,
                call_id=session.id,
                title=decision.ticket_title or "Support ticket from AI call",
                description=decision.ticket_description or user_text,
            )
            actions_executed.append(ActionType.CREATE_TICKET)

        for action in decision.actions:
            if action not in actions_executed:
                actions_executed.append(action)

        return TurnResult(decision=decision, ticket=ticket, actions_executed=actions_executed)
