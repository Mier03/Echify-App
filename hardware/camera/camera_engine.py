import os
import signal
import subprocess
import sys
import time

gstreamer_process = None

def run_command(command: list[str], check: bool = False):
    try:
        result = subprocess.run(command, check=check, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return result
    except Exception as e:
        print(f"Command failed: {' '.join(command)}")
        print(str(e))
        return None

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

def setup_loopback():
    print("Initializing camera loopback device...")

    run_command(["sudo", "modprobe", "-r", "v4l2loopback"])
    time.sleep(1)

    run_command([
        "sudo", "modprobe", "v4l2loopback",
        "video_nr=10",
        "card_label=Echify-Camera",
        "exclusive_caps=0"
    ])

    for _ in range(10):
        if os.path.exists("/dev/video10"):
            break
        time.sleep(0.5)

    if not os.path.exists("/dev/video10"):
        print("ERROR: /dev/video10 was not created.")
        sys.exit(1)

    run_command(["sudo", "chmod", "666", "/dev/video10"])
    print("Loopback device ready: /dev/video10")

def check_camera():
    print("Checking Pi camera...")
    result = run_command(["libcamera-hello", "--list-cameras"])

    if result is None or result.returncode != 0:
        print("ERROR: No usable Pi camera detected by libcamera.")
        sys.exit(1)

def start_gstreamer():
    global gstreamer_process
    print("Starting GStreamer bridge...")

    command = [
        "bash", "-lc",
        "GST_PLUGIN_FEATURE_RANK=v4l2codecs:NONE "
        "gst-launch-1.0 -v "
        "libcamerasrc ! "
        "video/x-raw,width=640,height=480,format=YUY2 ! "
        "videoconvert ! "
        "v4l2sink device=/dev/video10 sync=false"
    ]

    gstreamer_process = subprocess.Popen(command)
    time.sleep(3)

    if gstreamer_process.poll() is not None:
        print("ERROR: GStreamer pipeline exited immediately.")
        sys.exit(1)

    print("GStreamer bridge running.")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    check_camera()
    setup_loopback()
    start_gstreamer()

    print("Camera engine is running.")
    while True:
        time.sleep(1)