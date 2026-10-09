import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from voice_agent.local_server import create_handler
from voice_agent.platform import PlatformService
from voice_agent.storage import SQLiteStore


class ExotelWebhookTests(unittest.TestCase):
    def test_inbound_webhook_is_public_and_records_call_reachability(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PlatformService.local(store=SQLiteStore(Path(temp_dir) / "voice_agent.db"))
            handler = create_handler(service, api_token="private-api-token")

            log_output = io.StringIO()
            with redirect_stdout(log_output):
                status, _headers, body = handler.handle_json(
                    "GET",
                    "/webhooks/exotel/inbound?CallSid=abc&CallFrom=999&CallTo=09513886363",
                    headers={},
                )

            self.assertEqual(status, 200)
            self.assertIn("exotel_inbound_received", body)
            self.assertNotIn("CallFrom", log_output.getvalue())
            self.assertNotIn("09513886363", log_output.getvalue())


if __name__ == "__main__":
    unittest.main()
