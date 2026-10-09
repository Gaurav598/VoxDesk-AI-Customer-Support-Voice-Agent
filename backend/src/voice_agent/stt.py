from pathlib import Path


class FasterWhisperTranscriber:
    def __init__(self, model_size: str = "small", device: str = "auto") -> None:
        self.model_size = model_size
        self.device = device
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_size, device=self.device)
        return self._model

    def transcribe_file(self, audio_path: str | Path) -> str:
        model = self._load_model()
        segments, _info = model.transcribe(str(audio_path), vad_filter=True)
        return " ".join(segment.text.strip() for segment in segments).strip()
