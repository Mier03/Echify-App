import pygame
import os
import threading

class EmergencyAudio:
    def __init__(self, mp3_name="help_me.mp3"):
        self.mp3_path = f"/home/sms/Echify-App/hardware/button/{mp3_name}"
        self.mixer_ready = False
        
        # Initialize pygame safely inside the class
        try:
            # Optional: Uncomment the next line if ALSA still acts up on the Pi
            # os.environ['SDL_AUDIODRIVER'] = 'pulseaudio' 
            pygame.mixer.init()
            self.mixer_ready = True
            print("✅ Pygame audio initialized successfully.")
        except Exception as e:
            print(f"⚠️ Warning: Pygame audio failed to initialize. Error: {e}")

    def play_help_instant(self):
        if not self.mixer_ready:
            print("❌ Cannot play audio: Mixer failed to initialize on startup.")
            return

        def _run():
            try:
                if os.path.exists(self.mp3_path):
                    print(f"🔊 Playing: {self.mp3_path}")
                    pygame.mixer.music.load(self.mp3_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10) # Prevents CPU maxing out in the loop
                else:
                    print(f"❌ Audio file not found at: {self.mp3_path}")
            except Exception as e:
                print(f"Audio Error: {e}")

        threading.Thread(target=_run, daemon=True).start()