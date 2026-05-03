# tts_engine.py
import subprocess
import threading
from pathlib import Path
from TTS.api import TTS
from pydub import AudioSegment

# Load Coqui once
tts = TTS(
    model_name="tts_models/en/ljspeech/speedy-speech",
    progress_bar=False,
    gpu=False
)


OUTPUT_PATH = Path("/tmp/coqui_output.wav")
SLOW_OUTPUT_PATH = Path("/tmp/coqui_output_slow.wav")

# 1.0 = normal, lower = slower
SPEECH_SPEED = 1.0


def slow_down_wav(input_path, output_path, speed=0.85):
    audio = AudioSegment.from_wav(input_path)

    slowed = audio._spawn(
        audio.raw_data,
        overrides={
            "frame_rate": int(audio.frame_rate * speed)
        }
    ).set_frame_rate(audio.frame_rate)

    slowed.export(output_path, format="wav")


def speak(text: str):
    if not text or not text.strip():
        return

    def _run():
        try:
            print(f"🔊 Speaking with Coqui: {text}")

            tts.tts_to_file(
                text=text,
                file_path=str(OUTPUT_PATH)
            )

            slow_down_wav(
                OUTPUT_PATH,
                SLOW_OUTPUT_PATH,
                SPEECH_SPEED
            )

            subprocess.run(
                ["aplay", "-D", "default", str(SLOW_OUTPUT_PATH)],
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