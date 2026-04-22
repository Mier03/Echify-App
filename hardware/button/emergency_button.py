from gpiozero import Button
from tts.tts_engine import EmergencyAudio
from session_logger import global_logger
import time
from signal import pause
from threading import Thread

audio = EmergencyAudio("help.mp3")
button = Button(26, pull_up=True, bounce_time=0.1)

press_count = 0
last_press_time = 0
RESET_TIMEOUT = 0.8

global_logger.start()

def play_audio_and_log():
    start = time.perf_counter()
    success = True

    try:
        audio.play_help_instant()
    except Exception as e:
        success = False
        response_time_ms = (time.perf_counter() - start) * 1000
        global_logger.log_sos(
            response_time_ms=response_time_ms,
            state="triggered",
            success=False,
            notes=f"triple_press audio_error={e}"
        )
        return

    response_time_ms = (time.perf_counter() - start) * 1000
    global_logger.log_sos(
        response_time_ms=response_time_ms,
        state="triggered",
        success=True,
        notes="triple_press help_me_audio_played"
    )

def handle_press():
    global press_count, last_press_time
    current_time = time.time()

    if current_time - last_press_time > RESET_TIMEOUT:
        press_count = 1
    else:
        press_count += 1

    last_press_time = current_time
    print(f"Button Pressed! Count: {press_count}/3")

    if press_count == 3:
        print("🚨 Triple Press Detected! Playing 'Help me!'...")
        press_count = 0
        last_press_time = 0

        Thread(target=play_audio_and_log, daemon=True).start()

button.when_pressed = handle_press

print("=" * 40)
print("Pi 5 Emergency System Active")
print("Press button 3x quickly to speak.")
print("=" * 40)

pause()
