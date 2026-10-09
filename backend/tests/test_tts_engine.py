import json
import os
import unittest
from unittest.mock import patch

from voice_agent.tts_engine import FishLocalTTSEngine, FishTTSEngine, create_tts_engine


class FakeFishResponse:
    def __init__(
        self,
        status: int = 200,
        body: bytes = b"mp3-bytes",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._body = body
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return self._body


class FishTTSEngineTests(unittest.TestCase):
    def test_create_tts_engine_supports_fish_provider(self):
        self.assertIsInstance(create_tts_engine("fish"), FishTTSEngine)

    def test_fish_tts_posts_to_fish_api_with_free_model_header(self):
        captured_requests = []

        def fake_urlopen(request, timeout):
            captured_requests.append((request, timeout))
            return FakeFishResponse(body=b"real-human-audio")

        with patch.dict(os.environ, {"FISH_API_KEY": "fish-secret"}, clear=False):
            with patch("voice_agent.tts_engine.urllib.request.urlopen", side_effect=fake_urlopen):
                audio = FishTTSEngine().synthesize("Hello from support", "en-IN")

        request, timeout = captured_requests[0]
        payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual(request.full_url, "https://api.fish.audio/v1/tts")
        self.assertEqual(request.get_header("Authorization"), "Bearer fish-secret")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(request.get_header("Model"), "s2.1-pro-free")
        self.assertEqual(payload["text"], "Hello from support")
        self.assertEqual(payload["format"], "mp3")
        self.assertEqual(payload["latency"], "balanced")
        self.assertEqual(timeout, 60)
        self.assertEqual(audio.content_type, "audio/mpeg")
        self.assertEqual(audio.data, b"real-human-audio")

    def test_fish_tts_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "FISH_API_KEY"):
                FishTTSEngine().synthesize("hello", "en-IN")

    def test_create_tts_engine_supports_fish_local_provider(self):
        self.assertIsInstance(create_tts_engine("fish_local"), FishLocalTTSEngine)

    def test_fish_local_tts_posts_to_local_server(self):
        captured_requests = []

        def fake_urlopen(request, timeout):
            captured_requests.append((request, timeout))
            return FakeFishResponse(body=b"local-fish-audio", headers={"Content-Type": "audio/wav"})

        with patch.dict(
            os.environ,
            {
                "FISH_LOCAL_URL": "http://127.0.0.1:8080",
                "FISH_LOCAL_ENDPOINT": "/v1/tts",
                "FISH_LOCAL_API_KEY": "local-secret",
            },
            clear=False,
        ):
            with patch("voice_agent.tts_engine.urllib.request.urlopen", side_effect=fake_urlopen):
                audio = FishLocalTTSEngine().synthesize("Hello from local Fish", "en-IN")

        request, timeout = captured_requests[0]
        payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual(request.full_url, "http://127.0.0.1:8080/v1/tts")
        self.assertEqual(request.get_header("Authorization"), "Bearer local-secret")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(payload["text"], "Hello from local Fish")
        self.assertEqual(payload["format"], "wav")
        self.assertEqual(payload["latency"], "normal")
        self.assertEqual(timeout, 120)
        self.assertEqual(audio.content_type, "audio/wav")
        self.assertEqual(audio.data, b"local-fish-audio")


if __name__ == "__main__":
    unittest.main()
