import tempfile
import unittest
from pathlib import Path

from voice_agent.platform import PlatformService
from voice_agent.storage import SQLiteStore


class PlatformServiceTests(unittest.TestCase):
    def test_support_turn_runs_end_to_end_and_persists_ticket(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "voice_agent.db")
            service = PlatformService.local(store=store)
            service.add_knowledge(
                organization_id="org-1",
                text="Payment deducted but order missing should create a support ticket.",
            )

            result = service.handle_support_turn(
                organization_id="org-1",
                caller_phone="demo-caller",
                text="My payment was deducted but order is not showing",
            )

            self.assertIn("create_ticket", result["actions"])
            self.assertIsNotNone(result["ticket_id"])
            self.assertEqual(len(service.list_tickets()), 1)
            self.assertIn("agent:", service.get_call_transcript(result["call_id"])[1])


if __name__ == "__main__":
    unittest.main()
