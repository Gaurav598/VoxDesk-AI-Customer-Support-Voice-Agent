import subprocess
from pathlib import Path


class PiperSynthesizer:
    def __init__(self, piper_binary: str = "piper", voice_model_path: str | None = None) -> None:
        self.piper_binary = piper_binary
        self.voice_model_path = voice_model_path

    def synthesize_to_file(self, text: str, output_path: str | Path) -> Path:
        if not self.voice_model_path:
            raise RuntimeError("Piper voice model path is required for local TTS.")

        output = Path(output_path)
        command = [
            self.piper_binary,
            "--model",
            self.voice_model_path,
            "--output_file",
            str(output),
        ]
        subprocess.run(command, input=text.encode("utf-8"), check=True)
        return output
