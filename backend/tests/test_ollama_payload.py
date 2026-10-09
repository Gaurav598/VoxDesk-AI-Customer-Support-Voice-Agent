import unittest

from voice_agent.domain import CallMode, CallSession
from voice_agent.llm import OllamaConfig, OllamaLLMClient


class OllamaPayloadTests(unittest.TestCase):
    def test_build_payload_targets_local_ollama_generate_api_shape(self):
        client = OllamaLLMClient(OllamaConfig(base_url="http://127.0.0.1:11434", model="llama3.2:3b"))
        session = CallSession(
            id="call-1",
            organization_id="org-1",
            caller_phone="demo-caller",
            mode=CallMode.SUPPORT,
        )

        payload = client.build_payload(session, "payment deducted", [])

        self.assertEqual(payload["model"], "llama3.2:3b")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["format"], "json")
        self.assertIn("Return only valid JSON", payload["prompt"])
        self.assertIn("payment deducted", payload["prompt"])


if __name__ == "__main__":
    unittest.main()
