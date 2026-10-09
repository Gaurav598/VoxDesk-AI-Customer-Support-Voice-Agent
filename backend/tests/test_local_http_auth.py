import tempfile
import unittest
from pathlib import Path

from voice_agent.local_server import create_handler
from voice_agent.platform import PlatformService
from voice_agent.storage import SQLiteStore


class LocalHttpAuthTests(unittest.TestCase):
    def test_protected_route_rejects_missing_token(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PlatformService.local(store=SQLiteStore(Path(temp_dir) / "voice_agent.db"))
            handler = create_handler(service, api_token="secret-token")

            status, _headers, body = handler.handle_json(
                "POST",
                "/knowledge",
                {"organization_id": "org-1", "text": "hello"},
                headers={},
            )

            self.assertEqual(status, 401)
            self.assertIn("unauthorized", body)

    def test_protected_route_accepts_matching_token(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PlatformService.local(store=SQLiteStore(Path(temp_dir) / "voice_agent.db"))
            handler = create_handler(service, api_token="secret-token")

            status, _headers, body = handler.handle_json(
                "POST",
                "/knowledge",
                {"organization_id": "org-1", "text": "hello"},
                headers={"X-Voice-Agent-Token": "secret-token"},
            )

            self.assertEqual(status, 200)
            self.assertIn("stored", body)


if __name__ == "__main__":
    unittest.main()
