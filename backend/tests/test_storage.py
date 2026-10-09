import tempfile
import unittest
from pathlib import Path

from voice_agent.domain import CallMode, CallSession
from voice_agent.storage import SQLiteStore


class SQLiteStoreTests(unittest.TestCase):
    def test_persists_knowledge_tickets_and_call_transcript(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "voice_agent.db"
            store = SQLiteStore(db_path)
            store.migrate()

            store.add_knowledge("org-1", "Payments deducted without orders should create tickets.")
            hits = store.search_knowledge("org-1", "payment order ticket")

            session = CallSession(
                id="call-1",
                organization_id="org-1",
                caller_phone="demo-caller",
                mode=CallMode.SUPPORT,
            )
            store.save_call_session(session)
            store.append_call_turn("call-1", "customer", "payment deducted")
            ticket = store.create_ticket(
                organization_id="org-1",
                caller_phone="demo-caller",
                call_id="call-1",
                title="Payment issue",
                description="payment deducted",
            )

            reopened = SQLiteStore(db_path)
            reopened.migrate()

            self.assertEqual(len(hits), 1)
            self.assertEqual(reopened.list_tickets()[0].id, ticket.id)
            self.assertEqual(reopened.get_call_transcript("call-1"), ["customer: payment deducted"])


if __name__ == "__main__":
    unittest.main()
