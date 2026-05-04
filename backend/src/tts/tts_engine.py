# tts_engine.py
import subprocess
import threading
from pathlib import Path
from TTS.api import TTS

tts = TTS(
    model_name="tts_models/en/ljspeech/glow-tts",
    progress_bar=False
)

OUTPUT_PATH = Path("/tmp/coqui_output.wav")


def speak(text: str):
    text = text.strip()[:120]

    if not text:
        return

    def _run():
        try:
            print(f"🔊 Speaking: {text}")

            tts.tts_to_file(
                text=text,
                file_path=str(OUTPUT_PATH)
            )

            subprocess.run(
                ["aplay", str(OUTPUT_PATH)],
                check=False
            )

        except Exception as e:
            print(f"❌ TTS error: {e}")

    threading.Thread(target=_run, daemon=True).start()


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