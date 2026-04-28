from gpiozero import Button
from tts.tts_engine import EmergencyAudio
import time
from signal import pause
import requests

audio = EmergencyAudio("help_me.mp3")

button = Button(26, pull_up=True, bounce_time=0.03)

press_count = 0
last_press_time = 0
RESET_TIMEOUT = 0.8

BACKEND_URL = "http://localhost:8000/sos-triggered"

def notify_app():
    try:
        requests.post(BACKEND_URL, json={
            "state": "triggered",
            "response_time_ms": 0.0,
            "success": True,
            "client_id": "physical_button"
        }, timeout=1)
        print("✅ SOS notification sent to backend", flush=True)
    except Exception as e:
        print(f"⚠️ Failed to notify backend: {e}", flush=True)

def handle_press():
    global press_count, last_press_time

    current_time = time.time()

    if current_time - last_press_time > RESET_TIMEOUT:
        press_count = 1
    else:
        press_count += 1

    last_press_time = current_time

    print(f"Button Pressed! Count: {press_count}/3", flush=True)

    if press_count >= 3:
        print("🚨 Triple Press Detected! Playing 'Help me!'...", flush=True)

        audio.play_help_instant()
        notify_app()

        press_count = 0
        last_press_time = 0

button.when_pressed = handle_press

print("=" * 40, flush=True)
print("Pi 5 Emergency System Active", flush=True)
print("Press button 3x quickly to speak.", flush=True)
print("=" * 40, flush=True)

pause()