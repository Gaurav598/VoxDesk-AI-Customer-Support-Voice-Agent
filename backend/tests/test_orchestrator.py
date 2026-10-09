import unittest

from voice_agent.domain import ActionType, CallMode, CallSession
from voice_agent.knowledge import InMemoryKnowledgeBase, KnowledgeDocument
from voice_agent.llm import RuleBasedFallbackLLM
from voice_agent.orchestrator import ConversationOrchestrator
from voice_agent.tickets import InMemoryTicketStore


class OrchestratorTests(unittest.TestCase):
    def test_payment_issue_creates_ticket_and_records_transcript(self):
        knowledge = InMemoryKnowledgeBase()
        knowledge.add_document(
            KnowledgeDocument(
                id="doc-1",
                organization_id="org-1",
                text="Payment deducted but order missing should be handled by creating a support ticket.",
            )
        )
        tickets = InMemoryTicketStore()
        orchestrator = ConversationOrchestrator(
            knowledge_base=knowledge,
            llm_client=RuleBasedFallbackLLM(),
            ticket_store=tickets,
        )
        session = CallSession(
            id="call-1",
            organization_id="org-1",
            caller_phone="demo-caller",
            mode=CallMode.SUPPORT,
        )

        result = orchestrator.handle_user_text(session, "My payment was deducted but order is not showing")

        self.assertIsNotNone(result.ticket)
        self.assertIn(ActionType.CREATE_TICKET, result.actions_executed)
        self.assertEqual(len(tickets.list_tickets()), 1)
        self.assertIn("customer:", session.transcript[0])
        self.assertIn("agent:", session.transcript[1])


if __name__ == "__main__":
    unittest.main()
