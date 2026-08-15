from __future__ import annotations
import subprocess, sys, wave
from pathlib import Path
from piper import PiperVoice

def ensure_voice(voice_name: str, workdir: Path) -> Path:
    model_path = workdir / f"{voice_name}.onnx"
    if not model_path.exists():
        subprocess.run([
            sys.executable, "-m", "piper.download_voices",
            "--data-dir", str(workdir), voice_name
        ], check=True)
    if not model_path.exists():
        matches = list(workdir.glob(f"{voice_name}*.onnx"))
        if not matches:
            raise FileNotFoundError(f"Piper voice not downloaded: {voice_name}")
        model_path = matches[0]
    return model_path

def synthesize(text: str, voice_name: str, workdir: Path) -> Path:
    model = ensure_voice(voice_name, workdir)
    out = workdir / "narration.wav"
    voice = PiperVoice.load(str(model))
    with wave.open(str(out), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    return out
