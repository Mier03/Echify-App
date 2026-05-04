# tts_engine.py
import re
import queue
import subprocess
import threading
from pathlib import Path
from TTS.api import TTS

tts = TTS(
    model_name="tts_models/en/ljspeech/glow-tts",
    progress_bar=False
)

OUTPUT_DIR = Path("/tmp/coqui_tts")
OUTPUT_DIR.mkdir(exist_ok=True)

speech_queue = queue.Queue()

# Warm up model once
try:
    tts.tts_to_file(text="hello", file_path=str(OUTPUT_DIR / "warmup.wav"))
except Exception as e:
    print(f"Warmup error: {e}")


def split_text(text, max_len=70):
    words = text.strip().split()
    chunks = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 > max_len:
            chunks.append(current.strip())
            current = word
        else:
            current += " " + word

    if current.strip():
        chunks.append(current.strip())

    return chunks


def speech_worker():
    while True:
        text = speech_queue.get()

        try:
            chunks = split_text(text)

            for i, chunk in enumerate(chunks):
                output_path = OUTPUT_DIR / f"chunk_{i}.wav"

                print(f"🔊 Speaking chunk: {chunk}")

                tts.tts_to_file(
                    text=chunk,
                    file_path=str(output_path)
                )

                subprocess.run(
                    ["aplay", str(output_path)],
                    check=False
                )

        except Exception as e:
            print(f"❌ TTS error: {e}")

        speech_queue.task_done()


threading.Thread(target=speech_worker, daemon=True).start()


def speak(text: str):
    if not text or not text.strip():
        return

    speech_queue.put(text.strip())


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