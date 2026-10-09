from voice_agent.domain import CallMode, CallSession
from voice_agent.knowledge import InMemoryKnowledgeBase, KnowledgeDocument
from voice_agent.llm import RuleBasedFallbackLLM
from voice_agent.orchestrator import ConversationOrchestrator
from voice_agent.tickets import InMemoryTicketStore


def main() -> None:
    knowledge = InMemoryKnowledgeBase()
    knowledge.add_document(
        KnowledgeDocument(
            id="doc-payment-policy",
            organization_id="demo-org",
            text=(
                "If payment is deducted but order is not visible, create a support ticket, "
                "ask for order ID or registered phone number, and tell the customer they will "
                "receive an update after payment reconciliation."
            ),
        )
    )
    tickets = InMemoryTicketStore()
    orchestrator = ConversationOrchestrator(
        knowledge_base=knowledge,
        llm_client=RuleBasedFallbackLLM(),
        ticket_store=tickets,
    )
    session = CallSession(
        id="demo-call-1",
        organization_id="demo-org",
        caller_phone="demo-caller",
        mode=CallMode.SUPPORT,
    )

    print("AI Voice Agent local demo")
    print("Type a customer message. Type 'exit' to stop.")
    while True:
        user_text = input("\nCustomer: ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break
        result = orchestrator.handle_user_text(session, user_text)
        print(f"Agent: {result.decision.reply}")
        print(f"Actions: {[action.value for action in result.actions_executed]}")
        if result.ticket:
            print(f"Ticket: {result.ticket.id} - {result.ticket.title}")


if __name__ == "__main__":
    main()
