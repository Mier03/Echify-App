from gpiozero import Button
from tts.tts_engine import EmergencyAudio
import time
from signal import pause

audio = EmergencyAudio("help_me.mp3")

# Add debounce to prevent false/multiple triggers
button = Button(26, pull_up=True, bounce_time=0.1)

press_count = 0
last_press_time = 0
RESET_TIMEOUT = 0.8  # Time window to complete 3 presses

def handle_press():
    global press_count, last_press_time

    current_time = time.time()

    # Reset if too slow between presses
    if current_time - last_press_time > RESET_TIMEOUT:
        press_count = 1
    else:
        press_count += 1

    last_press_time = current_time

    print(f"Button Pressed! Count: {press_count}/3", flush=True)

    # IMPORTANT: use >= instead of ==
    if press_count >= 3:
        print("🚨 Triple Press Detected! Playing 'Help me!'...", flush=True)

        audio.play_help_instant()

        # Reset so it can trigger again unlimited times
        press_count = 0
        last_press_time = 0


# Attach event
button.when_pressed = handle_press

print("=" * 40, flush=True)
print("Pi 5 Emergency System Active", flush=True)
print("Press button 3x quickly to speak.", flush=True)
print("=" * 40, flush=True)

pause()