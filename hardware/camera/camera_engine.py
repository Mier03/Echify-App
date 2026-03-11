import os
import signal
import subprocess
import sys
import time

gstreamer_process = None


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


def ensure_video_device():
    if not os.path.exists("/dev/video10"):
        print("❌ /dev/video10 not found")
        sys.exit(1)

    print("✅ /dev/video10 found")


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
        "video/x-raw,width=640,height=480,format=NV12,colorimetry=bt601,framerate=30/1",
        "!",
        "videoflip", "method=rotate-180",
        "!",
        "videoconvert",
        "!",
        "video/x-raw,format=I420",
        "!",
        "v4l2sink",
        "device=/dev/video10",
        "sync=false",
    ]

    try:
        gstreamer_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError as exc:
        print(f"❌ Failed to start GStreamer: {exc}")
        sys.exit(1)

    time.sleep(4)

    if gstreamer_process.poll() is not None:
        output = gstreamer_process.stdout.read() if gstreamer_process.stdout else ""
        print("❌ GStreamer bridge exited unexpectedly")
        print(output)
        sys.exit(1)

    print("✅ GStreamer bridge running")
    return gstreamer_process


if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    ensure_video_device()
    start_gstreamer()

    print("Camera engine is running.")

    while True:
        time.sleep(1)