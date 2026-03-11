import os
import signal
import subprocess
import sys
import time

gstreamer_process = None


def run_command(command: str) -> int:
    print(f"Running: {command}")
    return os.system(command)


def cleanup(*args):
    global gstreamer_process
    print("Stopping camera engine...")

    if gstreamer_process and gstreamer_process.poll() is None:
        gstreamer_process.terminate()
        try:
            gstreamer_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gstreamer_process.kill()

    sys.exit(0)


def ensure_loopback_device():
    print("Initializing camera loopback device...")

    # Remove old module if loaded
    run_command("sudo modprobe -r v4l2loopback 2>/dev/null")

    # Recreate virtual webcam
    exit_code = run_command(
        "sudo modprobe v4l2loopback "
        "video_nr=10 "
        "card_label='Echify-Camera' "
        "exclusive_caps=1"
    )

    if exit_code != 0:
        print("❌ Failed to load v4l2loopback")
        sys.exit(1)

    time.sleep(2)

    if not os.path.exists("/dev/video10"):
        print("❌ /dev/video10 was not created")
        sys.exit(1)

    run_command("sudo chmod 777 /dev/video10")
    print("✅ /dev/video10 ready")


def start_gstreamer():
    global gstreamer_process

    print("Starting GStreamer bridge...")

    command = [
        "env",
        "GST_PLUGIN_FEATURE_RANK=v4l2codecs:NONE",
        "gst-launch-1.0",
        "-v",
        "libcamerasrc",
        "!",
        "video/x-raw,width=640,height=480,framerate=30/1",
        "!",
        "videoconvert",
        "!",
        "video/x-raw,format=YUY2",
        "!",
        "v4l2sink",
        "device=/dev/video10",
        "sync=false",
    ]

    try:
        gstreamer_process = subprocess.Popen(command)
    except FileNotFoundError as exc:
        print(f"❌ Failed to start GStreamer: {exc}")
        sys.exit(1)

    time.sleep(4)

    if gstreamer_process.poll() is not None:
        print("❌ GStreamer bridge exited unexpectedly")
        sys.exit(1)

    print("✅ GStreamer bridge running")
    return gstreamer_process


if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    ensure_loopback_device()
    start_gstreamer()

    print("Camera engine is running.")

    while True:
        time.sleep(1)