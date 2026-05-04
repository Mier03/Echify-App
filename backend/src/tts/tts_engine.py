# tts_engine.py
import subprocess
import threading
import queue
import re
from pathlib import Path
from TTS.api import TTS

# --- Model loaded once at import time (you already do this, good) ---
tts = TTS(
    model_name="tts_models/en/vctk/vits",
    progress_bar=False
)

SPEAKER = tts.speakers[0]
TMP_DIR = Path("/tmp/coqui_chunks")
TMP_DIR.mkdir(exist_ok=True)

# Pre-warm: run a silent dummy inference so the first real call isn't cold
def _prewarm():
    try:
        p = TMP_DIR / "_prewarm.wav"
        tts.tts_to_file(text="hello", file_path=str(p), speaker=SPEAKER)
    except Exception:
        pass

threading.Thread(target=_prewarm, daemon=True).start()


def _split_sentences(text: str) -> list[str]:
    """Split text into speakable chunks."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def speak(text: str):
    """
    Pipeline: sentence chunks are generated and played in parallel.
    Generation of chunk N+1 overlaps with playback of chunk N.
    """
    if not text or not text.strip():
        return

    chunks = _split_sentences(text)
    audio_queue = queue.Queue()
    SENTINEL = None

    def _generate():
        """Producer: synthesize each chunk and enqueue the wav path."""
        for i, chunk in enumerate(chunks):
            out_path = TMP_DIR / f"chunk_{i}.wav"
            try:
                tts.tts_to_file(
                    text=chunk,
                    file_path=str(out_path),
                    speaker=SPEAKER,
                )
                audio_queue.put(str(out_path))
            except Exception as e:
                print(f"❌ TTS generation error: {e}")
        audio_queue.put(SENTINEL)  # signal done

    def _play():
        """Consumer: play each wav as soon as it's ready."""
        while True:
            path = audio_queue.get()
            if path is SENTINEL:
                break
            try:
                subprocess.run(
                    ["aplay", "-D", "default", path],
                    check=False
                )
            except Exception as e:
                print(f"❌ Playback error: {e}")

    gen_thread = threading.Thread(target=_generate, daemon=True)
    play_thread = threading.Thread(target=_play, daemon=True)

    gen_thread.start()
    play_thread.start()


class EmergencyAudio:
    def __init__(self, wav_path="/home/sms/Echify-App/assets/help.wav"):
        self.wav_path = wav_path

    def play_help_instant(self):
        def _run():
            try:
                print(f"🔊 Playing emergency audio: {self.wav_path}")
                subprocess.run(
                    ["aplay", "-D", "default", self.wav_path],
                    check=False
                )
            except Exception as e:
                print(f"❌ Emergency audio error: {e}")

        threading.Thread(target=_run, daemon=True).start()