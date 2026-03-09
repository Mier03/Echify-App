# import subprocess
# import os
# import signal
# import sys
# import time

# gstreamer_process = None

# def cleanup(*args):
#     global gstreamer_process
#     print("Stopping camera engine...")
#     if gstreamer_process and gstreamer_process.poll() is None:
#         gstreamer_process.terminate()
#         try:
#             gstreamer_process.wait(timeout=5)
#         except subprocess.TimeoutExpired:
#             gstreamer_process.kill()
#     sys.exit(0)

# def start_gstreamer():
#     global gstreamer_process
#     print("Starting GStreamer bridge...")

#     command = [
#         "env", "GST_PLUGIN_FEATURE_RANK=v4l2codecs:NONE",
#         "gst-launch-1.0",
#         "libcamerasrc", "!",
#         "video/x-raw,width=640,height=480,format=YUY2", "!",
#         "videoconvert", "!",
#         "v4l2sink", "device=/dev/video10"
#     ]

#     gstreamer_process = subprocess.Popen(command)
#     return gstreamer_process

# if __name__ == "__main__":
#     signal.signal(signal.SIGINT, cleanup)
#     signal.signal(signal.SIGTERM, cleanup)

#     print("Initializing camera loopback device...")
#     os.system("sudo modprobe v4l2loopback video_nr=10 card_label='Echify-Camera' exclusive_caps=1")
#     os.system("sudo chmod 777 /dev/video10")

#     start_gstreamer()

#     print("Camera engine is running.")
#     while True:
#         time.sleep(1)
import subprocess
import os
import signal
import sys
import time

gstreamer_process = None

def run_command(command):
    print(">", " ".join(command))
    return subprocess.run(command, check=False)

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

    run_command(["pkill", "-f", "gst-launch-1.0"])
    run_command(["sudo", "modprobe", "-r", "v4l2loopback"])
    time.sleep(1)

    run_command([
        "sudo",
        "modprobe",
        "v4l2loopback",
        "video_nr=10",
        "card_label=Echify-Camera",
        "exclusive_caps=0",
    ])
    time.sleep(1)

    if not os.path.exists("/dev/video10"):
        print("ERROR: /dev/video10 was not created")
        sys.exit(1)

    run_command(["sudo", "chmod", "666", "/dev/video10"])
    print("Loopback device ready: /dev/video10")

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
        "videoconvert",
        "!",
        "queue",
        "!",
        "video/x-raw,format=YUY2,width=640,height=480,framerate=30/1",
        "!",
        "v4l2sink",
        "device=/dev/video10",
        "sync=false",
    ]

    gstreamer_process = subprocess.Popen(command)
    return gstreamer_process

if __name__ == "__main__":
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    setup_loopback()
    start_gstreamer()

    print("Camera engine is running.")

    while True:
        if gstreamer_process and gstreamer_process.poll() is not None:
            print("ERROR: GStreamer process exited unexpectedly")
            sys.exit(1)
        time.sleep(1)