import subprocess
import os
import signal
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

def start_gstreamer():
    global gstreamer_process
    print("Starting GStreamer bridge...")

    command = [
        "env", "GST_PLUGIN_FEATURE_RANK=v4l2codecs:NONE",
        "gst-launch-1.0",
        "libcamerasrc", "!",
        "video/x-raw,width=640,height=480,format=YUY2", "!",
        "videoconvert", "!",
        "v4l2sink", "device=/dev/video10"
    ]

    gstreamer_process = subprocess.Popen(command)
    return gstreamer_process

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("Initializing camera loopback device...")
    os.system("sudo modprobe v4l2loopback video_nr=10 card_label='Echify-Camera' exclusive_caps=1")
    os.system("sudo chmod 777 /dev/video10")

    start_gstreamer()

    print("Camera engine is running.")
    while True:
        time.sleep(1)