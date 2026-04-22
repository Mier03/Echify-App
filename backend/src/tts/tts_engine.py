# tts_engine.py
import subprocess
import threading


def speak(text: str):
    if not text or not text.strip():
        return

    def _run():
        try:
            print(f"🔊 Speaking: {text}")

            # Generate WAV stream from espeak
            espeak = subprocess.Popen(
               ["espeak", "-a", "200", "-s", "150", "--stdout", text],
                stdout=subprocess.PIPE
            )

            # Play it correctly using ALSA (let aplay auto-detect WAV format)
            subprocess.run(
                ["aplay", "-D", "default"],
                stdin=espeak.stdout,
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