import json
import tempfile
import unittest
from pathlib import Path

from voice_agent.local_server import create_handler
from voice_agent.platform import PlatformService
from voice_agent.storage import SQLiteStore
from voice_agent.tts_engine import SynthesizedAudio


class FakeTTSEngine:
    def synthesize(self, text: str, language: str) -> SynthesizedAudio:
        return SynthesizedAudio(content_type="audio/wav", data=b"RIFFfake-wav")


class LocalHttpServerTests(unittest.TestCase):
    def test_handler_routes_support_turn_without_fastapi_dependency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PlatformService.local(store=SQLiteStore(Path(temp_dir) / "voice_agent.db"))
            handler = create_handler(service)

            knowledge_status, _headers, knowledge_body = handler.handle_json(
                "POST",
                "/knowledge",
                {
                    "organization_id": "org-1",
                    "text": "Payment deducted but order missing should create ticket.",
                },
            )
            turn_status, _headers, turn_body = handler.handle_json(
                "POST",
                "/calls/turn",
                {
                    "organization_id": "org-1",
                    "caller_phone": "demo-caller",
                    "text": "payment deducted but order missing",
                },
            )

            self.assertEqual(knowledge_status, 200)
            self.assertEqual(json.loads(knowledge_body)["status"], "stored")
            self.assertEqual(turn_status, 200)
            self.assertIsNotNone(json.loads(turn_body)["ticket_id"])

    def test_handler_accepts_language_hint_for_support_turn(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PlatformService.local(store=SQLiteStore(Path(temp_dir) / "voice_agent.db"))
            handler = create_handler(service)

            turn_status, _headers, turn_body = handler.handle_json(
                "POST",
                "/calls/turn",
                {
                    "organization_id": "org-1",
                    "caller_phone": "browser-user",
                    "text": "hello",
                    "language": "hi-IN",
                },
            )

            self.assertEqual(turn_status, 200)
            self.assertEqual(json.loads(turn_body)["language"], "hi-IN")

    def test_serves_browser_call_test_page_without_auth(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PlatformService.local(store=SQLiteStore(Path(temp_dir) / "voice_agent.db"))
            handler = create_handler(service, api_token="secret")

            status, headers, body = handler.handle_json("GET", "/browser-call", headers={})

            self.assertEqual(status, 200)
            self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
            self.assertIn("AI Voice Agent Browser Call Test", body)
            self.assertIn("webkitSpeechRecognition", body)
            self.assertIn("/calls/turn", body)
            self.assertIn("Live conversation mode", body)
            self.assertIn("languageSelect", body)
            self.assertIn("restartListeningAfterAgent", body)
            self.assertIn("recognition.continuous = true", body)
            self.assertIn("scheduleListeningRestart", body)
            self.assertIn("/tts/synthesize", body)
            self.assertIn("audio.play()", body)
            self.assertNotIn("new SpeechSynthesisUtterance", body)

    def test_tts_synthesize_returns_audio_wav(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PlatformService.local(store=SQLiteStore(Path(temp_dir) / "voice_agent.db"))
            handler = create_handler(service, api_token="secret", tts_engine=FakeTTSEngine())

            status, headers, body = handler.handle_json(
                "POST",
                "/tts/synthesize",
                {"text": "hello", "language": "en-IN"},
                headers={"X-Voice-Agent-Token": "secret"},
            )

            self.assertEqual(status, 200)
            self.assertEqual(headers["Content-Type"], "audio/wav")
            self.assertEqual(body, b"RIFFfake-wav")


if __name__ == "__main__":
    unittest.main()
