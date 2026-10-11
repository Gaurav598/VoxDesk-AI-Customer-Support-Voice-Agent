import os
import json
import subprocess
import tempfile
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SynthesizedAudio:
    content_type: str
    data: bytes


class TTSEngine:
    def synthesize(self, text: str, language: str) -> SynthesizedAudio:
        raise NotImplementedError


class ChatterboxTTSEngine(TTSEngine):
    def __init__(self) -> None:
        self.device = os.getenv("TTS_DEVICE", "mps")
        self.voice_prompt_path = os.getenv("TTS_VOICE_PROMPT_PATH") or None
        self._model = None

    def synthesize(self, text: str, language: str) -> SynthesizedAudio:
        try:
            return self._synthesize_with_chatterbox(text, language)
        except Exception as error:
            print(f"Chatterbox TTS failed; using macOS fallback: {error}")
            return MacOSTTSEngine().synthesize(text, language)

    def _synthesize_with_chatterbox(self, text: str, language: str) -> SynthesizedAudio:
        import torchaudio

        language_id = normalize_language_id(language)
        if self._model is None:
            if language_id == "en":
                from chatterbox.tts import ChatterboxTTS

                self._model = ("en", ChatterboxTTS.from_pretrained(device=self.device))
            else:
                from chatterbox.mtl_tts import ChatterboxMultilingualTTS

                self._model = ("multi", ChatterboxMultilingualTTS.from_pretrained(device=self.device, t3_model="v3"))

        model_kind, model = self._model
        if model_kind == "en":
            wav = model.generate(text, audio_prompt_path=self.voice_prompt_path)
            sample_rate = model.sr
        else:
            generate_kwargs = {"language_id": language_id}
            if self.voice_prompt_path:
                generate_kwargs["audio_prompt_path"] = self.voice_prompt_path
            wav = model.generate(text, **generate_kwargs)
            sample_rate = model.sr

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        try:
            torchaudio.save(str(temp_path), wav, sample_rate)
            return SynthesizedAudio(content_type="audio/wav", data=temp_path.read_bytes())
        finally:
            temp_path.unlink(missing_ok=True)


class FishTTSEngine(TTSEngine):
    def __init__(self) -> None:
        self.api_key = os.getenv("FISH_API_KEY", "").strip()
        self.model = os.getenv("FISH_TTS_MODEL", "s2.1-pro-free").strip()
        self.reference_id = os.getenv("FISH_REFERENCE_ID", "").strip() or None
        self.timeout_seconds = int(os.getenv("FISH_TTS_TIMEOUT_SECONDS", "60"))

    def synthesize(self, text: str, language: str) -> SynthesizedAudio:
        del language
        if not self.api_key:
            raise RuntimeError("FISH_API_KEY is required when TTS_PROVIDER=fish.")

        payload = {
            "text": text,
            "format": "mp3",
            "latency": os.getenv("FISH_TTS_LATENCY", "balanced"),
            "prosody": {
                "speed": float(os.getenv("FISH_TTS_SPEED", "1")),
                "volume": float(os.getenv("FISH_TTS_VOLUME", "0")),
                "normalize_loudness": True,
            },
            "temperature": float(os.getenv("FISH_TTS_TEMPERATURE", "0.7")),
            "top_p": float(os.getenv("FISH_TTS_TOP_P", "0.7")),
            "repetition_penalty": float(os.getenv("FISH_TTS_REPETITION_PENALTY", "1.2")),
            "chunk_length": int(os.getenv("FISH_TTS_CHUNK_LENGTH", "250")),
            "min_chunk_length": int(os.getenv("FISH_TTS_MIN_CHUNK_LENGTH", "30")),
            "normalize": True,
            "condition_on_previous_chunks": True,
        }
        if self.reference_id:
            payload["reference_id"] = self.reference_id

        request = urllib.request.Request(
            "https://api.fish.audio/v1/tts",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "model": self.model,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                audio_bytes = response.read()
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Fish TTS failed with HTTP {error.code}: {body}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Fish TTS network error: {error.reason}") from error

        if not audio_bytes:
            raise RuntimeError("Fish TTS returned empty audio.")
        return SynthesizedAudio(content_type="audio/mpeg", data=audio_bytes)


class FishLocalTTSEngine(TTSEngine):
    def __init__(self) -> None:
        self.base_url = os.getenv("FISH_LOCAL_URL", "http://127.0.0.1:8080").rstrip("/")
        self.endpoint = os.getenv("FISH_LOCAL_ENDPOINT", "/v1/tts")
        self.api_key = os.getenv("FISH_LOCAL_API_KEY", "").strip()
        self.timeout_seconds = int(os.getenv("FISH_LOCAL_TIMEOUT_SECONDS", "120"))
        self.reference_id = os.getenv("FISH_LOCAL_REFERENCE_ID", "").strip() or None

    def synthesize(self, text: str, language: str) -> SynthesizedAudio:
        del language
        endpoint = self.endpoint if self.endpoint.startswith("/") else f"/{self.endpoint}"
        payload = {
            "text": text,
            "format": os.getenv("FISH_LOCAL_FORMAT", "wav"),
            "latency": os.getenv("FISH_LOCAL_LATENCY", "normal"),
            "prosody": {
                "speed": float(os.getenv("FISH_LOCAL_SPEED", "1")),
                "volume": float(os.getenv("FISH_LOCAL_VOLUME", "0")),
                "normalize_loudness": True,
            },
            "temperature": float(os.getenv("FISH_LOCAL_TEMPERATURE", "0.7")),
            "top_p": float(os.getenv("FISH_LOCAL_TOP_P", "0.7")),
            "repetition_penalty": float(os.getenv("FISH_LOCAL_REPETITION_PENALTY", "1.2")),
            "chunk_length": int(os.getenv("FISH_LOCAL_CHUNK_LENGTH", "250")),
            "min_chunk_length": int(os.getenv("FISH_LOCAL_MIN_CHUNK_LENGTH", "30")),
            "normalize": True,
            "condition_on_previous_chunks": True,
        }
        if self.reference_id:
            payload["reference_id"] = self.reference_id

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(
            f"{self.base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                audio_bytes = response.read()
                content_type = response.headers.get("Content-Type", "audio/wav").split(";")[0]
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Fish local TTS failed with HTTP {error.code}: {body}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Fish local TTS network error: {error.reason}") from error

        if not audio_bytes:
            raise RuntimeError("Fish local TTS returned empty audio.")
        return SynthesizedAudio(content_type=content_type, data=audio_bytes)


class MacOSTTSEngine(TTSEngine):
    def synthesize(self, text: str, language: str) -> SynthesizedAudio:
        voice = macos_voice_for_language(language)
        with tempfile.TemporaryDirectory() as temp_dir:
            aiff_path = Path(temp_dir) / "speech.aiff"
            wav_path = Path(temp_dir) / "speech.wav"
            subprocess.run(["say", "-v", voice, "-o", str(aiff_path), text], check=True)
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@24000", str(aiff_path), str(wav_path)], check=True)
            return SynthesizedAudio(content_type="audio/wav", data=wav_path.read_bytes())


class SilentTTSEngine(TTSEngine):
    def synthesize(self, text: str, language: str) -> SynthesizedAudio:
        del text, language
        sample_rate = 24000
        duration_seconds = 0.15
        frames = int(sample_rate * duration_seconds)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        try:
            with wave.open(str(temp_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b"\x00\x00" * frames)
            return SynthesizedAudio(content_type="audio/wav", data=temp_path.read_bytes())
        finally:
            temp_path.unlink(missing_ok=True)


def create_tts_engine(provider: str | None = None) -> TTSEngine:
    selected_provider = (provider or os.getenv("TTS_PROVIDER", "macos")).lower()
    if selected_provider == "fish_local":
        return FishLocalTTSEngine()
    if selected_provider == "fish":
        return FishTTSEngine()
    if selected_provider == "chatterbox":
        return ChatterboxTTSEngine()
    if selected_provider == "macos":
        return MacOSTTSEngine()
    if selected_provider in ("silent", "local", "mock"):
        return SilentTTSEngine()
    raise ValueError(f"Unsupported TTS provider: {selected_provider}")


def normalize_language_id(language: str) -> str:
    normalized = language.lower()
    if normalized.startswith("hi"):
        return "hi"
    if normalized.startswith("te"):
        return "te"
    return "en"


def macos_voice_for_language(language: str) -> str:
    normalized = language.lower()
    if normalized.startswith("hi"):
        return "Lekha"
    if normalized.startswith("te"):
        return "Lekha"
    return "Samantha"
